"""Free re-cut of the Higgsfield walk-through: drop the invented NOMA-mural room.

street (shot 1) -> door, before it opens (start of shot 2) -> push through the glass
(zoom + motion blur + dissolve) -> reception, from the moment only the real lobby is in view
(end of shot 3).

    python -E higgsfield/free_cut.py desktop
    python -E higgsfield/free_cut.py phone
"""
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image, ImageFilter

FF = imageio_ffmpeg.get_ffmpeg_exe()
V = "higgsfield/video/"
FPS = 24
CUTS = {   # clip names, shot-2 keep (s), shot-3 resume (s), door-glass centre (x, y as share of frame)
    "desktop": dict(s1="shot1_day_1080p", s2="shot2_day_1080p", s3="shot3_day_1080p", w=1920, h=1080,
                    keep2=0.62, resume3=3.6, door=(0.33, 0.45)),
    "phone": dict(s1="p1_day_1080p", s2="p2_day_1080p", s3="p3_day_1080p", w=1080, h=1920,
                  keep2=0.7, resume3=2.95, door=(0.33, 0.47)),
}
TRANS = 12   # frames of the push-through


def frames(name, w, h, start=0.0, dur=None):
    cmd = [FF, "-loglevel", "error", "-ss", str(start), "-i", V + name + ".mp4"]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    return [np.frombuffer(raw, np.uint8, w * h * 3, i * w * h * 3).reshape(h, w, 3) for i in range(n)]


def zoom(img, s, cx, cy, blur):
    """scale an image by s around (cx, cy) (shares of the frame), with a little motion blur"""
    im = Image.fromarray(img)
    W, H = im.size
    cw, ch = W / s, H / s
    x0 = min(max(0, cx * W - cw / 2), W - cw)
    y0 = min(max(0, cy * H - ch / 2), H - ch)
    im = im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
    if blur > 0.2:
        im = im.filter(ImageFilter.GaussianBlur(blur))
    return np.asarray(im)


def build(kind, keep2, resume3):
    c = CUTS[kind]
    w, h = c["w"], c["h"]
    a = frames(c["s1"], w, h)
    b = frames(c["s2"], w, h, 0, keep2 + TRANS / 2 / FPS)
    d = frames(c["s3"], w, h, resume3 - TRANS / 2 / FPS)
    keep_b = round(keep2 * FPS)
    out = a + b[:keep_b]
    cx, cy = c["door"]
    for i in range(TRANS):
        k = (i + 1) / TRANS
        e = k * k * (3 - 2 * k)
        src = b[min(keep_b + i // 2, len(b) - 1)]
        dst = d[min(i // 2, len(d) - 1)]
        pa = zoom(src, 1 + 1.4 * e, cx, cy, 10 * np.sin(np.pi * k))           # push into the glass
        pb = zoom(dst, 1.25 - 0.25 * e, 0.5, 0.5, 10 * np.sin(np.pi * k) * (1 - k))   # settle into the lobby
        mix = np.clip((k - 0.25) / 0.6, 0, 1)
        out.append((pa * (1 - mix) + pb * mix).astype(np.uint8))
    out += d[TRANS // 2:]
    dst = V + f"noma-walkthrough-day-{kind}-cut.mp4"
    enc = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
                            "-s", f"{w}x{h}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18",
                            "-preset", "slow", "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst],
                           stdin=subprocess.PIPE)
    for f in out:
        enc.stdin.write(f.tobytes())
    enc.stdin.close()
    enc.wait()
    print(dst, len(out) / FPS, "s")


if __name__ == "__main__":
    kind = sys.argv[1]
    c = CUTS[kind]
    keep2 = float(sys.argv[2]) if len(sys.argv) > 2 else c["keep2"]
    resume3 = float(sys.argv[3]) if len(sys.argv) > 3 else c["resume3"]
    build(kind, keep2, resume3)

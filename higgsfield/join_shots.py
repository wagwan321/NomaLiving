"""Join the walk-through shots into one clip, hiding the joins.

Each shot ends on the keyframe the next one starts from, but the generated end and start
frames never match exactly (a few % in scale, a slight tone shift). At every join the last
frames of the outgoing shot are eased in scale and position onto the first frame of the next
shot, then the two blend over a few frames.

    python -E higgsfield/join_shots.py desktop
    python -E higgsfield/join_shots.py phone
"""
import subprocess
import sys

import imageio_ffmpeg
import numpy as np
from PIL import Image

FF = imageio_ffmpeg.get_ffmpeg_exe()
V = "higgsfield/video/"
FPS = 24
SETS = {
    "desktop": (1920, 1080, ["shot1_day_clear", "b_desk_clean", "c_desk"]),
    "phone": (1080, 1920, ["p1_day_clear", "b_phone_clean2", "c_phone"]),
    "tour-desktop": (1920, 1080, ["shot1_day_clear", "../tour/tour_desk_1080p"]),
    "tour3-desktop": (1920, 1080, ["shot1_day_clear", "../tour/tour3_1920"]),
    "tour4-desktop": (1920, 1080, ["../tour4/s1_head", "../tour4/vB_tail"]),
}
# phone shot 3 overshoots its end frame (it invents a window and an arched door after 4.5 s):
# stop it there, slowing down smoothly instead of cutting mid-motion
TRIM = {"c_phone": 4.5}
SETTLE = 0.8   # seconds of the trimmed end that are stretched into a slow-down
EASE, BLEND = 12, 6   # frames: scale/position easing before a join, cross-blend across it


def frames(name, w, h):
    raw = subprocess.run([FF, "-loglevel", "error", "-i", V + name + ".mp4", "-vf", f"scale={w}:{h}:flags=lanczos,fps={FPS}",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    n = len(raw) // (w * h * 3)
    return [np.frombuffer(raw, np.uint8, w * h * 3, i * w * h * 3).reshape(h, w, 3) for i in range(n)]


def gray(a, s=8):
    return np.asarray(Image.fromarray(a).convert("L").resize((a.shape[1] // s, a.shape[0] // s)), np.float32)


def fit(a, b):
    """scale and shift that make frame a look like frame b (searched on small greyscale copies)"""
    gb = gray(b)
    best = (1e9, 1.0, 0, 0)
    for s in np.arange(1.0, 1.081, 0.01):
        for dx in range(-30, 31, 6):
            for dy in range(-20, 21, 5):
                e = np.mean(np.abs(gray(transform(a, s, dx, dy)) - gb))
                if e < best[0]:
                    best = (e, s, dx, dy)
    # fine pass around the coarse result, on a sharper copy, to the pixel
    gb = gray(b, 3)
    _, s0, x0, y0 = best
    best = (1e9, s0, x0, y0)
    for s in np.arange(s0 - 0.01, s0 + 0.0101, 0.0025):
        if s < 1:
            continue
        for dx in range(x0 - 6, x0 + 7, 1):
            for dy in range(y0 - 5, y0 + 6, 1):
                e = np.mean(np.abs(gray(transform(a, s, dx, dy), 3) - gb))
                if e < best[0]:
                    best = (e, s, dx, dy)
    return best[1:]


def transform(a, s, dx, dy):
    im = Image.fromarray(a)
    W, H = im.size
    cw, ch = W / s, H / s
    x0 = min(max(0.0, (W - cw) / 2 - dx / s), W - cw)
    y0 = min(max(0.0, (H - ch) / 2 - dy / s), H - ch)
    return np.asarray(im.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)))


def settle(fr, end):
    """keep the shot up to `end` s and ease its last SETTLE s out to a standstill (frame blending)"""
    n = round(end * FPS)
    fr, m = fr[:n], round(SETTLE * FPS)
    head, tail = fr[:n - m], fr[n - m:]
    out_len = round(m * 1.8)                       # the last stretch plays 1.8x longer, slowing to a stop
    res = []
    for i in range(out_len):
        k = (i + 1) / out_len
        t = (1 - (1 - k) ** 2) * (m - 1)           # ease-out position along the original frames
        a = int(t)
        f = t - a
        b = min(a + 1, m - 1)
        res.append((tail[a] * (1 - f) + tail[b] * f).astype(np.uint8))
    return head + res


def build(kind):
    w, h, names = SETS[kind]
    shots = [settle(frames(n, w, h), TRIM[n]) if n in TRIM else frames(n, w, h) for n in names]
    out = list(shots[0])
    for nxt in shots[1:]:
        s, dx, dy = fit(out[-1], nxt[0])            # outgoing shot is the wider one: zoom it in
        s2, dx2, dy2 = fit(nxt[0], out[-1])          # incoming shot is the wider one: zoom it in
        e_out = np.mean(np.abs(gray(transform(out[-1], s, dx, dy)) - gray(nxt[0])))
        e_in = np.mean(np.abs(gray(transform(nxt[0], s2, dx2, dy2)) - gray(out[-1])))
        nxt = list(nxt)
        if e_out <= e_in:
            print(f"join: outgoing scale {s:.2f}, shift {dx},{dy}")
            for i in range(EASE):                   # ease the outgoing frames onto the next shot's framing
                k = (i + 1) / EASE
                e = k * k * (3 - 2 * k)
                j = len(out) - EASE + i
                out[j] = transform(out[j], 1 + (s - 1) * e, dx * e, dy * e)
        else:
            print(f"join: incoming scale {s2:.2f}, shift {dx2},{dy2}")
            for i in range(EASE):                   # start the next shot on the previous framing, ease back
                k = i / EASE
                e = 1 - k * k * (3 - 2 * k)
                nxt[i] = transform(nxt[i], 1 + (s2 - 1) * e, dx2 * e, dy2 * e)
        from resample import between, flow          # motion-based morph: no double images
        for i in range(BLEND):                      # morph across the join
            m = (i + 1) / (BLEND + 1)
            j = len(out) - BLEND + i
            A, B = np.ascontiguousarray(out[j]), np.ascontiguousarray(nxt[i])
            sc = 960 / max(A.shape[:2])
            out[j] = between(A, B, m, flow(A, B, sc), flow(B, A, sc))
        out += nxt[BLEND:]
    dst = V + f"noma-walkthrough-day-{kind}-v2.mp4"
    enc = subprocess.Popen([FF, "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                            "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "18", "-preset", "slow",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", dst], stdin=subprocess.PIPE)
    for f in out:
        enc.stdin.write(f.tobytes())
    enc.stdin.close()
    enc.wait()
    print(dst, f"{len(out) / FPS:.1f} s")


if __name__ == "__main__":
    build(sys.argv[1])

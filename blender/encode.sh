#!/usr/bin/env bash
# Encode the rendered PNG frames (blender/render/f_####.png) into the web intro videos.
# Usage: bash blender/encode.sh   (from the project root)
set -euo pipefail
FF="${FFMPEG:-$(python -c 'import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())')}"
IN="blender/render/f_%04d.png"
OUT="assets/video"
mkdir -p "$OUT"

# desktop: 1080p H.264, fast start for streaming
"$FF" -y -loglevel error -framerate 30 -i "$IN" -c:v libx264 -preset slow -crf 20 -pix_fmt yuv420p -movflags +faststart -an "$OUT/noma-intro.mp4"
# phones: 720p, lighter
"$FF" -y -loglevel error -framerate 30 -i "$IN" -vf scale=1280:-2 -c:v libx264 -preset slow -crf 23 -pix_fmt yuv420p -movflags +faststart -an "$OUT/noma-intro-720.mp4"
# poster = first frame, shown while the video loads
"$FF" -y -loglevel error -i "blender/render/f_0001.png" -vf scale=1600:-2 -q:v 3 "$OUT/noma-intro-poster.jpg"

ls -la "$OUT"

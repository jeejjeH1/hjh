#!/usr/bin/env bash
# Rebuild the video: renders frames with headless Chromium (Playwright),
# synthesises the soundtrack, then muxes a Twitter/X-ready MP4.
set -euo pipefail
cd "$(dirname "$0")/src"
export NODE_PATH="${NODE_PATH:-$(npm root -g)}"
OUT=../out; TMP=$(mktemp -d); mkdir -p "$OUT"
FPS=60; FRAMES=$((66*FPS)); WORKERS=4; CH=$(( (FRAMES+WORKERS-1)/WORKERS ))
for i in $(seq 0 $((WORKERS-1))); do
  s=$((i*CH)); e=$(( (i+1)*CH < FRAMES ? (i+1)*CH : FRAMES ))
  node render.js video $s $e $FPS "$TMP/seg$i.mp4" &
done; wait
for i in $(seq 0 $((WORKERS-1))); do echo "file '$TMP/seg$i.mp4'"; done > "$TMP/list.txt"
python3 music.py "$TMP/music.wav"
ffmpeg -y -loglevel error -f concat -safe 0 -i "$TMP/list.txt" -i "$TMP/music.wav" \
  -map 0:v -map 1:a -c:v libx264 -preset slow -profile:v high -level 4.2 -crf 18 -maxrate 14M -bufsize 28M \
  -pix_fmt yuv420p -r $FPS -g 120 -af "loudnorm=I=-14:TP=-1.5:LRA=11" -c:a aac -b:a 192k -ar 48000 \
  -movflags +faststart -shortest "$OUT/genlayer_insurance.mp4"
echo "done -> out/genlayer_insurance.mp4"

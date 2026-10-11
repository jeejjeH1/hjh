# GenLayer × Insurance — motion graphic

`out/genlayer_insurance.mp4` — 66 s, 1920×1080 (16:9), 60 fps, H.264 High + AAC (ready for X/Twitter).

- `src/index.html` — the whole animation, drawn on canvas. Open it in a browser to watch a live preview (add `?t=26` to start at a given second).
- `src/render.js` — renders frames with headless Chromium (Playwright) and pipes them into ffmpeg.
- `src/music.py` — synthesises the soundtrack (120 BPM, F minor) with cues synced to the animation.
- `build.sh` — rebuilds everything from scratch.

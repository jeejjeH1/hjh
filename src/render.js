// Usage:
//   node render.js stills <t1,t2,...> <outDir>
//   node render.js video <startFrame> <endFrame> <fps> <out.mp4>
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const { chromium } = require('playwright');

async function open() {
  const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--force-color-profile=srgb'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1080 }, deviceScaleFactor: 1 });
  await page.goto('file://' + path.join(__dirname, 'index.html') + '?render');
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => { renderFrame(1); renderFrame(30); }); // warm up fonts / shaders
  return { browser, page };
}

const grab = (page, t, type, q) => page.evaluate(([t, type, q]) => {
  renderFrame(t);
  return document.getElementById('c').toDataURL(type, q).split(',')[1];
}, [t, type, q]);

(async () => {
  const [mode, ...args] = process.argv.slice(2);
  const { browser, page } = await open();
  if (mode === 'stills') {
    const ts = args[0].split(',').map(Number), out = args[1];
    fs.mkdirSync(out, { recursive: true });
    for (const t of ts) {
      const b64 = await grab(page, t, 'image/png');
      fs.writeFileSync(path.join(out, `t${t.toFixed(2).padStart(6, '0')}.png`), Buffer.from(b64, 'base64'));
    }
  } else if (mode === 'video') {
    const [f0, f1, fps, out] = [+args[0], +args[1], +args[2], args[3]];
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-',
      '-c:v', 'libx264', '-preset', 'slow', '-crf', '10', '-pix_fmt', 'yuv420p', '-r', String(fps), out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let f = f0; f < f1; f++) {
      const b64 = await grab(page, f / fps, 'image/jpeg', 0.97);
      const buf = Buffer.from(b64, 'base64');
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if ((f - f0) % 120 === 0) console.error(`[${f0}-${f1}] frame ${f} ${((Date.now() - t0) / 1000).toFixed(1)}s`);
    }
    ff.stdin.end();
    await new Promise(r => ff.on('close', r));
  }
  await browser.close();
})();

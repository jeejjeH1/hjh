"""Synthesised soundtrack for the GenLayer motion graphic.
120 BPM, F minor (i–VI–III–VII), cues locked to the animation timeline.
Writes a 48 kHz stereo WAV:  python3 music.py out.wav
"""
import sys
import numpy as np
from scipy import signal
from scipy.io import wavfile

SR = 48000
DUR = 66.0
N = int(SR * DUR)
BEAT = 0.5
rng = np.random.default_rng(7)

dry = np.zeros((N, 2))
send = np.zeros((N, 2))  # reverb bus
pump = np.zeros((N, 2))  # sidechained bus (bass/pad/arp)


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def tt(d):
    return np.arange(int(d * SR)) / SR


def place(bus, t0, sig, gain=1.0, pan=0.0):
    i0 = int(round(t0 * SR))
    if sig.ndim == 1:
        l, r = np.cos((pan + 1) * np.pi / 4), np.sin((pan + 1) * np.pi / 4)
        sig = np.stack([sig * l * 1.414, sig * r * 1.414], 1)
    if i0 < 0:
        sig = sig[-i0:]
        i0 = 0
    n = min(len(sig), N - i0)
    if n > 0:
        bus[i0:i0 + n] += sig[:n] * gain


def filt(x, kind, f, order=2):
    sos = signal.butter(order, f, kind, fs=SR, output='sos')
    return signal.sosfilt(sos, x, axis=0)


def sweep_filter(x, f0, f1, kind='bandpass', bw=0.6, chunk=256):
    """Time-varying filter (exponential sweep f0->f1)."""
    out = np.zeros_like(x)
    n = len(x)
    zi = None
    for s in range(0, n, chunk):
        fr = s / max(1, n - 1)
        fc = f0 * (f1 / f0) ** fr
        if kind == 'bandpass':
            wn = [max(20, fc * (1 - bw / 2)), min(SR / 2 - 100, fc * (1 + bw / 2))]
        else:
            wn = min(SR / 2 - 100, fc)
        sos = signal.butter(2, wn, kind, fs=SR, output='sos')
        if zi is None or zi.shape != (sos.shape[0], 2):
            zi = np.zeros((sos.shape[0], 2))
        out[s:s + chunk], zi = signal.sosfilt(sos, x[s:s + chunk], zi=zi)
    return out


def saw(f, t, ph=0.0):
    return 2 * ((f * t + ph) % 1) - 1


# ------------------------------------------------------------------ instruments
def kick():
    t = tt(0.55)
    f = 42 + 120 * np.exp(-t * 28)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 6.5)
    s += filt(rng.standard_normal(len(t)), 'highpass', 2000) * np.exp(-t * 250) * 0.25
    return np.tanh(s * 1.6)


def clap():
    t = tt(0.4)
    n = filt(rng.standard_normal(len(t)), 'bandpass', [900, 3200])
    env = np.zeros_like(t)
    for k, d in enumerate([0, 0.011, 0.022]):
        env += (t >= d) * np.exp(-(t - d).clip(0) * (140 if k < 2 else 16))
    body = np.sin(2 * np.pi * 190 * t) * np.exp(-t * 30) * 0.4
    return (n * env + body) * 0.7


def hat(open_=False):
    t = tt(0.3 if open_ else 0.08)
    n = filt(rng.standard_normal(len(t)), 'highpass', 7500)
    return n * np.exp(-t * (14 if open_ else 70)) * 0.5


def pluck(f, d=0.22, bright=3500):
    t = tt(d)
    s = np.sign(np.sin(2 * np.pi * f * t)) * 0.5 + saw(f * 1.003, t) * 0.5
    s = filt(s, 'lowpass', bright)
    return s * np.exp(-t * 16) * (1 - np.exp(-t * 800))


def bass_note(f, d):
    t = tt(d)
    s = saw(f, t) * 0.6 + saw(f * 1.006, t) * 0.4
    s = filt(s, 'lowpass', 520) + np.sin(2 * np.pi * f * t) * 0.6
    env = (1 - np.exp(-t * 400)) * np.exp(-t * 4)
    env *= np.clip((d - t) / 0.02, 0, 1)
    return s * env


def pad_chord(notes, d, cutoff=1400):
    t = tt(d)
    L = np.zeros_like(t)
    R = np.zeros_like(t)
    for m in notes:
        f = mtof(m)
        for k, det in enumerate([-0.11, 0.0, 0.12]):
            ff = f * 2 ** (det / 12)
            ph = rng.random()
            v = saw(ff, t, ph)
            if k == 0:
                L += v
            elif k == 2:
                R += v
            else:
                L += v * .6
                R += v * .6
    s = np.stack([L, R], 1)
    s = filt(s, 'lowpass', cutoff)
    att, rel = 0.35, 0.6
    env = np.clip(t / att, 0, 1) * np.clip((d - t) / rel, 0, 1)
    return s * env[:, None] * 0.09


def riser(d, f0=300, f1=6000):
    n = rng.standard_normal(int(d * SR))
    s = sweep_filter(n, f0, f1, 'bandpass', 0.5)
    t = tt(d)
    tone = np.sin(2 * np.pi * np.cumsum(110 * 2 ** (3 * t / d)) / SR) * 0.25
    env = (t / d) ** 2.2
    return (s * 0.9 + tone) * env


def whoosh(d=0.8, f0=400, f1=5000):
    n = rng.standard_normal(int(d * SR))
    s = sweep_filter(n, f0, f1, 'bandpass', 0.8)
    t = tt(d)
    env = np.sin(np.pi * t / d) ** 2
    return s * env


def impact(size=1.0):
    t = tt(2.5)
    f = 38 + 90 * np.exp(-t * 18)
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * (1.6 / size))
    n = filt(rng.standard_normal(len(t)), 'lowpass', 3500) * np.exp(-t * 5)
    crack = filt(rng.standard_normal(len(t)), 'highpass', 3000) * np.exp(-t * 30) * 0.5
    return np.tanh((sub * 1.2 + n * 0.5 + crack) * 1.3) * size


def hit():
    t = tt(0.6)
    f = 70 + 160 * np.exp(-t * 35)
    tom = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7)
    n = filt(rng.standard_normal(len(t)), 'bandpass', [400, 4000]) * np.exp(-t * 20)
    return np.tanh((tom + n * 0.6) * 1.4)


def glass():
    t = tt(1.4)
    s = np.zeros_like(t)
    for k in range(24):
        f = rng.uniform(2500, 9000)
        d0 = rng.uniform(0, 0.25)
        tk = (t - d0).clip(0)
        s += np.sin(2 * np.pi * f * tk) * np.exp(-tk * rng.uniform(8, 25)) * (t >= d0) * 0.12
    s += filt(rng.standard_normal(len(t)), 'highpass', 4000) * np.exp(-t * 12) * 0.6
    return s


def click(f=3000, d=0.025, g=1.0):
    t = tt(d)
    n = filt(rng.standard_normal(len(t)), 'bandpass', [f * 0.6, min(f * 1.6, 20000)])
    return n * np.exp(-t * 300) * g


def ping(f, d=0.6):
    t = tt(d)
    s = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * f * 2 * t)) * np.exp(-t * 7)
    return s * (1 - np.exp(-t * 2000))


def buzz(f=110, d=0.35):
    t = tt(d)
    s = np.sign(np.sin(2 * np.pi * f * t)) + saw(f * 1.5, t)
    return filt(s, 'lowpass', 1800) * np.exp(-t * 6) * 0.35


# ------------------------------------------------------------------ arrangement
CHORDS = [  # (bass midi, pad notes, arp notes)
    (41, [53, 56, 60, 65], [65, 68, 72, 77]),   # Fm
    (37, [49, 53, 56, 61], [61, 65, 68, 73]),   # Db
    (44, [51, 56, 60, 63], [68, 72, 75, 80]),   # Ab
    (39, [51, 55, 58, 63], [63, 67, 70, 75]),   # Eb
]


def chord_at(t):
    return CHORDS[int(t // 2) % 4]


def in_any(t, ranges):
    return any(a <= t < b for a, b in ranges)


KICK = [(6, 14), (18, 50)]
KICK_HALF = [(50, 54)]
SNARE = [(6, 13.5), (18, 25.5), (26, 35.5), (36, 43.5), (44, 50)]
HATS = [(4, 14), (18, 54)]
HATS16 = [(36, 50)]
BASS = [(6, 14), (18, 54)]
ARP = [(3, 6), (18, 54), (60, 64)]

kicks = []
steps = np.arange(0, DUR, BEAT / 4)  # 16ths
for i, t in enumerate(steps):
    st = i % 16  # position in bar (2 bars of 8 16ths? -> 16 per 2s bar? no: 4 beats/bar → 16 16ths)
    beat_pos = i % 4
    if beat_pos == 0 and (in_any(t, KICK) or (in_any(t, KICK_HALF) and (i // 4) % 2 == 0)):
        place(dry, t, kick(), 0.95)
        kicks.append(t)
    if beat_pos == 0 and (i // 4) % 2 == 1 and in_any(t, SNARE):
        place(dry, t, clap(), 0.55)
        place(send, t, clap(), 0.25)
    if beat_pos == 2 and in_any(t, HATS):
        place(dry, t, hat(open_=(i // 4) % 4 == 3), 0.32, pan=0.25)
    elif in_any(t, HATS16) and beat_pos in (1, 3):
        place(dry, t, hat(), 0.16, pan=-0.3)

# bass: 8th-notes, octave jump on offbeats
for i, t in enumerate(np.arange(0, DUR, BEAT / 2)):
    if not in_any(t, BASS):
        continue
    b = chord_at(t)[0]
    m = b + (12 if i % 2 else 0)
    place(pump, t, bass_note(mtof(m), BEAT / 2 * 0.95), 0.42)

# arp: 16ths up-down through the chord, ping-pong delay into the send
pattern = [0, 1, 2, 3, 2, 1, 2, 3]
for i, t in enumerate(steps):
    if not in_any(t, ARP):
        continue
    notes = chord_at(t)[2]
    m = notes[pattern[i % 8]] + (12 if (i // 32) % 2 and i % 8 == 3 else 0)
    g = 0.11 if t < 6 else 0.14
    pan = -0.45 if i % 2 else 0.45
    bright = 1800 + 3500 * (0.5 + 0.5 * np.sin(t * 0.7))
    p = pluck(mtof(m), 0.25, bright)
    place(pump, t, p, g, pan)
    place(send, t, p, g * 0.6, -pan)
    place(send, t + 0.375, p, g * 0.35, pan)

# pad: one chord per bar, whole track
for bar in range(int(DUR // 2)):
    t = bar * 2.0
    notes = chord_at(t)[1]
    loud = 1.5 if in_any(t, [(0, 6), (14, 18), (54, 66)]) else 1.0
    cut = 900 if t < 3 else 1600
    p = pad_chord(notes, 2.6, cut)
    place(pump, t - 0.05, p, loud)
    place(send, t - 0.05, p, loud * 0.5)

# low drone through the intro & breakdowns
for a, b in [(0, 6.5), (14, 18.3), (54, 60.3)]:
    t = tt(b - a)
    dr = (np.sin(2 * np.pi * mtof(29) * t) + 0.5 * saw(mtof(41), t)) * 0.18
    dr = filt(dr, 'lowpass', 300) * np.clip(t / 1.0, 0, 1) * np.clip((b - a - t) / 0.4, 0, 1)
    place(dry, a, dr, 1.0)

# ------------------------------------------------------------------ SFX cues
# intro: build + logo impact
place(dry, 0.0, riser(3.0, 150, 7000), 0.55)
place(send, 0.0, riser(3.0, 150, 7000), 0.3)
place(dry, 3.0, impact(1.3), 0.9)
place(send, 3.0, impact(1.0), 0.5)
place(send, 3.0, glass(), 0.25)
for k, t in enumerate([4.0, 4.5, 5.0]):
    place(dry, t, click(5000, 0.04, 0.5), 0.6, pan=0.3 - 0.3 * k)

# transitions
for tr in [6, 14, 18, 26, 36, 44, 50, 54]:
    place(dry, tr - 0.45, whoosh(0.9, 300, 7000), 0.42, pan=-0.2)
    place(send, tr - 0.45, whoosh(0.9, 300, 7000), 0.2)
    if tr not in (14, 54):
        place(dry, tr, hit(), 0.35)
for a, b in [(13.2, 14), (17.0, 18), (25.2, 26), (35.0, 36), (43.2, 44), (57.6, 60)]:
    place(dry, a, riser(b - a, 300, 8000), 0.32 if b != 60 else 0.5)

# S2 word slams + stamp
for t in [7.0, 8.5, 10.0]:
    place(dry, t, hit(), 0.6)
    place(send, t, hit(), 0.3)
place(dry, 12.4, impact(0.6), 0.55)
place(dry, 12.4, clap(), 0.4)
# S3 checkbox
place(dry, 14.4, whoosh(0.5, 800, 4000), 0.25)
place(dry, 15.0, ping(mtof(84), 0.5), 0.25)
place(send, 15.0, ping(mtof(84), 0.5), 0.2)
for k in range(5):
    place(dry, 16.0 + k * 0.05, click(2500, 0.03, 1), 0.5, pan=rng.uniform(-.5, .5))
place(dry, 16.3, impact(1.0), 0.8)
place(dry, 16.3, glass(), 0.7)
place(send, 16.3, glass(), 0.4)
# S4 split-flap board + delay meter
for t in np.arange(19.3, 21.6, 0.028):
    place(dry, t + rng.uniform(0, 0.015), click(rng.uniform(1800, 4200), 0.02, 1), 0.18, pan=rng.uniform(-.6, .6))
for t in np.arange(21.6, 24.6, 0.125):
    place(dry, t, click(6000, 0.02, 1), 0.12)
cross = 18 + 3.6 + 3.0 * 0.7578
for k in range(3):
    place(dry, cross + k * 0.16, ping(mtof(88), 0.3), 0.2)
place(send, cross, ping(mtof(88), 0.6), 0.2)
# S5 GenLayer reveal, pipeline, typing
place(dry, 26.5, impact(0.9), 0.7)
place(send, 26.5, impact(0.8), 0.4)
for k, t in enumerate([28.8, 29.15, 29.5, 29.85]):
    place(dry, t, ping(mtof(77 + [0, 3, 7, 12][k]), 0.4), 0.18)
code = [
    '# illustrative · an Intelligent Contract in Python',
    'class FlightDelayCover(gl.Contract):',
    '    @gl.public.write',
    '    def resolve_claim(self, flight: str):',
    '        page = gl.nondet.web.render(status_url(flight))',
    '        verdict = gl.nondet.exec_prompt(',
    '            f"Was {flight} delayed > 3h? Evidence: {page}")',
    '        if "YES" in verdict: self.pay(self.holder)',
]
starts = np.cumsum([0] + [len(c) for c in code])
total = starts[-1]
for t in np.arange(26 + 4.7, 26 + 4.7 + total / 95, 1 / 24):
    place(dry, t + rng.uniform(0, 0.02), click(rng.uniform(2500, 5000), 0.018, 1), 0.13, pan=rng.uniform(-.3, .3))
ends = [starts[4] + len(code[4]), starts[6] + len(code[6]), starts[7] + 25, total]
for k, e in enumerate(ends):
    t = 26 + 4.7 + e / 95
    place(dry, t, ping(mtof(84 + [0, 3, 7, 12][k]), 0.5), 0.22)
    place(send, t, ping(mtof(84 + [0, 3, 7, 12][k]), 0.5), 0.2)
for k, m in enumerate([77, 81, 84, 89]):
    place(dry, 34.5 + k * 0.06, ping(mtof(m), 0.9), 0.17)
    place(send, 34.5 + k * 0.06, ping(mtof(m), 0.9), 0.15)
# S6 validators
inner = [1, 1, 0, 1, 0]
outer = [1, 1, 1, 0, 1, 1]
place(dry, 36.4, ping(mtof(65), 0.8), 0.25)
for i in range(5):
    place(dry, 36.9 + i * .08, click(3000, 0.03, 1), 0.2)
for i, v in enumerate(inner):
    t = 38.6 + i * .18
    place(dry, t, ping(mtof(84 + i * 2), 0.4) if v else buzz(), 0.25 if v else 0.5, pan=rng.uniform(-.5, .5))
for i in range(6):
    place(dry, 40.0 + i * .08, click(3000, 0.03, 1), 0.2)
for i, v in enumerate(outer):
    t = 41.2 + i * .12
    place(dry, t, ping(mtof(86 + i * 2), 0.4) if v else buzz(), 0.25 if v else 0.5, pan=rng.uniform(-.5, .5))
place(dry, 42.0, impact(1.0), 0.8)
place(send, 42.0, impact(0.8), 0.4)
for m in [65, 68, 72, 77]:
    place(send, 42.0, ping(mtof(m), 1.5), 0.15)
# S7 cards
for k, t in enumerate([44.5, 44.75, 45.0]):
    place(dry, t, whoosh(0.4, 1000, 6000), 0.3, pan=-0.6 + 0.6 * k)
# S8 pills
for k in range(4):
    place(dry, 50.35 + k * .22, click(1500, 0.05, 1), 0.35, pan=-0.4 if k % 2 == 0 else 0.4)
    place(dry, 50.35 + k * .22, ping(mtof(72 + k * 3), 0.3), 0.1)
# S9 the big question
place(dry, 55.8, hit(), 0.7)
place(send, 55.8, hit(), 0.35)
t = tt(0.35)
gl_noise = filt(rng.standard_normal(len(t)), 'bandpass', [600, 6000]) * (np.sign(np.sin(2 * np.pi * 23 * t)) > 0) * 0.6
place(dry, 56.75, gl_noise, 0.5)
place(dry, 57.2, impact(1.2), 0.9)
place(send, 57.2, impact(1.0), 0.5)
# S10 outro
place(dry, 60.0, impact(1.4), 1.0)
place(send, 60.0, impact(1.2), 0.6)
place(send, 60.0, glass(), 0.3)
for k, m in enumerate([65, 72, 77, 80, 84]):
    place(send, 60.7 + k * 0.05, ping(mtof(m), 2.0), 0.12)

# ------------------------------------------------------------------ mix
# sidechain pump from kicks
sc = np.ones(N)
tv = np.arange(N) / SR
for k in kicks:
    i0 = int(k * SR)
    i1 = min(N, i0 + int(0.4 * SR))
    sc[i0:i1] = np.minimum(sc[i0:i1], 1 - 0.6 * np.exp(-(tv[i0:i1] - k) / 0.09))
pump *= sc[:, None]

# reverb: stereo decaying-noise impulse response
ir_len = int(2.4 * SR)
ti = np.arange(ir_len) / SR
ir = rng.standard_normal((ir_len, 2)) * np.exp(-ti * 2.6)[:, None]
ir = filt(ir, 'lowpass', 5000)
ir /= np.sqrt((ir ** 2).sum(0))
wet = np.stack([signal.oaconvolve(send[:, c] + pump[:, c] * 0.15, ir[:, c])[:N] for c in range(2)], 1)

mix = dry + pump + wet * 0.55
mix = filt(mix, 'highpass', 28)
# final fade
fade = np.clip((DUR - tv) / 1.0, 0, 1) * np.clip(tv / 0.05, 0, 1)
mix *= fade[:, None]
mix = np.tanh(mix * 1.1)
mix *= 0.89 / np.max(np.abs(mix))
wavfile.write(sys.argv[1] if len(sys.argv) > 1 else 'music.wav', SR, (mix * 32767).astype(np.int16))
print('ok', mix.shape)

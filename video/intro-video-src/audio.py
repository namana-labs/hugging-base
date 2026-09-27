import numpy as np
from scipy.signal import butter, sosfilt, fftconvolve
from scipy.io import wavfile
SR = 48000
DUR = 46.5
N = int(SR * (DUR + 1.5))
rng = np.random.default_rng(7)
music = np.zeros((N, 2)); sfx = np.zeros((N, 2)); send = np.zeros((N, 2))

def at(t): return int(t * SR)
def env_exp(n, dec): return np.exp(-np.arange(n) / SR / dec)
def add(buf, t, sig, gain=1.0, pan=0.0):
    i = at(t)
    if i >= N: return
    sig = sig[: N - i]
    l = gain * np.sqrt(0.5 * (1 - pan)); r = gain * np.sqrt(0.5 * (1 + pan))
    if sig.ndim == 1:
        buf[i:i + len(sig), 0] += sig * l; buf[i:i + len(sig), 1] += sig * r
    else:
        buf[i:i + len(sig)] += sig * gain
def lp(x, f, o=2): return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)
def hp(x, f, o=2): return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)
def bp(x, f1, f2, o=2): return sosfilt(butter(o, [f1, f2], 'band', fs=SR, output='sos'), x)
def midi(n): return 440 * 2 ** ((n - 69) / 12)

# ---------- instruments ----------
def kick(f0=130, f1=42, dec=0.32, dur=0.6):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f1 + (f0 - f1) * np.exp(-tt / 0.045)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * np.exp(-tt / dec)
    click = hp(rng.standard_normal(n), 2000) * np.exp(-tt / 0.004) * 0.25
    return np.tanh((s + click) * 1.6)
def heartbeat():
    lub = kick(95, 38, 0.18, 0.5); dub = kick(80, 36, 0.14, 0.45) * 0.6
    out = np.zeros(int(0.8 * SR)); out[:len(lub)] += lub; o = int(0.19 * SR); out[o:o + len(dub)] += dub
    return lp(out, 260)
def hat(dec=0.035):
    n = int(0.12 * SR); return hp(rng.standard_normal(n), 7500) * env_exp(n, dec) * 0.5
def whoosh(dur=0.7, f0=300, f1=4000, peak=0.6, rev=False):
    n = int(dur * SR); x = rng.standard_normal(n); out = np.zeros(n); blk = 480
    for i in range(0, n, blk):
        u = i / n; u = 1 - u if rev else u
        fc = f0 * (f1 / f0) ** u
        seg = x[i:i + blk]
        out[i:i + blk] = bp(seg, max(60, fc * 0.6), min(20000, fc * 1.6), 1) if len(seg) > 12 else 0
    tt = np.linspace(0, 1, n); e = np.where(tt < peak, (tt / peak) ** 2, ((1 - tt) / (1 - peak)) ** 1.5)
    return out * e * 1.4
def impact(big=1.0):
    n = int(3.0 * SR); tt = np.arange(n) / SR
    boom = np.sin(2 * np.pi * np.cumsum(32 + 60 * np.exp(-tt / 0.08)) / SR) * np.exp(-tt / 0.9)
    k = np.zeros(n); kk = kick(160, 40, 0.4, 1.0); k[:len(kk)] = kk
    nz = lp(rng.standard_normal(n), 3500) * np.exp(-tt / 0.18) * 0.6
    return np.tanh((boom * 0.9 + k + nz) * 1.3 * big) * 0.9
def shatter():
    n = int(1.2 * SR); out = np.zeros(n)
    for j in range(40):
        o = int(rng.uniform(0, 0.5) * SR); f = rng.uniform(2500, 9000); d = rng.uniform(0.02, 0.12)
        m = int(0.3 * SR); tt = np.arange(m) / SR
        s = np.sin(2 * np.pi * f * tt) * np.exp(-tt / d) * rng.uniform(0.1, 0.35)
        out[o:o + m] += s[: n - o]
    return out + hp(rng.standard_normal(n), 4000) * env_exp(n, 0.12) * 0.3
def tick(f=2600, dec=0.012, amp=0.35):
    n = int(0.06 * SR); tt = np.arange(n) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt / dec) * amp
def clink(f=3300):
    n = int(0.5 * SR); tt = np.arange(n) / SR
    return (np.sin(2 * np.pi * f * tt) + 0.6 * np.sin(2 * np.pi * f * 1.47 * tt) + 0.3 * np.sin(2 * np.pi * f * 2.3 * tt)) * np.exp(-tt / 0.09) * 0.22
def bell(f, dec=1.4, amp=0.35):
    n = int(dec * 3 * SR); tt = np.arange(n) / SR
    s = sum(a * np.sin(2 * np.pi * f * r * tt) * np.exp(-tt / (dec / r ** 0.5)) for r, a in [(1, 1), (2.0, 0.4), (2.76, 0.35), (5.4, 0.15)])
    return s * amp * (1 - np.exp(-tt / 0.002))
def pluck(f, dec=0.22, amp=0.25):
    n = int(0.6 * SR); tt = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * f * tt)) * 0.3 + np.sin(2 * np.pi * f * tt) + 0.3 * np.sin(4 * np.pi * f * tt)
    return lp(s * np.exp(-tt / dec), 3200) * amp
def riser(dur=1.0, f0=200, f1=1600):
    n = int(dur * SR); tt = np.arange(n) / SR
    f = f0 * (f1 / f0) ** (tt / dur); s = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.3
    return (s + whoosh(dur, 400, 8000, 0.98)) * (tt / dur) ** 2
def buzz():
    n = int(0.35 * SR); tt = np.arange(n) / SR
    s = np.sign(np.sin(2 * np.pi * 110 * tt)) + np.sign(np.sin(2 * np.pi * 116 * tt))
    return lp(s, 1200) * np.exp(-tt / 0.15) * 0.18
def crack():
    n = int(0.25 * SR); tt = np.arange(n) / SR
    return bp(rng.standard_normal(n), 800, 5000) * np.exp(-tt / 0.03) * 0.7

# ---------- music bed: 120 BPM, A minor ----------
BPM = 120; B = 60 / BPM
prog = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [55, 60, 64]), (55, [55, 59, 62])]  # Am F C G (roots in bass octave below)
def chord_at(t):
    i = int(t // (8 * B)) % 4; return prog[i]
def pad_note(f, dur):
    n = int(dur * SR); tt = np.arange(n) / SR
    s = sum(np.sin(2 * np.pi * f * d * tt + p) for d, p in [(1, 0), (1.004, 1), (0.996, 2), (2.0, 0.5)])
    a = np.minimum(1, tt / 0.8) * np.minimum(1, (dur - tt) / 0.8)
    return lp(s * a, 1400) * 0.05

# sections: (start, end, layers)
def in_range(t, a, b): return a <= t < b
# pad throughout (from 1.5), per 4 s chord
t = 1.5 - 0.0
for c in range(0, 12):
    t0 = c * 8 * B
    if t0 > 46: break
    root, notes = prog[c % 4]
    for nt in notes:
        add(music, max(t0, 1.2), pad_note(midi(nt), 8 * B + 0.8), 1.0, pan=(nt % 3 - 1) * 0.4)
# sub bass eighths 2.0–24.7 and 27.6–40.4
step = B / 2
for k in range(int(47 / step)):
    tt_ = k * step
    if not (in_range(tt_, 2.0, 24.6) or in_range(tt_, 27.5, 40.4)): continue
    root, _ = chord_at(tt_)
    n = int(step * SR); x = np.arange(n) / SR
    s = np.sin(2 * np.pi * midi(root - 24) * x) * np.exp(-x / 0.18) * (1 - np.exp(-x / 0.004))
    add(music, tt_, s, 0.32 if tt_ < 11.5 else 0.38)
# hats (8ths off-beat) from 7.5
for k in range(int(47 / step)):
    tt_ = k * step
    if in_range(tt_, 7.5, 24.6) or in_range(tt_, 27.5, 40.4):
        add(music, tt_ + step / 2, hat(), 0.18 if tt_ < 15.5 else 0.24, pan=0.3)
        if in_range(tt_, 15.5, 24.6) or in_range(tt_, 34.5, 40.4): add(music, tt_ + step * 0.75, hat(0.02), 0.08, pan=-0.3)
# kicks on quarters (four-on-floor) 15.5–24.6, 27.5–40.4 ; half-time 7.5–15.5
for k in range(int(47 / B)):
    tt_ = k * B
    if in_range(tt_, 15.5, 24.6) or in_range(tt_, 29.0, 40.4): add(music, tt_, kick(), 0.5)
    elif in_range(tt_, 7.5, 15.5) and k % 2 == 0: add(music, tt_, kick(), 0.42)
# arpeggio 16ths 11.5–24.6 and 29–40.4
s16 = B / 4
for k in range(int(47 / s16)):
    tt_ = k * s16
    if not (in_range(tt_, 11.5, 24.6) or in_range(tt_, 29.0, 40.4)): continue
    root, notes = chord_at(tt_)
    pat = [0, 1, 2, 1, 2, 0, 1, 2]; nt = notes[pat[k % 8]] + (12 if (k // 8) % 2 else 12)
    add(music, tt_, pluck(midi(nt)), 0.16 if tt_ < 15.5 else 0.2, pan=0.35 * np.sin(k * 0.7)); add(send, tt_, pluck(midi(nt)), 0.08)
# clap/snare on 2 & 4 in high-energy parts
def snare():
    n = int(0.3 * SR); x = np.arange(n) / SR
    return (bp(rng.standard_normal(n), 900, 6000) * np.exp(-x / 0.09) * 0.6 + np.sin(2 * np.pi * 190 * x) * np.exp(-x / 0.05) * 0.4)
for k in range(int(47 / B)):
    tt_ = k * B
    if k % 2 == 1 and (in_range(tt_, 15.5, 24.6) or in_range(tt_, 31.0, 40.4)):
        add(music, tt_, snare(), 0.26); add(send, tt_, snare(), 0.12)

# end card: pad chord Am add9 held, heartbeat
for nt in [45, 57, 60, 64, 71]:
    add(music, 40.5, pad_note(midi(nt), 6.5), 1.3)

# ---------- SFX ----------
hb = heartbeat()
add(sfx, 0.17, hb, 0.9); add(sfx, 0.60, hb, 0.9)
add(sfx, 1.15, whoosh(0.7, 200, 5000, 0.8), 0.35)
for i in range(12):  # record steps: ticks as line climbs
    yr = [2000, 2003, 2005, 2009, 2010, 2011, 2015, 2016, 2018, 2019, 2022, 2023][i]
    add(sfx, 2.0 + (yr - 2000) / 23 * 1.9, tick(1800 + i * 90), 0.5, pan=-0.6 + i * 0.1)
add(sfx, 3.35, riser(1.0, 180, 1400), 0.5)
add(sfx, 4.35, impact(1.1), 1.0); add(send, 4.35, impact(0.8), 0.4)
add(sfx, 4.35, shatter(), 0.5)
add(sfx, 5.0, whoosh(0.6, 3000, 300, 0.3), 0.35, pan=-0.4)
for i in range(5):
    add(sfx, 5.7 + i * 0.1, whoosh(0.35, 800, 3000, 0.5), 0.18, pan=-0.6 + i * 0.3)  # doors
    for k in range(4): add(sfx, 5.95 + i * 0.1 + k * 0.08, tick(1200 + k * 300 + i * 60, 0.02, 0.25), 0.5, pan=-0.6 + i * 0.3)
    add(sfx, 6.25 + i * 0.1, tick(880 * 2, 0.05, 0.3), 0.4, pan=-0.6 + i * 0.3)
add(sfx, 6.65, whoosh(1.0, 2500, 200, 0.4), 0.35)
for k in range(24): add(sfx, 6.9 + k * 0.025 + rng.uniform(0, 0.02), tick(rng.uniform(2200, 4200), 0.01, 0.2), 0.6, pan=rng.uniform(-0.8, 0.8))
add(sfx, 7.25, whoosh(0.6, 400, 7000, 0.55), 0.5, pan=-0.3)
add(sfx, 9.0, whoosh(0.3, 3000, 400, 0.8), 0.3)
add(sfx, 9.25, kick(110, 45, 0.3), 0.6); add(sfx, 9.25, bell(midi(81), 0.8, 0.3), 0.5); add(send, 9.25, bell(midi(81), 0.8, 0.3), 0.3)
for k, tt_ in enumerate(np.linspace(11.75, 12.35, 6)): add(sfx, tt_, crack(), 0.5, pan=-0.7 + k * 0.28)
add(sfx, 12.1, impact(0.6), 0.55)
for k in range(18): add(sfx, 12.45 + rng.uniform(0, 0.5) + 0.3, tick(rng.uniform(1500, 3000), 0.015, 0.25), 0.5, pan=rng.uniform(-0.8, 0.8))
add(sfx, 15.2, whoosh(0.6, 400, 7000, 0.55), 0.5, pan=0.3)
add(sfx, 15.9, whoosh(0.4, 600, 2000, 0.5), 0.2)
for k in range(24): add(sfx, 17.3 + k * 0.095, tick(2400 + (k % 2) * 400, 0.01, 0.22), 0.45, pan=(-0.5 if k % 2 else 0.5))
add(sfx, 19.6, bell(midi(88), 0.6, 0.25), 0.4, pan=-0.5)
add(sfx, 20.6, buzz(), 0.8, pan=0.5)
for k in range(26):
    t0 = 21.6 + k * 0.07 + 0.7
    add(sfx, t0, clink(rng.uniform(2800, 4200)), 0.55, pan=0.2 + (k % 13) * 0.05)
add(sfx, 21.0, whoosh(0.5, 300, 1500, 0.6), 0.2, pan=0.5)
add(sfx, 23.9, riser(0.9, 150, 1800), 0.7)
add(sfx, 24.75, whoosh(0.6, 200, 9000, 0.9), 0.4)
add(sfx, 25.3, impact(1.3), 1.0); add(send, 25.3, impact(1.0), 0.5)
for k in range(12):  # heartbeat 72 bpm from 25.9 to ~34
    tb = 25.9 + k * (60 / 72)
    if tb < 34.5: add(sfx, tb, hb, 0.75 if tb < 28 else 0.55)
add(sfx, 26.95, whoosh(0.8, 5000, 200, 0.3), 0.35)
# grid grows: rising shimmer
n = int(3.2 * SR); x = np.arange(n) / SR
shim = sum(np.sin(2 * np.pi * midi(69 + iv) * (1 + x / 3.2) * x) for iv in [0, 7, 12, 19]) * (x / 3.2) * np.exp(-np.maximum(0, x - 3.0) / 0.1) * 0.05
add(sfx, 27.5, shim, 0.8); add(send, 27.5, shim, 0.4)
for k in range(30): add(sfx, 27.6 + k * 0.1 + rng.uniform(0, 0.05), tick(rng.uniform(3000, 5000), 0.008, 0.15), 0.4, pan=rng.uniform(-0.9, 0.9))
add(sfx, 31.4, whoosh(1.7, 200, 3500, 0.85), 0.4)
for k in range(3): add(sfx, 32.95 + k * 0.33, bell(midi(84), 0.25, 0.25), 0.4, pan=0.3)
add(sfx, 34.3, whoosh(1.3, 3500, 250, 0.3), 0.35)
scale = [69, 71, 72, 74, 76, 77, 79, 81, 83, 84]
for i in range(10):
    add(sfx, 35.9 + i * 0.16, pluck(midi(scale[i] + 12), 0.15, 0.35), 0.6, pan=0.5 - i * 0.05); add(send, 35.9 + i * 0.16, pluck(midi(scale[i] + 12), 0.15, 0.3), 0.3)
for nt in [81, 88, 93]: add(sfx, 37.5, bell(midi(nt), 1.6, 0.18), 0.6); add(send, 37.5, bell(midi(nt), 1.6, 0.18), 0.35)
add(sfx, 40.4, whoosh(0.7, 200, 6000, 0.7), 0.45)
add(sfx, 40.95, impact(0.7), 0.6); add(send, 40.95, impact(0.6), 0.4)
# ECG on end card: spikes where the drawn line crosses them
import math
def eo(u): return 1 if u >= 1 else 1 - 2 ** (-10 * u)
x0, x1 = 240, 1580
for ph in [1.12, 2.12, 3.12]:
    target = (ph - 0.35) / 3
    if target > 1: continue
    u = -math.log2(1 - target) / 10 if target < 1 else 1
    add(sfx, 41.6 + u * 1.4, hb, 0.8)
add(sfx, 42.8, bell(midi(76), 2.0, 0.25), 0.6); add(sfx, 42.8, bell(midi(81), 2.0, 0.2), 0.5); add(send, 42.8, bell(midi(81), 2.0, 0.25), 0.4)
for k in range(4):
    tb = 43.3 + k * (60 / 72)
    add(sfx, tb, hb, 0.55 * (1 - k * 0.2))

# ---------- reverb ----------
irn = int(2.2 * SR); ir_t = np.arange(irn) / SR
ir = np.stack([rng.standard_normal(irn), rng.standard_normal(irn)], 1) * np.exp(-ir_t / 0.55)[:, None]
ir[:, 0] = lp(ir[:, 0], 5000); ir[:, 1] = lp(ir[:, 1], 5000)
rev = np.stack([fftconvolve(send[:, c] + 0.12 * music[:, c], ir[:, c])[:N] for c in range(2)], 1) * 0.08

# duck music under big impacts
duck = np.ones(N)
for tt_, d in [(4.35, 0.8), (25.3, 1.0), (12.1, 0.5), (40.95, 0.6)]:
    i = at(tt_); m = int(1.2 * SR); duck[i:i + m] = np.minimum(duck[i:i + m], 1 - d * 0.7 * np.exp(-np.arange(m) / SR / 0.4))
mix_ = music * duck[:, None] * 0.9 + sfx * 0.85 + rev
# fade in/out
mix_[:at(0.05)] *= np.linspace(0, 1, at(0.05))[:, None]
fo0 = at(43.3); fo1 = at(44.3)
mix_[fo0:fo1] *= np.linspace(1, 0, fo1 - fo0)[:, None] ** 1.5; mix_[fo1:] = 0
mix_ = hp(mix_.T, 25).T
mix_ = np.tanh(mix_ * 1.2) / np.tanh(1.2)
mix_ = mix_ / np.max(np.abs(mix_)) * 0.89
a = mix_[:at(7.2)].copy(); b = mix_[at(15.2):at(44.3)].copy()
xf = int(0.02 * SR); r = np.linspace(0, 1, xf)[:, None]
b[:xf] = b[:xf] * r + mix_[at(7.2):at(7.2) + xf] * (1 - r)
out = np.concatenate([a, b])
wavfile.write('score.wav', SR, (out * 32767).astype(np.int16)); print('len', len(out) / SR)
print('ok', np.max(np.abs(mix_)))

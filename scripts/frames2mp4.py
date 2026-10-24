"""PNG frames -> mp4.  python frames2mp4.py <out.mp4> <fps> <hold_frames> <fade_frames> img1.png img2.png ...
Each image is held, then cross-faded into the next (snapshot sequences); hold 1 / fade 0 = plain frame sequence."""
import sys
import numpy as np, imageio.v2 as io
out, fps, hold, fade = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
imgs = [io.imread(p)[:, :, :3].astype(float) for p in sys.argv[5:]]
frames = []
for i, im in enumerate(imgs):
    frames += [im] * hold
    if i + 1 < len(imgs):
        frames += [(1 - w) * im + w * imgs[i + 1] for w in np.linspace(0, 1, fade + 2)[1:-1]]
h, w = frames[0].shape[:2]
frames = [f[: h - h % 2, : w - w % 2].astype(np.uint8) for f in frames]
io.mimwrite(out, frames, fps=fps, codec="libx264", quality=6, pixelformat="yuv420p", macro_block_size=1)
print("wrote", out, len(frames), "frames")

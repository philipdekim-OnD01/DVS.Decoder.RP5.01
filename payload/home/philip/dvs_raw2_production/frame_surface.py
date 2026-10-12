"""Sparse time-surface rendering: valid events are processed once per input frame."""
import numpy as np

W, H = 960, 720


class FrameSurface:
    def __init__(self):
        self.timestamps = np.full(W * H, -1e9, dtype=np.float64)
        self.seen = self.timestamps.copy()
        self.polarity = np.zeros(W * H, dtype=np.uint8)
        self.hot_counts = np.zeros(W * H, dtype=np.uint16)
        self.hot_mask = np.zeros(W * H, dtype=bool)
        self.hot_start = None
        self.raw_active = np.empty(0, dtype=np.intp)

    def clear(self):
        self.timestamps.fill(-1e9); self.seen.fill(-1e9)
        self.raw_active = np.empty(0, dtype=np.intp)

    def accept(self, raw, now, opt):
        raw = raw.reshape(-1)
        indices = np.flatnonzero((raw == 255) | (raw == 64))
        if self.hot_start is None: self.hot_start = now
        self.hot_counts[indices] += 1
        elapsed = now - self.hot_start
        if elapsed >= 1:
            self.hot_mask = self.hot_counts > opt['Hot pixel active frames/s'] * elapsed
            self.hot_counts.fill(0); self.hot_start = now
        if opt['Hot pixel filter']: indices = indices[~self.hot_mask[indices]]
        if opt['Polarity'] == 'ON only': indices = indices[raw[indices] == 255]
        elif opt['Polarity'] == 'OFF only': indices = indices[raw[indices] == 64]
        x, y = indices % W, indices // W
        x0, x1, y0, y1 = opt['roi']; sub = int(opt['Sub-sampling'])
        indices = indices[(x >= x0) & (x <= x1) & (y >= y0) & (y <= y1) & (x % sub == 0) & (y % sub == 0)]
        self.seen[indices] = now
        if opt['Noise filter'] and indices.size:
            x, y = indices % W, indices // W
            neighbor = np.zeros(indices.size, dtype=bool)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if not dx and not dy: continue
                    valid = (x+dx >= 0) & (x+dx < W) & (y+dy >= 0) & (y+dy < H)
                    position = indices[valid] + dy * W + dx
                    neighbor[valid] |= self.seen[position] >= now - .035
            indices = indices[neighbor]
        self.timestamps[indices] = now
        self.polarity[indices] = raw[indices] == 64
        self.raw_active = indices

    def render(self, now, opt):
        mode = opt['Display mode']
        if mode == 'Raw frame':
            indices = self.raw_active
        else:
            duration = opt['Time Surface τ (ms)']*3 if mode == 'Time Surface' else opt[
                'Event lifetime (ms)' if mode == 'Event Dot' else 'Accumulation (ms)']
            indices = np.flatnonzero(self.timestamps >= now-duration/1000)
        x, y = indices % W, indices // W
        x0, x1, y0, y1 = opt['roi']
        indices = indices[(x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)]
        if opt['Polarity'] == 'ON only': indices = indices[self.polarity[indices] == 0]
        elif opt['Polarity'] == 'OFF only': indices = indices[self.polarity[indices] == 1]
        colors = opt['colors']
        rgb = np.empty((H, W, 3), dtype=np.uint8); rgb[:] = colors['BG']
        size = max(opt['Point size'], 3 if opt['Dilation'] else 1)
        age = (now - self.timestamps[indices])*1000
        weight = np.exp(-age / opt['Time Surface τ (ms)']) if mode == 'Time Surface' else np.ones(indices.size)
        levels = np.empty((indices.size, 3), dtype=np.uint8)
        for pol, name in [(0, 'ON'), (1, 'OFF')]:
            selected = self.polarity[indices] == pol
            levels[selected] = np.clip(colors['BG'] + (colors[name]-colors['BG'])*weight[selected, None]*
                opt['Contrast / gain (%)']/100, 0, 255)
        x, y = indices % W, indices // W
        # Dilation uses a snapshot and never changes stored polarity/timestamps.
        for dy in range(size):
            for dx in range(size):
                valid = (x+dx <= x1) & (y+dy <= y1)
                rgb[y[valid]+dy, x[valid]+dx] = levels[valid]
        if opt['Flip X']: rgb = rgb[:, ::-1]
        if opt['Flip Y']: rgb = rgb[::-1]
        return np.ascontiguousarray(rgb)

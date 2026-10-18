"""与界面无关的扫雷规则，可独立测试。"""
from collections import deque
import random


class Game:
    def __init__(self, rows=9, cols=9, mine_count=10, rng=None):
        if rows < 1 or cols < 1 or not 0 <= mine_count <= rows * cols - min(rows, 3) * min(cols, 3):
            raise ValueError("雷数必须为首次点击的安全区域留出空间")
        self.rows, self.cols, self.mine_count = rows, cols, mine_count
        self.rng = rng if rng is not None else random.Random()
        self.mines = set()
        self.flags = set()
        self.opened = set()
        self.counts = {}
        self.started = False
        self.state = "ready"
        self.hit = None

    @property
    def finished(self):
        return self.state in {"won", "lost"}

    def neighbors(self, pos):
        row, col = pos
        for r in range(max(0, row - 1), min(self.rows, row + 2)):
            for c in range(max(0, col - 1), min(self.cols, col + 2)):
                if (r, c) != pos:
                    yield r, c

    def valid(self, pos):
        return 0 <= pos[0] < self.rows and 0 <= pos[1] < self.cols

    def toggle_flag(self, pos):
        if not self.valid(pos) or self.finished or pos in self.opened:
            return False
        if pos in self.flags:
            self.flags.remove(pos)
        elif len(self.flags) < self.mine_count:
            self.flags.add(pos)
        else:
            return False
        return True

    def reveal(self, pos):
        """返回本次翻开的格子；快速展开先判雷，避免处理顺序影响胜负。"""
        if not self.valid(pos) or self.finished or pos in self.flags:
            return set()
        if not self.started:
            excluded = {pos, *self.neighbors(pos)}
            candidates = [(r, c) for r in range(self.rows) for c in range(self.cols)
                          if (r, c) not in excluded]
            self.mines = set(self.rng.sample(candidates, self.mine_count))
            self.counts = {(r, c): sum(n in self.mines for n in self.neighbors((r, c)))
                           for r in range(self.rows) for c in range(self.cols)}
            self.started = True
            self.state = "playing"
        targets = {pos}
        if pos in self.opened:
            adjacent = set(self.neighbors(pos))
            if not self.counts[pos] or sum(p in self.flags for p in adjacent) != self.counts[pos]:
                return set()
            targets = adjacent - self.flags - self.opened
        hits = targets & self.mines
        if hits:
            self.hit = min(hits)
            self.state = "lost"
            return set()
        changed = set()
        queue = deque(targets)
        queued = set(targets)
        while queue:
            current = queue.popleft()
            if current in self.opened or current in self.flags:
                continue
            self.opened.add(current)
            changed.add(current)
            if self.counts[current] == 0:
                for neighbor in self.neighbors(current):
                    if neighbor not in queued and neighbor not in self.opened and neighbor not in self.flags:
                        queued.add(neighbor)
                        queue.append(neighbor)
        if len(self.opened) == self.rows * self.cols - self.mine_count:
            self.state = "won"
            self.flags = self.mines.copy()
        return changed

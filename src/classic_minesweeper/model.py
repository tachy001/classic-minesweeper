"""与界面无关的扫雷规则，可独立测试。"""
from collections import deque
import random


def deduce(rows, cols, mine_count, visible, known_mines, known_safe=()):
    """只用可见数字和已推导雷，返回确定安全格、确定雷（含集合差推理）。"""
    unknown = {(r, c) for r in range(rows) for c in range(cols)} - visible.keys() - known_mines - set(known_safe)
    constraints = {}
    for (r, c), number in visible.items():
        adjacent = {(nr, nc) for nr in range(max(0, r-1), min(rows, r+2))
                    for nc in range(max(0, c-1), min(cols, c+2))} - {(r, c)}
        cells = frozenset(adjacent & unknown)
        if cells:
            constraints[cells] = number - len(adjacent & known_mines)
    if unknown:
        constraints[frozenset(unknown)] = mine_count - len(known_mines)
    safe, mines = set(), set()

    def collect(cells, count):
        if count == 0:
            safe.update(cells)
        elif count == len(cells):
            mines.update(cells)

    items = list(constraints.items())
    for cells, count in items:
        collect(cells, count)
    if not safe and not mines:
        # A 包含于 B 时，B-A 的雷数等于两组数字之差。
        for i, (a, ca) in enumerate(items):
            for b, cb in items[i+1:]:
                if len(a) < len(b) and a <= b:
                    collect(b-a, cb-ca)
                elif len(b) < len(a) and b <= a:
                    collect(a-b, ca-cb)
    if not safe and not mines and len(unknown) <= 22:
        # 小型残局穷举所有满足可见约束的布局，只接受所有布局共有的结论。
        # 约束剪枝限制搜索量；超出预算返回无结论，绝不采用未完成搜索的结果。
        cells = sorted(unknown, key=lambda p: -sum(p in group for group in constraints))
        groups = list(constraints)
        remaining = [len(group) for group in groups]
        needed = [constraints[group] for group in groups]
        membership = [[i for i, group in enumerate(groups) if p in group] for p in cells]
        all_mines, any_mines = set(cells), set()
        solutions = 0
        nodes = 0
        chosen = set()

        def search(index):
            nonlocal solutions, nodes
            nodes += 1
            if nodes > 200000:
                raise OverflowError
            if index == len(cells):
                solutions += 1
                all_mines.intersection_update(chosen)
                any_mines.update(chosen)
                return
            affected = membership[index]
            for value in (0, 1):
                for i in affected:
                    remaining[i] -= 1
                    needed[i] -= value
                if all(0 <= needed[i] <= remaining[i] for i in affected):
                    if value:
                        chosen.add(cells[index])
                    search(index + 1)
                    chosen.discard(cells[index])
                for i in affected:
                    remaining[i] += 1
                    needed[i] += value

        try:
            search(0)
        except OverflowError:
            return set(), set()
        if solutions:
            safe.update(unknown - any_mines)
            mines.update(all_mines)
    return safe, mines


def analyze(rows, cols, mine_count, visible, known_mines=()):
    """共用推理闭包：同时消去已证安全格和雷，不必实际翻开安全格。"""
    known = set(known_mines)
    safe = set()
    while True:
        next_safe, inferred = deduce(rows, cols, mine_count, visible, known, safe)
        added_safe = next_safe - safe
        added_mines = inferred - known
        safe.update(added_safe)
        known.update(added_mines)
        if not added_safe and not added_mines:
            return safe, known


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
        self.proven_mines = set()

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

    def logical_moves(self):
        """与生成验证器使用相同规则；手动旗子不作为证据。"""
        if not self.started or self.finished:
            return set(), set()
        visible = {pos: self.counts[pos] for pos in self.opened}
        safe, certain = analyze(self.rows, self.cols, self.mine_count, visible, self.proven_mines)
        self.proven_mines.update(certain)
        return safe, certain

    def auto_flag(self):
        """标记所有能推导的雷，包括集合差和剩余总雷数推理。"""
        _, certain = self.logical_moves()
        added = certain - self.flags
        # 手动错旗可能占满雷数；保持原有标记，不做部分、顺序相关的修改。
        if len(self.flags | added) > self.mine_count:
            return set()
        self.flags.update(added)
        return added

    def logic_solvable(self, first, mines, counts):
        """模拟玩家逐步获取数字；隐藏雷区只用于翻格和最后核验。"""
        visible, known = {}, set()
        pending = {first}
        target = self.rows * self.cols - self.mine_count
        while pending:
            queue = deque(pending)
            queued = set(pending)
            while queue:
                pos = queue.popleft()
                if pos in visible:
                    continue
                if pos in mines:
                    return False
                visible[pos] = counts[pos]
                if counts[pos] == 0:
                    for neighbor in self.neighbors(pos):
                        if neighbor not in visible and neighbor not in queued:
                            queue.append(neighbor)
                            queued.add(neighbor)
            if len(visible) == target:
                return True
            safe, known = analyze(self.rows, self.cols, self.mine_count, visible, known)
            pending = safe - visible.keys()
        return False

    def generate(self, first, max_attempts=1000):
        """逐个验证候选棋盘；每次失败让 GUI 有机会处理事件。"""
        excluded = {first, *self.neighbors(first)}
        candidates = [(r, c) for r in range(self.rows) for c in range(self.cols)
                      if (r, c) not in excluded]
        for _ in range(max_attempts):
            mines = set(self.rng.sample(candidates, self.mine_count))
            counts = {(r, c): 0 for r in range(self.rows) for c in range(self.cols)}
            for mine in mines:
                for neighbor in self.neighbors(mine):
                    counts[neighbor] += 1
            if self.logic_solvable(first, mines, counts):
                self.mines, self.counts = mines, counts
                self.started = True
                self.state = "playing"
                return
            yield None
        raise RuntimeError("暂未找到无猜测棋盘，请重试")

    def reveal(self, pos):
        """返回本次翻开的格子；快速展开先判雷，避免处理顺序影响胜负。"""
        if not self.valid(pos) or self.finished or pos in self.flags:
            return set()
        if not self.started:
            for _ in self.generate(pos):
                pass
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

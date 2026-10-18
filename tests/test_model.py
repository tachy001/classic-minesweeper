"""运行：python -m unittest discover -s tests。无需安装 PyQt6。"""
import random
from itertools import combinations
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from classic_minesweeper.model import Game, deduce, analyze


class GameTests(unittest.TestCase):
    def test_first_click_and_win_all_levels(self):
        for rows, cols, mines in [(9, 9, 10), (16, 16, 40), (16, 30, 99)]:
            for seed in range(10):
                game = Game(rows, cols, mines, random.Random(seed))
                pos = (seed % rows, seed % cols)
                game.reveal(pos)
                self.assertEqual(len(game.mines), mines)
                self.assertFalse(game.mines & {pos, *game.neighbors(pos)})
                self.assertFalse(game.opened & game.mines)
                for r in range(rows):
                    for c in range(cols):
                        if (r, c) not in game.mines and (r, c) not in game.opened:
                            game.reveal((r, c))
                self.assertEqual(game.state, "won")
                self.assertEqual(game.flags, game.mines)
                before = game.opened.copy()
                game.reveal(next(iter(game.mines)))
                self.assertEqual(before, game.opened)

    def test_flag_blocks_click_and_limit(self):
        game = Game(5, 5, 1)
        self.assertTrue(game.toggle_flag((0, 0)))
        self.assertFalse(game.toggle_flag((0, 1)))
        game.reveal((0, 0))
        self.assertFalse(game.started)
        self.assertTrue(game.toggle_flag((0, 0)))
        self.assertFalse(game.toggle_flag((-1, 0)))
        game.reveal((0, 0))
        self.assertFalse(game.toggle_flag((0, 0)))

    def prepared(self):
        game = Game(4, 4, 1)
        game.started = True
        game.state = "playing"
        game.mines = {(0, 0)}
        game.counts = {(r, c): sum(n in game.mines for n in game.neighbors((r, c)))
                       for r in range(4) for c in range(4)}
        game.opened = {(1, 1)}
        return game

    def test_wrong_chord_loses_atomically(self):
        game = self.prepared()
        game.toggle_flag((0, 1))
        self.assertEqual(game.reveal((1, 1)), set())
        self.assertEqual(game.state, "lost")
        self.assertEqual(game.hit, (0, 0))
        self.assertEqual(game.opened, {(1, 1)})
        self.assertFalse(game.toggle_flag((2, 2)))

    def test_correct_chord_wins(self):
        game = self.prepared()
        self.assertEqual(game.reveal((1, 1)), set())
        game.toggle_flag((0, 0))
        game.reveal((1, 1))
        self.assertEqual(game.state, "won")
        self.assertEqual(len(game.opened), 15)

    def test_direct_loss(self):
        game = self.prepared()
        game.reveal((0, 0))
        self.assertEqual(game.state, "lost")

    def test_no_guess_generation(self):
        for config in [(9, 9, 10), (16, 16, 40), (16, 30, 99)]:
            for seed in range(5):
                game = Game(*config, rng=random.Random(seed))
                first = (config[0]//2, config[1]//2)
                game.reveal(first)
                self.assertTrue(game.logic_solvable(first, game.mines, game.counts))
                self.assertEqual(len(game.mines), config[2])

    def test_ambiguous_two_choices_rejected(self):
        # 顶部两格一雷，底部两格都是 1：没有信息能区别两格。
        game = Game(2, 2, 0)
        game.mine_count = 1
        counts = {(r, c): 1 for r in range(2) for c in range(2)}
        self.assertFalse(game.logic_solvable((1, 0), {(0, 0)}, counts))
        safe, mines = deduce(2, 2, 1, {(1, 0): 1, (1, 1): 1}, set())
        self.assertFalse(safe or mines)

    def test_generation_limit_never_accepts_unverified_board(self):
        game = Game(rng=random.Random(0))
        game.logic_solvable = lambda *args: False
        with self.assertRaises(RuntimeError):
            list(game.generate((0, 0), max_attempts=2))
        self.assertFalse(game.started)
        self.assertEqual(game.mines, set())

    def test_auto_flag_certain_mine_without_reading_mines(self):
        game = self.prepared()
        game.opened = {(r, c) for r in range(4) for c in range(4)} - {(0, 0), (3, 3)}
        game.mines = set()  # 推理只能使用可见数字，与隐藏雷区无关。
        self.assertEqual(game.auto_flag(), {(0, 0)})
        self.assertEqual(game.auto_flag(), set())
        self.assertEqual(game.flags, {(0, 0)})
        self.assertEqual(game.state, "playing")

    def test_auto_flag_does_not_trust_wrong_flag_or_guess(self):
        game = self.prepared()
        game.flags = {(0, 1)}
        before = game.opened.copy()
        self.assertEqual(game.auto_flag(), set())
        self.assertEqual(game.flags, {(0, 1)})
        self.assertEqual(game.opened, before)

    def test_auto_flag_respects_capacity_and_lifecycle(self):
        self.assertEqual(Game().auto_flag(), set())
        game = self.prepared()
        game.opened = {(r, c) for r in range(4) for c in range(4)} - {(0, 0), (3, 3)}
        game.flags = {(3, 3)}
        self.assertEqual(game.auto_flag(), set())
        self.assertEqual(game.flags, {(3, 3)})
        game.flags.clear()
        game.state = "lost"
        self.assertEqual(game.auto_flag(), set())

    def test_generation_and_auto_flag_use_identical_inference(self):
        # 旧实现 seed=13 第六轮漏标集合差推出的 (2, 0)。
        game = Game(rng=random.Random(13))
        game.reveal((4, 4))
        while not game.finished:
            safe, proven = game.logical_moves()
            game.auto_flag()
            self.assertEqual(game.flags, proven)
            self.assertTrue(safe, "生成器认可的局面在实际游戏中不能无故无路可走")
            for pos in sorted(safe - game.opened):
                game.reveal(pos)
        self.assertEqual(game.state, "won")

    def test_isolated_cells_are_safe_when_all_mines_proven(self):
        game = self.prepared()
        game.opened = {(r, c) for r in range(4) for c in range(4)} - {(0, 0), (3, 0), (3, 1)}
        safe, proven = game.logical_moves()
        self.assertEqual(proven, {(0, 0)})
        self.assertTrue({(3, 0), (3, 1)} <= safe)
        game.auto_flag()
        game.reveal((3, 0))
        self.assertEqual(game.state, "won")

    def test_generated_boards_play_to_win_in_different_safe_orders(self):
        for config in [(9, 9, 10), (16, 16, 40), (16, 30, 99)]:
            for seed in range(3):
                game = Game(*config, rng=random.Random(seed))
                game.reveal((4, 4))
                chooser = random.Random(seed + 100)
                while not game.finished:
                    safe, proven = game.logical_moves()
                    self.assertTrue(safe)
                    self.assertFalse(safe & game.mines)
                    self.assertTrue(proven <= game.mines)
                    game.auto_flag()
                    game.reveal(chooser.choice(sorted(safe)))
                self.assertEqual(game.state, "won")

    def test_inferences_match_exhaustive_small_board_oracle(self):
        cells = {(r, c) for r in range(3) for c in range(3)}
        helper = Game(3, 3, 0)
        rng = random.Random(0)
        for _ in range(40):
            actual = set(rng.sample(sorted(cells), 2))
            opened = set(rng.sample(sorted(cells-actual), rng.randrange(1, 7)))
            visible = {p: len(set(helper.neighbors(p)) & actual) for p in opened}
            possibilities = [set(pair) for pair in combinations(cells-opened, 2)
                             if all(len(set(helper.neighbors(p)) & set(pair)) == n
                                    for p, n in visible.items())]
            safe, proven = analyze(3, 3, 2, visible)
            self.assertTrue(possibilities)
            for possibility in possibilities:
                self.assertFalse(safe & possibility)
                self.assertTrue(proven <= possibility)

    def test_screenshot_safe_elimination_infers_left_edge_mine(self):
        # 截图第7行第3列的2已被两雷满足 -> 第8行2/3/4列安全；
        # 第7行第1列的2还缺一雷 -> 第8行第1列为雷，无需先翻安全格。
        visible = {(5, 0): 2, (5, 2): 2, (5, 3): 1,
                   (6, 0): 2, (6, 1): 2, (6, 2): 2}
        proven = {(5, 1), (6, 3)}
        safe, mines = analyze(16, 30, 99, visible, proven)
        self.assertTrue({(7, 1), (7, 2), (7, 3)} <= safe)
        self.assertIn((7, 0), mines)
        # 自动标雷必须在同一次调用中将该结论显示出来。
        game = Game(16, 30, 99)
        game.started = True
        game.state = "playing"
        game.opened = set(visible)
        game.counts = visible.copy()
        game.proven_mines = proven.copy()
        game.flags = proven.copy()
        self.assertIn((7, 0), game.auto_flag())
        self.assertEqual(game.opened, set(visible))

    def test_three_mine_screenshot_has_safe_cells_but_no_forced_mine(self):
        # 图中左上角十个未翻开格，剩余三雷。旗子视为已证明雷。
        hidden = {(0, 3), (0, 4), (0, 5), (1, 3), (1, 4), (1, 5),
                  (2, 3), (2, 4), (2, 5), (2, 6)}
        known = {(0, 2), (0, 10), (1, 7), (2, 2), (2, 7),
                 (3, 2), (3, 3), (3, 7), (4, 2)}
        # 只提供截图中与隐藏区相邻的数字，其他可见格用于排除未知格。
        visible = {(r, c): 0 for r in range(5) for c in range(12)
                   if (r, c) not in hidden | known}
        # 用一个满足截图的布局计算边界数字，隐藏区布局仅用于构造测试数据。
        helper = Game(5, 12, 12)
        layout = known | {(0, 3), (0, 5), (2, 5)}
        visible = {p: len(set(helper.neighbors(p)) & layout) for p in visible}
        safe, mines = analyze(5, 12, 12, visible, known)
        self.assertTrue({(0, 4), (1, 4), (2, 4)} <= safe)
        self.assertEqual(mines, known)


if __name__ == "__main__":
    unittest.main()

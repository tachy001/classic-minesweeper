"""运行：python -m unittest discover -s tests。无需安装 PyQt6。"""
import random
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from classic_minesweeper.model import Game


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


if __name__ == "__main__":
    unittest.main()

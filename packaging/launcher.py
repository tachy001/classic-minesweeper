"""Windows 打包入口；--smoke-test REPORT 在不显示窗口的情况下自检。"""
import sys


if __name__ == "__main__":
    if "--smoke-test" in sys.argv:
        import json
        import os
        import random
        import time
        from pathlib import Path

        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from PyQt6.QtWidgets import QApplication
        from classic_minesweeper import __version__
        from classic_minesweeper.app import Minesweeper

        app = QApplication([])
        window = Minesweeper()
        for level in range(3):
            window.level.setCurrentIndex(level)
            window.game.rng = random.Random(level)
            window.auto_flag_action.setChecked(True)
            window.click_cell((4, 4))
            deadline = time.monotonic() + 30
            while window.generating and time.monotonic() < deadline:
                app.processEvents()
            assert window.game.started and not window.generating
            assert window.timer.isActive()
            assert window.game.flags <= window.game.mines
            window.show_safe_hint()
            if not window.game.finished:
                assert window.hint_pos is not None
                assert window.hint_pos not in window.game.mines
            window.click_cell(next(iter(window.game.mines - window.game.flags), next(iter(window.game.mines))))
            window.new_game()
            assert not window.game.started
        assert not window.windowIcon().isNull()
        report = {"ok": True, "frozen": bool(getattr(sys, "frozen", False)),
                  "version": __version__, "levels": 3}
        Path(sys.argv[sys.argv.index("--smoke-test") + 1]).write_text(json.dumps(report), encoding="utf-8")
    else:
        from classic_minesweeper.app import main
        main()

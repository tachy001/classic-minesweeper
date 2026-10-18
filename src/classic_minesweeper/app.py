"""中文桌面扫雷：运行 uv run classic-minesweeper。"""
import sys

from PyQt6.QtCore import QElapsedTimer, QPoint, QRect, QSettings, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QColor, QFont, QIcon, QKeySequence, QPainter, QPen, QPixmap, QPolygon
from PyQt6.QtWidgets import (QApplication, QComboBox, QFrame, QGridLayout,
    QHBoxLayout, QLabel, QLCDNumber, QMainWindow, QMessageBox, QPushButton, QScrollArea,
    QSizePolicy, QVBoxLayout, QWidget)

if __package__:
    from .model import Game
else:
    from model import Game


STYLE = """
QMainWindow, QWidget#root { background: #c0c0c0; color: black; }
QMenuBar, QMenu { background: #c0c0c0; color: black; font-size: 12px; }
QMenuBar::item:selected, QMenu::item:selected { background: #000080; color: white; }
QFrame#panel, QScrollArea { border: 3px solid; border-top-color: #808080;
    border-left-color: #808080; border-right-color: #ffffff; border-bottom-color: #ffffff; }
QLabel { color: #202020; font-size: 11px; background: transparent; }
QWidget#board { background: #c0c0c0; }
QLCDNumber { background: #180000; color: #ff0000; border: 1px solid #808080; }
"""


def bevel(p, rect, pressed=False):
    p.fillRect(rect, QColor("#c0c0c0"))
    light, dark = ("#808080", "#ffffff") if pressed else ("#ffffff", "#808080")
    for i in range(2):
        p.setPen(QColor(light))
        p.drawLine(rect.left()+i, rect.bottom()-i, rect.left()+i, rect.top()+i)
        p.drawLine(rect.left()+i, rect.top()+i, rect.right()-i, rect.top()+i)
        p.setPen(QColor(dark))
        p.drawLine(rect.right()-i, rect.top()+i, rect.right()-i, rect.bottom()-i)
        p.drawLine(rect.right()-i, rect.bottom()-i, rect.left()+i, rect.bottom()-i)


def application_icon():
    """多尺寸原生图标：经典立体灰格和黑色地雷。"""
    icon = QIcon()
    for size in (16, 20, 24, 32, 48, 64, 128, 256):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.scale(size / 32, size / 32)
        bevel(painter, QRect(0, 0, 32, 32))
        painter.translate(16, 16)
        painter.setPen(QPen(Qt.GlobalColor.black, 2))
        for dx, dy in ((0, 11), (11, 0), (8, 8), (8, -8)):
            painter.drawLine(-dx, -dy, dx, dy)
        painter.setBrush(Qt.GlobalColor.black)
        painter.drawEllipse(QRect(-8, -8, 16, 16))
        painter.fillRect(QRect(-4, -4, 4, 4), Qt.GlobalColor.white)
        painter.end()
        icon.addPixmap(pixmap)
    return icon


class Cell(QPushButton):
    right_clicked = pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit()
            event.accept()
        else:
            super().mousePressEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        state = self.property("state") or "closed"
        opened = state in {"open", "mine", "hit", "wrong"}
        if opened:
            p.fillRect(self.rect(), QColor("#ff0000" if state == "hit" else "#c0c0c0"))
            # 用实心边条避免缩放下细线落在半像素位置，四边均在格内。
            edge = QColor("#808080")
            p.fillRect(0, 0, self.width(), 1, edge)
            p.fillRect(0, self.height()-1, self.width(), 1, edge)
            p.fillRect(0, 0, 1, self.height(), edge)
            p.fillRect(self.width()-1, 0, 1, self.height(), edge)
        else:
            bevel(p, self.rect(), self.isDown())
        # Draw icons geometrically so the classic symbols do not depend on fonts.
        p.translate(self.width()/2, self.height()/2)
        if state in {"flag", "won"}:
            p.fillRect(QRect(-6, 6, 13, 3), Qt.GlobalColor.black)
            p.fillRect(QRect(-4, 4, 9, 2), Qt.GlobalColor.black)
            p.fillRect(QRect(0, -8, 2, 13), Qt.GlobalColor.black)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor("#ff0000"))
            p.drawPolygon(QPolygon([QPoint(0, -9), QPoint(-8, -4), QPoint(0, -1)]))
        elif state in {"mine", "hit", "wrong"}:
            p.setPen(QPen(Qt.GlobalColor.black, 2))
            for dx, dy in [(0, 9), (9, 0), (6, 6), (6, -6)]:
                p.drawLine(-dx, -dy, dx, dy)
            p.setBrush(Qt.GlobalColor.black)
            p.drawEllipse(QRect(-6, -6, 12, 12))
            p.fillRect(QRect(-3, -3, 3, 3), Qt.GlobalColor.white)
            if state == "wrong":
                p.setPen(QPen(QColor("#ff0000"), 3))
                p.drawLine(-9, -9, 9, 9)
                p.drawLine(-9, 9, 9, -9)
        elif state == "open" and self.text():
            p.setPen(QColor(self.property("numberColor") or "#0000ff"))
            font = QFont("Arial", 17, QFont.Weight.Bold)
            p.setFont(font)
            p.drawText(QRect(-13, -14, 26, 28), Qt.AlignmentFlag.AlignCenter, self.text())


class Face(QPushButton):
    mood = "ready"

    def paintEvent(self, event):
        p = QPainter(self)
        bevel(p, self.rect(), self.isDown())
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.translate(self.width()/2 + int(self.isDown()), self.height()/2 + int(self.isDown()))
        p.setPen(QPen(Qt.GlobalColor.black, 1.2))
        p.setBrush(QColor("#ffff00"))
        p.drawEllipse(QRect(-12, -12, 24, 24))
        p.setBrush(Qt.GlobalColor.black)
        if self.mood == "lost":
            for x in (-5, 5):
                p.drawLine(x-2, -5, x+2, -1)
                p.drawLine(x-2, -1, x+2, -5)
            p.drawArc(QRect(-6, 4, 12, 8), 0, 180*16)
        elif self.mood == "won":
            p.drawRect(QRect(-9, -5, 8, 5))
            p.drawRect(QRect(1, -5, 8, 5))
            p.drawLine(-1, -3, 1, -3)
            p.drawArc(QRect(-6, 0, 12, 8), 180*16, 180*16)
        else:
            p.drawEllipse(QRect(-6, -5, 3, 4))
            p.drawEllipse(QRect(3, -5, 3, 4))
            if self.mood == "pressed":
                p.drawEllipse(QRect(-3, 3, 6, 6))
            else:
                p.drawArc(QRect(-6, 0, 12, 8), 180*16, 180*16)


class Minesweeper(QMainWindow):
    LEVELS = {"初级 · 9 × 9": (9, 9, 10), "中级 · 16 × 16": (16, 16, 40),
              "高级 · 16 × 30": (16, 30, 99)}
    COLORS = ["#808080", "#0000ff", "#008000", "#ff0000", "#000080",
              "#800000", "#008080", "#000000", "#808080"]

    def __init__(self):
        super().__init__()
        self.setWindowTitle("扫雷")
        self.setWindowIcon(application_icon())
        self.setStyleSheet(STYLE)
        self.settings = QSettings("LocalGames", "Minesweeper")
        self.elapsed = QElapsedTimer()
        self.final_seconds = 0
        self.timer = QTimer(self)
        self.timer.setInterval(200)
        self.timer.timeout.connect(self.update_info)
        self.level = QComboBox(self)
        self.level.addItems(self.LEVELS)
        self.level.hide()
        game_menu = self.menuBar().addMenu("游戏(&G)")
        new_action = game_menu.addAction("新游戏(&N)")
        new_action.setShortcut(QKeySequence("F2"))
        new_action.triggered.connect(self.new_game)
        game_menu.addSeparator()
        group = QActionGroup(self)
        for index, name in enumerate(self.LEVELS):
            action = game_menu.addAction(name)
            action.setCheckable(True)
            action.setChecked(index == 0)
            group.addAction(action)
            action.triggered.connect(lambda checked=False, i=index: self.level.setCurrentIndex(i))
        game_menu.addSeparator()
        self.flag_mode = game_menu.addAction("左键插旗模式")
        self.flag_mode.setCheckable(True)
        game_menu.addAction("最佳成绩", self.show_records)
        game_menu.addSeparator()
        game_menu.addAction("退出", self.close)
        help_menu = self.menuBar().addMenu("帮助(&H)")
        help_menu.addAction("玩法", lambda: QMessageBox.information(self, "扫雷玩法",
            "左键翻开，右键插旗。\n点击数字快速展开周围格子。\n首次点击及周围安全。\n翻开所有安全格即可获胜。\n按 F2 或点击笑脸重新开始。"))
        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(9, 9, 9, 7)
        layout.setSpacing(8)
        panel = QFrame()
        panel.setObjectName("panel")
        top = QHBoxLayout(panel)
        top.setContentsMargins(7, 6, 7, 6)
        self.mine_label = self.counter("剩余雷数")
        self.time_label = self.counter("用时（秒，上限显示 999）")
        self.face = Face()
        self.face.setFixedSize(36, 36)
        self.face.setToolTip("新游戏（F2）")
        self.face.setAccessibleName("笑脸：重新开始")
        self.face.clicked.connect(self.new_game)
        top.addWidget(self.mine_label)
        top.addStretch()
        top.addWidget(self.face)
        top.addStretch()
        top.addWidget(self.time_label)
        layout.addWidget(panel)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)
        self.scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.scroll, 1)
        self.status = QLabel()
        self.status.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.status)
        self.level.currentIndexChanged.connect(self.new_game)
        self.new_game()

    def counter(self, tooltip):
        lcd = QLCDNumber(3)
        lcd.setSegmentStyle(QLCDNumber.SegmentStyle.Flat)
        lcd.setFixedSize(66, 38)
        lcd.setSmallDecimalPoint(False)
        lcd.setToolTip(tooltip)
        lcd.setAccessibleName(tooltip)
        return lcd

    def show_records(self):
        lines = []
        for index, name in enumerate(self.LEVELS):
            best = self.settings.value(f"best/{index}", None)
            lines.append(f"{name}：{best} 秒" if best is not None else f"{name}：暂无成绩")
        QMessageBox.information(self, "最佳成绩", "\n".join(lines))

    def set_face(self, mood):
        self.face.mood = mood
        self.face.update()

    def new_game(self):
        self.timer.stop()
        self.elapsed.invalidate()
        self.final_seconds = 0
        self.flag_mode.setChecked(False)
        self.set_face("ready")
        self.game = Game(*self.LEVELS[self.level.currentText()])
        container = QWidget()
        container.setObjectName("board")
        outer = QVBoxLayout(container)
        outer.setContentsMargins(0, 0, 0, 0)
        board_widget = QWidget()
        board_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        grid = QGridLayout(board_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)
        self.buttons = {}
        for r in range(self.game.rows):
            for c in range(self.game.cols):
                pos = r, c
                button = Cell()
                button.setObjectName("cell")
                button.setFixedSize(26, 26)
                button.pressed.connect(lambda: self.set_face("pressed") if not self.game.finished else None)
                button.released.connect(lambda: self.set_face(self.game.state if self.game.finished else "ready"))
                button.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                button.setAccessibleName(f"第 {r+1} 行，第 {c+1} 列，未翻开")
                button.clicked.connect(lambda checked=False, p=pos: self.click_cell(p))
                button.right_clicked.connect(lambda p=pos: self.toggle_flag(p))
                grid.addWidget(button, r, c)
                self.buttons[pos] = button
        outer.addWidget(board_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        container.setFixedSize(board_widget.sizeHint())
        self.scroll.setWidget(container)
        self.status.setText("准备就绪")
        self.update_info()
        self.fit_board()
        # 原生标题栏建立后再核算边框，避免首次显示或切换难度时误差。
        QTimer.singleShot(0, self.fit_board)

    def fit_board(self):
        """经典固定窗口：按布局测量，只在屏幕容纳不下时启用滚动。"""
        self.ensurePolished()
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        board = self.scroll.widget().size()
        border = self.scroll.frameWidth() * 2
        self.scroll.setFixedSize(board.width() + border, board.height() + border)
        self.centralWidget().layout().activate()
        self.layout().activate()
        desired = self.sizeHint()
        screen = self.screen().availableGeometry()
        frame = self.frameGeometry().size() - self.size()
        limit_w = max(1, screen.width() - frame.width())
        limit_h = max(1, screen.height() - frame.height())
        width = min(desired.width(), limit_w)
        height = min(desired.height(), limit_h)
        view_w = self.scroll.width() - (desired.width() - width)
        view_h = self.scroll.height() - (desired.height() - height)
        # 一个方向出现滚动条会占用另一个方向的视口。
        from PyQt6.QtWidgets import QStyle
        extent = self.style().pixelMetric(QStyle.PixelMetric.PM_ScrollBarExtent)
        if height < desired.height() and width + extent <= limit_w:
            width += extent
            view_w += extent
        if width < desired.width() and height + extent <= limit_h:
            height += extent
            view_h += extent
        self.scroll.setFixedSize(max(border + 1, view_w), max(border + 1, view_h))
        self.setFixedSize(width, height)
        # 大棋盘切回小棋盘或靠近屏幕边缘时，保持整个窗口可见。
        if self.isVisible():
            rect = self.frameGeometry()
            x = min(max(rect.left(), screen.left()), screen.right() - rect.width() + 1)
            y = min(max(rect.top(), screen.top()), screen.bottom() - rect.height() + 1)
            self.move(x, y)

    @property
    def seconds(self):
        return self.elapsed.elapsed() // 1000 if self.elapsed.isValid() and not self.game.finished else self.final_seconds

    def update_info(self):
        self.mine_label.display(f"{self.game.mine_count-len(self.game.flags):03d}")
        self.time_label.display(f"{min(self.seconds, 999):03d}")

    def paint_cell(self, pos, state, text="", color=None):
        button = self.buttons[pos]
        button.setText(text)
        button.setProperty("state", state)
        button.setProperty("numberColor", color)
        button.style().unpolish(button)
        button.style().polish(button)
        labels = {"open": f"数字 {text}" if text else "空白", "flag": "已插旗",
                  "mine": "地雷", "hit": "踩中地雷", "wrong": "错误标记", "won": "已找到地雷"}
        button.setAccessibleName(f"第 {pos[0]+1} 行，第 {pos[1]+1} 列，{labels.get(state, '未翻开')}")
        button.update()

    def toggle_flag(self, pos):
        if self.game.toggle_flag(pos):
            flagged = pos in self.game.flags
            self.paint_cell(pos, "flag" if flagged else "closed", "旗" if flagged else "")
            self.update_info()
        elif not self.game.finished and pos not in self.game.opened:
            self.status.setText("旗子已用完 · 请先取消一个标记")

    def click_cell(self, pos):
        if self.game.finished:
            return
        if self.flag_mode.isChecked():
            self.toggle_flag(pos)
            return
        was_started = self.game.started
        changed = self.game.reveal(pos)
        if self.game.started and not was_started:
            self.elapsed.start()
            self.timer.start()
        for p in changed:
            count = self.game.counts[p]
            self.paint_cell(p, "open", str(count) if count else "", self.COLORS[count])
        if self.game.finished:
            self.finish()
        elif self.game.started:
            self.status.setText("游戏中")
        self.update_info()

    def finish(self):
        self.final_seconds = self.elapsed.elapsed() // 1000 if self.elapsed.isValid() else 0
        self.timer.stop()
        self.set_face(self.game.state)
        won = self.game.state == "won"
        for pos in self.game.mines:
            state = "won" if won else "hit" if pos == self.game.hit else "mine"
            self.paint_cell(pos, state, "旗" if won or pos in self.game.flags else "●")
        for pos in self.game.flags-self.game.mines:
            self.paint_cell(pos, "wrong", "×")
        if won:
            key = f"best/{self.level.currentIndex()}"
            best = self.settings.value(key, None)
            record = best is None or self.final_seconds < int(best)
            if record:
                self.settings.setValue(key, self.final_seconds)
            self.status.setText(f"胜利！{self.final_seconds} 秒" + (" · 新纪录" if record else ""))
        else:
            self.status.setText("踩雷了！按 F2 重来")


def main() -> None:
    if sys.platform == "win32":
        import ctypes
        # 独立的任务栏分组，使用扫雷图标而不是 Python 解释器图标。
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LocalGames.Minesweeper")
    app = QApplication(sys.argv)
    app.setWindowIcon(application_icon())
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = Minesweeper()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

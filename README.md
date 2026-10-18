# Classic Minesweeper · 经典扫雷

Python + PyQt6 编写的经典 Windows 风格桌面扫雷。

![游戏截图](docs/images/preview.png)

## 功能

- 灰色立体方格、红色数码管、笑脸按钮与地雷图标。
- 初级（9×9 / 10 雷）、中级（16×16 / 40 雷）、高级（16×30 / 99 雷）。
- 首次点击及周围区域安全，空白区域自动展开。
- 右键插旗；点击已翻开的数字快速展开，插错旗仍可能踩雷。
- F2 或笑脸重开，支持左键插旗模式与分难度最佳成绩。
- 窗口按棋盘实际尺寸固定，屏幕容纳不下时使用滚动条。

## 运行

需要 Python 3.14+ 和 uv。在项目根目录执行：

```powershell
uv sync
uv run classic-minesweeper
```

也可使用模块入口：

```powershell
uv run python -m classic_minesweeper
```

IDE 请使用项目虚拟环境，运行 `src/classic_minesweeper/__main__.py`。

## 项目结构

```text
classic-minesweeper/
├── src/classic_minesweeper/
│   ├── __init__.py      # 包信息
│   ├── __main__.py      # 模块与 IDE 启动入口
│   ├── app.py           # PyQt6 界面、绘制、计时和窗口适配
│   └── model.py         # 不依赖 GUI 的游戏规则
├── tests/test_model.py  # 规则测试
├── docs/images/         # 游戏截图与图标预览
├── pyproject.toml       # 项目元数据和命令入口
└── uv.lock             # 依赖版本锁定
```

## 测试

规则测试无需安装 PyQt6：

```powershell
python -m unittest discover -s tests -v
```

使用 uv：

```powershell
uv run python -m unittest discover -s tests -v
```

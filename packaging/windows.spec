from pathlib import Path
import os
import sys
root = Path(SPECPATH).parent
sys.path.insert(0, str(root / "src"))
os.environ["QT_QPA_PLATFORM"] = "offscreen"
from PyQt6.QtWidgets import QApplication
from classic_minesweeper import __version__
from classic_minesweeper.app import application_icon

icon = root / "build" / "minesweeper.ico"
icon.parent.mkdir(exist_ok=True)
app = QApplication.instance() or QApplication([])
assert application_icon().pixmap(256, 256).save(str(icon), "ICO")
a = Analysis([str(root / "packaging" / "launcher.py")], pathex=[str(root / "src")],
             binaries=[], datas=[], hiddenimports=[], hookspath=[], hooksconfig={},
             runtime_hooks=[], excludes=[], noarchive=False, optimize=0)
# Qt uses the Windows system ICU API. Exclude unrelated ICU DLLs found on PATH.
a.binaries = [entry for entry in a.binaries
              if Path(entry[0]).name.lower() not in {"icuuc.dll", "icudt78.dll"}]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, a.binaries, a.datas, [],
          name=f"ClassicMinesweeper-v{__version__}-Windows-x64",
          debug=False, strip=False, upx=False, console=False, icon=[str(icon)])

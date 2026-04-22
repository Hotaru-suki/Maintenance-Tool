import importlib.util
from pathlib import Path
import sys

project_root = Path.cwd()
src_root = project_root / "src"
if str(src_root) not in sys.path:
    sys.path.insert(0, str(src_root))

from maintenancetool.branding import PRODUCT_EXE_NAME, PRODUCT_ICON_NAME, PRODUCT_NAME

src_root = project_root / "src"
template_root = project_root / "packaging" / "config_templates"
icon_path = project_root / "packaging" / "assets" / PRODUCT_ICON_NAME
hiddenimports = []

if importlib.util.find_spec("tzdata") is not None:
    hiddenimports.append("tzdata")

block_cipher = None

a = Analysis(
    [str(src_root / "maintenancetool" / "runtime_main.py")],
    pathex=[str(src_root)],
    binaries=[],
    datas=[(str(template_root), "config_templates")],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "tests"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=Path(PRODUCT_EXE_NAME).stem,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    icon=str(icon_path),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name=PRODUCT_NAME,
)

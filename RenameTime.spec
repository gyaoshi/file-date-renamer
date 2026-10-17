# -*- mode: python ; coding: utf-8 -*-
#
# onedir 打包配置（产出 RenameTime-fast.zip，启动比 onefile 快约 1.5 秒）
# onefile 版请用 README 中记录的等价命令行参数重新生成。
#
# excludes 每项都经源码核实为「零引用」：
#   hashlib/_hashlib -> 连带 libcrypto-3-x64.dll (7.6MB)，本程序不联网
#   _ssl/ssl         -> 本程序不联网
#   wx.html          -> 连带 wxmsw333u_html DLL + _html.pyd (1.3MB)，v1.0 遗留功能已废弃
#   email            -> 被 importlib.metadata 连带引入的 20 个模块
#   tarfile          -> 不读写 .tar
#
# ⚠️ 切勿排除 gettext / lzma / bz2：argparse 在 Python 3.13 会 import gettext，
#    排除后 exe 启动即崩（ModuleNotFoundError: No module named 'gettext'）

a = Analysis(
    ['D:/project/renameTime/rename_time.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['hashlib', '_hashlib', '_ssl', 'ssl', 'wx.html', 'email', 'tarfile'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RenameTime',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['D:/project/renameTime/app_icon.ico'],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RenameTime',
)

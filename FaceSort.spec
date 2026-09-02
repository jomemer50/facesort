# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['C:/Users/My PC/Documents/facesort/run.py'],
    pathex=['C:/Users/My PC/Documents/facesort/src'],
    binaries=[],
    datas=[('C:/Users/My PC/Documents/facesort/.venv/Lib/site-packages/insightface/data/images/mask_blue.jpg', 'insightface/data/images'), ('C:/Users/My PC/Documents/facesort/.venv/Lib/site-packages/insightface/data/images/mask_black.jpg', 'insightface/data/images'), ('C:/Users/My PC/Documents/facesort/.venv/Lib/site-packages/insightface/data/images/t1.jpg', 'insightface/data/images'), ('C:/Users/My PC/Documents/facesort/.venv/Lib/site-packages/insightface/data/objects/meanshape_68.pkl', 'insightface/data/objects'), ('C:/Users/My PC/Documents/facesort/.venv/Lib/site-packages/insightface/gui/assets/app_icon.icns', 'insightface/gui/assets'), ('C:/Users/My PC/Documents/facesort/.venv/Lib/site-packages/insightface/data/images/Tom_Hanks_54745.png', 'insightface/data/images'), ('C:/Users/My PC/Documents/facesort/.venv/Lib/site-packages/insightface/data/images/mask_green.jpg', 'insightface/data/images'), ('C:/Users/My PC/Documents/facesort/.venv/Lib/site-packages/insightface/gui/assets/app_icon.png', 'insightface/gui/assets'), ('C:/Users/My PC/Documents/facesort/.venv/Lib/site-packages/insightface/gui/assets/app_icon.ico', 'insightface/gui/assets'), ('C:/Users/My PC/Documents/facesort/.venv/Lib/site-packages/insightface/data/images/mask_white.jpg', 'insightface/data/images'), ('C:/Users/My PC/Documents/facesort/.venv/Lib/site-packages/insightface/data/objects', 'objects'), ('C:/Users/My PC/Documents/facesort/assets/favicon.png', 'assets/favicon.png')],
    hiddenimports=['sklearn', 'scipy', 'onnxruntime', 'cv2', 'faiss', 'insightface', 'msal', 'requests', 'msal.oauth2cli.http', 'PySide6.QtWidgets', 'PySide6.QtGui', 'PySide6.QtCore'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='FaceSort',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:/Users/My PC/Documents/facesort/assets/favicon.ico'],
)

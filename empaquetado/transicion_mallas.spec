# Receta de PyInstaller: empaqueta Python, las librerías y la aplicación en dist/TransicionMallas/.
# Uso (desde la raíz del proyecto):  .venv\Scripts\pyinstaller empaquetado\transicion_mallas.spec --noconfirm
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

RAIZ = SPECPATH + "/.."

ocultos = (
    collect_submodules("uvicorn")          # uvicorn carga sus protocolos de forma dinámica
    + collect_submodules("app")
    + ["scripts.crear_datos_ejemplo", "scripts.datos_ingenieria_quimica", "multipart", "python_multipart"]
)
datos = [
    (RAIZ + "/app/presentation/web", "app/presentation/web"),   # interfaz (HTML, CSS, JS)
    *collect_data_files("googleapiclient"),                     # documentos de la API de Drive
]

a = Analysis(
    [RAIZ + "/empaquetado/lanzador.py"],
    pathex=[RAIZ],
    datas=datos,
    hiddenimports=ocultos,
    excludes=["pytest", "_pytest", "tkinter", "PyInstaller"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="TransicionMallas",
    console=True,                 # ventana con el estado; cerrarla detiene el servidor
    icon=RAIZ + "/empaquetado/icono.ico",
)
coll = COLLECT(exe, a.binaries, a.datas, name="TransicionMallas")

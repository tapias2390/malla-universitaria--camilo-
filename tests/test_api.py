"""Pruebas de punta a punta de la API sobre una copia temporal de los Excel."""
import shutil

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.config import Settings
from app.presentation.api.main import crear_app

ADMIN = ("admin", "Admin2025*")
CONSULTOR = ("consultor", "Consulta2025*")
PRUEBA1 = ("20242001", "Estudiante2026*")


@pytest.fixture(scope="module")
def cliente(datos_dir, tmp_path_factory) -> TestClient:
    carpeta = tmp_path_factory.mktemp("api")
    for nombre in ("usuarios.xlsx", "academico.xlsx"):
        shutil.copy(datos_dir / nombre, carpeta / nombre)   # el CRUD escribe: se usa una copia
    settings = Settings(
        jwt_secret="x" * 40,
        fuente_datos="local",
        usuarios_excel_path=str(carpeta / "usuarios.xlsx"),
        academico_excel_path=str(carpeta / "academico.xlsx"),
        tickets_path=str(carpeta / "tickets.json"),
        auditoria_path=str(carpeta / "auditoria.jsonl"),
        malla_vigente="2026",
    )
    return TestClient(crear_app(settings))


def token(cliente: TestClient, credenciales: tuple[str, str]) -> dict:
    r = cliente.post("/api/auth/login", data={"username": credenciales[0], "password": credenciales[1]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


# ------------------------------------------------------------------ autenticación y roles
def test_login_incorrecto(cliente):
    assert cliente.post("/api/auth/login", data={"username": "admin", "password": "mala"}).status_code == 401


def test_usuario_inactivo_no_entra(cliente):
    r = cliente.post("/api/auth/login", data={"username": "inactivo", "password": "Inactivo2025*"})
    assert r.status_code == 401


def test_sin_token_no_hay_acceso(cliente):
    assert cliente.get("/api/estudiantes").status_code == 401


def test_consultor_no_administra(cliente):
    h = token(cliente, CONSULTOR)
    assert cliente.get("/api/tickets", headers=h).status_code == 403
    assert cliente.get("/api/admin/usuarios", headers=h).status_code == 403
    assert cliente.get("/api/estudiantes", headers=h).status_code == 200


def test_estudiante_solo_ve_su_avance(cliente):
    h = token(cliente, PRUEBA1)
    r = cliente.get("/api/mi-avance", headers=h)
    assert r.status_code == 200
    datos = r.json()
    assert datos["estudiante"]["codigo"] == "20242001"
    assert datos["creditos"]["reconocidos"] == 49
    assert datos["tickets_nuevos"] == 0                       # el estudiante no abre tickets
    # No puede ver a otros estudiantes ni administrar
    assert cliente.get("/api/estudiantes", headers=h).status_code == 403
    assert cliente.post("/api/estudiantes/20221001/validar-malla", headers=h).status_code == 403
    assert cliente.get("/api/admin/estudiantes/20221001", headers=h).status_code == 403
    # Sí puede ver las mallas y sus equivalencias (vista de comparación)
    assert cliente.get("/api/mallas/vigente", headers=h).json()["version"] == "2026"
    equivalencias = cliente.get("/api/equivalencias", headers=h).json()
    assert len(equivalencias) == 7 and {"codigo_anterior", "codigo_nuevo", "estado"} <= equivalencias[0].keys()


# ------------------------------------------------------------------ validación y tickets
def test_validacion_crea_tickets_una_sola_vez(cliente):
    h = token(cliente, ADMIN)
    r = cliente.post("/api/estudiantes/20242001/validar-malla", headers=h).json()
    assert r["requiere_transicion"] is True
    assert r["tickets_nuevos"] == 4
    assert r["comparacion"]["pendientes_origen"] == 132
    r2 = cliente.post("/api/estudiantes/20242001/validar-malla", headers=h).json()
    assert r2["tickets_nuevos"] == 0 and len(r2["tickets"]) == 4


def test_admin_cierra_ticket(cliente):
    h = token(cliente, ADMIN)
    abiertos = cliente.get("/api/tickets?estado=abierto", headers=h).json()
    assert abiertos
    r = cliente.post(f"/api/tickets/{abiertos[0]['id']}/cerrar", json={"resolucion": "Homologada por comité"}, headers=h)
    assert r.status_code == 200 and r.json()["estado"] == "cerrado"


# ------------------------------------------------------------------ CRUD estudiantes
NUEVO = {
    "codigo": "20262099", "nombre": "Estudiante Prueba Cuatro", "documento": "1000000099",
    "correo": "prueba4@ejemplo.edu.co", "malla_version": "2016", "estado": "activo",
    "password_cuenta": "Clave2026x",
}


def test_crud_estudiante_completo(cliente):
    h = token(cliente, ADMIN)

    r = cliente.post("/api/admin/estudiantes", json=NUEVO, headers=h)
    assert r.status_code == 201, r.text
    assert cliente.post("/api/admin/estudiantes", json=NUEVO, headers=h).status_code == 409   # duplicado

    historial = {"materias": [
        {"codigo": "1000004", "nombre": "Cálculo Diferencial", "creditos": 4, "nota": 3.8,
         "periodo": "2026-1S", "estado": "aprobada", "tipologia": "fund_obligatoria"},
        {"codigo": "1000006", "nombre": "Cálculo Vectorial", "creditos": 4, "nota": None,
         "periodo": "2026-2S", "estado": "cursando", "tipologia": "fund_obligatoria"},
    ]}
    r = cliente.put("/api/admin/estudiantes/20262099/historial", json=historial, headers=h)
    assert r.status_code == 200 and len(r.json()["historial"]) == 2

    cambios = {k: NUEVO[k] for k in ("nombre", "documento", "correo", "estado")} | {"malla_version": "2026"}
    r = cliente.put("/api/admin/estudiantes/20262099", json=cambios, headers=h)
    assert r.status_code == 200 and r.json()["malla_version"] == "2026"

    # Su cuenta de estudiante funciona y ve su avance
    h_est = token(cliente, ("20262099", "Clave2026x"))
    assert cliente.get("/api/mi-avance", headers=h_est).json()["creditos"]["reconocidos"] == 4

    assert cliente.delete("/api/admin/estudiantes/20262099", headers=h).status_code == 204
    assert cliente.get("/api/admin/estudiantes/20262099", headers=h).status_code == 404
    # Al eliminar el estudiante se elimina su cuenta
    assert cliente.post("/api/auth/login", data={"username": "20262099", "password": "Clave2026x"}).status_code == 401


def test_estudiante_con_malla_inexistente_es_rechazado(cliente):
    h = token(cliente, ADMIN)
    datos = {**NUEVO, "codigo": "X1234", "documento": "55555", "malla_version": "1999", "password_cuenta": ""}
    r = cliente.post("/api/admin/estudiantes", json=datos, headers=h)
    assert r.status_code == 422 and "1999" in r.json()["detail"]


# ------------------------------------------------------------------ CRUD usuarios y auditoría
def test_crud_usuario_y_protecciones(cliente):
    h = token(cliente, ADMIN)
    nuevo = {"username": "consultor2", "nombre": "Otro Consultor", "rol": "consultor", "password": "Consulta123"}
    assert cliente.post("/api/admin/usuarios", json=nuevo, headers=h).status_code == 201
    token(cliente, ("consultor2", "Consulta123"))

    r = cliente.put("/api/admin/usuarios/consultor2", json={**nuevo, "activo": False, "password": ""}, headers=h)
    assert r.status_code == 200 and r.json()["activo"] is False
    assert cliente.post("/api/auth/login", data={"username": "consultor2", "password": "Consulta123"}).status_code == 401

    assert cliente.delete("/api/admin/usuarios/consultor2", headers=h).status_code == 204
    # El admin no puede borrarse a sí mismo
    assert cliente.delete("/api/admin/usuarios/admin", headers=h).status_code == 422


def test_auditoria_registra_las_operaciones(cliente):
    h = token(cliente, ADMIN)
    eventos = cliente.get("/api/admin/auditoria", headers=h).json()
    acciones = {e["accion"] for e in eventos}
    assert {"login", "login_fallido", "validar_malla", "cerrar_ticket", "crear_estudiante",
            "eliminar_estudiante", "crear_usuario", "eliminar_usuario"} <= acciones
    assert all(e["usuario"] for e in eventos)
    solo_fallidos = cliente.get("/api/admin/auditoria?accion=login_fallido", headers=h).json()
    assert solo_fallidos and all(not e["exito"] for e in solo_fallidos)


# ------------------------------------------------------------------ importación desde Excel
def _excel(estudiantes: list[list], materias: list[list]) -> bytes:
    import io

    from openpyxl import Workbook

    libro = Workbook()
    hoja = libro.active
    hoja.title = "estudiantes"
    hoja.append(["codigo", "nombre", "documento", "correo", "malla_version", "estado"])
    for fila in estudiantes:
        hoja.append(fila)
    hoja = libro.create_sheet("materias_vistas")
    hoja.append(["codigo_estudiante", "codigo_materia", "nombre_materia", "creditos", "nota", "estado", "tipologia", "periodo"])
    for fila in materias:
        hoja.append(fila)
    buffer = io.BytesIO()
    libro.save(buffer)
    return buffer.getvalue()


def _subir(cliente, h, ruta, contenido, **form):
    archivos = {"archivo": ("estudiantes.xlsx", contenido, "application/octet-stream")}
    return cliente.post(f"/api/admin/importacion/{ruta}", files=archivos, data=form, headers=h)


def test_plantilla_se_descarga(cliente):
    r = cliente.get("/api/admin/importacion/plantilla", headers=token(cliente, ADMIN))
    assert r.status_code == 200 and r.content[:2] == b"PK"      # un .xlsx es un zip


def test_importacion_con_errores_no_guarda_nada(cliente):
    h = token(cliente, ADMIN)
    contenido = _excel(
        [["30001", "Importado Uno", "2000000001", "", "2016", "activo"],
         ["30002", "Importado Dos", "2000000002", "", "1999", "activo"]],          # malla inexistente
        [["30001", "1000004", "Cálculo Diferencial", 4, 7, "aprobada", "", "2025-1S"],   # nota fuera de rango
         ["99999", "1000004", "Cálculo Diferencial", 4, 4, "aprobada", "", "2025-1S"]],  # estudiante inexistente
    )
    r = _subir(cliente, h, "aplicar", contenido).json()
    assert r["aplicado"] is False
    filas = {(e["hoja"], e["fila"]) for e in r["errores"]}
    assert {("estudiantes", 3), ("materias_vistas", 2), ("materias_vistas", 3)} <= filas
    assert cliente.get("/api/admin/estudiantes/30001", headers=h).status_code == 404


def test_importacion_crea_y_actualiza(cliente):
    h = token(cliente, ADMIN)
    contenido = _excel(
        [["30010", "Importado Diez", "2000000010", "diez@ejemplo.edu.co", "2016", "activo"],
         ["20261001", "Estudiante Prueba Tres", "1000000003", "", "2026", "activo"]],   # ya existe: se actualiza
        [["30010", "1000004", "Cálculo Diferencial", 4, 4.1, "aprobada", "B", "2025-1S"],
         ["30010", "1000044", "Inglés I", 3, None, "Aprobada (SUF)", "E", "2025-1S"],
         ["30010", "1000005", "Cálculo Integral", 4, None, "cursando", "B", "2025-2S"]],
    )
    previa = _subir(cliente, h, "validar", contenido, password_cuentas="Clave2026x").json()
    assert previa["errores"] == [] and previa["aplicado"] is False
    assert (previa["nuevos"], previa["actualizados"], previa["total_materias"]) == (1, 1, 3)

    r = _subir(cliente, h, "aplicar", contenido, password_cuentas="Clave2026x").json()
    assert r["aplicado"] is True
    detalle = cliente.get("/api/admin/estudiantes/30010", headers=h).json()
    assert len(detalle["historial"]) == 3
    # prueba3 se actualizó pero conservó su historial (no venía en materias_vistas)
    assert len(cliente.get("/api/admin/estudiantes/20261001", headers=h).json()["historial"]) == 10
    # Se creó la cuenta del estudiante nuevo y ve su avance (Cálculo Diferencial 4 + Inglés I 3)
    h_est = token(cliente, ("30010", "Clave2026x"))
    assert cliente.get("/api/mi-avance", headers=h_est).json()["creditos"]["reconocidos"] == 7
    acciones = {e["accion"] for e in cliente.get("/api/admin/auditoria", headers=h).json()}
    assert "importar_estudiantes" in acciones

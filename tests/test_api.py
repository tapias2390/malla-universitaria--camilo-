"""Pruebas de punta a punta de la API usando los Excel de ejemplo."""
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.infrastructure.config import Settings
from app.presentation.api.main import crear_app

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def cliente(tmp_path_factory) -> TestClient:
    if not (RAIZ / "data" / "academico.xlsx").exists():
        subprocess.run([sys.executable, str(RAIZ / "scripts" / "crear_datos_ejemplo.py")], check=True)
    settings = Settings(
        jwt_secret="x" * 40,
        fuente_datos="local",
        usuarios_excel_path=str(RAIZ / "data" / "usuarios.xlsx"),
        academico_excel_path=str(RAIZ / "data" / "academico.xlsx"),
        tickets_path=str(tmp_path_factory.mktemp("tickets") / "tickets.json"),
        malla_vigente="2025",
    )
    return TestClient(crear_app(settings))


def token(cliente: TestClient, usuario: str, clave: str) -> dict:
    r = cliente.post("/api/auth/login", data={"username": usuario, "password": clave})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_login_incorrecto(cliente):
    r = cliente.post("/api/auth/login", data={"username": "admin", "password": "mala"})
    assert r.status_code == 401


def test_usuario_inactivo_no_entra(cliente):
    r = cliente.post("/api/auth/login", data={"username": "inactivo", "password": "Inactivo2025*"})
    assert r.status_code == 401


def test_sin_token_no_hay_acceso(cliente):
    assert cliente.get("/api/estudiantes").status_code == 401


def test_validacion_estudiante_antiguo_crea_ticket_una_sola_vez(cliente):
    h = token(cliente, "admin", "Admin2025*")
    r = cliente.post("/api/estudiantes/2002/validar-malla", headers=h).json()
    assert r["requiere_transicion"] is True
    assert r["tickets_nuevos"] == 1
    # Validar otra vez no duplica el ticket
    r2 = cliente.post("/api/estudiantes/2002/validar-malla", headers=h).json()
    assert r2["tickets_nuevos"] == 0 and len(r2["tickets"]) == 1


def test_consultor_no_ve_tickets(cliente):
    h = token(cliente, "consultor", "Consulta2025*")
    assert cliente.get("/api/tickets", headers=h).status_code == 403


def test_admin_cierra_ticket(cliente):
    h = token(cliente, "admin", "Admin2025*")
    abiertos = cliente.get("/api/tickets?estado=abierto", headers=h).json()
    assert abiertos
    r = cliente.post(f"/api/tickets/{abiertos[0]['id']}/cerrar", json={"resolucion": "Homologada por comité"}, headers=h)
    assert r.status_code == 200 and r.json()["estado"] == "cerrado"

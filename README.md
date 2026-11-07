# Transición de Mallas Curriculares

Aplicación local en Python (FastAPI) con login JWT. Lee dos archivos Excel guardados en
Google Drive (uno de **usuarios** y otro **académico**) y calcula cómo queda cada
estudiante en la **malla vigente**. Crea tickets para los casos que una persona tiene que revisar.

## Inicio rápido

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env                 # y cambia JWT_SECRET
python scripts\crear_datos_ejemplo.py  # genera data\usuarios.xlsx y data\academico.xlsx
python run.py                          # http://127.0.0.1:8000   (API: /docs)
pytest                                 # pruebas
```

Usuarios de ejemplo: `admin / Admin2025*` (ve los tickets) y `consultor / Consulta2025*`.

## Arquitectura (limpia / hexagonal)

```
app/
├── domain/                  ← reglas de negocio puras (no usa librerías externas)
│   ├── entities.py            Usuario, Materia, Malla, Estudiante, Ticket, ResultadoTransicion…
│   ├── exceptions.py          errores de negocio
│   └── services/motor_transicion.py   ★ algoritmo de homologación
├── application/             ← casos de uso + puertos (interfaces)
│   ├── ports.py               RepositorioUsuarios, RepositorioAcademico, RepositorioTickets…
│   └── use_cases/             IniciarSesion, ValidarMallaEstudiante, CerrarTicket…
├── infrastructure/          ← implementaciones concretas
│   ├── config.py              variables de entorno (.env)
│   ├── security/              JWT (PyJWT) y bcrypt
│   ├── data_sources/          Excel local, Google Drive y caché
│   └── repositories/          Excel → entidades; tickets en JSON
├── presentation/            ← API FastAPI + página web
└── bootstrap.py             ← conecta todo según la configuración
```

Las dependencias van **hacia adentro**: el dominio no conoce Excel, Drive ni HTTP. Para cambiar
el origen de datos (por ejemplo, a una base de datos) se escribe otro repositorio que cumpla el
puerto, sin tocar las reglas.

## Reglas de transición de malla

Para cada estudiante se compara su historial con la malla vigente (`MALLA_VIGENTE`):

| #   | Situación de la materia vista                                                        | Resultado                                              |
| --- | ------------------------------------------------------------------------------------ | ------------------------------------------------------ |
| 1   | Reprobada (nota < `NOTA_MINIMA`)                                                     | No se homologa. Si la repitió, cuenta el mejor intento |
| 2   | Existe con el mismo código en la malla nueva                                         | **Directa**                                            |
| 3   | Cambió de código (hoja `equivalencias`)                                              | **Equivalencia**                                       |
| 4   | Fue eliminada y hay un cupo de electiva libre con **créditos ≤** a los de la materia | **Reemplazo por electiva**                             |
| 5   | Fue eliminada y no hay electiva que cumpla los créditos                              | **Requiere revisión → ticket**                         |

- Un estudiante **nuevo** (su `malla_version` ya es la vigente) solo ve su avance en la malla nueva.
- Las materias eliminadas se procesan de **mayor a menor número de créditos**, y a cada una se le asigna
  la electiva que menos créditos desperdicia.
- Se abre **un solo ticket** por estudiante y materia, aunque se valide varias veces.
- El resultado muestra los créditos aprobados, reconocidos, requeridos y pendientes.

## Estructura de los Excel

**usuarios.xlsx**, hoja `usuarios`:
`username | password_hash | nombre | rol (admin/consultor) | activo (si/no)`

Las contraseñas se guardan **solo como hash bcrypt**. Para generar uno: `python scripts\generar_hash.py`

**academico.xlsx**:

| Hoja                         | Columnas                                                                   |
| ---------------------------- | -------------------------------------------------------------------------- |
| `estudiantes`                | codigo, nombre, documento, malla_version, estado                           |
| `materias_vistas`            | codigo_estudiante, codigo_materia, nombre_materia, creditos, nota, periodo |
| `mallas`                     | version, codigo, nombre, creditos, semestre, tipo (obligatoria/electiva)   |
| `equivalencias` _(opcional)_ | codigo_anterior, codigo_nuevo                                              |

Los encabezados no distinguen mayúsculas ni tildes (`Código Materia` = `codigo_materia`).

## Conectar Google Drive (sin hacer públicos los archivos)

1. En [Google Cloud Console](https://console.cloud.google.com/): crea un proyecto, activa la **Google Drive API**
   y crea una **cuenta de servicio**. Descarga su llave JSON en `credenciales/service_account.json`.
2. En Drive, **comparte** los dos archivos (como _Lector_) con el correo de la cuenta de servicio
   (`...@...iam.gserviceaccount.com`). No hace falta "cualquier persona con el enlace".
3. En `.env`:
   ```
   FUENTE_DATOS=drive
   USUARIOS_EXCEL_LINK=https://docs.google.com/spreadsheets/d/XXXX/edit
   ACADEMICO_EXCEL_LINK=https://docs.google.com/spreadsheets/d/YYYY/edit
   ```
   Sirve un `.xlsx` subido a Drive o una Hoja de cálculo de Google. Los archivos se guardan en caché
   `CACHE_SEGUNDOS` segundos. Si Drive falla, se sigue usando la última copia descargada.

## Seguridad

- Tokens JWT firmados con HS256 y con vencimiento. El algoritmo está fijo en el código, así que no se acepta `alg: none`.
- Contraseñas con bcrypt. El login responde el mismo error si el usuario no existe, está inactivo
  o la contraseña es incorrecta.
- Después de 5 intentos fallidos en 5 minutos (por IP y usuario) se bloquea el login temporalmente.
- Roles: `consultor` solo consulta; `admin` además gestiona tickets.
- Acceso a Drive de **solo lectura** con una cuenta de servicio. `.env` y `credenciales/` están en `.gitignore`.
- El servidor escucha solo en `127.0.0.1`.

## API

| Método | Ruta                                            | Rol        |
| ------ | ----------------------------------------------- | ---------- |
| POST   | `/api/auth/login` (form: username, password)    | —          |
| GET    | `/api/auth/yo`                                  | cualquiera |
| GET    | `/api/estudiantes?q=`                           | cualquiera |
| POST   | `/api/estudiantes/{codigo}/validar-malla`       | cualquiera |
| GET    | `/api/mallas/vigente` · `/api/mallas/{version}` | cualquiera |
| GET    | `/api/tickets?estado=abierto\|cerrado`          | admin      |
| POST   | `/api/tickets/{id}/cerrar` (json: resolucion)   | admin      |

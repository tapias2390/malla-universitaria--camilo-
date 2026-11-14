# Transición de Mallas Curriculares — Ingeniería Química

Aplicación local (Python + FastAPI) para **pasar a los estudiantes de la malla 2016 a la malla
vigente 2026** del programa de Ingeniería Química (UNAL Manizales). El sistema:

- calcula qué materias vistas se reconocen en la malla nueva y cuántos créditos lleva y le faltan
  a cada estudiante;
- reemplaza las materias que ya no existen por cupos de **libre elección de igual o menor crédito**
  y, si no caben, **abre un ticket** para que una persona decida;
- compara cuánto le falta en su malla y en la nueva, y **recomienda si le conviene la transición**;
- permite al **administrador** registrar y editar estudiantes, su historial y los usuarios
  (CRUD), y deja todo en una **auditoría**;
- permite al **estudiante** iniciar sesión y ver solo su avance en la malla nueva.

Los datos viven en dos Excel (local o en Google Drive): **usuarios** y **académico**.

## Inicio rápido

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env                          # y cambia JWT_SECRET
python scripts\crear_datos_ejemplo.py           # genera data\usuarios.xlsx y data\academico.xlsx
python run.py                                   # http://127.0.0.1:8000   (API: /docs)
pytest                                          # pruebas
```

En Git Bash, activa el entorno con `source .venv/Scripts/activate`.

| Rol | Usuario | Contraseña | Qué puede hacer |
|---|---|---|---|
| Administrador | `admin` | `Admin2025*` | Todo: estudiantes, historial, usuarios, tickets, auditoría |
| Consultor | `consultor` | `Consulta2025*` | Buscar estudiantes y validar su transición |
| Estudiante | `20242001`, `20221001`, `20261001` | `Estudiante2026*` | Ver solo su propio avance |

Los tres estudiantes de prueba son casos reales **anonimizados**:

| Código | Caso |
|---|---|
| 20242001 (prueba1) | Ingresó en 2024-2S y va en curso. Tiene Inglés por suficiencia, materias repetidas y una fusión incompleta. Le conviene la malla 2026. |
| 20221001 (prueba2) | Ingresó en 2022-1S y lleva el 81 %. **No le conviene** la transición: en la 2026 terminaría con 2 créditos más. |
| 20261001 (prueba3) | Ingresó directamente en la malla 2026, así que no requiere transición. |

## Reglas de transición

Para cada materia **aprobada** del estudiante se busca su lugar en la malla vigente, en este orden:

| # | Situación | Resultado |
|---|---|---|
| 1 | Existe con el mismo código | **Directa**. Si cambió de créditos se indica. |
| 2 | Hay una equivalencia registrada | **Equivalencia**. Si varias materias apuntan a la misma nueva es una **fusión** y se exigen todas; si falta alguna, va a revisión. |
| 3 | Está en el catálogo de optativas | **Optativa**: ocupa un cupo de optativa de su grupo. |
| 4 | Ya no existe, o era de libre elección | **Libre elección**: ocupa un cupo con créditos **menores o iguales** (no se regalan créditos). |
| 5 | No cabe en ningún cupo | **Requiere revisión**: se abre **un ticket** por estudiante y materia. |

Además:

- Si la materia se repitió, cuenta el mejor intento aprobado.
- Las materias reprobadas o canceladas no cuentan.
- Las aprobadas sin nota, por suficiencia (SUF), sí cuentan.
- Lo que está **cursando** se muestra aparte y solo se usa para la proyección.
- Las materias de los pasos 3 a 5 se procesan de mayor a menor crédito, y cada una ocupa el cupo que menos créditos desperdicia.
- La **comparación de mallas** cuenta la malla de origen como lo hace la universidad en su reporte: las obligatorias materia por materia, y las optativas y la libre elección por bolsa de créditos. Con los estudiantes reales da exactamente las cifras oficiales.

## Arquitectura (limpia / hexagonal)

```
app/
├── domain/                         ← reglas de negocio puras (sin librerías externas)
│   ├── entities.py                   Estudiante, Malla, Materia, Equivalencia, Ticket, EventoAuditoria…
│   ├── exceptions.py                 errores de negocio
│   └── services/
│       ├── motor_transicion.py       ★ algoritmo de homologación
│       └── comparador_mallas.py      ¿le conviene la transición?
├── application/                    ← casos de uso + puertos (interfaces)
│   ├── ports.py                      RepositorioAcademico, RepositorioUsuarios, RepositorioAuditoria…
│   └── use_cases/
│       ├── autenticacion.py          IniciarSesion, ValidarToken
│       ├── estudiantes.py            consulta, ValidarMallaEstudiante, ConsultarMiAvance
│       ├── gestion_estudiantes.py    CRUD de estudiantes e historial (admin)
│       ├── gestion_usuarios.py       CRUD de usuarios (admin)
│       ├── tickets.py                listar y cerrar tickets
│       └── auditoria.py              Auditor (registra) y ListarAuditoria
├── infrastructure/                 ← implementaciones concretas
│   ├── config.py                     variables de entorno (.env)
│   ├── security/                     JWT (PyJWT) y bcrypt
│   ├── data_sources/                 Excel local / Drive / caché, lector y editor de Excel
│   └── repositories/                 Excel → entidades; tickets en JSON; auditoría en JSONL
├── presentation/
│   ├── api/                          FastAPI: routers auth, academico, admin, tickets
│   └── web/                          interfaz (HTML + CSS + módulos JS por vista)
└── bootstrap.py                    ← conecta todo según la configuración
scripts/
├── datos_ingenieria_quimica.py     ← mallas reales, catálogo, equivalencias y casos de prueba
├── crear_datos_ejemplo.py          ← genera los Excel (con hoja LEEME y listas desplegables)
├── generar_hash.py · probar_drive.py
tests/                              ← motor, casos reales y API de punta a punta
```

Las dependencias van **hacia adentro**: el dominio no conoce Excel, Drive ni HTTP. Para pasar a
una base de datos basta con escribir otro repositorio que cumpla el puerto.

## Estructura de los Excel

Cada archivo trae una hoja **LEEME** que explica todas sus columnas. Los encabezados no distinguen
mayúsculas ni tildes. Las filas en **amarillo** tienen datos por confirmar.

**usuarios.xlsx**, hoja `usuarios`:
`username | password_hash | nombre | rol (admin/consultor/estudiante) | activo (si/no) | codigo_estudiante`

**academico.xlsx**:

| Hoja | Columnas | Quién la mantiene |
|---|---|---|
| `estudiantes` | codigo, nombre, documento, correo, malla_version, estado | La aplicación (admin) |
| `materias_vistas` | codigo_estudiante, codigo_materia, nombre_materia, creditos, nota, estado, tipologia, periodo | La aplicación (admin) |
| `mallas` | version, semestre, codigo, nombre, creditos, tipo, grupo, observacion | Oficina académica |
| `equivalencias` | codigo_anterior, nombre_anterior, codigo_nuevo, nombre_nuevo, estado, observacion | Oficina académica |
| `optativas` | grupo, codigo, nombre | Oficina académica |

- **tipo** (mallas): `obligatoria`, `optativa` (cupo que se llena con el catálogo de su `grupo`),
  `electiva` (cupo de libre elección) o `nivelacion`.
- **estado** (materias_vistas): `aprobada`, `reprobada`, `cursando` o `cancelada`. Si se deja
  vacío, se deduce de la nota; sin nota se toma como cursando.

### Importar estudiantes desde Excel

Menú **Importar Excel** (solo el admin):

1. Descargue la plantilla.
2. Llénela con las hojas `estudiantes` y `materias_vistas`, con las mismas columnas de arriba.
3. Súbala y pulse **Validar**.

Reglas de la importación:

- **Validación previa:** el sistema revisa cada fila y muestra los errores con su hoja y número de fila. Si hay un solo error **no se guarda nada**.
- **Estudiantes:** si el código ya existe, sus datos se actualizan; si no, se crea.
- **Historial:** si un estudiante aparece en `materias_vistas`, su historial se **reemplaza completo** por el del archivo. Si solo aparece en `estudiantes`, su historial no se toca.
- **Una sola hoja:** puede subir solo `materias_vistas` para actualizar el historial de estudiantes que ya existen.
- **Cuentas:** opcionalmente, se le crea la cuenta a cada estudiante nuevo, con una contraseña inicial.
- **Auditoría:** la importación queda registrada.

### Pendiente de confirmar con la universidad

1. **Códigos de las materias nuevas.** Aparecen como `XXXXXX` en la malla 2026 y por ahora usan
   códigos temporales `NUEVO01`–`NUEVO08`: Química General, Balances, Laboratorio de
   Fisicoquímica, Fundamentos de Biotecnología, Programación y Métodos Numéricos, Transferencia de
   Masa I y II, y Seguridad de Procesos.
2. **Equivalencias.** Todas están cargadas como `propuesta`:
   - Fusiones: Química General I + II, y Programación + Métodos Numéricos.
   - Principios de los Procesos Químicos → Balances de Materia y Energía.
   - Fenómenos de Transferencia → Transferencia de Masa I.
   - Procesos de Separación → Transferencia de Masa II.
3. **Equivalencias que podría aprobar el comité** y que reducirían los tickets:
   - Higiene y Seguridad Industrial → Seguridad de Procesos Químicos.
   - Biología Celular o Bioquímica → Fundamentos de Biotecnología.
4. **Materias de 2 créditos que ya no existen** (Fundamentos de Economía, Biología, Cátedras de
   2 créditos). Siempre generan ticket, porque los cupos de libre elección de la malla 2026 son de
   3 créditos.

## Google Drive

1. En [Google Cloud Console](https://console.cloud.google.com/), activa la **Google Drive API** y
   crea una **cuenta de servicio**. Guarda su llave en `credenciales/service_account.json`.
2. **Sube los dos Excel** generados en `data/`, o reemplaza el contenido de los que ya tienes.
3. Comparte cada archivo con el correo de la cuenta de servicio:
   - como **Editor**, para que el administrador pueda registrar estudiantes y usuarios;
   - como **Lector**, si la aplicación solo va a consultar.
4. Configura el `.env`:
   ```
   FUENTE_DATOS=drive
   USUARIOS_EXCEL_LINK=https://docs.google.com/spreadsheets/d/XXXX/edit
   ACADEMICO_EXCEL_LINK=https://docs.google.com/spreadsheets/d/YYYY/edit
   ```
5. Verifica con `python scripts\probar_drive.py`.

Cómo funciona la conexión:

- **Lectura:** usa permiso de solo lectura. Los archivos se guardan en caché `CACHE_SEGUNDOS` segundos. Si Drive falla, se usa la última copia descargada.
- **Escritura:** pide permiso de escritura solo al guardar. Antes de modificar, descarga la versión más reciente.

## Ejecutable e instalador para Windows 11

No requiere instalar Python. Hay dos formas de usarlo:

| Archivo | Uso |
|---|---|
| `dist\TransicionMallas-2.0.1.msi` | **Instalador**: doble clic. Se instala para el usuario actual, sin permisos de administrador, y crea accesos directos en el menú Inicio y en el escritorio. |
| `dist\TransicionMallas\TransicionMallas.exe` | **Portable**: se copia la carpeta completa y se ejecuta el `.exe`. |

Cómo funciona el ejecutable:

- **Al abrirlo:** aparece una ventana con el estado y se abre el navegador en http://127.0.0.1:8000. Cerrar esa ventana detiene la aplicación.
- **Carpeta de datos:** `%LOCALAPPDATA%\TransicionMallas`. La primera vez se crean ahí el `.env` (con una clave aleatoria) y los Excel de prueba (`admin` / `Admin2025*`). Los datos se conservan al actualizar o desinstalar.
- **Usar Drive o los Excel reales:** edite el `.env` de esa carpeta y copie ahí la carpeta `credenciales\`.
- **Si el puerto 8000 está ocupado:** defina la variable de entorno `TRANSICION_PUERTO`.

Para volver a construir el instalador (requisitos en el encabezado del script):

```powershell
powershell -ExecutionPolicy Bypass -File empaquetado\construir.ps1 -Version 2.0.2
```

## Seguridad y auditoría

- Tokens JWT firmados con HS256 y con vencimiento. El algoritmo está fijo en el código, así que no se acepta `alg: none`.
- Contraseñas con bcrypt. La contraseña debe tener al menos 8 caracteres, con letras y números.
- El login responde el mismo error si el usuario no existe, está inactivo o la contraseña es incorrecta.
- Después de 5 intentos fallidos en 5 minutos (por IP y usuario), el login se bloquea temporalmente.
- **Roles:**
  - El CRUD lo hace solo el `admin`.
  - El `consultor` solo consulta.
  - El `estudiante` solo ve su avance (`/api/mi-avance`); su cuenta está atada a su código.
- **Protecciones del CRUD:**
  - El admin no puede borrarse ni quitarse el rol a sí mismo.
  - Siempre debe quedar un admin activo.
  - Al eliminar un estudiante se elimina su cuenta.
- **Auditoría** (`data/auditoria.jsonl`): registra inicios de sesión (también los fallidos),
  validaciones, cambios de estudiantes, historial y usuarios, y cierres de tickets, con usuario,
  fecha e IP. La aplicación solo agrega eventos: nunca los modifica ni los borra.
- `.env`, `credenciales/` y los datos de `data/` están en `.gitignore`. El servidor escucha solo en `127.0.0.1`.

## API

| Método | Ruta | Rol |
|---|---|---|
| POST | `/api/auth/login` (form: username, password) | — |
| GET | `/api/auth/yo` | cualquiera |
| GET | `/api/mallas` · `/api/mallas/vigente` · `/api/mallas/{version}` | cualquiera |
| GET | `/api/mi-avance` | estudiante |
| GET | `/api/estudiantes?q=` | admin, consultor |
| POST | `/api/estudiantes/{codigo}/validar-malla` | admin, consultor |
| POST · GET · PUT · DELETE | `/api/admin/estudiantes[/{codigo}]` | admin |
| PUT | `/api/admin/estudiantes/{codigo}/historial` | admin |
| GET · POST · PUT · DELETE | `/api/admin/usuarios[/{username}]` | admin |
| GET | `/api/admin/auditoria?usuario=&accion=&desde=` | admin |
| GET | `/api/tickets?estado=abierto\|cerrado` | admin |
| POST | `/api/tickets/{id}/cerrar` (json: resolucion) | admin |

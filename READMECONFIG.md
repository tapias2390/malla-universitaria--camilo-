1. Crear el usuario robot (cuenta de servicio)

Entra a https://console.cloud.google.com/ con ytapias2390@gmail.com, la cuenta dueña de los archivos.
Arriba, en el selector de proyectos, elige Nuevo proyecto y ponle de nombre camilo-universidad. Luego crear.
En el buscador de arriba escribe Google Drive API, entra y pulsa Habilitar.
En el buscador escribe Cuentas de servicio y entra.
Pulsa + Crear cuenta de servicio, ponle de nombre lector-app y pulsa Listo. No le asignes ningún rol. 2. Descargar la llave

Haz clic en la cuenta que creaste, ve a la pestaña Claves, luego Agregar clave → Crear clave nueva → JSON.
Se descarga un archivo .json.
Crea la carpeta C:\camiloUniversidad\credenciales\ y guarda ahí el archivo con el nombre service_account.json.
⚠️ Ese archivo es como una contraseña: no lo envíes por chat ni lo subas a ningún lado.

3. Compartir los 2 archivos con el robot

En la pestaña Detalles de la cuenta de servicio aparece un correo parecido a lector-app@camilo-universidad.iam.gserviceaccount.com. Cópialo.
Abre cada Excel en Drive, pulsa Compartir, pega ese correo, pon el permiso Lector, desmarca "Notificar" y pulsa Compartir.
El acceso general sigue en Restringido. 4. Activar y probar

En el archivo .env cambia FUENTE_DATOS=local por FUENTE_DATOS=drive.
Ejecuta:

.\.venv\Scripts\python scripts\probar_drive.py
Pégame lo que salga. Si aparece [OK] en todo, ya puedes correr python run.py y entrar con los usuarios de tu Excel.
Algo que me ayudaría mientras tanto
Desde aquí no puedo ver tus archivos, así que no sé si las pestañas y columnas coinciden con las que espera el código. Para revisarlo antes tienes dos opciones:

Abre cada Excel, ve a Archivo → Descargar → .xlsx y guárdalo en C:\camiloUniversidad\data\ con un nombre distinto, por ejemplo real_usuarios.xlsx y real_academico.xlsx. Yo reviso la estructura y, si hace falta, adapto el código a tus columnas.
O escríbeme los nombres de las pestañas y de las columnas que tiene cada uno.

image.png
1866×943
de donde lod escargo
9:42 PM
La cuenta de servicio quedó bien creada. Su correo es:

lector-ap@ultimate-result-468001-g8.iam.gserviceaccount.com

Cómo descargar la llave (JSON)
En la fila de lector-ap, haz clic en los tres puntos ⋮ de la columna Acciones, a la derecha.
Elige Administrar claves.
Haz clic en Agregar clave → Crear clave nueva.
Selecciona JSON y pulsa Crear.
El archivo .json se descarga solo, a tu carpeta de Descargas.
Muévelo a C:\camiloUniversidad\credenciales\ (crea la carpeta si no existe) y cámbiale el nombre a service_account.json.
Si al crear la clave aparece un error como "La creación de claves está inhabilitada por una política de la organización", mándame captura y te digo cómo desbloquearlo.

Después de descargar la llave
Comparte los 2 Excel con este correo, en cada archivo: Drive → Compartir → pegar el correo → permiso Lector → desmarcar "Notificar" → Compartir.

lector-ap@ultimate-result-468001-g8.iam.gserviceaccount.com
Habilita la API de Drive en este proyecto. Creaste la cuenta en el proyecto BookMy, así que la API tiene que estar habilitada ahí:

En el buscador de arriba escribe Google Drive API.
Pulsa Habilitar. Si ya dice "Administrar", es que ya está habilitada.
Activa Drive y prueba la conexión:

En el archivo .env cambia FUENTE_DATOS=local por FUENTE_DATOS=drive.

---

Abre el Excel en Drive (el de usuarios y el de estudiantes).
Pulsa Compartir, arriba a la derecha. Es la misma ventana de tu primera captura.
En "Añadir personas, grupos…" pega exactamente este correo:

lector-ap@ultimate-result-468001-g8.iam.gserviceaccount.com
A la derecha elige Lector.
Desmarca "Notificar a las personas". Ese correo no puede recibir emails, y si lo dejas marcado a veces sale un aviso.
Pulsa Compartir.
Comprueba que en "Personas con acceso" aparezcan tú como Propietario y lector-ap@… como Lecto

---

correr el proyecto
python run.py

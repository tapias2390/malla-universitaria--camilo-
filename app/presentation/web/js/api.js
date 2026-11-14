/* Cliente de la API. El token se guarda en sessionStorage: se borra al cerrar la pestaña. */

let token = null;
try { token = sessionStorage.getItem("token"); } catch { /* almacenamiento no disponible */ }

let alVencerSesion = () => {};

export function configurarSesionVencida(funcion) { alVencerSesion = funcion; }

export function guardarToken(nuevo) {
  token = nuevo;
  try { nuevo ? sessionStorage.setItem("token", nuevo) : sessionStorage.removeItem("token"); } catch { /* se ignora */ }
}

export const hayToken = () => Boolean(token);

/** Descarga un archivo protegido (con el token) y lo guarda con `nombre`. */
export async function descargar(ruta, nombre) {
  const respuesta = await fetch(ruta, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (respuesta.status === 401) { alVencerSesion(); throw new Error("Su sesión venció. Inicie sesión de nuevo."); }
  if (!respuesta.ok) throw new Error(`No se pudo descargar el archivo (código ${respuesta.status}).`);
  const url = URL.createObjectURL(await respuesta.blob());
  const enlace = Object.assign(document.createElement("a"), { href: url, download: nombre });
  document.body.append(enlace);
  enlace.click();
  enlace.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

/** Llama a la API y devuelve el JSON. Lanza Error con un mensaje claro si falla. */
export async function api(ruta, { metodo = "GET", json, form, archivos } = {}) {
  const opciones = { method: metodo, headers: {} };
  if (token) opciones.headers.Authorization = `Bearer ${token}`;
  if (json !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(json);
  } else if (archivos) {
    opciones.body = archivos;             // FormData: el navegador pone el Content-Type
  } else if (form) {
    opciones.body = new URLSearchParams(form);
  }

  let respuesta;
  try {
    respuesta = await fetch(ruta, opciones);
  } catch {
    throw new Error("No hay conexión con el servidor. ¿Está encendido?");
  }
  if (respuesta.status === 401 && ruta !== "/api/auth/login") {
    alVencerSesion();
    throw new Error("Su sesión venció. Inicie sesión de nuevo.");
  }
  if (respuesta.status === 204) return null;
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    throw new Error(typeof datos.detail === "string" ? datos.detail : `Error en la solicitud (código ${respuesta.status}).`);
  }
  return datos;
}

/* Punto de entrada del frontend: sesión, menú según el rol y navegación por #rutas. */
import { api, configurarSesionVencida, guardarToken, hayToken } from "./api.js";
import { mostrarLogin, prepararLogin } from "./login.js";
import { $, ETIQUETAS, errorCarga, esc } from "./ui.js";
import { vistaAuditoria } from "./vistas/auditoria.js";
import { vistaDetalleEstudiante, vistaEstudiantes } from "./vistas/estudiantes.js";
import { vistaImportar } from "./vistas/importar.js";
import { vistaMiAvance, vistaPanel } from "./vistas/inicio.js";
import { vistaMalla } from "./vistas/malla.js";
import { vistaTickets } from "./vistas/tickets.js";
import { vistaUsuarios } from "./vistas/usuarios.js";

const ICONO = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${d}</svg>`;
const ICONOS_MENU = {
  inicio: ICONO('<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/>'),
  avance: ICONO('<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>'),
  estudiantes: ICONO('<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20c.8-3.5 3.4-5.5 6.5-5.5s5.7 2 6.5 5.5"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7M21.5 20c-.5-2.6-2-4.3-4-5"/>'),
  malla: ICONO('<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>'),
  tickets: ICONO('<path d="M4 7a2 2 0 0 1 2-2h12a2 2 0 0 1 2 2v3a2 2 0 0 0 0 4v3a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-3a2 2 0 0 0 0-4Z"/><path d="M14 5v14" stroke-dasharray="2 2"/>'),
  usuarios: ICONO('<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>'),
  auditoria: ICONO('<path d="M9 4h6l1 2h3v15H5V6h3Z"/><path d="M9 12l2 2 4-4"/>'),
  importar: ICONO('<path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 17v3h16v-3"/>'),
};

// Qué ve cada rol en el menú (y a qué rutas puede entrar).
const MENU = {
  admin: [["inicio", "Inicio"], ["estudiantes", "Estudiantes"], ["importar", "Importar Excel"], ["malla", "Mallas"], ["tickets", "Tickets"], ["usuarios", "Usuarios"], ["auditoria", "Auditoría"]],
  consultor: [["inicio", "Inicio"], ["estudiantes", "Estudiantes"], ["malla", "Mallas"]],
  estudiante: [["mi-avance", "Mi avance"], ["malla", "Malla vigente"]],
};
const VISTAS = {
  inicio: vistaPanel, "mi-avance": vistaMiAvance, estudiantes: vistaEstudiantes, malla: vistaMalla,
  tickets: vistaTickets, usuarios: vistaUsuarios, auditoria: vistaAuditoria, importar: vistaImportar,
};

let sesion = null;

function salir() {
  guardarToken(null);
  sesion = null;
  history.replaceState(null, "", location.pathname);
  mostrarLogin();
}

async function entrar() {
  try { sesion = await api("/api/auth/yo"); } catch { return salir(); }
  $("#perfilNombre").textContent = sesion.nombre;
  $("#perfilRol").textContent = ETIQUETAS.rol[sesion.rol] || sesion.rol;
  $("#navegacion").innerHTML = MENU[sesion.rol].map(([ruta, texto]) => `
    <a href="#/${ruta}" data-ruta="${ruta}">${ICONOS_MENU[ruta === "mi-avance" ? "avance" : ruta]}<span>${esc(texto)}</span>
      ${ruta === "tickets" ? '<span class="contador oculto" id="contadorTickets"></span>' : ""}</a>`).join("");
  $("#vistaLogin").classList.add("oculto");
  $("#vistaApp").classList.remove("oculto");
  navegar();
}

async function navegar() {
  if (!sesion) return;
  const [ruta = "", parametro] = location.hash.replace(/^#\/?/, "").split("/").map(decodeURIComponent);
  const permitidas = MENU[sesion.rol].map(([r]) => r);
  if (!permitidas.includes(ruta)) {
    location.replace(`#/${permitidas[0]}`);
    return;
  }

  document.querySelectorAll("#navegacion a").forEach((a) => a.classList.toggle("activa", a.dataset.ruta === ruta));
  $("#menu").classList.remove("abierto");
  const contenido = $("#contenido");
  try {
    if (ruta === "estudiantes" && parametro) await vistaDetalleEstudiante(contenido, sesion, parametro);
    else await VISTAS[ruta](contenido, sesion);
  } catch (error) {
    contenido.innerHTML = errorCarga(error.message);
  }
  contenido.focus({ preventScroll: true });
  window.scrollTo(0, 0);
  if (sesion.rol === "admin") actualizarContadorTickets();
}

async function actualizarContadorTickets() {
  try {
    const abiertos = await api("/api/tickets?estado=abierto");
    const contador = $("#contadorTickets");
    if (!contador) return;
    contador.textContent = abiertos.length;
    contador.classList.toggle("oculto", abiertos.length === 0);
  } catch { /* el contador es informativo */ }
}

// ------------------------------------------------------------- arranque
configurarSesionVencida(salir);
prepararLogin(entrar);
$("#btnSalir").onclick = salir;
$("#btnMenu").onclick = () => $("#menu").classList.toggle("abierto");
window.addEventListener("hashchange", navegar);

if (hayToken()) entrar(); else mostrarLogin();

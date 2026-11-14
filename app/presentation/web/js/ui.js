/* Utilidades de interfaz compartidas por todas las vistas. */

export const $ = (selector, raiz = document) => raiz.querySelector(selector);
export const $$ = (selector, raiz = document) => [...raiz.querySelectorAll(selector)];

/** Escapa texto antes de insertarlo como HTML (evita inyección de código). */
export const esc = (valor) => String(valor ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// ------------------------------------------------------------- textos
export const ETIQUETAS = {
  homologacion: {
    directa: "Directa", equivalencia: "Equivalencia", optativa: "Optativa",
    reemplazo_electiva: "Libre elección", requiere_revision: "En revisión",
  },
  tipoMateria: { obligatoria: "Obligatorias", optativa: "Optativas", electiva: "Libre elección", nivelacion: "Nivelación" },
  tipoMateriaSingular: { obligatoria: "Obligatoria", optativa: "Optativa", electiva: "Libre elección", nivelacion: "Nivelación" },
  rol: { admin: "Administrador", consultor: "Consultor", estudiante: "Estudiante" },
  tipologia: {
    fund_obligatoria: "Fund. obligatoria", disciplinar_obligatoria: "Disc. obligatoria",
    fund_optativa: "Fund. optativa", disciplinar_optativa: "Disc. optativa",
    libre_eleccion: "Libre elección", nivelacion: "Nivelación", trabajo_de_grado: "Trabajo de grado",
  },
};

export const chip = (clase, texto) => `<span class="chip ${esc(clase)}">${esc(texto)}</span>`;
export const nota = (valor) => (valor === null || valor === undefined ? "—" : Number(valor).toFixed(1));
export const fecha = (iso) => new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });

export const cargando = (texto = "Cargando…") => `<div class="cargando">${esc(texto)}</div>`;
export const errorCarga = (mensaje) => `<div class="panel error-carga">${esc(mensaje)}</div>`;

export const ICONOS = {
  buscar: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
  ok: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></svg>',
  alerta: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M12 3 2 21h20Z"/><path d="M12 10v5M12 18h.01"/></svg>',
  info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/></svg>',
  borrar: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"/></svg>',
};

// ------------------------------------------------------------- avisos flotantes
export function toast(mensaje, tipo = "") {
  const caja = document.createElement("div");
  caja.className = `toast ${tipo}`;
  caja.textContent = mensaje;
  $("#toasts").append(caja);
  setTimeout(() => caja.remove(), tipo === "error" ? 6000 : 3500);
}

// ------------------------------------------------------------- modal
/**
 * Abre un formulario modal. `alAceptar(form)` puede ser async; si lanza un
 * error se muestra dentro del modal y el modal sigue abierto.
 */
export function abrirModal({ titulo, cuerpo, textoAceptar = "Guardar", peligro = false, alAceptar, alAbrir }) {
  const dialogo = $("#modal");
  $("#modalTitulo").textContent = titulo;
  $("#modalCuerpo").innerHTML = `${cuerpo}<div class="error-form" id="modalError" role="alert"></div>`;
  const aceptar = $("#modalAceptar");
  aceptar.textContent = textoAceptar;
  aceptar.className = peligro ? "peligro" : "";

  const cerrar = () => dialogo.close();
  $("#modalCerrar").onclick = cerrar;
  $("#modalCancelar").onclick = cerrar;
  $("#modalForm").onsubmit = async (evento) => {
    evento.preventDefault();
    aceptar.disabled = true;
    $("#modalError").textContent = "";
    try {
      await alAceptar($("#modalForm"));
      cerrar();
    } catch (error) {
      $("#modalError").textContent = error.message;
    } finally {
      aceptar.disabled = false;
    }
  };
  dialogo.showModal();
  alAbrir?.($("#modalForm"));
  $("input:not([type=hidden]):not([disabled]), select, textarea", $("#modalCuerpo"))?.focus();
}

export function confirmar({ titulo, mensaje, textoAceptar = "Eliminar", alAceptar }) {
  abrirModal({ titulo, cuerpo: `<p>${mensaje}</p>`, textoAceptar, peligro: true, alAceptar });
}

/** Lee los campos con atributo name de un formulario como objeto. */
export function datosFormulario(form) {
  const datos = {};
  $$("[name]", form).forEach((campo) => {
    datos[campo.name] = campo.type === "checkbox" ? campo.checked : campo.value.trim();
  });
  return datos;
}

export const campo = ({ nombre, etiqueta, valor = "", tipo = "text", ayuda = "", requerido = false, extra = "" }) => `
  <div class="campo-form">
    <label for="f_${nombre}">${esc(etiqueta)}${requerido ? " *" : ""}</label>
    <input id="f_${nombre}" name="${nombre}" type="${tipo}" value="${esc(valor)}" ${requerido ? "required" : ""} ${extra}>
    ${ayuda ? `<small>${esc(ayuda)}</small>` : ""}
  </div>`;

export const selector = ({ nombre, etiqueta, opciones, valor = "", ayuda = "" }) => `
  <div class="campo-form">
    <label for="f_${nombre}">${esc(etiqueta)}</label>
    <select id="f_${nombre}" name="${nombre}">
      ${opciones.map(([v, t]) => `<option value="${esc(v)}" ${String(v) === String(valor) ? "selected" : ""}>${esc(t)}</option>`).join("")}
    </select>
    ${ayuda ? `<small>${esc(ayuda)}</small>` : ""}
  </div>`;

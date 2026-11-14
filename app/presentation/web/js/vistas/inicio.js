/* Pantallas de entrada según el rol: panel del personal y "Mi avance" del estudiante. */
import { api } from "../api.js";
import { cargando, errorCarga, esc } from "../ui.js";
import { renderTransicion } from "./transicion.js";

export async function vistaPanel(raiz, sesion) {
  const esAdmin = sesion.rol === "admin";
  raiz.innerHTML = cargando();
  try {
    const [estudiantes, malla, tickets] = await Promise.all([
      api("/api/estudiantes"),
      api("/api/mallas/vigente"),
      esAdmin ? api("/api/tickets?estado=abierto") : [],
    ]);
    const porMalla = {};
    estudiantes.forEach((e) => { porMalla[e.malla_version] = (porMalla[e.malla_version] || 0) + 1; });
    const antiguos = estudiantes.filter((e) => e.malla_version !== malla.version && e.estado === "activo").length;

    raiz.innerHTML = `
      <div class="encabezado"><div><h1>Hola, ${esc(sesion.nombre.split(" ")[0])}</h1>
        <p>Transición de los estudiantes de Ingeniería Química a la malla ${esc(malla.version)}.</p></div></div>
      <div class="kpis">
        <div class="kpi destacado"><b>${esc(malla.version)}</b><span>Malla vigente · ${malla.creditos_totales} créditos</span></div>
        <div class="kpi"><b>${estudiantes.length}</b><span>Estudiantes registrados</span></div>
        <div class="kpi"><b>${antiguos}</b><span>Activos que deben pasar a la malla ${esc(malla.version)}</span></div>
        ${esAdmin ? `<div class="kpi ${tickets.length ? "alerta" : ""}"><b>${tickets.length}</b><span>Tickets abiertos</span></div>` : ""}
      </div>
      <div class="panel">
        <h2>¿Qué hacer?</h2>
        <p>Pasos para pasar a un estudiante a la malla vigente.</p>
        <ol style="line-height:1.9;margin:0;padding-left:20px">
          <li>Vaya a <a href="#/estudiantes">Estudiantes</a> y búsquelo por código, nombre o documento.</li>
          <li>Al abrirlo, el sistema calcula qué materias se reconocen, cuántos créditos lleva y cuántos le faltan.</li>
          <li>Las materias que no encuentran lugar abren un <b>ticket</b> automáticamente${esAdmin ? ', que se resuelve en <a href="#/tickets">Tickets</a>' : " para que el administrador lo revise"}.</li>
          ${esAdmin ? '<li>Registre estudiantes nuevos o corrija su historial desde su ficha; todo queda en la <a href="#/auditoria">Auditoría</a>.</li>' : ""}
        </ol>
      </div>
      <div class="panel"><h2>Estudiantes por malla</h2><p>Malla con la que ingresaron.</p>
        <div class="tipos">${Object.entries(porMalla).sort().map(([v, n]) => `
          <div class="tipo-fila"><span>Malla ${esc(v)}</span>
            <div class="progreso"><div style="width:${Math.round((100 * n) / estudiantes.length)}%"></div></div>
            <span class="valor">${n} ${n === 1 ? "estudiante" : "estudiantes"}</span></div>`).join("")}</div></div>`;
  } catch (error) { raiz.innerHTML = errorCarga(error.message); }
}

export async function vistaMiAvance(raiz) {
  raiz.innerHTML = cargando("Calculando tu avance…");
  try {
    const [r, malla] = await Promise.all([api("/api/mi-avance"), api("/api/mallas/vigente")]);
    raiz.innerHTML = `
      <div class="encabezado"><div><h1>Hola, ${esc(r.estudiante.nombre.split(" ")[0])}</h1>
        <p>Así vas en la malla ${esc(r.malla_vigente)} de Ingeniería Química · Código ${esc(r.estudiante.codigo)}</p></div></div>
      <div id="avance"></div>
      <p style="color:var(--suave);font-size:13px">Esta consulta es informativa. Si ves algo incorrecto en tu historial, comunícate con la dirección del programa.</p>`;
    renderTransicion(document.getElementById("avance"), r, malla, { esEstudiante: true });
  } catch (error) { raiz.innerHTML = errorCarga(error.message); }
}

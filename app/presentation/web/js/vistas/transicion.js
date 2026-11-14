/* Resultado de la transición de un estudiante: indicadores, malla visual y detalle por materia.
 * La usan el estudiante (Mi avance) y el personal académico (detalle de estudiante). */
import { $, $$, ETIQUETAS, ICONOS, chip, esc, nota } from "../ui.js";

/**
 * @param r      Respuesta de /validar-malla o /mi-avance
 * @param malla  Malla vigente (/api/mallas/vigente)
 * @param esEstudiante  Ajusta los textos a segunda persona
 */
export function renderTransicion(raiz, r, malla, { esEstudiante = false } = {}) {
  const c = r.creditos;
  const revision = r.homologaciones.filter((h) => h.tipo === "requiere_revision");

  raiz.innerHTML = `
    ${avisoPrincipal(r, esEstudiante)}

    <div class="kpis">
      <div class="kpi destacado"><b>${c.porcentaje_avance}%</b><span>Avance en la malla ${esc(r.malla_vigente)}</span>
        <div class="progreso"><div style="width:${Math.min(c.porcentaje_avance, 100)}%"></div></div></div>
      <div class="kpi"><b>${c.reconocidos}</b><span>Créditos reconocidos de ${c.requeridos}</span></div>
      <div class="kpi"><b>${c.pendientes}</b><span>Créditos pendientes</span></div>
      <div class="kpi"><b>${c.cursando}</b><span>Créditos cursando ahora</span></div>
      <div class="kpi ${revision.length ? "alerta" : ""}"><b>${revision.length}</b><span>Materias en revisión</span></div>
    </div>

    <div class="panel">
      <h2>Créditos por tipo</h2>
      <p>Lo que exige la malla ${esc(r.malla_vigente)} y lo que ya ${esEstudiante ? "tienes" : "tiene"} reconocido.</p>
      <div class="tipos">${c.por_tipo.map(filaTipo).join("")}</div>
    </div>

    <div class="panel">
      <h2>Malla ${esc(r.malla_vigente)}</h2>
      <p>Cada tarjeta es una materia o un cupo (optativa / libre elección) de la malla vigente.</p>
      <div class="leyenda">
        <span><i class="cubierta"></i>Reconocida</span><span><i class="cursando"></i>Cursando</span>
        <span><i class="pendiente"></i>Pendiente</span><span>Borde punteado = cupo</span>
      </div>
      <div class="malla-scroll">${mallaVisual(malla, r)}</div>
    </div>

    <div class="panel">
      <h2>Cómo se reconoció cada materia</h2>
      <p>Materias aprobadas en la malla ${esc(r.estudiante.malla_version)} y su lugar en la malla ${esc(r.malla_vigente)}.</p>
      <div class="fila" id="filtrosHomologacion" style="margin-bottom:12px">${filtros(r.homologaciones)}</div>
      <div class="tabla-scroll"><table>
        <thead><tr><th>Materia vista</th><th class="num">Cr.</th><th class="num">Nota</th><th>Resultado</th><th>En la malla ${esc(r.malla_vigente)}</th><th>Detalle</th></tr></thead>
        <tbody id="tablaHomologaciones">${r.homologaciones.map(filaHomologacion).join("")
          || `<tr><td colspan="6" class="vacio">Todavía no hay materias aprobadas.</td></tr>`}</tbody>
      </table></div>
    </div>

    ${r.materias_cursando.length ? listaMaterias("Cursando en este periodo", "No cuentan hasta que tengan nota aprobatoria.", r.materias_cursando) : ""}
    ${r.materias_no_aprobadas.length ? listaMaterias("Materias no aprobadas", "No se homologan.", r.materias_no_aprobadas) : ""}
    ${!esEstudiante && r.tickets.length ? panelTickets(r) : ""}
  `;

  $$("#filtrosHomologacion button", raiz).forEach((boton) => boton.onclick = () => {
    $$("#filtrosHomologacion button", raiz).forEach((b) => b.classList.toggle("sec", b !== boton));
    const tipo = boton.dataset.tipo;
    $$("#tablaHomologaciones tr[data-tipo]", raiz).forEach((tr) =>
      tr.classList.toggle("oculto", Boolean(tipo) && tr.dataset.tipo !== tipo));
  });
}

function avisoPrincipal(r, esEstudiante) {
  const c = r.comparacion;
  if (!r.requiere_transicion) {
    return `<div class="aviso info">${ICONOS.info}<div><b>${esEstudiante ? "Ya estás" : "Ya está"} en la malla vigente (${esc(r.malla_vigente)}).</b>
      No requiere transición: se muestra el avance sobre la malla nueva.</div></div>`;
  }
  if (!c) return "";
  const clase = c.conviene_transicion ? "ok" : "alerta";
  const icono = c.conviene_transicion ? ICONOS.ok : ICONOS.alerta;
  const [faltan, aprueba, esta] = esEstudiante ? ["te faltan", "apruebas", "estás"] : ["le faltan", "aprueba", "está"];
  return `<div class="aviso ${clase}">${icono}<div><b>${esc(esEstudiante ? c.recomendacion.replace("Le conviene", "Te conviene").replace("le faltarían", "te faltarían") : c.recomendacion)}</b>
    Hoy ${faltan} <b style="display:inline">${c.pendientes_origen}</b> créditos en la malla ${esc(c.malla_origen)} y
    <b style="display:inline">${c.pendientes_destino}</b> en la ${esc(c.malla_destino)}.
    Si ${aprueba} lo que ${esta} cursando: ${c.pendientes_origen_proyectado} frente a ${c.pendientes_destino_proyectado}.
    <br><small>Estimación orientativa; la decisión final es del comité.</small></div></div>`;
}

function filaTipo(t) {
  const porcentaje = t.requeridos ? Math.round((100 * t.reconocidos) / t.requeridos) : 0;
  return `<div class="tipo-fila">
    <span>${esc(ETIQUETAS.tipoMateria[t.tipo] || t.tipo)}</span>
    <div class="progreso" role="progressbar" aria-valuenow="${porcentaje}" aria-valuemin="0" aria-valuemax="100"><div style="width:${porcentaje}%"></div></div>
    <span class="valor">${t.reconocidos} / ${t.requeridos} cr.</span>
  </div>`;
}

function mallaVisual(malla, r) {
  const cubiertas = new Set(r.materias_cubiertas.map((m) => m.codigo));
  const cursando = new Set(r.materias_cursando.map((m) => m.codigo));
  const semestres = [...new Set(malla.materias.map((m) => m.semestre))].sort((a, b) => a - b);

  const tarjeta = (m) => {
    const estado = cubiertas.has(m.codigo) ? "cubierta" : cursando.has(m.codigo) ? "cursando" : "pendiente";
    const cupo = m.tipo === "electiva" || m.tipo === "optativa";
    return `<div class="materia ${estado} ${cupo ? "cupo" : ""}" title="${esc(m.observacion || ETIQUETAS.tipoMateriaSingular[m.tipo])}">
      <b>${esc(m.nombre)}</b>
      <small><span>${esc(cupo ? ETIQUETAS.tipoMateriaSingular[m.tipo] : m.codigo)}</span><span>${m.creditos} cr.</span></small>
    </div>`;
  };

  return `<div class="malla" style="--semestres:${semestres.length}">${semestres.map((s) => {
    const materias = malla.materias.filter((m) => m.semestre === s);
    const creditos = materias.reduce((suma, m) => suma + m.creditos, 0);
    return `<div class="semestre"><h4><span>Semestre ${s}</span><span>${creditos} cr.</span></h4>${materias.map(tarjeta).join("")}</div>`;
  }).join("")}</div>`;
}

function filtros(homologaciones) {
  const conteo = {};
  homologaciones.forEach((h) => { conteo[h.tipo] = (conteo[h.tipo] || 0) + 1; });
  const botones = [`<button class="mini" data-tipo="">Todas (${homologaciones.length})</button>`];
  Object.keys(ETIQUETAS.homologacion).forEach((tipo) => {
    if (conteo[tipo]) botones.push(`<button class="mini sec" data-tipo="${tipo}">${ETIQUETAS.homologacion[tipo]} (${conteo[tipo]})</button>`);
  });
  return botones.join("");
}

function filaHomologacion(h) {
  const v = h.materia_vista, d = h.materia_destino;
  return `<tr data-tipo="${esc(h.tipo)}">
    <td>${esc(v.nombre)}<span class="sub">${esc(v.codigo)} · ${esc(v.periodo)}</span></td>
    <td class="num">${v.creditos}</td><td class="num">${nota(v.nota)}</td>
    <td>${chip(h.tipo, ETIQUETAS.homologacion[h.tipo] || h.tipo)}</td>
    <td>${d ? `${esc(d.nombre)}<span class="sub">${esc(d.codigo)} · ${d.creditos} cr.</span>` : "—"}</td>
    <td>${esc(h.observacion)}</td>
  </tr>`;
}

function listaMaterias(titulo, descripcion, materias) {
  return `<div class="panel"><h2>${esc(titulo)}</h2><p>${esc(descripcion)}</p>
    <div class="tabla-scroll"><table>
      <thead><tr><th>Materia</th><th class="num">Cr.</th><th class="num">Nota</th><th>Periodo</th></tr></thead>
      <tbody>${materias.map((v) => `<tr><td>${esc(v.nombre)}<span class="sub">${esc(v.codigo)}</span></td>
        <td class="num">${v.creditos}</td><td class="num">${nota(v.nota)}</td><td>${esc(v.periodo)}</td></tr>`).join("")}</tbody>
    </table></div></div>`;
}

function panelTickets(r) {
  return `<div class="panel"><h2>Tickets de revisión</h2>
    <p>${r.tickets_nuevos ? `Se abrieron ${r.tickets_nuevos} tickets nuevos en esta validación.` : "Casos ya registrados para este estudiante."}</p>
    <div class="tabla-scroll"><table>
      <thead><tr><th>Materia</th><th>Motivo</th><th>Estado</th></tr></thead>
      <tbody>${r.tickets.map((t) => `<tr><td>${esc(t.nombre_materia)}<span class="sub">${esc(t.codigo_materia)} · ${t.creditos} cr.</span></td>
        <td>${esc(t.motivo)}</td><td>${chip(t.estado, t.estado)}</td></tr>`).join("")}</tbody>
    </table></div></div>`;
}

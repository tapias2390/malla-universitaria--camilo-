/* Mallas curriculares, en tres pestañas:
 *  1. PDF oficial: el documento de la malla tal como lo publica el programa (visor + descarga).
 *  2. Comparar: la malla anterior y la vigente, una encima de la otra, con colores que
 *     muestran qué se mantiene, qué cambia, qué se fusiona, qué se elimina y qué es nuevo.
 *     Al pasar el cursor por una materia se resalta su pareja en la otra malla.
 *  3. Ver una malla: detalle de una versión por semestre.
 * Los PDF están en web/documentos/ y se listan en documentos/mallas.json. */
import { api } from "../api.js";
import { $, $$, ETIQUETAS, cargando, chip, errorCarga, esc } from "../ui.js";

const esCupo = (m) => m.tipo === "electiva" || m.tipo === "optativa";

export async function vistaMalla(raiz) {
  raiz.innerHTML = `
    <div class="encabezado"><div><h1>Mallas curriculares</h1><p>Plan de estudios de Ingeniería Química.</p></div></div>
    <div class="pestanas" role="tablist">
      <button class="activa" data-modo="pdf" role="tab">PDF oficial</button>
      <button data-modo="comparar" role="tab">Comparar malla anterior y vigente</button>
      <button data-modo="una" role="tab">Ver una malla</button>
    </div>
    <section id="modoPdf">${cargando()}</section>
    <section id="modoComparar" class="oculto">${cargando()}</section>
    <section id="modoUna" class="oculto">${cargando()}</section>`;

  $$(".pestanas button", raiz).forEach((b) => b.onclick = () => {
    $$(".pestanas button", raiz).forEach((x) => x.classList.toggle("activa", x === b));
    $("#modoPdf").classList.toggle("oculto", b.dataset.modo !== "pdf");
    $("#modoComparar").classList.toggle("oculto", b.dataset.modo !== "comparar");
    $("#modoUna").classList.toggle("oculto", b.dataset.modo !== "una");
  });

  // Cada pestaña carga por su cuenta: si falla una, las demás siguen funcionando.
  await Promise.all([pestanaPdf($("#modoPdf")), pestanasDatos()]);
}

// ===================================================================== PDF oficial
async function pestanaPdf(caja) {
  let documentos;
  try {
    const respuesta = await fetch("documentos/mallas.json", { cache: "no-cache" });
    if (!respuesta.ok) throw new Error();
    documentos = await respuesta.json();
  } catch {
    caja.innerHTML = errorCarga("No se encontraron los PDF de las mallas (carpeta web/documentos).");
    return;
  }

  const iconoPdf = `<svg class="icono-pdf" viewBox="0 0 24 24" aria-hidden="true"><rect x="2" y="2" width="20" height="20" rx="4" fill="#e5322d"/>
    <text x="12" y="15.2" text-anchor="middle" font-size="7.2" font-weight="700" font-family="Arial, sans-serif" fill="#fff">PDF</text></svg>`;

  caja.innerHTML = `
    <div class="documentos">
      <div class="panel lista-archivos" role="listbox" aria-label="Documentos de las mallas">
        <h2>Documentos</h2>
        ${documentos.map((d, i) => `
          <button class="archivo" data-i="${i}" type="button" role="option">
            ${iconoPdf}<span><b>${esc(d.nombre)}</b><small>${esc(d.titulo)}</small></span>
          </button>`).join("")}
      </div>
      <div class="panel visor-pdf">
        <div class="encabezado" style="margin-bottom:12px">
          <div><h2 id="tituloPdf"></h2><p id="descripcionPdf"></p></div>
          <div class="fila">
            <a class="boton sec" id="abrirPdf" target="_blank" rel="noopener">Abrir en pestaña nueva</a>
            <a class="boton" id="descargarPdf" download>Descargar</a>
          </div>
        </div>
        <iframe id="marcoPdf" title="Malla curricular en PDF"></iframe>
        <p class="ayuda-pdf">¿No se ve el documento? Use “Abrir en pestaña nueva” o “Descargar”.</p>
      </div>
    </div>`;

  const mostrar = (i) => {
    const d = documentos[i];
    $$(".lista-archivos .archivo").forEach((b) => {
      const activo = Number(b.dataset.i) === i;
      b.classList.toggle("activo", activo);
      b.setAttribute("aria-selected", String(activo));
    });
    $("#tituloPdf").textContent = `${d.nombre} · ${d.titulo}`;
    $("#descripcionPdf").textContent = d.descripcion;
    $("#abrirPdf").href = d.archivo;
    $("#descargarPdf").href = d.archivo;
    $("#descargarPdf").setAttribute("download", d.nombre);
    $("#marcoPdf").src = `${d.archivo}#navpanes=0&view=FitH`;
  };
  $$(".lista-archivos .archivo").forEach((b) => b.onclick = () => mostrar(Number(b.dataset.i)));
  mostrar(0);
}

// ===================================================================== datos del sistema
async function pestanasDatos() {
  let versiones, vigente, equivalencias;
  try {
    [versiones, vigente, equivalencias] = await Promise.all([
      api("/api/mallas"), api("/api/mallas/vigente"), api("/api/equivalencias"),
    ]);
  } catch (error) {
    const mensaje = `${error.message} Si acaba de actualizar la aplicación, reinicie el servidor.`;
    $("#modoComparar").innerHTML = errorCarga(mensaje);
    $("#modoUna").innerHTML = errorCarga(mensaje);
    return;
  }

  const cache = new Map([[vigente.version, vigente]]);
  const obtener = async (v) => {
    if (!cache.has(v)) cache.set(v, await api(`/api/mallas/${encodeURIComponent(v)}`));
    return cache.get(v);
  };
  const opciones = (seleccion) => versiones.map((v) =>
    `<option value="${esc(v)}" ${v === seleccion ? "selected" : ""}>Malla ${esc(v)}${v === vigente.version ? " (vigente)" : ""}</option>`).join("");
  const anterior = versiones.filter((v) => v !== vigente.version).at(-1) || vigente.version;

  $("#modoComparar").innerHTML = `
    <div class="fila" style="margin-bottom:16px">
      <div><label for="verOrigen">Malla anterior</label><select id="verOrigen">${opciones(anterior)}</select></div>
      <span style="padding-top:22px;color:var(--suave)">→</span>
      <div><label for="verDestino">Malla nueva</label><select id="verDestino">${opciones(vigente.version)}</select></div>
    </div>
    <div id="comparacion"></div>`;
  $("#modoUna").innerHTML = `
    <div style="margin-bottom:16px"><label for="version">Versión</label>
      <select id="version" style="max-width:260px">${opciones(vigente.version)}</select></div>
    <div id="detalleMalla"></div>`;

  const comparar = async () => {
    const caja = $("#comparacion");
    caja.innerHTML = cargando();
    try {
      const [origen, destino] = await Promise.all([obtener($("#verOrigen").value), obtener($("#verDestino").value)]);
      renderComparacion(caja, origen, destino, equivalencias);
    } catch (error) { caja.innerHTML = errorCarga(error.message); }
  };
  const mostrarUna = async () => {
    const caja = $("#detalleMalla");
    caja.innerHTML = cargando();
    try { renderDetalle(caja, await obtener($("#version").value)); } catch (error) { caja.innerHTML = errorCarga(error.message); }
  };
  $("#verOrigen").onchange = comparar;
  $("#verDestino").onchange = comparar;
  $("#version").onchange = mostrarUna;
  await Promise.all([comparar(), mostrarUna()]);
}

// ===================================================================== comparación
function clasificar(origen, destino, equivalencias) {
  const concretasO = new Map(origen.materias.filter((m) => !esCupo(m)).map((m) => [m.codigo, m]));
  const concretasD = new Map(destino.materias.filter((m) => !esCupo(m)).map((m) => [m.codigo, m]));
  const eq = equivalencias.filter((e) => concretasO.has(e.codigo_anterior) && concretasD.has(e.codigo_nuevo));
  const nuevoDe = new Map(eq.map((e) => [e.codigo_anterior, e]));
  const fuentesDe = new Map();
  eq.forEach((e) => fuentesDe.set(e.codigo_nuevo, [...(fuentesDe.get(e.codigo_nuevo) || []), e]));

  const estadoOrigen = (m) => {
    if (esCupo(m)) return { clase: "cupo-neutro", grupo: `o-${m.codigo}`, etiqueta: ETIQUETAS.tipoMateriaSingular[m.tipo] };
    const d = concretasD.get(m.codigo);
    if (d) {
      return d.creditos === m.creditos
        ? { clase: "mantiene", grupo: m.codigo, etiqueta: "Se mantiene" }
        : { clase: "cambia", grupo: m.codigo, etiqueta: `Créditos ${m.creditos} → ${d.creditos}` };
    }
    const e = nuevoDe.get(m.codigo);
    if (e) {
      const n = concretasD.get(e.codigo_nuevo);
      const fusion = fuentesDe.get(e.codigo_nuevo).length > 1;
      return { clase: "equivale", grupo: `eq-${e.codigo_nuevo}`, etiqueta: `${fusion ? "Se fusiona en" : "Pasa a"}: ${n.nombre}`, propuesta: e.estado === "propuesta" };
    }
    return { clase: "eliminada", grupo: `o-${m.codigo}`, etiqueta: "Eliminada → libre elección" };
  };

  const estadoDestino = (m) => {
    if (esCupo(m)) return { clase: "cupo-neutro", grupo: `d-${m.codigo}`, etiqueta: ETIQUETAS.tipoMateriaSingular[m.tipo] };
    const o = concretasO.get(m.codigo);
    if (o) {
      return o.creditos === m.creditos
        ? { clase: "mantiene", grupo: m.codigo, etiqueta: "Se mantiene" }
        : { clase: "cambia", grupo: m.codigo, etiqueta: `Créditos ${o.creditos} → ${m.creditos}` };
    }
    const fuentes = fuentesDe.get(m.codigo);
    if (fuentes) {
      const nombres = fuentes.map((f) => concretasO.get(f.codigo_anterior).nombre).join(" + ");
      return { clase: "equivale", grupo: `eq-${m.codigo}`, etiqueta: `Viene de: ${nombres}`, propuesta: fuentes.some((f) => f.estado === "propuesta") };
    }
    return { clase: "nueva", grupo: `d-${m.codigo}`, etiqueta: "Materia nueva" };
  };

  return { estadoOrigen, estadoDestino, eq, concretasO, concretasD };
}

function renderComparacion(caja, origen, destino, equivalencias) {
  if (origen.version === destino.version) {
    caja.innerHTML = `<div class="aviso info"><div>Elija dos mallas diferentes para compararlas.</div></div>`;
    return;
  }
  const { estadoOrigen, estadoDestino } = clasificar(origen, destino, equivalencias);
  const estadosO = origen.materias.map((m) => ({ m, e: estadoOrigen(m) }));
  const estadosD = destino.materias.map((m) => ({ m, e: estadoDestino(m) }));
  const contar = (lista, clase) => lista.filter((x) => x.e.clase === clase).length;

  caja.innerHTML = `
    <div class="kpis">
      <div class="kpi destacado"><b>${origen.creditos_totales} → ${destino.creditos_totales}</b><span>Créditos totales (malla ${esc(origen.version)} → ${esc(destino.version)})</span></div>
      <div class="kpi"><b>${contar(estadosO, "mantiene")}</b><span>Se mantienen igual</span></div>
      <div class="kpi"><b>${contar(estadosO, "cambia")}</b><span>Cambian de créditos</span></div>
      <div class="kpi"><b>${contar(estadosO, "equivale")}</b><span>Pasan por equivalencia o fusión</span></div>
      <div class="kpi"><b>${contar(estadosO, "eliminada")}</b><span>Se eliminan</span></div>
      <div class="kpi"><b>${contar(estadosD, "nueva")}</b><span>Materias nuevas</span></div>
    </div>

    <div class="panel">
      <div class="leyenda">
        <span><i class="mantiene"></i>Se mantiene</span><span><i class="cambia"></i>Cambia de créditos</span>
        <span><i class="equivale"></i>Equivalencia / fusión</span><span><i class="eliminada"></i>Eliminada</span>
        <span><i class="nueva"></i>Nueva</span><span><i class="cupo-neutro"></i>Cupo (optativa / libre elección)</span>
      </div>
      <p style="margin:0 0 4px;color:var(--suave);font-size:13px">Pase el cursor (o toque) una materia para ver su pareja en la otra malla. * = equivalencia propuesta, pendiente de aval.</p>
    </div>

    <div class="panel">
      <h2>Malla ${esc(origen.version)} <span class="titulo-sub">· anterior · ${origen.creditos_totales} créditos</span></h2>
      <div class="malla-scroll" style="margin-top:12px">${grilla(estadosO)}</div>
    </div>
    <div class="panel">
      <h2>Malla ${esc(destino.version)} <span class="titulo-sub">· nueva · ${destino.creditos_totales} créditos</span></h2>
      <div class="malla-scroll" style="margin-top:12px">${grilla(estadosD)}</div>
    </div>

    <div class="rejilla">
      ${listaCambios("Materias que se eliminan", "Quien ya las vio las usa en un cupo de libre elección (o va a revisión).",
        estadosO.filter((x) => x.e.clase === "eliminada"), (x) => `${x.m.creditos} cr.`)}
      ${listaCambios("Materias nuevas", "Las deben ver todos los estudiantes que pasen a la malla nueva.",
        estadosD.filter((x) => x.e.clase === "nueva"), (x) => `${x.m.creditos} cr.`)}
      ${listaCambios("Cambian de créditos", "Mismo código, distinto número de créditos.",
        estadosD.filter((x) => x.e.clase === "cambia"), (x) => x.e.etiqueta.replace("Créditos ", ""))}
      ${listaCambios("Equivalencias y fusiones", "Materia nueva y de dónde viene.",
        estadosD.filter((x) => x.e.clase === "equivale"), (x) => `${x.e.etiqueta.replace("Viene de: ", "← ")}${x.e.propuesta ? " *" : ""}`)}
    </div>`;

  // Resaltar la pareja en la otra malla.
  const tarjetas = $$(".materia[data-grupo]", caja);
  const resaltar = (grupo) => tarjetas.forEach((t) => {
    t.classList.toggle("resaltada", grupo !== null && t.dataset.grupo === grupo);
    t.classList.toggle("atenuada", grupo !== null && t.dataset.grupo !== grupo);
  });
  tarjetas.forEach((t) => {
    t.onmouseenter = () => resaltar(t.dataset.grupo);
    t.onfocus = () => resaltar(t.dataset.grupo);
    t.onclick = () => resaltar(t.classList.contains("resaltada") && !t.matches(":hover") ? null : t.dataset.grupo);
  });
  $$(".malla", caja).forEach((m) => { m.onmouseleave = () => resaltar(null); });
}

function grilla(estados) {
  const semestres = [...new Set(estados.map((x) => x.m.semestre))].sort((a, b) => a - b);
  return `<div class="malla" style="--semestres:${semestres.length}">${semestres.map((s) => {
    const delSemestre = estados.filter((x) => x.m.semestre === s);
    const creditos = delSemestre.reduce((suma, x) => suma + x.m.creditos, 0);
    return `<div class="semestre"><h4><span>Semestre ${s}</span><span>${creditos} cr.</span></h4>
      ${delSemestre.map(({ m, e }) => `
        <div class="materia ${e.clase} ${esCupo(m) ? "cupo" : ""}" data-grupo="${esc(e.grupo)}" tabindex="0"
             title="${esc(`${m.nombre} (${m.codigo}) — ${e.etiqueta}${m.observacion ? ` — ${m.observacion}` : ""}`)}">
          <b>${esc(m.nombre)}</b>
          <small><span>${esc(esCupo(m) ? "Cupo" : m.codigo)}</span><span>${m.creditos} cr.</span></small>
          ${esCupo(m) ? "" : `<span class="etiqueta">${esc(e.etiqueta)}${e.propuesta ? " *" : ""}</span>`}
        </div>`).join("")}
    </div>`;
  }).join("")}</div>`;
}

function listaCambios(titulo, descripcion, filas, detalle) {
  return `<div class="panel" style="margin:0">
    <h2>${esc(titulo)} <span class="titulo-sub">(${filas.length})</span></h2><p>${esc(descripcion)}</p>
    ${filas.length ? `<table><tbody>${filas.map((x) => `<tr>
      <td>${esc(x.m.nombre)}<span class="sub">${esc(x.m.codigo)}</span></td><td class="detalle-cambio">${esc(detalle(x))}</td></tr>`).join("")}</tbody></table>`
      : `<p class="vacio" style="margin:0">Ninguna.</p>`}
  </div>`;
}

// ===================================================================== una sola malla
function renderDetalle(caja, malla) {
  const porTipo = {};
  malla.materias.forEach((m) => { porTipo[m.tipo] = (porTipo[m.tipo] || 0) + m.creditos; });
  const semestres = [...new Set(malla.materias.map((m) => m.semestre))].sort((a, b) => a - b);
  caja.innerHTML = `
    <div class="kpis">
      <div class="kpi destacado"><b>${malla.creditos_totales}</b><span>Créditos totales</span></div>
      ${Object.entries(porTipo).map(([t, c]) => `<div class="kpi"><b>${c}</b><span>${esc(ETIQUETAS.tipoMateria[t] || t)}</span></div>`).join("")}
    </div>
    ${semestres.map((s) => {
      const materias = malla.materias.filter((m) => m.semestre === s);
      return `<div class="panel"><h2>Semestre ${s} <span class="titulo-sub">· ${materias.reduce((a, m) => a + m.creditos, 0)} créditos</span></h2>
        <div class="tabla-scroll" style="margin-top:10px"><table>
          <thead><tr><th>Código</th><th>Materia</th><th>Tipo</th><th class="num">Créditos</th><th>Observación</th></tr></thead>
          <tbody>${materias.map((m) => `<tr><td>${esc(m.codigo)}</td><td>${esc(m.nombre)}</td>
            <td>${chip(m.tipo === "obligatoria" ? "neutro" : m.tipo === "electiva" ? "aviso" : "equivalencia", ETIQUETAS.tipoMateriaSingular[m.tipo] || m.tipo)}
              ${m.grupo ? `<span class="sub">${esc(m.grupo.replace("_", " "))}</span>` : ""}</td>
            <td class="num">${m.creditos}</td><td>${esc(m.observacion)}</td></tr>`).join("")}</tbody>
        </table></div></div>`;
    }).join("")}`;
}

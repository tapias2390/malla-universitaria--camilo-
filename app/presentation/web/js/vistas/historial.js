/* Editor del historial académico de un estudiante (solo admin).
 * Se edita en la tabla y se guarda todo junto; al escribir un código de las mallas
 * se completan nombre y créditos automáticamente. */
import { api } from "../api.js";
import { $, $$, ETIQUETAS, ICONOS, esc, toast } from "../ui.js";

const ESTADOS = ["aprobada", "reprobada", "cursando", "cancelada"];

export async function editorHistorial(raiz, estudiante, alGuardar) {
  let filas = estudiante.historial.map((m) => ({ ...m }));
  let catalogo = new Map();
  try {
    const versiones = await api("/api/mallas");
    const mallas = await Promise.all(versiones.map((v) => api(`/api/mallas/${encodeURIComponent(v)}`)));
    mallas.flatMap((m) => m.materias).filter((m) => !["electiva", "optativa"].includes(m.tipo))
      .forEach((m) => catalogo.set(m.codigo, m));
  } catch { catalogo = new Map(); }   // sin autocompletado, el editor sigue funcionando

  const opcionesTipologia = Object.entries(ETIQUETAS.tipologia);

  const fila = (m, i) => `<tr data-i="${i}">
    <td><input list="codigosMalla" data-campo="codigo" value="${esc(m.codigo)}" aria-label="Código" style="min-width:90px"></td>
    <td><input data-campo="nombre" value="${esc(m.nombre)}" aria-label="Nombre" style="min-width:200px"></td>
    <td><input data-campo="creditos" type="number" min="1" max="20" value="${esc(m.creditos)}" aria-label="Créditos" style="width:70px"></td>
    <td><input data-campo="nota" type="number" min="0" max="5" step="0.1" value="${m.nota ?? ""}" placeholder="—" aria-label="Nota" style="width:75px"></td>
    <td><select data-campo="estado" aria-label="Estado">${ESTADOS.map((e) => `<option ${e === m.estado ? "selected" : ""}>${e}</option>`).join("")}</select></td>
    <td><select data-campo="tipologia" aria-label="Tipología"><option value="">—</option>
      ${opcionesTipologia.map(([v, t]) => `<option value="${v}" ${v === m.tipologia ? "selected" : ""}>${t}</option>`).join("")}</select></td>
    <td><input data-campo="periodo" value="${esc(m.periodo)}" placeholder="2026-1S" aria-label="Periodo" style="width:95px"></td>
    <td><button type="button" class="icono" data-borrar="${i}" aria-label="Quitar materia">${ICONOS.borrar}</button></td>
  </tr>`;

  const pintar = () => {
    raiz.innerHTML = `
      <div class="panel">
        <div class="encabezado" style="margin-bottom:12px">
          <div><h2>Historial académico</h2><p>${filas.length} registros. Una fila por materia y periodo; si repitió una materia, agregue una fila por intento.
            Deje la nota vacía si fue por suficiencia o si la está cursando.</p></div>
          <div class="fila"><button class="sec" id="btnAgregar" type="button">+ Agregar materia</button>
            <button id="btnGuardarHistorial" type="button">Guardar historial</button></div>
        </div>
        <datalist id="codigosMalla">${[...catalogo.values()].map((m) => `<option value="${esc(m.codigo)}">${esc(m.nombre)}</option>`).join("")}</datalist>
        <div class="tabla-scroll"><table class="editable">
          <thead><tr><th>Código</th><th>Nombre</th><th>Cr.</th><th>Nota</th><th>Estado</th><th>Tipología</th><th>Periodo</th><th></th></tr></thead>
          <tbody>${filas.map(fila).join("") || `<tr><td colspan="8" class="vacio">Sin materias. Use “Agregar materia”.</td></tr>`}</tbody>
        </table></div>
      </div>`;

    $$("[data-campo]", raiz).forEach((control) => control.oninput = () => {
      const i = Number(control.closest("tr").dataset.i);
      filas[i][control.dataset.campo] = control.value;
      if (control.dataset.campo === "codigo" && catalogo.has(control.value.trim())) {
        const m = catalogo.get(control.value.trim());
        const tr = control.closest("tr");
        if (!filas[i].nombre) { filas[i].nombre = m.nombre; $("[data-campo=nombre]", tr).value = m.nombre; }
        if (!filas[i].creditos) { filas[i].creditos = m.creditos; $("[data-campo=creditos]", tr).value = m.creditos; }
      }
    });
    $$("[data-borrar]", raiz).forEach((b) => b.onclick = () => { filas.splice(Number(b.dataset.borrar), 1); pintar(); });
    $("#btnAgregar", raiz).onclick = () => {
      filas.push({ codigo: "", nombre: "", creditos: "", nota: null, estado: "aprobada", tipologia: "", periodo: "" });
      pintar();
      $$("[data-campo=codigo]", raiz).at(-1).focus();
    };
    $("#btnGuardarHistorial", raiz).onclick = guardar;
  };

  const guardar = async () => {
    const boton = $("#btnGuardarHistorial", raiz);
    boton.disabled = true;
    try {
      const materias = filas.map((m) => ({
        codigo: String(m.codigo).trim(),
        nombre: String(m.nombre ?? "").trim(),
        creditos: Number(m.creditos),
        nota: m.nota === "" || m.nota === null || m.nota === undefined ? null : Number(m.nota),
        estado: m.estado,
        tipologia: m.tipologia || "",
        periodo: String(m.periodo ?? "").trim(),
      }));
      const actualizado = await api(`/api/admin/estudiantes/${encodeURIComponent(estudiante.codigo)}/historial`,
        { metodo: "PUT", json: { materias } });
      filas = actualizado.historial.map((m) => ({ ...m }));
      pintar();
      toast("Historial guardado. La transición se recalculó.", "ok");
      await alGuardar(actualizado);
    } catch (error) {
      toast(error.message, "error");
    } finally {
      const b = $("#btnGuardarHistorial", raiz);
      if (b) b.disabled = false;
    }
  };

  pintar();
}

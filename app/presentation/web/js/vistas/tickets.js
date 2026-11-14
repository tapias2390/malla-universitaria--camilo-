/* Tickets de revisión (solo admin): casos que el motor no pudo resolver solo. */
import { api } from "../api.js";
import { $, $$, abrirModal, cargando, chip, datosFormulario, esc, fecha, toast } from "../ui.js";

export async function vistaTickets(raiz) {
  raiz.innerHTML = `
    <div class="encabezado">
      <div><h1>Tickets de revisión</h1><p>Materias que no encontraron lugar en la malla vigente. Revise cada caso y registre la decisión.</p></div>
      <div class="pestanas" style="margin:0;border:0">
        <button class="activa" data-estado="abierto">Abiertos</button><button data-estado="cerrado">Cerrados</button><button data-estado="">Todos</button>
      </div>
    </div>
    <div class="panel"><div class="tabla-scroll"><table>
      <thead><tr><th>Fecha</th><th>Estudiante</th><th>Materia</th><th>Motivo</th><th>Estado</th><th></th></tr></thead>
      <tbody id="tablaTickets"><tr><td colspan="6">${cargando()}</td></tr></tbody>
    </table></div></div>`;

  let estado = "abierto";
  const cargar = async () => {
    let lista;
    try { lista = await api(`/api/tickets${estado ? `?estado=${estado}` : ""}`); } catch (error) {
      $("#tablaTickets").innerHTML = `<tr><td colspan="6" class="error-carga">${esc(error.message)}</td></tr>`; return;
    }
    $("#tablaTickets").innerHTML = lista.map((t) => `<tr>
      <td>${esc(fecha(t.fecha_creacion))}</td>
      <td><a href="#/estudiantes/${encodeURIComponent(t.codigo_estudiante)}">${esc(t.codigo_estudiante)}</a></td>
      <td>${esc(t.nombre_materia)}<span class="sub">${esc(t.codigo_materia)} · ${t.creditos} cr.</span></td>
      <td>${esc(t.motivo)}${t.resolucion ? `<span class="sub"><b>Resolución:</b> ${esc(t.resolucion)} — ${esc(t.cerrado_por)}</span>` : ""}</td>
      <td>${chip(t.estado, t.estado)}</td>
      <td>${t.estado === "abierto" ? `<button class="mini" data-cerrar="${esc(t.id)}">Resolver</button>` : ""}</td>
    </tr>`).join("") || `<tr><td colspan="6" class="vacio">${estado === "abierto" ? "No hay casos pendientes. 🎉" : "No hay tickets."}</td></tr>`;

    $$("[data-cerrar]").forEach((b) => b.onclick = () => {
      const t = lista.find((x) => x.id === b.dataset.cerrar);
      abrirModal({
        titulo: "Resolver caso",
        textoAceptar: "Cerrar ticket",
        cuerpo: `<p><b>${esc(t.nombre_materia)}</b> (${esc(t.codigo_materia)}, ${t.creditos} cr.) — estudiante ${esc(t.codigo_estudiante)}</p>
          <p style="color:var(--suave);font-size:14px">${esc(t.motivo)}</p>
          <div class="campo-form"><label for="f_resolucion">Decisión tomada *</label>
            <textarea id="f_resolucion" name="resolucion" rows="4" required minlength="3"
              placeholder="Ej.: El comité la homologa como libre elección según acta 12 de 2026."></textarea></div>`,
        alAceptar: async (form) => {
          const { resolucion } = datosFormulario(form);
          if (resolucion.length < 3) throw new Error("Describa la decisión tomada.");
          await api(`/api/tickets/${encodeURIComponent(t.id)}/cerrar`, { metodo: "POST", json: { resolucion } });
          toast("Ticket cerrado.", "ok"); cargar();
        },
      });
    });
  };

  $$(".encabezado .pestanas button").forEach((b) => b.onclick = () => {
    $$(".encabezado .pestanas button").forEach((x) => x.classList.toggle("activa", x === b));
    estado = b.dataset.estado; cargar();
  });
  await cargar();
}

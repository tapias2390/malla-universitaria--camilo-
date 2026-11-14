/* Auditoría (solo admin): quién hizo qué y cuándo. Los eventos no se pueden editar ni borrar. */
import { api } from "../api.js";
import { $, cargando, chip, esc, fecha } from "../ui.js";

const ACCIONES = {
  login: "Inicio de sesión", login_fallido: "Intento fallido de sesión", validar_malla: "Validó transición",
  crear_estudiante: "Registró estudiante", actualizar_estudiante: "Editó estudiante", eliminar_estudiante: "Eliminó estudiante",
  actualizar_historial: "Editó historial", crear_usuario: "Creó usuario", actualizar_usuario: "Editó usuario",
  eliminar_usuario: "Eliminó usuario", cerrar_ticket: "Cerró ticket",
};

export async function vistaAuditoria(raiz) {
  raiz.innerHTML = `
    <div class="encabezado"><div><h1>Auditoría</h1><p>Registro inalterable de las operaciones del sistema (más recientes primero).</p></div></div>
    <div class="panel">
      <div class="fila" style="margin-bottom:14px">
        <div class="crece"><label for="filtroUsuario">Usuario</label><input id="filtroUsuario" placeholder="Todos"></div>
        <div class="crece"><label for="filtroAccion">Acción</label><select id="filtroAccion"><option value="">Todas</option>
          ${Object.entries(ACCIONES).map(([v, t]) => `<option value="${v}">${t}</option>`).join("")}</select></div>
        <div class="crece"><label for="filtroDesde">Desde</label><input id="filtroDesde" type="date"></div>
      </div>
      <div class="tabla-scroll"><table>
        <thead><tr><th>Fecha</th><th>Usuario</th><th>Acción</th><th>Sobre</th><th>Detalle</th><th>IP</th></tr></thead>
        <tbody id="tablaAuditoria"><tr><td colspan="6">${cargando()}</td></tr></tbody>
      </table></div>
    </div>`;

  let espera;
  const cargar = async () => {
    const parametros = new URLSearchParams({ limite: "300" });
    if ($("#filtroUsuario").value.trim()) parametros.set("usuario", $("#filtroUsuario").value.trim());
    if ($("#filtroAccion").value) parametros.set("accion", $("#filtroAccion").value);
    if ($("#filtroDesde").value) parametros.set("desde", `${$("#filtroDesde").value}T00:00:00`);
    try {
      const eventos = await api(`/api/admin/auditoria?${parametros}`);
      $("#tablaAuditoria").innerHTML = eventos.map((e) => `<tr>
        <td style="white-space:nowrap">${esc(fecha(e.fecha))}</td>
        <td><b>${esc(e.usuario)}</b>${e.rol ? `<span class="sub">${esc(e.rol)}</span>` : ""}</td>
        <td>${chip(e.exito ? "neutro" : "error", ACCIONES[e.accion] || e.accion)}</td>
        <td>${esc(e.entidad)}${e.entidad_id ? `<span class="sub">${esc(e.entidad_id)}</span>` : ""}</td>
        <td>${esc(e.detalle)}</td><td>${esc(e.ip)}</td>
      </tr>`).join("") || `<tr><td colspan="6" class="vacio">No hay eventos con esos filtros.</td></tr>`;
    } catch (error) {
      $("#tablaAuditoria").innerHTML = `<tr><td colspan="6" class="error-carga">${esc(error.message)}</td></tr>`;
    }
  };
  $("#filtroUsuario").oninput = () => { clearTimeout(espera); espera = setTimeout(cargar, 300); };
  $("#filtroAccion").onchange = cargar;
  $("#filtroDesde").onchange = cargar;
  await cargar();
}

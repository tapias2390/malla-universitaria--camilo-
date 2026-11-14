/* Importar estudiantes e historial desde un Excel (solo admin).
 * Paso 1: descargar plantilla · Paso 2: subir y validar · Paso 3: confirmar. Nada se guarda sin confirmar. */
import { api, descargar } from "../api.js";
import { $, chip, esc, toast } from "../ui.js";

const ACCIONES = { nuevo: ["ok", "Nuevo"], actualizado: ["info", "Se actualiza"], solo_historial: ["equivalencia", "Solo historial"] };

export async function vistaImportar(raiz) {
  raiz.innerHTML = `
    <div class="migas"><a href="#/estudiantes">← Estudiantes</a></div>
    <div class="encabezado"><div><h1>Importar estudiantes desde Excel</h1>
      <p>Registre o actualice muchos estudiantes y su historial de una sola vez. Nada se guarda hasta que usted confirme.</p></div></div>

    <div class="rejilla">
      <div class="panel" style="margin:0">
        <h2>1. Descargue la plantilla</h2>
        <p>Trae las hojas <b>estudiantes</b> y <b>materias_vistas</b>, ejemplos y una hoja LEEME con cada columna explicada.</p>
        <button class="sec" id="btnPlantilla" type="button">Descargar plantilla (.xlsx)</button>
      </div>
      <div class="panel" style="margin:0">
        <h2>2. Suba el archivo lleno</h2>
        <p>El sistema revisa cada fila y le dice exactamente qué corregir.</p>
        <input type="file" id="archivo" accept=".xlsx" aria-label="Archivo de Excel">
        <div class="campo-form" style="margin-top:12px">
          <label for="passwordCuentas">Contraseña inicial para estudiantes nuevos (opcional)</label>
          <input id="passwordCuentas" type="password" autocomplete="new-password">
          <small>Si la escribe, a cada estudiante nuevo se le crea su usuario (usuario = código) con esta contraseña.</small>
        </div>
        <button id="btnValidar" type="button" disabled>Validar archivo</button>
      </div>
    </div>

    <div class="aviso info" style="margin-top:16px">
      <div><b>Reglas importantes</b>
        Si el código ya existe, los datos del estudiante se <b style="display:inline">actualizan</b>; si no, se crea.
        Si un estudiante aparece en <i>materias_vistas</i>, su historial se <b style="display:inline">reemplaza completo</b> por el del archivo;
        si solo aparece en <i>estudiantes</i>, su historial no se toca. Si hay un solo error, no se guarda nada.</div>
    </div>

    <div id="resultado"></div>`;

  $("#btnPlantilla").onclick = async () => {
    try { await descargar("/api/admin/importacion/plantilla", "plantilla_importar_estudiantes.xlsx"); }
    catch (error) { toast(error.message, "error"); }
  };
  $("#archivo").onchange = () => { $("#btnValidar").disabled = !$("#archivo").files.length; $("#resultado").innerHTML = ""; };
  $("#btnValidar").onclick = () => enviar(false);

  async function enviar(aplicar) {
    const archivo = $("#archivo").files[0];
    if (!archivo) return;
    const datos = new FormData();
    datos.append("archivo", archivo);
    datos.append("password_cuentas", $("#passwordCuentas").value);
    const boton = aplicar ? $("#btnAplicar") : $("#btnValidar");
    boton.disabled = true;
    try {
      const r = await api(`/api/admin/importacion/${aplicar ? "aplicar" : "validar"}`, { metodo: "POST", archivos: datos });
      mostrar(r, archivo.name);
      if (r.aplicado) toast(`Importación lista: ${r.nuevos} nuevos y ${r.actualizados} actualizados.`, "ok");
    } catch (error) {
      toast(error.message, "error");
    } finally {
      boton.disabled = false;
    }
  }

  function mostrar(r, nombreArchivo) {
    const caja = $("#resultado");
    const tabla = `<div class="tabla-scroll"><table>
      <thead><tr><th>Código</th><th>Nombre</th><th>Acción</th><th>Malla</th><th class="num">Materias</th>
        <th class="num">Aprobadas</th><th class="num">Cursando</th><th>Historial</th><th>Cuenta</th></tr></thead>
      <tbody>${r.estudiantes.map((e) => `<tr>
        <td>${r.aplicado ? `<a href="#/estudiantes/${encodeURIComponent(e.codigo)}">${esc(e.codigo)}</a>` : esc(e.codigo)}</td>
        <td>${esc(e.nombre)}</td><td>${chip(...ACCIONES[e.accion])}</td><td>${esc(e.malla_version)}</td>
        <td class="num">${e.materias}</td><td class="num">${e.aprobadas}</td><td class="num">${e.cursando}</td>
        <td>${e.reemplaza_historial ? "Se reemplaza" : "Sin cambios"}</td>
        <td>${e.crea_cuenta ? chip("ok", "Se crea") : "—"}</td></tr>`).join("")
        || `<tr><td colspan="9" class="vacio">No hay estudiantes válidos en el archivo.</td></tr>`}</tbody>
    </table></div>`;

    if (r.aplicado) {
      caja.innerHTML = `
        <div class="aviso ok" style="margin-top:16px"><div><b>Importación completada.</b>
          ${r.nuevos} estudiantes nuevos, ${r.actualizados} actualizados y ${r.total_materias} materias guardadas.
          Quedó registrado en la auditoría. Abra cada estudiante para ver su transición.</div></div>
        <div class="panel">${tabla}</div>`;
      $("#archivo").value = ""; $("#btnValidar").disabled = true;
      return;
    }

    if (r.errores.length) {
      caja.innerHTML = `
        <div class="aviso alerta" style="margin-top:16px"><div><b>El archivo tiene ${r.errores.length} ${r.errores.length === 1 ? "error" : "errores"}.</b>
          Corríjalos en <i>${esc(nombreArchivo)}</i> y vuelva a subirlo. No se guardó nada.</div></div>
        <div class="panel"><h2>Errores</h2>
          <div class="tabla-scroll"><table><thead><tr><th>Hoja</th><th class="num">Fila</th><th>Qué corregir</th></tr></thead>
          <tbody>${r.errores.map((e) => `<tr><td>${esc(e.hoja)}</td><td class="num">${e.fila || "—"}</td><td>${esc(e.mensaje)}</td></tr>`).join("")}</tbody>
          </table></div></div>
        ${r.estudiantes.length ? `<div class="panel"><h2>Filas sin errores</h2><p>Así quedarían una vez corregidos los errores.</p>${tabla}</div>` : ""}`;
      return;
    }

    caja.innerHTML = `
      <div class="aviso ok" style="margin-top:16px"><div><b>El archivo está correcto.</b>
        Se van a crear ${r.nuevos} estudiantes, actualizar ${r.actualizados} y guardar ${r.total_materias} materias.</div></div>
      <div class="panel">
        <div class="encabezado" style="margin-bottom:12px"><div><h2>3. Revise y confirme</h2></div>
          <button id="btnAplicar" type="button">Importar ${r.estudiantes.length} estudiantes</button></div>
        ${tabla}
      </div>`;
    $("#btnAplicar").onclick = () => enviar(true);
  }
}

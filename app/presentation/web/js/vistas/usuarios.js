/* Usuarios del sistema (solo admin): crear, editar, activar/desactivar y eliminar. */
import { api } from "../api.js";
import { $, $$, ETIQUETAS, abrirModal, campo, cargando, chip, confirmar, datosFormulario, esc, selector, toast } from "../ui.js";

export async function vistaUsuarios(raiz, sesion) {
  raiz.innerHTML = `
    <div class="encabezado">
      <div><h1>Usuarios</h1><p>Quién puede entrar y qué puede hacer. Solo el administrador ve esta sección.</p></div>
      <button id="btnNuevoUsuario">+ Nuevo usuario</button>
    </div>
    <div class="rejilla" style="margin-bottom:16px">
      <div class="aviso info" style="margin:0"><div><b>Administrador</b>Todo: estudiantes, historial, usuarios, tickets y auditoría.</div></div>
      <div class="aviso info" style="margin:0"><div><b>Consultor</b>Busca estudiantes y valida su transición. No modifica datos.</div></div>
      <div class="aviso info" style="margin:0"><div><b>Estudiante</b>Solo ve su propio avance en la malla vigente.</div></div>
    </div>
    <div class="panel"><div class="tabla-scroll"><table>
      <thead><tr><th>Usuario</th><th>Nombre</th><th>Rol</th><th>Estudiante</th><th>Estado</th><th></th></tr></thead>
      <tbody id="tablaUsuarios"><tr><td colspan="6">${cargando()}</td></tr></tbody>
    </table></div></div>`;

  let usuarios = [];
  const cargar = async () => {
    try { usuarios = await api("/api/admin/usuarios"); } catch (error) {
      $("#tablaUsuarios").innerHTML = `<tr><td colspan="6" class="error-carga">${esc(error.message)}</td></tr>`; return;
    }
    $("#tablaUsuarios").innerHTML = usuarios.map((u) => `<tr>
      <td><b>${esc(u.username)}</b>${u.username === sesion.username ? '<span class="sub">(usted)</span>' : ""}</td>
      <td>${esc(u.nombre)}</td><td>${chip(u.rol, ETIQUETAS.rol[u.rol])}</td>
      <td>${u.codigo_estudiante ? `<a href="#/estudiantes/${encodeURIComponent(u.codigo_estudiante)}">${esc(u.codigo_estudiante)}</a>` : "—"}</td>
      <td>${chip(u.activo ? "activo" : "inactivo", u.activo ? "Activo" : "Inactivo")}</td>
      <td class="num"><button class="sec mini" data-editar="${esc(u.username)}">Editar</button>
        ${u.username !== sesion.username ? `<button class="peligro mini" data-eliminar="${esc(u.username)}">Eliminar</button>` : ""}</td>
    </tr>`).join("") || `<tr><td colspan="6" class="vacio">No hay usuarios.</td></tr>`;

    $$("[data-editar]").forEach((b) => b.onclick = () => formulario(usuarios.find((u) => u.username === b.dataset.editar)));
    $$("[data-eliminar]").forEach((b) => b.onclick = () => confirmar({
      titulo: "Eliminar usuario",
      mensaje: `El usuario <b>${esc(b.dataset.eliminar)}</b> ya no podrá entrar. Si solo quiere suspenderlo, edítelo y desactívelo.`,
      alAceptar: async () => {
        await api(`/api/admin/usuarios/${encodeURIComponent(b.dataset.eliminar)}`, { metodo: "DELETE" });
        toast("Usuario eliminado.", "ok"); cargar();
      },
    }));
  };

  const formulario = (actual) => {
    const nuevo = !actual;
    abrirModal({
      titulo: nuevo ? "Nuevo usuario" : `Editar ${actual.username}`,
      cuerpo: `
        <div class="form-rejilla">
          ${campo({ nombre: "username", etiqueta: "Usuario", valor: actual?.username, requerido: true,
                    extra: nuevo ? 'autocomplete="off"' : "disabled", ayuda: nuevo ? "Minúsculas, sin espacios." : "" })}
          ${selector({ nombre: "rol", etiqueta: "Rol", valor: actual?.rol || "consultor",
                       opciones: Object.entries(ETIQUETAS.rol) })}
        </div>
        ${campo({ nombre: "nombre", etiqueta: "Nombre", valor: actual?.nombre, requerido: true })}
        <div id="campoEstudiante">${campo({ nombre: "codigo_estudiante", etiqueta: "Código del estudiante", valor: actual?.codigo_estudiante,
                                             ayuda: "La cuenta solo verá el avance de este estudiante." })}</div>
        ${campo({ nombre: "password", etiqueta: nuevo ? "Contraseña" : "Nueva contraseña", tipo: "password", requerido: nuevo,
                  extra: 'autocomplete="new-password"',
                  ayuda: nuevo ? "Mínimo 8 caracteres, con letras y números." : "Déjela vacía para no cambiarla." })}
        <label class="casilla"><input type="checkbox" name="activo" ${actual?.activo === false ? "" : "checked"}> Usuario activo (puede iniciar sesión)</label>`,
      alAbrir: (form) => {
        const sincronizar = () => $("#campoEstudiante", form).classList.toggle("oculto", $("[name=rol]", form).value !== "estudiante");
        $("[name=rol]", form).onchange = sincronizar;
        sincronizar();
      },
      alAceptar: async (form) => {
        const datos = datosFormulario(form);
        if (nuevo) await api("/api/admin/usuarios", { metodo: "POST", json: datos });
        else {
          const { username, ...cambios } = datos;
          await api(`/api/admin/usuarios/${encodeURIComponent(actual.username)}`, { metodo: "PUT", json: cambios });
        }
        toast(nuevo ? "Usuario creado." : "Usuario actualizado.", "ok");
        cargar();
      },
    });
  };

  $("#btnNuevoUsuario").onclick = () => formulario(null);
  await cargar();
}

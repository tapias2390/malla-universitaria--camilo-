/* Estudiantes: búsqueda, ficha con su transición y, para el admin, registro / edición / historial. */
import { api } from "../api.js";
import {
  $, $$, ICONOS, abrirModal, campo, cargando, chip, confirmar, datosFormulario, errorCarga, esc, selector, toast,
} from "../ui.js";
import { editorHistorial } from "./historial.js";
import { renderTransicion } from "./transicion.js";

const ESTADOS = [["activo", "Activo"], ["inactivo", "Inactivo"], ["graduado", "Graduado"], ["retirado", "Retirado"]];

// ===================================================================== lista
export async function vistaEstudiantes(raiz, sesion) {
  const esAdmin = sesion.rol === "admin";
  raiz.innerHTML = `
    <div class="encabezado">
      <div><h1>Estudiantes</h1><p>Busque un estudiante para ver cómo queda en la malla vigente.</p></div>
      ${esAdmin ? `<div class="fila"><a class="boton sec" href="#/importar">Importar desde Excel</a>
        <button id="btnNuevo">+ Registrar estudiante</button></div>` : ""}
    </div>
    <div class="panel">
      <div class="buscador" style="margin-bottom:14px">${ICONOS.buscar}
        <input id="buscar" type="search" placeholder="Buscar por código, nombre o documento" aria-label="Buscar estudiante"></div>
      <div class="tabla-scroll"><table>
        <thead><tr><th>Código</th><th>Nombre</th><th>Documento</th><th>Malla</th><th>Estado</th></tr></thead>
        <tbody id="tablaEstudiantes"><tr><td colspan="5">${cargando()}</td></tr></tbody>
      </table></div>
    </div>`;

  let espera;
  const buscar = async () => {
    try {
      const lista = await api(`/api/estudiantes?q=${encodeURIComponent($("#buscar").value)}`);
      $("#tablaEstudiantes").innerHTML = lista.map((e) => `
        <tr class="click" data-codigo="${esc(e.codigo)}" tabindex="0">
          <td><b>${esc(e.codigo)}</b></td><td>${esc(e.nombre)}<span class="sub">${esc(e.correo)}</span></td>
          <td>${esc(e.documento)}</td><td>${esc(e.malla_version)}</td><td>${chip(e.estado, e.estado)}</td>
        </tr>`).join("") || `<tr><td colspan="5" class="vacio">No hay estudiantes que coincidan.</td></tr>`;
      $$("#tablaEstudiantes tr.click").forEach((tr) => {
        const abrir = () => { location.hash = `#/estudiantes/${encodeURIComponent(tr.dataset.codigo)}`; };
        tr.onclick = abrir;
        tr.onkeydown = (e) => e.key === "Enter" && abrir();
      });
    } catch (error) {
      $("#tablaEstudiantes").innerHTML = `<tr><td colspan="5" class="error-carga">${esc(error.message)}</td></tr>`;
    }
  };
  $("#buscar").oninput = () => { clearTimeout(espera); espera = setTimeout(buscar, 250); };
  if (esAdmin) $("#btnNuevo").onclick = () => formularioEstudiante(null, (e) => { location.hash = `#/estudiantes/${encodeURIComponent(e.codigo)}`; });
  await buscar();
  $("#buscar").focus();
}

// ===================================================================== ficha
export async function vistaDetalleEstudiante(raiz, sesion, codigo) {
  const esAdmin = sesion.rol === "admin";
  raiz.innerHTML = cargando("Calculando la transición…");

  let estudiante, malla;
  try {
    [estudiante, malla] = await Promise.all([
      esAdmin ? api(`/api/admin/estudiantes/${encodeURIComponent(codigo)}`) : null,
      api("/api/mallas/vigente"),
    ]);
  } catch (error) { raiz.innerHTML = errorCarga(error.message); return; }

  const pintar = () => {
    raiz.innerHTML = `
      <div class="migas"><a href="#/estudiantes">← Estudiantes</a></div>
      <div class="encabezado">
        <div><h1 id="tituloEstudiante">${esc(estudiante?.nombre || codigo)}</h1><p id="datosEstudiante"></p></div>
        ${esAdmin ? `<div class="fila"><button class="sec" id="btnEditar">Editar datos</button>
          <button class="peligro" id="btnEliminar">Eliminar</button></div>` : ""}
      </div>
      <div class="pestanas" role="tablist">
        <button class="activa" data-pestana="transicion" role="tab">Transición a la malla vigente</button>
        ${esAdmin ? `<button data-pestana="historial" role="tab">Historial académico</button>` : ""}
      </div>
      <section id="pestanaTransicion">${cargando("Calculando la transición…")}</section>
      <section id="pestanaHistorial" class="oculto"></section>`;

    $$(".pestanas button").forEach((b) => b.onclick = () => {
      $$(".pestanas button").forEach((x) => x.classList.toggle("activa", x === b));
      $("#pestanaTransicion").classList.toggle("oculto", b.dataset.pestana !== "transicion");
      $("#pestanaHistorial").classList.toggle("oculto", b.dataset.pestana !== "historial");
    });

    if (esAdmin) {
      $("#btnEditar").onclick = () => formularioEstudiante(estudiante, (e) => { estudiante = { ...estudiante, ...e }; pintar(); });
      $("#btnEliminar").onclick = () => confirmar({
        titulo: "Eliminar estudiante",
        mensaje: `Se eliminará a <b>${esc(estudiante.nombre)}</b>, su historial (${estudiante.historial.length} materias) y su cuenta de acceso. Esta acción queda en la auditoría y no se puede deshacer.`,
        alAceptar: async () => {
          await api(`/api/admin/estudiantes/${encodeURIComponent(codigo)}`, { metodo: "DELETE" });
          toast("Estudiante eliminado.", "ok");
          location.hash = "#/estudiantes";
        },
      });
      editorHistorial($("#pestanaHistorial"), estudiante, async (actualizado) => {
        estudiante = actualizado;
        await cargarTransicion();
      });
    }
    cargarTransicion();
  };

  const cargarTransicion = async () => {
    const caja = $("#pestanaTransicion");
    caja.innerHTML = cargando("Calculando la transición…");
    try {
      const r = await api(`/api/estudiantes/${encodeURIComponent(codigo)}/validar-malla`, { metodo: "POST" });
      const e = r.estudiante;
      $("#tituloEstudiante").textContent = e.nombre;
      $("#datosEstudiante").innerHTML = `Código ${esc(e.codigo)} · Documento ${esc(e.documento)} · Ingresó con la malla
        <b>${esc(e.malla_version)}</b> · ${chip(e.estado, e.estado)}`;
      renderTransicion(caja, r, malla);
      if (r.tickets_nuevos) toast(`Se abrieron ${r.tickets_nuevos} tickets de revisión.`);
    } catch (error) { caja.innerHTML = errorCarga(error.message); }
  };

  pintar();
}

// ===================================================================== formulario
async function formularioEstudiante(actual, alGuardar) {
  let versiones = [];
  try { versiones = await api("/api/mallas"); } catch (error) { toast(error.message, "error"); return; }
  const nuevo = !actual;

  abrirModal({
    titulo: nuevo ? "Registrar estudiante" : `Editar ${actual.nombre}`,
    textoAceptar: nuevo ? "Registrar" : "Guardar cambios",
    cuerpo: `
      <div class="form-rejilla">
        ${campo({ nombre: "codigo", etiqueta: "Código", valor: actual?.codigo, requerido: true,
                  extra: nuevo ? 'maxlength="30"' : "disabled", ayuda: nuevo ? "No se puede cambiar después." : "" })}
        ${campo({ nombre: "documento", etiqueta: "Documento", valor: actual?.documento, requerido: true })}
      </div>
      ${campo({ nombre: "nombre", etiqueta: "Nombre completo", valor: actual?.nombre, requerido: true })}
      ${campo({ nombre: "correo", etiqueta: "Correo institucional", valor: actual?.correo, tipo: "email" })}
      <div class="form-rejilla">
        ${selector({ nombre: "malla_version", etiqueta: "Malla con la que ingresó", valor: actual?.malla_version || versiones.at(-1),
                     opciones: versiones.map((v) => [v, `Malla ${v}`]) })}
        ${selector({ nombre: "estado", etiqueta: "Estado", valor: actual?.estado || "activo", opciones: ESTADOS })}
      </div>
      ${nuevo ? campo({ nombre: "password_cuenta", etiqueta: "Contraseña para su cuenta (opcional)", tipo: "password",
                        extra: 'autocomplete="new-password"',
                        ayuda: "Si la escribe, se crea su usuario (usuario = código) para que vea su avance. Mínimo 8 caracteres con letras y números." }) : ""}`,
    alAceptar: async (form) => {
      const datos = datosFormulario(form);
      let guardado;
      if (nuevo) {
        guardado = await api("/api/admin/estudiantes", { metodo: "POST", json: datos });
      } else {
        const { codigo, password_cuenta, ...cambios } = datos;
        guardado = await api(`/api/admin/estudiantes/${encodeURIComponent(actual.codigo)}`, { metodo: "PUT", json: cambios });
      }
      toast(nuevo ? "Estudiante registrado." : "Datos actualizados.", "ok");
      alGuardar(guardado);
    },
  });
}

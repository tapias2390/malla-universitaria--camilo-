/* Pantalla de inicio de sesión (la escena ilustrada se define en index.html y css/login.css). */
import { api, guardarToken } from "./api.js";
import { $ } from "./ui.js";

// "Recordar usuario": solo se guarda el nombre de usuario, nunca la contraseña.
const CLAVE_RECORDAR = "usuarioRecordado";
const sinAnimacion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

export function prepararLogin(alEntrar) {
  try {
    const recordado = localStorage.getItem(CLAVE_RECORDAR);
    if (recordado) { $("#usuario").value = recordado; $("#recordar").checked = true; }
  } catch { /* almacenamiento no disponible: se ignora */ }

  $("#verClave").onclick = () => {
    const mostrar = $("#clave").type === "password";
    $("#clave").type = mostrar ? "text" : "password";
    $("#verClave").setAttribute("aria-pressed", String(mostrar));
    $("#verClave").setAttribute("aria-label", mostrar ? "Ocultar contraseña" : "Mostrar contraseña");
  };

  $("#olvide").onclick = () => {
    const abierta = $("#ayudaClave").classList.toggle("visible");
    $("#olvide").setAttribute("aria-expanded", String(abierta));
  };

  $("#formLogin").addEventListener("submit", async (evento) => {
    evento.preventDefault();
    const boton = $("#btnEntrar");
    $("#errorLogin").textContent = "";
    if (!$("#usuario").value.trim() || !$("#clave").value) {
      return mostrarError("Escribe tu usuario y tu contraseña.");
    }

    boton.disabled = true; boton.classList.add("cargando"); $("#txtEntrar").textContent = "Entrando…";
    try {
      const r = await api("/api/auth/login", { metodo: "POST", form: { username: $("#usuario").value, password: $("#clave").value } });
      guardarToken(r.access_token);
      try {
        if ($("#recordar").checked) localStorage.setItem(CLAVE_RECORDAR, $("#usuario").value.trim());
        else localStorage.removeItem(CLAVE_RECORDAR);
      } catch { /* se ignora */ }
      $("#clave").value = "";
      $("#tarjetaLogin").classList.add("saliendo");
      await new Promise((ok) => setTimeout(ok, sinAnimacion() ? 0 : 360));
      await alEntrar();
    } catch (error) {
      mostrarError(error.message);
    } finally {
      boton.disabled = false; boton.classList.remove("cargando"); $("#txtEntrar").textContent = "Iniciar sesión";
    }
  });
}

export function mostrarLogin() {
  $("#vistaApp").classList.add("oculto");
  $("#tarjetaLogin").classList.remove("saliendo", "error");
  $("#vistaLogin").classList.remove("oculto");
}

function mostrarError(mensaje) {
  const tarjeta = $("#tarjetaLogin");
  $("#errorLogin").textContent = mensaje;
  tarjeta.classList.remove("error");
  void tarjeta.offsetWidth;            // reinicia la animación de "temblor"
  tarjeta.classList.add("error");
}

// Acceso a la API desde el navegador. Traduce cada error a un mensaje en lenguaje de usuario.
// No contiene reglas de negocio: las reglas viven en el servidor (app/services).

const CLAVE_SESION = 'articla-sesion';

// Identificador anónimo de este navegador: separa tu historial del de otras personas.
// No es un dato personal: no contiene nombre, correo ni RUT.
export function sesion() {
  try {
    let s = localStorage.getItem(CLAVE_SESION);
    if (!s) {
      s = (crypto.randomUUID ? crypto.randomUUID() : `s-${Date.now()}-${Math.random().toString(36).slice(2)}`);
      localStorage.setItem(CLAVE_SESION, s);
    }
    return s;
  } catch {
    return undefined;
  }
}

function mensajeDeError(status, cuerpo) {
  const e = cuerpo && cuerpo.error;
  if (status === 422 && e && e.codigo === 'REGLA_DE_NEGOCIO') return e.mensaje;
  if (status === 422) return 'Revisa lo que escribiste: hay un dato que no es válido.';
  if (status === 404) return 'No encontramos lo que buscas. Puede que se haya borrado.';
  if (status === 409) return 'Ya existe un registro con esos datos.';
  if (status === 503) return 'El servicio no está disponible en este momento. Intenta de nuevo en unos segundos.';
  return 'Ocurrió un problema inesperado. Intenta de nuevo.';
}

export async function pedir(ruta, { method = 'GET', body } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  const s = sesion();
  if (s) headers['X-Sesion'] = s;
  let r;
  try {
    r = await fetch(`/api/v1${ruta}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      cache: 'no-store',
    });
  } catch {
    throw new Error('No hay conexión con Articla. Revisa tu internet e intenta de nuevo.');
  }
  if (r.status === 204) return null;
  let datos = null;
  try { datos = await r.json(); } catch { datos = null; }
  if (!r.ok) throw new Error(mensajeDeError(r.status, datos));
  return datos;
}

export const MIN_PREGUNTA = 5;
export const MAX_PREGUNTA = 1000;

export function fecha(iso) {
  try {
    return new Date(iso).toLocaleString('es-CL', { dateStyle: 'medium', timeStyle: 'short' });
  } catch {
    return iso;
  }
}

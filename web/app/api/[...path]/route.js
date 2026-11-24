// Puente entre el navegador y la API de FastAPI.
// El navegador llama a /api/v1/... en este mismo servidor y aquí se reenvía a API_URL.
// Capa de presentación: no tiene reglas de negocio, solo reenvía la petición tal cual.
export const dynamic = 'force-dynamic';

const API_URL = process.env.API_URL || 'http://localhost:8000';

async function reenviar(req) {
  const url = new URL(req.url);
  const destino = `${API_URL}${url.pathname}${url.search}`;
  const headers = {};
  const tipo = req.headers.get('content-type');
  const sesion = req.headers.get('x-sesion');
  if (tipo) headers['content-type'] = tipo;
  if (sesion) headers['x-sesion'] = sesion;
  const conCuerpo = !['GET', 'HEAD'].includes(req.method);
  try {
    const r = await fetch(destino, {
      method: req.method,
      headers,
      body: conCuerpo ? await req.text() : undefined,
      cache: 'no-store',
    });
    const cuerpo = r.status === 204 ? null : await r.text();
    return new Response(cuerpo, {
      status: r.status,
      headers: { 'content-type': r.headers.get('content-type') || 'application/json' },
    });
  } catch {
    return Response.json(
      { error: { codigo: 'API_NO_DISPONIBLE', mensaje: 'No se pudo conectar con el servicio de Articla.' } },
      { status: 503 },
    );
  }
}

export const GET = reenviar;
export const POST = reenviar;
export const PUT = reenviar;
export const PATCH = reenviar;
export const DELETE = reenviar;

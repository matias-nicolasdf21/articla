'use client';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { fecha, pedir } from '../../lib/api';
import { Cargando, ErrorCaja, Vacio } from '../../components/Estados';
import Respuesta from '../../components/Respuesta';
import { Carpeta } from '../../components/Ilustraciones';

export default function Historial() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [abierta, setAbierta] = useState(null);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setDatos(await pedir('/consultas?limit=100'));
    } catch (err) {
      setError(err.message);
    }
  }, []);

  useEffect(() => { cargar(); }, [cargar]);

  async function borrar(id) {
    if (!window.confirm('¿Borrar esta consulta de tu historial?')) return;
    try {
      await pedir(`/consultas/${id}`, { method: 'DELETE' });
      setDatos((d) => ({ ...d, items: d.items.filter((c) => c.id !== id), total: d.total - 1 }));
    } catch (err) {
      setError(err.message);
    }
  }

  async function marcarUtil(consulta, util) {
    try {
      const nueva = await pedir(`/consultas/${consulta.id}`, { method: 'PATCH', body: { util } });
      setDatos((d) => ({ ...d, items: d.items.map((c) => (c.id === nueva.id ? nueva : c)) }));
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <section className="pagina-angosta">
      <h1 className="page-title">Historial</h1>
      <p className="sub">Tus consultas en este navegador. Se guardan 90 días y puedes borrarlas cuando quieras.</p>
      {error ? <ErrorCaja mensaje={error} onReintentar={cargar} /> : null}
      {!datos && !error ? <Cargando texto="Cargando tu historial…" /> : null}
      {datos && datos.items.length === 0 ? (
        <Vacio titulo="Aún no tienes consultas.">
          <Carpeta />
          <Link href="/preguntar">Haz tu primera pregunta</Link> y aparecerá aquí.
        </Vacio>
      ) : null}
      {datos && datos.items.length > 0 ? (
        <ul className="lista">
          {datos.items.map((c) => (
            <li key={c.id} className="tarjeta">
              <button className="fila" onClick={() => setAbierta(abierta === c.id ? null : c.id)} aria-expanded={abierta === c.id}>
                <span className="titulo">{c.pregunta}</span>
                <span className="detalle">{fecha(c.creada_en)}{c.modo === 'ia' ? ', respuesta redactada con IA' : ''}</span>
                {c.citas.length > 0 ? (
                  <span className="mini-timbres">
                    {c.citas.slice(0, 3).map((x) => (
                      <span key={x.fragmento_id} className="timbre timbre-mini">{x.fuente.replace(/\s*\(idNorma \d+\)$/, '')}, {x.articulo}</span>
                    ))}
                  </span>
                ) : null}
              </button>
              {abierta === c.id ? (
                <div className="abierta">
                  <Respuesta consulta={c} onUtil={marcarUtil} />
                  <button className="btn btn-secondary btn-sm" onClick={() => borrar(c.id)}>Borrar esta consulta</button>
                </div>
              ) : null}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

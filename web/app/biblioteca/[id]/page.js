'use client';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { pedir } from '../../../lib/api';
import { Cargando, ErrorCaja, Vacio } from '../../../components/Estados';

const POR_PAGINA = 20;

export default function FichaFuente() {
  const { id } = useParams();
  const [fuente, setFuente] = useState(null);
  const [pagina, setPagina] = useState(1);
  const [arts, setArts] = useState(null);
  const [error, setError] = useState(null);

  const cargar = useCallback(async () => {
    setError(null);
    setArts(null);
    try {
      const [f, a] = await Promise.all([
        pedir(`/fuentes/${id}`),
        pedir(`/fuentes/${id}/fragmentos?page=${pagina}&limit=${POR_PAGINA}`),
      ]);
      setFuente(f);
      setArts(a);
    } catch (err) {
      setError(err.message);
    }
  }, [id, pagina]);
  useEffect(() => { cargar(); }, [cargar]);

  const paginas = arts ? Math.max(1, Math.ceil(arts.total / POR_PAGINA)) : 1;
  return (
    <section>
      <Link href="/biblioteca" className="volver">← Biblioteca</Link>
      <h1 className="page-title">{fuente ? fuente.titulo : 'Fuente'}</h1>
      {fuente ? (
        <p className="sub">
          {fuente.articulos.toLocaleString('es-CL')} artículos vigentes · {fuente.licencia}
          {fuente.url_oficial ? <> · <a href={fuente.url_oficial} target="_blank" rel="noreferrer">Ver en LeyChile</a></> : null}
        </p>
      ) : null}
      {error ? <ErrorCaja mensaje={error} onReintentar={cargar} /> : null}
      {!arts && !error ? <Cargando texto="Cargando artículos…" /> : null}
      {arts && arts.items.length === 0 ? <Vacio titulo="Esta fuente no tiene artículos cargados." /> : null}
      {arts && arts.items.length > 0 ? (
        <>
          <ul className="lista">
            {arts.items.map((a) => (
              <li key={a.id}>
                <Link href={`/articulo/${a.id}`} className="tarjeta fila">
                  <span className="titulo">{a.articulo}</span>
                  <span className="detalle">{a.texto.replace(/\s+/g, ' ').slice(0, 160)}…</span>
                </Link>
              </li>
            ))}
          </ul>
          <div className="paginacion">
            <button className="btn btn-secondary btn-sm" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>Anterior</button>
            <span>Página {pagina} de {paginas}</span>
            <button className="btn btn-secondary btn-sm" disabled={pagina >= paginas} onClick={() => setPagina(pagina + 1)}>Siguiente</button>
          </div>
        </>
      ) : null}
    </section>
  );
}

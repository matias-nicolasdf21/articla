'use client';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useCallback, useEffect, useState } from 'react';
import { pedir } from '../../../lib/api';
import { ErrorCaja } from '../../../components/Estados';

// El artículo citado, presentado como una hoja oficial con su timbre.
export default function Articulo() {
  const { id } = useParams();
  const [art, setArt] = useState(null);
  const [error, setError] = useState(null);
  const [copiado, setCopiado] = useState(false);

  const cargar = useCallback(async () => {
    setError(null);
    try {
      setArt(await pedir(`/fragmentos/${id}`));
    } catch (err) {
      setError(err.message);
    }
  }, [id]);
  useEffect(() => { cargar(); }, [cargar]);

  const nombre = art ? art.fuente.replace(/\s*\(idNorma \d+\)$/, '') : '';
  const titulo = art ? (art.fuente_titulo || nombre) : '';

  async function copiar() {
    try {
      await navigator.clipboard.writeText(`${nombre}, ${art.articulo}\n\n${art.texto}\n\nFuente: LeyChile${art.url_oficial ? ` (${art.url_oficial})` : ''}`);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      setCopiado(false);
    }
  }

  return (
    <section className="pagina-articulo">
      <nav className="migas" aria-label="Ruta">
        <Link href="/biblioteca">Biblioteca de leyes</Link>
        {art ? <><span aria-hidden="true">/</span><Link href={`/biblioteca/${art.fuente_id}`}>{nombre}</Link><span aria-hidden="true">/</span><span>{art.articulo}</span></> : null}
      </nav>
      {error ? <ErrorCaja mensaje={error} onReintentar={cargar} /> : null}
      {!art && !error ? (
        <div className="documento esqueleto" role="status" aria-live="polite">
          <span className="sr-only">Cargando el artículo…</span>
          <div className="barra" style={{ width: '40%' }} /><div className="barra" style={{ width: '90%' }} />
          <div className="barra" style={{ width: '85%' }} /><div className="barra" style={{ width: '70%' }} />
        </div>
      ) : null}
      {art ? (
        <article className="documento">
          <header className="documento-cabecera">
            <div>
              <p className="documento-norma">{titulo}</p>
              <h1>{art.articulo.replace(/^art\./, 'Artículo')}</h1>
              {art.ubicacion ? <p className="documento-ubicacion">{art.ubicacion}</p> : null}
            </div>
            <div className="timbre timbre-grande" aria-hidden="true"><span>{nombre}</span><span>{art.articulo}</span></div>
          </header>
          <div className="texto-oficial">{art.texto}</div>
          <footer className="documento-pie">
            <span className="verificado">
              Texto oficial de LeyChile
              {art.fecha_version ? `, versión del ${new Date(art.fecha_version + 'T00:00:00').toLocaleDateString('es-CL')}` : ''}
            </span>
            <span className="documento-acciones">
              <button className="btn btn-secundario btn-sm" onClick={copiar}>{copiado ? 'Copiado ✓' : 'Copiar texto'}</button>
              {art.url_oficial ? <a className="btn btn-secundario btn-sm" href={art.url_oficial} target="_blank" rel="noreferrer">Ver la norma en LeyChile</a> : null}
              <Link className="btn btn-primario btn-sm" href={`/biblioteca/${art.fuente_id}`}>Más artículos de esta norma</Link>
            </span>
          </footer>
        </article>
      ) : null}
    </section>
  );
}

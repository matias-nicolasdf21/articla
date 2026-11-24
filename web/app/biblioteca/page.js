'use client';
import Link from 'next/link';
import { useCallback, useEffect, useState } from 'react';
import { pedir } from '../../lib/api';
import { Cargando, ErrorCaja, Vacio } from '../../components/Estados';

const TIPOS = { codigo: 'Código', ley: 'Ley', libro: 'Libro' };
const POR_PAGINA = 30;

export default function Biblioteca() {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [texto, setTexto] = useState('');
  const [buscar, setBuscar] = useState('');
  const [pagina, setPagina] = useState(1);

  const cargar = useCallback(async () => {
    setError(null);
    setDatos(null);
    try {
      const q = buscar ? `&q=${encodeURIComponent(buscar)}` : '';
      setDatos(await pedir(`/fuentes?limit=${POR_PAGINA}&page=${pagina}${q}`));
    } catch (err) {
      setError(err.message);
    }
  }, [buscar, pagina]);
  useEffect(() => { cargar(); }, [cargar]);

  function enviar(e) {
    e.preventDefault();
    setPagina(1);
    setBuscar(texto.trim());
  }

  const paginas = datos ? Math.max(1, Math.ceil(datos.total / POR_PAGINA)) : 1;
  return (
    <section>
      <h1 className="page-title">Biblioteca de fuentes</h1>
      <p className="sub">Las leyes y códigos con que responde Articla. Todo es texto oficial y público de LeyChile (Biblioteca del Congreso Nacional). No usamos libros.</p>
      <form className="composer buscador" onSubmit={enviar} role="search">
        <label htmlFor="buscar" className="sr-only">Buscar una ley</label>
        <input id="buscar" value={texto} onChange={(e) => setTexto(e.target.value)}
          placeholder="Busca por número o tema, por ejemplo: 18.101, tránsito, consumidor…" />
        <button className="btn btn-primary" type="submit">Buscar</button>
      </form>
      {datos ? <p className="nota">{datos.total.toLocaleString('es-CL')} {datos.total === 1 ? 'fuente' : 'fuentes'}{buscar ? ` para “${buscar}”` : ' cargadas'}</p> : null}
      {error ? <ErrorCaja mensaje={error} onReintentar={cargar} /> : null}
      {!datos && !error ? <Cargando texto="Cargando las leyes…" /> : null}
      {datos && datos.items.length === 0 ? (
        <Vacio titulo={buscar ? 'No encontramos leyes con ese texto.' : 'Todavía no hay leyes cargadas.'}>
          {buscar ? 'Prueba con otra palabra o con el número de la ley sin puntos.' : null}
        </Vacio>
      ) : null}
      {datos && datos.items.length > 0 ? (
        <>
          <div className="grilla">
            {datos.items.map((f) => (
              <Link key={f.id} href={`/biblioteca/${f.id}`} className="tarjeta fuente">
                <span className="tipo">{TIPOS[f.tipo] || f.tipo} · {f.identificador}</span>
                <strong>{f.titulo}</strong>
                <span className="detalle">{f.articulos.toLocaleString('es-CL')} artículos vigentes</span>
              </Link>
            ))}
          </div>
          <div className="paginacion">
            <button className="btn btn-secondary btn-sm" disabled={pagina <= 1} onClick={() => setPagina(pagina - 1)}>Anterior</button>
            <span>Página {pagina} de {paginas.toLocaleString('es-CL')}</span>
            <button className="btn btn-secondary btn-sm" disabled={pagina >= paginas} onClick={() => setPagina(pagina + 1)}>Siguiente</button>
          </div>
        </>
      ) : null}
    </section>
  );
}

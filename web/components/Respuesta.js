'use client';
import Link from 'next/link';
import { useState } from 'react';

// Muestra una respuesta con sus secciones (Qué dice la ley, Qué puedes hacer, Ten en cuenta…)
// y sus citas; cada cita lleva al texto oficial del artículo. Solo presenta: no decide nada.

const TITULOS = ['Qué dice la ley:', 'Qué puedes hacer:', 'Ten en cuenta:', 'Artículos relacionados:'];

function Bloque({ texto }) {
  const lineas = texto.split('\n').filter((l) => l.trim() !== '');
  const titulo = TITULOS.includes(lineas[0]?.trim()) ? lineas[0].trim().replace(/:$/, '') : null;
  const cuerpo = titulo ? lineas.slice(1) : lineas;
  const numerada = cuerpo.length > 0 && cuerpo.every((l) => /^\d+\.\s/.test(l));
  const vinetas = cuerpo.length > 0 && cuerpo.every((l) => /^[-•]\s/.test(l));
  const limpiar = (l) => l.replace(/^(\d+\.|[-•])\s/, '');

  if (!titulo && !numerada && !vinetas) {
    const aviso = /no reemplaza/i.test(texto);
    return <p className={aviso ? 'aviso-final' : 'resumen'}>{texto}</p>;
  }
  return (
    <div className="seccion">
      {titulo ? <h3>{titulo}</h3> : null}
      {numerada ? (
        <ol>{cuerpo.map((l, i) => <li key={i}>{limpiar(l)}</li>)}</ol>
      ) : vinetas ? (
        <ul>{cuerpo.map((l, i) => <li key={i}>{limpiar(l)}</li>)}</ul>
      ) : (
        cuerpo.map((l, i) => <p key={i}>{l}</p>)
      )}
    </div>
  );
}

export default function Respuesta({ consulta, onUtil, demo = false }) {
  const [copiado, setCopiado] = useState(false);
  const bloques = (consulta.respuesta || '').split(/\n{2,}/);

  async function copiar() {
    const citas = consulta.citas.map((c) => `${c.fuente}, ${c.articulo}`).join('; ');
    const texto = `Pregunta: ${consulta.pregunta}\n\n${consulta.respuesta}${citas ? `\n\nCitas: ${citas}` : ''}\n\n(Articla)`;
    try {
      await navigator.clipboard.writeText(texto);
      setCopiado(true);
      setTimeout(() => setCopiado(false), 2000);
    } catch {
      setCopiado(false);
    }
  }

  return (
    <div className="msg msg-assistant">
      {consulta.alerta ? (
        <div className="alerta" role="alert">
          <strong>Importante:</strong> {consulta.alerta}
        </div>
      ) : null}
      <div className="meta">
        <span className={`badge ${consulta.modo === 'ia' ? 'badge-ia' : ''}`}>
          {consulta.modo === 'ia' ? 'Respuesta redactada con IA' : 'Artículos encontrados'}
        </span>
        {typeof consulta.duracion_ms === 'number' ? (
          consulta.modo === 'ia' && consulta.duracion_ms < 1000 ? (
            <span title="Esta pregunta ya se había respondido: se muestra la respuesta guardada">Respuesta guardada: pregunta ya respondida antes</span>
          ) : (
            <span>Respondió en {(consulta.duracion_ms / 1000).toLocaleString('es-CL', { maximumFractionDigits: 1 })} s</span>
          )
        ) : null}
      </div>
      {bloques.map((b, i) => <Bloque key={i} texto={b} />)}
      {consulta.citas.length > 0 ? (
        <>
          <div className="label-citas">{demo ? 'Artículos citados' : 'Artículos citados: toca uno para leer el texto oficial'}</div>
          <div className="cite-row" aria-label="Artículos citados">
            {consulta.citas.map((c) => {
              const nombre = c.fuente.replace(/\s*\(idNorma \d+\)$/, '');
              return demo ? (
                <span key={c.fragmento_id} className="timbre timbre-cita"><span>{nombre}</span><span>{c.articulo}</span></span>
              ) : (
                <Link key={c.fragmento_id} href={`/articulo/${c.fragmento_id}`} className="timbre timbre-cita"
                  aria-label={`Leer ${nombre}, ${c.articulo}`}>
                  <span>{nombre}</span>
                  <span>{c.articulo}</span>
                </Link>
              );
            })}
          </div>
        </>
      ) : null}
      {demo ? null : (<div className="util">
        {onUtil ? (
          <>
            <span>¿Te sirvió?</span>
            <button className={`btn-sm btn btn-secondary ${consulta.util === true ? 'on' : ''}`} onClick={() => onUtil(consulta, true)}>Sí</button>
            <button className={`btn-sm btn btn-secondary ${consulta.util === false ? 'on' : ''}`} onClick={() => onUtil(consulta, false)}>No</button>
          </>
        ) : null}
        <button className="btn-sm btn btn-secondary copiar" onClick={copiar}>{copiado ? 'Copiado ✓' : 'Copiar respuesta'}</button>
      </div>)}
    </div>
  );
}

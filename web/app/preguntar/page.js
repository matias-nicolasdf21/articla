'use client';
import { useEffect, useRef, useState } from 'react';
import { MAX_PREGUNTA, MIN_PREGUNTA, pedir } from '../../lib/api';
import { ErrorCaja } from '../../components/Estados';
import Respuesta from '../../components/Respuesta';
import { Balanza } from '../../components/Ilustraciones';

function validar(texto) {
  const t = texto.trim();
  if (t.length === 0) return 'Escribe tu pregunta.';
  if (t.length < MIN_PREGUNTA) return `Tu pregunta es muy corta: escribe al menos ${MIN_PREGUNTA} caracteres.`;
  if (t.length > MAX_PREGUNTA) return `Tu pregunta es muy larga: el máximo es ${MAX_PREGUNTA} caracteres.`;
  return null;
}

const SUGERENCIAS = [
  '¿Mi arrendador puede subirme el arriendo a mitad de contrato?',
  'Me despidieron sin aviso, ¿qué me corresponde?',
  '¿Qué hago si un producto que compré vino fallado?',
];

export default function Preguntar() {
  const [texto, setTexto] = useState('');
  const [aviso, setAviso] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(false);
  const [conversacion, setConversacion] = useState([]);
  const [pendiente, setPendiente] = useState('');
  const [etapa, setEtapa] = useState(0);
  const fin = useRef(null);

  const ETAPAS = ['Entendiendo tu pregunta…', 'Buscando en las leyes chilenas…', 'Leyendo los artículos más relacionados…', 'Redactando tu respuesta…'];

  useEffect(() => {
    if (!cargando) { setEtapa(0); return undefined; }
    const t = setInterval(() => setEtapa((e) => Math.min(e + 1, ETAPAS.length - 1)), 4000);
    return () => clearInterval(t);
  }, [cargando]);

  useEffect(() => {
    const q = new URLSearchParams(window.location.search).get('q');
    if (q) setTexto(q);
  }, []);

  useEffect(() => {
    if (fin.current) fin.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, [conversacion, cargando]);

  async function enviar(e) {
    e.preventDefault();
    const problema = validar(texto);
    setAviso(problema);
    if (problema) return;
    setError(null);
    setCargando(true);
    setPendiente(texto.trim());
    setTexto('');
    try {
      const c = await pedir('/consultas', { method: 'POST', body: { pregunta: texto.trim() } });
      setConversacion((xs) => [...xs, c]);
    } catch (err) {
      setError(err.message);
      setTexto(texto);
    } finally {
      setCargando(false);
      setPendiente('');
    }
  }

  async function marcarUtil(consulta, util) {
    try {
      const nueva = await pedir(`/consultas/${consulta.id}`, { method: 'PATCH', body: { util } });
      setConversacion((xs) => xs.map((x) => (x.id === nueva.id ? nueva : x)));
    } catch (err) {
      setError(err.message);
    }
  }

  const restantes = MAX_PREGUNTA - texto.length;
  return (
    <section className="chat">
      <h1 className="page-title">Preguntar</h1>

      {conversacion.length === 0 && !cargando ? (
        <div className="vacio-preguntar">
          <Balanza />
          <strong>Cuéntanos qué te pasa</strong>
          <p>Escribe tu duda abajo, o parte con uno de estos ejemplos:</p>
          <div className="sugerencias">
            {SUGERENCIAS.map((q) => (
              <button key={q} type="button" className="sugerencia" onClick={() => setTexto(q)}>{q}</button>
            ))}
          </div>
        </div>
      ) : null}

      {conversacion.map((c) => (
        <div key={c.id}>
          <div className="msg-row-user"><div className="msg-user">{c.pregunta}</div></div>
          <Respuesta consulta={c} onUtil={marcarUtil} />
        </div>
      ))}

      {cargando ? (
        <div>
          <div className="msg-row-user"><div className="msg-user">{pendiente}</div></div>
          <div className="msg msg-assistant esqueleto" role="status" aria-live="polite">
            <div className="esqueleto-etapa"><span className="spinner" aria-hidden="true" /> {ETAPAS[etapa]}</div>
            <div className="barra" style={{ width: '92%' }} />
            <div className="barra" style={{ width: '78%' }} />
            <div className="barra corta" style={{ width: '34%' }} />
            <div className="barra" style={{ width: '88%' }} />
            <div className="barra" style={{ width: '64%' }} />
            <div className="esqueleto-timbres"><span /><span /></div>
          </div>
        </div>
      ) : null}
      {error ? <ErrorCaja mensaje={error} /> : null}
      <div ref={fin} />

      <form className="composer" onSubmit={enviar} noValidate>
        <label htmlFor="pregunta" className="sr-only">Tu pregunta</label>
        <textarea
          id="pregunta"
          rows={2}
          value={texto}
          maxLength={MAX_PREGUNTA + 50}
          placeholder="Escribe tu pregunta legal…"
          onChange={(e) => { setTexto(e.target.value); if (aviso) setAviso(validar(e.target.value)); }}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) enviar(e); }}
          aria-invalid={aviso ? 'true' : 'false'}
          aria-describedby="ayuda-pregunta"
          disabled={cargando}
        />
        <button className="btn btn-primary" type="submit" disabled={cargando}>
          {cargando ? 'Enviando…' : 'Enviar'}
        </button>
      </form>
      <div id="ayuda-pregunta" className={`ayuda ${aviso ? 'mal' : ''}`}>
        {aviso || `Quedan ${restantes} caracteres.`}
      </div>
      <p className="nota">
        Articla entrega orientación general basada en el texto oficial de las leyes chilenas y no reemplaza la
        asesoría de un abogado o abogada. No escribas datos personales (nombre, RUT, dirección).
      </p>
    </section>
  );
}

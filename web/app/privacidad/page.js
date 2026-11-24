'use client';
import { useState } from 'react';
import { pedir } from '../../lib/api';
import { ErrorCaja } from '../../components/Estados';

export default function Privacidad() {
  const [estado, setEstado] = useState(null);
  const [error, setError] = useState(null);

  async function borrarTodo() {
    if (!window.confirm('Se borrarán todas tus consultas. Esta acción no se puede deshacer. ¿Continuar?')) return;
    setError(null);
    setEstado('borrando');
    try {
      await pedir('/consultas', { method: 'DELETE' });
      setEstado('listo');
    } catch (err) {
      setError(err.message);
      setEstado(null);
    }
  }

  return (
    <section className="texto-largo">
      <h1 className="page-title">Privacidad</h1>
      <p className="sub">Articla no te pide cuenta, nombre, correo ni RUT para usarla.</p>
      <h2>Qué guardamos</h2>
      <ul>
        <li>El texto de tu pregunta, la respuesta, los artículos citados, si te sirvió y la fecha.</li>
        <li>Un identificador anónimo de este navegador, para mostrarte solo tu historial. No contiene datos tuyos.</li>
      </ul>
      <h2>Para qué y por cuánto tiempo</h2>
      <p>Solo para mostrarte tu historial y medir si las respuestas sirven. Las consultas se borran solas a los 90 días.</p>
      <h2>Con quién se comparte</h2>
      <p>
        Para redactar la respuesta, tu pregunta y los artículos encontrados se envían al modelo de lenguaje Gemini de
        Google. No se envía ningún dato que te identifique, pero por eso te pedimos no escribir datos personales en
        la pregunta.
      </p>
      <h2>Borrar tus datos</h2>
      <p>Puedes borrar una consulta desde el Historial, o todas de una vez aquí:</p>
      <button className="btn btn-primary" onClick={borrarTodo} disabled={estado === 'borrando'}>
        {estado === 'borrando' ? 'Borrando…' : 'Borrar todo mi historial'}
      </button>
      {estado === 'listo' ? <div className="estado ok" role="status">Listo: tu historial quedó vacío.</div> : null}
      {error ? <ErrorCaja mensaje={error} /> : null}
    </section>
  );
}

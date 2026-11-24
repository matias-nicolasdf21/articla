'use client';
import { useEffect, useState } from 'react';
import { pedir } from '../lib/api';

// Cifras reales del corpus cargado (GET /api/v1/estadisticas). Si la API no responde, no muestra nada.
export default function Cifras() {
  const [datos, setDatos] = useState(null);
  useEffect(() => {
    pedir('/estadisticas').then(setDatos).catch(() => setDatos(null));
  }, []);
  if (!datos) return null;
  return (
    <>
      <div className="stat"><div className="n">{datos.fuentes.toLocaleString('es-CL')}</div><div className="l">normas oficiales de LeyChile</div></div>
      <div className="stat"><div className="n">{datos.articulos.toLocaleString('es-CL')}</div><div className="l">artículos vigentes donde buscamos</div></div>
    </>
  );
}

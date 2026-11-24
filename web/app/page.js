import Link from 'next/link';
import Cifras from '../components/Cifras';
import { EscenaPrincipal, IconoPaso, IconoTema } from '../components/Ilustraciones';
import Respuesta from '../components/Respuesta';

const TEMAS = [
  ['trabajo', 'Trabajo', 'Me despidieron sin aviso, ¿qué me corresponde?'],
  ['arriendo', 'Arriendo', 'Mi arrendador quiere subirme el arriendo a mitad de contrato, ¿puede hacerlo?'],
  ['familia', 'Familia', 'El papá de mi hijo no paga la pensión de alimentos, ¿qué puedo hacer?'],
  ['consumo', 'Compras', 'Compré un producto que vino fallado, ¿puedo pedir la devolución?'],
  ['transito', 'Tránsito', 'Me pasaron un parte por exceso de velocidad, ¿qué hago?'],
  ['violencia', 'Violencia', 'Mi pareja me amenaza, ¿qué puedo hacer?'],
  ['prevision', 'Pensiones', '¿Cuánto me descuenta la AFP del sueldo?'],
  ['herencia', 'Herencias', 'Murió mi papá sin testamento, ¿quiénes heredan?'],
];

// Respuesta real entregada por Articla (Ley 20.066), usada como muestra.
const MUESTRA = {
  id: 0,
  pregunta: 'Mi pareja me amenaza, ¿qué puedo hacer?',
  modo: 'ia',
  duracion_ms: 24200,
  util: null,
  alerta: 'Si estás en peligro ahora, llama al 133 (Carabineros). También puedes llamar al 149 (Fono Familia de Carabineros) o al 1455 (orientación en violencias de género, gratuito, todos los días de 8:00 a 24:00).',
  respuesta: 'La ley te protege ante situaciones de riesgo de violencia intrafamiliar: el tribunal puede adoptar de inmediato medidas de protección para resguardar tu seguridad.\n\nQué dice la ley:\n- Ante un riesgo inminente de maltrato, el tribunal debe adoptar medidas de protección o cautelares con el solo mérito de la denuncia (Ley 20.066, art. 7)\n- En cualquier etapa del procedimiento, el juez puede decretar las medidas cautelares necesarias para proteger a la víctima (Ley 20.066, art. 15)\n\nQué puedes hacer:\n1. Denuncia en Carabineros, la PDI, la Fiscalía o directamente en el Tribunal de Familia.\n2. Reúne antecedentes de las amenazas: mensajes, audios, correos o testigos.\n3. Pide al tribunal medidas cautelares urgentes, como la prohibición de acercarse a ti.\n\nEsto es orientación general y no reemplaza la asesoría de un abogado.',
  citas: [
    { fragmento_id: 1, fuente: 'Ley 20.066', articulo: 'art. 7' },
    { fragmento_id: 2, fuente: 'Ley 20.066', articulo: 'art. 15' },
  ],
};

const PASOS = [
  ['Escribes tu duda como se la contarías a alguien', 'Sin palabras técnicas. No necesitas cuenta ni dar tu nombre.'],
  ['Articla busca en el texto oficial de las leyes', 'Revisa más de 21 mil normas de LeyChile y elige los artículos que tratan tu caso.'],
  ['Recibes una respuesta con el artículo timbrado', 'Qué dice la ley, qué puedes hacer y cada cita enlazada al texto oficial para que lo compruebes.'],
];

export default function Inicio() {
  return (
    <>
      <section className="portada">
        <div className="portada-texto">
          <h1>Tu duda legal, respondida con la ley en la mano.</h1>
          <p className="entrada">
            Escribe tu problema con tus palabras. En menos de un minuto te explicamos qué dice la ley chilena,
            qué puedes hacer, y te mostramos el artículo exacto que lo respalda.
          </p>
          <div className="acciones">
            <Link href="/preguntar" className="btn btn-primario">Hacer una pregunta</Link>
            <Link href="/biblioteca" className="btn btn-secundario">Ver las leyes</Link>
          </div>
          <div className="cifras"><Cifras /></div>
        </div>
        <div className="portada-ilustracion"><EscenaPrincipal /></div>
      </section>

      <section className="bloque">
        <h2>¿De qué se trata tu duda?</h2>
        <p className="bloque-sub">Toca un tema para empezar con una pregunta de ejemplo. Después puedes cambiarla.</p>
        <div className="temas">
          {TEMAS.map(([icono, nombre, pregunta]) => (
            <Link key={icono} href={`/preguntar?q=${encodeURIComponent(pregunta)}`} className="tema">
              <IconoTema tema={icono} />
              <strong>{nombre}</strong>
              <span>{pregunta}</span>
            </Link>
          ))}
        </div>
      </section>

      <section className="bloque">
        <h2>Cómo responde Articla</h2>
        <ol className="pasos">
          {PASOS.map(([titulo, detalle], i) => (
            <li key={titulo}>
              <span className="paso-num" aria-hidden="true">{i + 1}</span>
              <IconoPaso paso={i + 1} />
              <strong>{titulo}</strong>
              <span>{detalle}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="bloque muestra">
        <div className="muestra-texto">
          <h2>Así se ve una respuesta</h2>
          <p>
            Una respuesta corta, lo que dice la ley con su cita, pasos concretos y, si la pregunta lo requiere,
            teléfonos de ayuda. Este es un ejemplo real entregado por Articla.
          </p>
          <Link href="/preguntar" className="btn btn-primario">Probar con mi pregunta</Link>
        </div>
        <div className="muestra-respuesta">
          <div className="msg-row-user"><div className="msg-user">{MUESTRA.pregunta}</div></div>
          <Respuesta consulta={MUESTRA} demo />
        </div>
      </section>

      <section className="bloque aviso-cita">
        <div className="timbre timbre-grande" aria-hidden="true">
          <span>LEY 19.496</span><span>ART. 21</span>
        </div>
        <div>
          <h2>Cada cita es un artículo real</h2>
          <p>
            Articla nunca muestra una cita que no haya leído. Si la ley no trata tu caso, te lo dice y te sugiere
            dónde pedir ayuda, como una Corporación de Asistencia Judicial.
          </p>
        </div>
      </section>
    </>
  );
}

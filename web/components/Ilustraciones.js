// Ilustraciones propias de Articla (SVG dibujado para el proyecto, sin imágenes de terceros).
// Usan currentColor y variables CSS para verse bien en modo claro y oscuro.

// Escena principal: una pregunta en lenguaje común se convierte en un documento con el artículo timbrado.
export function EscenaPrincipal() {
  return (
    <svg className="ilus-principal" viewBox="0 0 420 360" role="img"
      aria-label="Una pregunta escrita en un globo de conversación se transforma en un documento legal con un timbre rojo que indica el artículo exacto de la ley">
      {/* hoja de fondo */}
      <g transform="rotate(-5 250 200)">
        <rect x="150" y="70" width="220" height="270" rx="10" fill="var(--hoja)" stroke="var(--linea-fuerte)" strokeWidth="2" />
      </g>
      {/* documento principal */}
      <g transform="rotate(3 240 200)">
        <rect x="140" y="60" width="230" height="280" rx="10" fill="var(--hoja)" stroke="var(--tinta)" strokeWidth="2.5" />
        <rect x="165" y="88" width="120" height="12" rx="6" fill="var(--tinta)" />
        <rect x="165" y="112" width="180" height="7" rx="3.5" fill="var(--linea-fuerte)" />
        <rect x="165" y="128" width="165" height="7" rx="3.5" fill="var(--linea-fuerte)" />
        <rect x="165" y="144" width="175" height="7" rx="3.5" fill="var(--linea-fuerte)" />
        {/* párrafo destacado: el artículo citado */}
        <rect x="158" y="166" width="195" height="62" rx="6" fill="var(--verificado-fondo)" />
        <rect x="170" y="178" width="150" height="7" rx="3.5" fill="var(--verificado)" />
        <rect x="170" y="194" width="165" height="7" rx="3.5" fill="var(--verificado)" opacity=".65" />
        <rect x="170" y="210" width="120" height="7" rx="3.5" fill="var(--verificado)" opacity=".65" />
        <rect x="165" y="246" width="170" height="7" rx="3.5" fill="var(--linea-fuerte)" />
        <rect x="165" y="262" width="140" height="7" rx="3.5" fill="var(--linea-fuerte)" />
        {/* timbre (se "estampa" al cargar la página) */}
        <g className="estampa">
        <g transform="rotate(-12 300 300)">
          <rect x="238" y="276" width="124" height="50" rx="6" fill="none" stroke="var(--timbre)" strokeWidth="3" />
          <rect x="244" y="282" width="112" height="38" rx="4" fill="none" stroke="var(--timbre)" strokeWidth="1.5" strokeDasharray="4 3" />
          <text x="300" y="299" textAnchor="middle" fontSize="13" fontWeight="800" fill="var(--timbre)" fontFamily="var(--f-titulo)">LEY 18.101</text>
          <text x="300" y="315" textAnchor="middle" fontSize="12" fontWeight="700" fill="var(--timbre)" fontFamily="var(--f-titulo)">ART. 1</text>
        </g>
        </g>
      </g>
      {/* globo de la pregunta */}
      <g>
        <path d="M24 46 h170 a16 16 0 0 1 16 16 v62 a16 16 0 0 1 -16 16 h-118 l-26 24 v-24 h-26 a16 16 0 0 1 -16 -16 v-62 a16 16 0 0 1 16 -16z"
          fill="var(--tinta)" />
        <text x="34" y="80" fontSize="15" fontWeight="700" fill="var(--papel)" fontFamily="var(--f-texto)">¿Me pueden subir</text>
        <text x="34" y="100" fontSize="15" fontWeight="700" fill="var(--papel)" fontFamily="var(--f-texto)">el arriendo a mitad</text>
        <text x="34" y="120" fontSize="15" fontWeight="700" fill="var(--papel)" fontFamily="var(--f-texto)">de contrato?</text>
      </g>
      {/* flecha que une pregunta y documento */}
      <path d="M118 176 C 110 230, 120 262, 150 280" fill="none" stroke="var(--timbre)" strokeWidth="2.5" strokeDasharray="6 6" strokeLinecap="round" />
      <path d="M140 270 l12 11 l-16 4" fill="none" stroke="var(--timbre)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

const trazo = { fill: 'none', stroke: 'currentColor', strokeWidth: 2, strokeLinecap: 'round', strokeLinejoin: 'round' };

export function IconoTema({ tema }) {
  const d = {
    trabajo: (<><rect x="4" y="9" width="24" height="17" rx="3" {...trazo} /><path d="M11 9V6.5A2.5 2.5 0 0 1 13.5 4h5A2.5 2.5 0 0 1 21 6.5V9M4 16h24M14 16v3h4v-3" {...trazo} /></>),
    arriendo: (<><path d="M5 15 16 5l11 10M8 13v13h16V13" {...trazo} /><circle cx="14" cy="20" r="2.5" {...trazo} /><path d="M16.5 20H21v3" {...trazo} /></>),
    familia: (<><circle cx="11" cy="9" r="3.5" {...trazo} /><circle cx="22" cy="11" r="2.8" {...trazo} /><path d="M4 26c0-4.5 3-8 7-8s7 3.5 7 8M17 26c0-3.4 2.2-6 5-6s5 2.6 5 6" {...trazo} /></>),
    consumo: (<><path d="M4 6h3l3 14h14l3-10H9" {...trazo} /><circle cx="12" cy="25" r="2" {...trazo} /><circle cx="22" cy="25" r="2" {...trazo} /></>),
    transito: (<><path d="M16 4 28 16 16 28 4 16z" {...trazo} /><path d="M16 10v8M16 21.5v.5" {...trazo} /></>),
    violencia: (<><path d="M16 4 26 8v7c0 6.5-4.3 11.2-10 13-5.7-1.8-10-6.5-10-13V8z" {...trazo} /><path d="M12 16l3 3 5-6" {...trazo} /></>),
    prevision: (<><circle cx="16" cy="16" r="11" {...trazo} /><path d="M16 9v7l5 3" {...trazo} /></>),
    herencia: (<><path d="M6 27h20M8 27V13M24 27V13M16 27V13M5 13h22L16 5z" {...trazo} /></>),
  }[tema];
  return <svg className="icono-tema" viewBox="0 0 32 32" aria-hidden="true">{d}</svg>;
}

// Pasos de "cómo responde Articla" (sí es una secuencia, por eso van numerados en la página).
export function IconoPaso({ paso }) {
  const d = {
    1: (<><path d="M5 7h22v14H14l-6 5v-5H5z" {...trazo} /><path d="M10 12h12M10 16h8" {...trazo} /></>),
    2: (<><circle cx="14" cy="14" r="8" {...trazo} /><path d="m20 20 7 7M11 12h6M11 16h4" {...trazo} /></>),
    3: (<><rect x="7" y="4" width="18" height="24" rx="2" {...trazo} /><path d="M11 10h10M11 14h10" {...trazo} /><rect x="12" y="18" width="10" height="6" rx="1" {...trazo} /></>),
  }[paso];
  return <svg className="icono-paso" viewBox="0 0 32 32" aria-hidden="true">{d}</svg>;
}

export function Balanza() {
  return (
    <svg className="ilus-chica" viewBox="0 0 120 100" aria-hidden="true">
      <path d="M60 14v70M38 88h44M24 30h72" {...trazo} strokeWidth="3" />
      <circle cx="60" cy="14" r="5" fill="var(--timbre)" />
      <path d="M24 30 12 58h24zM96 30 84 58h24z" {...trazo} strokeWidth="2.5" />
      <path d="M10 58a14 6 0 0 0 28 0M82 58a14 6 0 0 0 28 0" {...trazo} strokeWidth="2.5" />
    </svg>
  );
}

export function Carpeta() {
  return (
    <svg className="ilus-chica" viewBox="0 0 120 100" aria-hidden="true">
      <path d="M14 28h32l8 8h52v46a4 4 0 0 1-4 4H18a4 4 0 0 1-4-4z" {...trazo} strokeWidth="3" />
      <path d="M30 56h44M30 68h30" {...trazo} strokeWidth="3" opacity=".5" />
    </svg>
  );
}

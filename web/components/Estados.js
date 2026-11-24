// Estados visibles de la interfaz: cargando, vacío y error. Una pantalla en blanco es un error de diseño.
export function Cargando({ texto = 'Cargando…' }) {
  return (
    <div className="estado" role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" /> {texto}
    </div>
  );
}

export function Vacio({ titulo, children }) {
  return (
    <div className="estado vacio">
      <strong>{titulo}</strong>
      {children ? <div>{children}</div> : null}
    </div>
  );
}

export function ErrorCaja({ mensaje, onReintentar }) {
  return (
    <div className="estado error" role="alert">
      <span>{mensaje}</span>
      {onReintentar ? (
        <button className="btn btn-secondary btn-sm" onClick={onReintentar}>Reintentar</button>
      ) : null}
    </div>
  );
}

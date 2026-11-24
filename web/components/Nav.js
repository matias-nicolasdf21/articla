'use client';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

// Arriba en computador; en el celular, barra fija abajo con las secciones principales (como una app).
const PRINCIPALES = [
  ['/', 'Inicio', 'M4 11 12 4l8 7v9h-5v-6H9v6H4z'],
  ['/preguntar', 'Preguntar', 'M4 5h16v11H11l-5 4v-4H4z'],
  ['/historial', 'Historial', 'M12 7v5l3 2M12 3a9 9 0 1 1-9 9'],
  ['/biblioteca', 'Leyes', 'M5 4h10l4 4v12H5zM9 11h6M9 15h6'],
];
const SECUNDARIOS = [['/privacidad', 'Privacidad'], ['/aviso-legal', 'Aviso legal']];

export default function Nav() {
  const ruta = usePathname();
  const activo = (href) => (href === '/' ? ruta === '/' : ruta.startsWith(href));
  return (
    <>
      <header className="cabecera">
        <Link href="/" className="marca" aria-label="Articla, inicio">
          <span className="sello" aria-hidden="true">A</span>
          <span>Articla</span>
        </Link>
        <nav aria-label="Principal" className="nav-arriba">
          {[...PRINCIPALES.map(([h, t]) => [h, t === 'Leyes' ? 'Biblioteca de leyes' : t]), ...SECUNDARIOS].map(([href, texto]) => (
            <Link key={href} href={href} className={activo(href) ? 'activo' : ''} aria-current={activo(href) ? 'page' : undefined}>
              {texto}
            </Link>
          ))}
        </nav>
        <Link href="/privacidad" className="cabecera-movil-enlace">Privacidad</Link>
      </header>
      <nav aria-label="Secciones" className="nav-abajo">
        {PRINCIPALES.map(([href, texto, icono]) => (
          <Link key={href} href={href} className={activo(href) ? 'activo' : ''} aria-current={activo(href) ? 'page' : undefined}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d={icono} fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" /></svg>
            <span>{texto}</span>
          </Link>
        ))}
      </nav>
    </>
  );
}

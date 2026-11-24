import './globals.css';
import Link from 'next/link';
import { headers } from 'next/headers';
import { Atkinson_Hyperlegible, Bricolage_Grotesque } from 'next/font/google';
import Nav from '../components/Nav';

// Las fuentes se descargan al construir y quedan dentro de la app (no dependen de Google al usarla).
const titulo = Bricolage_Grotesque({ subsets: ['latin'], variable: '--f-bricolage', display: 'swap' });
const texto = Atkinson_Hyperlegible({ subsets: ['latin'], weight: ['400', '700'], variable: '--f-atkinson', display: 'swap' });

const DESCRIPCION = 'Respuestas claras a dudas legales cotidianas, citando el artículo exacto de la ley chilena.';

// La dirección se toma de cada petición (localhost o el link del túnel), para que la vista previa
// al compartir el enlace (WhatsApp, redes) apunte a la imagen correcta.
export async function generateMetadata() {
  let base;
  try {
    const h = await headers();
    const host = h.get('x-forwarded-host') || h.get('host');
    const proto = h.get('x-forwarded-proto') || (host && host.startsWith('localhost') ? 'http' : 'https');
    if (host) base = new URL(`${proto}://${host}`);
  } catch {
    base = undefined;
  }
  return {
    metadataBase: base,
    title: { default: 'Articla · Orientación legal con la ley chilena', template: '%s · Articla' },
    description: DESCRIPCION,
    openGraph: { title: 'Articla', description: DESCRIPCION, type: 'website', locale: 'es_CL' },
  };
}

export const viewport = { width: 'device-width', initialScale: 1, themeColor: '#14213D' };

export default function RootLayout({ children }) {
  return (
    <html lang="es" className={`${titulo.variable} ${texto.variable}`}>
      <body>
        <Nav />
        <main className="contenido">{children}</main>
        <footer className="pie">
          <div className="pie-marca">
            <span className="sello" aria-hidden="true">A</span>
            <p>Articla entrega orientación general basada en el texto oficial de las leyes chilenas. No reemplaza la asesoría de un abogado o abogada.</p>
          </div>
          <nav className="pie-enlaces" aria-label="Información">
            <Link href="/aviso-legal">Aviso legal</Link>
            <Link href="/privacidad">Privacidad</Link>
            <a href="https://www.bcn.cl/leychile" target="_blank" rel="noreferrer">Fuente oficial: LeyChile (BCN)</a>
            <a href="https://github.com/matias-nicolasdf21/articla" target="_blank" rel="noreferrer">Código en GitHub</a>
          </nav>
          <p className="pie-credito">Proyecto INGT1003 Arquitectura de Desarrollo, Universidad Mayor, 2026. Matías del Fierro y Camilo González.</p>
        </footer>
      </body>
    </html>
  );
}

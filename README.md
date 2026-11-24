# Articla

**Para cualquier persona en Chile que enfrenta una duda legal cotidiana y no tiene acceso rápido ni económico a orientación jurídica, Articla entrega una respuesta clara en menos de un minuto, citando el artículo exacto de la ley chilena que la respalda.**

Proyecto semestral de INGT1003 Arquitectura de Desarrollo (Móvil y Web) · Universidad Mayor · Prof. Carlos Muñoz S.

| Integrante | Usuario de GitHub |
|---|---|
| Matías del Fierro | `matias-nicolasdf21` |
| Camilo González | `camilogonzalez114` |

**Documentos:** [Documento final](docs/Articla_Documento_Final.pdf) · [Manual de uso e instalación](docs/Manual_Articla.pdf) · [Manual técnico y de recuperación](docs/Manual_Tecnico_Articla.pdf) · [Documento técnico Hito 2](docs/Articla_Documento_Tecnico_Hito2.pdf) · [Propuesta Hito 1](docs/Articla_Propuesta_Hito1.pdf) · [Prototipo Hito 1](https://matias-nicolasdf21.github.io/articla/prototipo_articla_fuente.html)


---

## Cómo levantarlo (un solo comando)

Requisitos: [Docker Desktop](https://www.docker.com/products/docker-desktop/) abierto (en Windows, con WSL 2).

1. Copia `.env.example` como `.env` y cambia `POSTGRES_PASSWORD` (y la misma clave dentro de `DATABASE_URL`).
2. *(Opcional, recomendado)* Pega tu clave gratuita de Gemini en `GEMINI_API_KEY` ([Google AI Studio](https://aistudio.google.com/apikey)). Sin clave, Articla funciona igual y responde mostrando los artículos encontrados.
3. En la carpeta del proyecto:

   ```
   docker compose up --build
   ```

4. Espera el mensaje `[preparar] listo` y luego `Uvicorn running`. **La primera vez tarda varios minutos**: descarga imágenes, carga las 15 normas base (unos 6.900 artículos) y calcula sus embeddings. Las veces siguientes parte en segundos.
5. Abre **http://localhost:3000** (la aplicación). La API y su documentación están en http://localhost:8000/docs.

Para detenerlo: `Ctrl + C` y luego `docker compose down` (los datos se conservan). Para empezar de cero: `docker compose down -v`.

**Datos de prueba:** no hay usuarios ni contraseñas (Articla no pide cuenta). Preguntas de ejemplo:
- "Mi arrendador quiere subirme el arriendo a mitad de contrato, ¿puede hacerlo?"
- "Me despidieron sin aviso, ¿qué me corresponde?"
- "Compré un producto que vino fallado, ¿puedo pedir la devolución?"

### Fallas frecuentes

| Síntoma | Solución |
|---|---|
| `port is already allocated` (5432, 8000 o 3000) | Otra aplicación usa ese puerto (por ejemplo, la base del Hito 2). Detén la otra con `docker compose down` en su carpeta, o cierra el programa que lo usa. |
| La página dice "El servicio no está disponible" | La API todavía está preparando la base. Espera `[preparar] listo` en la consola. |
| Las respuestas dicen "Artículos encontrados" y no "Respuesta redactada con IA" | Falta `GEMINI_API_KEY` en `.env`, la clave no es válida o se agotó la cuota gratuita. Revisa la consola de la API (líneas `[gemini] ...`) y reinicia con `docker compose up`. |
| Docker no inicia en Windows | Abre PowerShell como administrador, ejecuta `wsl --update` y reinicia el computador. |

## Arquitectura

Monolito modular por capas:

```
web/                  # Presentación: Next.js (React). Pantallas, validación en cliente, estados de carga/vacío/error.
  app/api/[...path]/  #   puente que reenvía /api/v1/* a la API (sin reglas de negocio)
app/
  routers/            # Ruteo HTTP: valida la entrada y llama al servicio. Sin lógica de negocio ni SQL.
  services/           # Negocio: reglas, recuperación de artículos (RAG), validación de citas.
  repositories/       # Datos: todas las consultas SQL.
  ia/                 # Servicios externos aislados: embeddings (modelo abierto) y Gemini (redacción).
  schemas/            # Contratos de entrada y salida (Pydantic).
  ingesta/            # Lector del XML oficial de LeyChile.
scripts/              # preparar.py (migraciones + carga + embeddings), carga y descarga de LeyChile.
data/leychile/        # XML oficiales de las normas base (el DFL 1 de 2000 trae el Código Civil y 5 leyes refundidas).
db/                   # schema.sql (crea la base desde cero) y modelo_datos.png.
docs/                 # Documentos PDF, diagramas, tabla de la API y colección de Postman.
tests/                # Pruebas de la capa de negocio.
```

**Cómo responde una pregunta:** la API busca los artículos más relacionados por dos vías (por significado, con embeddings y pgvector; y por palabras, con la búsqueda de texto en español de PostgreSQL), los combina y se los entrega a Gemini con un código cada uno. Gemini redacta en lenguaje simple e indica qué códigos usó; la API comprueba que cada cita exista entre los artículos entregados y descarta cualquier otra. Si Gemini no está disponible, responde mostrando los artículos.

## Desarrollo sin Docker (opcional)

```
docker compose up -d db                               # solo la base
python -m venv .venv && .venv\Scripts\activate        # en Windows
pip install -r requirements.txt -r requirements-ia.txt
python -m scripts.preparar                            # migraciones, carga del corpus y embeddings
python -m uvicorn app.main:app --reload               # API en :8000
cd web && npm install && npm run dev                  # interfaz en :3000 (requiere Node.js 20+)
```

Pruebas: `docker compose exec api python -m unittest discover -s tests` (54 pruebas) · Pruebas de la API: importar `docs/Articla_API.postman_collection.json` en Postman y ejecutar el Collection Runner.

## Corpus

Solo texto oficial y público de LeyChile (Biblioteca del Congreso Nacional). No usamos libros.

- **Corpus base (incluido en el repositorio):** 15 normas de `data/normas.json` — Código Civil, Código del Trabajo, Código Penal, Código de Comercio, Código de Procedimiento Civil, Código Procesal Penal, Constitución Política, leyes 18.101 (arriendo), 19.496 (consumidor) y 19.628 (datos personales), y los textos refundidos de las leyes 14.908 (pensiones de alimentos), 16.618 (menores), 4.808 (Registro Civil), 17.344 (cambio de nombre) y 16.271 (herencias) — con unos 6.900 artículos vigentes. Los artículos que solo modifican otra ley (“Modifícase…”, “Reemplázase…”) se marcan y no se usan para responder. Se carga solo al iniciar.
- **Corpus completo (proceso ETL):** todas las leyes de los datos abiertos de la BCN. En nuestro equipo: 15.959 leyes listadas, 15.809 descargadas (150 sin XML en LeyChile), 14.856 con artículos vigentes y 87.168 artículos, más el corpus base: **unos 93.800 artículos**. No va en Git por tamaño. Se reproduce con:

  ```
  docker compose exec api python -m scripts.corpus_completo listar
  docker compose exec api python -m scripts.corpus_completo descargar   # horas: LeyChile limita la velocidad
  docker compose exec api python -m scripts.corpus_completo cargar
  docker compose exec api python -m scripts.calcular_embeddings
  ```
  o restaurando un respaldo de la base (ver el manual técnico, capítulos 8 y 9).

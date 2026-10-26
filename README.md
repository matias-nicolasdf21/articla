# Articla — Asistente legal con fuentes verificables

**Promesa:** Para cualquier persona en Chile que enfrenta una duda legal cotidiana y no tiene acceso rápido ni económico a orientación jurídica, Articla entrega una respuesta clara en menos de un minuto, citando el artículo exacto de la ley chilena que la respalda.

## Integrantes

| Nombre | Usuario de GitHub | Rol |
|---|---|---|
| Matías del Fierro | [matias-nicolasdf21](https://github.com/matias-nicolasdf21) | Coordinación y repositorio |
| Camilo González | [camilogonzalez114](https://github.com/camilogonzalez114) | Documento de propuesta y prototipo |

## Enlaces — Hito 1

- **Prototipo navegable:** https://claude.ai/artifact/GVKR1kge7CbDKUdRSczxxp
- **Documento de propuesta (PDF):** `docs/Articla_Propuesta_Hito1.pdf`
- **Láminas de la presentación (PDF):** `docs/Articla_Laminas_Hito1.pdf`
- **Mapa del producto:** `docs/mapa_producto.png`
- **Diagrama de arquitectura:** `docs/diagrama_arquitectura.png`

## Qué es Articla

Asistente legal conversacional que responde preguntas de orientación jurídica en lenguaje simple, citando siempre el artículo exacto de la ley que respalda la respuesta. El corpus se construye con el texto oficial de LeyChile (Biblioteca del Congreso Nacional, dominio público) y, como fuente complementaria y solo con autorización, libros de la Facultad de Derecho de la Universidad de Chile.

## Arquitectura (resumen)

- **Cliente:** React + Next.js (el chat es una ruta renderizada en el cliente; las páginas informativas son estáticas). Diseño responsive / PWA.
- **Servidor:** API REST en Python + FastAPI (orquestador RAG).
- **Datos:** PostgreSQL + pgvector (corpus vectorizado) y PostgreSQL relacional (consultas, historial).
- **Generación:** modelo de lenguaje (LLM) consumido vía API, servicio externo aislado tras una capa de servicio propia para poder reemplazarlo.

Detalle en `docs/Articla_Propuesta_Hito1.pdf`, secciones 5 y 6.

## Métricas de éxito (Hito 3)

Respuesta en menos de 1 minuto y exactitud de citas de al menos 90% sobre una batería de preguntas verificadas contra LeyChile.

## Privacidad

Articla no pide nombre, RUT ni dirección para consultar. Las consultas se guardan 90 días y pueden borrarse antes.

## Estado — Hito 1

Propuesta, arquitectura y prototipo navegable (sin backend ni IA conectada todavía; solo la primera pregunta de ejemplo tiene respuesta de demostración). API y motor de recuperación se construyen en el Hito 2.

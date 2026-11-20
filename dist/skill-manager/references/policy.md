# Política de selección de skills

## Principio

Una skill es una instrucción que se carga en contexto: cuesta tokens y atención. El objetivo no es activar poco por un tope arbitrario, sino activar **exactamente lo que la tarea necesita** y apagar el resto.

- **Sin máximo por tarea.** Si la tarea necesita cinco skills, se activan cinco.
- **El ruido se controla con `sync`**, no limitando la selección.
- Si dos skills cubren lo mismo, quedate con la más específica.

## Inicio de sesión

Las skills **fijas de sesión** son las que se usan en casi todas las tareas de esa sesión. Se marcan una vez y `sync` nunca las mueve.

1. `skillctl session-begin`
2. `skillctl session-keep <slug...>`
3. Avisar al usuario en una línea qué se fijó.

Criterio: si una skill se va a usar en la mayoría de las tareas de la sesión, fijala. Si es para una tarea puntual, no la fijes: activala con `ensure` y dejala ir con `sync`.

Ejemplos:

| Sesión | Fijas razonables |
|---|---|
| Backend Python | `modern-python`, `pytest-patterns` |
| Análisis de datos | `pandas-analysis`, `data-visualization` |
| Lanzamiento de un producto | `marketing-copy`, `seo-copywriting`, `landing-page-design` |
| Mantenimiento de legacy | `systematic-debugging`, `code-review` |
| Mixta y exploratoria | solo `skill-manager` (no fijar nada) |

## Cómo elegir por tarea

1. Extraé de la tarea el **sustantivo técnico** y la **acción**.
   - "arreglá el groupby de pandas" → sustantivo: pandas; acción: debugging.
   - "hacé un commit" → acción: commit.
   - "publicá el lanzamiento en LinkedIn" → acción: marketing/social.
2. Buscá con el sustantivo, no con la frase entera:
   - Bien: `search "pandas groupby"`
   - Mal: `search "arreglá el groupby de pandas que falla"`
3. Sumá todas las que aporten. Preferí la específica sobre la genérica.
   - `pandas-analysis` > `data-cleaning` para un groupby.
   - `fastapi-patterns` > `modern-python` para un endpoint.
4. Si no hay match claro, no actives nada. Es una respuesta válida.

## Ejemplos

| Tarea | Skills | Por qué |
|---|---|---|
| "Hola, ¿cómo estás?" | ninguna | Trivial |
| "Commit y PR de estos cambios" | `git-commits` | Una sola skill específica |
| "Revisá este PR" | `code-review` | Una sola |
| "Este test falla intermitentemente" | `systematic-debugging`, `pytest-patterns` | Debug + test |
| "Optimizá esta consulta SQL" | `sql-optimization` | Una sola |
| "Armá un pipeline de dbt" | `dbt-models` | Una sola |
| "Explicá este notebook" | `jupyter-notebooks` | Una sola |
| "Escribí un post técnico y posicionarlo" | `developer-blog-posts`, `seo-copywriting` | Contenido + SEO |
| "Landing para mi proyecto" | `landing-page-design`, `marketing-copy` | Diseño + copy |
| "Instalá una skill para Stripe" | `stripe-integration` | Búsqueda + ensure |
| "No sé qué framework frontend uso" | ninguna | Falta información; preguntar |

## Requisito nuevo a mitad de tarea

- Si el requisito es **complementario** (mismo trabajo, otra herramienta), no reinicies: `search` + `ensure` con todas las que hagan falta.
- Si el requisito **cambia el tema** (de backend a marketing, de datos a deploy), hacé `begin` con el nuevo resumen y volvé a elegir.
- Si el requisito no necesita ninguna skill, no cargues nada y seguí.

## Desactivación

- `sync` mueve a `skills-disabled/` todo lo que no sea core, fija de sesión, activa o fijada global.
- El core por defecto es solo `skill-manager`.
- `session-keep` fija para la sesión actual; `pin` fija para todas las sesiones.
- Las skills ya cargadas siguen en el contexto de la conversación hasta que se compacte; `sync` solo evita que se sigan anunciando.
- Si el usuario pide algo que estaba desactivado, `ensure` lo reactiva sin volver a descargarlo.
- Cambiar de sesión de OpenCode reinicia automáticamente `active` y `session_core` (detectado por `OPENCODE_SESSION_ID`).

## Seguridad

- El catálogo se indexa desde `https://opencodeskills.dev/llms-full.txt`.
- `ensure` solo acepta URLs de `opencodeskills.dev`.
- Rechaza zips con rutas absolutas, `..` o symlinks.
- Rechaza skills con `curl | sh`, `wget | sh`, `sudo` o `rm -rf /`.
- La config de OpenCode tiene `* -> ask` para skills nuevas: la descarga puede ser automática, pero la carga requiere aprobación.
- Nunca desactives `skill-manager`: es el que ejecuta la política.

## Estado

Archivo por defecto: `<raíz-de-skills>/../skill-manager/state.json`.

| Instalación | Ruta |
|---|---|
| Global | `~/.config/opencode/skill-manager/state.json` |
| Proyecto | `.opencode/skill-manager/state.json` |

```json
{
  "session_id": "ses_...",
  "task": "descripción breve",
  "active": ["pandas-analysis", "data-visualization"],
  "core": ["skill-manager"],
  "session_core": ["skill-manager", "modern-python", "pytest-patterns"],
  "pinned": [],
  "updated": "2026-11-19T22:00:00-0300"
}
```

## Portabilidad

El script calcula la raíz de skills desde su propia ubicación:

```text
<raíz-de-skills>/skill-manager/scripts/skillctl
                  └── parents[2] = <raíz-de-skills>
```

Por eso funciona igual en `~/.config/opencode/skills` y en `.opencode/skills`. Podés sobreescribir las rutas:

| Variable | Default |
|---|---|
| `OPENCODE_SKILLS_DIR` | dos niveles arriba del script |
| `OPENCODE_SKILLS_DISABLED` | `<raíz>/../skills-disabled` |
| `OPENCODE_SKILL_MANAGER_STATE` | `<raíz>/../skill-manager/state.json` |
| `OPENCODE_SKILL_CATALOG_DIR` | `<raíz>/../skill-catalog` |

Ejemplo para gestionar otra raíz:

```bash
OPENCODE_SKILLS_DIR=~/proyecto/.opencode/skills \
  python3 ~/proyecto/.opencode/skills/skill-manager/scripts/skillctl status
```

Para volver a tener todas las skills activas: `skillctl restore`. Para fijar una skill en todas las sesiones: `skillctl pin <slug>`. Para fijarla solo en la actual: `skillctl session-keep <slug>`.

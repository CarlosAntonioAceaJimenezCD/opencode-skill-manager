---
name: skill-manager
description: "Use at the start of every new session to mark the persistent skills that must never be deactivated, and at the start of every new task, and whenever the user adds a requirement that changes the kind of work, to choose and install every skill the task needs and disable the ones it does not. Also use when the user asks to find, add, remove, enable, disable, pin or list skills."
license: MIT
---

# Skill Manager

Gestiona el ciclo de vida de las skills para que la sesión cargue lo necesario y nada más.

## Ruta del script

La herramienta `skill` te da el directorio base de esta skill. En los comandos de abajo, `skillctl` significa:

```bash
python3 "<base>/scripts/skillctl"
```

Usá `python3` para no depender del bit de ejecución del archivo.

## Modelo

Hay tres niveles:

| Nivel | Cuándo se define | Sobrevive a `sync` | Se limpia |
|---|---|---|---|
| `core` | en `state.json` | siempre | nunca |
| fijas de sesión (`session_core`) | al inicio de la sesión | sí | con `session-end` o sesión nueva |
| activas de tarea (`active`) | por tarea | mientras dure la tarea | con `begin`, `end` o `session-end` |

**No hay máximo por tarea.** Activá todas las skills que aporten. Lo que evita el ruido es `sync`, no un tope artificial.

## Inicio de sesión

1. `skillctl session-begin` — detecta `OPENCODE_SESSION_ID` y reinicia lo efímero.
2. Elegí las skills **transversales** de esta sesión: las que vas a usar en casi todas las tareas. Ejemplos:
   - sesión de backend Python: `modern-python`, `pytest-patterns`.
   - sesión de datos: `pandas-analysis`, `data-visualization`.
   - sesión de lanzamiento: `marketing-copy`, `seo-copywriting`.
3. `skillctl session-keep <slug...>` para fijarlas.
4. Decile al usuario en una línea cuáles fijaste. Si objeta, usá `session-drop` / `session-keep`.

No fijes diez "por las dudas": solo las que realmente cruzan toda la sesión. Todo lo demás se activa por tarea.

Si dudás entre dos skills, o necesitás los criterios completos, leé `references/policy.md`. Ese archivo no se carga solo: tenés que leerlo cuando haga falta.

## Flujo por tarea

1. `skillctl begin "<resumen de la tarea>"` — solo si la tarea es nueva o cambió de tema. Si es un requisito complementario, **no** hagas `begin`: conservá las activas.
2. `skillctl search "<palabras clave>"` — devuelve hasta 8 candidatas con puntaje.
3. Elegí **todas** las que aporten. Si no hay match claro, no actives nada y decilo en una línea. Si dos cubren lo mismo, preferí la más específica.
4. `skillctl ensure <slug...>` — acepta varios slugs. Por cada uno:
   - lo instala desde el catálogo si falta,
   - lo reactiva si estaba desactivado,
   - lo marca activo en el estado.
5. Cargá cada elegida con la herramienta `skill`.
6. `skillctl sync` — mueve a `skills-disabled/` toda skill que no sea core, fija de sesión, activa o fijada global. Ante la duda, `sync --dry-run` primero.
7. Al terminar la tarea, `skillctl end`. Las fijas de sesión siguen vigentes.

## Resultado esperado

Al cerrar la tarea, informá en pocas líneas:

- qué buscaste y qué candidatas aparecieron,
- qué skills activaste y por qué,
- qué skills desactivaste,
- qué fijas de sesión quedaron,
- si hubo descarga o pedido de permiso.

## Reglas de seguridad

- Solo se descarga desde `opencodeskills.dev`.
- El script valida frontmatter, nombre, largo de la descripción y rutas del zip.
- Si detecta `curl | sh`, `sudo` o `rm -rf /`, se niega a instalar.
- La carga de una skill nueva pedirá confirmación por la config `permissions: * -> ask`.
- Nunca desactives `skill-manager`.
- No ejecutes scripts internos de una skill descargada; solo cargala con `skill`.

## Efectos secundarios

- Descarga el catálogo y los zips solo desde `opencodeskills.dev`.
- Mueve carpetas entre `skills/` y `skills-disabled/`.
- Escribe estado en `skill-manager/state.json` y caché en `skill-catalog/`, junto a la raíz de skills.
- No ejecuta código de las skills descargadas.
- No modifica `opencode.json` ni credenciales.

## Comandos

| Comando | Efecto |
|---|---|
| `skillctl refresh` | Actualiza el índice del catálogo (caché de 7 días) |
| `skillctl search "<texto>"` | Busca y puntúa candidatas |
| `skillctl session-begin [slug...]` | Inicia la sesión y fija skills transversales |
| `skillctl session-keep <slug...>` | Suma skills al set fijo de la sesión |
| `skillctl session-drop <slug...>` | Quita skills del set fijo de la sesión |
| `skillctl session-end` | Cierra la sesión y libera las fijas |
| `skillctl begin "<tarea>"` | Reinicia el set activo (conserva las fijas) |
| `skillctl ensure <slug...>` | Instala/reactiva y marca activas, sin límite |
| `skillctl sync` | Desactiva lo que no se usa |
| `skillctl sync --dry-run` | Muestra qué desactivaría, sin mover nada |
| `skillctl status` | Muestra sesión, tarea, fijas, activas y conteos |
| `skillctl list` | Lista activas y desactivadas |
| `skillctl enable <slug>` | Reactiva manualmente |
| `skillctl disable <slug>` | Desactiva manualmente (y la desfija) |
| `skillctl pin <slug>` | La fija para todas las sesiones |
| `skillctl unpin <slug>` | Quita la fijación global |
| `skillctl restore` | Reactiva todas las desactivadas |
| `skillctl end` | Cierra la tarea actual |

## Límites reales

- Una skill ya cargada **no se elimina del contexto**; deja de anunciarse para los pasos siguientes.
- La lista de skills se recalcula en cada paso, así que mover carpetas surte efecto sin reiniciar la sesión.
- Si el usuario menciona `@slug`, respetá esa elección aunque no sea la que vos elegirías.
- Si `sync` desactivó algo que hacía falta, `enable` o `ensure` lo recuperan sin volver a descargarlo.
- `pin` es global y permanente; `session-keep` es solo para la sesión actual.
- Si instalás la skill en una ruta no estándar, definí `OPENCODE_SKILLS_DIR` para que el script sepa qué raíz gestionar.

## Referencias

- `references/policy.md`: criterios de selección, ejemplos y reglas de desactivación.

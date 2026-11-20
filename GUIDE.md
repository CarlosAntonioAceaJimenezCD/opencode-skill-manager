# Guía completa de skill-manager

Referencia de uso de `skillctl`, el motor de `skill-manager`. Si recién empezás, leé primero el [README](README.md); acá está todo lo que se puede hacer.

## Cómo invocar `skillctl`

La herramienta `skill` de OpenCode informa el directorio base de la skill cuando la cargás. En todos los ejemplos:

```bash
skillctl = python3 "<base>/scripts/skillctl"
```

Es decir, si la base es `/home/usuario/.config/opencode/skills/skill-manager`:

```bash
python3 /home/usuario/.config/opencode/skills/skill-manager/scripts/skillctl status
```

Usá `python3` directamente para no depender del bit de ejecución. Si instalaste la skill en otra raíz, el script la detecta solo; si gestionás otra raíz distinta a la de su ubicación, definí `OPENCODE_SKILLS_DIR`.

Para invocar la skill desde el chat: `@skill-manager`, o dejá que se anuncie por su descripción.

## Modelo mental

| Grupo | Se define con | Sobrevive a `sync` | Dura hasta |
|---|---|---|---|
| `core` | `state.json` | siempre | siempre |
| fijas de sesión | `session-begin`, `session-keep` | sí | `session-end` o sesión nueva |
| activas de tarea | `begin`, `ensure` | sí | `end`, otro `begin` o sesión nueva |
| globales | `pin` | siempre | `unpin` |

`sync` solo mueve carpetas a `skills-disabled/`: nada se borra. Las skills ya cargadas en el contexto siguen ahí hasta que se compacte la conversación; `sync` evita que se sigan anunciando en los pasos siguientes.

Además de skills, el estado guarda dos listas de GitHub:

- `sources`: repos registrados con `source add`.
- `topics`: etiquetas registradas con `topic add`.

Ninguna de las dos se reinicia al cambiar de sesión.

## Flujo recomendado

```bash
# 1. Sesión nueva
skillctl session-begin
skillctl session-keep modern-python pytest-patterns

# 2. Cada tarea
skillctl begin "arreglar el pipeline de datos"
skillctl search "pandas groupby"
skillctl ensure pandas-analysis data-visualization
skillctl sync

# 3. Cerrar tarea y sesión
skillctl end
skillctl session-end
```

## Referencia de comandos

### `session-begin [slug...]`

Inicia la sesión. Detecta `OPENCODE_SESSION_ID`; si cambió, reinicia `active`, `task` y las fijas de sesión, y conserva `core`, `pinned`, `sources` y `topics`. Los slugs que pases como argumento se instalan si faltan y quedan fijos para la sesión.

```bash
skillctl session-begin
skillctl session-begin modern-python pytest-patterns
```

Salida:

```text
sesión: ses_e09a310a4ffexpNcfy5qjSTTNr
fijas: skill-manager, modern-python, pytest-patterns
```

### `session-keep <slug...>`

Suma skills al grupo fijo de la sesión. No tiene límite. Úsalo para lo transversal, no para todo.

```bash
skillctl session-keep pandas-analysis data-visualization
```

### `session-drop <slug...>`

Quita fijas de la sesión. Las skills del `core` no se pueden quitar.

```bash
skillctl session-drop data-visualization
```

### `session-end`

Cierra la sesión y libera todas las fijas (salvo `core`). No desactiva skills por sí solo.

```bash
skillctl session-end
```

### `begin "<tarea>"`

Reinicia el conjunto de skills activas y guarda el nombre de la tarea. Las fijas de sesión y las globales se conservan. Usalo solo cuando cambie el tema; si el requisito es complementario, seguí con `search` + `ensure`.

```bash
skillctl begin "publicar la versión 1.1.0"
```

### `search "<texto>"`

Indexa el catálogo (si la caché tiene más de 7 días lo renueva) y devuelve hasta 8 candidatas con puntaje. La columna `fuente` indica `opencodeskills`, `github:<repo>` o está vacía para entradas antiguas.

```bash
skillctl search "pandas groupby"
skillctl search "github"
```

Salida:

```text
score	slug	nombre	categoria	tagline	fuente
13	pandas-analysis	Pandas Analysis	Data	Clean, fast, reproducible DataFrame work	opencodeskills
```

La primera búsqueda descarga el índice completo; después usa caché.

### `ensure <slug...>`

Acepta varios slugs. Por cada uno: lo instala si falta, lo reactiva si estaba en `skills-disabled/` y lo marca activo. No hay tope. También acepta `owner/repo` de GitHub.

```bash
skillctl ensure pandas-analysis data-visualization
skillctl ensure CarlosAntonioAceaJimenezCD/opencode-skill-manager
```

Si un slug no está en ningún índice, falla con `ERROR <slug>: no está en el catálogo`.

### `sync` y `sync --dry-run`

Mueve a `skills-disabled/` toda skill que no sea core, fija de sesión, activa o global. Siempre mirá primero el simulacro si no estás seguro:

```bash
skillctl sync --dry-run
skillctl sync
```

Salida real:

```text
activas: skill-manager, skill-optimizer
se desactivan: 44
movidas: agent-tool-design, ai-agent-patterns, ...
```

Si `sync` se pasó de largo, `enable` o `ensure` recupera la skill sin volver a descargarla.

### `status`

Muestra sesión, tarea, fijas, activas, fuentes, topics y conteos. Es el primer comando a ejecutar cuando algo no cuadra.

```bash
skillctl status
```

### `list`

Lista las skills activas y las desactivadas, separadas por secciones.

```bash
skillctl list
```

### `enable <slug>`

Reactiva una skill desactivada moviéndola de vuelta desde `skills-disabled/`.

```bash
skillctl enable pandas-analysis
```

### `disable <slug>`

Desactiva una skill y la quita de `active`, `session_core` y `pinned`. `skill-manager` no se puede desactivar.

```bash
skillctl disable pandas-analysis
```

### `pin <slug>`

Fija una skill para todas las sesiones. Es distinto de `session-keep`, que solo dura la sesión actual. La fijación se guarda en `pinned` y `sync` nunca desactiva esa skill.

```bash
skillctl pin modern-python
```

### `unpin <slug>`

Quita una fijación global. La skill sigue instalada; solo deja de estar protegida por `sync`.

```bash
skillctl unpin modern-python
```

### `restore`

Reactiva todas las desactivadas de una vez. Es el botón de «deshacer» de `sync`.

```bash
skillctl restore
```

### `end`

Cierra la tarea actual y limpia `active` y `task`. Las fijas de sesión siguen vigentes. No mueve skills: eso lo hace `sync`.

```bash
skillctl end
```

### `refresh`

Reconstruye el índice combinando opencodeskills.dev, las fuentes de `source` y los topics de `topic`. Se ejecuta solo cuando la caché vence, pero podés forzarlo.

```bash
skillctl refresh
```

Si una fuente falla, avisa y sigue con las demás. Si ninguna fuente responde, el comando termina con error y no sobrescribe el índice anterior.

### `source add <repo...>`

Registra repositorios de GitHub como fuente permanente. Acepta `owner/repo`, `owner/repo@rama`, URLs `https://github.com/owner/repo` y URLs `/tree/<rama>`.

```bash
skillctl source add owner/repo
skillctl source add https://github.com/otro/repo/tree/dev
```

Después corré `skillctl refresh` para indexarlos.

### `source list`

Muestra las fuentes registradas, con la rama normalizada.

```bash
skillctl source list
```

### `source remove <repo...>`

Quita fuentes registradas. Acepta el mismo formato que `source add`.

```bash
skillctl source remove owner/repo
```

### `topic add <tag...>`

Registra topics de GitHub. En cada `refresh` se buscan repos con esos topics y sus skills entran al índice con categoría `GitHub:<tag>`.

```bash
skillctl topic add opencode-skills python
```

### `topic list`

Lista los topics registrados.

```bash
skillctl topic list
```

### `topic remove <tag...>`

Quita topics registrados. Acepta con o sin `#`.

```bash
skillctl topic remove python
```

### `topic search [tag...]`

Busca repositorios por topic, descarta los que no contienen `SKILL.md` y muestra cuántas skills tiene cada uno, sus etiquetas y su URL. Sin argumentos usa los topics registrados.

```bash
skillctl topic search opencode-skills python
```

Salida:

```text
fabiandistler/agents [main]: 30 skills → ai-ml, architecture-pattern-advisor, architecture, blue-team
  temas: claude-skills, codex-skill, opencode-skills, skill-md, skills
  https://github.com/fabiandistler/agents
```

Por defecto consulta hasta 20 repos por etiqueta. Cambialo con `GITHUB_TOPIC_LIMIT`.

## GitHub: fuentes y etiquetas

Un repo se indexa de dos maneras:

1. Si publica `index.json` en la raíz o en `docs/`, se usa ese catálogo y se descargan sus archivos desde `raw.githubusercontent.com`.
2. Si no, se recorre el árbol con la API, se leen los `SKILL.md` y se descarga el zipball. Se ignoran `docs/`, `dist/` y carpetas ocultas para no instalar copias generadas.

Para repos privados o para no agotar el límite anónimo de la API:

```bash
export GITHUB_TOKEN=ghp_...
skillctl source add mi-organizacion/skills-privadas
skillctl refresh
```

El token se envía solo en la cabecera `Authorization`; no se imprime ni se guarda en el estado. Nunca lo subas al repositorio ni lo pases como argumento.

Un topic es una pista declarada por el autor, no una garantía de compatibilidad. Revisá siempre el `SKILL.md` antes de activar una skill descubierta por etiqueta.

## Variables de entorno

| Variable | Default | Para qué sirve |
|---|---|---|
| `OPENCODE_SKILLS_DIR` | dos niveles arriba del script | Gestionar otra raíz de skills |
| `OPENCODE_SKILLS_DISABLED` | `<raíz>/../skills-disabled` | Elegir el destino de desactivadas |
| `OPENCODE_SKILL_MANAGER_STATE` | `<raíz>/../skill-manager/state.json` | Cambiar el archivo de estado |
| `OPENCODE_SKILL_CATALOG_DIR` | `<raíz>/../skill-catalog` | Cambiar la caché del índice |
| `OPENCODE_SESSION_ID` | la pone OpenCode | Detectar sesiones nuevas |
| `GITHUB_TOKEN` | — | API de GitHub y repos privados |
| `GITHUB_TOPIC_LIMIT` | `20` | Repos a consultar por etiqueta (1–100) |

Ejemplo gestionando un proyecto:

```bash
OPENCODE_SKILLS_DIR=~/proyecto/.opencode/skills \
  python3 ~/proyecto/.opencode/skills/skill-manager/scripts/skillctl status
```

## Recetas

### Instalar una skill puntual y olvidarla

```bash
skillctl search "nombre"
skillctl ensure slug-encontrado
skillctl sync
skillctl end
```

### Compartir skills del equipo desde GitHub

```bash
skillctl source add mi-equipo/opencode-skills
skillctl refresh
skillctl ensure skill-del-equipo
skillctl pin skill-del-equipo
```

### Descubrir skills sin conocer el repo

```bash
skillctl topic search opencode-skills
skillctl topic add opencode-skills
skillctl refresh
skillctl search "lo que necesito"
```

### Recuperarse de un `sync` demasiado agresivo

```bash
skillctl enable nombre-de-la-skill     # una sola
skillctl restore                       # todas
```

### Probar una skill sin fijarla

```bash
skillctl ensure owner/repo
skillctl sync
skillctl end
# en la próxima tarea, begin la saca del activo
```

## Seguridad

- Descargas solo desde `opencodeskills.dev` y dominios de GitHub.
- Validación de frontmatter, nombre, descripción, rutas del zip y rutas del catálogo raw.
- Rechazo de symlinks y de rutas que salgan del directorio.
- Los scripts y archivos de configuración se escanean en busca de `curl | sh`, `sudo` y `rm -rf /`. Los `.md` quedan fuera porque suelen citar esos comandos como ejemplos.
- No se ejecuta código de las skills descargadas: solo se cargan con la herramienta `skill`.
- No se modifica `opencode.json` ni credenciales.

## Solución de problemas

| Síntoma | Acción |
|---|---|
| La skill no se anuncia | Revisá `description`, ruta y permiso `skill`; reiniciá OpenCode |
| `ensure` dice «no está en el catálogo» | Corré `refresh`; verificá que el slug exista en `search` |
| No aparece una skill de GitHub | `source list` / `topic list`, después `refresh` |
| `sync` desactivó algo necesario | `enable <slug>` o `restore` |
| Cambiaron las fijas sin intervención | Cambió `OPENCODE_SESSION_ID`: es esperado |
| `topic search` devuelve poco | Probá otro tag; solo se muestran repos con `SKILL.md` |
| Errores de límite de GitHub | Definí `GITHUB_TOKEN` y bajá `GITHUB_TOPIC_LIMIT` |

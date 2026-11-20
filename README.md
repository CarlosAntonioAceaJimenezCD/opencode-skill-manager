# skill-manager

Skill de [OpenCode](https://opencode.ai) que gestiona el ciclo de vida de otras skills: fija las transversales de la sesión, activa las que pide cada tarea y desactiva el resto de forma reversible.

📖 **[Guía completa](GUIDE.md)** — referencia de todos los comandos, ejemplos y recetas.

## El problema

Cuando hay decenas de skills instaladas, OpenCode anuncia todas en cada paso. El modelo recibe descripciones que no corresponden a la tarea, y termina eligiendo mal o cargando de más. `skill-manager` reduce ese ruido sin limitar cuántas skills podés usar: lo que se controla es qué se anuncia, no cuántas se activan.

## Cómo funciona

| Nivel | Cuándo se define | Sobrevive a `sync` | Se limpia |
|---|---|---|---|
| `core` | en `state.json` | siempre | nunca |
| fijas de sesión (`session_core`) | al inicio de la sesión | sí | con `session-end` o sesión nueva |
| activas de tarea (`active`) | por tarea | mientras dure la tarea | con `begin`, `end` o sesión nueva |
| globales (`pinned`) | con `pin` | siempre | con `unpin` |

`sync` mueve a `skills-disabled/` toda skill que no esté en esos cuatro grupos. Es un movimiento, no un borrado: `enable` o `restore` la devuelve. El cambio de sesión se detecta por `OPENCODE_SESSION_ID`, así que las fijas de una sesión no se filtran a la siguiente.

Otras características:

- `search` indexa el catálogo de [opencodeskills.dev](https://opencodeskills.dev) y puntúa candidatas por coincidencia.
- También acepta repositorios de GitHub como fuente: regístralos con `source add` o instalalos directo con `ensure owner/repo`.
- Puede buscar repos por etiqueta (topics de GitHub) para descubrir skills compatibles con `topic search`.
- `ensure` instala, reactiva y marca activas **varias** skills de una vez, sin tope.
- Los zips se validan antes de instalar: rutas seguras, sin symlinks, sin `curl | sh`, `sudo` ni `rm -rf /`.
- No ejecuta código de las skills descargadas.

## Requisitos

- OpenCode v2 con soporte de skills.
- Python 3.10 o superior (solo biblioteca estándar).
- Acceso a `opencodeskills.dev` para buscar e instalar skills nuevas.

## Instalación

### Manual

```bash
git clone https://github.com/CarlosAntonioAceaJimenezCD/opencode-skill-manager.git
mkdir -p ~/.config/opencode/skills
cp -R opencode-skill-manager/skills/skill-manager ~/.config/opencode/skills/
```

Verificá que OpenCode la vea:

```bash
python3 ~/.config/opencode/skills/skill-manager/scripts/skillctl status
```

También podés instalarla a nivel proyecto copiando la carpeta a `.opencode/skills/`; el script calcula su raíz desde su propia ubicación, así que funciona igual en los dos ámbitos.

### Como catálogo HTTP

Con GitHub Pages habilitado, agregá esto a `opencode.json` o `opencode.jsonc`:

```jsonc
{
  "skills": ["https://CarlosAntonioAceaJimenezCD.github.io/opencode-skill-manager/"]
}
```

Sin Pages, también funciona desde el contenido publicado en `main`:

```jsonc
{
  "skills": ["https://raw.githubusercontent.com/CarlosAntonioAceaJimenezCD/opencode-skill-manager/main/docs/"]
}
```

OpenCode lee `<base>/index.json` y descarga cada archivo desde `<base>/skill-manager/<archivo>`. El `version` del índice cambia con cada `VERSION`; eso renueva la caché.

### Desde GitHub

Además del catálogo público, `skillctl` puede buscar e instalar skills desde repositorios de GitHub:

```bash
skillctl source add owner/repo
skillctl refresh
skillctl search "nombre de la skill"
skillctl ensure nombre-de-la-skill
```

`source add` acepta `owner/repo`, `owner/repo@rama`, `https://github.com/owner/repo` y URLs `/tree/<rama>`. `source list` muestra las fuentes registradas y `source remove` las quita.

Si el repo publica un `index.json` de catálogo (en la raíz o en `docs/`), se usa ese índice. Si no, se recorren los `SKILL.md` del árbol con la API de GitHub y se descarga el zipball. Las carpetas `docs/`, `dist/` y las ocultas se ignoran para no instalar copias generadas.

Para instalar un repo sin registrarlo:

```bash
skillctl ensure owner/repo
```

Eso instala todas las skills que encuentre en el repo. Para repos privados o para evitar el límite de la API anónima, exportá `GITHUB_TOKEN`.

### Búsqueda por etiqueta

Si no conocés el repo, buscá por topics de GitHub:

```bash
skillctl topic search opencode-skills python
```

El comando consulta `topic:<tag>`, descarta repos que no contienen `SKILL.md` y muestra cuántas skills tiene cada uno, sus etiquetas y su URL. Con varios tags hace una búsqueda por cada uno.

Para que esas skills aparezcan también en `search`, registrá las etiquetas:

```bash
skillctl topic add opencode-skills
skillctl refresh
skillctl search "opencode"
```

Cada etiqueta registrada se indexa con categoría `GitHub:<tag>` (hasta 20 repos por etiqueta). `topic list` y `topic remove` gestionan la lista. Un topic es una pista declarada por el autor, no una garantía de compatibilidad: revisá el `SKILL.md` antes de activar la skill.

### Permiso

Para que se cargue sin preguntar, permití el ID `skill-manager` en la config de OpenCode:

```jsonc
{
  "permissions": [
    { "action": "skill", "resource": "*", "effect": "ask" },
    { "action": "skill", "resource": "skill-manager", "effect": "allow" }
  ]
}
```

## Uso

Podés invocarla con `@skill-manager` o dejar que se anuncie por su descripción. Un flujo típico de sesión:

```bash
# Al empezar la sesión: fijá lo transversal
skillctl session-begin
skillctl session-keep modern-python pytest-patterns

# Por cada tarea
skillctl begin "limpiar el dataset de ventas"
skillctl search "pandas groupby"
skillctl ensure pandas-analysis data-visualization
skillctl sync

# Al cerrar
skillctl end
```

En los comandos de arriba, `skillctl` significa `python3 "<base>/scripts/skillctl"`, donde `<base>` es el directorio que la herramienta `skill` informa al cargar la skill. Usar `python3` evita depender del bit de ejecución del archivo.

### Salida real de `status`

```text
sesión: ses_e09a310a4ffexpNcfy5qjSTTNr
tarea: (ninguna)
fijas de sesión: skill-manager
activas (estado): (ninguna)
fijadas globales: (ninguna)
core: skill-manager
skills en disco: 50
desactivadas: 0
actualizado: 2026-11-19T21:50:50-0400
```

## Comandos

Detalle y ejemplos de cada uno en la [guía completa](GUIDE.md#referencia-de-comandos).

| Comando | Efecto |
|---|---|
| `refresh` | Actualiza el índice del catálogo (caché de 7 días) |
| `search "<texto>"` | Busca y puntúa hasta 8 candidatas |
| `session-begin [slug...]` | Inicia la sesión y fija skills |
| `session-keep <slug...>` | Suma fijas a la sesión actual |
| `session-drop <slug...>` | Quita fijas de la sesión actual |
| `session-end` | Cierra la sesión y libera las fijas |
| `begin "<tarea>"` | Reinicia el set activo (conserva fijas) |
| `ensure <slug...>` | Instala/reactiva y marca activas, sin límite |
| `sync` | Desactiva lo que no se usa |
| `sync --dry-run` | Muestra qué desactivaría sin mover nada |
| `status` | Muestra sesión, tarea, fijas, activas y conteos |
| `list` | Lista activas y desactivadas |
| `enable <slug>` | Reactiva manualmente |
| `disable <slug>` | Desactiva manualmente y la desfija |
| `pin <slug>` | Fija para todas las sesiones |
| `unpin <slug>` | Quita la fijación global |
| `restore` | Reactiva todas las desactivadas |
| `end` | Cierra la tarea actual |
| `source add <repo...>` | Registra repositorios GitHub como fuente |
| `source list` | Lista las fuentes GitHub |
| `source remove <repo...>` | Quita fuentes GitHub |
| `topic add <tag...>` | Registra topics para buscar skills |
| `topic list` | Lista los topics registrados |
| `topic remove <tag...>` | Quita topics registrados |
| `topic search [tag...]` | Busca repos por topic y muestra sus skills |

## Configuración

| Variable | Default | Descripción |
|---|---|---|
| `OPENCODE_SKILLS_DIR` | dos niveles arriba del script | Raíz de skills a gestionar |
| `OPENCODE_SKILLS_DISABLED` | `<raíz>/../skills-disabled` | Destino de las desactivadas |
| `OPENCODE_SKILL_MANAGER_STATE` | `<raíz>/../skill-manager/state.json` | Archivo de estado |
| `OPENCODE_SKILL_CATALOG_DIR` | `<raíz>/../skill-catalog` | Caché del catálogo |
| `OPENCODE_SESSION_ID` | la define OpenCode | Detecta el cambio de sesión |
| `GITHUB_TOKEN` | — (opcional) | API de GitHub, repos privados y límites más altos |

Ejemplo para gestionar otra raíz:

```bash
OPENCODE_SKILLS_DIR=~/proyecto/.opencode/skills \
  python3 ~/proyecto/.opencode/skills/skill-manager/scripts/skillctl status
```

## Estado y archivos

Con instalación global, el estado queda en `~/.config/opencode/skill-manager/state.json` y la caché en `~/.config/opencode/skill-catalog/`. Con instalación de proyecto, al lado de `.opencode/`.

```json
{
  "session_id": "ses_...",
  "task": "descripción breve",
  "active": ["pandas-analysis", "data-visualization"],
  "core": ["skill-manager"],
  "session_core": ["skill-manager", "modern-python", "pytest-patterns"],
  "pinned": [],
  "sources": ["owner/repo@main"],
  "topics": ["opencode-skills"],
  "updated": "2026-11-19T22:00:00-0300"
}
```

## Desarrollo

```bash
python3 -m unittest discover -s tests -v
python3 scripts/build.py
python3 scripts/build.py --check
```

Estructura:

```text
.
├── SKILL.md                      instrucciones de la skill (en skills/skill-manager/)
├── VERSION                       versión del catálogo y del zip
├── scripts/build.py              genera docs/ y valida el frontmatter
├── tests/                        pruebas del CLI y del paquete
├── skills/skill-manager/
│   ├── SKILL.md
│   ├── references/policy.md
│   └── scripts/skillctl
└── docs/                         generado: index.json, skill-manager/ y el zip
```

Si cambiás algo dentro de `skills/skill-manager/`, ejecutá `build.py` y confirmá los cambios en `docs/`. `build.py --check` falla si el contenido generado quedó desactualizado; ejecutalo antes de publicar.

## Publicación

GitHub Pages publica `docs/` desde la rama `main`: **Settings → Pages → Build and deployment → Source: Deploy from a branch → main / docs**. Cada push que actualice `docs/` actualiza el sitio. La base del catálogo es `https://CarlosAntonioAceaJimenezCD.github.io/opencode-skill-manager/`.

El zip de `docs/` sirve para instalar a mano o para adjuntarlo a un release:

```bash
gh release create v1.0.0 docs/opencode-skill-manager-1.0.0.zip --generate-notes
```

Para proponerla al directorio de terceros `opencodeskills.dev`, escribí al correo de contacto publicado en su página `/about/`, adjuntando el zip, el propósito de la skill y la licencia. Ese directorio no tiene un formulario público de envío; su página `/request/` es para pedir que construyan skills, no para publicar las propias.

## Seguridad

- Solo descarga de `opencodeskills.dev` y de dominios de GitHub (`github.com`, `api.github.com`, `raw.githubusercontent.com`, `codeload.github.com`).
- El token de GitHub se envía solo en la cabecera `Authorization`: no se imprime ni se guarda en el estado.
- Los topics son una pista de búsqueda, no una verificación de compatibilidad.
- Valida frontmatter, nombre, largo de la descripción y rutas del zip.
- Rechaza zips con symlinks o patrones de comandos peligrosos.
- No ejecuta scripts internos de las skills descargadas.
- No modifica `opencode.json` ni credenciales.

Si querés endurecer el permiso de carga, dejá `* -> ask` en `permissions` y aprobá cada skill nueva.

## Solución de problemas

| Síntoma | Acción |
|---|---|
| La skill no se anuncia | Verificá `description`, la ruta y el permiso `skill`; reiniciá OpenCode |
| `sync` desactivó algo necesario | `skillctl enable <slug>` o `ensure <slug>` |
| El catálogo no se actualiza | Subí `VERSION`, ejecutá `build.py` y publicá de nuevo |
| Cambiaron las fijas sin intervención | Es el cambio de `OPENCODE_SESSION_ID`: es esperado |
| `search` falla sin red | La primera búsqueda descarga el índice; después usa caché de 7 días |
| No aparece una skill de GitHub | `source list` / `topic list`, después `skillctl refresh`; revisá `GITHUB_TOKEN` para repos privados |
| La búsqueda por topics devuelve poco | Probá otro tag, revisá `topic list` y recordá que solo se muestran repos con `SKILL.md` |

## Licencia

MIT. Ver [LICENSE](LICENSE).

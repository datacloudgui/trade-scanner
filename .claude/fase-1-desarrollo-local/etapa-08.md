# Etapa 8 — OutputSink y notificación por entorno

**Estado:** completada (T1–T7, 2026-06-19) — 225 passed; backtest dev verificado; switch por canal config-only demostrado. Pendiente solo lo diferido a E9 (envío real Gmail + `qc_notify` cloud) y tu revisión del template (D8.6).
**Depende de:**
- **Etapa 7** (cerrada en dev): `ScanPipeline.scan(symbol_data, as_of, log) -> list[ScanResult]`; `ScanResult` completo (`strategy`, `as_of`, `ticker`, `direction`, `partial_bar`, `price`, `time_frames_evaluated`, `sma_evidence`, `passed_rules`, `rules_passed_count`) en [core/pipeline.py](../../trade-scanner/core/pipeline.py#L30); `main.py._scan(name)` produce los `ScanResult` en memoria + log ([main.py:323](../../trade-scanner/main.py#L323)).
- **Etapa 4** (cerrada): precedente `core/universe.py` **sin imports de `AlgorithmImports`** → testeable con mock y reutilizable desde scripts del host (D-E4). Se replica para `core/output.py` y `core/email_render.py`.
**Autoridad de diseño:** SPECS §6 (contrato de salida + notificación por entorno), PLAN §5 (contrato `ScanResult` CSV/JSON), CLAUDE.md ("el switch local/cloud vive SOLO en `core/output.py`"). Decisiones nuevas D8.x ratificadas en conversación 2026-06-19 (abajo).
**Estimado:** 6–9 h (serialización + renderer + sink con dispatch + config/seed + integración L5 + script host con dry-run + backtest de verificación).

**Contexto.** La Etapa 7 dejó los `ScanResult` **en memoria + log**: el scan ya produce watchlists reproducibles con evidencia por candidato, pero no las **persiste** ni **notifica**. Esta etapa cierra el criterio nº6 del SPECS ("salida por entorno, sin ramas de negocio por entorno") y materializa el correo que el trader consume.

La pieza delicada NO es serializar (el contrato CSV/JSON ya está fijado en PLAN §5): es **respetar las dos reglas duras** mientras se habilita el correo por Gmail que pediste:
- *"El código solo habla con la API de `QCAlgorithm`. Sin SDKs externos."* → el algoritmo **no** puede importar la librería de Gmail/GCP.
- *"Portable local ↔ QC cloud sin cambios de código."* → el envío real no puede depender de en qué máquina corre.

La reconciliación (D8.1) es: **el envío vive en dos planos**. El renderizador del correo es una función **pura y compartida**; el *canal* lo elige el entorno vía config — cloud → `self.notify.email` (nativo, portable); local/VPS → un **script host-side** (`scripts/notify_email.py`) lee la salida persistida y envía por Gmail con tu token. El algoritmo nunca toca Gmail.

---

## Decisiones de diseño

> Numeradas D8.x. D8.1 (dónde vive el envío) y D8.4 (dispatch por config, no por nombre de entorno) son las que tocan capas/portabilidad — máximo cuidado. El resto son mecánicas de serialización/config.

### D8.1 — Envío híbrido: renderer puro compartido + canal por entorno *(ratificada 2026-06-19)*

El correo se parte en **render** (puro) y **transporte** (por entorno):

- **Render** — `core/email_render.py`: función pura `render_email(envelope) -> EmailDoc(subject, text_body, html_body)`. **Sin imports de `AlgorithmImports` ni SDK de Gmail** (precedente `universe.py`, D-E4) → la importan *ambos* planos: el algoritmo (para `self.notify.email`) y el script host (para Gmail). El template vive aquí; flipar de cloud a local **no recompone el cuerpo**, solo cambia el transporte.
- **Transporte cloud** — dentro del algoritmo, `self.notify.email(recipients, subject, html_body)` (`NotificationManager`, nativo y portable). Es la vía que confirmaste online.
- **Transporte local/VPS** — el algoritmo **no envía**: persiste el *envelope* a `results/` (D8.3) y un **script host-side** (`scripts/notify_email.py`, T6) lo lee y envía por Gmail con tu token (de `.env`/GCP, nunca en el repo).

"Híbrido y fácil de volverlo híbrido" = el cuerpo es el mismo objeto en los dos caminos; el entorno solo elige **quién** lo despacha. Un futuro VPS que prefiera `self.notify` por SMTP, o un cloud que prefiera Gmail, se resuelve en config (D8.4), no en código.

### D8.2 — La unidad de salida es la *estrategia base* (long+short en un solo envelope) *(ratificada 2026-06-19)*

**Un correo por estrategia base**, no por variante: `swing_eod` envía **un** correo con secciones LONG y SHORT; `market_close` otro. Las variantes `*_short` **no** son una estrategia aparte a efectos de salida — son la sección SHORT de su estrategia base. Esto supersede la lectura literal de "4 correos": son **2** (swing_eod, market_close), cada uno con sus dos lados.

Esto es viable porque long y short de una misma base **comparten horario** (`swing_eod`/`swing_eod_short` → `after_close`; `market_close`/`market_close_short` → `before_close_30m`). La implicación de orquestación (D8.7): **un `ScheduledEvent` por estrategia base** que corre sus pipelines miembro (long y short) y llama a `OutputSink.emit` **una vez** con ambos lados — sin buffering ni estado entre callbacks.

La unidad de persistencia y de correo es un **envelope por estrategia base·scan**, con los candidatos partidos en secciones por dirección:

```json
{
  "strategy": "swing_eod",
  "env": "prod",
  "as_of": "2026-06-19T20:01:00Z",
  "partial_bar": false,
  "totals": { "long": 7, "short": 5, "all": 12 },
  "sections": {
    "long":  { "direction": "long",  "count": 7, "candidates": [ /* ScanResult dict, ordenado */ ] },
    "short": { "direction": "short", "count": 5, "candidates": [ /* ScanResult dict, ordenado */ ] }
  }
}
```

- Dentro de cada sección, `candidates` viene **ordenado** por `rules_passed_count` desc (tie-break `ticker` alfabético — reproducibilidad D7.6); renderer y CSV **no reordenan**.
- Una estrategia base sin variante short (si la hubiera) tiene solo la sección `long`; el envelope es robusto a secciones ausentes.
- El envelope es lo que pediste por "añadir campos al JSON para facilitar el correo": metadata (estrategia, hora, conteo por lado, entorno) fuera de cada candidato, sin recomputar. `ScanResult` **no cambia** (PLAN §5); el envelope lo envuelve y agrupa por dirección.

### D8.7 — Estrategia base = grupo de notificación; un ScheduledEvent por base

`STRATEGIES` ya mapea las 4 claves de config a 2 `StrategyConfig` (C3 de E7: `swing_eod`/`swing_eod_short` → misma instancia). Etapa 8 formaliza ese par como **estrategia base** y lo usa como unidad de schedule y de correo:

- **Grupos** declarados en `config/notifications.json` (`notification_groups`, T4): `{"swing_eod": ["swing_eod","swing_eod_short"], "market_close": ["market_close","market_close_short"]}`. La estrategia base es la clave; los miembros son las variantes de pipeline.
- **Invariante** (validado en `initialize()`): todos los miembros de un grupo comparten `schedule` (si no, error de config explícito). `partial_bar` también es uniforme por grupo (deriva del horario, D7.4).
- `main.py` registra **un `ScheduledEvent` por estrategia base** (no por variante): el callback corre el pipeline de cada miembro activo, junta los resultados por dirección y llama `output.emit(base, as_of, sections)` una sola vez. Reemplaza el "un evento por estrategia" de E7 — sin tocar la lógica de pipeline (cada variante sigue siendo el mismo `ScanPipeline` de E7), solo el punto de agregación.
- Variantes omitidas (sin `StrategyConfig`, ya logueadas en E7) simplemente no aportan su sección; el grupo emite con las que haya.

### D8.3 — Persistencia: SIEMPRE archivo; notificación condicional

Independiente del entorno, todo scan **escribe archivo** (durable, auditable, e insumo del script host). Artefactos por **estrategia base**·scan (D8.2), vía `self.object_store` (en local cae a `storage/results/`, mismo mecanismo que `validation/` en [main.py:313](../../trade-scanner/main.py#L313)), keyeados por la estrategia base — **no** por variante:

- `results/<base>/<YYYYMMDD-HHMM>.json` — el envelope completo con secciones long/short (D8.2).
- `results/<base>/<YYYYMMDD-HHMM>.csv` — filas `ScanResult` de **ambos lados** (la columna `direction` distingue long/short), contrato CSV de PLAN §5 (`sma_evidence` como JSON-string, `passed_rules` pipe-separated, `time_frames_evaluated` como `D,W,M`). Una sola tabla; ordenada por sección y luego por ranking.
- `results/<base>/latest.json` (sobrescrito cada scan) — **puntero fijo que lee el script host (opción A, confirmada).** El host no lista ni parsea timestamps; lee `latest.json`. Recuperar scans atrasados listando por timestamp queda como extensión V2.

La **notificación** (correo) es condicional (D8.4). Un scan **sin candidatos en ningún lado** escribe igual un envelope `totals.all: 0` (auditoría) pero **no** dispara correo (config `notify_empty: false`, default).

### D8.4 — Dispatch por *canales en config*, no por `if env == ...` *(criterio nº6 del SPECS)*

El "switch por entorno" vive **solo** en `core/output.py` y se expresa como **lista de canales habilitados por entorno**, leída de config — nunca como ramas `if env == "prod"` esparcidas. `OutputSink` tiene una **tabla de handlers** `{ "file": ..., "qc_notify": ..., "host_email": ... }` y ejecuta los que el entorno declare:

```jsonc
// config/notifications.json  → environments[env].channels
"channels": ["file", "host_email"]   // prod local/VPS: archivo + lo recoge el script host
"channels": ["file", "qc_notify"]    // cloud: archivo + self.notify.email
"channels": ["file"]                  // dev/backtest: solo archivo, sin correo
```

- `file` → escribe envelope+CSV (D8.3). Siempre presente.
- `qc_notify` → `self.notify.email(...)` con el render compartido (cloud).
- `host_email` → no-op de envío en el algoritmo; garantiza que el envelope+`latest.json` quedan listos para el script host (en la práctica es lo mismo que `file` + marca de "pendiente"). Esto mantiene el algoritmo agnóstico de Gmail.
- **Gate de vida:** en backtest (`self.live_mode == False`) los canales de correo (`qc_notify`) se **suprimen** aunque estén en config (no spamear durante backtests); `file` siempre corre. El gate es una línea en `OutputSink`, no una rama de negocio. `host_email` no envía nada por sí mismo, así que es inocuo en backtest.

Resultado: agregar un canal o cambiar el de un entorno = editar `notifications.json` (ObjectStore), cero código. Cumple "sin ramas de negocio por entorno fuera de `output.py`".

### D8.5 — Suscriptores por estrategia, detrás de un loader swappable a DB *(ratificada 2026-06-19)*

La lista de correos **difiere por estrategia base** (no por variante: una sola lista para `swing_eod` cubre LONG y SHORT) y "eventualmente sería una DB". Por eso:

- Config separada `config/notifications.json` (no dentro de `strategies.json`): la notificación es cross-cutting y su sección de suscriptores es la que más cambia y la candidata a migrar a DB. Separarla deja esa migración limpia (se cambia el loader, no `strategies.json`).
- Lookup detrás de una abstracción mínima `SubscriberSource.for_strategy(base) -> list[str]`, keyeada por **estrategia base**. La implementación V1 (`JsonSubscriberSource`) lee `notifications.json["subscribers"][base]` (`swing_eod`, `market_close` — sin claves `*_short`); un futuro `DbSubscriberSource` cumple la misma interfaz sin tocar `OutputSink` ni el render.
- **Secretos fuera del repo siempre:** el token/credenciales de Gmail y el remitente viven en `.env` (gitignoreado) / GCP, **nunca** en `notifications.json`. La config solo lleva flags, canales, formato y destinatarios (que no son secretos, pero migran a DB).

### D8.6 — Contenido del correo (template base, para tu revisión)

Un solo correo por estrategia base, con **bloque LONG y bloque SHORT** (en ese orden). Cada bloque repite la misma estructura de dos partes (lo que pediste: el trader copia la lista rápido, luego audita). Si un lado va vacío, su bloque muestra "sin candidatos" pero el correo se envía igual (mientras el otro lado tenga candidatos o `notify_empty` lo permita).

Por cada lado (LONG, SHORT):

1. **Lista de tickers, uno por línea, SIN viñetas**, en orden descendente por `rules_passed_count` (D8.2). Bloque limpio para pegar directo en su escáner — listas separadas long/short para pegarlas por separado. Ej.:
   ```
   LONG
   AAPL
   MSFT
   NVDA

   SHORT
   XYZ
   ABC
   ```
2. **Tabla de detalle** (HTML para el cliente de correo; equivalente en texto plano como fallback): `Ticker · Reglas (n) · Reglas que pasaron · Evidencia clave (distance_pct por tf) · partial_bar`. Ordenada igual; las "mejores" arriba por conteo de reglas.

- **Subject:** `[trade-scanner] {strategy} — {totals.all} candidatos ({totals.long} LONG · {totals.short} SHORT) · {as_of:%Y-%m-%d %H:%M}Z`.
- **Header del cuerpo:** estrategia base, entorno, `as_of`, flag `partial_bar` (si `True`, nota "barra parcial: resultado provisional intradía").
- El template es un **borrador V1**: lo entrego en T2 y lo revisas; el render es puro, así que iterar el HTML no toca lógica.

---

## Tareas

> Cada tarea abre con **Por qué**. `(xhigh)` en lo que cruza capas/portabilidad (T3, T6). Resto `high`; config/commit `medium`.

### T1 — Serialización pura + envelope (`core/output.py`)

**Por qué.** Es el núcleo determinista y testeable sin CLR. Aislar serialización + construcción de envelope del transporte permite verificar el contrato de PLAN §5 byte a byte con mocks, antes de tocar `self.notify`/ObjectStore.

- **T1.1** — `build_envelope(strategy, env, as_of, partial_bar, sections) -> dict` (D8.2): `sections` = `{"long": [ScanResult], "short": [ScanResult]}` (lados ausentes permitidos). Por sección ordena por `(-rules_passed_count, ticker)`, serializa cada `ScanResult` a dict, calcula `count` por lado y `totals` (long/short/all). Orden determinista (reproducibilidad D7.6).
- **T1.2** — `serialize_csv(sections) -> str`: contrato CSV de PLAN §5 exacto (header + filas de **ambos lados**, columna `direction` los distingue; `sma_evidence` → `json.dumps`, `passed_rules` → `\|`-join, `time_frames_evaluated` → `,`-join, `as_of` ISO-8601). Orden: sección long, luego short; dentro, el orden de T1.1.
- **T1.3** — `serialize_json(envelope) -> str`: `json.dumps(envelope, sort_keys=True, default=...)` para `datetime`→ISO. Round-trip estable.
- **T1.4** — `core/output.py` **sin imports de `AlgorithmImports`** a nivel de módulo (precedente D-E4); las referencias a `self.notify`/`self.object_store` entran por runtime (T3), no por import.

**Criterio de aceptación:**
- (a) `build_envelope` con candidatos desordenados en ambos lados → cada sección ordenada por reglas desc, tie-break ticker; `totals` (long/short/all) correctos; metadata completa; un lado vacío produce `sección.count == 0` sin reventar.
- (b) `serialize_csv` produce el header y los tipos exactos de PLAN §5 con filas long+short y la columna `direction` correcta (test compara contra string esperado, incluido un `sma_evidence` anidado y `passed_rules` con 2 reglas).
- (c) `serialize_json(envelope)` round-trip: `json.loads` reproduce el envelope (con `as_of` ISO-8601).
- (d) grep: `core/output.py` sin `AlgorithmImports` a nivel módulo. `bash scripts/run_tests.sh` verde.

### T2 — Renderer del correo compartido (`core/email_render.py`)

**Por qué.** Es la pieza que hace el correo "híbrido" (D8.1): un solo cuerpo, dos transportes. Puro y SDK-free para que lo importen el algoritmo y el script host. Aquí vive el template que vas a revisar (D8.6).

- **T2.1 (xhigh)** — `render_email(envelope) -> EmailDoc` (dataclass `subject`, `text_body`, `html_body`). Sin `AlgorithmImports`, sin SDK de Gmail. Consume el orden del envelope (no reordena). Itera las secciones (LONG luego SHORT).
- **T2.2** — Por sección: lista de tickers, uno por línea, sin viñetas (D8.6.1), precedida del rótulo `LONG`/`SHORT`, en `text_body` y `html_body` (`<pre>` o `<br>`).
- **T2.3** — Por sección: tabla de detalle (HTML `<table>` + equivalente texto con columnas alineadas). Columnas de D8.6.2; evidencia = `distance_pct` por tf desde `sma_evidence`.
- **T2.4** — Subject y header con estrategia base/entorno/`as_of`/`partial_bar` y totales por lado (D8.6).

**Criterio de aceptación:**
- (a) Con un envelope de 3 long + 2 short, `text_body` contiene un bloque `LONG` con 3 tickers uno por línea y un bloque `SHORT` con 2, sin `-`/`*`/`•`, cada bloque en orden de `rules_passed_count` desc.
- (b) `html_body` trae una `<table>` por sección con una fila por candidato en el mismo orden; subject incluye `{strategy}` y los totales `({long} LONG · {short} SHORT)`.
- (c) Un envelope con un lado vacío (`short.count == 0`) renderiza el bloque SHORT como "sin candidatos" sin reventar; `totals.all == 0` también renderiza (defensivo, aunque D8.3 no lo envía).
- (d) `core/email_render.py` sin `AlgorithmImports`/SDK. `run_tests.sh` verde.

### T3 — `OutputSink`: dispatch por canales + entorno (`core/output.py`)

**Por qué.** Es el único lugar del proyecto con el switch local/cloud (CLAUDE.md). Implementarlo como tabla de handlers leída de config (D8.4) es lo que cumple el criterio nº6 ("sin ramas de negocio por entorno").

- **T3.1 (xhigh)** — `OutputSink(object_store, notify, live_mode, notif_config, subscribers)`: recibe los handles del algoritmo por constructor (no import). Guarda los canales del entorno activo desde `notif_config`.
- **T3.2 (xhigh)** — `emit(strategy, env, as_of, partial_bar, sections)`: `sections = {"long": [...], "short": [...]}` (D8.2). Construye **un** envelope (T1.1) por estrategia base, y por cada canal habilitado ejecuta su handler de una tabla `{"file", "qc_notify", "host_email"}`:
  - `_emit_file`: `object_store.save(results/<base>/<ts>.json|csv)` + `latest.json` (D8.3).
  - `_emit_qc_notify`: si `live_mode` y hay suscriptores (lookup por **estrategia base**, D8.5) → `notify.email(",".join(subs), doc.subject, doc.html_body)`; render vía `email_render` (T2).
  - `_emit_host_email`: no-op de envío (garantiza `file`+`latest.json`); deja traza en log de "envelope listo para script host".
- **T3.3** — Gate de vida (D8.4): en `live_mode == False`, suprimir `qc_notify` (loguear "correo suprimido en backtest"); `file`/`host_email` corren. Una sola guarda, no ramas dispersas.
- **T3.4** — `notify_empty` (default `False`): un scan con `totals.all == 0` escribe archivo pero no dispara `qc_notify`.

**Criterio de aceptación:**
- (a) Con `channels=["file","qc_notify"]`, `live_mode=True`, `sections` con long+short y mock de `object_store`/`notify`: se guardan `.json`+`.csv`+`latest.json` bajo `results/<base>/` y se llama `notify.email` **una vez** con el subject/recipients (lista de la base) esperados.
- (b) Con `live_mode=False` (backtest) y los mismos canales: se guardan archivos pero `notify.email` **no** se llama (gate D8.3/T3.3).
- (c) Con `channels=["file","host_email"]`: archivos escritos, `notify.email` nunca llamado; log marca "listo para host".
- (d) `totals.all==0` y `notify_empty=False`: archivo sí, correo no. Cambiar de canal = solo `notif_config`, sin tocar `emit`. `run_tests.sh` verde.

### T4 — Config de notificación + seed + loader de suscriptores

**Por qué.** Habilitar canales y editar suscriptores por estrategia debe ser dato, no código (D8.5), y la lista debe poder migrar a DB sin tocar el sink.

- **T4.1** — `config/notifications.json`: `notification_groups` (estrategia base → variantes, D8.7); `environments.{dev,prod,...}.channels` + `notify_empty`; `subscribers.{base}: [emails]` (claves de **estrategia base**, sin `*_short`); `email.from`/`subject_prefix` (no secretos). Token Gmail **no** aquí. Ejemplo:
  ```jsonc
  {
    "notification_groups": {
      "swing_eod":    ["swing_eod", "swing_eod_short"],
      "market_close": ["market_close", "market_close_short"]
    },
    "environments": {
      "dev":  { "channels": ["file"],                 "notify_empty": false },
      "prod": { "channels": ["file", "host_email"],   "notify_empty": false }
    },
    "email": { "from": "trade-scanner@<tu-dominio>", "subject_prefix": "[trade-scanner]" },
    "subscribers": {
      "swing_eod":    ["tu-correo@gmail.com"],
      "market_close": ["tu-correo@gmail.com"]
    }
  }
  ```
- **T4.2** — `SubscriberSource` (en `core/output.py` o `core/notifications.py`): interfaz `for_strategy(base) -> list[str]`; `JsonSubscriberSource(notif_config)` la implementa (lookup por estrategia base). Documentar `DbSubscriberSource` como punto de extensión (no implementado en V1). Sin `AlgorithmImports`.
- **T4.3** — `scripts/seed_object_store.sh`: añadir `config/notifications.json` al copiado a `storage/config/` (junto a `strategies.json`).

**Criterio de aceptación:**
- (a) `JsonSubscriberSource` devuelve la lista correcta por estrategia base y `[]` para una base ausente (sin reventar).
- (b) `bash scripts/seed_object_store.sh` deja `storage/config/notifications.json`; `main.py` lo lee vía `object_store` sin error.
- (c) El token de Gmail no aparece en `notifications.json` (grep). `run_tests.sh` verde.

### T5 — Integración en `main.py` (L5)

**Por qué.** `_scan` ya produce los `ScanResult` por variante ([main.py:336](../../trade-scanner/main.py#L336)); falta (i) agrupar long+short por estrategia base (D8.7) y (ii) enchufarlos al sink. `main.py` es el único que toca `object_store`/`notify`/`live_mode`/`schedule`, así que construye el `OutputSink` y registra los eventos por base.

- **T5.1** — En `initialize()`: leer `config/notifications.json` (object_store), construir `JsonSubscriberSource` y `OutputSink(self.object_store, self.notify, self.live_mode, notif_cfg, subs)` en `self.output`. Validar el invariante D8.7 (miembros de un grupo comparten `schedule`).
- **T5.2** — Schedule por **estrategia base** (D8.7): un `ScheduledEvent` por grupo activo. El callback `_scan_group(base)` corre el pipeline de cada miembro (long, short), arma `sections = {"long": [...], "short": [...]}` y llama `self.output.emit(base, env, self.utc_time, partial_bar, sections)` **una vez**. Conservar el log de candidatos por variante (ortogonal). `partial_bar` uniforme por grupo.
- **T5.3** — No introducir ramas de entorno en `main.py`: toda la decisión de canal vive en `OutputSink` (D8.4).

**Criterio de aceptación:**
- (a) `lean backtest "trade-scanner"` (env dev) corre sin errores y escribe `storage/results/<base>/*.json` y `*.csv` (un envelope por estrategia base con secciones long/short) para los scans.
- (b) Los archivos son legibles y válidos (`json.loads` del envelope con `sections`; CSV con header de PLAN §5 y columna `direction`). Verificar con un candidato real del backtest dev (p. ej. IBM short de E7 en la sección SHORT de su base).
- (c) `main.py` sin `if env ==` para decidir salida (grep); el switch vive en `output.py`; un solo `emit` por estrategia base por scan. `run_tests.sh` verde.

### T6 — Script host-side de correo (`scripts/notify_email.py`)

**Por qué.** Es el transporte local de Gmail (D8.1), fuera del algoritmo para no romper "solo API QCAlgorithm". Testeable contra un envelope de muestra sin enviar (la app GCP/token aún no está lista).

- **T6.1 (xhigh)** — Lee envelopes de `storage/results/<base>/latest.json` (opción A confirmada — sin listar por timestamp; o `--file <path>`), renderiza con `core/email_render.render_email` (mismo cuerpo que cloud), resuelve suscriptores por estrategia base desde `config/notifications.json`.
- **T6.2** — Transporte Gmail vía token/credenciales de `.env`/GCP (OAuth de tu desktop app). Aislar el envío en una función `send_gmail(doc, recipients, creds)` para poder mockearla.
- **T6.3** — `--dry-run`: renderiza e imprime subject + cuerpos + destinatarios, **sin** enviar. Modo por defecto hasta que tengas la app GCP. `--sample <json>` para correr contra un envelope de muestra commiteado en `tests/fixtures/`.
- **T6.4** — Corre sobre Python 3.11 del `.venv` del host (no Docker; es script auxiliar, como `explore_universe.py`). Documentar en el header cómo se obtienen las credenciales (sin commitearlas).

**Criterio de aceptación:**
- (a) `python scripts/notify_email.py --dry-run --sample tests/fixtures/envelope_sample.json` imprime subject + bloques LONG y SHORT (tickers uno por línea) + tablas + destinatarios de la base, sin enviar y sin requerir token.
- (b) El render del script es **idéntico** al del algoritmo (mismo `email_render`): un test compara `render_email(sample)` con el cuerpo esperado.
- (c) El envío real (`send_gmail`) está aislado y mockeado en test; el token se lee de `.env`, nunca hardcodeado. El envío real **se valida en Etapa 9** (live).

### T7 — Backtest de verificación + cierre

**Por qué.** Cerrar el "Done when" con evidencia ejecutada (definición de "verificado" de CLAUDE.md), no asumida.

- **T7.1** — `lean backtest "trade-scanner"` (dev) → confirmar archivos CSV/JSON legibles en `storage/results/`; citar una ruta y un envelope en la bitácora.
- **T7.2** — Verificar que el switch está aislado: grep de ramas de entorno fuera de `output.py`; demostrar que cambiar `channels` en `notifications.json` cambia el comportamiento sin tocar `.py`.
- **T7.3** — Bitácora `etapa-08-decisiones-y-pendientes.md` (hallazgos, lo diferido a E9: envío real Gmail + `qc_notify` en cloud live) y commit `[Etapa 8] ...`.

**Criterio de aceptación:**
- (a) Backtest dev escribe archivos legibles (T5/T7.1) — evidencia citada.
- (b) `notifications.json` con `channels=["file","host_email"]` vs `["file"]` cambia el log/artefactos sin editar código.
- (c) `run_tests.sh` verde; commit con resumen y qué sigue (E9).

---

## Consideraciones técnicas (stack)

- **ObjectStore = `storage/` en local** (no `data/object-store/`). `object_store.save(key, str)` escribe texto; las keys `results/<strategy>/<ts>.json` caen a `storage/results/...`. Mismo mecanismo ya usado para `validation/` ([main.py:313](../../trade-scanner/main.py#L313)). En cloud es transparente.
- **`self.notify.email(address, subject, message)`** es la API nativa de `NotificationManager`; `address` admite varios separados por coma. Solo dispara en `live_mode`; en backtest se suprime (D8.4). El cuerpo HTML se pasa como `message`.
- **`core/output.py` y `core/email_render.py` SIN `AlgorithmImports`** a nivel de módulo (precedente `universe.py`, D-E4): así el script host los importa con Python del `.venv` y los tests corren con mocks simples sin CLR. Los handles de LEAN (`object_store`, `notify`, `live_mode`) entran por constructor en runtime.
- **Tests dentro de la imagen LEAN** (`scripts/run_tests.sh`) con mocks de `object_store`/`notify` (capturan llamadas); `TradeBar`s no hacen falta aquí — se testea sobre `ScanResult`/envelope sintéticos.
- **Detección de entorno:** `env` (dev/prod) viene de `get_parameter("env")` (lee de `trade-scanner/config.json`, D-E4); `self.live_mode` distingue live de backtest. El canal lo decide `notifications.json[env].channels`, **no** el nombre del entorno en código.
- **Script host** corre en `.venv` (Python 3.11), no en Docker — es auxiliar (como `explore_universe.py`); la regla "solo API QCAlgorithm" aplica al algoritmo, no a scripts del host.

## Fuera de scope (NO hacer en esta etapa)

- **Envío real de Gmail** (entrega de un correo de verdad con tu token/app GCP): se valida en **Etapa 9** (live). Aquí solo `--dry-run` + render verificado contra muestra.
- **`qc_notify` en cloud live de verdad**: requiere sesión QC cloud (ADR-002); el código queda listo y testeado con mock, la validación end-to-end es E9.
- **Migración de suscriptores a DB**: solo se deja la interfaz `SubscriberSource` (D8.5). Sin DB, sin ORM.
- **Correo consolidado entre estrategias / digest diario**: la unidad es la estrategia base·scan (swing_eod en un correo, market_close en otro — D8.2). Fusionar swing_eod + market_close en un solo correo es V2.
- **Calibración de `bucket_thresholds`, nuevos campos de evidencia, ranking avanzado**: el contrato `ScanResult` no cambia (PLAN §5).
- **Plantillas configurables / multi-idioma del correo**: un template base V1 en `email_render.py`. Parametrizarlo es V2.
- **Reintentos/cola/dedupe de envíos**: el script host envía best-effort en V1.

## Done when (medible)

- [x] `lean backtest "trade-scanner"` produce archivos **CSV y JSON legibles** en `storage/results/<base>/` — **un envelope por estrategia base** con secciones long/short (envelope válido + CSV conforme a PLAN §5 con columna `direction`) — evidencia citada (criterio nº1 del PLAN E8 / nº6 del SPECS).
- [x] El switch de destino por entorno está **aislado en `core/output.py`** (tabla de canales leída de `notifications.json`); grep confirma cero ramas de negocio por entorno fuera de `output.py`; cambiar `channels` altera el comportamiento sin tocar `.py` (criterio nº2 del PLAN E8 / nº6 del SPECS).
- [x] **Un solo correo por estrategia base** (swing_eod = LONG + SHORT en un correo, una lista de suscriptores): `core/email_render.render_email` renderiza bloques LONG/SHORT (tickers uno-por-línea sin viñetas, orden `rules_passed_count` desc + tabla por lado) y lo comparten algoritmo (`qc_notify`) y script host — verificado por test idéntico en ambos planos.
- [x] `python scripts/notify_email.py --dry-run --sample <fixture>` imprime el correo completo sin enviar y sin requerir token.
- [x] `config/notifications.json` sembrado a ObjectStore con `notification_groups` + canales por entorno + suscriptores por estrategia base; sin secretos; `SubscriberSource` swappable a DB documentado.
- [x] `bash scripts/run_tests.sh` verde (serialización, render, dispatch por canal, gate de backtest, loader de suscriptores) — **225 passed**.
- [x] Commit `[Etapa 8] ...` + bitácora con lo diferido a E9 (envío real Gmail + `qc_notify` cloud).

---

## Cómo iniciar la sesión

1. Leer este spec + PLAN §5 (contrato `ScanResult` CSV/JSON) + SPECS §6 (salida por entorno). Confirmar Etapa 8 en `en progreso` en PLAN.md.
2. Revisar el punto de enganche existente: [main.py:323-346](../../trade-scanner/main.py#L323) (`_scan` ya tiene los `ScanResult` en memoria) y el contrato [pipeline.py:30](../../trade-scanner/core/pipeline.py#L30).
3. Orden sugerido: **T1** (serialización pura) → **T2** (renderer, te paso el template para revisión) → **T3** (sink + dispatch) → **T4** (config/seed/loader) → **T5** (integración `main.py`) → **T6** (script host dry-run) → **T7** (backtest + cierre). T1–T4 y T6 son testeables sin engine; T5/T7 requieren `lean backtest` dev.
4. Antes de marcar checkboxes: `bash scripts/run_tests.sh` verde y `lean backtest "trade-scanner"` con evidencia de archivos en `storage/results/` (definición de "verificado" de CLAUDE.md).
5. **Punto de revisión contigo:** el template del correo (T2) — lo apruebas antes de cerrar la etapa.

### Preguntas abiertas (no bloquean el arranque)
- Dominio/remitente real del correo (`email.from`) y formato exacto del token de la app GCP → se concretan al validar en E9; V1 usa placeholder + `.env`.

### Decisiones cerradas en conversación (2026-06-19)
- **Opción A `latest.json`** (no listar por timestamp). Recuperar atrasados = extensión V2.
- **Un correo por estrategia base** (long+short en un correo con secciones, una lista de suscriptores por base). Supersede la lectura literal de "4 correos".

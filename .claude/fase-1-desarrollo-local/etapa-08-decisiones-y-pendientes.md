# Etapa 8 — Bitácora de decisiones y pendientes

> Se actualiza a medida que avanzan las tareas. Cierre formal de la etapa: T7.3.

## T1 — Serialización pura + envelope (`core/output.py`) — ✅ completada (2026-06-19)

### Qué se hizo
- `core/output.py` nuevo, **sin imports de `AlgorithmImports`/SDK** (solo stdlib + `core.pipeline.ScanResult`).
  - `build_envelope(strategy, env, as_of, partial_bar, sections)` — envelope D8.2 con secciones long/short ordenadas, `count` por lado y `totals` (long/short/all).
  - `serialize_csv(sections)` — contrato CSV de PLAN §5 (una tabla, ambos lados, columna `direction`).
  - `serialize_json(envelope)` — `json.dumps(sort_keys=True, default=datetime→ISO, indent=2)`.
- `tests/test_output.py` — 9 tests (orden/totals/lado vacío, CSV header+tipos, JSON round-trip, sin import LEAN).

### Decisiones tomadas en T1 (mecánicas, dentro de lo ya ratificado)
- **Quoting CSV con `csv.writer`** (no join manual): maneja automáticamente las comas/comillas del `sma_evidence` (JSON-string). Terminador `\n` fijo para salida estable cross-OS.
- **`as_of` se conserva como `datetime`** dentro del envelope; la conversión a ISO 8601 la hace `serialize_json` vía `default` (tal como pide T1.3), no `build_envelope`. Para CSV se usa `as_of.isoformat()`.
- **Claves `period` (int) del `sma_evidence`** → string al pasar por JSON (comportamiento estándar de `json.dumps`); el round-trip las devuelve como string. Documentado en docstring y verificado en test.
- **`totals` siempre con las 3 claves** (`long`/`short`/`all`, 0 si el lado falta); las **secciones ausentes** simplemente no aparecen en `envelope["sections"]` (robusto, D8.2).
- **`serialize_json` con `indent=2`**: artefactos legibles en `storage/results/` (no afecta el round-trip ni el contrato).

### Criterio de aceptación T1
- (a) orden por reglas desc + tie-break ticker, totals correctos, lado vacío sin reventar → ✅
- (b) CSV header y tipos exactos de PLAN §5, filas long+short con columna `direction`, `sma_evidence` anidado + `passed_rules` con 2 reglas → ✅
- (c) `serialize_json` round-trip con `as_of` ISO 8601 → ✅
- (d) sin `AlgorithmImports` a nivel módulo + `run_tests.sh` verde (187 passed) → ✅

### Sin bloqueos / preguntas
T1 está completamente especificado por el contrato fijo de PLAN §5; no requirió decisiones que necesiten aprobación del usuario.

## T2.1 — Esqueleto del renderer (`core/email_render.py`) — ✅ completada (2026-06-19)

### Qué se hizo
- `core/email_render.py` nuevo, **sin imports de `AlgorithmImports`/SDK** (solo `dataclasses`).
  - `EmailDoc(subject, text_body, html_body)` — dataclass agnóstica del transporte.
  - `render_email(envelope) -> EmailDoc` — orquestación: itera secciones `("long","short")` sobre `envelope["sections"]`, ensambla `text_body`/`html_body`, omite secciones ausentes; **no reordena** (consume el orden del envelope, D8.2).
  - Helpers stub `_subject` / `_header_text` / `_header_html` / `_section_text` / `_section_html`, con firmas finales y marcados `T2.2/T2.3/T2.4`.
- `tests/test_email_render.py` — 5 tests (forma de `EmailDoc`, orden LONG→SHORT, sección ausente y all-empty sin reventar, sin imports externos).

### Decisiones tomadas en T2.1
- **`SECTION_ORDER` definido localmente** en `email_render.py` (no importado de `output.py`): mantiene el renderer auto-contenido para el script host; es solo el orden de display ENTRE secciones (el orden DENTRO de cada sección ya viene del envelope).
- **Orquestación final vs. contenido diferido**: dejé la iteración/ensamblado/dataclass como definitivos y el contenido visible en helpers stub, para no construir-y-reconstruir. El stub de `_section_text` emite el rótulo `LONG`/`SHORT` (suficiente para verificar el orden entre secciones); `_subject` emite la estrategia como mínimo.

### Criterio de aceptación (alcance T2.1)
- `render_email` devuelve `EmailDoc` con los 3 campos string → ✅
- Itera LONG antes que SHORT en ambos cuerpos → ✅
- Sección ausente / all-empty sin reventar → ✅
- Sin `AlgorithmImports`/SDK a nivel módulo; `run_tests.sh` verde (192 passed) → ✅

## T2.2–T2.4 — Contenido del template (`core/email_render.py`) — ✅ completada (2026-06-19)

### Qué se hizo
- Rellené los helpers stub con el template V1 (D8.6), solo stdlib (`html`, `dataclasses`, `datetime`):
  - **T2.2** — `_section_text/_section_html`: rótulo `LONG`/`SHORT` + lista de tickers uno-por-línea sin viñetas (`<pre>` en HTML, ideal para copia-pega).
  - **T2.3** — `_detail_table_text/_detail_table_html`: tabla `Ticker · Reglas · Reglas que pasaron · Evidencia · Parcial`. Texto con columnas alineadas a ancho fijo; HTML `<table>`. Evidencia = `_evidence_str` (`distance_pct` por `(tf,period)` en orden de `time_frames_evaluated`, fracción → `+2.31%`).
  - **T2.4** — `_subject` (`[trade-scanner] {strategy} — {all} candidatos ({long} LONG · {short} SHORT) · {as_of}Z`) + `_header_text/_header_html` (estrategia·entorno·as_of + nota de barra parcial si `partial_bar`).
- `tests/test_email_render.py` — +8 tests (listas sin viñetas + orden, `<table>` por sección + subject/totales, evidencia distance_pct, lado vacío "(sin candidatos)", all-empty, header + nota parcial, **render idéntico con envelope JSON-loaded**).

### Decisiones tomadas
- **Robustez cross-plano (clave para T6):** `_format_as_of` y `_evidence_str` toleran envelope **nativo** (algoritmo: `as_of` `datetime`, `period` int) y **JSON-loaded** (script host: `as_of` string ISO, `period` string). Test `test_render_identical_for_json_loaded_envelope` prueba que `render_email(json_env) == render_email(env)`.
- **`SUBJECT_PREFIX = "[trade-scanner]"` como constante** del módulo (no del envelope, que es la unidad de datos D8.2). Prefijo configurable por entorno = V2 (fuera de scope). `notifications.json["email"]["subject_prefix"]` documenta el valor de referencia.
- **Evidencia con etiqueta `{tf}{period}`** (ej. `D20:+2.31%`) para desambiguar cuando una tf tenga varios periodos; `distance_pct` con signo (`:+.2%`).
- **`<pre>` para la lista de tickers** (monospace, selección limpia para pegar al escáner).
- **HTML-escapado** de todos los campos (`html.escape`) — `passed_rules` tiene paréntesis/comas (`AboveSMA(20,W+M)`); inocuo pero defensivo.

### Criterio de aceptación T2
- (a) 3 long + 2 short → bloques LONG/SHORT con tickers uno-por-línea sin `-`/`*`/`•`, orden `rules_passed_count` desc → ✅
- (b) `<table>` por sección, una fila por candidato mismo orden; subject con `{strategy}` y `({long} LONG · {short} SHORT)` → ✅
- (c) lado vacío → "(sin candidatos)" sin reventar; `totals.all==0` renderiza → ✅
- (d) sin `AlgorithmImports`/SDK; `run_tests.sh` verde (199 passed) → ✅

### Ajuste de humanización (feedback 2026-06-19)
Por pedido tuyo, el correo pasa de jerga a lenguaje humano (**solo en `email_render.py`; el CSV/JSON de `output.py` conservan los valores crudos** — el archivo es auditoría precisa, el correo es legible):
- Reglas: `AboveSMA(20,W+M)` → "sobre las medias de semanas, meses"; `BelowSMA(...)` → "bajo ..."; `NotExtended(8,D)` → "sin sobreextensión en días". Vía `_humanize_rule` (regex `Label(period,tfs)` + fallback al nombre crudo si no matchea). El periodo de la SMA se omite en la regla (vive en la evidencia).
- Evidencia: `D20:+2.31%` → "20SMA en días: 2.31%" (timeframe→sustantivo `días/semanas/meses`; sin `+`, conserva el `-`).
- `partial_bar`: `True/False` → `Sí/No`. Headers de tabla legibles (`Reglas OK`, `Qué cumple`, `Distancia a las medias`, `Barra parcial`).
- +3 tests (evidencia/reglas humanas, short con signo negativo + `Sí`, fallback de regla desconocida). `run_tests.sh` verde (201 passed).
- **Layout multi-línea (feedback 2026-06-19):** reglas y evidencias van **una por línea** en vez de `;`/`·`. Texto plano = columnas paralelas (cada candidato ocupa tantas líneas como su lado más largo; `Ticker`/`Reglas OK` solo en la 1ª línea, alineación a ancho fijo intacta sin saltos dentro de celda); HTML = `<br>` dentro de la celda. `_evidence_str`→`_evidence_lines` (devuelve lista); `_detail_row` devuelve `(reglas[], evidencias[])`.
- **Columna "Barra parcial" eliminada del correo:** es uniforme por scan (deriva del horario, D7.4); se anota una sola vez en el header del cuerpo cuando aplica. Tabla queda en 4 columnas. `run_tests.sh` verde (202 passed).

### 🔶 Pendiente: tu revisión del template (D8.6)
Render de muestra generado y mostrado en conversación (subject + text_body + html_body). **El template es un borrador V1 que apruebas antes de cerrar la etapa.** Iterar el HTML/columnas no toca lógica (render puro). Si quieres cambios (orden de columnas, formato de evidencia, incluir `price`, estilos HTML), se ajustan solo en `email_render.py`.

## T3.1 — `OutputSink`: constructor + resolución de canales (`core/output.py`) — ✅ completada (2026-06-19)

### Qué se hizo
- Clase `OutputSink(object_store, notify, live_mode, notif_config, subscribers, log=None)` en `output.py` (sigue sin `AlgorithmImports`; handles por constructor).
  - Guarda los handles del algoritmo (`object_store`, `notify`, `live_mode`), `notif_config` y `subscribers`.
  - `_channels_for(env)` — canales desde `notif_config["environments"][env]["channels"]` (D8.4, sin `if env==`); entorno ausente → `["file"]` + log.
  - `_notify_empty_for(env)` — default `False`, configurable por entorno.
- `tests/test_output.py` — +4 tests (guarda handles, canales por entorno, entorno ausente→`["file"]`+log, `notify_empty`). `run_tests.sh` verde (206 passed).

### Decisiones tomadas
- **`env` no está en el constructor** (sí en `emit`, D8.2): guardo `notif_config` y resuelvo canales **por `env`** vía helper. Un mismo sink sirve cualquier entorno. "Entorno activo" = el `env` que llega en `emit` (T3.2).
- **Entorno ausente → `["file"]`** (no error): D8.3 exige SIEMPRE archivo; nunca se pierde la auditoría por config incompleta. Deja traza en log.
- **6º parámetro `log=None`** (no-op) añadido a la firma documentada: patrón de inyección de log de L4 (como `ScanPipeline`) que T3.2/T3.3 necesitan ("correo suprimido"/"listo para host") sin que el sink hable con `QCAlgorithm`. Compatible con la firma del spec (opcional, al final).

## T3.2 — `emit` + tabla de handlers (`core/output.py`) — ✅ completada (2026-06-19)

### Qué se hizo
- `OutputSink.emit(strategy, env, as_of, partial_bar, sections)`: construye **un** envelope (T1.1) y despacha por cada canal habilitado vía tabla `{file, qc_notify, host_email}` (D8.4, sin `if env==`).
  - `_emit_file` — `object_store.save` de `results/<base>/<ts>.json`, `.csv` y `latest.json` (D8.3); `_timestamp(as_of)` → `YYYYMMDD-HHMM`.
  - `_emit_qc_notify` — guard de vida (backtest suprime) + lookup de suscriptores por base (D8.5); `notify.email(",".join(subs), doc.subject, doc.html_body)` con `render_email` (T2).
  - `_emit_host_email` — no-op de envío; log "listo para script host" (la persistencia la da `file`).
- `output.py` ahora importa `render_email` (puro, sin LEAN). +6 tests. `run_tests.sh` verde (212 passed).

### Decisiones tomadas
- **Guard `live_mode` incluido en T3.2** (está literal en su texto: "_emit_qc_notify: si live_mode..."). Cubre de hecho el criterio (b) de T3 y adelanta T3.3. El log "correo suprimido en backtest" queda aquí.
- **`notify_empty` (T3.4) NO incluido aún**: en T3.2 un scan vacío en live con suscriptores enviaría correo. Se cierra en T3.4. No hay test del caso vacío todavía.
- **Canal desconocido → ignorado + log** (robustez ante config mala), no excepción.
- **`_emit_host_email` no reescribe archivos**: la persistencia es responsabilidad del canal `file` (siempre presente, D8.4); host_email solo marca "pendiente para host". Evita duplicar la escritura.
- **`latest.json` == el `.json` del scan** (mismo contenido), confirmado por test (puntero fijo, opción A).

## T3.3 + T3.4 — gate de vida + notify_empty (`core/output.py`) — ✅ completada (2026-06-19)

### T3.3 — Gate de vida (validado, ya implementado en T3.2)
- **Una sola guarda**: `if not self._live_mode` en `_emit_qc_notify` (suprime + log "correo suprimido en backtest"). `file`/`host_email` no tienen esa guarda → corren siempre. Sin ramas de entorno dispersas (D8.4). Verificado por `test_emit_backtest_suppresses_qc_notify` (archivo sí, correo no). No requirió código nuevo.

### T3.4 — notify_empty
- Guard añadido en `_emit_qc_notify` (tras el gate de vida): si `totals.all == 0` y `not notify_empty(env)` → omite el correo + log `notify_empty=false`. El `env` y `totals` se leen del propio envelope (sin parámetros nuevos). El canal `file` escribe igual el envelope `totals.all:0` (auditoría, D8.3).
- +3 tests: vacío+`notify_empty=false` → archivo sí/correo no; vacío+`notify_empty=true` → sí notifica; no-vacío notifica normal. `run_tests.sh` verde (215 passed).

### Orden de guards en `_emit_qc_notify` (decisión)
vida (backtest) → `notify_empty` (scan vacío) → suscriptores → envío. Cada uno con su log; cambiar canales/flags = solo `notif_config`, sin tocar `emit`.

### ✅ T3 cerrada — criterios de aceptación
- (a) file+qc_notify live → 3 archivos + `notify.email` una vez (recipients/subject) → ✅
- (b) backtest → archivos sí, correo no → ✅
- (c) file+host_email → archivos, sin correo, log "listo para host" → ✅
- (d) `totals.all==0` + `notify_empty=false` → archivo sí, correo no; cambiar canal = solo config → ✅; `run_tests.sh` verde.

## T4 — Config de notificación + seed + loader de suscriptores — ✅ completada (2026-06-19)

### Qué se hizo
- **T4.1** — `config/notifications.json` nuevo (D8.7/D8.4/D8.5): `notification_groups` (base→variantes),
  `environments.{dev,prod}.channels` + `notify_empty`, `email.from`/`subject_prefix`,
  `subscribers.{base}` (solo claves base, sin `*_short`). **Sin secretos** (grep limpio).
- **T4.2** — `JsonSubscriberSource(notif_config)` en `core/output.py` (`for_strategy(base) -> list[str]`,
  `[]` si la base/`subscribers` falta). Sin `AlgorithmImports`. `DbSubscriberSource` documentado como
  punto de extensión (comentario, no implementado V1).
- **T4.3** — `seed_object_store.sh` **no requirió cambios**: ya itera `config/*.json` → copia
  `notifications.json` a `storage/config/` automáticamente. Verificado ejecutándolo.
- `tests/test_output.py` — +3 tests (lookup por base, base ausente/variante→`[]`, sin sección
  `subscribers`→`[]`). `run_tests.sh` verde (218 passed).

### Decisiones tomadas
- **`SubscriberSource` vive en `core/output.py`** (el spec permitía `output.py` o `notifications.py`):
  está acoplado al `OutputSink` que lo consume y es pequeño; evita un módulo nuevo. Si la migración a
  DB lo engorda, se extrae a `core/notifications.py` sin cambiar la interfaz.
- **`email.from` = placeholder `trade-scanner@example.com`**: el dominio/remitente real es pregunta
  abierta del spec (se concreta en E9 al validar Gmail). No bloquea; el campo no es secreto.
- **`subscribers` con tu correo real** (`guillermosanchezh@gmail.com`) para ambas bases. No es secreto
  (migra a DB); el token Gmail sí va a `.env`/GCP (fuera del repo).
- **`dev` solo `["file"]`, `prod` `["file","host_email"]`** (tal cual el ejemplo del spec): backtest
  dev no intenta correo; prod local deja el envelope listo para el script host (T6).

### Criterio de aceptación T4
- (a) `JsonSubscriberSource.for_strategy(base)` devuelve la lista correcta y `[]` para base ausente → ✅
- (b) `seed_object_store.sh` deja `storage/config/notifications.json` (verificado, 550 B). La lectura
  vía `object_store` en `main.py` es **T5** (integración); aquí queda sembrado y JSON válido → ✅ (parcial: el read real lo cierra T5)
- (c) token Gmail no aparece en `notifications.json` (grep limpio); `run_tests.sh` verde (218) → ✅

### Pendiente / nota
- La parte de (b) que dice "`main.py` lo lee vía object_store sin error" se materializa en **T5**
  (es donde `main.py` construye `OutputSink`/`JsonSubscriberSource` desde la config). Hoy se dejó el
  archivo sembrado y validado; no se tocó `main.py`.

## T5 — Integración en `main.py` (L5) — ✅ completada (2026-06-19)

### Qué se hizo
- **T5.1** — `initialize()` lee `config/notifications.json` (object_store), construye
  `JsonSubscriberSource` + `OutputSink(self.object_store, self.notify, self.live_mode, notif_cfg,
  subs, self.log)` en `self.output`; guarda `self._env = env`.
- **T5.2** — El loop de estrategias **ya no registra schedule por variante**: solo construye los
  `ScanPipeline` (4 variantes). El schedule ahora es **por estrategia base** iterando
  `notification_groups`: un `ScheduledEvent` por grupo activo con callback `_scan_group(base, members)`.
  El callback corre el pipeline de cada miembro, siembra `sections` con la dirección de cada miembro
  **activo** (lado activo sin candidatos → sección vacía count 0, para que el correo muestre "(sin
  candidatos)"), agrega resultados por dirección y llama `self.output.emit(base, env, utc_time,
  partial_bar, sections)` **una vez**. Conserva el log por variante.
- **Invariante D8.7 validado en `initialize()`**: miembros activos de un grupo deben compartir
  `schedule` y `partial_bar` → `ValueError` explícito si divergen (config inconsistente falla temprano).
- **T5.3** — Sin `if env ==` en `main.py` (grep limpio); el switch de canal vive en `OutputSink`.
- `_scan(name)` reemplazado por `_scan_group(base, members)`.

### Hallazgo / fix (bug de runtime, no detectado por tests con datetime naive)
- **`dataclasses.asdict()` deepcopia** cada campo. En runtime `ScanResult.as_of` (= `self.utc_time`)
  es un `datetime` **tz-aware** cuyo `tzinfo` es el `GMT` de LEAN (pythonnet), **no deep-copiable**
  → `GMT.__init__() missing 2 required positional arguments`, RuntimeError en el ScheduledEvent.
  El primer backtest abortó por esto. **Fix:** `_scanresult_to_dict` ahora hace **copia superficial**
  de campos (`{f.name: getattr(...)}`), no `asdict` — solo se serializa, nunca se muta, así que es
  seguro. `serialize_json`/CSV usan `isoformat()` (no deepcopia) y emiten el offset (`+00:00`).
- **Regresión añadida**: `test_build_envelope_does_not_deepcopy_runtime_datetime` con un `tzinfo`
  que revienta en `__deepcopy__` (simula `GMT`); verifica serialización JSON+CSV sin deepcopy.

### Decisiones tomadas
- **`sections` keyeado por dirección del miembro activo** (no por la de sus resultados): garantiza que
  un lado activo vacío aparezca como sección count 0 (D8.6 "(sin candidatos)") en vez de omitirse.
- **Schedule iterado sobre `notification_groups`** (autoridad de agrupación de salida, D8.7), no sobre
  `strategies_config`: las variantes sin grupo simplemente no se agendan (no ocurre hoy; las 4 están
  cubiertas). `partial_bar` del grupo = el de sus pipelines (uniforme, validado).
- **`emit` recibe `self.utc_time`** (UTC, consistente con E7 y con el `as_of` del CSV/JSON).

### Criterio de aceptación T5
- (a) `lean backtest "trade-scanner"` (dev) corre sin errores y escribe `storage/results/<base>/*.json`
  y `*.csv` (un envelope por base con secciones long/short) → ✅ (11 JSON + 10 CSV: `swing_eod/` y
  `market_close/`, con `latest.json` por base)
- (b) Archivos legibles/válidos: los 11 JSON parsean; `swing_eod/latest.json` → `totals {all:1,long:0,
  short:1}`, secciones `long`(0)+`short`(1) con **IBM** (candidato short de E7); CSV con header de
  PLAN §5 y fila `market_close_short,...,IBM,short,True,...` (columna `direction` correcta) → ✅
- (c) `main.py` sin `if env ==` (grep limpio); switch en `output.py`; un solo `emit` por base por scan;
  `run_tests.sh` verde (219) → ✅

## T6 — Script host-side de correo (`scripts/notify_email.py`) — ✅ completada (2026-06-19)

### Qué se hizo
- **`scripts/notify_email.py`** (T6.1–T6.4): transporte host-side, fuera del algoritmo (D8.1).
  - **Bootstrap de path**: añade `trade-scanner/` al `sys.path` para importar `core.email_render` y
    `core.output` (cadena CLR-free, verificada). En Docker `/Project` ya está en PYTHONPATH.
  - **`load_envelope`** (T6.1): `--sample`/`--file` (ruta explícita, con fallback a `trade-scanner/`)
    o `--base` → `storage/results/<base>/latest.json` (opción A confirmada).
  - **`render_email`** compartido (mismo cuerpo que `qc_notify`); **`resolve_recipients`** vía
    `JsonSubscriberSource` (D8.5) desde `config/notifications.json`.
  - **`--dry-run` por defecto** (T6.3): imprime subject + destinatarios + text_body + html_body, sin
    enviar y sin requerir token. `--send` opta al envío real.
  - **`send_gmail(doc, recipients, creds)`** AISLADO (T6.2): import del SDK **lazy** dentro de la
    función (dry-run/tests no dependen de él); creds vía `load_credentials()` desde el entorno
    (`GMAIL_SENDER`/`GMAIL_OAUTH_TOKEN`/`GOOGLE_APPLICATION_CREDENTIALS`), nunca hardcodeadas. El
    envío real lanza `NotImplementedError` → se concreta en **E9**.
  - Header documenta cómo obtener credenciales sin commitearlas.
- **`scripts/run_tests.sh`**: monta `scripts/` en `/Scripts` y lo añade a `PYTHONPATH` para que el
  test del script corra dentro de la imagen LEAN (los tests siguen siendo Docker-only).
- **`tests/fixtures/envelope_sample.json`**: envelope JSON-loaded (3 long + 2 short) commiteado.
- **`tests/test_notify_email.py`** (+6 tests): render idéntico (mismo `render_email`), cuerpo esperado
  del fixture, dry-run no llama `send_gmail`, `--send` lo llama 1× con `(doc, recipients, creds)`,
  creds desde el entorno, sin token hardcodeado. `run_tests.sh` verde (**225 passed**).

### Decisiones tomadas
- **Montar `scripts/` en `run_tests.sh`** (cambio de infra): necesario para satisfacer el criterio (c)
  ("`send_gmail` mockeado en test") sin romper la convención "tests solo en Docker". El script es
  importable en el contenedor (`import notify_email`) porque sus imports de nivel módulo son stdlib +
  `core.*` (el SDK de Gmail es lazy dentro de `send_gmail`).
- **`send_gmail` lanza `NotImplementedError` en V1**: el envío real es E9 (sin app GCP aún). El modo
  por defecto es dry-run; el `--send` sin creds da un error limpio (no traceback).
- **`--base` lee `latest.json`** (opción A): el host no lista timestamps (recuperar atrasados = V2).
- **Resolución de `--sample` con fallback a `trade-scanner/`**: el comando del criterio (a)
  (`--sample tests/fixtures/...`) funciona desde la raíz del workspace y desde el proyecto.

### Criterio de aceptación T6
- (a) `python scripts/notify_email.py --dry-run --sample tests/fixtures/envelope_sample.json` imprime
  subject + bloques LONG (3) y SHORT (2) (tickers uno-por-línea) + tablas + destinatarios, sin enviar
  ni token → ✅ (ejecutado en `.venv`)
- (b) Render del script == render del algoritmo (mismo `core.email_render.render_email`): test compara
  el cuerpo del fixture + identidad de la función → ✅
- (c) `send_gmail` aislado y mockeado (no en dry-run, sí en `--send`); token desde `.env`/entorno, sin
  hardcodear; envío real diferido a E9 → ✅

## T7 — Backtest de verificación + cierre — ✅ completada (2026-06-19)

### Qué se hizo / evidencia ejecutada
- **T7.1** — `lean backtest "trade-scanner"` (dev) corre sin runtime errors; escribe envelope JSON + CSV
  por estrategia base bajo `storage/results/<base>/` + `latest.json`. Evidencia citada:
  `storage/results/swing_eod/latest.json` → `strategy=swing_eod, env=dev, as_of=2013-10-10T20:01:00+00:00,
  totals={all:1,long:0,short:1}`, sección SHORT con **IBM** (candidato short de E7). Un `emit` por base
  por scan en el log (`[market_close] emit @ …`, `[swing_eod] emit @ …`).
- **T7.2** — Switch aislado: `grep "if env ==\|env ==\|live_mode =="` en `main.py`/`strategies/`/
  `pipeline.py`/`features.py` → **cero** ramas de entorno fuera de `output.py`. Demo **config-only**:
  con `dev.channels=["file"]` el log NO trae `listo para script host`; cambiando SOLO
  `notifications.json` a `["file","host_email"]` (+reseed) el log SÍ trae `envelope listo para script
  host (host_email)` — **sin editar ningún `.py`**. Revertido a `["file"]`.
- **T7.3** — Esta bitácora + commit `[Etapa 8] …`.

### Criterio de aceptación T7
- (a) Backtest dev escribe archivos legibles — evidencia citada (swing_eod/latest.json, IBM short) → ✅
- (b) `channels=["file","host_email"]` vs `["file"]` cambia el log/artefactos sin tocar código → ✅
- (c) `run_tests.sh` verde (**225 passed**); commit con resumen y qué sigue (E9) → ✅

### Nota de estado de artefactos
`storage/` está gitignoreado (copia regenerable; fuente versionada en `config/`), así que
`storage/results/` no se commitea. La fuente de la salida (código + `config/notifications.json`) sí.

## ✅ Etapa 8 cerrada — resumen
- **Entregado:** `core/output.py` (serialización + envelope + `OutputSink` con dispatch por canal/
  entorno + `JsonSubscriberSource`), `core/email_render.py` (render puro compartido), `config/
  notifications.json`, `scripts/notify_email.py` (host-side dry-run), integración en `main.py`
  (schedule por estrategia base + `emit`), `tests/fixtures/envelope_sample.json`, y tests
  (`test_output.py`, `test_email_render.py`, `test_notify_email.py`). `run_tests.sh` montó `scripts/`.
- **Done when del spec:** todos verdes salvo lo explícitamente diferido a E9 (abajo).

### Diferido a Etapa 9 (ya previsto en el spec)
- **Envío real de Gmail** con token/app GCP (`send_gmail` aislado + mockeado; lanza `NotImplementedError`
  en V1). Falta también el `email.from` real (placeholder `trade-scanner@example.com`).
- **`qc_notify` end-to-end en cloud live** (ADR-002): código listo y testeado con mock; validación
  end-to-end requiere sesión QC cloud.

### Pendiente de tu lado (no bloquea el cierre técnico)
- 🔶 **Revisión del template del correo** (D8.6): el dry-run de T6 es el render real; iterar HTML/
  columnas/incluir `price` se toca solo en `email_render.py` (render puro).

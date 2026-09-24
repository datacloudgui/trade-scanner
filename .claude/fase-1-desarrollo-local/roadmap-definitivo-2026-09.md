# Roadmap definitivo — ciclo de septiembre 2026

**Fecha:** 2026-09-22 · **Estado:** PROPUESTA CONSOLIDADA (requiere aprobación; nada ejecutado)
**Supersede a:** [roadmap-inmediato-2026-09.md](roadmap-inmediato-2026-09.md) (se conserva como registro del
diagnóstico original). **No reemplaza a [PLAN.md](../../PLAN.md)**: al aprobarse, cada unidad entra a PLAN §7.
**Base de verificación:** working tree de `feature/etapa-6-features-rules` @ `f8ded63` + cambios sin commitear
(`config/strategies.json`, `trade-scanner/main.py`, `lean.json`), `storage/` sembrado el 2026-09-20, backtest
prod `trade-scanner/backtests/2026-09-20_18-33-27/`. Cada afirmación de este documento se verificó contra ese
estado, no contra lo que asumía el roadmap anterior.
**Validación independiente (2026-09-22):** un revisor sin contexto previo re-derivó H1/H2/H4/H4b/H8 desde el repo y
dictaminó "LISTO CON CAMBIOS"; sus 10 cambios están incorporados (baseline §0.5, precedencia §0.4, U0 reordenado,
`session_date` en U1, plan B de U2, 27 series en U1b, criterios de U3a/U3b, U4 después de U3b, riesgos §4b).
Segunda pasada: **"LISTO para iniciar U0"**; también se incorporaron sus 5 ajustes residuales (glob recursivo por el
layout de U2, congelamiento solo para G4, conversión de `warmup_depth` en el host, tests de universo vacío y de dos CSV).
**Suite no ejecutada en esta revisión** (Docker apagado): es el paso 1 de U0.

**Leyenda de veredictos:** ✅ **Vigente** · 🔄 **Cambia por hallazgos** · 📦 **Pasa a OpenSpec** (se ejecuta como
change) · ❌ **Ya no aplica**.

---

## 0. Vocabulario: estructura OpenSpec + gates + rollback

Todo lo demás se expresa en estos términos.

### 0.1 Modelo: OpenSpec **anidado** en las etapas de PLAN.md

| Pieza | Rol | Quién escribe el estado |
|---|---|---|
| `PLAN.md` §7 | Índice operativo: etapa, **Estado**, **Done when**, link al change. Precedencia máxima (CLAUDE.md). | Solo PLAN.md |
| `openspec/changes/<id>/proposal.md` | Objetivo + scope + **diferencias esperadas en la watchlist** (insumo del gate G4) | — |
| `openspec/changes/<id>/design.md` | Decisiones D-x (sustituye a `etapa-NN-decisiones-y-pendientes.md`) | — |
| `openspec/changes/<id>/tasks.md` | Tareas granulares con checkbox (sustituye a la lista T1..Tn de `etapa-NN.md`) | Solo tasks.md |
| `openspec/changes/<id>/specs/**` | Deltas (ADDED/MODIFIED/REMOVED) con escenarios = criterios verificables | — |
| `openspec/specs/**` | Comportamiento aceptado. **Bootstrap perezoso:** cada change agrega (ADDED) la capacidad que toca; no se documenta el sistema entero de golpe | — |
| `.claude/fase-1-desarrollo-local/` | Archivo histórico E0–E11. No se migra retroactivamente | — |

- **Unidad de change = unidad coherente** (misma regla que los commits): un change por invariante o contrato
  que se modifica y que puede revertirse de forma independiente.
- **Vía ligera `[config]` (sin OpenSpec):** ajustes que solo tocan `config/strategies.json` o
  `config/notifications.json` sin cambiar ningún requisito (umbrales, `top_n`, `filters` ya soportados, `enabled`).
  Flujo: rama `config/<slug>` → G3/G4 → commit `[config] …` → tag. Un cambio de config que **modifica
  semántica** (p. ej. el vocabulario de `filters`) NO es vía ligera.
- **Tareas de proceso** (resincronizar PLAN, merges, docs) quedan en PLAN.md sin change.

### 0.2 Gates (identificadores usados en el resto del documento)

| Gate | Momento | Comando / evidencia | Bloquea |
|---|---|---|---|
| **G0** | Cierre de `propose` | `openspec validate <id> --strict` → exit 0 | El inicio de `apply` |
| **G1** | Tras G0 | Aprobación humana de `proposal.md` (= paso 6 de CLAUDE.md) | El inicio de `apply` |
| **G2** | Tras cada tarea de `apply` | `bash scripts/run_tests.sh` verde (Docker **arriba**) | El checkbox en `tasks.md` |
| **G3** | Antes de `sync` | `lean backtest "trade-scanner" --parameter env dev` (**dev**; el `config.json` versionado es `prod`), EXIT=0 | `sync` |
| **G4** | Antes de `sync`, **si el change toca el scan o la salida** | Backtest **prod** con ventana fija; antes de correr se vacía `storage/results/`. Diff de `results/<base>/**/2026*.json` contra `baselines/<tag>/` (ver §0.5); las diferencias deben coincidir con las declaradas en `proposal.md`. dev NO sirve: su override `universe: sample_dev` oculta #12 | `sync` |
| **G-data** | Antes de G4 (cuando exista U1) | Preflight de cobertura con exit 0 | G4 |
| **G5** | Antes de `sync` | `/opsx:verify` sin **CRITICAL**; los WARNING se corrigen o se justifican en `design.md`. (verify por sí solo no bloquea `archive`: el bloqueo es convención nuestra) | `sync` y checkboxes de PLAN |
| **G6** | Cierre | `sync` → checkboxes de PLAN con evidencia citada → `openspec validate <id> --strict` → `archive` (la CLI `openspec archive` valida, pero **`/opsx:archive` no**: archiva con `mv`, verificado en Etapa 12 T5; **prohibido** `--no-validate`) → Purpose **verificado** en cada capability nueva (sync/archive lo copian del delta; se escribe solo si quedó `TBD`) y `openspec validate --all --strict` exit 0 → commit `[Etapa N][<id>] …` → merge `--no-ff` a `develop` → fast-forward de `main` + tag `scan/vYYYY.MM.DD-N` (etapa-12 §Manejo de ramas) | — |

### 0.3 Primitivas de rollback

| Primitiva | Qué revierte | Cómo | Cuándo basta |
|---|---|---|---|
| **R-cfg** | Qué estrategias corren | `enabled: false` en `config/strategies.json` → `bash scripts/seed_object_store.sh` (en cloud, subir el JSON al ObjectStore) → relanzar (en live, `enabled` solo se lee en `initialize()`) | Cuando el código es correcto y lo que no se quiere es **publicar** esa watchlist |
| **R-git** | Código + config juntos | `git checkout <tag> -- config/ trade-scanner/` o `git revert` de los commits del change → reseed | Cuando el código del change es defectuoso |
| **R-trace** | Auditoría del rollback | `config_sha256` en log + envelope (se implementa en U1) → cada watchlist dice con qué config salió | Siempre: sin esto no se prueba qué config generó un correo |

`storage/` y el ObjectStore de la nube son **derivados** de git (no tienen historia); la unidad de rollback es
el tag de git, que captura config y código juntos (están acoplados: las claves de `filters` dependen de la
composición en `strategies/`).

### 0.4 Reglas para que OpenSpec y PLAN.md no se contradigan (entran a CLAUDE.md en U0)

1. Precedencia: `PLAN.md` > change activo > `openspec/specs` > `SPECS.md` > `CLAUDE.md` > skills `/opsx:*`
   generadas. **Excepción:** las "Reglas duras" y el "Flujo de trabajo" de CLAUDE.md no los puede anular ningún
   change; solo un ADR aprobado más la edición explícita de CLAUDE.md. Si una skill sugiere algo contrario
   (archivar con tareas abiertas, `--no-validate`, `sync` antes de G4), gana CLAUDE.md.
2. Equivalencias: etapa `en progreso` ⇔ change activo; "Done when" ⇔ escenarios + gates; `archive` ⇔
   cierre de etapa.
3. Prohibido: `--no-validate`; `--skip-specs` sin `skip_specs: true` en la metadata; `sync` sin G3/G4/G5;
   `archive` con CRITICAL abiertos; `/opsx:archive` sin `openspec validate <id> --strict` previo; confirmar un archive
   con tareas o artefactos incompletos; "Archive without syncing" si hay delta specs (hallazgos de Etapa 12 T5).
4. Commits: `[Etapa N][<change-id>] …`; `[config] …` en la vía ligera.

### 0.5 Baseline de G4 (lo que el tag de git NO captura)

`storage/` y `data/` están gitignoreados: un tag no guarda ni resultados ni datos. Por eso cada baseline es un
directorio versionado `baselines/<tag>/` con:
- copia de `storage/results/<base>/**/2026*.json` de la corrida de referencia, generada con `storage/results/` vaciado
  antes de correr (hoy contiene corridas dev de 2013 y un `latest copy.json`);
- `manifest.sha256` de los zips de `data/equity/usa/daily/` usados + de `storage/config/*.json` + de `storage/universes/*.csv`.

El glob es recursivo (`**/`) para cubrir los dos layouts: plano hasta U2 y `results/{base}/{YYYYMMDD}/` desde U2.
Se excluyen `latest*.json` (son punteros, no scans).

**Datos congelados para G4:** las corridas G4 entre U0 y U3b usan siempre los zips y CSV del manifiesto. Las
**corridas semanales reales** (runbook de U1 y revisión del trader en U3b) sí refrescan datos: se hacen en una copia
de trabajo y después se restaura el snapshot del manifiesto (`sha256sum -c manifest.sha256` exit 0 antes de cada G4). **Baseline móvil:** la referencia de G4 de cada change es el baseline regenerado desde el
tag del change anterior ya archivado (U2 cambia la salida a propósito: añade la sesión 09-18 y las carpetas por fecha).

**Alcance de las métricas de backtest:** cada sesión pasada de la ventana usa el universo **futuro** (CSV del 09-19),
así que tiene sesgo de supervivencia. Las cifras tipo "11/116 días" sirven para **comparar** entre corridas (G4), no
como medida de rendimiento de la estrategia.

---

## 1. Revalidación del roadmap anterior, sección por sección

### §1 — Estado real

| Afirmación (roadmap 2026-09-22) | Estado verificado hoy | Veredicto |
|---|---|---|
| 1–4, 5A completadas | Correcto según PLAN. **Omisión:** PLAN marca **Etapa 0 como `pendiente`** con los 4 checkboxes vacíos ([PLAN.md:167](../../PLAN.md#L167)), aunque el entorno funciona | 🔄 añadir a la resincronización de U0 |
| 5B en progreso; F2/F3 abiertas; `test_sma_regression.py` "INTERINO" | 5B en progreso ✔ e INTERINO ✔ ([test_sma_regression.py:1](../../trade-scanner/tests/test_sma_regression.py#L1)), pero **F2 ya está `[x]`**: solo queda **F3 (T6.3 y T6.4)** ([PLAN.md:275-292](../../PLAN.md#L275-L292)) | 🔄 → U1b |
| 6B "en progreso" en PLAN pese a estar commiteada | Confirmado ([PLAN.md:311](../../PLAN.md#L311)) | ✅ → U0 |
| 7/8 completadas, "225 passed" | 225 es la cifra de PLAN para E8; 9A declara 238 y 9B 284. **Hoy no se pudo ejecutar**: Docker estaba apagado (`run_tests.sh` → "failed to connect to the docker API"). Conteo estático: 224 `def test_` + 17 `parametrize` | 🔄 G2 queda **pendiente de correr** como primer paso de U0 |
| 9A T1–T6 cerradas, T7/T8 pendientes, T9 diferida | Confirmado ([etapa-09a:3](etapa-09a-conexion-alpaca.md#L3)) | ✅ → U4 |
| 9B: 19/20 corregidos | Confirmado (b5294bb, 9acf292, 53be8bd); citas #7 [seed:62-69](../../scripts/seed_object_store.sh#L62-L69), #21 [output.py:245](../../trade-scanner/core/output.py#L245), #11 [universe.py:33](../../trade-scanner/core/universe.py#L33), #18 [rules.py:50](../../trade-scanner/core/rules.py#L50) exactas | ✅ |
| 10 implementada y commiteada (`8b0afc2`) | Confirmado, pero el commit se llama "add: some improvements" sin `[Etapa 10]`, y PLAN no la registra | 🔄 U0 |
| 11 solo spec | Confirmado (`parse_asof_date` = 0 hits). **Pero la spec tiene un error de premisa** (H4) | 🔄 📦 U2 |
| #12 abierto | Confirmado (sin `tickers_by_strategy`); **y además activo** (H1) | 🔄 📦 U3a |

### §2 — "El hallazgo que reordena": cobertura de datos

| Afirmación | Hoy | Veredicto |
|---|---|---|
| CSV *as of* 09-13, 65 tickers post-filtro | `storage/universes/*` resembrados el 2026-09-20 con CSV **as of 09-19-2026**: advances **76**, declines **49**, unión **125** | ❌ números obsoletos |
| 26 (40 %) sin zip; última barra jun-jul | **0 sin zip** en ambos universos; **las 125 con última barra el 2026-09-18** (el refresh con `alpaca_to_lean.py` se corrió a mano el 20-sep) | ❌ el síntoma desapareció… |
| Los fríos se excluyen en silencio y la salida no lo delata | **Sigue siendo cierto, con otra causa:** `ready: 95/125`; en el último scan, **16 símbolos (13 %) excluidos por `M:20` fría** por historia corta (listados recientes: PBLS 70 barras, USDE 59, ELMT 103…; CAI/PS con huecos: 538/162 barras desde 2021). Ni el JSON ni el CSV lo reflejan | 🔄 …pero el **problema estructural** sigue → U1 cambia de foco |
| `end_date` 2026-09-01 ([main.py:40](../../trade-scanner/main.py#L40)) | En el working tree (sin commitear) dice **2026-09-18** | 🔄 ver H4/H5 |

**Conclusión de §2:** "el screener miente en silencio" sigue siendo cierto, pero ya no por falta de zips (eso
lo arregló el refresh manual de esta semana, sin que ningún mecanismo lo garantice) sino por **profundidad de
historia** y por **la última sesión sin escanear** (H4). U1 sigue en P0 con otro alcance.

### §3 — Unidades U1–U4

| Unidad | Veredicto | Motivo |
|---|---|---|
| U1 cobertura | 🔄 📦 | Cambia el foco: de "zips faltantes" a preflight de **frescura + profundidad** y cobertura en el envelope. Se suma R-trace (`config_sha256`) porque toca el mismo envelope |
| Spike 5B F2/F3 dentro de U1 | 🔄 📦 **se separa** (U1b) | Cierra otra etapa (5B) y tiene una precondición de datos (H8) |
| U2 Etapa 11 | 🔄 📦 | La premisa `end_date = asof` está refutada (H4) y la fuente de fecha debe ser la sesión, no el footer |
| U3 #12 + short | 🔄 📦 **se parte en U3a + U3b** | No es solo cambiar el flag (H2); el rollback de U3b solo es limpio después de U3a (§3 de este doc) |
| U4 cierre Fase 1 | ✅ (queda como tarea de PLAN Etapa 9, sin change) | Sin cambio de comportamiento; su evidencia debe salir de corridas posteriores a U3b |

### §4 — Tensión usabilidad vs cierre formal

✅ **Vigente** (U1/U2 antes que U4; 5B F3 como excepción no negociable; F2 ya estaba cerrada). Distinción confirmada: 9A T4
midió Alpaca↔Stooq (máx. 0,2259 %, [etapa-09a:126](etapa-09a-conexion-alpaca.md#L126)), no contra la plataforma
de referencia del trader. Se añade la precondición H8.

### §5 — Decisiones de #12

| Pregunta | Veredicto |
|---|---|
| ADR-006 nuevo | ✅ No existe ADR-006 (`.claude/decisions/` llega a ADR-005). Se amplía con el **tope de 200 sobre la unión** (H11) |
| No optimizar warmup por símbolo | ✅ |
| Universo vacío → sección vacía + WARNING + registro en envelope | ✅ se implementa dentro de U1 (mismo campo de cobertura) |

### §6 — POC Finnhub

✅ **Vigente** (diferir a post-V1). `scripts/poc/` existe y `docs/ROADMAP.md` aún no lo menciona. Se ejecuta
como `/opsx:explore` (sin change) cuando se aborde. Acción mínima en U0: cerrar por escrito la pregunta del
commit `f8ded63`.

### §7 — Higiene documental

| Punto | Hoy | Veredicto |
|---|---|---|
| PLAN no contiene 9A/9B/10/11 | Confirmado (`grep "9A|9B|Etapa 10|Etapa 11|filters|enabled" PLAN.md` = 0) | ✅ → U0 |
| ROADMAP/DEVLOG desfasados | Confirmado: ROADMAP "Última cerrada 5A"; DEVLOG termina 2026-06-13 | ✅ → al cerrar U2 |
| Mergear la rama a `develop` tal cual | `develop` existe (último commit 2026-06-11, 0 commits propios) y la rama le lleva **16 commits** → merge **fast-forward** sin conflictos | 🔄 → U0 (Etapa 12): fast-forward **sin checkout** en la Fase A; el working tree pasa a la rama de la etapa (ver etapa-12 §Manejo de ramas) |
| (nuevo) `AGENTS.md` | Es un prompt de **revisor Codex de solo lectura** ("NUNCA modifiques archivos"); choca con `/opsx:apply` para cualquier agente que lea AGENTS.md | 🔄 → U0 |

### §8 — Archivos críticos

🔄 Referencias verificadas: `ready` está en [main.py:271](../../trade-scanner/main.py#L271) (no L270-275), `run_group_scan`
en [main.py:400-409](../../trade-scanner/main.py#L400-L409) ✅. Se añaden [core/rules.py](../../trade-scanner/core/rules.py),
[core/features.py:320](../../trade-scanner/core/features.py#L320) (`resolve_filters`), [strategies/swing_eod.py](../../trade-scanner/strategies/swing_eod.py),
[core/pipeline.py:223](../../trade-scanner/core/pipeline.py#L223), [config/notifications.json](../../config/notifications.json) y
[scripts/notify_email.py:72](../../scripts/notify_email.py#L72) (puntero fijo `latest.json`).

---

## 2. Hallazgos nuevos (evidencia verificada el 2026-09-22)

| # | Hallazgo | Evidencia | Unidad |
|---|---|---|---|
| **H1** | **#12 está ACTIVO.** `swing_eod_short` en `enabled: true` (sin commitear) y sembrado en `storage/` | Backtest prod 2026-09-20: **500/1163** candidatos short son tickers solo de `swing_advances`; **10/11** long son solo de `swing_declines`. Causa: unión en [main.py:65-78](../../trade-scanner/main.py#L65-L78) + mapa completo en [pipeline.py:223](../../trade-scanner/core/pipeline.py#L223). Las exclusiones del log también se duplican: cada pipeline lista los mismos 16 fríos | U0 (R-cfg) + U3a |
| **H2** | **El short no es el espejo efectivo del long.** Solo `swing_eod` tiene `filters`; el short cae al default estricto. Long W:20/M:20 = `{near, above_mild}` (pullback); short = `{below_mild, below_strong, extended_below}` (tendencia) | Misma corrida: long con candidatos **11/116** días, short **116/116**. [strategies.json:28-44](../../config/strategies.json#L28-L44), [swing_eod.py:17](../../trade-scanner/strategies/swing_eod.py#L17) | U3b |
| **H2b** | Vocabulario de `filters` = canónico "above" + espejo; `resolve_filters` acepta los 7 buckets → un short escrito como `below_mild` **se invierte sin aviso** a `above_mild` | [features.py:357](../../trade-scanner/core/features.py#L357) + [rules.py:65](../../trade-scanner/core/rules.py#L65) | U3b |
| **H2c** | `filters["W:8"]` es clave muerta (ninguna rule usa `(W,8)`); `filters["D:8"]` alimenta una rule `required=False` que no filtra; [pipeline.py:164](../../trade-scanner/core/pipeline.py#L164) dice "en V1 todas son required" | [swing_eod.py:27-31](../../trade-scanner/strategies/swing_eod.py#L27-L31) | U3b |
| **H3** | 13 % del universo excluido por `M:20` fría por historia corta; invisible en la salida. Que M:20 esté fría **no se predice contando barras**: CAI (538 barras, con huecos) está fría y BBNX (411) no; depende de cuántos meses calendario distintos caen en la ventana de warmup | 16 fríos en el scan del 09-17 (§2); `ready: 95/125` se mide al cerrar el warmup (04-02), no en el último scan | U1 |
| **H4** | **La última sesión no se escanea.** Con `end_date = 2026-09-18` (viernes, último día con datos) el log termina el 09-18 a las 16:00 y el scan `after_close` (16:01) no dispara; la watchlist "de la semana" usa **cierres del jueves 09-17** | `latest.json` `as_of = 2026-09-17T20:01Z`; CHTR `price = 133.36` = cierre del 09-17 (el del 09-18 es 128.135). Refuta la premisa de [etapa-11:30](etapa-11-fecha-desde-universo.md#L30) | U2 |
| **H4b** | Footer "as of 09-19-2026" es la **fecha de descarga (sábado)**; la sesión retratada es `max(Time) = 2026-09-18`. La spec de E11 prioriza el footer | CSV `storage/universes/*.csv` | U2 |
| **H5** | Working tree con 3 cambios sin commitear que cambian el comportamiento en prod: `enabled` del short, `end_date` 09-18, `lean.json` (timestamp). `storage/results/swing_eod/latest.json` proviene de la corrida contaminada | `git status` / `git diff` | U0 |
| **H6** | PLAN: Etapa 0 `pendiente`, 6B `en progreso`, sin 9A/9B/10/11 | §1 | U0 |
| **H7** | Suite no verificada hoy (Docker apagado) | §1 | U0 (G2 inicial) |
| **H8** | Datos de referencia para 5B: `spy.zip` termina el **2021-03-31**, `aapl/ibm.zip` el **2026-06-11**. El fixture INTERINO lee `spy.zip` 1998–2021: **refrescar SPY con `alpaca_to_lean.py` (default `--start 2016-01-01`) sobrescribe el zip y rompe ese fixture** (y 2016→ no alcanza para M:200). `data/stooq_lean/` ya tiene SPY/AAPL/IBM hasta 2026-06-11 con historia larga | `unzip -p …` ; [test_sma_regression.py:12](../../trade-scanner/tests/test_sma_regression.py#L12) | U1b |
| **H9** | Shortability sin decidir: el ranking short elige a los que más caen, justo los que activan la **SSR (Reg SHO 201, caída ≥10 %)**; HTB no es detectable con los datos actuales. Ninguna decisión escrita (`grep borrow|shortable` en SPECS/PLAN = 0) | — | U3b (SSR) / Fase 2 (HTB) |
| **H10** | `AGENTS.md` de solo lectura choca con OpenSpec | §7 | U0 |
| **H11** | El tope de 200 se aplica por `UniverseSpec` ([universe.py:72](../../trade-scanner/core/universe.py#L72)), no a la unión (máximo real 400). Hoy 125 → sin impacto | — | U3a |
| **H12** | Sin sizing ni órdenes en código versionado. Los `set_holdings` que encuentra el grep están en `trade-scanner/backtests/2026-06-11_*/code/main.py` (copias del template, gitignoreadas) | `.gitignore:5` | — (opcional: borrar esas carpetas) |

---

## 3. Roadmap definitivo

Orden: **U0 → U1 → U1b → U2 → U3a → U3b → U4.** U1b puede ir en paralelo a U1 (1 h del trader).

### U0 — Estabilizar la base y adoptar OpenSpec · **Etapa 12** ([etapa-12.md](etapa-12.md), sin change) · ~3-4 h

**Por qué va primero:** hoy la config sembrada publica watchlists contaminadas (H1) y el contrato con el
agente (PLAN) está desfasado (H6). Todo change posterior necesita una base limpia y un baseline confiable para G4.

Orden de pasos elegido para que **todos los commits queden antes del merge**:

1. Levantar Docker y correr `bash scripts/run_tests.sh` → registrar la cifra real (H7). Si falla, se arregla
   antes de seguir.
2. Working tree (H5): los cambios ya se descartaron el 2026-09-23; queda **reseed** de `storage/`, que sigue con el short en `true` (R-cfg; justificación en U3b §Rollback).
   `end_date` 09-18 se commitea como edición semanal o se descarta; U2 la elimina.
3. Resincronizar PLAN §7: 0 (estado real), 5B (solo F3 abierta), 6B (completada), 9A, 9B, 10, 11 como entradas con
   link a sus specs; registrar U1–U3b como etapas nuevas (numeración a decidir; propuesta: 12, 12b, 13, 14, 15).
4. Instalar OpenSpec: Node ≥ 20 + `npm i -g @fission-ai/openspec` (hoy no están ni `node` ni `openspec`).
   `openspec init` solo para Claude Code; revisar el diff antes de commitear.
5. (Codex ya no está disponible desde 2026-09-23: `run_review.sh` pasa a opcional; la revisión por defecto es `/opsx:verify` + `/code-review`.) Mover `AGENTS.md` a `docs/review/codex-review-prompt.md` y actualizar
   [run_review.sh:39,47](../../scripts/run_review.sh#L39), que hoy pide a Codex "los criterios de AGENTS.md":
   hay que pasarle la ruta nueva explícitamente. Editar CLAUDE.md con §0.4.
6. **Spike de ciclo OpenSpec:** un change de prueba (`chore-openspec-smoke`, un requisito ADDED trivial) recorre
   `validate --strict` → `/opsx:sync` → `openspec archive --yes`. Objetivo: comprobar que `archive` tras `sync`
   no reaplica los deltas ni exige `--skip-specs` (prohibido en §0.4). Si lo exige, se ajusta §0.4 antes de U1.
   Al terminar, se elimina el requisito trivial de `openspec/specs/` con un commit aparte, para que las specs
   arranquen vacías.
7. Cerrar por escrito la pregunta del POC Finnhub (§6) en `docs/ROADMAP.md`.
8. Baseline (§0.5): vaciar `storage/results/`, backtest prod de la ventana actual con solo el long, copiar a
   `baselines/scan-v2026.09.xx-baseline/` con su manifiesto, commit y tag.
9. Manejo de ramas según [etapa-12.md §Manejo de ramas](etapa-12.md): Fase A (fast-forward de `develop` y `main`, tag `scan/v2026.09.23-pre-ciclo`, rama `feature/etapa-12-bootstrap-openspec` con la spec como primer commit) y, al cerrar, merge `--no-ff` a `develop` + promoción fast-forward a `main`. Una rama por etapa desde aquí.

**Done when:**
- [ ] `run_tests.sh` verde con la cifra registrada en PLAN
- [ ] `git status` limpio; `sha256sum storage/config/strategies.json config/strategies.json` iguales, con el short en `false`
- [ ] `baselines/<tag>/` versionado con `manifest.sha256`; **ningún** `results/swing_eod/**/2026*.json` del baseline contiene tickers fuera de `swing_advances` (script de U3a o equivalente ad hoc)
- [ ] PLAN §7 contiene 0/5B/6B/9A/9B/10/11 con estado real y U1–U3b como etapas pendientes
- [ ] `openspec --version` OK; `openspec validate --all --strict` exit 0; el change de prueba del paso 6 está archivado con exit 0 en `sync` y en `archive`
- [ ] `AGENTS.md` ya no contiene instrucciones de solo lectura; `run_review.sh` apunta a la ruta nueva; CLAUDE.md contiene §0.4
- [ ] Merge `[Etapa 12] merge:` en `develop`; `main` == `develop`; tags pre-ciclo, baseline y promoción en `origin`; ramas integradas borradas

### U1 — `add-data-coverage-gate` · 📦 change · P0 · ~4-6 h

**Por qué:** la cobertura pasó del 60 % (09-13) al 100 % (09-20) solo porque alguien corrió el refresh a mano, y
la salida de ambas semanas se ve igual. Además, 13 % del universo se excluye por historia corta sin dejar rastro (H3).
Sin esto ninguna watchlist es auditable.

**Qué (tasks):**
0. `session_date(raw_csv) -> date` = `max(Time)` del CSV, en `core/universe.py` (sin imports LEAN, con tests). El
   preflight la necesita para saber contra qué fecha medir la frescura, y U2 la reutiliza (dependencia resuelta aquí,
   no en U2).
1. `scripts/preflight_coverage.py` (host, patrón `check_alpaca_credentials.py`, exit code como gate):
   universo post-filtro (reusa `UniverseSpec`, sin CLR) → por ticker: zip existe; última barra ≥ `session_date`;
   **historia suficiente por serie**, emulando cómo se enfría el engine: para W/M, contar **semanas/meses calendario
   distintos con al menos una barra** dentro de `[start − warmup_depth, sesión]`, con `warmup_depth` derivado de
   `plan_warmup` (nunca un número fijo; contar barras no sirve, H3). `warmup_depth` está en **barras de trading**:
   el host lo convierte a fecha usando las propias fechas del zip de cada ticker (la barra N-ésima hacia atrás
   desde la sesión), sin calendario bursátil externo. Los tickers con huecos pueden diferir del engine: la
   coherencia se exige en el Done when. Salida: tabla + faltantes/desactualizados/historia
   corta; exit ≠ 0 si faltan zips o están desactualizados; "historia corta" se reporta sin fallar (es estructural).
2. Runbook (README "Operación semanal"): paso obligatorio `alpaca_to_lean.py --universe <csv> --end <sesión>` →
   preflight → backtest.
3. Envelope ([core/output.py](../../trade-scanner/core/output.py) `build_envelope`): `coverage = {universe_size, ready,
   excluded: [{ticker, reason}]}` por miembro + `config_sha256` (R-trace). WARNING si el universo quedó vacío (§5).
4. Email render: línea de cobertura ("evaluados 60/76; 16 excluidos por historia corta").

**Precondición:** U0 cerrado. **Gates:** G0, G1, G2, G3, G4 (diferencias esperadas: solo campos nuevos en el
envelope; candidatos idénticos al baseline), G5.
**Rollback:** R-git (el cambio es aditivo en el envelope; `notify_email.py` debe tolerar la clave nueva).

**Done when:**
- [ ] `session_date` sobre los CSV del 09-19 → `2026-09-18`; CSV sin columna `Time` → `ValueError` (tests)
- [ ] Preflight sobre los CSV del 09-19: 76/49 con zip, 0 desactualizados, exit 0. Con un zip borrado o truncado antes de la sesión → exit ≠ 0
- [ ] **Coherencia preflight ↔ engine:** el conjunto "historia corta" del preflight == el `coverage.excluded` del envelope del último scan de la ventana (hoy, los 16 del 09-17); cualquier diferencia queda explicada en `design.md`
- [ ] `latest.json` de un backtest prod trae `coverage` por miembro y `config_sha256`; el hash coincide con `sha256sum storage/config/strategies.json`
- [ ] G4: candidatos idénticos al baseline; solo cambian los campos nuevos
- [ ] Test: miembro con universo vacío post-filtro → sección vacía, `WARNING` en el log y `coverage.universe_size = 0` en el envelope
- [ ] README con el runbook de 3 pasos (refresh → preflight → backtest)

### U1b — `close-5b-reference-fixture` · 📦 change · P0 · ~1 h del trader + ~1 h

**Por qué:** si la semana de `Calendar.WEEKLY` no cuadra con el gráfico de referencia, `main_timeframe: "W"` y los
filtros W:20 están calibrados contra otra realidad. Es riesgo de corrección, no papeleo (§4).

**Alcance exacto:** cierra 5B **F3** (T6.3 + T6.4); F2 ya está cerrada.
**Precondición (H8):** no refrescar `data/equity/usa/daily/{spy,aapl,ibm}.zip` (el fixture INTERINO lee `spy.zip`
1998–2021, y Alpaca IEX desde 2016 no alcanza para M:200). La fuente es la que define T6.3: **`data/stooq_lean/`**
(split-only; hoy SPY 2005→, AAPL 1984→, IBM 1962→, todos hasta **2026-06-11**, así que M:200 es viable). Fecha de
corte por defecto: **2026-06-11** (no requiere descargar nada); si se refresca Stooq, la nueva fecha se anota en `design.md`.
**Qué:** comparar las **27 series** (SPY/AAPL/IBM × SMA 8/20/200 × D/W/M) contra TradingView/IBKR en modo *Adjusted*
(split-only) a la fecha de corte, con ≤0,25 % de desvío; verificar que la semana de referencia cierra el viernes
(convención `Calendar.WEEKLY`); congelar como fixture autoritativo y reemplazar el test INTERINO.
**Gates:** G0–G2, G5. **Rollback:** R-git (solo afecta tests).

**Done when:**
- [ ] Tabla en `design.md`: 27 filas (serie, valor LEAN, valor plataforma, % desvío), todas ≤0,25 %, con fecha de corte y ajuste declarados
- [ ] Una fila explícita que confirma el cierre semanal (valor W:8 del viernes de corte coincide)
- [ ] `test_sma_regression.py` sin "INTERINO", leyendo el fixture autoritativo; suite verde
- [ ] PLAN Etapa 5B → `completada` (F3 `[x]`)

### U2 — `derive-backtest-range-from-universe` (ex Etapa 11) · 📦 change · P0 · ~5-7 h

**Por qué:** elimina la edición manual semanal de `main.py` y, sobre todo, **corrige H4**: hoy la watchlist llega
un día tarde aunque los datos estén.

**Cambios respecto de la spec de E11:**
1. **Fecha de sesión = `session_date` de U1** (`max(Time)`); el footer solo sirve para control de coherencia (H4b).
2. **Spike previo obligatorio (primera tarea):** determinar empíricamente qué `end_date` hace que el scan
   `after_close` de la última sesión dispare con feed DAILY (candidatas: sesión + 1 día; siguiente día hábil). Se
   documenta en `design.md` con el log como evidencia. No se asume nada. **Plan B** si ninguna candidata dispara
   (el reloj no avanza sin datos y la última barra es del 09-18 16:00): scan final del grupo en `on_end_of_algorithm`
   con guard "solo si la sesión `session_date` aún no se escaneó", decidido y justificado en `design.md`.
3. Puntero para el host (decisión que no puede quedar para después): carpeta por fecha **y** `results/{base}/latest.json`
   se mantiene como espejo del último scan → `notify_email.py` no cambia.

**Precondición:** U1 (el preflight valida que existan datos para la sesión derivada). **Gates:** G0–G5, G-data.
**Rollback:** R-git.

**Done when:**
- [ ] Spike documentado en `design.md` con el extracto de log de la opción elegida (candidata o plan B)
- [ ] Con los CSV del 09-19: log `asof=2026-09-18`, y `latest.json.as_of` corresponde a la **sesión 2026-09-18** (verificable: el `price` de un candidato = cierre del 09-18 en su zip, p. ej. CHTR 128.135 si sale); exactamente **un** scan por sesión (sin duplicar el 09-18)
- [ ] **Test** (no backtest: con el short apagado en prod solo se carga un CSV): dos CSV de sesiones distintas → `ValueError` en la reconciliación de fechas
- [ ] `results/{base}/{YYYYMMDD}/` y `results/{base}/latest.json` coexisten; `notify_email.py --base swing_eod` sin cambios funciona
- [ ] `main.py` sin fechas prod hardcodeadas; dev inalterado; README sin el paso 4 manual
- [ ] Al cerrar: DEVLOG/ROADMAP con una entrada por etapa (§7.2)

### U3a — `partition-scan-universe-per-strategy` (#12) · 📦 change + ADR-006 · P1 · ~3-4 h

**Por qué:** H1 contamina ambos lados, y además **es la precondición de un rollback limpio del short**: mientras
exista la unión, apagar o encender el short cambia también la watchlist long (10/11 long del 20-sep venían de declines).

**Qué:** [propuesta-diseno-12.md](../../revisiones/20260619-205134/propuesta-diseno-12.md) tal cual (mapas por miembro en
`initialize()`, `run_group_scan` recibe `symbol_data_by_member`) + ADR-006 ("cada pipeline escanea exactamente su
universo declarado; la unión solo para suscripción/warmup") + **tope de 200 sobre la unión: si la unión supera 200 →
`ValueError` en `initialize()`** (truncar rompería el invariante de ADR-006) + script
`scripts/check_watchlist_universe.py` (verifica que cada candidato de cada `results/<base>/**/2026*.json` pertenezca al
universo de su miembro; exit ≠ 0 si hay violaciones; queda como herramienta de G4).

**Gates:** G0–G5. G4 **con el short encendido solo en la rama de prueba** (no se promueve).
**Rollback:** R-git.

**Done when:**
- [ ] Tests: mapas disjuntos por miembro + partición L5-style (cierra #25) + unión > 200 → `ValueError`
- [ ] **Test unitario de invariancia:** `run_group_scan` con un FakePipeline long produce la misma sección long con y sin el miembro short (necesario porque el baseline long real tiene ~1 candidato en 116 sesiones: un diff vacío contra vacío demuestra poco)
- [ ] G4 con short activo en la rama: `check_watchlist_universe.py` exit 0 sobre toda la ventana
- [ ] **Invariancia del long en backtest:** para cada `results/swing_eod/**/2026*.json`, `jq -S .sections.long` idéntico al del baseline
- [ ] ADR-006 aceptado; en el log, cada pipeline solo lista exclusiones de su propio universo

### U3b — `enable-short-side` · 📦 change (+ enmienda a ADR-005) · P1 · ~4-6 h + calibración del trader

**Por qué no es "cambiar el flag":** el código del espejo es correcto (el long→short invierte `SMAPositionRule` y
`NotExtended` en [rules.py:65](../../trade-scanner/core/rules.py#L65) / [rules.py:109-116](../../trade-scanner/core/rules.py#L109-L116)),
y el fallback `ABOVE` es **comportamiento documentado** ([etapa-10:52](etapa-10-refinamiento.md#L52),
[swing_eod.py:15-16](../../trade-scanner/strategies/swing_eod.py#L15-L16)). La brecha es de **producto y legibilidad**:
la config efectiva del short no es el espejo del long calibrado (H2), no puede escribirse en su vocabulario natural
sin invertirse (H2b), tiene claves que no hacen nada (H2c) y no dice nada sobre la operabilidad en corto (H9).

**Precondiciones:**
1. U3a archivado (sin él, ni la validación ni el rollback de U3b son confiables).
2. **Decisión de producto del trader:** ¿el short es el espejo del setup long (pullback a la SMA: `near`+`below_mild`)
   o un setup de tendencia (default actual)? Se registra en `design.md`.
3. Aprobación de la enmienda a ADR-005/D6B.4: los `filters` de config pasan a **vocabulario absoluto**, el mismo de
   la evidencia (los defaults del código siguen canónicos).

**Qué (tasks):**
1. `resolve_filters(full_config, name, side)` pre-espeja con `mirror_buckets(set, side)` (involución → la rule los deja
   literales). Migración nula: para long el espejo es la identidad y el short no tiene `filters` hoy.
2. Validación fail-fast: toda clave de `filters` debe corresponder a una serie de la composición (`W:8` → error o
   rule nueva, a decidir); decidir si `D:8` pasa a `required` o sale del bloque.
3. Log en `initialize()` del conjunto efectivo por rule con origen `config|default`.
4. Bloque `filters` explícito en `swing_eod_short` (y `market_close_short`) según la decisión 2.
5. `ssr_likely` (`day_change_pct <= -0.10`) en `ScanResult` y en el correo (feature L3, sin datos nuevos). Decisión
   escrita en PLAN/ADR: HTB fuera de V1 (Fase 2: enriquecimiento host-side con flags `shortable`/`easy_to_borrow` de Alpaca).
6. Corregir docs: [PLAN.md:158](../../PLAN.md#L158), [SPECS.md:121](../../SPECS.md#L121), [pipeline.py:164](../../trade-scanner/core/pipeline.py#L164),
   [swing_eod.py:4](../../trade-scanner/strategies/swing_eod.py#L4); renombrar `ABOVE` → `DEFAULT_FAVORABLE`.
7. **Solo después de G4:** `enabled: true` del short, commit `[Etapa N][enable-short-side] promote` + tag.

**Gate G4 específico (todo con el short activo en la rama):**
- `check_watchlist_universe.py` = 0 violaciones.
- Sección long **idéntica** al baseline (el short no altera el long).
- Todo bucket de la evidencia de cada candidato short ∈ conjunto configurado para su serie (script o test de integración).
- Log de `initialize()`: ninguna rule de estrategia habilitada con origen `default`.
- Revisión del trader sobre **≥3 corridas semanales reales**, cada una con su propio CSV y su sesión (no sesiones
  pasadas de una misma ventana: usan el universo futuro, §0.5). Criterio registrado en `design.md`: por cada
  candidato short, ¿encaja con el setup decidido en la precondición 2? (sí/no + motivo). Umbral de aprobación
  fijado **antes** de mirar los resultados.

**Rollback — por qué `enabled: false` es la acción de reversión de U3b:**

1. **Separa "publicar" de "código".** Lo que puede resultar inaceptable tras la promoción es la *watchlist* (setup
   distinto del pretendido, candidatos no operables por SSR/HTB, ruido), no el código: el espejo es correcto y el
   pre-espejo de `resolve_filters` es la identidad para el long. Por eso la reversión es de config (R-cfg), de
   segundos, sin revertir commits.
2. **Es limpia solo gracias a U3a.** Con la partición, apagar el short elimina su pipeline en `initialize()`
   ([main.py:56-60](../../trade-scanner/main.py#L56-L60)) y el envelope pasa a traer solo la sección long
   ([pipeline.py:222](../../trade-scanner/core/pipeline.py#L222)), **idéntica** a la del baseline (ya demostrado en G4).
   Matiz esperado, no es un fallo: `totals.short` sigue apareciendo con 0, y el correo **pierde** el bloque short (no
   muestra "(sin candidatos)", porque ese texto solo sale para lados activos). Sin U3a,
   el mismo flag cambiaría también el long: por eso hoy, en U0, R-cfg sirve para *detener la contaminación*, pero
   todavía no es un rollback "quirúrgico".
3. **Deja rastro auditable.** Con `config_sha256` (U1), cada correo posterior demuestra que salió de la config revertida.
4. **Cómo encaja en OpenSpec:** si el rollback ocurre **antes de `archive`**, el change sigue activo y la tarea 7
   se desmarca. Si ocurre **después**, va por la vía ligera (`[config] rollback enable-short-side` + nota en PLAN);
   la spec no se toca, porque el requisito ("el short está soportado y configurado explícitamente") sigue siendo
   cierto: solo está apagado. Si el defecto está en el **código** (p. ej. el pre-espejo invierte mal), la
   reversión es R-git al tag previo, no el flag.

**Disparadores de rollback:** violación de `check_watchlist_universe.py`; un candidato short con bucket fuera del
conjunto configurado; rechazo del trader en la revisión; cambio inesperado de la sección long.

**Procedimiento:** `enabled: false` → `seed_object_store.sh` (cloud: subir el JSON) → backtest prod (en live,
reiniciar) → verificar que `latest.json` no trae sección `short` y que su `config_sha256` ==
`git show <commit-rollback>:config/strategies.json | sha256sum`.

**Done when:**
- [ ] Decisión de setup short registrada en `design.md`; enmienda a ADR-005 aceptada
- [ ] Tests: short con `"W:20": ["near","below_mild"]` → rule permite exactamente `{near, below_mild}`; long sin cambios; clave muerta → `ValueError`
- [ ] G4 específico completo (5 checks), con la revisión del trader registrada en `design.md` y por encima del umbral fijado
- [ ] `ssr_likely` visible en CSV/JSON/correo; decisión HTB escrita
- [ ] Docs corregidos (task 6); PLAN.md:158 ya no afirma el espejo implícito
- [ ] Promoción: `enabled: true` commiteado, tag creado, rollback **ensayado una vez** en la rama (flag → reseed → backtest → long idéntico)

### U4 — Cierre formal de Fase 1 · tarea de PLAN Etapa 9 (sin change) · P2 · ~4-5 h

✅ Vigente: 9A T7 (portabilidad), 9A T8 (matriz de proveedor), #23 (`qc_notify` en cloud, **vía ligera `[config]`**),
#5 (anchor SPY: `spy.zip` termina en 2021 y prod lo usa solo por market hours; documentarlo), checklist de los 6 DoD
con el nº4 diferido (ADR-002). **Cambio:** toda evidencia de DoD debe salir de corridas **posteriores a U3b**
(U3b cambia la salida: `ssr_likely`, filtros del short).

**Done when:** los 6 DoD de SPECS §8 con evidencia citada (nº4 diferido y justificado); PLAN Etapa 9 → `completada`.

---

## 4. Diferidos (sin fecha en este ciclo)

| Ítem | Forma | Motivo |
|---|---|---|
| POC Finnhub (earnings / `10DayAverageTradingVolume`) | `/opsx:explore` post-V1; si procede, change + ADR | Sin semántica de producto en V1 (§6) |
| HTB/borrow | Fase 2, enriquecimiento host-side del CSV | Requiere datos que V1 no tiene (H9) |
| Modo `shadow` (`mode: off\|shadow\|on`) | Change pequeño en `core/output.py` | Útil si el correo se automatiza; en el flujo actual (backtest + revisión manual) G4 cumple ese papel |
| `run_review.sh`: `CHANGE=<id>` + `DRY_RUN` | Si se reactiva Codex, antes de revisar una etapa ≥13 | Codex no disponible desde 2026-09-23; sin ejecutable no hay forma de usarlo ni de probarlo. Etapa 12 T6 deja un aviso explícito en su lugar |
| Borrar `trade-scanner/backtests/2026-06-11_*` | Limpieza local | Evita falsos positivos en greps de órdenes (H12) |

## 4b. Riesgos abiertos que este ciclo no resuelve (explícitos)

| Riesgo | Evidencia | Tratamiento |
|---|---|---|
| **El long, ya aislado, casi nunca produce candidatos** | De los 11 candidatos long de la ventana (116 sesiones), 10 venían de declines por #12 → queda ~1 legítimo; 0 en la última sesión. W:20 `{near, above_mild}` lo corta (p. ej. 41→0 el 09-17) | Tras U3a: revisión de calibración del long por la **vía ligera `[config]`** (el mecanismo `filters` ya existe), con G4 y revisión del trader sobre corridas semanales reales. No bloquea U3b, pero sin ella el ciclo hace auditable una watchlist long casi siempre vacía |
| Sesgo de supervivencia en backtests de ventana | §0.5 | Métricas solo comparativas; validación de producto con corridas semanales reales |
| El refresh semanal (runbook de U1) cambia la base de G4 | §0.5 | Datos congelados durante el ciclo + manifiesto |

## 5. Decisiones que necesita el usuario

1. ~~Numeración de las etapas nuevas en PLAN~~ **Decidido 2026-09-23:**
   - 12 = U0 ([etapa-12.md](etapa-12.md), último spec en formato clásico: es el bootstrap de OpenSpec)
   - 13 = U1
   - U1b = cierre de 5B F3
   - U2 = Etapa 11 con re-scope
   - 14 = U3a
   - 15 = U3b
   - U4 = Etapa 9

   Desde la 13, cada unidad es un change de OpenSpec.
2. Setup del short: espejo del pullback long o tendencia (U3b, precondición 2).
3. Vocabulario absoluto en `filters` (enmienda a ADR-005).
4. `W:8`: ¿rule nueva o clave eliminada? `D:8`: ¿required u opcional sin filtro?
5. `end_date`: se decide con evidencia en el spike de U2, no por preferencia.
6. Si la recalibración del long (§4b) entra en este ciclo (tras U3a) o queda para el siguiente.

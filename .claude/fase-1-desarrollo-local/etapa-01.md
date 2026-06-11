# Etapa 1 — Workspace LEAN, cuentas y credenciales

**Estado:** completada
**Depende de:** Etapa 0 (Docker operativo, Python 3.11 en venv, `lean --version` pasa)
**Completada:** 2026-06-11

## Objetivo

Entorno local LEAN completamente operativo: Alpaca paper configurado, workspace inicializado con `lean.json`, y `lean backtest "trade-scanner"` corriendo sin errores sobre el algoritmo de ejemplo. Esta etapa no toca código de negocio — solo valida que el toolchain completo funciona end-to-end.

> **`lean login` (QuantConnect cloud) no es necesario para Fase 1.** Los backtests locales corren 100% dentro de Docker sin autenticación QC. `lean login` solo hace falta para `lean cloud backtest` y `lean data download` desde el catálogo QC — ninguno de los dos está en alcance de Fase 1. La portabilidad a QC cloud es un goal de diseño del código, no un requisito operativo de esta fase.

---

## Tareas

### T1 — Crear cuenta Alpaca paper y obtener API key/secret ✅

**Criterio de aceptación:** Key ID y Secret Key de Alpaca paper guardados en `.env` en la raíz del repo (gitignoreado).

**Cómo se hizo:**
- Credenciales obtenidas desde Alpaca dashboard → Paper Trading → API Keys.
- Guardadas en `.env` en la raíz del repo (excluido de git vía `.gitignore` línea `.env`).
- `.env` tiene las variables `ALPACA_KEY_ID` y `ALPACA_SECRET_KEY`.

---

### T2 — Inicializar el workspace ✅

**Criterio de aceptación:** `lean.json` y `data/object-store/` existen en la raíz del workspace; `data/*` está en `.gitignore` con excepción de `data/object-store/`.

**Cómo se hizo (desvío documentado):**
- `lean init` requiere auth QC paga (selección de organización). Se resolvió sin QC:
  1. Se descargó `config.json` directamente del repo público de LEAN en GitHub (mismo archivo que descarga el CLI internamente).
  2. Se aplicó la transformación `clean_lean_config()` del CLI (elimina claves auto-configurables).
  3. Se registró la ruta en `~/.lean/config` vía `container.lean_config_manager.store_known_lean_config_path()`.
  4. Se añadió `"organization-id": "00000000000000000000000000000000"` para satisfacer el check de versión del CLI (ver nota abajo).
- `data/` y `data/object-store/` creados manualmente.
- `.gitignore` actualizado con `data/*` y `!data/object-store/`.

> **Nota — organization-id placeholder:** El CLI v1.0.x exige `organization-id` no-nulo en `lean.json` para cualquier comando (check de compatibilidad de versión). Para `lean backtest` local el valor nunca se valida contra QC. Reemplazar con el org-id real antes de usar `lean live` (ver ADR-002).

> **Nota — lean.json reformateado:** El linter reformateó `lean.json` a JSON estándar (sin comentarios) en la primera escritura del CLI. El engine acepta ambos formatos; el resultado es equivalente.

---

### T3 — Crear el proyecto trade-scanner y correr el smoke test ✅

**Criterio de aceptación:** `lean backtest "trade-scanner"` completa; los logs muestran "Successfully ran 'trade-scanner'".

**Cómo se hizo:**
```bash
lean project-create "trade-scanner" --language python
lean backtest "trade-scanner"
```
- La imagen `quantconnect/lean:latest` (~3–4 GB) se descargó en la primera ejecución.
- El backtest corrió con 0 datos locales (100% failed data requests) — esperado y no bloqueante.
- Log clave: `Successfully ran 'trade-scanner' in the 'backtesting' environment`.

> **Nota — flag `--language`:** `lean project-create` requiere `--language python` explícito si el default-language del CLI no está configurado. Sin él falla con error de lenguaje faltante.

---

### T4 — Credenciales Alpaca fuera del repo ✅

**Criterio de aceptación:** `lean.json` tiene campos Alpaca con strings vacíos; credenciales reales solo en `.env` (gitignoreado).

**Cómo se hizo:**
- `lean.json` tiene `alpaca-api-key: ""`, `alpaca-api-secret: ""`, `alpaca-paper-trading: true` con valores vacíos.
- Las credenciales reales viven exclusivamente en `.env`.

> **Nota — `${VAR}` no soportado:** El LEAN CLI no realiza sustitución de variables de entorno en `lean.json`. El enfoque correcto es dejar los campos vacíos en `lean.json` (commiteado) y configurarlos vía `lean live` interactivo cuando se llegue a Etapa 9, o pasarlos como flags. Las credenciales reales nunca van en `lean.json`.

---

### T5 — Verificar `.gitignore` y auditoría de secretos ✅

**Criterio de aceptación:** `grep` de valores reales de claves retorna cero hits en archivos trackeables.

**Entradas de `.gitignore` relevantes añadidas en esta etapa:**
```
data/*
!data/object-store/
**/backtests/
**/.idea/
**/.vscode/
**/research.ipynb
.env
```

**Evidencia:** `grep -r "PKCQ\|Pxxm" . --exclude-dir=.git --exclude=".env"` → cero hits.

---

## Consideraciones técnicas — lo que cambió respecto al spec original

| Punto | Spec original | Realidad |
|---|---|---|
| `lean init` | Comandó directo | Requiere QC pago → se reemplazó con descarga directa de GitHub + script Python |
| `organization-id` | No mencionado | Requerido por CLI v1.0.x; se usa placeholder para backtest local |
| `${VAR}` en lean.json | Mencionado como soportado | NO soportado por el CLI; campos vacíos es el approach correcto |
| lean.json con comentarios | Formato con `//` | El CLI lo reformatea a JSON estándar en la primera escritura |
| Nombre del proyecto | "Screener" | "trade-scanner" (coincide con el repo) |
| `--language` en project-create | No mencionado | Requerido explícitamente si default-language no está seteado |
| Gitignore para backtests/.idea | No mencionado | Necesario; añadido con `**/backtests/`, `**/.idea/`, `**/.vscode/` |

---

## Scope

✅ Cuenta Alpaca paper creada y credenciales en `.env` (gitignoreado)
✅ `lean.json` generado y `data/object-store/` creados
✅ Proyecto `trade-scanner` creado con `lean project-create --language python`
✅ `lean backtest "trade-scanner"` corre; engine Docker operativo
✅ Credenciales Alpaca: campos vacíos en `lean.json`, valores reales solo en `.env`
✅ `.gitignore` protege secretos y artefactos de build/IDE

❌ Modificar `main.py` más allá del template (→ Etapa 2)
❌ Estructura `core/`, `strategies/`, `tests/`, `scripts/` (→ Etapa 2)
❌ `lean live` con Alpaca (→ Etapa 9; requiere QC paid — ver ADR-002)
❌ Datos históricos para backtest real (→ Etapas 4–5)
❌ `config.json` de estrategias (→ Etapa 2)

---

## Done when

- [x] `lean backtest "trade-scanner"` corre en Docker sin errores de toolchain
- [x] Credenciales Alpaca obtenidas, en `.env` (gitignoreado), `lean.json` sin valores reales
- [x] `grep` de claves reales retorna cero hits en archivos trackeables
- [x] `lean.json`, `.gitignore` y proyecto commiteados con `[Etapa 1] ...`

---

## Preguntas abiertas — resueltas

- [x] ¿Workspace root = repo root? **Sí.** `lean.json` vive en la raíz del repo `trade-scanner/`.
- [x] ¿`.env` compartido o individual? **Individual.** Cada desarrollador genera sus propias claves Alpaca paper.

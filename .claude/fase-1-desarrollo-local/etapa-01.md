# Etapa 1 — Workspace LEAN, cuentas y credenciales

**Estado:** pendiente
**Depende de:** Etapa 0 (Docker operativo, Python 3.11 en venv, `lean --version` pasa)
**Estimado:** 1–2 horas

## Objetivo

Entorno local LEAN completamente operativo: Alpaca paper configurado en `lean.json`, workspace inicializado con `lean init`, y un primer `lean backtest "Screener"` corriendo sin errores sobre el algoritmo de ejemplo que genera la CLI. Esta etapa no toca código de negocio — solo valida que el toolchain completo funciona end-to-end.

> **Nota: `lean login` (QuantConnect cloud) no es necesario para Fase 1.** Los backtests locales corren 100% dentro de Docker sin autenticación QC. `lean login` solo hace falta para `lean cloud backtest` y `lean data download` desde el catálogo QC — ninguno de los dos está en alcance de Fase 1. La portabilidad a QC cloud es un goal de diseño del código (solo API de `QCAlgorithm`), no un requisito operativo de esta fase.

---

## Tareas

### T1 — Crear cuenta Alpaca paper y obtener API key/secret

**Criterio de aceptación:** Key ID y Secret Key de Alpaca paper visibles y anotadas en un gestor de contraseñas o archivo local fuera del repo.

**Notas:**
- Registrarse en https://alpaca.markets (cuenta paper = gratuita, sin depósito real).
- En el dashboard de Alpaca: sección **Paper Trading → API Keys → Generate New Key**.
- El par generado (`APCA-API-KEY-ID` + `APCA-API-SECRET-KEY`) se usa solo en Fase 1. **No generar claves de live trading en esta etapa.**
- Alpaca free usa datos IEX (volumen subestimado, 15 min delay): documentado y esperado — no es un error.
- Guardar las claves en un gestor de contraseñas (1Password, Bitwarden, etc.) o en un archivo `.env` local **fuera del directorio del repo**. En ningún caso dentro del workspace.

---

### T2 — Inicializar el workspace con `lean init`

**Criterio de aceptación:** `lean.json` y la carpeta `data/` existen en la raíz del workspace; el contenido de `lean.json` es el generado por defecto por la CLI (sin modificaciones aún).

**Notas:**
- Desde la raíz del repo (donde vive `.python-version` y `.venv`), con el venv activo:
  ```bash
  source .venv/bin/activate
  lean init
  ```
- El comando genera:
  - `lean.json` — archivo de configuración del workspace (provider de datos, broker, rutas).
  - `data/` — carpeta de datos local que la CLI gestiona (no versionar su contenido pesado).
- Revisar `lean.json` generado para entender su estructura; no editar todavía.
- Agregar a `.gitignore` el contenido de `data/` (excepto `data/object-store/` que sí se versiona por los CSVs de universo):
  ```
  data/*
  !data/object-store/
  ```
- `lean.json` **sí se versiona** (es configuración de workspace, sin credenciales en él todavía).

---

### T3 — Crear el proyecto trade-scanner y correr el smoke test

**Criterio de aceptación:** `lean backtest "trade-scanner"` completa sin errores; los logs del backtest muestran al menos una línea de resultado (ej. "Backtest Complete") en la terminal.

**Notas:**
- Crear el proyecto con el template por defecto:
  ```bash
  lean project-create "trade-scanner"
  ```
  Esto genera `trade-scanner/main.py` con el algoritmo de ejemplo de QC (`BuyAndHoldAlgorithm` o similar). El nombre coincide con el del repo para evitar ambigüedad.
- Correr el backtest:
  ```bash
  lean backtest "trade-scanner"
  ```
  La primera ejecución descarga la imagen Docker `quantconnect/lean` (~2–4 GB) — puede tardar varios minutos según la red.
- El backtest usará datos históricos locales o los descargará según la config; para el algoritmo de ejemplo con AAPL o SPY, LEAN CLI suele incluir datos de muestra en `data/`.
- **Si falla por datos faltantes:** es esperado en el algoritmo de ejemplo si pide datos no incluidos. El criterio es que el engine arranque y no falle por configuración/permisos/Docker — un fallo de datos es aceptable y no bloquea la etapa.
- Si falla por permisos Docker: verificar que Docker Desktop está corriendo y el usuario tiene acceso al socket (`docker run hello-world` debe seguir pasando).

---

### T4 — Configurar credenciales Alpaca en `lean.json` (sin commitear secretos)

**Criterio de aceptación:** `lean.json` tiene el bloque de configuración de Alpaca con los campos correctos; los valores reales de las claves están en variables de entorno o en un archivo `.env` local excluido del repo — **no hardcodeados en `lean.json`**.

**Notas:**
- LEAN CLI soporta variables de entorno en `lean.json` con la sintaxis `${VAR_NAME}`. Usar ese mecanismo para las claves:
  ```json
  {
    "data-folder": "data",
    "environments": {
      "paper-alpaca": {
        "live-mode": true,
        "live-mode-brokerage": "AlpacaBrokerage",
        "live-mode-data-feed": "AlpacaDataFeed",
        "alpaca-access-token": "${ALPACA_KEY_ID}",
        "alpaca-access-token-secret": "${ALPACA_SECRET_KEY}",
        "paper": true
      }
    }
  }
  ```
- Crear un archivo `.env.local` (o equivalente) en la raíz del repo con los valores reales; agregarlo a `.gitignore`.
- Documentar en `README.md` (o en este archivo) qué variables de entorno se necesitan y cómo crearlas — sin revelar los valores.
- La estructura exacta de `lean.json` para Alpaca puede variar según la versión del CLI; consultar `lean live --help` o la documentación oficial si los campos difieren.

---

### T5 — Verificar `.gitignore` y que ningún secreto está en el repo

**Criterio de aceptación:** `git status` y `git diff --cached` no muestran ningún archivo con credenciales; `grep -r "APCA" .` (excluyendo `.git`) no retorna hits con valores reales de claves.

**Notas:**
- Revisar que `.gitignore` incluye al menos:
  ```
  .venv/
  .env
  .env.local
  *.env
  data/*
  !data/object-store/
  ```
- Confirmar que `lean.json` solo tiene `${VAR_NAME}` como valores de claves, no los valores reales.
- Las credenciales QC están en `~/.lean/credentials` (fuera del repo): no necesitan `.gitignore` extra.
- Hacer un commit limpio con todo lo del workspace: `[Etapa 1] init LEAN workspace, Screener project, gitignore`.

---

## Consideraciones técnicas específicas al stack

| Punto | Detalle |
|---|---|
| `lean.json` es la única frontera de configuración | Todo cambio de fuente de datos (Alpaca ↔ QC cloud) ocurre aquí. El código del algoritmo nunca referencia credenciales ni proveedores. Esta es la regla más crítica del proyecto. |
| Variables de entorno en `lean.json` | LEAN CLI expande `${VAR}` al leer el archivo. La alternativa es usar `lean live --brokerage AlpacaBrokerage` con flags, pero el enfoque de `lean.json` es más reproducible. |
| Paper vs live en Alpaca | Paper trading en Alpaca usa el mismo endpoint pero con datos simulados. En Fase 1 **siempre paper**. Los endpoints difieren (`paper-api.alpaca.markets` vs `api.alpaca.markets`); LEAN lo gestiona según la flag `"paper": true`. |
| Imagen Docker y primera ejecución | `quantconnect/lean` es una imagen x86_64 de ~3–4 GB. En Apple Silicon corre vía Rosetta/emulación. La primera descarga puede tomar 10–20 min; las siguientes ejecuciones usan caché. |
| `lean login` no requerido en Fase 1 | `lean backtest` local corre 100% en Docker sin auth QC. `lean login` solo hace falta para `lean cloud backtest` y `lean data download` del catálogo QC — ambos fuera de scope. La portabilidad a QC cloud es un constraint de diseño del código, no operativo. |
| Datos para el smoke test | El algoritmo de ejemplo generado por `lean project-create` puede requerir datos de AAPL o SPY. LEAN CLI descarga datos automáticamente si no están en `data/`; esto puede fallar si los datos requieren suscripción. Un error de tipo "No data found" no bloquea la etapa: lo que importa es que el engine Docker arranca correctamente. |
| Alpaca free = IEX | 15 min de delay en datos live y volumen muy subestimado. No es un error; está documentado. Los filtros del screener usarán volumen relativo, no absoluto, por esta razón (decisión de diseño de Etapas futuras). |

---

## Scope

✅ Cuenta Alpaca paper creada y credenciales guardadas de forma segura  
✅ `lean init` ejecutado: `lean.json` y `data/` en el workspace  
✅ Proyecto `Screener` creado con `lean project-create`  
✅ `lean backtest "Screener"` corre sin errores de toolchain  
✅ Credenciales Alpaca en `lean.json` vía variables de entorno (sin valores hardcodeados)  
✅ `.gitignore` protege secretos y artefactos locales  

❌ Modificar `main.py` más allá del template generado (→ Etapa 2)  
❌ Crear la estructura de carpetas `core/`, `strategies/`, `tests/` (→ Etapa 2)  
❌ Configurar o testear `lean live` con Alpaca real (→ Etapa 9)  
❌ Descargar datos históricos de Alpaca para backtest real (→ Etapas 4–5)  
❌ Definir parámetros de estrategias en `config.json` (→ Etapa 2)  
❌ Instalar dependencias de Python más allá de `lean` (→ Etapa 2)  
❌ Usar `lean data download` para poblar `data/` (→ Etapas futuras según necesidad)  

---

## Done when

- [ ] `lean backtest "Screener"` corre en Docker sin errores de toolchain (el engine arranca y produce output)
- [ ] Credenciales Alpaca paper obtenidas, guardadas fuera del repo, y configuradas en `lean.json` vía `${VAR}`
- [ ] `git status` no muestra ningún secreto; `grep -r "APCA" . --exclude-dir=.git` retorna cero hits con valores reales
- [ ] `lean.json` y `.gitignore` actualizados commiteados con mensaje `[Etapa 1] ...`

---

## Preguntas abiertas

- [ ] ¿El workspace root es el mismo directorio del repo (`trade-scanner/`) o se crea un subdirectorio separado? PLAN.md §3 sugiere que el repo raíz **es** el workspace (donde vive `lean.json`).
- [ ] ¿Se necesita un `.env.local` compartido entre miembros del equipo (pasado fuera de git) o cada desarrollador genera sus propias claves Alpaca paper?

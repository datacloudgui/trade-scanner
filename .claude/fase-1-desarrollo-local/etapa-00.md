# Etapa 0 — Entorno de desarrollo

**Estado:** pendiente
**Depende de:** ninguna
**Estimado:** 1–2 horas (más si hay problemas de red o compatibilidad)

## Objetivo

Máquina lista para correr `lean backtest` en cualquier PC: Docker operativo, Python 3.11 aislado en un virtualenv, y LEAN CLI instalado y verificado. Esta etapa no toca código de negocio ni cuentas; solo garantiza que el toolchain funciona.

---

## Tareas

### T1 — Instalar Docker Desktop

**Criterio de aceptación:** `docker run hello-world` imprime `Hello from Docker!` sin errores.

**Notas:**
- Descargar desde https://www.docker.com/products/docker-desktop/
- Elegir el instalador correcto para el chip: **Apple Silicon (M1/M2/M3)** o **Intel**.
- En Apple Silicon, Docker Desktop corre la imagen `quantconnect/lean` (x86_64) vía emulación automática. No se requiere configuración extra.
- Tras instalar, abrir Docker Desktop y esperar a que el icono de ballena en la barra de menú muestre "Docker Desktop is running" antes de correr cualquier comando.

---

### T2 — Instalar pyenv y Python 3.11

**Criterio de aceptación:** `pyenv versions` muestra `3.11.x` instalado; dentro del repo, `python --version` devuelve `Python 3.11.x`.

**Notas:**
- Instalar pyenv vía Homebrew (Mac): `brew install pyenv`.
- Agregar al shell (`~/.zshrc` o `~/.bash_profile`):
  ```bash
  export PYENV_ROOT="$HOME/.pyenv"
  export PATH="$PYENV_ROOT/bin:$PATH"
  eval "$(pyenv init -)"
  ```
  Recargar: `source ~/.zshrc` (o abrir terminal nueva).
- Instalar Python 3.11: `pyenv install 3.11.9` (u otra patch version disponible).
- Fijar versión local **en la raíz del repo**: `pyenv local 3.11.9` → genera el archivo `.python-version`.
- `.python-version` **se versiona en el repo** (garantiza reproducibilidad en cualquier máquina con pyenv).
- El motor LEAN también corre Python 3.11 (dentro de Docker), lo que elimina cualquier discrepancia entre host y engine.

---

### T3 — Crear virtualenv e instalar LEAN CLI

**Criterio de aceptación:** `lean --version` ejecutado con el venv activo devuelve un número de versión sin errores.

**Notas:**
- Crear el venv en la raíz del repo: `python -m venv .venv`
- Activar: `source .venv/bin/activate` (el prompt debe cambiar a `(.venv)`).
- Instalar CLI: `pip install lean`
- `.venv/` **nunca se versiona**; se recrea en cada máquina con `python -m venv .venv && pip install lean`.
- No instalar `lean` fuera del venv: contaminaría el Python del sistema y podría romper otras herramientas.

---

### T4 — Actualizar `.gitignore` y commitear archivos de entorno

**Criterio de aceptación:** `git status` no muestra `.venv/` como untracked; `.python-version` sí aparece en el árbol versionado.

**Notas:**
- Agregar al `.gitignore` (crear si no existe): `.venv/`
- Confirmar que `.python-version` **no** está en `.gitignore` (debe commitearse).
- Commit sugerido: `[Etapa 0] add .python-version and .gitignore`.

---

## Consideraciones técnicas específicas al stack

| Punto | Detalle |
|---|---|
| Python host vs engine | El host solo necesita Python 3.11 para el CLI y scripts auxiliares. El engine (código de negocio) corre siempre dentro de `quantconnect/lean` (Docker), que también usa Python 3.11. Nunca usar `python3` del sistema directamente. |
| Apple Silicon | `lean backtest` descarga y corre la imagen `quantconnect/lean` (x86_64). Docker Desktop gestiona la emulación transparentemente; el primer `lean backtest` tardará más por la descarga inicial (~3 GB). |
| LEAN CLI y Python 3.13 | Python 3.13 tiene breaking changes que pueden romper dependencias del CLI. Por eso se fija 3.11 en el repo: es la versión en la que LEAN es plenamente compatible. |
| Activar el venv | Debe estar activo (`source .venv/bin/activate`) antes de cualquier comando `lean`. Si no está activo, el CLI puede no encontrarse o ejecutarse con el Python del sistema. |
| `lean pull` / imagen Docker | El CLI descarga la imagen la primera vez que se lanza un backtest. No hace falta hacer `docker pull` a mano. |

---

## Scope

✅ Docker Desktop instalado y verificado  
✅ pyenv + Python 3.11 operativo en el repo  
✅ Virtualenv `.venv` con LEAN CLI instalado  
✅ `.gitignore` y `.python-version` en el repo  

❌ Crear cuenta en QuantConnect o Alpaca (→ Etapa 1)  
❌ `lean login` (→ Etapa 1)  
❌ `lean init` / `lean project-create` (→ Etapa 1)  
❌ Cualquier código de negocio (→ Etapa 2 en adelante)  
❌ Configurar credenciales o variables de entorno de brokers (→ Etapa 1)  
❌ Instalar dependencias de Python más allá de `lean` (→ Etapa 2)  

---

## Done when

- [ ] `docker run hello-world` imprime `Hello from Docker!`
- [ ] `python --version` dentro del venv muestra `Python 3.11.x`
- [ ] `lean --version` devuelve número de versión sin errores
- [ ] `.venv/` aparece en `.gitignore`; `.python-version` commiteado en el repo

---

## Preguntas abiertas

- [ ] ¿Se usa la misma máquina para desarrollo y para live en Fase 1, o habrá una segunda máquina/VPS ya en esta fase? (Si hay VPS, este setup se repite allí antes de Fase 2.)

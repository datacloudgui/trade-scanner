# ADR-001 — Versión de Python para host y engine

**Estado:** aceptado  
**Fecha:** 2026-06-11  
**Supersede a:** —  
**Supersedido por:** —

---

## Contexto

El stack tiene dos entornos Python distintos con ciclos de vida independientes:

- **Host** (la máquina del desarrollador): corre el LEAN CLI (`pip install lean`) y scripts auxiliares del repo.
- **Engine** (Docker `quantconnect/lean`): corre el código de negocio (`main.py`, `core/`, `strategies/`).

Al iniciar el proyecto, la máquina del desarrollador tenía Python 3.13.1 instalado como sistema. La pregunta era: ¿qué versión fijar en el repo, y es necesario aislarla?

---

## Opciones evaluadas

| Opción | Pro | Contra |
|---|---|---|
| Usar Python 3.13.1 del sistema | Sin instalación extra | LEAN CLI no la lista en sus classifiers; riesgo de rotura silenciosa |
| Devcontainer con Python 3.11 | Entorno 100% reproducible | Docker-in-Docker: el CLI lanza otro contenedor → complejidad innecesaria |
| **pyenv + Python 3.11 + virtualenv** | Reproducible, sin Docker-in-Docker, coincide con engine | Requiere pyenv en cada máquina (pasos documentados en Etapa 0) |

---

## Decisión

**Fijar Python 3.11 en el repo vía pyenv** (archivo `.python-version`) y **aislar el CLI en un virtualenv `.venv`**.

Versión exacta: **3.11.11**, para coincidir con la fijada en el engine Docker.

---

## Evidencia recopilada

Fuentes consultadas el 2026-06-11:

- **LEAN CLI `setup.py`** — `python_requires=">= 3.9"`, classifiers: 3.9–3.14.  
  → El CLI técnicamente acepta 3.13, pero el engine no.  
  Fuente: https://github.com/QuantConnect/lean-cli/blob/master/setup.py

- **`DockerfileLeanFoundation`** — `Miniconda3-py311_24.9.2-0`, label `strict_python_version=3.11.11`.  
  → El engine fija exactamente 3.11.11.  
  Fuente: https://github.com/QuantConnect/Lean/blob/master/DockerfileLeanFoundation

- **PyPI `lean`** — versión 1.0.225 (marzo 2026).  
  Fuente: https://pypi.org/project/lean/

- **Docker Hub `quantconnect/lean`** — imagen oficial del engine.  
  Fuente: https://hub.docker.com/r/quantconnect/lean

---

## Consecuencias

**Positivas:**
- Host y engine corren la misma versión → sin discrepancias si un script auxiliar importa tipos de LEAN.
- `.python-version` commiteado garantiza reproducibilidad en cualquier máquina con pyenv.
- `.venv/` aislado evita contaminación del Python del sistema.

**Negativas / trade-offs:**
- Cada desarrollador nuevo necesita instalar pyenv (pasos en [etapa-00.md](../fase-1-desarrollo-local/etapa-00.md)).
- Si el engine sube a 3.12 en el futuro, habrá que crear un nuevo ADR y actualizar `.python-version`.

---

## Revisión futura

Revisar cuando `DockerfileLeanFoundation` cambie el label `strict_python_version`. El comando para chequearlo:

```bash
docker inspect quantconnect/lean:latest | grep -i python_version
```

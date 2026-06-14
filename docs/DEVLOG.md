# Development Log

## 2026-06-10

Horas: 7

### Trabajo realizado
- Diseño top down con investigación de herramientas para el proyecto, consolidacion en SPECS.md
- Refinamiento del diseño por fases y etapas en PLAN.md
- Diseño y ejecucion de Etapa 0 de configuracion del ambiente, herramientas y pruebas iniciales (Docker, pyenv...)
- Diseño y ejecucion de Etapa 1 Inicio del workspace, configuracion de credenciales y repositorio
- Diseño y ejecucion de Etapa 2 Esqueleto funcional del proyecto, configuraciones de archivo de entrada y pruebas.
- Actualización de documentacion con las etapas avanzadas

### Comentarios
- Se deja hasta la etapa 2 en la rama main, se inicia el branching: develop y ramas feature

### Próximo paso
- Etapa 3 en su rama y siguientes

---

## 2026-06-10

Horas: 10h

### Trabajo realizado
- Diseño y ejecucion de Etapa 3 exploracion de contratos de datos para archivo de entrada usando ejemplo de barchart, diseño de universos de acciones.
- Cierre de etapa 3 y merge a develop
- Diseño y ejecucion de Etapa 4 especificacion del universo y arquitectura de filtros por estrategia
- Diseño Etapa 5 (etapa critica): Revision detallada de requisitos y decision de subdividir en etapas 5A y 5B.
- Diseño y ejecucion de etapa 5A: Registro de timeline, indicadores, warmup de indicadores y construccion de barras (velas).
- Prediseño etapa 5B con alineación de la documentacion y estado actual del proyecto luego de la etapa 5B.
#### Tarde - Noche
- Finalizacion diseño etapa 5B: 4 Fases 8 tareas.
- Finalizacion Fase 1 pipeline completo con SPY historico LEAN .zip: Tareas 1 a 4.
- Archivo de salida pasa validacion manual con trading view de valores de medias en tres marcos diferentes D, W, M.
- Uso de Stooq para validacion de medias recientes con tres acciones.
- IMPORTANTE: Se encontro limitacion de usar Stooq automaticamente, se deja solo para esa validacion de medias (se debe usar alpaca u otro sistema de datos)
- Se finaliza la etapa 5, generando un archivo de validacion manual.
- Se diseña el spec detallado de la etapa 6 con una feature central que calcule la posicion de un precio versus la media movil en un marco especifico.


### Comentarios
- Se rediseña antes de la etapa critica para asegurar alineacion.
- Se define un lineamiento para el uso de Fable, de manera optima en la etapa critica.
- Día intensivo (4 sesiones con 100% de usage en ventana de 5 horas), en pro de aprovechar antes del reset semanal.

### Próximo paso
- Implementacion etapa 6

---

## 2026-06-13

Horas: 3h

### Trabajo realizado
- Implementacion T1 y T2 de Etapa 6
- Se evidencia posible mejora, para flexibilidad y eficiencia de cara a daytrading.
- Se redisena la aplicacion de reglas
- Nueva sub etapa 6B, refinada y validada para no dejar codigo muerto.

### Comentarios
- TODO definicion de archivo de estrategias.

### Próximo paso
- Implementacion de etapa 6B

---

---
# Development Log template
---

## YYYY-MM-DD

Horas: Xh

### Trabajo realizado
- 

### Comentarios
- 

### Próximo paso
- 

---
# Cápsula: factory vs composición

**Tipo:** material de estudio (cápsula breve). Para entender un patrón con ejemplos reales del proyecto.
**Relacionado:** [buckets-y-simetria-largo-corto.md](buckets-y-simetria-largo-corto.md),
[ADR-005](../../.claude/decisions/ADR-005-snapshot-unico-y-reglas-como-filtros.md),
`etapa-06b.md` (D6B.5 `SMAPositionRule`, D6B.6 `NotExtended`).

---

## La idea en una frase

- **Composición** = construir comportamiento **combinando/configurando** objetos, en vez de heredar (subclasear).
- **Factory** (constructor con nombre) = una función que **arma y devuelve** un objeto ya configurado, encapsulando el *cómo se construye*.

No son opuestos. De hecho, en este proyecto **usamos un factory para expresar composición**.

---

## Composición vs herencia (el eje de verdad)

Tenemos UNA clase genérica de regla, `SMAPositionRule`. La regla "no extendido" **no** es una
subclase nueva: es esa misma clase **configurada** de cierta forma.

```python
# COMPOSICIÓN vía factory: NotExtended ES un SMAPositionRule configurado, no una subclase.
def NotExtended(period, tf, side, required=True):
    return SMAPositionRule(
        period, [tf],
        buckets_allowed=set(BUCKETS) - {"extended_above"},  # ← el concepto, encapsulado
        side, required, label="NotExtended",
    )
```

La alternativa con **herencia** sería `class NotExtended(SMAPositionRule): ...`: más rígida, acoplada
a los detalles de la base, y multiplicaría clases (`NotExtended`, `AboveSMA`, `BelowSMA`…). La
composición mantiene **una sola clase** y muchas configuraciones con nombre. Por eso el proyecto
prefiere composición (ADR-005): reglas = *composición declarativa*, no jerarquías de clases.

---

## ¿Cuándo un factory "se gana" su nombre?

Regla práctica:

- ✅ **Encapsula conocimiento** que el llamador tendría que reproducir → vale.
  `NotExtended` calcula *qué* buckets son "no extendido" (`BUCKETS − {extended_above}`); el llamador
  no repite esa aritmética ni puede equivocarse.
- ❌ **Solo renombra o precarga** un parámetro sin añadir significado → es un **alias** vacío; mejor
  llamar al constructor directo.
  Por eso **NO** conservamos `AboveSMA` como factory: solo precargaba `side="above"` —
  `SMAPositionRule(..., side="above")` ya lo dice, y el alias escondía justo el dato útil (la dirección).

> La línea: **¿el nombre aporta semántica, o solo esconde un argumento?** Si aporta → factory con nombre.
> Si solo esconde → alias innecesario.

**Cuidado con la proliferación:** crea un constructor con nombre solo si el concepto (a) se reusa y
(b) su construcción no es obvia. Si no, vuelves a un zoo de nombres (`NearSMA`, `FarBelow`…).

---

## Glosario (términos poco comunes)

- **Composición** — diseñar combinando objetos/funciones configurables en vez de heredar. *Favorece
  composición sobre herencia* es un principio clásico de diseño OO.
- **Herencia (inheritance)** — extender una clase base con subclases (`class Hijo(Base)`). Potente pero
  acopla el hijo a los detalles del padre; fácil de sobreusar.
- **Factory / constructor con nombre** — función que crea y devuelve un objeto ya configurado.
  Encapsula el "cómo se arma". Ej.: `NotExtended(...)`.
- **Alias** — un segundo nombre para lo mismo, sin comportamiento nuevo. Si un "factory" es solo un
  alias, normalmente sobra. Ej. rechazado: `AboveSMA` como `SMAPositionRule(side="above")`.
- **Guard** — una regla/condición cuyo propósito es **bloquear** un caso no deseado, no seleccionar uno
  bueno. Ej.: `NotExtended` actúa de guard ("no persigas algo ya disparado por encima de la media").
- **Fail-fast** — validar y **reventar en construcción** (no en caliente) ante una entrada inválida.
  Ej.: `SMAPositionRule` valida `buckets_allowed ⊆ BUCKETS` al crearse, no durante el scan.
- **Hot path** — el código que corre muchísimas veces (por símbolo × timeframe × scan). Se evita
  trabajo y validaciones ahí. Ej.: `_bucketize` es hot path; la validación de thresholds vive fuera.
- **Boilerplate** — código repetitivo y mecánico sin valor conceptual. Un buen factory lo elimina
  (centraliza la aritmética de buckets en un solo sitio).
- **Syntactic sugar ("azúcar")** — sintaxis más cómoda que no añade capacidad, solo legibilidad. Un
  alias es azúcar; un factory que encapsula un concepto es **más** que azúcar.
- **DRY (Don't Repeat Yourself)** — no duplicar conocimiento. Ojo: DRY es sobre *conceptos*, no sobre
  *parámetros*; precargar un argumento (alias) no es la repetición que DRY busca evitar.
- **Preset** — una configuración con nombre lista para usar. Otra forma de leer `NotExtended`: un preset
  de `SMAPositionRule`.

---

## En una línea para recordar

> Usa **composición** (una clase, muchas configuraciones) y dale **nombre con un factory** solo cuando
> ese nombre **encapsula un concepto**; si el nombre solo esconde un parámetro, es un alias y sobra.

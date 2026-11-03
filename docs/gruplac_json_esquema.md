# Esquema del JSON extraído del GrupLAC

Este documento describe el JSON que produce el paquete **gruplac-json** (comando `gruplac-json` o función `gruplac_json.extract()`) a partir de la página pública del GrupLAC de un grupo de investigación:

```
https://scienti.minciencias.gov.co/gruplac/jsp/visualiza/visualizagr.jsp?nro=NRO
```

Los registros siguen el esquema de [cvlac-json](https://github.com/restrepo/cvlac-json/blob/main/docs/cvlac_json_esquema.md) siempre que el producto es el mismo: `works` tiene la forma de las obras de ImpactU, y `projects`, `events` y `other_products` las de cvlac-json. Este documento explica sobre todo lo que cambia. El esquema se construyó con las 6.936 páginas de la búsqueda de grupos de Minciencias (descargadas del 31 de octubre al 1 de noviembre de 2026), con nueve grupos que juntos tienen ítems en todas las secciones.

## 1. Cómo se genera

```bash
gruplac-json COL|NRO [-o salida.json] [--html pagina.html[.gz]] [--save-html pagina.html]
             [--scienti auto|off] [--institution udea] [--model-year 2024] [--apikey CLAVE] [--ror auto|off]
```

| Fuente | Qué aporta | Opción |
| --- | --- | --- |
| Página pública del GrupLAC | **Todos los registros** | Siempre |
| Tabla de grupos de Minciencias (en el paquete) | Código COL ↔ número de GrupLAC | Siempre |
| Scienti (apis.colav.co, con clave), consultado por el código COL del grupo | Ids Scienti de los ítems que coinciden, y autores de los ítems que no los listan | `--scienti auto` (por defecto) |
| ROR (api.ror.org) | ROR de las instituciones del grupo y de las tesis | `--ror auto` (por defecto) |

## 2. Convenciones generales

Las de cvlac-json (§2 de su esquema): los mismos campos en todos los registros de una colección (`[]` o `null` donde no hay dato), los campos vacíos en toda la colección se eliminan, los textos se conservan como en la página, y `provenance` / `source` siguen la convención de ImpactU, aquí con `gruplac` en lugar de `cvlac`. Excepción: los ítems de `other_products` siempre tienen `authors`, aunque sea `[]`.

Las secciones vacías (el GrupLAC muestra siempre las 87, la mayoría sin ítems) no aparecen.

## 3. Nivel superior

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `nro` | string | Número de GrupLAC (14 dígitos). |
| `col` | string o null | Código del grupo en Minciencias (`COL0008423`); `null` si la tabla no conoce el número. |
| `url`, `retrieved` | string | Página leída y fecha de la extracción (UTC). |
| `name` | string | Nombre del grupo. |
| `profile` | object | "Datos básicos" (§4). |
| `institutions` | array | `{name, status, ror}`: instituciones del grupo; `status` es "Avalado" u otro; `ror` es `{id, name, match}` o `null`. Son también afiliación de los integrantes (§9). |
| `strategic_plan` | object | "Plan Estratégico": `Plan de trabajo`, `Estado del arte`, `Objetivos`, `Retos`, `Visión`…, como en la página. |
| `research_lines` | array | `{name}`: líneas de investigación declaradas. |
| `members` | array | "Integrantes del grupo" (§5). |
| `works` | array | Producción bibliográfica, en el esquema de obras de ImpactU (§6). |
| `projects` | array | Proyectos (§7). |
| `events` | array | Eventos científicos (§7). |
| `other_products` | object | Las demás secciones, por título (§8). |
| `section_categories` | object | Sección → categoría de la página: "PRODUCCIÓN BIBLIOGRÁFICA", "PRODUCCIÓN TÉCNICA Y TECNOLÓGICA", "APROPIACIÓN SOCIAL Y DIVULGACIÓN PÚBLICA DE LA CIENCIA", "Producción en arte, arquitectura y diseño", "ACTIVIDADES DE FORMACIÓN", "ACTIVIDADES COMO EVALUADOR", "PRODUCCIÓN DE FORMACIÓN Y EXTENSIÓN"… |
| `counts` | object | Conteos (§10). |
| `affiliations_from_members` | object | Resumen de la asignación de integrantes y afiliaciones (§9). |
| `scienti` | object | Resumen del cruce con Scienti; solo con clave (§11). |

## 4. `profile`

| Campo | Tipo | Ejemplo |
| --- | --- | --- |
| `raw` | object | Las filas de "Datos básicos", con las etiquetas como en la página. |
| `formed` | object | `{"year": 1979, "month": 12}` ("Año y mes de formación"). |
| `department`, `city` | string | "ANTIOQUIA", "MEDELLÍN". |
| `leader` | string | Nombre del líder. |
| `certified` | object o null | `{"value": "Si", "date": "2016-01-21"}`. |
| `website`, `email` | string o null | Como en la página. |
| `classification` | object o null | `{"category": "A1", "text": "con vigencia hasta …"}`. |
| `knowledge_area` | array de string | `["Ciencias Naturales", "Ciencias Físicas", "Física de Partículas y Campos"]`. |
| `national_program`, `national_program_secondary` | string o null | Programas nacionales de CTI. |

## 5. `members[]`

| Campo | Tipo | Descripción |
| --- | --- | --- |
| `full_name` | string | Nombre como en la tabla. |
| `cod_rh` | string | COD_RH (del enlace a su CvLAC). |
| `url` | string | Enlace al CvLAC. |
| `linkage` | string | "Vinculación": Integrante, Estudiante… |
| `hours` | integer | Horas de dedicación. |
| `period` | string | Texto original, "2012/1 - Actual". |
| `start`, `end` | object | `{year, month}`; `end` es `null` si el periodo sigue abierto. |
| `open_end` | boolean | `true` si termina en "Actual". |

## 6. `works[]`

Las secciones Artículos publicados, Otros artículos publicados, Libros publicados, Libros de formación, Libros de divulgación y/o Compilación de divulgación, Manuales y Guías Especializadas, Otros Libros publicados, Capítulos de libro publicados, Documentos de trabajo, Otra publicación divulgativa, Traducciones, Traducciones Filológicas y Edición de Fuentes, Notas científicas y Publicaciones editoriales no especializadas (esta última, como en cvlac-json).

Mismos campos que en cvlac-json (§10 de su esquema), con estas diferencias:

- `id` es `gruplac:NRO:n` (n = orden en la página).
- `types[]`: nivel 0 "Producción bibliográfica", nivel 1 la clase de la sección (Artículo, Libro, Capítulo de libro…), nivel 2 el tipo en negrilla del ítem ("Publicado en revista especializada", "Libro resultado de investigación"…), con `source: "gruplac"`.
- `authors[]` son los de "Autores:" (el GrupLAC lista solo a los integrantes que registraron el producto y a sus coautores en el CvLAC). Los integrantes llevan su COD_RH en `id` y en `external_ids` y, si el año está en su periodo, la afiliación al grupo (§9).
- `source.publisher.country` es el país de la revista o editorial, como en cvlac-json.
- `gruplac` reemplaza a `cvlac`: `section`, `endorsed` (marca de verificación), `country`, `fields` (pares etiqueta → valor rotulados), `text` (texto completo) y `scienti` (§11).

## 7. `projects[]` y `events[]`

| `projects[]` | Descripción |
| --- | --- |
| `type`, `title` | "Investigación y desarrollo", "Extensión y responsabilidad social CTI"…, y el título. |
| `endorsed` | Marca de verificación. |
| `start`, `end` | `{year, month}`; `end` es `null` si el proyecto sigue ("Actual"). |
| `ongoing` | `true` si termina en "Actual". |
| `text` | Texto completo. |
| `scienti`, `external_ids` | Coincidencia con Scienti (§11). |

| `events[]` | Descripción |
| --- | --- |
| `name`, `type` | Nombre y tipo (Congreso, Encuentro, Seminario, Simposio, Taller, Otro). |
| `scope` | "Ámbito". |
| `start`, `end` | `AAAA-MM-DD`. |
| `place` | Ciudad. |
| `participation` | "Tipos de participación", p. ej. `["Ponente"]`. |
| `institutions[]` | `{name, link}` de "Instituciones asociadas" (`link`: Patrocinadora, Organizadora…). |
| `text`, `endorsed`, `scienti` | |

## 8. `other_products`

Un objeto cuyas claves son los títulos de las demás secciones del GrupLAC, con los ítems en el orden de la página. Las cuatro secciones de apropiación social del conocimiento (fortalecimiento o solución de asuntos de interés social; trabajo conjunto entre un Centro de Ciencia y un grupo; generación de insumos de política pública y normatividad; fortalecimiento de cadenas productivas) van juntas en "Apropiación social del conocimiento", como en cvlac-json, con `type` "Apropiación social del conocimiento - <título de la sección>". Las secciones de arte, arquitectura y diseño (Obras o productos, Industrias creativas y culturales, Eventos Artísticos, Talleres de Creación) son filas de encabezado dentro de una sola tabla de la página; aquí son secciones normales.

Cada ítem tiene los campos de cvlac-json (§13 de su esquema) que se puedan leer de su texto, y algunos propios del GrupLAC:

| Campo | Tipo | De dónde sale |
| --- | --- | --- |
| `type` | string | El tipo en negrilla ("Consultoría científica", "Computacional", "Marcas", "Spin-off"…). En Redes de Conocimiento Especializado es la clase de red ("Real", "Virtual"). |
| `endorsed` | boolean | Marca de verificación. |
| `title` | string | El texto tras el tipo, o el valor de "Nombre del producto", "Nombre del proceso", "Nombre del curso", "Programa académico", "Nombre del evento", "Nombre del taller", "Nombre de la empresa creativa o cultural". |
| `authors[]` | array | **Siempre presente.** Las personas de "Autores:", como en las obras (§6), con `{full_name, id, external_ids, affiliations}`. En tesis, `type` `advisor`/`co-advisor` (Tutor(es)/Cotutor(es), según "Tipo de orientación") y `student` (Nombre del estudiante); en jurados, `jury` y `student` (Nombre del orientado). Muchas secciones no listan autores (consultorías, conceptos e informes técnicos, contenido digital, apropiación social, redes, estrategias…): ahí la lista queda vacía, salvo que Scienti diga qué integrantes registraron el producto (§11). |
| `authors_inferred` | boolean | `true` si los autores vienen de los registros Scienti. |
| `country`, `city`, `place` | string | "Colombia, 2020" al inicio de la línea, "Ciudad", "en MEDELLÍN", "Lugar", "Lugar de realización". |
| `institution` | string | "Institución", "Institución solicitante", "Institución que emite el registro", "Institución en la cual prestó el servicio". En tesis es `{name, id, ror_name, ror_match}`, como en cvlac-json. |
| `funder` | string | "Institución financiadora". |
| `certifier` | string | "Institución certificadora". |
| `participating_institutions` | string | "Instituciones participantes", "Entidades vinculadas". |
| `date` | string | `AAAA-MM-DD`, `AAAA-MM` o `AAAA`: fecha de creación, presentación (también "Año: …, Mes: …"), envío, obtención, publicación, registro ante cámara, del acto administrativo, de solicitud, o el año de la línea. |
| `start`, `end` | string | Fechas de inicio y fin ("Fecha de inicio", "Año de inicio"/"Mes de inicio", "desde … hasta …"). |
| `year` | integer o null | Año de `date`, `start` o `end`, o del texto. Es el año que se compara con el periodo del integrante. |
| `duration` | object | `{value, unit}` cuando la etiqueta trae la unidad ("Duración (semanas): 3"). |
| `pages` | integer | Tesis: "Número de páginas". |
| `project` | string | "Nombre del proyecto", "Proyecto de investigación". |
| `program`, `role`, `assessment` | string | "Programa académico", "Tipo de orientación", "Valoración". |
| `audience`, `differential_focus` | array de string | "público objetivo" y "Enfoque diferencial", separados por ";". |
| `scope`, `availability`, `language`, `medium`, `genre`, `circulation`, `format`, `license`, `topic`, `purpose`, `holder`, `database`, `description`, `commercial_name`, `participants_count`, `discipline`, `distinction`, `selection`, `cycle`, `edition`, `series`, `broadcaster`, `fairs`, `original_authors`, `original_language`, `translation_language` | string | Ámbito, Disponibilidad, Idioma, Medio de divulgación o de circulación, Género literario, Tipo de circulación, Tipo de formato, Licencia, Tema, Finalidad u Objeto, Titular, Base de datos, Descripción, Nombre comercial, Nro de participantes, Disciplina o ámbito de origen, Distinción obtenida, Mecanismo de selección, Tipo de ciclo, Edición, Serie, Emisora, Nombre de las ferias, y los datos de las traducciones. |
| `identifiers[]` | array | `{source, id}`: `contract` (Número del contrato), `registration` (Número de registro), `nit`, `concept number`, `administrative act`, `snies`, `doi`, `isbn`. |
| `links[]` | array | `{url, label}`: enlaces `<a>` y URL escritas en el texto ("medio de verificación", "Sitio web"…). |
| `text` | string | Texto completo del ítem. |
| `fields` | object | Todos los pares etiqueta → valor, como en la página (los vacíos se quitan). |
| `scienti` | object | Coincidencia con Scienti (§11). |

## 9. Afiliaciones y `affiliations_from_members`

Un autor es **integrante** cuando su nombre en "Autores:" coincide con el de un solo integrante de la tabla:

- `exact`: las mismas palabras, sin tildes ni mayúsculas ("OSCAR ALBERTO ZAPATA NORENA" = "Oscar Alberto Zapata Norena").
- `words`: las mismas palabras en otro orden, o un nombre contenido en el otro con al menos tres palabras ("ROBERTO TORRES CORREDOR" ⊂ "Roberto Armando Torres Corredor").
- `spelling`: las mismas palabras salvo una, que difiere en una letra o en dos letras vecinas intercambiadas ("GIRLADO" / "GIRALDO").
- `scienti`: el autor se agregó desde un registro Scienti de ese integrante (§11).

El integrante recibe su COD_RH en `id` y en `external_ids` (`{provenance: "gruplac", source: "scienti", id}`) y, **si el año del producto está en su periodo** "Inicio - Fin Vinculación" (hasta el año actual si dice "Actual"), el grupo como afiliación:

```json
{
  "id": "COL0008423",
  "name": "Grupo de Fenomenologia de Interacciones Fundamentales",
  "types": [{"source": "minciencias", "type": "group"}],
  "external_ids": [{"provenance": "gruplac", "source": "minciencias", "id": "COL0008423"},
                   {"provenance": "gruplac", "source": "gruplac", "id": "00000000001676"}],
  "years": [2012, 2013, "…", 2026],
  "gruplac": {"provenance": "gruplac members", "member": "Oscar Alberto Zapata Norena", "linkage": "Integrante",
              "hours": 20, "period": "2012/1 - Actual", "name_match": "exact"}
}
```

y además **cada institución del grupo** (`institutions`), con su ROR, en la forma de las afiliaciones de cvlac-json por experiencia:

```json
{
  "id": "03bp5hc83",
  "name": "Universidad de Antioquia",
  "types": [{"source": "ror", "type": "education"}],
  "external_ids": [{"provenance": "ror", "source": "ror", "id": "https://ror.org/03bp5hc83"}, "…"],
  "addresses": [{"city": "Medellín", "country": "Colombia", "country_code": "CO"}],
  "years": [2012, 2013, "…", 2026],
  "gruplac": {"provenance": "gruplac institutions", "names": ["UNIVERSIDAD DE ANTIOQUIA"], "status": "Avalado",
              "member": "Oscar Alberto Zapata Norena", "period": "2012/1 - Actual", "ror_match": "name"}
}
```

Sin ROR (`--ror off`, o la institución no está en ROR), `id` es `null` y `name` es el de la página. Primero va el grupo, luego sus instituciones en el orden de la página. Es la misma idea que las afiliaciones de cvlac-json ("cvlac experience"): significa "era integrante del grupo ese año", no que la página declare dónde se hizo el producto. Los autores que no son integrantes tienen `id: null` y `affiliations: []`. En las tesis, el tutor y los estudiantes también reciben la institución de la tesis con su ROR (`gruplac.provenance: "gruplac thesis"`).

`affiliations_from_members`: `ror_lookup_errors`, `members`, `members_with_cod_rh`, `authors`, `authors_matched`, `name_match` (por regla), `works_with_affiliation`, `products_with_affiliation`, `rule` y `ror_lookup_errors`.

## 10. `counts`

`members`, `works`, `projects`, `events`, `works:<sección>`, `<título de sección>` (ítems de cada lista de `other_products`), `endorsed_works`, `works_with_affiliation` y `products_with_affiliation` (con al menos un autor con la afiliación al grupo), y `product_hash_repeated` (§13).

## 11. Coincidencias con Scienti

Se piden a apis.colav.co los registros del grupo (`/scienti/product`, `/project`, `/event` y `/network` con `group_id=COL…`), en el primer volcado (udea, univalle, uec, unaula) que los tenga. Cada registro es la entrada del CvLAC de un integrante, así que un producto del grupo puede coincidir con varios: uno por cada integrante que lo registró.

- Las reglas son las de cvlac-json: mismo DOI; mismo título (≥ 25 caracteres y 4 palabras) con año, ISSN, ISBN o revista; un título truncado con el mismo año; y, en proyectos, eventos y redes, mismo nombre y año.
- El mejor registro va a `scienti` (`id`, `by`, `evidence`, `shared`, `scienti_title`, `scienti_year`); los demás registros del mismo producto (mismo DOI, o mismo título y año) van a `scienti.also`. En las obras, todos se agregan a `external_ids` con `source: "scienti"`, y en los proyectos a `external_ids`.
- Los ítems sin autores en la página reciben como autores a los integrantes cuyos COD_RH tienen esos registros (`authors_inferred: true`).

Objeto `scienti` del nivel superior: `institution`, `model_year`, `source`, `group_id`, `products` (registros de productos del grupo), `products_matched`, `matched` (`works`, `other_products`, `projects`, `events`, `networks`), `records`, `items_with_authors_from_scienti`, `rules`, `not_on_page` (registros de productos sin ítem en la página) y `not_on_page_note`.

## 12. Valores observados (7.170 páginas guardadas, 2026-11-02)

Las 7.170 páginas descargadas el 31 de octubre y el 1 de noviembre de 2026 (los 6.936 grupos de la búsqueda de Minciencias y 234 más que conoce ImpactU) se analizaron sin errores. Algunas cifras, sumadas sobre todos los grupos:

| Sección | Ítems | Con título | Con año | Autores que son integrantes | Ítems con afiliación al grupo |
| --- | --- | --- | --- | --- | --- |
| Artículos publicados | 588.181 | 100 % | 100 % | 59 % | 91 % |
| Capítulos de libro publicados | 169.019 | 100 % | 100 % | 72 % | 93 % |
| Libros publicados | 61.299 | 100 % | 100 % | 65 % | 93 % |
| Trabajos dirigidos/turorías | 869.980 | 100 % | 100 % | 48 % | 91 % |
| Jurado/Comisiones evaluadoras de trabajo de grado | 390.944 | 100 % | 100 % | 49 % | 94 % |
| Eventos Científicos | 650.438 | 100 % | 100 % | — | — |
| Proyectos | 334.728 | 100 % | 99 % | — | — |
| Consultorías científico-tecnológicas | 58.218 | 100 % | 100 % | sin autores en la página | |
| Apropiación social del conocimiento (4 secciones) | 32.186 | 100 % | 100 % | sin autores en la página | |
| Obras o productos | 23.026 | 94 % | 100 % | sin autores en la página | |
| Integrantes del grupo | 301.377 | | | | |

"Autores que son integrantes" cuenta personas de "Autores:" (en tesis y jurados también estudiantes, que pocas veces son integrantes). "Con afiliación al grupo" cuenta ítems con al menos un integrante cuyo periodo contiene el año del ítem. Las secciones Guías de práctica clínica y Proyectos de ley ponen una fila de encabezado vacía antes de sus ítems (868 ítems en total); se leen como parte de su sección.

## 13. Identificador de producto: `product_hash`

Cada integrante autor de una obra (`works`) o de un producto de `other_products` lleva, en su entrada de `authors[]`, un `product_hash`: un identificador de 40 caracteres hexadecimales que sale solo del contenido del registro y del COD_RH del integrante. Es el mismo que [cvlac-json](https://github.com/restrepo/cvlac-json) pone en la entrada del dueño de cada producto de su CvLAC (§21 de su esquema), así que une un producto del GrupLAC con el mismo producto en el CV de cada integrante que lo firmó.

**Cómo se calcula.** Es el SHA-1 de la clave

```
<título>|<COD_RH>|<tipo>|<año>
```

| Parte | Regla | Ejemplo |
| --- | --- | --- |
| título | En minúsculas, sin tildes ni otras marcas (Unicode NFKD y luego solo ASCII: "Física" → "fisica", la letra matemática "𝐽" → "j"), y solo con las letras `a`–`z` y los dígitos `0`–`9`: los espacios y la puntuación no cuentan. Un título vacío da `""`. | "Bleomicina: Una revisión" → `bleomicinaunarevision` |
| COD_RH | El del integrante (su `id` en `authors[]`), con 10 dígitos. | `0000707619` |
| tipo | `work` (`works`) u `other` (cualquier sección de `other_products`, también tesis y jurados). `patent` sería una sección Patentes, que el GrupLAC no tiene, y `project` no se usa: los proyectos del GrupLAC no listan autores. Los eventos no tienen `product_hash`. | `work` |
| año | Obras: `year_published`. Demás productos: `year`, o el año de `date`. Vacío si no hay. | `2024` |

Ejemplo: "Singlet Dirac dark matter streamlined", del integrante `0000707619`, publicado en 2024, tiene la clave `singletdiracdarkmatterstreamlined|0000707619|work|2024` y el `product_hash` `efc8d0bb2fa5…` (SHA-1 de la clave en ASCII).

**Dónde va.** En la entrada de cada integrante (el autor con COD_RH en `id`: por nombre, o agregado desde Scienti), calculado con su propio COD_RH: un artículo de dos integrantes tiene dos `product_hash`, cada uno igual al del CV de ese integrante. Los autores que no son integrantes tienen `product_hash: null`.

**Único por integrante.** Si varios registros de un integrante dan la misma clave (el mismo producto escrito dos veces, un curso dictado dos veces el mismo año), el primero, en el orden de la página (obras y luego `other_products`), conserva la clave y el n-ésimo la lleva con `|n` al final (`…|work|2024|2`). `counts.product_hash_repeated` cuenta esos registros. El primero es el que el CvLAC reproduce; uno repetido coincide solo si el CvLAC lista las mismas repeticiones en el mismo orden.

**Qué no lo reproduce.** El hash cambia si cambia el título (más allá de mayúsculas, tildes, espacios y puntuación), el año o el tipo. En nueve grupos de muestra, comparados con los CvLAC de sus integrantes de la UdeA (2026-11-02), el hash del integrante está en su CV en 971 de 1.142 parejas de obra e integrante (85 %) y en 122 de 251 de los demás productos (49 %). Las diferencias son títulos editados en una de las dos páginas, años distintos (frecuentes en los demás productos) y productos que no están en el CV. Cuando hay clave de apis.colav.co, el id de Scienti (`COD_RH-COD_PRODUCTO`, §11) identifica el registro de origen y no depende del título.

**En Python.** `gruplac_json.product_hash(título, cod_rh, tipo, año=None, n=1)` da el hash; `gruplac_json.product_hash.hash_key(...)`, la clave; `gruplac_json.product_hash.product_hashes(registros, cod_rh)`, los hashes únicos de una lista de `(título, tipo, año)` en orden. El módulo `product_hash.py` solo usa la biblioteca estándar y es una copia sin cambios del de cvlac-json; los casos de `tests/product_hash_vectors.json` fijan su resultado en los dos paquetes.

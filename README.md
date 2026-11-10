# gruplac-json

[![CI](https://github.com/restrepo/gruplac-json/actions/workflows/ci.yml/badge.svg)](https://github.com/restrepo/gruplac-json/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/gruplac-json.svg)](https://pypi.org/project/gruplac-json/)
[![Python](https://img.shields.io/pypi/pyversions/gruplac-json.svg)](https://pypi.org/project/gruplac-json/)

Convierte la página pública del **GrupLAC** de un grupo de investigación (Minciencias, Colombia) en un único documento JSON: datos básicos, instituciones (con su ROR), plan estratégico, líneas de investigación, integrantes con su COD_RH y su periodo de vinculación, producción bibliográfica en el esquema de obras de [ImpactU](https://impactu.colav.co), proyectos, eventos y todos los demás productos (`other_products`), con autores, título, lugar, fechas, identificadores, enlaces y los demás datos rotulados de cada ítem.

Es la pareja de [cvlac-json](https://github.com/restrepo/cvlac-json): los productos que existen en ambos tienen la misma forma, y usa sus herramientas de ROR y de Scienti.

- **Afiliaciones de los integrantes:** cada autor de un producto que aparece en "Integrantes del grupo" recibe su COD_RH y, si el año del producto está en su periodo "Inicio - Fin Vinculación", el grupo como afiliación, con la procedencia (`gruplac.provenance: "gruplac members"`), y las instituciones declaradas del grupo con su ROR (`"gruplac institutions"`), como hace cvlac-json con la experiencia.
- Con una clave de [apis.colav.co](https://apis.colav.co), agrega los **identificadores Scienti** (`COD_RH-COD_PRODUCTO`, `-COD_PROYECTO`, `-COD_EVENTO`, `-COD_RED`) de los registros del grupo que coinciden. Los productos sin autores en la página (consultorías, conceptos técnicos, procesos de apropiación social…) reciben como autores a los integrantes que registraron ese producto en Scienti.

## Instalación

```bash
pip install gruplac-json
```

## Uso en la terminal

```bash
gruplac-json COL0008423                        # escribe gruplac_COL0008423.json
gruplac-json 1676                              # el número de GrupLAC, con o sin ceros a la izquierda
gruplac-json COL0008423 --save-html g.html     # guarda también la página descargada
gruplac-json COL0008423 --html g.html.gz       # analiza una página guardada (.html o .html.gz), sin descargar
gruplac-json COL0008423 -o -                   # JSON por la salida estándar
gruplac-json COL0008423 --scienti off --ror off
gruplac-json COL0008423 --format jsonld        # JSON-LD: escribe gruplac_COL0008423.jsonld
```

| Opción | Efecto |
| --- | --- |
| `--scienti auto` (por defecto) | Si hay clave de apis.colav.co, agrega los ids Scienti de los registros del grupo que coinciden. |
| `--scienti off` | No consulta Scienti. |
| `--institution`, `--model-year` | Volcado de Scienti (`udea`, `univalle`, `uec`, `unaula`) y año del modelo. Por defecto se prueban en ese orden. |
| `--apikey CLAVE` | Clave de apis.colav.co para esta ejecución. |
| `--ror auto` / `off` | Consulta o no el registro ROR (instituciones del grupo y de las tesis). |
| `--format json` / `jsonld` | Salida JSON (por defecto) o JSON-LD (ver más abajo). Sin `-o`, el archivo es `gruplac_COL.json` o `gruplac_COL.jsonld`. |
| `--base URL` | Con `--format jsonld`, prefijo del IRI del grupo, al que se agrega el código COL. Por defecto, el IRI es la URL de la página del GrupLAC. |

El código COL se traduce al número de GrupLAC con la tabla de los 6.936 grupos de la búsqueda de grupos de Minciencias (31 de octubre de 2026), incluida en el paquete. Un grupo que no esté en la tabla se puede pedir por su número de GrupLAC; sin código COL no se consulta Scienti.

La clave de apis.colav.co se toma, en este orden, de `--apikey`, de la variable de entorno `COLAV_APIKEY` o del archivo `~/.config/colav/apikey`. Nunca se imprime.

## Uso como biblioteca

```python
from gruplac_json import extract

data = extract("COL0008423", scienti="off")  # descarga y analiza la página
print(data["name"], len(data["members"]), len(data["works"]))

from gruplac_json.parser import decode

html = decode(open("g.html", "rb").read())
data = extract("COL0008423", html=html, ror=False)
```

## JSON-LD

`--format jsonld` (o `to_jsonld(data)` en Python) entrega el mismo documento con `@context`, `@id` y `@type`, listo para convertirlo a RDF, como el de cvlac-json:

```bash
gruplac-json COL0008423 --format jsonld                                    # @id = URL de la página del GrupLAC
gruplac-json COL0008423 --format jsonld --base https://ejemplo.org/grupos/ # @id = https://ejemplo.org/grupos/COL0008423
```

```python
from gruplac_json import extract, to_jsonld

doc = to_jsonld(extract("COL0008423", scienti="off"), base="https://ejemplo.org/grupos/")
doc["works"][0]["@id"]  # 'https://ejemplo.org/grupos/COL0008423#/works/0'
```

El contexto, los tipos y los `@id` están en el [esquema](docs/gruplac_json_esquema.md#14-json-ld) (§14).

## Identificador de producto (`product_hash`)

Cada integrante autor de una obra o de un producto de `other_products` lleva, en su entrada de `authors[]`, un `product_hash`: el SHA-1 de `título|COD_RH|tipo|año`, con el título en minúsculas, sin tildes y solo con letras y dígitos, el COD_RH del integrante y el tipo `work` (obras) u `other` (demás productos). Un ítem sin título usa su texto en la página (`text`) como título. Es el mismo valor que [cvlac-json](https://github.com/restrepo/cvlac-json) pone en la entrada del dueño de cada producto de su CvLAC, así que une un producto del GrupLAC con el del CV de cada integrante que lo firmó, sin depender de mayúsculas, tildes, espacios ni puntuación. Un artículo de dos integrantes tiene dos `product_hash`, uno por integrante; los autores que no son integrantes tienen `null`. Es único por integrante: si dos de sus registros dan la misma clave, el segundo lleva `|2` al final, el tercero `|3`…

```python
from gruplac_json import product_hash
from gruplac_json.product_hash import hash_key

hash_key("Singlet Dirac dark matter streamlined", "0000707619", "work", 2024)
# 'singletdiracdarkmatterstreamlined|0000707619|work|2024'
product_hash("Singlet Dirac dark matter streamlined", "0000707619", "work", 2024)
# 'efc8d0bb2fa5…' (40 caracteres)
```

Cambia si cambia el título (más allá de esas diferencias), el año o el tipo. Reglas, ejemplos y cuánto coincide con los CvLAC: [§13 del esquema](docs/gruplac_json_esquema.md#13-identificador-de-producto-product_hash).

## Esquema del JSON

El esquema completo, campo por campo, está en [docs/gruplac_json_esquema.md](docs/gruplac_json_esquema.md).

## Desarrollo

```bash
git clone https://github.com/restrepo/gruplac-json.git
cd gruplac-json
python -m pip install -e ".[dev]"
python -m pytest
ruff check . && ruff format --check .
```

Las pruebas no usan la red: corren sobre una página sintética (`tests/fixtures/gruplac_sintetico.html`) con personas y productos ficticios y la misma estructura HTML del GrupLAC.

Cómo publicar una versión nueva en PyPI: [PUBLISHING.md](PUBLISHING.md) y [CHANGELOG.md](CHANGELOG.md).

## Avisos

- La página del GrupLAC es pública, pero contiene datos personales (nombres de los integrantes, correo del grupo). Úselos de acuerdo con la normativa de protección de datos que aplique.
- Sea moderado con el servidor de Minciencias: haga una pausa de uno o dos segundos entre grupos cuando procese muchos.
- Las afiliaciones de los productos son **inferidas** del periodo de vinculación (el autor era integrante del grupo ese año); el GrupLAC no las declara. Los coautores que no son integrantes no tienen afiliación.

## Licencia

[MIT](LICENSE)

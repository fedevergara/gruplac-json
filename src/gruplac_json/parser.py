"""Parse a public GrupLAC page (Minciencias, Colombia) into one JSON document.

The records follow the cvlac-json schema wherever the product is the same: bibliographic production goes to
`works` (ImpactU work schema), projects to `projects`, scientific events to `events`, and every other section to
`other_products`, keyed by the section title, with the structured fields read from the item text.
"""

import datetime as dt
import html as H
import json
import re
import urllib.request
from importlib import resources

from cvlac_json.parser import clean, find_doi, harmonize, month_year, norm, year_of

URL = "https://scienti.minciencias.gov.co/gruplac/jsp/visualiza/visualizagr.jsp?nro={}"
CVLAC = "https://scienti.minciencias.gov.co/cvlac/visualizador/generarCurriculoCv.do?cod_rh={}"
ASC = "Apropiación social del conocimiento"  # its four GrupLAC sections are merged into one other_products list
THESES = "Trabajos dirigidos/turorías"
ART = "Producción en arte, arquitectura y diseño"  # a category: its sections are header rows inside its table
# Sections whose items are bibliographic works (mapped to the ImpactU work schema), with the class used as types[1]
BIBLIO = {
    "Artículos publicados": "Artículo",
    "Otros artículos publicados": "Otro artículo publicado",
    "Libros publicados": "Libro",
    "Libros de formación": "Libro de formación",
    "Libros de divulgación y/o Compilación de divulgación": "Libro de divulgación",
    "Manuales y Guías Especializadas": "Manuales y guías especializadas",
    "Otros Libros publicados": "Otro libro publicado",
    "Capítulos de libro publicados": "Capítulo de libro",
    "Documentos de trabajo": "Documento de trabajo",
    "Otra publicación divulgativa": "Otra publicación divulgativa",
    "Traducciones": "Traducción",
    "Traducciones Filológicas y Edición de Fuentes": "Traducción filológica",
    "Notas científicas": "Nota científica",
    "Publicaciones editoriales no especializadas": "Publicación editorial no especializada",
}
# Sections whose <strong> text is the product's name, not its type
TITLE_IN_STRONG = {
    "Redes de Conocimiento Especializado",
    "Estrategias de Comunicación del Conocimiento",
    "Estrategias Pedagógicas para el fomento a la CTI",
    "Espacios de Participación Ciudadana",
    "Participación Ciudadana en Proyectos de CTI",
    "Asesorías al Programa Ondas",
}
# Labels that the page sometimes writes after a single space instead of a comma
INLINE_LABELS = (
    "Programa académico",
    "Disciplina o ámbito de origen",
    "Ámbito",
    "Duracion",
    "Duración",
    "Número de participantes",
    "Tipos de participación",
)
# Labels whose value runs to the end of the line (free text that may hold "x: y")
GREEDY = {"descripcion", "descripcion del registro", "descripcion del evento", "objeto", "autor del documento original"}
EMPTY = {"", "n/a", "na", "no aplica", "ninguno", "null", "0", "-", "none"}

# GrupLAC label (normalized) -> key of the structured item, as in cvlac-json other_products where the meaning is the same
LABEL_KEYS = {
    "institucion": "institution",
    "institucion solicitante": "institution",
    "institucion que emite el registro": "institution",
    "institucion en la cual presto el servicio": "institution",
    "institucion financiadora": "funder",
    "institucion certificadora": "certifier",
    "instituciones participantes": "participating_institutions",
    "entidades vinculadas": "participating_institutions",
    "ciudad": "city",
    "lugar": "place",
    "lugar de realizacion": "place",
    "lugar de publicacion": "place",
    "pais de obtencion": "country",
    "editorial": "publisher",
    "disponibilidad": "availability",
    "nombre comercial": "commercial_name",
    "idioma": "language",
    "idiomas": "language",
    "medio de divulgacion": "medium",
    "medio de circulacion": "medium",
    "nombre del proyecto": "project",
    "proyecto de investigacion": "project",
    "publico objetivo": "audience",
    "enfoque diferencial": "differential_focus",
    "ambito": "scope",
    "finalidad": "purpose",
    "objeto": "purpose",
    "nombre del titular": "holder",
    "titular del registro": "holder",
    "base de datos donde esta incluido el registro": "database",
    "descripcion": "description",
    "descripcion del registro": "description",
    "descripcion del evento": "description",
    "tema": "topic",
    "programa academico": "program",
    "tipo de orientacion": "role",
    "valoracion": "assessment",
    "genero literario": "genre",
    "tipo de circulacion": "circulation",
    "tipo de formato": "format",
    "licencia creative commons u open data commons del contenido": "license",
    "nro de participantes": "participants_count",
    "numero de participantes": "participants_count",
    "tipos de participacion": "participation",
    "disciplina o ambito de origen": "discipline",
    "distincion obtenida": "distinction",
    "mecanismo de seleccion": "selection",
    "tipo de ciclo": "cycle",
    "autor del documento original": "original_authors",
    "idioma del documento original": "original_language",
    "idioma de la traduccion": "translation_language",
    "edicion": "edition",
    "serie": "series",
    "emisora": "broadcaster",
    "nombre de las ferias": "fairs",
}
TITLE_LABELS = (
    "nombre del producto",
    "nombre del curso",
    "nombre del proceso",
    "programa academico",
    "nombre del evento",
    "nombre del taller",
    "nombre de la red",
    "nombre de la empresa creativa o cultural",
    "titulo",
)
DATE_LABELS = (
    "fecha de creacion",
    "fecha de presentacion",
    "fecha de envio",
    "fecha de obtencion",
    "fecha de publicacion",
    "fecha de registro ante camara",
    "fecha de registro ante la camara de comercio",
    "fecha acto administrativo programa",
    "fecha acto administrativo curso",
)
START_LABELS, END_LABELS = ("fecha de inicio",), ("fecha de finalizacion",)
ID_LABELS = {
    "numero del contrato": "contract",
    "numero del registro": "registration",
    "numero de registro": "registration",
    "nit": "nit",
    "nit o codigo de registro": "nit",
    "numero consecutivo del concepto": "concept number",
    "numero acto administrativo programa": "administrative act",
    "numero acto administrativo curso": "administrative act",
}
LIST_KEYS = {"audience", "differential_focus"}
KNOWN = {
    *LABEL_KEYS,
    *TITLE_LABELS,
    *DATE_LABELS,
    *START_LABELS,
    *END_LABELS,
    *ID_LABELS,
    *GREEDY,
    "ano",
    "mes",
    "mes de solicitud",
    "ano de solicitud",
    "ano de inicio",
    "mes de inicio",
    "ano de fin",
    "mes de fin",
    "medio de verificacion",
    "sitio web",
    "sitio web url",
    "url",
    "pagina web",
    "tipo",
    "doi",
    "nro paginas",
    "nombre del estudiante",
    "nombre del orientado",
    "tutor es cotutor es",
    "numero de paginas",
    "nombre del espacio o evento",
    "entidad convocante 1",
    "revista",
    "libro",
}
URL_RE = re.compile(r"(?:https?://|www\.)[^\s,;<>\"']+", re.I)
LABEL_RE = re.compile(r"(?:(?<=^)|(?<=,)|(?<=: )|(?<=  )|(?<=\|))\s*([^\W\d_][^:,|]{0,70}?)\s*:(?=\s|$|[^\s/])")
ISO = re.compile(r"\b((?:19|20)\d\d)-(\d\d)-(\d\d)\b")


# ---------------------------------------------------------------- helpers
def fetch(nro):
    req = urllib.request.Request(URL.format(nro), headers={"User-Agent": "Mozilla/5.0 (gruplac-json)"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return decode(r.read())


def decode(raw):
    """Page bytes -> str, with the charset the page declares (GrupLAC pages are ISO-8859-1)."""
    enc = re.search(rb"charset=([\w-]+)", raw[:3000])
    return raw.decode(enc.group(1).decode() if enc else "latin-1", errors="replace")


def text(s, keep_lines=False):
    """HTML fragment -> clean text (optionally keeping <br>/<li> as line breaks)."""
    if keep_lines:
        s = re.sub(r"<br\s*/?>|</?li[^>]*>|</?ul[^>]*>", "\n", re.sub(r"[\r\n]+", " ", s or ""), flags=re.I)
    s = H.unescape(re.sub(r"<[^>]+>", " ", s or "")).replace("\xa0", " ")
    if keep_lines:
        lines = [re.sub(r"[ \t\r\f\v]+", " ", ln).strip() for ln in s.split("\n")]
        return "\n".join(ln for ln in lines if ln)
    return re.sub(r"\s+", " ", s).strip()


def value(v):
    v = clean(v)
    return None if v is None or v.lower() in EMPTY else v


def iso_date(s):
    """'2023-02-01' / '2023-02-01 00:00:00' / 'Junio-1998' / 'Mayo 2018' / '2016' -> 'AAAA-MM-DD' / 'AAAA-MM' / 'AAAA'."""
    s = s or ""
    m = ISO.search(s)
    if m:
        return "-".join(m.groups())
    my = month_year(s)
    if my and my.get("year"):
        return f"{my['year']}-{my['month']:02d}" if my.get("month") else str(my["year"])
    return None


def url(u):
    u = u.rstrip(".,;)")
    return "http://" + u if u.lower().startswith("www.") else u


def links(frag, txt):
    out, seen = [], set()
    for u, lbl in re.findall(r"<a[^>]+href=[\"']([^\"'#][^\"']*)[\"'][^>]*>(.*?)</a>", frag or "", flags=re.I | re.S):
        u = H.unescape(u).strip()
        if u.lower().startswith(("http", "www")) and u not in seen:
            seen.add(u)
            out.append({"url": url(u), "label": clean(text(lbl))})
    for u in URL_RE.findall(txt or ""):
        u = url(u)
        if u not in seen and not any(o["url"] == u for o in out):
            seen.add(u)
            out.append({"url": u, "label": None})
    return out


def fields(line):
    """'A: x, B: y z, C:' -> ([('A', 'x'), ('B', 'y z'), ('C', '')], free text before the first label)."""
    for lab in INLINE_LABELS:
        line = re.sub(rf"(?<=\S) ({lab}):", r", \1:", line)
    ms = [m for m in LABEL_RE.finditer(line) if not m.group(1).isupper()]  # 'CINEMATECA: ...' is text, not a label
    # 'Nombre del Producto: Exposición: Los inmigrantes...': after an empty value, an unknown label is part of the value
    ms = [
        m
        for k, m in enumerate(ms)
        if not (k and norm(m.group(1)) not in KNOWN and not line[ms[k - 1].end() : m.start(1)].strip())
    ]
    out = []
    for k, m in enumerate(ms):
        lab = m.group(1).strip()
        if norm(lab) in GREEDY:
            out.append((lab, line[m.end() :].strip()))
            break
        end = ms[k + 1].start(1) if k + 1 < len(ms) else len(line)
        out.append((lab, line[m.end() : end].strip().strip(",").strip()))
    return out, line[: ms[0].start(1)].strip(" ,|") if ms else line.strip()


def is_label(k):
    """A real 'label:' of a work, not a piece of the citation ('JOURNAL OF X ISSN', 'P05064 págs')."""
    return (len(k) <= 40 and k != k.upper()) or k in ("DOI", "URL")


def split_people(s):
    return [p for p in (clean(x) for x in re.split(r",\s*", s or "")) if p and p.lower() not in EMPTY]


# ---------------------------------------------------------------- page structure
def blocks(page):
    """[(title, [row_html, ...])] for every header cell, in page order, and the group's name. A header usually starts
    a table; the art, architecture and design sections are header rows inside one table."""
    out = []
    heads = list(re.finditer(r'<td[^>]*class="celdaEncabezado"[^>]*>(.*?)</td>', page, flags=re.I | re.S))
    for k, m in enumerate(heads):
        end = page.find("</table>", m.end())
        if k + 1 < len(heads):
            end = min(end if end >= 0 else len(page), heads[k + 1].start())
        body = page[m.end() : end if end >= 0 else len(page)]
        rows = re.findall(r"<tr[^>]*>(.*?)(?:</tr>|$)", body, flags=re.I | re.S)
        out.append((text(m.group(1)), [r for r in rows if "celdaEncabezado" not in r and text(r)]))
    name = re.search(r'<span class="celdaEncabezado">(.*?)</span>', page, flags=re.I | re.S)
    return (text(name.group(1)) if name else None), out


def row_item(row):
    """(endorsed, content html) of an item row: the check image means 'avalado' in the last measurement."""
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row, flags=re.I | re.S)
    return "chulo_1" in row, (cells[-1] if cells else row)


def head(section, frag):
    """(type, title, rest of the first line, other lines) of an item."""
    m = re.search(r"<(strong|b)>(.*?)</\1>", frag, flags=re.I | re.S)
    if not m or not re.fullmatch(r"\s*(\d+\s*\.-?)?\s*", text(frag[: m.start()])):
        return None, None, "", text(frag, keep_lines=True).split("\n")
    label = re.sub(r"^\d+\s*\.-?\s*", "", text(m.group(2))).strip()
    lines = text(frag[m.end() :], keep_lines=True).split("\n")
    first = lines[0].lstrip(" :") if lines and lines[0] else ""
    if section == "Redes de Conocimiento Especializado":  # '«Name» : Real' / ': Virtual' is the kind of network
        return clean(first), clean(label), "", lines[1:]
    if section in TITLE_IN_STRONG:
        return None, clean(label), first, lines[1:]
    label = label.rstrip(": ").strip()
    if norm(label).startswith(
        ("nombre del", "nombre de la", "programa academico")
    ):  # 'Nombre del proceso:' is a field, not a type
        return None, clean(first), "", lines[1:]
    return label or None, clean(first), "", lines[1:]


def parse_profile(rows):
    prof = {}
    for r in rows:
        c = re.findall(r"<td[^>]*>(.*?)</td>", r, flags=re.I | re.S)
        if len(c) >= 2:
            prof[text(c[0]).rstrip(" ?:")] = text(c[1]) or None
    out = {"raw": prof}
    f = prof.get("Año y mes de formación") or ""
    m = re.match(r"\s*((?:19|20)\d\d)\s*-\s*(\d{1,2})?", f)
    out["formed"] = {"year": int(m.group(1)), "month": int(m.group(2)) if m.group(2) else None} if m else None
    dep = prof.get("Departamento - Ciudad") or ""
    out["department"], _, out["city"] = (clean(x) for x in dep.partition(" - ")) if dep else (None, "", None)
    out["leader"] = prof.get("Líder")
    cert = prof.get("¿La información de este grupo se ha certificado") or ""
    mc = re.search(r"(\d{4}-\d\d-\d\d)", cert)
    out["certified"] = {"value": cert.split()[0] if cert else None, "date": mc.group(1) if mc else None} if cert else None
    out["website"] = prof.get("Página web")
    out["email"] = prof.get("E-mail")
    cl = prof.get("Clasificación") or ""
    mc = re.match(r"\s*(\S+)\s*(.*)", cl)
    out["classification"] = {"category": mc.group(1), "text": clean(mc.group(2))} if mc else None
    area = prof.get("Área de conocimiento")
    out["knowledge_area"] = [x.strip() for x in area.split("--")] if area else []
    out["national_program"] = prof.get("Programa nacional de ciencia y tecnología")
    out["national_program_secondary"] = prof.get("Programa nacional de ciencia y tecnología (secundario)")
    return out


def numbered(rows):
    return [re.sub(r"^\d+\s*\.-?\s*", "", text(row_item(r)[1])) for r in rows]


def parse_institutions(rows):
    out = []
    for t in numbered(rows):
        m = re.match(r"(.*?)\s*-\s*\(([^)]*)\)\s*$", t)
        out.append({"name": clean(m.group(1) if m else t), "status": clean(m.group(2)) if m else None, "ror": None})
    return out


def parse_plan(rows):
    t = text(rows[0], keep_lines=True) if rows else ""
    out = {}
    for ln in t.split("\n"):
        k, sep, v = ln.partition(":")
        if sep and len(k) <= 40:
            out[k.strip()] = clean(v)
        elif out:
            last = list(out)[-1]
            out[last] = (out[last] or "") + "\n" + ln
    return out


def period(s):
    """'2012/1 - Actual' -> ({year, month}, None, True); '2007/2 - 2009/7' -> (start, end, False)."""
    a, _, b = (s or "").partition(" - ")
    ym = lambda x: (lambda m: {"year": int(m.group(1)), "month": int(m.group(2)) if m.group(2) else None} if m else None)(
        re.match(r"\s*((?:19|20)\d\d)(?:/(\d{1,2}))?", x)
    )
    return ym(a), ym(b), bool(re.search(r"actual", b, flags=re.I))


def parse_members(rows):
    out = []
    for r in rows:
        c = re.findall(r"<td[^>]*>(.*?)</td>", r, flags=re.I | re.S)
        if len(c) < 4 or "celdasTitulo" in r:
            continue
        cod = re.search(r"cod_rh=(\d+)", c[0])
        start, end, open_end = period(text(c[3]))
        hours = text(c[2])
        out.append(
            {
                "full_name": re.sub(r"^\d+\s*\.-?\s*", "", text(c[0])),
                "cod_rh": cod.group(1) if cod else None,
                "url": CVLAC.format(cod.group(1)) if cod else None,
                "linkage": text(c[1]) or None,
                "hours": int(hours) if hours.isdigit() else (hours or None),
                "period": text(c[3]) or None,
                "start": start,
                "end": end,
                "open_end": open_end,
            }
        )
    return out


def parse_projects(rows):
    out = []
    for r in rows:
        endorsed, frag = row_item(r)
        typ, title, _, lines = head("Proyectos", frag)
        start, end, open_end = period(" ".join(lines))
        out.append(
            {
                "type": typ,
                "title": title,
                "endorsed": endorsed,
                "start": start,
                "end": end,
                "ongoing": open_end,
                "text": text(frag, keep_lines=True),
            }
        )
    return out


def parse_events(rows):
    out = []
    for r in rows:
        endorsed, frag = row_item(r)
        typ, name, _, lines = head("Eventos Científicos", frag)
        main = lines[0] if lines else ""
        m = re.match(r"(.*?),?\s*desde\s+(\S*)\s*-\s*hasta\s*(\S*)", main)
        fl = dict((norm(k), v) for k, v in fields(main)[0])
        insts = [
            {"name": clean(mi.group(1)), "link": clean(mi.group(2))}
            for mi in re.finditer(r"Nombre de la instituci[oó]n:\s*(.*?)\s*Tipo de vinculaci[oó]n:?\s*(.*)", "\n".join(lines))
        ]
        out.append(
            {
                "name": name,
                "type": typ,
                "scope": value(fl.get("ambito")),
                "endorsed": endorsed,
                "start": iso_date(m.group(2)) if m else None,
                "end": iso_date(m.group(3)) if m else None,
                "place": clean(m.group(1)) if m else None,
                "participation": [x.strip() for x in (fl.get("tipos de participacion") or "").split(",") if x.strip()],
                "institutions": insts,
                "text": text(frag, keep_lines=True),
            }
        )
    return out


# ---------------------------------------------------------------- other products
def structure(section, endorsed, frag):
    """Generic item: type, title, authors, place, dates, identifiers, links and every 'label: value' field."""
    typ, title, first, lines = head(section, frag)
    txt = text(frag, keep_lines=True)
    it = {"type": typ, "endorsed": endorsed, "title": title, "authors": []}
    raw, free = {}, []
    if first:
        free.append(first)
    for ln in lines:
        if re.match(r"Autores\s*:", ln):
            it["authors"] = [{"full_name": a} for a in split_people(ln.split(":", 1)[1])]
            continue
        fl, lead = fields(ln)
        if lead:
            free.append(lead)
        for k, v in fl:
            if k not in raw or not raw[k]:
                raw[k] = v
    nf = {norm(k): v for k, v in raw.items()}
    if value(nf.get("nombre del orientado")):  # juries: the evaluated student
        it["authors"] = [{**a, "type": "jury"} for a in it["authors"]] + [
            {"full_name": x, "type": "student"} for x in split_people(nf["nombre del orientado"])
        ]
    if not title:
        it["title"] = next((value(nf[k]) for k in TITLE_LABELS if value(nf.get(k))), None)
    for k, v in nf.items():
        key = LABEL_KEYS.get(k)
        v = value(v)
        if key and v and key not in it:
            it[key] = [x.strip() for x in v.split(";") if x.strip()] if key in LIST_KEYS else v
    # place and dates from the free text: 'Colombia, 2020', 'en BARRANQUILLA, desde 2014-03-17 - hasta',
    # 'desde Julio 2016 hasta ...'
    lead = " ".join(free)
    mc = re.match(r"\s*(?:en\s+)?([^\d,][^,]*?)\s*,\s*(?:(?:19|20)\d\d|desde)", lead) or re.match(r"\s*en\s+(.+?)\s*$", lead)
    if mc and not re.search(r"desde|hasta", mc.group(1), flags=re.I):
        it.setdefault("country" if not lead.lstrip().lower().startswith("en ") else "city", clean(mc.group(1)))
    md = re.search(r"desde\s+(.*?)\s*-?\s*hasta\s*(.*?)(?:,|$)", lead, flags=re.I)
    if md:
        it["start"], it["end"] = iso_date(md.group(1)), iso_date(md.group(2))
    date = next((iso_date(nf[k]) for k in DATE_LABELS if nf.get(k) and iso_date(nf[k])), None)
    if not date and nf.get("ano"):  # 'Fecha de presentación: Año: 2021, Mes: Febrero' / 'Año: 2016, Mes: 12'
        mes = nf.get("mes") or ""
        date = iso_date(f"{mes} {nf['ano']}") if not mes.isdigit() else f"{nf['ano']}-{int(mes):02d}"
    if not date and nf.get("ano de solicitud"):
        mes = nf.get("mes de solicitud") or ""
        date = f"{nf['ano de solicitud']}-{int(mes):02d}" if mes.isdigit() and int(mes) else nf["ano de solicitud"]
    for keys, out_key in ((START_LABELS, "start"), (END_LABELS, "end")):
        d = next((iso_date(nf[k]) for k in keys if nf.get(k)), None)
        if d:
            it[out_key] = d
    if nf.get("ano de inicio"):  # consultancies: 'Año de inicio: 2014, Mes de inicio: 7, Año de fin: 2015, Mes de fin: 3'
        for a, m_, k in (("ano de inicio", "mes de inicio", "start"), ("ano de fin", "mes de fin", "end")):
            y, mo = nf.get(a) or "", nf.get(m_) or ""
            if y.isdigit() and int(y):
                it[k] = f"{y}-{int(mo):02d}" if mo.isdigit() and 0 < int(mo) <= 12 else y
    if date:
        it["date"] = date
    if not date and not it.get("start") and re.search(r"\b(?:19|20)\d\d\b", lead):
        it["date"] = iso_date(lead)
    for k, v in nf.items():  # durations with a unit in the label: 'Duración (semanas): 3'
        mu = re.match(r"duracion\s*\((\w+)\)", k)
        if mu and value(v) and v.strip().isdigit():
            it["duration"] = {"value": int(v), "unit": mu.group(1)}
    ids = []
    for k, src in ID_LABELS.items():
        if value(nf.get(k)):
            ids.append({"source": src, "id": value(nf[k])})
    for m in re.finditer(r"SNIES\s*(\d+)", txt):
        ids.append({"source": "snies", "id": m.group(1)})
    doi = find_doi(txt)
    if doi:
        ids.append({"source": "doi", "id": doi})
    for m in re.finditer(r"ISBN:?\s*([\dXx-]{10,17})", txt):
        ids.append({"source": "isbn", "id": m.group(1)})
    if ids:
        it["identifiers"] = ids
    lk = links(frag, txt)
    if lk:
        it["links"] = lk
    it["text"] = txt
    kept = {k: v for k, v in raw.items() if value(v)}
    if kept:
        it["fields"] = kept
    y = (it.get("date") or it.get("start") or it.get("end") or "")[:4]
    it["year"] = int(y) if y.isdigit() else year_of(lead)
    return it


def parse_thesis(endorsed, frag):
    it = structure(THESES, endorsed, frag)
    nf = {norm(k): v for k, v in (it.get("fields") or {}).items()}
    students = split_people(nf.get("nombre del estudiante"))
    tutors = split_people(nf.get("tutor es cotutor es"))
    role = it.get("role") or ""
    ttype = "co-advisor" if "cotutor" in norm(role) or "asesor" in norm(role) else "advisor"
    it["authors"] = [{"full_name": t, "type": ttype} for t in tutors] + [{"full_name": s, "type": "student"} for s in students]
    inst = value(nf.get("institucion"))
    it["institution"] = {"name": inst} if inst else None
    it["titles"] = [{"title": it["title"], "source": "gruplac", "provenance": "gruplac"}] if it.get("title") else []
    pages = nf.get("numero de paginas") or ""
    if pages.isdigit() and int(pages):
        it["pages"] = int(pages)
    if it.get("end"):
        it["year"] = int(it["end"][:4])
    return it


def merge_asc(prods):
    """The four sections of social appropriation of knowledge (fortalecimiento o solución de asuntos de interés social,
    Centro de Ciencia, política pública y normatividad, cadenas productivas) go into one list titled ASC, as in
    cvlac-json, where the first of them was; each item's `type` says which section it came from."""
    out = {}
    for title, its in prods.items():
        if re.match(r"(procesos?|productos) de apropiaci[oó]n social del conocimiento", title, flags=re.I):
            for it in its:
                it["type"] = f"{ASC} - {title}"
            out.setdefault(ASC, []).extend(its)
        else:
            out.setdefault(title, []).extend(its)
    return out


# ---------------------------------------------------------------- works
def work_from_item(section, endorsed, frag, nro, n):
    it = structure(section, endorsed, frag)
    typ, title, _, lines = head(section, frag)
    detail = next((ln for ln in lines if not re.match(r"Autores\s*:", ln)), "")
    flat = " ".join(ln for ln in lines if not re.match(r"Autores\s*:", ln))
    g = lambda pat, s=flat: (lambda m: value(m.group(1)) if m else None)(re.search(pat, s, flags=re.I))
    issn = g(r"ISSN:\s*([\dXx-]{8,9})")
    isbn = g(r"ISBN:\s*([\dXx-]{9,17})")
    year = it.get("year") if it.get("date") else None
    if not year:
        m = re.search(r"(?:^|,\s*|\s)((?:19|20)\d\d)\b(?!-\d)", detail)
        year = int(m.group(1)) if m else it.get("year")
    m_doi = re.search(r"DOI:\s*(\S*)", flat, flags=re.I)
    doi = find_doi(m_doi.group(1) if m_doi else "", flat, *(lk["url"] for lk in it.get("links") or []))
    country = None
    mc = re.match(r"\s*([^\d,][^,]*?)\s*,", detail)
    if mc and not re.search(r":", mc.group(1)):
        country = clean(mc.group(1))
    source_name = None
    if re.search(r"\sISSN:", detail):  # also with 'ISSN: 0'
        ms = re.match(r"\s*[^,]*,\s*(.*?)\s+ISSN:", detail)
        source_name = value(ms.group(1)) if ms else None
    elif section.startswith("Capítulos"):
        ms = re.match(r"\s*[^,]*,\s*(?:19|20)\d\d\s*,\s*(.*?),\s*ISBN:", detail)
        source_name = value(ms.group(1)) if ms else None
    pub = g(r"\bEd\.\s*(.*?)\s*$", detail) or it.get("publisher")
    vol = g(r"\bvol\.?:?\s*([\w/-]+)") or g(r"\bVol\.\s*([\w/-]+)")
    issue = g(r"fasc:\s*([\w/-]+)")
    pages = re.search(r"p[aá]gs:?\s*([\w-]*?\w)\s+-\s+([\w-]+)", flat)
    npages = g(r"Nro\. Paginas:\s*(\d+)") or g(r"\bp[aá]gs:\s*(\d+)\s*,?\s*Ed\.")
    cls = BIBLIO.get(section, section)
    hier = ["Producción bibliográfica", cls] + ([typ] if typ and norm(typ) != norm(cls) else [])
    ext = []
    if doi:
        ext.append({"provenance": "gruplac", "source": "doi", "id": doi})
    if isbn:
        ext.append({"provenance": "gruplac", "source": "isbn", "id": isbn})
    src_ids = [{"source": "issn", "id": issn}] if issn else ([{"source": "isbn", "id": isbn}] if isbn and source_name else [])
    authors = [{"full_name": a["full_name"], "id": None, "external_ids": [], "affiliations": []} for a in it["authors"]]
    title = clean(title or it.get("title"))
    return {
        "id": f"gruplac:{nro}:{n}",
        "title": title,
        "titles": [{"title": title, "lang": "", "source": "gruplac", "provenance": "gruplac"}] if title else [],
        "types": [{"provenance": "gruplac", "source": "gruplac", "type": x, "level": i} for i, x in enumerate(hier)],
        "product_types": [{"name": hier[-1], "source": "gruplac"}],
        "authors": authors,
        "authors_count": len(authors),
        "year_published": year,
        "doi": f"https://doi.org/{doi}" if doi else None,
        "external_ids": ext,
        "external_urls": [{"provenance": "gruplac", "source": "gruplac", "url": lk["url"]} for lk in it.get("links") or []],
        "source": {
            "name": source_name,
            "external_ids": src_ids,
            "publisher": {"name": clean(pub), "country": country} if (pub or country) else {},
        },
        "bibliographic_info": {
            k: v
            for k, v in {
                "volume": vol,
                "issue": issue,
                "start_page": value(pages.group(1)) if pages else None,
                "end_page": value(pages.group(2)) if pages else None,
                "pages": npages,
            }.items()
            if v
        },
        "gruplac": {
            "section": section,
            "endorsed": endorsed,
            "country": country,
            "fields": {k: v for k, v in (it.get("fields") or {}).items() if is_label(k)},
            "text": it["text"],
        },
    }


# ---------------------------------------------------------------- main
def col_table():
    return json.loads(resources.files("gruplac_json").joinpath("data/col_nro.json").read_text(encoding="utf-8"))


def resolve(group_id):
    """'COL0008423' or '1676' / '00000000001676' -> (nro, col); col is None when the table does not know the number."""
    g = str(group_id).strip().upper()
    table = col_table()
    if g.startswith("COL"):
        if g not in table:
            raise ValueError(f"{g} is not in the table of Minciencias groups (2026-10-31); pass the GrupLAC number")
        return table[g], g
    if not g.isdigit() or len(g) > 14:
        raise ValueError("a group is a COL code (COL0008423) or a GrupLAC number (up to 14 digits)")
    nro = g.zfill(14)
    return nro, next((c for c, n in table.items() if n == nro), None)


def build(page, nro, col=None):
    name, blks = blocks(page)
    if not blks:
        raise SystemExit(f"error: no GrupLAC sections found for {nro} (wrong number or the page changed)")
    out = {
        "nro": nro,
        "col": col,
        "url": URL.format(nro),
        "retrieved": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "name": name,
        "profile": {},
        "institutions": [],
        "strategic_plan": {},
        "research_lines": [],
        "members": [],
        "works": [],
        "projects": [],
        "events": [],
        "other_products": {},
        "section_categories": {},
        "counts": {},
    }
    category = None
    for title, rows in blks:
        if title == "Datos básicos":
            out["profile"] = parse_profile(rows)
        elif title == "Instituciones":
            out["institutions"] = parse_institutions(rows)
        elif title == "Plan Estratégico":
            out["strategic_plan"] = parse_plan(rows)
        elif title.startswith("Líneas de investigación"):
            out["research_lines"] = [{"name": x} for x in numbered(rows) if x]
        elif title == "Integrantes del grupo":
            out["members"] = parse_members(rows)
        elif not title:
            continue
        elif not rows and (title == title.upper() or title == ART):
            category = title  # 'PRODUCCIÓN BIBLIOGRÁFICA', 'ACTIVIDADES DE FORMACIÓN'...
        elif not rows:
            continue
        else:
            out["section_categories"][title] = category
            if title == "Proyectos":
                out["projects"] = parse_projects(rows)
            elif title == "Eventos Científicos":
                out["events"] = parse_events(rows)
            elif title in BIBLIO:
                for r in rows:
                    out["works"].append(work_from_item(title, *row_item(r), nro, len(out["works"]) + 1))
            elif title == THESES:
                out["other_products"][title] = [parse_thesis(*row_item(r)) for r in rows]
            else:
                out["other_products"][title] = [structure(title, *row_item(r)) for r in rows]
    out["other_products"] = merge_asc(out["other_products"])
    if ASC in out["other_products"]:
        out["section_categories"][ASC] = "APROPIACIÓN SOCIAL Y DIVULGACIÓN PÚBLICA DE LA CIENCIA"
    for _, its in out["other_products"].items():
        for it in its:
            it["authors"] = [{**a, "id": None, "external_ids": [], "affiliations": []} for a in it.get("authors") or []]
    count(out)
    return out


def count(out):
    old = out.get("counts", {})
    c = {
        "members": len(out["members"]),
        "works": len(out["works"]),
        "projects": len(out["projects"]),
        "events": len(out["events"]),
    }
    for w in out["works"]:
        k = "works:" + w["gruplac"]["section"]
        c[k] = c.get(k, 0) + 1
    c.update({k: len(v) for k, v in out["other_products"].items()})
    c["endorsed_works"] = sum(bool(w["gruplac"]["endorsed"]) for w in out["works"])
    for k in ("works_with_affiliation", "products_with_affiliation"):
        if k in old:
            c[k] = old[k]
    out["counts"] = c


def tidy(data):
    """Same keys for every record of a collection (works, projects, events, members, each other_products list)."""
    for k, v in data.items():
        if isinstance(v, list):
            harmonize(v)
        elif k == "other_products":
            for x in v.values():
                harmonize(x)
                for it in x:  # as in cvlac-json, every product has `authors`, even when the page lists none
                    it.setdefault("authors", [])
    return data


def extract(group_id, html=None, scienti="auto", institution=None, model_year=None, apikey=None, ror=True, log=print):
    """Build the GrupLAC JSON of a group given by its COL code or GrupLAC number.

    html: the page's HTML (str) instead of downloading it. scienti: "auto" (Scienti ids of the matching items when an
    apis.colav.co key is available) or "off". ror: look the group's institutions and thesis institutions up in ROR.
    """
    from . import members
    from . import scienti as scienti_match

    nro, col = resolve(group_id)
    page = html if html is not None else fetch(nro)
    data = build(page, nro, col)
    members.enrich(data)
    if scienti != "off" and col:
        try:
            if scienti_match.enrich(data, col, institution, model_year, key=apikey, log=log):
                members.enrich(data)  # authors added from Scienti records get their affiliations
        except RuntimeError as e:
            log(f"scienti: skipped ({e})")
    elif scienti != "off":
        log("scienti: skipped (COL code unknown for this GrupLAC number)")
    members.ror_institutions(data, ror=ror)
    count(data)
    tidy(data)
    return data

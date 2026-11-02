"""Command line entry point: `gruplac-json`."""

import argparse
import gzip
import json
import sys

from . import __version__
from .parser import decode, extract, fetch, resolve


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="gruplac-json",
        description="Build a JSON from a research group's public GrupLAC page (Minciencias, Colombia)",
    )
    ap.add_argument("group", help="COL code (COL0008423) or GrupLAC number (00000000001676; leading zeros optional)")
    ap.add_argument("-o", "--output", help="output file (default gruplac_<COL or number>.json; '-' for stdout)")
    ap.add_argument("--html", help="parse a saved page (.html or .html.gz) instead of downloading it")
    ap.add_argument("--save-html", help="also save the downloaded page here")
    ap.add_argument("--scienti", choices=["auto", "off"], default="auto", help="add Scienti ids (needs an apis.colav.co key)")
    ap.add_argument("--institution", help="Scienti dump (udea, univalle, uec, unaula); default: try them in turn")
    ap.add_argument("--model-year", help="Scienti model year (default: the dump's latest)")
    ap.add_argument("--apikey", help="apis.colav.co key (else $COLAV_APIKEY or ~/.config/colav/apikey)")
    ap.add_argument("--ror", choices=["auto", "off"], default="auto", help="look institutions up in the ROR registry")
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    a = ap.parse_args(argv)
    log = lambda *x: print(*x, file=sys.stderr)
    try:
        nro, col = resolve(a.group)
    except ValueError as e:
        ap.error(str(e))
    if a.html:
        with open(a.html, "rb") as fh:
            raw = fh.read()
        html = decode(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
    else:
        html = fetch(nro)
        if a.save_html:
            with open(a.save_html, "w", encoding="latin-1", errors="xmlcharrefreplace") as fh:  # as the page declares
                fh.write(html)
    data = extract(
        col or nro,
        html=html,
        scienti=a.scienti,
        institution=a.institution,
        model_year=a.model_year,
        apikey=a.apikey,
        ror=a.ror == "auto",
        log=log,
    )
    out = a.output or f"gruplac_{col or nro}.json"
    text = json.dumps(data, ensure_ascii=False, indent=1)
    if out == "-":
        print(text)
    else:
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(text + "\n")
        c = data["counts"]
        log(
            f"{out}: {data['name']} - {c['members']} members, {c['works']} works, {c['projects']} projects, "
            f"{c['events']} events, {sum(len(v) for v in data['other_products'].values())} other products"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

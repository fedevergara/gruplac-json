"""Command line entry point: `gruplac-json`."""

import argparse

from . import __version__


def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="gruplac-json",
        description="Build a JSON from a research group's public GrupLAC page (Minciencias, Colombia)",
    )
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    ap.parse_args(argv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

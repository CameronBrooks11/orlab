"""``python -m orlab`` — jar management from the command line.

``fetch [version] [--sha256 HEX]`` downloads and verifies a jar into the
cache and prints its path to stdout (the path is the only stable, scriptable
output of this CLI). ``which`` reports the jar ``OpenRocketInstance()``
would use and where the resolution chain found it; its output format is
informational, not a contract.
"""

import argparse
import logging
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m orlab", description="OpenRocket jar management"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    fetch = sub.add_parser("fetch", help="download and verify an OpenRocket jar")
    fetch.add_argument(
        "version", nargs="?", default=None, help="e.g. 24.12 (default: orlab's default version)"
    )
    fetch.add_argument(
        "--sha256", default=None, help="expected digest, required for versions orlab does not pin"
    )
    sub.add_parser("which", help="show the jar OpenRocketInstance() would use")
    args = parser.parse_args(argv)

    # the library never configures logging; the CLI is an application and
    # does, on stderr, so download progress doesn't pollute scriptable stdout
    logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(message)s")

    if args.command == "fetch":
        from .jars import fetch_jar

        try:
            print(fetch_jar(args.version, sha256=args.sha256))
        except Exception as e:  # CLI boundary: message, not traceback
            print(f"error: {e}", file=sys.stderr)
            return 1
        return 0

    import os

    from .core.openrocket_instance import _resolve_default_jar

    try:
        path, source = _resolve_default_jar()
    except FileNotFoundError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    note = "" if os.path.exists(path) else " — does not exist"
    print(f"{path} (via {source}){note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Keep redirected text and CSV portable across operating systems."""
import sys

from .cli import main

for stream in (sys.stdin, sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8", newline="")

raise SystemExit(main())

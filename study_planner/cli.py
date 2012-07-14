"""Command-line entry point."""
import argparse

from . import __version__


def main(argv=None):
    parser = argparse.ArgumentParser(description="Plan and track study tasks.")
    parser.add_argument("--version", action="version", version=__version__)
    parser.parse_args(argv)
    parser.print_help()
    return 0

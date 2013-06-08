# Contributing

Small, focused improvements and reproducible bug reports are welcome.

1. Keep the application dependency-free and compatible with Python 3.10+.
2. Add behavior coverage in `tests/` for changes to persistence or commands.
3. Run `python -m unittest discover -s tests -v` from the repository root.
4. Update the README when command syntax or data behavior changes.
5. Describe the concrete problem, resulting behavior, and validation in a pull request.

Use temporary databases for development and tests. Local database files are ignored
by Git. Preserve existing data when changing the schema or import behavior.

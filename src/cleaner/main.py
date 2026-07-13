"""Entry point.

Run with:
    python -m cleaner.main

Suggested flow:
    1. Load config from environment
    2. Build a Keycloak client
    3. List users, filter for stale ones (respect exclusions)
    4. If dry-run, log the candidates. Otherwise, delete them.
    5. Emit a summary (log line, metric, whatever fits your design)
"""

import sys


def main() -> int:
    # TODO: implement
    print("Not yet implemented.", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())

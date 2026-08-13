import sys

from .app import main as app_main


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "daemon":
        from .daemon import main as daemon_main
        return daemon_main()
    return app_main()


if __name__ == "__main__":
    raise SystemExit(main())

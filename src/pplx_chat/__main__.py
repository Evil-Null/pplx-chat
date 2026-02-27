import sys


def main():
    try:
        from .app import ChatApp

        app = ChatApp()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        _handle_fatal_error(e)
        sys.exit(1)


def _handle_fatal_error(error: Exception):
    """Show user-friendly error messages for common startup failures."""
    from pydantic import ValidationError

    if isinstance(error, ValidationError):
        print("\n  Configuration error:", file=sys.stderr)
        for err in error.errors():
            field = ".".join(str(loc) for loc in err["loc"])
            msg = err["msg"]
            if "PPLX_API_KEY" in field or "api_key" in field:
                print(
                    f"  - Missing API key. Set PPLX_API_KEY in .env or environment.",
                    file=sys.stderr,
                )
            else:
                print(f"  - {field}: {msg}", file=sys.stderr)
        print(file=sys.stderr)
    else:
        print(f"\n  Fatal error: {error}\n", file=sys.stderr)


if __name__ == "__main__":
    main()

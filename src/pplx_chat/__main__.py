import argparse
import sys

from . import __version__


def main():
    parser = argparse.ArgumentParser(
        prog="pplx",
        description="Professional Perplexity AI terminal client",
    )
    parser.add_argument(
        "-v", "--version", action="version", version=f"pplx-chat {__version__}"
    )
    parser.add_argument(
        "-q", "--question", type=str, help="Ask a question and exit (inline mode)"
    )
    parser.add_argument(
        "-m", "--model", type=str, help="Model to use"
    )

    args = parser.parse_args()

    try:
        from .app import ChatApp

        app = ChatApp()

        if args.model:
            from .config import MODELS
            if args.model in MODELS:
                app.current_model = args.model
            else:
                valid = ", ".join(MODELS.keys())
                print(f"  Unknown model '{args.model}'. Valid: {valid}", file=sys.stderr)
                sys.exit(1)

        if args.question:
            app.run_inline(args.question)
        else:
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

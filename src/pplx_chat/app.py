import logging
from rich.console import Console

from .config import load_config, MODELS
from .api import PerplexityClient, APIError, AuthenticationError, RateLimitError
from .streaming import StreamController
from .db import Database
from .ui import UIRenderer
from .prompt import create_prompt_session, get_input
from .commands import find_command, COMMANDS
from .export import export_markdown, export_json
from .logger import setup_logging

logger = logging.getLogger(__name__)


class ChatApp:
    def __init__(self):
        self.config = load_config()
        setup_logging(self.config.log_path)

        self.console = Console()
        self.ui = UIRenderer()

        # Track resources for cleanup on partial init failure
        self.db = None
        self.client = None
        try:
            self.db = Database(self.config.db_path)
            self.client = PerplexityClient(self.config)
        except Exception:
            self._cleanup()
            raise

        self.stream_ctrl = StreamController(self.client, self.ui, self.console, self.config)
        self.prompt_session = create_prompt_session()

        self.current_model = self.config.default_model
        self.session_id: int | None = None
        self.messages: list[dict] = []
        self.session_cost = 0.0
        self.session_tokens = 0
        self.running = True

    def run(self):
        """Main entry point."""
        self.console.print(self.ui.render_welcome())

        # Initialize system message
        self.messages = [{"role": "system", "content": self.config.system_prompt}]

        # Create DB session
        self.session_id = self.db.create_session(self.current_model)
        self.db.add_message(self.session_id, "system", self.config.system_prompt)

        self.console.print(
            f"  Model: [bold cyan]{self.current_model}[/bold cyan] | "
            f"Session: [bold]#{self.session_id}[/bold] | "
            f"Type [bold green]/help[/bold green] for commands\n"
        )

        while self.running:
            try:
                user_input = get_input(self.prompt_session, self.current_model)
            except KeyboardInterrupt:
                continue

            if user_input is None:
                self.cmd_exit("")
                break

            text = user_input.strip()
            if not text:
                continue

            # Check for command
            command, args = find_command(text)
            if command:
                handler = getattr(self, command.handler, None)
                if handler:
                    handler(args)
                continue

            # Regular message — send to API
            self._send_message(text)

        self._cleanup()

    def _send_message(self, text: str):
        """Send user message, stream response, save to DB."""
        self.messages.append({"role": "user", "content": text})
        self.db.add_message(self.session_id, "user", text)

        try:
            response = self.stream_ctrl.stream_response(self.messages, self.current_model)

            if response:
                # Add assistant message to conversation
                self.messages.append({"role": "assistant", "content": response.content})

                # Save to DB
                self.db.add_message(
                    self.session_id,
                    "assistant",
                    response.content,
                    citations=response.citations,
                    usage_json=response.usage.model_dump_json(),
                    cost_json=response.cost.model_dump_json(),
                )

                # Update session cost tracking
                self.session_cost += response.cost.total_cost
                self.session_tokens += response.usage.total_tokens
                self.db.update_session_cost(
                    self.session_id, response.cost.total_cost, response.usage.total_tokens
                )

                # Show cost line if enabled
                if self.config.show_cost:
                    self.console.print(
                        self.ui.render_session_cost(self.session_cost, self.session_tokens)
                    )
                self.console.print()

        except AuthenticationError:
            self.console.print(
                self.ui.render_error("Invalid API key. Check your PPLX_API_KEY in .env")
            )
            self._rollback_user_message()

        except RateLimitError:
            self.console.print(
                self.ui.render_error("Rate limited. Wait a moment and try again.")
            )
            self._rollback_user_message()

        except APIError as e:
            self.console.print(self.ui.render_error(str(e)))
            self._rollback_user_message()
            logger.exception("API error")

        except Exception as e:
            self.console.print(self.ui.render_error(f"Unexpected error: {e}"))
            self._rollback_user_message()
            logger.exception("Unexpected error in _send_message")

    def _rollback_user_message(self):
        """Remove failed user message from both memory and DB."""
        self.messages.pop()
        self.db.delete_last_message(self.session_id)

    # --- Command Handlers ---

    def cmd_help(self, args: str):
        commands_dict = {}
        for cmd in COMMANDS:
            aliases = f" ({', '.join(cmd.aliases)})" if cmd.aliases else ""
            name = f"{cmd.name} {cmd.args}" if cmd.args else cmd.name
            commands_dict[name + aliases] = cmd.description
        self.console.print(self.ui.render_help(commands_dict))

    def cmd_model(self, args: str):
        if args.strip() and args.strip() in MODELS:
            self.current_model = args.strip()
            self.console.print(f"  Switched to [bold cyan]{self.current_model}[/bold cyan]\n")
            return
        # Show selector
        self.console.print(self.ui.render_model_selector())
        models_list = list(MODELS.keys())
        try:
            choice = self.prompt_session.prompt(f"Select (1-{len(models_list)}): ").strip()
            idx = int(choice) - 1
            if 0 <= idx < len(models_list):
                self.current_model = models_list[idx]
                self.console.print(
                    f"  Switched to [bold cyan]{self.current_model}[/bold cyan]\n"
                )
            else:
                self.console.print("  [yellow]Invalid selection[/yellow]\n")
        except (ValueError, EOFError, KeyboardInterrupt):
            self.console.print("  [dim]Cancelled[/dim]\n")

    def cmd_clear(self, args: str):
        self.messages = [{"role": "system", "content": self.config.system_prompt}]
        self.console.clear()
        self.console.print(self.ui.render_welcome())
        self.console.print(
            f"  Conversation cleared. Model: [bold cyan]{self.current_model}[/bold cyan]\n"
        )

    def cmd_new(self, args: str):
        """Start a new session."""
        self.messages = [{"role": "system", "content": self.config.system_prompt}]
        self.session_id = self.db.create_session(self.current_model)
        self.db.add_message(self.session_id, "system", self.config.system_prompt)
        self.session_cost = 0.0
        self.session_tokens = 0
        self.console.print(f"  New session [bold]#{self.session_id}[/bold] started.\n")

    def cmd_save(self, args: str):
        name = args.strip() or f"Session #{self.session_id}"
        self.db.rename_session(self.session_id, name)
        self.console.print(f"  Session saved as [bold]{name}[/bold]\n")

    def cmd_load(self, args: str):
        try:
            sid = int(args.strip())
        except ValueError:
            self.cmd_list("")
            try:
                sid_str = self.prompt_session.prompt("Session ID to load: ").strip()
                sid = int(sid_str)
            except (ValueError, EOFError, KeyboardInterrupt):
                self.console.print("  [dim]Cancelled[/dim]\n")
                return

        session = self.db.get_session(sid)
        if not session:
            self.console.print(f"  [yellow]Session #{sid} not found[/yellow]\n")
            return

        self.session_id = session.id
        self.current_model = session.model
        self.session_cost = session.total_cost
        self.session_tokens = session.total_tokens
        self.messages = [
            {"role": msg.role.value, "content": msg.content} for msg in session.messages
        ]
        self.console.print(
            f"  Loaded session [bold]#{sid}[/bold] "
            f"({len(session.messages)} messages, model: {session.model})\n"
        )

    def cmd_list(self, args: str):
        sessions = self.db.list_sessions()
        if not sessions:
            self.console.print("  [dim]No saved sessions[/dim]\n")
            return
        self.console.print(self.ui.render_session_list(sessions))

    def cmd_delete(self, args: str):
        try:
            sid = int(args.strip())
        except ValueError:
            self.console.print("  [yellow]Usage: /delete <session_id>[/yellow]\n")
            return
        if self.db.delete_session(sid):
            self.console.print(f"  Deleted session [bold]#{sid}[/bold]\n")
        else:
            self.console.print(f"  [yellow]Session #{sid} not found[/yellow]\n")

    def cmd_rename(self, args: str):
        if not args.strip():
            self.console.print("  [yellow]Usage: /rename <name>[/yellow]\n")
            return
        self.db.rename_session(self.session_id, args.strip())
        self.console.print(f"  Session renamed to [bold]{args.strip()}[/bold]\n")

    def cmd_export(self, args: str):
        fmt = args.strip().lower() or "md"
        session = self.db.get_session(self.session_id)
        if not session:
            self.console.print("  [yellow]No session to export[/yellow]\n")
            return

        if fmt in ("md", "markdown"):
            path = export_markdown(session, self.config.export_dir)
        elif fmt == "json":
            path = export_json(session, self.config.export_dir)
        else:
            self.console.print(f"  [yellow]Unknown format: {fmt}. Use 'md' or 'json'[/yellow]\n")
            return

        self.console.print(f"  Exported to [bold]{path}[/bold]\n")

    def cmd_cost(self, args: str):
        self.console.print(self.ui.render_session_cost(self.session_cost, self.session_tokens))
        self.console.print()

    def cmd_search(self, args: str):
        """Set search filters."""
        parts = args.strip().split(maxsplit=1)
        if not parts:
            self.console.print(
                "  Usage:\n"
                "    /search domain <domain1,domain2>  -- Filter to specific domains\n"
                "    /search recency <hour|day|week|month|year>\n"
                "    /search mode <web|academic|sec>\n"
                "    /search clear  -- Reset all filters\n"
            )
            return

        option = parts[0].lower()

        # Handle /search clear (no value needed)
        if option == "clear":
            self.config.search_domain_filter = []
            self.config.search_recency_filter = None
            self.config.search_mode = "web"
            self.console.print("  Search filters cleared.\n")
            return

        if len(parts) < 2:
            self.console.print(
                f"  [yellow]Usage: /search {option} <value>[/yellow]\n"
            )
            return

        value = parts[1].strip()

        if option == "domain":
            domains = [d.strip() for d in value.split(",")]
            self.config.search_domain_filter = domains
            self.console.print(f"  Domain filter: [bold]{domains}[/bold]\n")
        elif option == "recency":
            if value in ("hour", "day", "week", "month", "year"):
                self.config.search_recency_filter = value
                self.console.print(f"  Recency filter: [bold]{value}[/bold]\n")
            else:
                self.console.print(
                    "  [yellow]Invalid recency. Use: hour, day, week, month, year[/yellow]\n"
                )
        elif option == "mode":
            if value in ("web", "academic", "sec"):
                self.config.search_mode = value
                self.console.print(f"  Search mode: [bold]{value}[/bold]\n")
            else:
                self.console.print(
                    "  [yellow]Invalid mode. Use: web, academic, sec[/yellow]\n"
                )
        else:
            self.console.print(
                f"  [yellow]Unknown option: {option}. Use: domain, recency, mode, clear[/yellow]\n"
            )

    def cmd_system(self, args: str):
        if not args.strip():
            self.console.print(
                f"  Current: [dim]{self.config.system_prompt[:100]}...[/dim]\n"
            )
            return
        self.config.system_prompt = args.strip()
        self.messages[0] = {"role": "system", "content": args.strip()}
        self.console.print("  System prompt updated.\n")

    def cmd_info(self, args: str):
        info = (
            f"  Model:    [bold cyan]{self.current_model}[/bold cyan]\n"
            f"  Session:  [bold]#{self.session_id}[/bold]\n"
            f"  Cost:     [bold yellow]${self.session_cost:.6f}[/bold yellow]\n"
            f"  Tokens:   {self.session_tokens:,}\n"
            f"  Messages: {len(self.messages)}\n"
            f"  Search:   {self.config.search_mode}"
        )
        if self.config.search_domain_filter:
            info += f" | domains: {self.config.search_domain_filter}"
        if self.config.search_recency_filter:
            info += f" | recency: {self.config.search_recency_filter}"
        self.console.print(info + "\n")

    def cmd_exit(self, args: str):
        self.running = False
        self.console.print("\n  [dim]Goodbye.[/dim]\n")

    def _cleanup(self):
        if self.client:
            self.client.close()
        if self.db:
            self.db.close()

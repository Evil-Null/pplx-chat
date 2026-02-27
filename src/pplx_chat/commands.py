from dataclasses import dataclass, field


@dataclass
class Command:
    name: str
    aliases: list[str] = field(default_factory=list)
    description: str = ""
    handler: str = ""
    args: str = ""


# Registry of all commands
COMMANDS = [
    Command("/help", ["/h", "/?"], "Show available commands", "cmd_help"),
    Command("/model", ["/m"], "Switch model", "cmd_model", "[model_name]"),
    Command("/clear", ["/c"], "Clear conversation", "cmd_clear"),
    Command("/save", ["/s"], "Save session with name", "cmd_save", "[name]"),
    Command("/load", ["/l"], "Load a previous session", "cmd_load", "[session_id]"),
    Command("/list", ["/ls"], "List saved sessions", "cmd_list"),
    Command("/delete", ["/del"], "Delete a session", "cmd_delete", "<session_id>"),
    Command("/rename", ["/rn"], "Rename current session", "cmd_rename", "<name>"),
    Command("/export", ["/e"], "Export session (md/json)", "cmd_export", "[format]"),
    Command("/cost", [], "Show session cost summary", "cmd_cost"),
    Command("/search", [], "Set search filters", "cmd_search", "<option> <value>"),
    Command("/system", [], "Change system prompt", "cmd_system", "<prompt>"),
    Command("/info", [], "Show current settings", "cmd_info"),
    Command("/temp", [], "Set temperature", "cmd_temp", "[value]"),
    Command("/top_p", [], "Set top-p sampling", "cmd_top_p", "[value]"),
    Command("/maxtokens", [], "Set max output tokens", "cmd_maxtokens", "[value]"),
    Command("/new", ["/n"], "Start a new session", "cmd_new"),
    Command("/exit", ["/quit", "/q"], "Exit the application", "cmd_exit"),
]


def find_command(input_text: str) -> tuple[Command | None, str]:
    """Match input to a command. Returns (command, remaining_args)."""
    parts = input_text.strip().split(maxsplit=1)
    if not parts or not parts[0].startswith("/"):
        return None, input_text

    cmd_str = parts[0].lower()
    args = parts[1] if len(parts) > 1 else ""

    for cmd in COMMANDS:
        if cmd_str == cmd.name or cmd_str in cmd.aliases:
            return cmd, args

    return None, input_text

from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style as PTStyle

from .commands import COMMANDS


def create_prompt_session() -> PromptSession:
    """Create a configured Prompt Toolkit session."""

    history_path = Path("~/.local/share/pplx-chat/prompt_history").expanduser()
    history_path.parent.mkdir(parents=True, exist_ok=True)

    # Key bindings
    bindings = KeyBindings()

    @bindings.add("c-d")
    def exit_handler(event):
        """Ctrl+D to exit."""
        event.app.exit(result=None)

    @bindings.add("escape", "enter")
    def multiline_handler(event):
        """Alt+Enter for newline in input."""
        event.current_buffer.insert_text("\n")

    # Command completer
    command_names = []
    for cmd in COMMANDS:
        command_names.append(cmd.name)
        command_names.extend(cmd.aliases)

    completer = WordCompleter(command_names, sentence=True)

    # Style
    style = PTStyle.from_dict({
        "prompt": "bold green",
        "": "",
    })

    session = PromptSession(
        history=FileHistory(str(history_path)),
        key_bindings=bindings,
        completer=completer,
        style=style,
        multiline=False,
        enable_history_search=True,
        mouse_support=False,
    )

    return session


def get_input(session: PromptSession, model: str) -> str | None:
    """
    Get user input. Returns None on Ctrl+D/EOF.
    The prompt shows the current model name.
    """
    try:
        prompt_text = HTML(f"<b><style fg='green'>You [{model}]</style></b> &gt; ")
        return session.prompt(prompt_text)
    except (EOFError, KeyboardInterrupt):
        return None

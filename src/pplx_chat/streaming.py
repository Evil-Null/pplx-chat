import logging

from rich.live import Live
from rich.console import Console

from .api import PerplexityClient, APIError
from .config import AppConfig
from .models import APIResponse
from .ui import UIRenderer

logger = logging.getLogger(__name__)


class StreamController:
    """Manages the real-time streaming display."""

    def __init__(self, client: PerplexityClient, ui: UIRenderer, console: Console, config: AppConfig):
        self.client = client
        self.ui = ui
        self.console = console
        self.config = config

    def stream_response(
        self, messages: list[dict], model: str, **overrides
    ) -> APIResponse | None:
        """
        Stream a response with live display.
        Returns the final APIResponse with all metadata.
        Raises APIError subclasses to the caller (app.py) for handling.
        """
        accumulated = ""
        api_response = None

        try:
            with Live(
                self.ui.render_thinking(model),
                console=self.console,
                refresh_per_second=15,
                transient=False,
            ) as live:
                for chunk in self.client.stream_chat(messages, model, **overrides):
                    if isinstance(chunk, str):
                        accumulated += chunk
                        live.update(self.ui.render_streaming(accumulated, model))
                    elif isinstance(chunk, APIResponse):
                        api_response = chunk

                # Replace streaming panel with final polished response before Live exits
                if api_response:
                    live.update(self.ui.render_response(
                        api_response, model,
                        show_citations=self.config.show_citations,
                        show_related=self.config.show_related,
                    ))
        except APIError:
            # Let API errors propagate to app.py for user-facing handling
            logger.debug("API error during streaming, propagating to app")
            raise
        except Exception:
            logger.exception("Unexpected error during streaming")
            raise

        return api_response

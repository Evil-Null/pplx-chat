import json
import logging
from datetime import datetime
from pathlib import Path

from .models import Session

logger = logging.getLogger(__name__)


class ExportError(Exception):
    """Export operation failed."""
    pass


def export_markdown(session: Session, output_dir: Path) -> Path:
    """Export session as a readable Markdown file."""
    filename = _safe_filename(session, "md")
    path = output_dir / filename

    lines = [
        f"# {session.name or f'Session #{session.id}'}",
        "",
        f"**Model:** {session.model}",
        f"**Created:** {session.created_at.strftime('%Y-%m-%d %H:%M')}",
        f"**Total cost:** ${session.total_cost:.6f}",
        f"**Total tokens:** {session.total_tokens:,}",
        "",
        "---",
        "",
    ]

    for msg in session.messages:
        if msg.role.value == "system":
            continue
        role_label = "**You:**" if msg.role.value == "user" else "**Assistant:**"
        lines.append(role_label)
        lines.append("")
        lines.append(msg.content)
        lines.append("")
        lines.append("---")
        lines.append("")

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(lines), encoding="utf-8")
    except OSError as e:
        logger.exception("Failed to export markdown")
        raise ExportError(f"Cannot write file: {e}") from e
    return path


def export_json(session: Session, output_dir: Path) -> Path:
    """Export session as structured JSON."""
    filename = _safe_filename(session, "json")
    path = output_dir / filename

    data = {
        "session_id": session.id,
        "name": session.name,
        "model": session.model,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat(),
        "total_cost": session.total_cost,
        "total_tokens": session.total_tokens,
        "messages": [
            {
                "role": msg.role.value,
                "content": msg.content,
                "timestamp": msg.timestamp.isoformat(),
            }
            for msg in session.messages
        ],
    }

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except OSError as e:
        logger.exception("Failed to export JSON")
        raise ExportError(f"Cannot write file: {e}") from e
    return path


def _safe_filename(session: Session, ext: str) -> str:
    name = session.name or f"session_{session.id}"
    safe = "".join(c if c.isalnum() or c in "-_ " else "" for c in name)
    safe = safe.strip().replace(" ", "_")[:50]
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"pplx_{safe}_{ts}.{ext}"

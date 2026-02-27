# PPLX Chat

Professional Perplexity AI terminal client with real-time streaming, session management, and cost tracking.

![License](https://img.shields.io/badge/License-MIT-green.svg)
![Version](https://img.shields.io/badge/Version-1.2.0-blue.svg)
![Platform](https://img.shields.io/badge/Platform-Linux-yellow.svg)
![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg?logo=python&logoColor=white)
![Perplexity](https://img.shields.io/badge/Perplexity_AI-API-1a1a2e.svg)

![PPLX Chat Screenshot](assets/screenshot.png)

## Features

- **Real-time streaming** — responses render as Markdown mid-stream
- **4 models** — sonar, sonar-pro, sonar-reasoning-pro, sonar-deep-research
- **Session persistence** — SQLite with full conversation history
- **Inline mode** — `pplx -q "your question"` for one-shot queries
- **18 slash commands** — `/help`, `/model`, `/save`, `/load`, `/export`, and more
- **Citations & related questions** — displayed inline from Perplexity search
- **Cost tracking** — per-response and per-session token/cost totals
- **Export** — Markdown or JSON
- **Search filters** — domain, recency, mode (web/academic)
- **Tab completion** — commands auto-complete, Ctrl+R history search

## Quick Start

```bash
git clone https://github.com/Evil-Null/pplx-chat.git
cd pplx-chat
chmod +x install.sh
./install.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
# Edit .env with your Perplexity API key
pplx
```

## Inline Mode

Ask a question without entering the interactive shell:

```bash
pplx -q "What is quantum computing?"
pplx -q "Python vs Rust" -m sonar-pro
```

| Flag | Description |
|------|-------------|
| `-q`, `--question` | Ask a question and exit |
| `-m`, `--model` | Model to use |
| `-v`, `--version` | Show version |

## Requirements

- Python 3.10+
- [Perplexity API key](https://www.perplexity.ai/settings/api)

## Configuration

### API Key

Set your key in `.env`:

```
PPLX_API_KEY=pplx-your-key-here
```

### Optional YAML Config

Copy `config.default.yaml` to `~/.config/pplx-chat/config.yaml` and customize:

```yaml
default_model: sonar
temperature: 0.2
max_tokens: 4096
search_mode: web
show_cost: true
show_citations: true
```

## Commands

| Command | Alias | Description |
|---------|-------|-------------|
| `/help` | `/h` | Show available commands |
| `/model [name]` | `/m` | Switch model |
| `/new` | `/n` | Start new session |
| `/save [name]` | `/s` | Save session with name |
| `/load [id]` | `/l` | Load previous session |
| `/list` | `/ls` | List saved sessions |
| `/delete <id>` | `/del` | Delete a session |
| `/rename <name>` | `/rn` | Rename current session |
| `/export [md\|json]` | `/e` | Export session |
| `/cost` | | Show session cost |
| `/search <option>` | | Set search filters |
| `/system <prompt>` | | Change system prompt |
| `/info` | | Show current settings |
| `/temp [value]` | | Set temperature (0.0-2.0) |
| `/top_p [value]` | | Set top-p sampling (0.0-1.0) |
| `/maxtokens [value]` | | Set max output tokens |
| `/clear` | `/c` | Clear conversation |
| `/exit` | `/q` | Exit |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Tab` | Auto-complete commands |
| `Ctrl+R` | Search input history |
| `Ctrl+D` | Exit |
| `Ctrl+C` | Cancel current input / stop streaming |
| `Alt+Enter` | Newline in input |

## Architecture

```
src/pplx_chat/
├── __main__.py    # Entry point
├── config.py      # Pydantic Settings (.env + YAML)
├── models.py      # Data models
├── api.py         # httpx + SSE streaming client
├── streaming.py   # Rich Live display controller
├── db.py          # SQLite persistence
├── ui.py          # Rich rendering components
├── prompt.py      # Prompt Toolkit input
├── commands.py    # Slash command registry
├── export.py      # Markdown/JSON export
└── logger.py      # File-only logging
```

## License

MIT

## Author

**Evil Null**

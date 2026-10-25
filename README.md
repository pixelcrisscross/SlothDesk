# SlothDesk 🦥

**A local-first AI file organizer powered by Qwen through Ollama.** SlothDesk scans a folder, asks a locally running model for organization suggestions, lets you review each change, then applies approved moves with a manifest and undo support.

> Safety first: use a disposable test folder before trying this with real files. The model only receives file metadata, not document contents, in this MVP.

## Features

- Local model inference through Ollama
- Filename and category suggestions from Qwen
- Human review before filesystem changes
- Path validation and collision checks
- Exact duplicate detection using SHA-256
- Run history in SQLite
- Undo successful operations where the original path is available
- Synthetic demo folder generator

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/) installed and running
- A model supported by your Ollama install, such as `qwen3:8b`
- Enough RAM and disk space for the selected model

## Run locally

### 1. Pull the model

```bash
ollama pull qwen3:8b
```

Confirm Ollama is available at `http://localhost:11434`.

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Start the app

```bash
streamlit run app.py
```

Use the sidebar to set the folder path. You can click **Create demo folder with sample files** and then set the folder to `~/SlothDesk-Demo`.

## How it works

1. `scanner.py` discovers regular files and skips symlinks and common generated folders.
2. `ai_planner.py` sends names and metadata to local Ollama and requests structured output.
3. `schemas.py` and `safety.py` validate the model response and destinations.
4. The UI requires explicit approval.
5. `executor.py` applies allowed operations and creates a run manifest.
6. `undo.py` reverses successful operations when safe.
7. `database.py` saves run history in `~/.slothdesk/history.sqlite3`.

## Run tests

```bash
pytest -q
```

## Limitations

- The MVP operates on files directly inside the selected folder; nested source files are not moved by the AI planner.
- The planner sends at most 150 files to the model in one request; remaining files receive conservative fallback suggestions.
- Classification is based on filenames and metadata, not document contents.
- Exact duplicate detection hashes file contents but never deletes duplicates.
- Undo can fail safely if an original path has been occupied or a moved file is missing.
- This is a local prototype, not a substitute for backups.
- Local inference does not guarantee that all computer activity is offline; verify your own environment and integrations.

## Privacy

The application calls the local Ollama endpoint at `localhost`. It does not intentionally send file metadata to a remote AI API. Ollama, the operating system, and other installed software are outside this application's control.

## License

MIT. Check the license and model terms for any model you download separately.

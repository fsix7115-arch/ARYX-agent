# Frequently Asked Questions (FAQ)

### 1. How is ARYx different from standard AI chat interfaces?
ARYx is a native terminal agent built for developers. It has access to real filesystem tools, surgical code replacement, sandboxed terminal execution, episodic and semantic memory in SQLite, and self-improving skill synthesis.

### 2. Are my API keys safe?
Yes. Keys are stored locally in `~/.aryx/config.toml` with `chmod 600` (readable and writable only by your user account). ARYx actively redacts API keys from all terminal outputs, error messages, and logs.

### 3. What if the agent edits a file incorrectly?
Every write or edit operation automatically creates a timestamped backup in `~/.aryx/snapshots/`. Simply type `/revert` (or `/revert 3` for multiple files) inside the chat, and your files will be restored instantly.

### 4. Can ARYx damage my machine?
ARYx operates in "safe" mode by default, prompting you before executing any file write, edit, or bash command. Dangerous command patterns (e.g. `rm -rf /`, `mkfs`, raw device writes, fork bombs) are blocked unconditionally even if running in `--yolo` mode.

### 5. Can I use ARYx completely offline without paying for API keys?
Yes! Install Ollama (`ollama run llama3.2`), and run `/model use ollama` in ARYx. Everything runs on your local machine with zero external network calls.

### 6. Where is memory stored?
Episodic conversations and semantic facts are saved in an embedded SQLite database at `~/.aryx/memory.db`. It requires no separate daemon or database service.

### 7. What does `aryx doctor` do?
`aryx doctor` tests 9 crucial environment and provider components (Python version, PATH, directory permissions, config, live API key probe, endpoint connectivity, SQLite database, skills directory, and disk space). Running `aryx doctor --fix` automatically repairs common misconfigurations.

### 8. What is the difference between `--yolo` and safe mode?
Safe mode prompts you for confirmation before writing files or running shell commands. `--yolo` executes commands autonomously while still enforcing sandboxed timeouts and the destructive command blocklist.

### 9. How do I switch models or update my API key?
Use the in-chat `/model` command, run `aryx config` to open your configuration file, or run `aryx config show` to inspect settings with keys safely masked.

### 10. How do I clear conversation context without losing memory?
Type `/clear` in chat. Your conversational context window will be refreshed, while all persistent semantic facts and procedural skills in SQLite remain intact.

# ARYx AGENT — Self-Improving Skills Engine

ARYx does not just store conversation text; it extracts repeatable, procedural skills into Markdown playbooks saved in `~/.aryx/skills/`.

## How Skills Are Formed

1. **Threshold Trigger**: When a task takes more than 5 tool steps (e.g. searching code, modifying multiple files, running unit tests, fixing errors) and finishes successfully, the synthesis engine triggers.
2. **Procedural Distillation**: The agent distills the sequence of tool operations, arguments, and outcomes into structured Markdown:
   ```markdown
   # Skill: Build Docker Production Image
   ## Objective
   Create a multi-stage Docker build with zero cache leaks.
   ## Verified Procedure
   1. Execute `read_file`: path='Dockerfile'
   2. Execute `edit_file`: target_content='FROM node:18'...
   3. Execute `bash`: command='docker build -t app:latest .'
   ```
3. **Quality Gate (GRASP-inspired)**:
   - Every skill has a `success_count` and `fail_count` tracked in SQLite.
   - When a skill is reused, ARYx evaluates whether the run succeeded.
   - If a skill falls below 20% success over 10+ uses, it is automatically archived to prevent prompt pollution.
4. **Adaptive Rewriting**: If a skill fails during a subsequent run, the agent creates an evolved version (e.g., `<name>.v2.md`) incorporating corrected steps.

## Managing Skills

In-chat:
```text
aryx > /skills
aryx > /skills show deploy-react
```

Filesystem:
All skills are standard, human-editable Markdown files in `~/.aryx/skills/`. You can edit them in any text editor.

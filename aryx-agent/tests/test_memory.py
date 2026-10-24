"""
ARYx AGENT - Memory & Skills Tests
Verifies episodic logs, semantic facts extraction, procedural skill auto-generation, and quality gates.
"""

from aryx.memory.db import add_semantic_fact, extract_quick_facts, get_semantic_facts, save_message, search_history
from aryx.memory.skills import generate_skill_from_run, list_skills, read_skill, record_skill_outcome, save_skill


def test_semantic_facts():
    add_semantic_fact("User prefers TypeScript and strict mode", category="preference")
    facts = get_semantic_facts(limit=10)
    assert any("TypeScript" in f["fact"] for f in facts)

    extract_quick_facts("I prefer Python 3.11 for all backend services.")
    updated = get_semantic_facts(limit=10)
    assert any("Python 3.11" in f["fact"] for f in updated)


def test_episodic_memory():
    sess = "test_session_123"
    save_message(sess, "user", "How do I build a container with Docker?")
    save_message(sess, "assistant", "Use Dockerfile with multi-stage build.")

    results = search_history("multi-stage", limit=5)
    assert len(results) > 0
    assert any("Docker" in r["content"] for r in results)


def test_procedural_skills_quality_gate():
    skill_content = "# Skill: Deploy React App\n1. Run npm run build\n2. Serve dist"
    saved_path = save_skill("deploy-react", skill_content, version=1)
    assert saved_path is not None

    read_back = read_skill("deploy-react")
    assert read_back is not None
    assert "npm run build" in read_back

    # Quality Gate outcome
    record_skill_outcome("deploy-react", success=True)
    all_skills = list_skills()
    matching = [s for s in all_skills if s["name"] == "deploy-react"]
    assert len(matching) == 1
    assert matching[0]["success_rate"] == 100.0


def test_auto_skill_generation_on_complex_tasks():
    tool_history = [
        {"name": "read_file", "args": {"path": "package.json"}},
        {"name": "grep", "args": {"pattern": "vite"}},
        {"name": "write_file", "args": {"path": "config.js"}},
        {"name": "bash", "args": {"command": "npm test"}},
        {"name": "bash", "args": {"command": "git status"}},
    ]
    skill_file = generate_skill_from_run("Setup Vite build configuration and run tests", tool_history)
    assert skill_file is not None
    assert "build" in skill_file or "config" in skill_file


if __name__ == "__main__":
    test_semantic_facts()
    test_episodic_memory()
    test_procedural_skills_quality_gate()
    test_auto_skill_generation_on_complex_tasks()
    print("✓ All memory and skill engine tests passed successfully!")

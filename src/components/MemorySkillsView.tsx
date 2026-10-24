import React, { useState } from 'react';
import {
  Database,
  Sparkles,
  History,
  Shield,
  RotateCcw,
  Plus,
  Trash2,
  FileCode,
  CheckCircle2,
  Flame,
  BookOpen,
} from 'lucide-react';

interface SemanticFact {
  id: number;
  category: string;
  fact: string;
  confidence: number;
}

interface ProceduralSkill {
  name: string;
  version: number;
  successRate: number;
  uses: number;
  procedure: string;
}

interface Snapshot {
  id: string;
  file: string;
  timestamp: string;
  size: string;
}

export default function MemorySkillsView() {
  const [activeSubTab, setActiveSubTab] = useState<'memory' | 'skills' | 'snapshots'>('skills');

  const [facts, setFacts] = useState<SemanticFact[]>([
    { id: 1, category: 'preference', fact: 'User prefers Python 3.10+ and strictly typed TypeScript.', confidence: 1.0 },
    { id: 2, category: 'context', fact: 'Project root is aryx-agent with zero-friction installation promise.', confidence: 1.0 },
    { id: 3, category: 'rule', fact: 'Never run dangerous commands like rm -rf / or wipe disk partitions.', confidence: 1.2 },
    { id: 4, category: 'preference', fact: 'Always create snapshots in ~/.aryx/snapshots before file writes.', confidence: 1.1 },
    { id: 5, category: 'provider', fact: 'Primary model is gemini-2.5-flash via Google AI Studio API.', confidence: 1.0 },
  ]);

  const [newFact, setNewFact] = useState('');
  const [newCategory, setNewCategory] = useState('preference');

  const [skills, setSkills] = useState<ProceduralSkill[]>([
    {
      name: 'deploy-react-vite',
      version: 1,
      successRate: 100,
      uses: 14,
      procedure: `# Skill: Deploy React Vite Application
## Objective
Verify dependencies, test production compilation, and preview distribution.
## Steps
1. Execute \`read_file\`: path='package.json'
2. Execute \`bash\`: command='npm run build'
3. Execute \`list_dir\`: path='dist'
## Quality Gate: Accepted (100% success rate)`,
    },
    {
      name: 'auto-repair-permissions',
      version: 2,
      successRate: 92.3,
      uses: 13,
      procedure: `# Skill: Auto Repair Permissions
## Objective
Heal corrupted ~/.aryx folder permissions and recreate SQLite WAL indexes safely.
## Steps
1. Execute \`bash\`: command='mkdir -p ~/.aryx/skills ~/.aryx/snapshots'
2. Execute \`bash\`: command='chmod 700 ~/.aryx'
3. Execute \`python\`: code='import sqlite3; conn = sqlite3.connect("~/.aryx/memory.db"); conn.execute("PRAGMA journal_mode=WAL;")'
## Quality Gate: Accepted (v2 evolved after step 2 race condition fix)`,
    },
    {
      name: 'setup-docker-service',
      version: 1,
      successRate: 100,
      uses: 8,
      procedure: `# Skill: Setup Docker Service
## Objective
Create multi-stage Dockerfile and test container build.
## Steps
1. Execute \`write_file\`: path='Dockerfile'
2. Execute \`write_file\`: path='.dockerignore'
3. Execute \`bash\`: command='docker build -t app:test .'
## Quality Gate: Accepted (8/8 successful runs)`,
    },
  ]);

  const [selectedSkill, setSelectedSkill] = useState<ProceduralSkill>(skills[0]);

  const [snapshots, setSnapshots] = useState<Snapshot[]>([
    { id: 'snap-1', file: 'aryx/cli.py', timestamp: '2 minutes ago', size: '24.1 KB' },
    { id: 'snap-2', file: 'aryx/config.py', timestamp: '8 minutes ago', size: '8.4 KB' },
    { id: 'snap-3', file: 'aryx/doctor.py', timestamp: '14 minutes ago', size: '9.2 KB' },
    { id: 'snap-4', file: 'install.sh', timestamp: '22 minutes ago', size: '6.8 KB' },
  ]);

  const handleAddFact = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newFact.trim()) return;
    const item: SemanticFact = {
      id: Date.now(),
      category: newCategory,
      fact: newFact.trim(),
      confidence: 1.0,
    };
    setFacts([item, ...facts]);
    setNewFact('');
  };

  const handleDeleteFact = (id: number) => {
    setFacts(facts.filter((f) => f.id !== id));
  };

  const handleRevertSnapshot = (snap: Snapshot) => {
    alert(`Restoring ${snap.file} from ~/.aryx/snapshots/${snap.id}... Restored successfully.`);
  };

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl border border-slate-800 shadow-xl overflow-hidden">
      {/* Top Header & Sub-Navigation */}
      <div className="flex flex-wrap items-center justify-between px-6 py-4 bg-slate-950/80 border-b border-slate-800 gap-3">
        <div>
          <h2 className="text-base font-bold text-slate-100 flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-purple-400" />
            ARYx Cognitive Memory &amp; Self-Improving Skills Engine
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Episodic SQLite conversations, persistent semantic facts, and procedural markdown skills.
          </p>
        </div>

        {/* Tab pills */}
        <div className="flex items-center gap-1 bg-slate-900 p-1 rounded-lg border border-slate-800">
          <button
            onClick={() => setActiveSubTab('skills')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
              activeSubTab === 'skills'
                ? 'bg-purple-950 text-purple-300 border border-purple-800/80 shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            Procedural Skills ({skills.length})
          </button>
          <button
            onClick={() => setActiveSubTab('memory')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
              activeSubTab === 'memory'
                ? 'bg-blue-950 text-blue-300 border border-blue-800/80 shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Database className="w-3.5 h-3.5" />
            Semantic Facts ({facts.length})
          </button>
          <button
            onClick={() => setActiveSubTab('snapshots')}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
              activeSubTab === 'snapshots'
                ? 'bg-amber-950 text-amber-300 border border-amber-800/80 shadow'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <RotateCcw className="w-3.5 h-3.5" />
            Snapshots &amp; /revert ({snapshots.length})
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* SKILLS TAB */}
        {activeSubTab === 'skills' && (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 h-full">
            {/* Skills List Column */}
            <div className="space-y-3">
              <div className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center justify-between">
                <span>Synthesized Skills</span>
                <span className="text-[10px] text-purple-400 font-mono">Quality Gate Active</span>
              </div>

              <div className="space-y-2">
                {skills.map((skill) => {
                  const isSelected = selectedSkill.name === skill.name;
                  return (
                    <button
                      key={skill.name}
                      onClick={() => setSelectedSkill(skill)}
                      className={`w-full p-3.5 rounded-xl text-left border transition ${
                        isSelected
                          ? 'bg-purple-950/60 border-purple-700/80 text-purple-100 shadow-md'
                          : 'bg-slate-950 border-slate-800 hover:border-slate-700 text-slate-300'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-mono text-xs font-bold text-slate-100 truncate">
                          {skill.name}
                        </span>
                        <span className="text-[10px] px-2 py-0.5 rounded bg-purple-900/60 text-purple-300 border border-purple-700/50">
                          v{skill.version}
                        </span>
                      </div>

                      <div className="flex items-center justify-between mt-2 text-xs text-slate-400">
                        <span className="flex items-center gap-1 text-emerald-400 font-medium">
                          <CheckCircle2 className="w-3.5 h-3.5" />
                          {skill.successRate}% Success
                        </span>
                        <span>{skill.uses} executions</span>
                      </div>
                    </button>
                  );
                })}
              </div>

              {/* Quality Gate Info Box */}
              <div className="p-3.5 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-400 space-y-1.5">
                <div className="font-semibold text-slate-200 flex items-center gap-1 text-xs">
                  <Flame className="w-3.5 h-3.5 text-amber-400" />
                  GRASP-Inspired Quality Gate
                </div>
                <p className="text-[11px] leading-relaxed">
                  When a task exceeds 5 tool calls and succeeds, ARYx compiles a Markdown procedure.
                  Skills with &lt;20% success over 10+ uses are auto-archived.
                </p>
              </div>
            </div>

            {/* Selected Skill Markdown Preview Column */}
            <div className="md:col-span-2 flex flex-col bg-slate-950 rounded-xl border border-slate-800 overflow-hidden">
              <div className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4 text-purple-400" />
                  <span className="font-mono text-xs font-bold text-slate-200">
                    ~/.aryx/skills/{selectedSkill.name}.md
                  </span>
                </div>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-950 text-emerald-400 border border-emerald-800">
                  {selectedSkill.successRate}% Success Rate
                </span>
              </div>

              <div className="flex-1 p-5 font-mono text-xs text-slate-200 whitespace-pre-wrap leading-relaxed overflow-y-auto">
                {selectedSkill.procedure}
              </div>
            </div>
          </div>
        )}

        {/* SEMANTIC MEMORY TAB */}
        {activeSubTab === 'memory' && (
          <div className="space-y-6">
            {/* Add Fact Form */}
            <form onSubmit={handleAddFact} className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-wrap items-center gap-3">
              <select
                value={newCategory}
                onChange={(e) => setNewCategory(e.target.value)}
                className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-200 focus:outline-none"
              >
                <option value="preference">Preference</option>
                <option value="context">Context</option>
                <option value="rule">Rule</option>
                <option value="identity">Identity</option>
              </select>

              <input
                type="text"
                value={newFact}
                onChange={(e) => setNewFact(e.target.value)}
                placeholder="Teach ARYx a new semantic fact (e.g. 'User prefers Vitest over Jest')..."
                className="flex-1 px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-slate-100 placeholder-slate-500 focus:outline-none"
              />

              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold flex items-center gap-1.5 transition"
              >
                <Plus className="w-3.5 h-3.5" />
                Add Fact
              </button>
            </form>

            {/* Facts Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {facts.map((fact) => (
                <div
                  key={fact.id}
                  className="p-4 rounded-xl bg-slate-950 border border-slate-800 hover:border-slate-700 transition flex items-start justify-between gap-3"
                >
                  <div className="space-y-1">
                    <span className="inline-block px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-blue-950 text-blue-300 border border-blue-800/80">
                      {fact.category}
                    </span>
                    <p className="text-xs text-slate-200 leading-relaxed font-sans mt-1">
                      {fact.fact}
                    </p>
                    <span className="text-[10px] text-slate-400 font-mono">
                      Confidence: {(fact.confidence * 100).toFixed(0)}%
                    </span>
                  </div>

                  <button
                    onClick={() => handleDeleteFact(fact.id)}
                    className="p-1 text-slate-500 hover:text-rose-400 transition"
                    title="Delete fact"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* SNAPSHOTS TAB */}
        {activeSubTab === 'snapshots' && (
          <div className="space-y-4">
            <div className="p-4 rounded-xl bg-amber-950/30 border border-amber-800/50 text-amber-300 text-xs flex items-center gap-2">
              <Shield className="w-4 h-4 text-amber-400 shrink-0" />
              <span>
                Before any write or edit action, ARYx automatically preserves a timestamped snapshot in `~/.aryx/snapshots/`.
                Type `/revert` in the chat anytime to restore previous versions!
              </span>
            </div>

            <div className="space-y-2">
              {snapshots.map((snap) => (
                <div
                  key={snap.id}
                  className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex items-center justify-between gap-4"
                >
                  <div className="flex items-center gap-3 font-mono text-xs">
                    <FileCode className="w-4 h-4 text-yellow-400" />
                    <div>
                      <div className="font-semibold text-slate-200">{snap.file}</div>
                      <div className="text-[11px] text-slate-400">{snap.timestamp} · {snap.size}</div>
                    </div>
                  </div>

                  <button
                    onClick={() => handleRevertSnapshot(snap)}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition flex items-center gap-1.5"
                  >
                    <RotateCcw className="w-3.5 h-3.5 text-amber-400" />
                    Revert File
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

import React, { useState } from 'react';
import {
  BookOpen,
  Terminal,
  ExternalLink,
  Copy,
  Check,
  CheckCircle2,
  ShieldCheck,
  Cpu,
  Key,
  HelpCircle,
  Sparkles,
} from 'lucide-react';

export default function QuickstartDocs() {
  const [copiedClone, setCopiedClone] = useState(false);
  const [copiedInstall, setCopiedInstall] = useState(false);

  const cloneCmd = 'git clone https://github.com/aryx-agent/aryx-agent && cd aryx-agent && ./install.sh && aryx';
  const installCmd = './install.sh';

  const handleCopy = (text: string, type: 'clone' | 'install') => {
    navigator.clipboard.writeText(text);
    if (type === 'clone') {
      setCopiedClone(true);
      setTimeout(() => setCopiedClone(false), 2000);
    } else {
      setCopiedInstall(true);
      setTimeout(() => setCopiedInstall(false), 2000);
    }
  };

  const providers = [
    {
      name: 'Google Gemini',
      prefix: 'AIza...',
      freeTier: 'Yes (Generous)',
      link: 'https://aistudio.google.com/apikey',
      model: 'gemini-2.5-flash',
      desc: 'Recommended default. Blazing fast, huge context window, superior tool-calling.',
    },
    {
      name: 'Groq',
      prefix: 'gsk_...',
      freeTier: 'Yes',
      link: 'https://console.groq.com/keys',
      model: 'llama-3.3-70b',
      desc: 'Extreme sub-second inference speeds powered by LPUs.',
    },
    {
      name: 'Ollama',
      prefix: '(None required)',
      freeTier: '100% Offline / Free',
      link: 'https://ollama.com',
      model: 'llama3.2',
      desc: 'Completely private and offline on your local GPU/CPU.',
    },
    {
      name: 'OpenAI',
      prefix: 'sk-...',
      freeTier: 'Paid / Trial',
      link: 'https://platform.openai.com/api-keys',
      model: 'gpt-4.1-mini',
      desc: 'Standard GPT-4o and mini models with reliable code reasoning.',
    },
    {
      name: 'Anthropic Claude',
      prefix: 'sk-ant-...',
      freeTier: 'Paid',
      link: 'https://console.anthropic.com/settings/keys',
      model: 'claude-sonnet-4',
      desc: 'Industry-leading code generation and nuanced architecture planning.',
    },
    {
      name: 'OpenRouter',
      prefix: 'sk-or-...',
      freeTier: 'Unified API',
      link: 'https://openrouter.ai/keys',
      model: 'anthropic/claude-3.5-sonnet',
      desc: 'Single key accessing 200+ state of the art models worldwide.',
    },
  ];

  const tools = [
    { name: 'read_file', type: 'READ-ONLY', desc: 'Read file contents up to 500 lines without approval.' },
    { name: 'list_dir', type: 'READ-ONLY', desc: 'List files and directories flat or recursively.' },
    { name: 'glob', type: 'READ-ONLY', desc: 'Locate files matching glob patterns like **/*.py.' },
    { name: 'grep', type: 'READ-ONLY', desc: 'Search file contents using regex or substrings.' },
    { name: 'web_fetch', type: 'READ-ONLY', desc: 'Extract clean markdown/text from web pages.' },
    { name: 'web_search', type: 'READ-ONLY', desc: 'Real-time query of technical docs and answers.' },
    { name: 'write_file', type: 'WRITE', desc: 'Create or overwrite files with automatic pre-write snapshot.' },
    { name: 'edit_file', type: 'WRITE', desc: 'Surgically replace unique text blocks with snapshotting.' },
    { name: 'bash', type: 'WRITE', desc: 'Sandboxed shell command with 30s timeout and safety blocklist.' },
    { name: 'python', type: 'WRITE', desc: 'Sandboxed Python runner in isolated child process.' },
  ];

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl border border-slate-800 shadow-xl overflow-y-auto p-6 space-y-8">
      {/* Hero Quickstart */}
      <div className="space-y-4">
        <div className="flex items-center gap-2 text-cyan-400 text-xs font-bold uppercase tracking-wider">
          <Sparkles className="w-4 h-4" />
          The 30-Second Zero-Friction Promise
        </div>
        <h2 className="text-2xl font-bold text-slate-100">Quickstart &amp; Setup Guide</h2>
        <p className="text-sm text-slate-300 leading-relaxed max-w-3xl">
          ARYx AGENT was engineered with one priority: <strong>ZERO FRICTION</strong>.
          You clone the repository, run one command, paste any API key, and you are chatting within 30 seconds.
          No missing help. No silent failures. No tracebacks.
        </p>

        {/* 1-Line Install Box */}
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
          <div className="text-xs text-slate-400 font-semibold flex items-center justify-between">
            <span>Terminal Command (Copy &amp; Paste):</span>
            <button
              onClick={() => handleCopy(cloneCmd, 'clone')}
              className="text-cyan-400 hover:text-cyan-300 transition flex items-center gap-1 text-xs"
            >
              {copiedClone ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              {copiedClone ? 'Copied!' : 'Copy Command'}
            </button>
          </div>
          <pre className="p-3 rounded-lg bg-slate-900 font-mono text-xs text-emerald-400 overflow-x-auto select-all">
            {cloneCmd}
          </pre>
        </div>
      </div>

      {/* 4 Steps Visual */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
          <div className="w-7 h-7 rounded-full bg-cyan-950 border border-cyan-800 text-cyan-400 font-bold text-xs flex items-center justify-center">
            1
          </div>
          <h3 className="text-sm font-bold text-slate-200">One-Command Install</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            <code className="text-slate-300">./install.sh</code> checks OS, ensures Python 3.10+, installs via pipx, and adds to PATH safely.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
          <div className="w-7 h-7 rounded-full bg-cyan-950 border border-cyan-800 text-cyan-400 font-bold text-xs flex items-center justify-center">
            2
          </div>
          <h3 className="text-sm font-bold text-slate-200">One-Question Setup</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Run <code className="text-slate-300">aryx</code>. Paste any key. Key prefixes auto-detect Gemini, OpenAI, Claude, or Groq.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
          <div className="w-7 h-7 rounded-full bg-cyan-950 border border-cyan-800 text-cyan-400 font-bold text-xs flex items-center justify-center">
            3
          </div>
          <h3 className="text-sm font-bold text-slate-200">5-Token Probe</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Validates instantly with a tiny 5-token call. If invalid, gives exact actionable URL without tracebacks.
          </p>
        </div>

        <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-2">
          <div className="w-7 h-7 rounded-full bg-cyan-950 border border-cyan-800 text-cyan-400 font-bold text-xs flex items-center justify-center">
            4
          </div>
          <h3 className="text-sm font-bold text-slate-200">Start Chatting</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Drops directly into <code className="text-slate-300">aryx &gt;</code>. File writes are snapshotted; memory persists in SQLite.
          </p>
        </div>
      </div>

      {/* Providers Table */}
      <div className="space-y-4">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <Key className="w-5 h-5 text-cyan-400" />
          Supported Providers &amp; Key Links
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {providers.map((p) => (
            <div key={p.name} className="p-4 rounded-xl bg-slate-950 border border-slate-800 flex flex-col justify-between space-y-3">
              <div>
                <div className="flex items-center justify-between">
                  <h4 className="text-sm font-bold text-slate-100">{p.name}</h4>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 text-slate-300 border border-slate-700">
                    {p.freeTier}
                  </span>
                </div>
                <div className="text-xs font-mono text-cyan-400 mt-1">Prefix: {p.prefix}</div>
                <p className="text-xs text-slate-400 mt-2 leading-relaxed">{p.desc}</p>
              </div>

              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs">
                <span className="text-slate-500 font-mono text-[11px]">{p.model}</span>
                <a
                  href={p.link}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold"
                >
                  Get Key <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Built-in Tools Matrix */}
      <div className="space-y-4">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <Cpu className="w-5 h-5 text-emerald-400" />
          Native Built-in Tools
        </h3>

        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950">
          <table className="w-full text-xs text-left">
            <thead className="bg-slate-900 text-slate-400 uppercase font-mono text-[11px] border-b border-slate-800">
              <tr>
                <th className="px-4 py-3">Tool</th>
                <th className="px-4 py-3">Classification</th>
                <th className="px-4 py-3">Safety &amp; Execution Behavior</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/80 font-mono">
              {tools.map((t) => (
                <tr key={t.name} className="hover:bg-slate-900/40">
                  <td className="px-4 py-2.5 font-bold text-slate-200">{t.name}</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-semibold ${
                        t.type === 'READ-ONLY'
                          ? 'bg-blue-950 text-blue-300 border border-blue-800'
                          : 'bg-amber-950 text-amber-300 border border-amber-800'
                      }`}
                    >
                      {t.type}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-slate-300 font-sans">{t.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Troubleshooting FAQ */}
      <div className="space-y-4">
        <h3 className="text-lg font-bold text-slate-100 flex items-center gap-2">
          <HelpCircle className="w-5 h-5 text-amber-400" />
          Frequently Asked Questions &amp; Troubleshooting
        </h3>

        <div className="space-y-3">
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <h4 className="text-xs font-bold text-slate-200">Q: `command not found: aryx`?</h4>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Add <code className="text-cyan-300 font-mono">~/.local/bin</code> to your PATH:
              <br />
              <code className="text-emerald-400 font-mono">export PATH=&quot;$HOME/.local/bin:$PATH&quot;</code>
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <h4 className="text-xs font-bold text-slate-200">Q: Key rejected or extra spaces?</h4>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Run <code className="text-cyan-300 font-mono">aryx doctor --fix</code> or type{' '}
              <code className="text-cyan-300 font-mono">/model add</code> in chat to update credentials with live validation.
            </p>
          </div>

          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-1">
            <h4 className="text-xs font-bold text-slate-200">Q: How does /revert work?</h4>
            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Whenever ARYx modifies or writes a file, a copy is automatically placed in{' '}
              <code className="text-cyan-300 font-mono">~/.aryx/snapshots/</code>. Typing{' '}
              <code className="text-cyan-300 font-mono">/revert</code> restores the previous version without losing state.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

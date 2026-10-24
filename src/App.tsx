import React, { useState } from 'react';
import {
  Terminal as TerminalIcon,
  FolderGit2,
  Stethoscope,
  Database,
  BookOpen,
  Download,
  Shield,
  Zap,
  Check,
  Copy,
  Key,
  ExternalLink,
} from 'lucide-react';

import Terminal from './components/Terminal';
import RepoExplorer from './components/RepoExplorer';
import DoctorDashboard from './components/DoctorDashboard';
import MemorySkillsView from './components/MemorySkillsView';
import QuickstartDocs from './components/QuickstartDocs';

export default function App() {
  const [activeTab, setActiveTab] = useState<'terminal' | 'repo' | 'doctor' | 'memory' | 'docs'>('terminal');
  const [apiKey, setApiKey] = useState('');
  const [activeProvider, setActiveProvider] = useState('gemini');
  const [approvalMode, setApprovalMode] = useState<'safe' | 'yolo'>('safe');
  const [showKeyModal, setShowKeyModal] = useState(false);
  const [tempKey, setTempKey] = useState('');
  const [keyValidationMessage, setKeyValidationMessage] = useState<string | null>(null);
  const [copiedClone, setCopiedClone] = useState(false);

  const handleCopyClone = () => {
    navigator.clipboard.writeText('git clone https://github.com/aryx-agent/aryx-agent && cd aryx-agent && ./install.sh && aryx');
    setCopiedClone(true);
    setTimeout(() => setCopiedClone(false), 2000);
  };

  const handleSaveKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tempKey.trim()) return;

    try {
      const res = await fetch('/api/validate-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key: tempKey.trim() }),
      });
      const data = await res.json();
      if (data.valid) {
        setApiKey(tempKey.trim());
        setActiveProvider(data.provider || 'gemini');
        setKeyValidationMessage(`✓ Connected to ${data.name || data.provider} successfully!`);
        setTimeout(() => {
          setShowKeyModal(false);
          setKeyValidationMessage(null);
        }, 1200);
      } else {
        setKeyValidationMessage(`✗ ${data.message || 'Key validation failed'}`);
      }
    } catch (err: any) {
      setKeyValidationMessage(`✗ Connection error: ${err.message}`);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-slate-950 text-slate-100 font-sans select-none overflow-hidden">
      {/* Top Main Navigation Bar */}
      <header className="flex items-center justify-between px-5 py-3 bg-slate-900 border-b border-slate-800 z-10 shrink-0">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5 cursor-pointer" onClick={() => setActiveTab('terminal')}>
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-600 to-blue-500 flex items-center justify-center shadow-lg shadow-cyan-900/40">
              <TerminalIcon className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-extrabold text-sm tracking-wider text-slate-100">ARYx AGENT</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-400 border border-cyan-800 font-semibold">
                  v0.1.0
                </span>
              </div>
              <p className="text-[10px] text-slate-400 font-mono hidden sm:block">Zero-Friction Terminal AI Agent</p>
            </div>
          </div>

          {/* Tab Navigation */}
          <nav className="flex items-center gap-1 bg-slate-950 p-1 rounded-lg border border-slate-800/80 ml-2">
            <button
              onClick={() => setActiveTab('terminal')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'terminal'
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/80 shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <TerminalIcon className="w-3.5 h-3.5" />
              Live Terminal
            </button>

            <button
              onClick={() => setActiveTab('repo')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'repo'
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/80 shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <FolderGit2 className="w-3.5 h-3.5" />
              Repository
            </button>

            <button
              onClick={() => setActiveTab('doctor')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'doctor'
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/80 shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Stethoscope className="w-3.5 h-3.5" />
              Doctor
            </button>

            <button
              onClick={() => setActiveTab('memory')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'memory'
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/80 shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <Database className="w-3.5 h-3.5" />
              Memory &amp; Skills
            </button>

            <button
              onClick={() => setActiveTab('docs')}
              className={`px-3 py-1.5 rounded-md text-xs font-semibold transition flex items-center gap-1.5 ${
                activeTab === 'docs'
                  ? 'bg-cyan-950 text-cyan-300 border border-cyan-800/80 shadow'
                  : 'text-slate-400 hover:text-slate-200'
              }`}
            >
              <BookOpen className="w-3.5 h-3.5" />
              Docs &amp; Setup
            </button>
          </nav>
        </div>

        {/* Action Controls & Provider Indicator */}
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setShowKeyModal(true)}
            className="px-2.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition flex items-center gap-1.5"
            title="Configure or switch API provider key"
          >
            <Key className="w-3.5 h-3.5 text-cyan-400" />
            <span className="capitalize">{activeProvider}</span>
            <span className="text-[10px] text-slate-400">
              {apiKey ? `(${apiKey.slice(0, 4)}...)` : '(injected key ready)'}
            </span>
          </button>

          <button
            onClick={handleCopyClone}
            className="hidden md:flex px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition items-center gap-1.5"
          >
            {copiedClone ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
            Copy Clone
          </button>

          <a
            href="/api/repo/download"
            className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow transition flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Download Repo</span>
          </a>
        </div>
      </header>

      {/* Main View Area */}
      <main className="flex-1 p-4 overflow-hidden">
        {activeTab === 'terminal' && (
          <Terminal
            apiKey={apiKey}
            setApiKey={setApiKey}
            activeProvider={activeProvider}
            setActiveProvider={setActiveProvider}
            approvalMode={approvalMode}
            setApprovalMode={setApprovalMode}
            onNavigateTab={(tab) => setActiveTab(tab as any)}
          />
        )}

        {activeTab === 'repo' && <RepoExplorer />}

        {activeTab === 'doctor' && <DoctorDashboard />}

        {activeTab === 'memory' && <MemorySkillsView />}

        {activeTab === 'docs' && <QuickstartDocs />}
      </main>

      {/* Modal: Set Custom API Key */}
      {showKeyModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl p-6 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-bold text-slate-100 flex items-center gap-2">
                <Key className="w-4 h-4 text-cyan-400" />
                Configure Provider API Key
              </h3>
              <button
                onClick={() => setShowKeyModal(false)}
                className="text-slate-400 hover:text-slate-200 text-xs"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-300 leading-relaxed">
              Paste any API key. ARYx auto-detects the provider from the key prefix:
              <br />
              <span className="text-cyan-400 font-mono text-[11px]">
                AIza... (Gemini) · sk-ant-... (Claude) · sk-... (OpenAI) · gsk_... (Groq)
              </span>
            </p>

            <form onSubmit={handleSaveKey} className="space-y-3">
              <input
                type="text"
                value={tempKey}
                onChange={(e) => setTempKey(e.target.value)}
                placeholder="Paste API key here (e.g. AIzaSy... or sk-...)"
                className="w-full px-3.5 py-2.5 rounded-lg bg-slate-950 border border-slate-700 text-xs font-mono text-slate-100 placeholder-slate-600 focus:outline-none focus:border-cyan-500"
                autoFocus
              />

              {keyValidationMessage && (
                <div
                  className={`text-xs p-2 rounded ${
                    keyValidationMessage.startsWith('✓')
                      ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-800'
                      : 'bg-rose-950/60 text-rose-300 border border-rose-800'
                  }`}
                >
                  {keyValidationMessage}
                </div>
              )}

              <div className="flex items-center justify-between pt-2">
                <a
                  href="https://aistudio.google.com/apikey"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs text-cyan-400 hover:underline flex items-center gap-1"
                >
                  Get free Gemini key <ExternalLink className="w-3 h-3" />
                </a>

                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      setApiKey('');
                      setActiveProvider('gemini');
                      setShowKeyModal(false);
                    }}
                    className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs"
                  >
                    Use Runtime Key
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow"
                  >
                    Validate &amp; Save
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

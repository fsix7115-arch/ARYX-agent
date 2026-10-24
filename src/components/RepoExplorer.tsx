import React, { useState, useEffect } from 'react';
import {
  Folder,
  FileCode,
  FileText,
  FileSpreadsheet,
  Download,
  Copy,
  Check,
  ExternalLink,
  Terminal,
  FolderOpen,
  ChevronRight,
  ChevronDown,
} from 'lucide-react';

interface RepoFile {
  path: string;
  relativePath: string;
  content: string;
  size: number;
}

export default function RepoExplorer() {
  const [files, setFiles] = useState<RepoFile[]>([]);
  const [selectedFile, setSelectedFile] = useState<RepoFile | null>(null);
  const [loading, setLoading] = useState(true);
  const [copied, setCopied] = useState(false);
  const [cloneCopied, setCloneCopied] = useState(false);

  useEffect(() => {
    fetch('/api/repo/files')
      .then((res) => res.json())
      .then((data) => {
        if (data.files && data.files.length > 0) {
          setFiles(data.files);
          // Default select README or install.sh
          const readme = data.files.find((f: RepoFile) => f.relativePath === 'README.md');
          setSelectedFile(readme || data.files[0]);
        }
      })
      .catch((err) => console.error(err))
      .finally(() => setLoading(false));
  }, []);

  const handleCopyCode = () => {
    if (!selectedFile) return;
    navigator.clipboard.writeText(selectedFile.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyClone = () => {
    navigator.clipboard.writeText('git clone https://github.com/aryx-agent/aryx-agent && cd aryx-agent && ./install.sh && aryx');
    setCloneCopied(true);
    setTimeout(() => setCloneCopied(false), 2000);
  };

  const getFileIcon = (rel: string) => {
    if (rel.endsWith('.py')) return <FileCode className="w-4 h-4 text-emerald-400" />;
    if (rel.endsWith('.sh')) return <Terminal className="w-4 h-4 text-yellow-400" />;
    if (rel.endsWith('.toml')) return <FileSpreadsheet className="w-4 h-4 text-orange-400" />;
    if (rel.endsWith('.md')) return <FileText className="w-4 h-4 text-cyan-400" />;
    return <FileText className="w-4 h-4 text-slate-400" />;
  };

  // Group files into folder tree
  const folders: { [key: string]: RepoFile[] } = {
    Root: [],
    'aryx/': [],
    'aryx/providers/': [],
    'aryx/tools/': [],
    'aryx/memory/': [],
    'aryx/ui/': [],
    'docs/': [],
    'tests/': [],
  };

  files.forEach((f) => {
    if (f.relativePath.startsWith('aryx/providers/')) folders['aryx/providers/'].push(f);
    else if (f.relativePath.startsWith('aryx/tools/')) folders['aryx/tools/'].push(f);
    else if (f.relativePath.startsWith('aryx/memory/')) folders['aryx/memory/'].push(f);
    else if (f.relativePath.startsWith('aryx/ui/')) folders['aryx/ui/'].push(f);
    else if (f.relativePath.startsWith('aryx/')) folders['aryx/'].push(f);
    else if (f.relativePath.startsWith('docs/')) folders['docs/'].push(f);
    else if (f.relativePath.startsWith('tests/')) folders['tests/'].push(f);
    else folders['Root'].push(f);
  });

  return (
    <div className="flex flex-col h-full bg-slate-900 rounded-xl border border-slate-800 shadow-xl overflow-hidden">
      {/* Header bar */}
      <div className="flex flex-wrap items-center justify-between px-5 py-3.5 bg-slate-950/80 border-b border-slate-800 gap-3">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-950 border border-cyan-800 flex items-center justify-center text-cyan-400">
            <FolderOpen className="w-4 h-4" />
          </div>
          <div>
            <h2 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              aryx-agent
              <span className="text-xs px-2 py-0.5 rounded-full bg-cyan-950 text-cyan-400 border border-cyan-800/80">
                v0.1.0 Ready for GitHub
              </span>
            </h2>
            <p className="text-xs text-slate-400">Complete zero-friction repository files</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleCopyClone}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-mono border border-slate-700 transition flex items-center gap-1.5"
          >
            {cloneCopied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-slate-400" />}
            Copy Clone Command
          </button>

          <a
            href="/api/repo/download"
            className="px-3.5 py-1.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold shadow-lg shadow-cyan-950/50 transition flex items-center gap-1.5"
          >
            <Download className="w-3.5 h-3.5" />
            Download .tar.gz
          </a>
        </div>
      </div>

      {/* Main split: Tree Explorer & Code Viewer */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Tree Explorer */}
        <div className="w-64 md:w-72 bg-slate-950/50 border-r border-slate-800 overflow-y-auto p-3 text-xs select-none">
          <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 px-2">
            Repository Structure ({files.length} files)
          </div>

          {loading ? (
            <div className="p-4 text-slate-500">Scanning repository...</div>
          ) : (
            <div className="space-y-3">
              {Object.entries(folders).map(([folderName, folderFiles]) => {
                if (folderFiles.length === 0) return null;
                return (
                  <div key={folderName} className="space-y-1">
                    <div className="flex items-center gap-1.5 text-slate-400 font-semibold px-2 py-1">
                      <Folder className="w-3.5 h-3.5 text-cyan-400" />
                      <span>{folderName}</span>
                    </div>

                    <div className="pl-3 space-y-0.5">
                      {folderFiles.map((file) => {
                        const isSelected = selectedFile?.relativePath === file.relativePath;
                        const fileName = file.relativePath.split('/').pop() || file.relativePath;
                        return (
                          <button
                            key={file.relativePath}
                            onClick={() => setSelectedFile(file)}
                            className={`w-full flex items-center justify-between px-2 py-1.5 rounded text-left transition font-mono ${
                              isSelected
                                ? 'bg-cyan-950/80 text-cyan-300 font-semibold border border-cyan-800/80'
                                : 'text-slate-300 hover:bg-slate-850 hover:text-white'
                            }`}
                          >
                            <span className="flex items-center gap-2 truncate">
                              {getFileIcon(file.relativePath)}
                              <span className="truncate">{fileName}</span>
                            </span>
                            <span className="text-[10px] text-slate-400 font-sans">
                              {(file.size / 1024).toFixed(1)}k
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Code Viewer */}
        <div className="flex-1 flex flex-col bg-slate-950 overflow-hidden">
          {selectedFile ? (
            <>
              {/* File header bar */}
              <div className="flex items-center justify-between px-4 py-2.5 bg-slate-900 border-b border-slate-800">
                <div className="flex items-center gap-2 font-mono text-xs text-slate-200">
                  {getFileIcon(selectedFile.relativePath)}
                  <span className="font-semibold text-slate-100">{selectedFile.relativePath}</span>
                  <span className="text-slate-400 font-sans text-[11px]">
                    ({(selectedFile.size / 1024).toFixed(2)} KB · {selectedFile.content.split('\n').length} lines)
                  </span>
                </div>

                <button
                  onClick={handleCopyCode}
                  className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono transition flex items-center gap-1.5 border border-slate-700"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  {copied ? 'Copied' : 'Copy'}
                </button>
              </div>

              {/* Code text display with line numbers */}
              <div className="flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed text-slate-200 bg-slate-950 selection:bg-cyan-900/40">
                <table className="w-full border-collapse">
                  <tbody>
                    {selectedFile.content.split('\n').map((line, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/50">
                        <td className="w-10 pr-4 text-right text-slate-400 select-none text-[11px] align-top">
                          {idx + 1}
                        </td>
                        <td className="whitespace-pre overflow-x-auto text-slate-200 font-mono">
                          {line || ' '}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-400 text-sm">
              Select a file from the tree to preview its source code.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

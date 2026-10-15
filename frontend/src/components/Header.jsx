import React from 'react';
import { Disc3, Cpu, RefreshCw, AlertCircle, CheckCircle2 } from 'lucide-react';

export default function Header({ aiStatus, onRefreshStatus, checkingStatus }) {
  const isConnected = aiStatus?.status === 'connected';
  const isDisconnected = aiStatus?.status === 'disconnected';
  const modelName = aiStatus?.configured_model || 'qwen3:1.7b';

  return (
    <header className="border-b border-slate-800/80 bg-[#0c0c14]/90 sticky top-0 z-40 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-3.5 flex flex-col sm:flex-row items-center justify-between gap-3">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 via-indigo-600 to-cyan-500 shadow-lg shadow-purple-950/40 border border-purple-400/20">
            <Disc3 className="w-6 h-6 text-white animate-spin-slow" />
            <div className="absolute -top-1 -right-1 w-3 h-3 rounded-full bg-cyan-400 blur-[2px] opacity-70"></div>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold font-['Outfit'] tracking-tight bg-gradient-to-r from-white via-slate-100 to-purple-200 bg-clip-text text-transparent">
                SoundDeck Studio
              </h1>
              <span className="text-[10px] font-semibold tracking-wider uppercase px-2 py-0.5 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/20">
                v0.7.0
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium">
              Local AI Music Curation &middot; <span className="text-slate-500">Your AI-powered playlist preparation workspace</span>
            </p>
          </div>
        </div>

        {/* AI Model Status Badge */}
        <div className="flex items-center gap-2 bg-slate-900/90 border border-slate-800/80 rounded-full px-3.5 py-1.5 shadow-inner">
          <Cpu className="w-3.5 h-3.5 text-slate-400" />
          
          {checkingStatus ? (
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <span className="w-2 h-2 rounded-full bg-slate-500 animate-pulse"></span>
              <span>Checking AI status...</span>
            </div>
          ) : isConnected ? (
            <div className="flex items-center gap-2 text-xs">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
              </span>
              <span className="font-medium text-emerald-300">
                Ollama: <span className="font-semibold text-white">{modelName}</span>
              </span>
              <span className="text-[10px] text-emerald-400/80 bg-emerald-500/10 px-1.5 py-0.5 rounded">Ready</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs">
              <span className="h-2 w-2 rounded-full bg-rose-500"></span>
              <span className="font-medium text-rose-300">Ollama Offline</span>
              <span className="text-[10px] text-rose-400/80 bg-rose-500/10 px-1.5 py-0.5 rounded">503</span>
            </div>
          )}

          <button
            onClick={onRefreshStatus}
            disabled={checkingStatus}
            title="Refresh Ollama status"
            className="text-slate-400 hover:text-slate-200 p-1 rounded-full hover:bg-slate-800/80 transition-colors ml-1 disabled:opacity-50"
          >
            <RefreshCw className={`w-3 h-3 ${checkingStatus ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
}

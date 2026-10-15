import React from 'react';
import { AlertCircle, Terminal, X, WifiOff } from 'lucide-react';

export default function ErrorAlert({ error, onDismiss }) {
  if (!error) return null;

  const isOllamaError =
    error.status === 503 ||
    error.detail?.toLowerCase().includes('ollama') ||
    error.message?.toLowerCase().includes('ollama');

  const isTimeout =
    error.status === 504 ||
    error.detail?.toLowerCase().includes('timed out');

  return (
    <div className="rounded-xl bg-rose-950/40 border border-rose-800/60 p-4 text-sm text-rose-200 shadow-lg relative animate-in fade-in duration-200">
      <div className="flex items-start gap-3">
        {isOllamaError ? (
          <WifiOff className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
        ) : (
          <AlertCircle className="w-5 h-5 text-rose-400 shrink-0 mt-0.5" />
        )}

        <div className="space-y-1.5 flex-1 pr-6">
          <div className="font-semibold text-rose-100 flex items-center gap-2">
            <span>{isOllamaError ? 'Local AI Service Offline' : isTimeout ? 'Request Timed Out' : 'Curation Request Failed'}</span>
            {error.status && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-rose-900/60 text-rose-300 border border-rose-700/50">
                HTTP {error.status}
              </span>
            )}
          </div>

          <p className="text-xs text-rose-200/90">
            {error.detail || error.message || 'An unexpected error occurred during playlist generation.'}
          </p>

          {isOllamaError && (
            <div className="mt-2 pt-2 border-t border-rose-900/50 space-y-1 text-xs">
              <div className="text-rose-300 font-medium">To resolve:</div>
              <div className="bg-[#0b0b14] border border-rose-900/40 rounded-lg p-2 font-mono text-[11px] text-slate-300 flex items-center gap-2">
                <Terminal className="w-3.5 h-3.5 text-rose-400 shrink-0" />
                <span>ollama serve</span>
              </div>
              <div className="text-[11px] text-rose-300/80">
                Ensure the model is installed: <code className="bg-rose-900/40 px-1 py-0.5 rounded text-white">ollama pull qwen3:1.7b</code>
              </div>
            </div>
          )}
        </div>

        {onDismiss && (
          <button
            onClick={onDismiss}
            className="text-rose-400 hover:text-rose-200 p-1 rounded-lg hover:bg-rose-900/40 transition-colors absolute top-3 right-3"
            title="Dismiss message"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

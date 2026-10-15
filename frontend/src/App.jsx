import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import PromptCreator from './components/PromptCreator';
import PlaylistView from './components/PlaylistView';
import AnalyticsDashboard from './components/AnalyticsDashboard';
import ErrorAlert from './components/ErrorAlert';
import { fetchAiStatus, curatePlaylist, exportPlaylistCsv } from './api/client';
import {
  Disc,
  Sparkles,
  Sliders,
  FileSpreadsheet,
  Layers,
  BarChart3,
  CheckCircle2,
  ListMusic,
  ExternalLink,
} from 'lucide-react';

export default function App() {
  const [aiStatus, setAiStatus] = useState(null);
  const [checkingStatus, setCheckingStatus] = useState(false);

  const [prompt, setPrompt] = useState(
    'Create a calm indie playlist for late-night studying. Include acoustic tracks, start with Lord Huron, and avoid repeating artists.'
  );
  const [limit, setLimit] = useState(20);
  const [maxPerArtist, setMaxPerArtist] = useState(2);
  const [diversityWeight, setDiversityWeight] = useState(0.2);

  const [isGenerating, setIsGenerating] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [error, setError] = useState(null);
  const [playlistData, setPlaylistData] = useState(null);
  const [toastMessage, setToastMessage] = useState(null);
  const [activeTab, setActiveTab] = useState('tracks'); // 'tracks' | 'analytics'

  // Fetch AI status on mount
  const checkStatus = async () => {
    setCheckingStatus(true);
    try {
      const data = await fetchAiStatus();
      setAiStatus(data);
    } catch (err) {
      setAiStatus({ status: 'disconnected', error: err.message });
    } finally {
      setCheckingStatus(false);
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  const handleGenerate = async () => {
    if (!prompt.trim() || isGenerating) return;

    setIsGenerating(true);
    setError(null);

    try {
      const data = await curatePlaylist({
        prompt,
        limit,
        maxPerArtist,
        diversityWeight,
      });
      setPlaylistData(data);
      // Auto-switch to tracks tab
      setActiveTab('tracks');
    } catch (err) {
      console.error('Curation error:', err);
      setError({
        status: err.status,
        detail: err.detail || err.message,
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const handleExportCsv = async () => {
    if (!playlistData || isExporting) return;

    setIsExporting(true);
    setError(null);

    try {
      const { blob, filename } = await exportPlaylistCsv({
        playlistId: playlistData.playlist_id,
        tracks: playlistData.tracks,
      });

      // Trigger browser file download
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);

      showToast(`Exported "${filename}" successfully with formula injection protection.`);
    } catch (err) {
      console.error('Export error:', err);
      setError({
        detail: `CSV Export failed: ${err.message}`,
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleReset = () => {
    setPrompt('');
    setError(null);
  };

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 4500);
  };

  return (
    <div className="min-h-screen bg-[#09090e] text-slate-100 flex flex-col font-['Inter']">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-2 px-4 py-3 rounded-xl bg-purple-950/90 border border-purple-500/50 text-purple-100 text-xs shadow-2xl backdrop-blur-md animate-in slide-in-from-bottom-3 duration-200">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header */}
      <Header
        aiStatus={aiStatus}
        onRefreshStatus={checkStatus}
        checkingStatus={checkingStatus}
      />

      {/* Main Container */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
        {/* Error Alert Banner */}
        {error && <ErrorAlert error={error} onDismiss={() => setError(null)} />}

        {/* AI Playlist Creator */}
        <PromptCreator
          prompt={prompt}
          setPrompt={setPrompt}
          limit={limit}
          setLimit={setLimit}
          maxPerArtist={maxPerArtist}
          setMaxPerArtist={setMaxPerArtist}
          diversityWeight={diversityWeight}
          setDiversityWeight={setDiversityWeight}
          onGenerate={handleGenerate}
          isGenerating={isGenerating}
          onReset={handleReset}
        />

        {/* Results Navigation Tabs (when playlist generated) */}
        {playlistData && (
          <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
            <div className="flex items-center gap-2">
              <button
                onClick={() => setActiveTab('tracks')}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === 'tracks'
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-900/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <ListMusic className="w-4 h-4" />
                <span>Tracklist ({playlistData.tracks?.length || 0})</span>
              </button>

              <button
                onClick={() => setActiveTab('analytics')}
                className={`flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-semibold transition-all ${
                  activeTab === 'analytics'
                    ? 'bg-purple-600 text-white shadow-lg shadow-purple-900/40'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <BarChart3 className="w-4 h-4" />
                <span>Analytics Dashboard</span>
              </button>
            </div>

            <button
              onClick={handleExportCsv}
              disabled={isExporting}
              className="hidden sm:flex items-center gap-2 text-xs font-medium text-slate-300 hover:text-cyan-300 bg-slate-900 hover:bg-slate-850 px-3.5 py-1.5 rounded-lg border border-slate-800 hover:border-cyan-500/40 transition-all"
            >
              <FileSpreadsheet className="w-3.5 h-3.5 text-cyan-400" />
              <span>Export CSV</span>
            </button>
          </div>
        )}

        {/* Active Content View */}
        {playlistData ? (
          <div>
            {activeTab === 'tracks' ? (
              <PlaylistView
                playlistData={playlistData}
                onExportCsv={handleExportCsv}
                isExporting={isExporting}
              />
            ) : (
              <AnalyticsDashboard analytics={playlistData.analytics} />
            )}
          </div>
        ) : (
          /* Empty / Getting Started State */
          <div className="glass-panel-subtle rounded-2xl p-8 sm:p-12 text-center space-y-6 max-w-3xl mx-auto border border-dashed border-slate-800/80">
            <div className="w-14 h-14 rounded-2xl bg-gradient-to-tr from-purple-900/60 to-cyan-900/40 border border-purple-500/30 flex items-center justify-center mx-auto shadow-inner text-purple-300">
              <Disc className="w-7 h-7" />
            </div>

            <div className="space-y-2">
              <h3 className="text-lg font-semibold font-['Outfit'] text-white">
                No Playlist Curated Yet
              </h3>
              <p className="text-xs text-slate-400 max-w-md mx-auto leading-relaxed">
                Enter your prompt above or click one of the suggested templates. SoundDeck Studio will
                interpret your musical constraints using the local Qwen 1.7B LLM and generate a ranked playlist using Last.fm similarity and hybrid scoring.
              </p>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2 text-left">
              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/60 space-y-1">
                <div className="text-xs font-semibold text-purple-300 flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                  <span>1. Local AI Reasoning</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Parses genres, moods, seeds, and diversity preferences locally with zero cloud dependencies.
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/60 space-y-1">
                <div className="text-xs font-semibold text-cyan-300 flex items-center gap-1.5">
                  <Sliders className="w-3.5 h-3.5 text-cyan-400" />
                  <span>2. Hybrid Scoring</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Ranks tracks by acoustic Last.fm similarity (60%), genre matching (20%), and mood profile (15%).
                </p>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800/60 space-y-1">
                <div className="text-xs font-semibold text-emerald-300 flex items-center gap-1.5">
                  <FileSpreadsheet className="w-3.5 h-3.5 text-emerald-400" />
                  <span>3. Production Export</span>
                </div>
                <p className="text-[11px] text-slate-400">
                  Download sanitized CSV files with full scores, explanations, and spreadsheet formula-injection protection.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#07070b] py-6 text-center text-xs text-slate-500 mt-12">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-semibold text-slate-400">SoundDeck Studio</span>
            <span>&middot;</span>
            <span>Local AI Music Curation System</span>
          </div>
          <div className="text-[11px] text-slate-500">
            Powered by Ollama, Qwen 1.7B, Last.fm & MusicBrainz
          </div>
        </div>
      </footer>
    </div>
  );
}

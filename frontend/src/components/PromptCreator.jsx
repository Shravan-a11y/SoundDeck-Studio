import React, { useState } from 'react';
import { Sparkles, SlidersHorizontal, RotateCcw, Play, Music, Flame, Coffee, Compass } from 'lucide-react';

const EXAMPLE_PROMPTS = [
  {
    icon: Flame,
    title: "Sunset Rooftop Party",
    prompt: "Create a 15-track indie and electronic playlist for a rooftop sunset party. Start relaxed and gradually increase the energy. Avoid repeating artists.",
    limit: 15,
  },
  {
    icon: Coffee,
    title: "Late-Night Studying",
    prompt: "Create a calm indie playlist for late-night studying. Include acoustic tracks, start with Lord Huron, and avoid repeating artists.",
    limit: 15,
  },
  {
    icon: Compass,
    title: "Deep Focus Ambient",
    prompt: "Build a 12-track ambient and post-rock playlist for deep focus. Emphasize peaceful dreamy vibes with max artist diversity.",
    limit: 12,
  },
  {
    icon: Music,
    title: "Acoustic Folk Roadtrip",
    prompt: "Curate an 18-track folk rock and indie folk playlist for an autumn road trip. Keep it mellow and soulful.",
    limit: 18,
  },
];

export default function PromptCreator({
  prompt,
  setPrompt,
  limit,
  setLimit,
  maxPerArtist,
  setMaxPerArtist,
  diversityWeight,
  setDiversityWeight,
  onGenerate,
  isGenerating,
  onReset,
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSelectExample = (ex) => {
    setPrompt(ex.prompt);
    if (ex.limit) setLimit(ex.limit);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!prompt.trim() || isGenerating) return;
    onGenerate();
  };

  return (
    <div className="glass-panel rounded-2xl p-6 sm:p-7 glow-purple transition-all duration-300">
      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Header & Controls */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <h2 className="text-lg font-semibold font-['Outfit'] text-white flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-purple-400" />
              AI Playlist Curation Workspace
            </h2>
            <p className="text-xs text-slate-400">
              Describe your mood, vibe, genre blend, or seed artist in natural language.
            </p>
          </div>

          <div className="flex items-center gap-2 self-end sm:self-auto">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className={`flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg border transition-all ${
                showAdvanced
                  ? 'bg-purple-950/40 text-purple-300 border-purple-500/40'
                  : 'bg-slate-900/60 text-slate-400 border-slate-800 hover:text-slate-300'
              }`}
            >
              <SlidersHorizontal className="w-3.5 h-3.5" />
              <span>{showAdvanced ? 'Hide Options' : 'Tune Settings'}</span>
            </button>

            {prompt && (
              <button
                type="button"
                onClick={onReset}
                disabled={isGenerating}
                className="flex items-center gap-1 text-xs text-slate-400 hover:text-rose-400 px-2 py-1.5 rounded-lg hover:bg-slate-800/60 transition-colors"
                title="Clear prompt and reset"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset</span>
              </button>
            )}
          </div>
        </div>

        {/* Prompt Textarea */}
        <div className="relative">
          <textarea
            id="playlist-prompt-input"
            rows={3}
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            disabled={isGenerating}
            placeholder="Create a 15-track indie and electronic playlist for a rooftop sunset party. Start relaxed and gradually increase the energy. Avoid repeating artists."
            className="w-full bg-[#0e0e18] border border-slate-800/90 rounded-xl px-4 py-3.5 text-slate-100 placeholder:text-slate-500 text-sm focus:outline-none focus:border-purple-500/70 focus:ring-2 focus:ring-purple-500/20 transition-all resize-y min-h-[90px] disabled:opacity-50"
          />
        </div>

        {/* Advanced Settings Drawer */}
        {showAdvanced && (
          <div className="p-4 rounded-xl bg-slate-900/70 border border-slate-800/80 grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs animate-in fade-in duration-200">
            {/* Track Limit */}
            <div className="space-y-1.5">
              <div className="flex justify-between font-medium">
                <span className="text-slate-300">Playlist Size</span>
                <span className="text-purple-300 font-semibold">{limit} tracks</span>
              </div>
              <input
                type="range"
                min="5"
                max="50"
                step="1"
                value={limit}
                onChange={(e) => setLimit(Number(e.target.value))}
                disabled={isGenerating}
                className="w-full accent-purple-500 bg-slate-800 cursor-pointer h-1.5 rounded-lg"
              />
              <div className="flex justify-between text-[10px] text-slate-500">
                <span>5</span>
                <span>20 (Default)</span>
                <span>50</span>
              </div>
            </div>

            {/* Max Per Artist */}
            <div className="space-y-1.5">
              <div className="flex justify-between font-medium">
                <span className="text-slate-300">Max Per Artist</span>
                <span className="text-purple-300 font-semibold">{maxPerArtist} tracks</span>
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                {[1, 2, 3].map((val) => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => setMaxPerArtist(val)}
                    disabled={isGenerating}
                    className={`py-1 rounded text-center font-medium border transition-all ${
                      maxPerArtist === val
                        ? 'bg-purple-600/30 text-purple-200 border-purple-500/50'
                        : 'bg-slate-800/50 text-slate-400 border-slate-800 hover:bg-slate-800'
                    }`}
                  >
                    {val === 1 ? '1 (Strict)' : val === 2 ? '2 (Balanced)' : `${val} Max`}
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-slate-500">Prevents excessive artist repetition</p>
            </div>

            {/* Diversity Weight */}
            <div className="space-y-1.5">
              <div className="flex justify-between font-medium">
                <span className="text-slate-300">Diversity Penalty</span>
                <span className="text-purple-300 font-semibold">
                  {diversityWeight === 0.2 ? 'Subtle (0.2)' : diversityWeight === 0.5 ? 'Medium (0.5)' : 'High (0.8)'}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-1.5">
                {[
                  { label: 'Low', val: 0.2 },
                  { label: 'Medium', val: 0.5 },
                  { label: 'High', val: 0.8 },
                ].map(({ label, val }) => (
                  <button
                    key={val}
                    type="button"
                    onClick={() => setDiversityWeight(val)}
                    disabled={isGenerating}
                    className={`py-1 rounded text-center font-medium border transition-all ${
                      diversityWeight === val
                        ? 'bg-purple-600/30 text-purple-200 border-purple-500/50'
                        : 'bg-slate-800/50 text-slate-400 border-slate-800 hover:bg-slate-800'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
              <p className="text-[10px] text-slate-500">Score penalty applied to repeated artists</p>
            </div>
          </div>
        )}

        {/* Example Prompt Chips */}
        <div className="space-y-1.5">
          <span className="text-[11px] font-medium text-slate-400 tracking-wider uppercase">
            Suggested Prompts:
          </span>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.map((ex, i) => {
              const Icon = ex.icon;
              return (
                <button
                  key={i}
                  type="button"
                  onClick={() => handleSelectExample(ex)}
                  disabled={isGenerating}
                  className="flex items-center gap-1.5 text-xs text-slate-300 bg-slate-900/80 hover:bg-purple-950/30 hover:text-purple-200 border border-slate-800 hover:border-purple-500/40 px-3 py-1.5 rounded-full transition-all text-left disabled:opacity-50"
                >
                  <Icon className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                  <span>{ex.title}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Generate Button & Progress */}
        <div className="pt-2 flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 border-t border-slate-800/60">
          <div className="text-xs text-slate-400">
            {isGenerating ? (
              <span className="inline-flex items-center gap-2 text-purple-300 font-medium">
                <span className="w-2 h-2 rounded-full bg-purple-400 animate-ping"></span>
                Local AI analyzing request & curating tracks...
              </span>
            ) : (
              <span>Ready &middot; Connects local Qwen 1.7B with SoundDeck hybrid engine</span>
            )}
          </div>

          <button
            type="submit"
            id="generate-playlist-btn"
            disabled={!prompt.trim() || isGenerating}
            className="flex items-center justify-center gap-2 px-6 py-3 rounded-xl font-medium text-sm text-white bg-gradient-to-r from-purple-600 via-indigo-600 to-purple-700 hover:from-purple-500 hover:to-indigo-500 focus:outline-none focus:ring-2 focus:ring-purple-400/40 shadow-lg shadow-purple-950/40 disabled:opacity-50 disabled:cursor-not-allowed transition-all transform active:scale-[0.99]"
          >
            {isGenerating ? (
              <>
                <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                </svg>
                <span>Curating Playlist...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-4 h-4 text-purple-200" />
                <span>Curate Playlist</span>
              </>
            )}
          </button>
        </div>
      </form>
    </div>
  );
}

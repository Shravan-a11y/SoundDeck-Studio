import React from 'react';
import {
  BarChart3,
  Users,
  Repeat,
  Layers,
  Sparkles,
  Info,
  CheckCircle2,
  AlertTriangle,
  FileCheck2,
} from 'lucide-react';

export default function AnalyticsDashboard({ analytics }) {
  if (!analytics) return null;

  const {
    total_tracks = 0,
    unique_artists = 0,
    repetition_ratio = 0.0,
    metadata_coverage = 0.0,
    average_recommendation_score = null,
    duplicate_track_count = 0,
    genre_distribution = {},
    mood_distribution = {},
    unmet_constraints = [],
    notes = [],
  } = analytics;

  const genres = Object.entries(genre_distribution);
  const moods = Object.entries(mood_distribution);

  const maxGenreCount = genres.length > 0 ? Math.max(...genres.map(([, c]) => c)) : 1;
  const maxMoodCount = moods.length > 0 ? Math.max(...moods.map(([, c]) => c)) : 1;

  return (
    <div className="glass-panel rounded-2xl p-6 sm:p-7 glow-purple space-y-6">
      {/* Title */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-4 border-b border-slate-800/80">
        <div>
          <h2 className="text-xl font-bold font-['Outfit'] text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-purple-400" />
            Playlist Analytics & Diversity Audit
          </h2>
          <p className="text-xs text-slate-400">
            Calculated deterministically from actual track catalog metadata and scoring weights.
          </p>
        </div>

        <div className="flex items-center gap-2 self-start sm:self-auto text-xs font-mono text-purple-300 bg-purple-950/30 border border-purple-500/20 px-3 py-1 rounded-full">
          <FileCheck2 className="w-3.5 h-3.5 text-purple-400" />
          <span>Stage 4 Engine</span>
        </div>
      </div>

      {/* KPI Cards Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* KPI 1: Total Tracks & Uniques */}
        <div className="bg-slate-900/80 border border-slate-800/80 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Track Catalog</span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-white">{total_tracks}</div>
          <div className="text-[11px] text-slate-400">
            <span className="text-purple-300 font-semibold">{unique_artists}</span> unique artists
          </div>
        </div>

        {/* KPI 2: Repetition Ratio */}
        <div className="bg-slate-900/80 border border-slate-800/80 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Repetition Ratio</span>
            <Repeat className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-300">
            {(repetition_ratio * 100).toFixed(1)}%
          </div>
          <div className="text-[11px] text-slate-400">
            {repetition_ratio <= 0.1 ? 'High artist diversity' : repetition_ratio <= 0.3 ? 'Balanced repeat spread' : 'Curated repeat artist emphasis'}
          </div>
        </div>

        {/* KPI 3: Metadata Coverage */}
        <div className="bg-slate-900/80 border border-slate-800/80 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Metadata Coverage</span>
            <Users className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-300">
            {(metadata_coverage * 100).toFixed(0)}%
          </div>
          <div className="text-[11px] text-slate-400">
            Tracks with catalog tags
          </div>
        </div>

        {/* KPI 4: Mean Recommendation Score */}
        <div className="bg-slate-900/80 border border-slate-800/80 rounded-xl p-4 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span>Avg SoundDeck Score</span>
            <Sparkles className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-300">
            {average_recommendation_score !== null
              ? average_recommendation_score.toFixed(3)
              : 'N/A'}
          </div>
          <div className="text-[11px] text-slate-400">
            {duplicate_track_count === 0 ? 'Zero duplicates' : `${duplicate_track_count} duplicate detected`}
          </div>
        </div>
      </div>

      {/* Distributions Row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 pt-2">
        {/* Genre Distribution */}
        <div className="space-y-3 bg-[#0d0d17] border border-slate-800/80 rounded-xl p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center justify-between">
            <span>Genre Distribution</span>
            <span className="text-[11px] text-slate-500 font-normal">Last.fm Taxonomy</span>
          </h3>

          {genres.length > 0 ? (
            <div className="space-y-2.5">
              {genres.slice(0, 6).map(([genre, count], idx) => {
                const percent = Math.round((count / total_tracks) * 100);
                const barWidth = Math.round((count / maxGenreCount) * 100);

                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="capitalize text-slate-300 font-medium">{genre}</span>
                      <span className="text-slate-400 font-mono">
                        {count} <span className="text-slate-600">({percent}%)</span>
                      </span>
                    </div>
                    <div className="h-2 w-full bg-slate-800/80 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-500"
                        style={{ width: `${barWidth}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic py-4 text-center">
              No classified genre metadata available for these candidates.
            </p>
          )}
        </div>

        {/* Mood Distribution */}
        <div className="space-y-3 bg-[#0d0d17] border border-slate-800/80 rounded-xl p-4 sm:p-5">
          <h3 className="text-sm font-semibold text-slate-200 flex items-center justify-between">
            <span>Mood & Vibe Distribution</span>
            <span className="text-[11px] text-slate-500 font-normal">SoundDeck Intelligence</span>
          </h3>

          {moods.length > 0 ? (
            <div className="space-y-2.5">
              {moods.slice(0, 6).map(([mood, count], idx) => {
                const percent = Math.round((count / total_tracks) * 100);
                const barWidth = Math.round((count / maxMoodCount) * 100);

                return (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="capitalize text-slate-300 font-medium">{mood}</span>
                      <span className="text-slate-400 font-mono">
                        {count} <span className="text-slate-600">({percent}%)</span>
                      </span>
                    </div>
                    <div className="h-2 w-full bg-slate-800/80 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-teal-400 transition-all duration-500"
                        style={{ width: `${barWidth}%` }}
                      ></div>
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <p className="text-xs text-slate-500 italic py-4 text-center">
              No classified mood metadata available for these candidates.
            </p>
          )}
        </div>
      </div>

      {/* Unmet Constraints Audit */}
      {unmet_constraints.length > 0 ? (
        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-800/40 text-xs text-amber-200 space-y-1.5">
          <div className="flex items-center gap-1.5 font-semibold text-amber-300">
            <AlertTriangle className="w-4 h-4 text-amber-400" />
            <span>Unmet Curation Constraints:</span>
          </div>
          <ul className="list-disc list-inside space-y-1 text-amber-200/90 pl-1 text-[11px]">
            {unmet_constraints.map((u, i) => (
              <li key={i}>{u}</li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="p-3 rounded-xl bg-emerald-950/20 border border-emerald-800/30 text-xs text-emerald-300 flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>All AI-requested constraints, genres, and artist diversity rules were fully satisfied.</span>
        </div>
      )}

      {/* Methodology Notes */}
      {notes.length > 0 && (
        <div className="p-3.5 rounded-xl bg-slate-900/50 border border-slate-800/60 text-[11px] text-slate-400 space-y-1">
          <div className="flex items-center gap-1.5 font-medium text-slate-300">
            <Info className="w-3.5 h-3.5 text-purple-400" />
            <span>Catalog & Metric Disclaimers:</span>
          </div>
          <ul className="list-disc list-inside space-y-0.5 text-slate-400/90 pl-1">
            {notes.map((n, i) => (
              <li key={i}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

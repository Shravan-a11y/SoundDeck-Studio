import React from 'react';
import { ExternalLink, Disc, Sparkles, Tag, Heart, ShieldAlert, Award, FileSpreadsheet } from 'lucide-react';

export default function PlaylistView({ playlistData, onExportCsv, isExporting }) {
  if (!playlistData) return null;

  const { playlist_id, interpreted_request, tracks, summary } = playlistData;
  const trackCount = tracks?.length || 0;
  const requestedLimit = interpreted_request?.limit || 20;

  // Unmet constraints alert if any
  const unmetConstraints = summary?.unmet_constraints || [];

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="glass-panel rounded-2xl p-6 sm:p-7 glow-cyan">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-slate-800/80">
          <div>
            <div className="flex items-center gap-2 mb-1.5">
              <span className="text-[11px] font-mono text-cyan-400 bg-cyan-950/40 border border-cyan-800/60 px-2 py-0.5 rounded">
                ID: {playlist_id}
              </span>
              <span className="text-xs text-slate-400">&bull;</span>
              <span className="text-xs font-medium text-purple-300">
                {trackCount} tracks curated
                {trackCount !== requestedLimit && ` (Requested: ${requestedLimit})`}
              </span>
            </div>
            <h2 className="text-xl sm:text-2xl font-bold font-['Outfit'] text-white">
              Curated Playlist & Track Breakdown
            </h2>
          </div>

          {/* Export Action Button */}
          <button
            onClick={onExportCsv}
            disabled={isExporting || trackCount === 0}
            className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl text-xs font-semibold text-slate-100 bg-slate-850 hover:bg-slate-800 border border-slate-700/80 hover:border-cyan-500/50 shadow-md transition-all self-start md:self-auto disabled:opacity-50"
            title="Download CSV file with all metadata and explanations"
          >
            <FileSpreadsheet className={`w-4 h-4 text-cyan-400 ${isExporting ? 'animate-pulse' : ''}`} />
            <span>{isExporting ? 'Exporting CSV...' : 'Export Playlist CSV'}</span>
          </button>
        </div>

        {/* Interpreted Constraints Badges */}
        <div className="pt-4 flex flex-wrap items-center gap-2 text-xs">
          <span className="text-slate-400 font-medium">Interpreted Signals:</span>
          {interpreted_request?.seed_artist && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-purple-950/40 text-purple-200 border border-purple-500/30">
              <span className="text-purple-400 font-semibold">Seed Artist:</span>
              <span>{interpreted_request.seed_artist}</span>
            </span>
          )}
          {interpreted_request?.seed_track && (
            <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-purple-950/40 text-purple-200 border border-purple-500/30">
              <span className="text-purple-400 font-semibold">Seed Track:</span>
              <span>{interpreted_request.seed_track}</span>
            </span>
          )}
          {interpreted_request?.target_genres?.map((g, i) => (
            <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/80 text-cyan-300 border border-cyan-800/40">
              <Tag className="w-3 h-3 text-cyan-400" />
              <span>{g}</span>
            </span>
          ))}
          {interpreted_request?.target_moods?.map((m, i) => (
            <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/80 text-rose-300 border border-rose-800/40">
              <Heart className="w-3 h-3 text-rose-400" />
              <span>{m}</span>
            </span>
          ))}
          {interpreted_request?.target_contexts?.map((c, i) => (
            <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-slate-800/80 text-amber-300 border border-amber-800/40">
              <span>{c}</span>
            </span>
          ))}
        </div>

        {/* Unmet Constraints Alert Banner */}
        {unmetConstraints.length > 0 && (
          <div className="mt-4 p-3.5 rounded-xl bg-amber-950/30 border border-amber-700/40 text-xs text-amber-200 flex items-start gap-2.5">
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div className="space-y-0.5">
              <div className="font-semibold text-amber-300">Catalog Constraint Notes:</div>
              <ul className="list-disc list-inside space-y-0.5 text-amber-200/90 text-[11px]">
                {unmetConstraints.map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        )}
      </div>

      {/* Ordered Track List */}
      <div className="space-y-3">
        {tracks.map((track, index) => {
          const position = track.ranking_position || index + 1;
          const sounddeckScore = track.sounddeck_score !== undefined ? Number(track.sounddeck_score) : null;
          const relevanceScore = track.relevance_score !== undefined ? Number(track.relevance_score) : null;
          const diversityAdj = track.diversity_adjustment !== undefined ? Number(track.diversity_adjustment) : null;
          const genres = track.genres || [];
          const moods = track.moods || [];
          const explanation = track.explanation;
          const lastfmUrl = track.url;

          return (
            <div
              key={index}
              className="glass-panel-subtle hover:glass-panel rounded-xl p-4 sm:p-5 transition-all duration-200 border border-slate-800/70 hover:border-purple-500/30 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 group"
            >
              {/* Left Column: Number, Artwork placeholder & Title/Artist */}
              <div className="flex items-start sm:items-center gap-3.5 min-w-0 flex-1">
                {/* Ranking Position */}
                <div className="w-8 h-8 rounded-lg bg-slate-900 border border-slate-800 flex items-center justify-center text-xs font-bold font-mono text-purple-300 shrink-0 shadow-inner">
                  {position}
                </div>

                {/* Generative Vinyl Cover Placeholder */}
                <div className="w-11 h-11 rounded-lg bg-gradient-to-br from-slate-900 via-purple-950/60 to-slate-950 border border-slate-800/80 flex items-center justify-center shrink-0 shadow relative overflow-hidden group-hover:border-purple-500/40 transition-colors">
                  <Disc className="w-6 h-6 text-slate-600 group-hover:text-purple-400 group-hover:rotate-45 transition-all duration-500" />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/40 to-transparent"></div>
                </div>

                {/* Title & Metadata */}
                <div className="min-w-0 flex-1 space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold text-white truncate group-hover:text-purple-200 transition-colors">
                      {track.title || "Untitled Track"}
                    </h3>
                    {lastfmUrl && (
                      <a
                        href={lastfmUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-slate-500 hover:text-cyan-400 transition-colors p-0.5 rounded"
                        title="View on Last.fm"
                      >
                        <ExternalLink className="w-3.5 h-3.5" />
                      </a>
                    )}
                  </div>

                  <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-slate-400">
                    <span className="font-medium text-slate-300">{track.artist || "Unknown Artist"}</span>
                    {track.album && (
                      <>
                        <span className="text-slate-600">&bull;</span>
                        <span className="text-slate-400 truncate italic">{track.album}</span>
                      </>
                    )}
                  </div>

                  {/* Tags Pill Row */}
                  {(genres.length > 0 || moods.length > 0) && (
                    <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
                      {genres.slice(0, 3).map((g, i) => (
                        <span
                          key={i}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800"
                        >
                          {g}
                        </span>
                      ))}
                      {moods.slice(0, 2).map((m, i) => (
                        <span
                          key={i}
                          className="text-[10px] px-1.5 py-0.5 rounded bg-purple-950/30 text-purple-300 border border-purple-800/30"
                        >
                          {m}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Recommendation Explanation */}
                  {explanation && (
                    <p className="text-[11px] text-slate-400/90 pt-1 flex items-start gap-1.5">
                      <Sparkles className="w-3 h-3 text-purple-400/80 shrink-0 mt-0.5" />
                      <span>{explanation}</span>
                    </p>
                  )}
                </div>
              </div>

              {/* Right Column: Scoring Badges */}
              <div className="flex sm:flex-col items-end justify-between sm:justify-center gap-2 self-stretch sm:self-auto shrink-0 pl-11 sm:pl-0 border-t sm:border-t-0 border-slate-800/40 pt-2 sm:pt-0">
                {sounddeckScore !== null && (
                  <div className="flex items-center gap-1.5 bg-slate-900/90 border border-slate-800 px-2.5 py-1 rounded-lg">
                    <Award className="w-3.5 h-3.5 text-cyan-400" />
                    <div className="text-right">
                      <div className="text-xs font-mono font-bold text-white">
                        {sounddeckScore.toFixed(3)}
                      </div>
                      <div className="text-[9px] text-slate-500 uppercase tracking-wider">Score</div>
                    </div>
                  </div>
                )}

                {relevanceScore !== null && (
                  <div className="text-[10px] font-mono text-slate-400">
                    Relevance: <span className="text-slate-300">{relevanceScore.toFixed(2)}</span>
                  </div>
                )}

                {diversityAdj !== null && diversityAdj > 0 && (
                  <span className="text-[10px] text-amber-400/80 bg-amber-950/20 px-1.5 py-0.5 rounded border border-amber-800/30">
                    -{diversityAdj.toFixed(2)} penalty
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

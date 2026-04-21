import { Github, ExternalLink } from 'lucide-react';

function PopcornIcon({ size = 24 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 28 28" fill="none">
      <path d="M8 14L10 25H18L20 14Z" fill="#E50914" />
      <path d="M10.5 14L11.2 25H12.5L11.8 14Z" fill="rgba(255,255,255,0.28)" />
      <path d="M14.8 14L15.5 25H16.8L16.1 14Z" fill="rgba(255,255,255,0.28)" />
      <rect x="7" y="12" width="14" height="2.5" rx="1.25" fill="#bf0010" />
      <circle cx="11" cy="9.5" r="3" fill="#FFF176" />
      <circle cx="14" cy="7.8" r="3.2" fill="#FFF9C4" />
      <circle cx="17" cy="9.5" r="3" fill="#FFF176" />
      <circle cx="8.5" cy="11.2" r="2" fill="#FFF9C4" />
      <circle cx="19.5" cy="11.2" r="2" fill="#FFF176" />
    </svg>
  );
}

export default function Footer() {
  return (
    <footer className="mt-20 border-t border-white/5 py-12 px-6 md:px-10">
      <div className="max-w-screen-2xl mx-auto">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-10">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <PopcornIcon size={26} />
              <span className="text-lg font-black tracking-tight text-white">
                Pop<span className="text-[#E50914]">corn</span>
              </span>
            </div>
            <p className="text-sm text-[#666] leading-relaxed max-w-xs">
              LLM-Augmented Hybrid Movie Recommender. CSE 573 — Semantic Web Mining. Group 18, Spring 2026.
            </p>
          </div>

          {/* Models */}
          <div>
            <h4 className="text-xs font-semibold text-[#888] uppercase tracking-widest mb-4">
              Recommendation Models
            </h4>
            <ul className="space-y-2.5 text-sm text-[#666]">
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-blue-500" />
                OCCF — Long-Term Collaborative Filtering
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-emerald-500" />
                GRU4Rec — Session-Based Next-Item
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-violet-500" />
                Knowledge Graph — Neo4j + TMDB
              </li>
              <li className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-amber-500" />
                LLM Fusion — Natural Language Query
              </li>
            </ul>
          </div>

          {/* Dataset & Links */}
          <div>
            <h4 className="text-xs font-semibold text-[#888] uppercase tracking-widest mb-4">
              Data Sources
            </h4>
            <ul className="space-y-2.5 text-sm text-[#666]">
              <li className="flex items-center gap-2">
                <ExternalLink size={12} className="shrink-0" />
                MovieLens 20M — 20M ratings, 138K users
              </li>
              <li className="flex items-center gap-2">
                <ExternalLink size={12} className="shrink-0" />
                TMDB API — 24K movies with full metadata
              </li>
              <li className="flex items-center gap-2">
                <Github size={12} className="shrink-0" />
                <span>Group 18 — ASU Spring 2026</span>
              </li>
            </ul>
          </div>
        </div>

        <div className="mt-10 pt-6 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-xs text-[#444]">
            © 2026 Popcorn — Built for CSE 573 Semantic Web Mining · Group 18
          </p>
          <div className="flex items-center gap-1 text-xs text-[#444]">
            <span>Powered by</span>
            <span className="text-blue-400 font-medium">OCCF</span>
            <span>·</span>
            <span className="text-emerald-400 font-medium">GRU4Rec</span>
            <span>·</span>
            <span className="text-violet-400 font-medium">KnowledgeGraph</span>
            <span>·</span>
            <span className="text-amber-400 font-medium">LLM</span>
          </div>
        </div>
      </div>
    </footer>
  );
}

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Plus, ChevronDown, Star } from 'lucide-react';
import { Movie } from '../types';
import RecommendationBadge from './RecommendationBadge';

interface Props {
  movie: Movie;
  size?: 'sm' | 'md' | 'lg';
}

export default function MovieCard({ movie, size = 'md' }: Props) {
  const [hovered, setHovered] = useState(false);
  const navigate = useNavigate();

  const widthClass = size === 'sm' ? 'w-36' : size === 'lg' ? 'w-52' : 'w-44';
  const heightClass = size === 'sm' ? 'h-52' : size === 'lg' ? 'h-72' : 'h-64';

  const primarySource = movie.recommendationSources?.[0];

  return (
    <motion.div
      className={`relative ${widthClass} shrink-0 cursor-pointer`}
      onHoverStart={() => setHovered(true)}
      onHoverEnd={() => setHovered(false)}
      whileHover={{ scale: 1.06, zIndex: 30 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      onClick={() => navigate(`/movie/${movie.id}`, { state: { movie } })}
    >
      {/* Poster */}
      <div
        className={`relative ${heightClass} rounded-lg overflow-hidden`}
        style={{
          background: `linear-gradient(160deg, ${movie.gradient[0]} 0%, ${movie.gradient[1]} 100%)`,
        }}
      >
        {/* Decorative background art */}
        <div className="absolute inset-0 opacity-30">
          <div
            className="absolute top-4 right-4 w-16 h-16 rounded-full opacity-40 blur-xl"
            style={{ background: movie.accentColor }}
          />
          <div
            className="absolute bottom-8 left-4 w-10 h-10 rounded-full opacity-30 blur-lg"
            style={{ background: movie.accentColor }}
          />
        </div>

        {/* Film grain overlay */}
        <div className="absolute inset-0 opacity-5"
          style={{
            backgroundImage: 'url("data:image/svg+xml,%3Csvg viewBox=\'0 0 256 256\' xmlns=\'http://www.w3.org/2000/svg\'%3E%3Cfilter id=\'noise\'%3E%3CfeTurbulence type=\'fractalNoise\' baseFrequency=\'0.9\' numOctaves=\'4\' stitchTiles=\'stitch\'/%3E%3C/filter%3E%3Crect width=\'100%25\' height=\'100%25\' filter=\'url(%23noise)\' opacity=\'1\'/%3E%3C/svg%3E")',
          }}
        />

        {/* Genre tag (top left accent) */}
        <div className="absolute top-0 left-0 right-0 h-1 opacity-70" style={{ background: movie.accentColor }} />

        {/* Rating badge */}
        <div className="absolute top-2 right-2 flex items-center gap-1 px-1.5 py-0.5 bg-black/60 rounded text-[10px] font-bold text-yellow-400 backdrop-blur-sm">
          <Star size={9} fill="currentColor" />
          {movie.rating.toFixed(1)}
        </div>

        {/* Recommendation badge */}
        {primarySource && (
          <div className="absolute top-2 left-2">
            <RecommendationBadge model={primarySource.model} size="sm" />
          </div>
        )}

        {/* Poster text */}
        <div className="absolute bottom-0 left-0 right-0 p-3 bg-gradient-to-t from-black/90 via-black/40 to-transparent">
          <p className="text-white font-bold text-sm leading-tight line-clamp-2">{movie.title}</p>
          <p className="text-[#888] text-[11px] mt-1">{movie.year}</p>
        </div>
      </div>

      {/* Hover overlay */}
      <AnimatePresence>
        {hovered && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 4 }}
            transition={{ duration: 0.15 }}
            className="absolute left-0 right-0 top-full mt-1 z-40 glass-card rounded-lg border border-white/10 shadow-2xl overflow-hidden"
            style={{ boxShadow: `0 20px 60px rgba(0,0,0,0.8), 0 0 0 1px rgba(255,255,255,0.05)` }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Mini poster header */}
            <div
              className="h-20 relative"
              style={{
                background: `linear-gradient(160deg, ${movie.gradient[0]} 0%, ${movie.gradient[1]} 100%)`,
              }}
            >
              <div className="absolute inset-0 bg-gradient-to-b from-transparent to-black/60" />
              <div className="absolute bottom-2 left-3">
                <p className="text-white font-bold text-sm">{movie.title}</p>
                <p className="text-[#aaa] text-[11px]">{movie.year} · {movie.runtime}m · {movie.maturityRating}</p>
              </div>
            </div>

            <div className="p-3 space-y-3">
              {/* Action buttons */}
              <div className="flex items-center gap-2">
                <button
                  onClick={() => navigate(`/movie/${movie.id}`, { state: { movie } })}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-white text-black text-xs font-bold rounded-md hover:bg-gray-200 transition-colors"
                >
                  <Play size={12} fill="currentColor" />
                  Play
                </button>
                <button className="p-1.5 rounded-full border border-white/30 text-white hover:border-white transition-colors">
                  <Plus size={14} />
                </button>
                <button
                  onClick={() => navigate(`/movie/${movie.id}`, { state: { movie } })}
                  className="ml-auto p-1.5 rounded-full border border-white/30 text-white hover:border-white transition-colors"
                >
                  <ChevronDown size={14} />
                </button>
              </div>

              {/* Rating */}
              <div className="flex items-center gap-2 text-xs">
                <span className="text-emerald-400 font-bold">{Math.round(movie.rating * 10)}% Match</span>
                <span className="text-[#666]">·</span>
                <div className="flex gap-1">
                  {movie.genres.slice(0, 2).map((g) => (
                    <span key={g} className="text-[#aaa]">{g}</span>
                  ))}
                </div>
              </div>

              {/* Recommendation source */}
              {primarySource && (
                <div className="pt-2 border-t border-white/10">
                  <div className="flex items-start gap-2">
                    <RecommendationBadge model={primarySource.model} size="sm" />
                    <p className="text-[10px] text-[#888] leading-relaxed">{primarySource.reason}</p>
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

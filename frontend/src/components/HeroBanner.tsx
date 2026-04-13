import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Info, Volume2, VolumeX, ChevronLeft, ChevronRight } from 'lucide-react';
import { Movie } from '../types';
import RecommendationBadge from './RecommendationBadge';

interface Props {
  movies: Movie[];
}

export default function HeroBanner({ movies }: Props) {
  const [current, setCurrent] = useState(0);
  const [muted, setMuted] = useState(true);
  const navigate = useNavigate();

  const movie = movies[current];

  // Auto-advance hero
  useEffect(() => {
    const timer = setInterval(() => {
      setCurrent((c) => (c + 1) % movies.length);
    }, 8000);
    return () => clearInterval(timer);
  }, [movies.length]);

  const prev = () => setCurrent((c) => (c - 1 + movies.length) % movies.length);
  const next = () => setCurrent((c) => (c + 1) % movies.length);

  return (
    <div className="relative h-[92vh] min-h-[560px] max-h-[860px] overflow-hidden">
      {/* Background gradient (changes per movie) */}
      <AnimatePresence mode="wait">
        <motion.div
          key={movie.id}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.8 }}
          className="absolute inset-0"
          style={{
            background: `
              radial-gradient(ellipse 80% 80% at 70% 50%, ${movie.gradient[1]}88 0%, transparent 70%),
              linear-gradient(135deg, ${movie.gradient[0]} 0%, #0f0f0f 100%)
            `,
          }}
        />
      </AnimatePresence>

      {/* Cinematic vignette overlays */}
      <div className="absolute inset-0 bg-gradient-to-r from-[#0f0f0f] via-[#0f0f0f]/60 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-t from-[#0f0f0f] via-transparent to-[#0f0f0f]/30" />

      {/* Decorative orbs */}
      <AnimatePresence mode="wait">
        <motion.div
          key={`orb-${movie.id}`}
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 1.2 }}
          className="absolute right-16 top-1/2 -translate-y-1/2 w-[480px] h-[480px] rounded-full blur-[120px] opacity-20 pointer-events-none"
          style={{ background: movie.accentColor }}
        />
      </AnimatePresence>

      {/* Content */}
      <div className="relative h-full flex items-center px-6 md:px-10 max-w-screen-2xl mx-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={`content-${movie.id}`}
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 30 }}
            transition={{ duration: 0.55, ease: 'easeOut' }}
            className="max-w-2xl"
          >
            {/* Top badge */}
            <div className="flex items-center gap-3 mb-5">
              <div
                className="text-[10px] font-bold uppercase tracking-widest px-2 py-1 rounded"
                style={{
                  background: `${movie.accentColor}30`,
                  color: movie.accentColor,
                  border: `1px solid ${movie.accentColor}50`,
                }}
              >
                Featured
              </div>
              {movie.recommendationSources?.[0] && (
                <RecommendationBadge model={movie.recommendationSources[0].model} size="md" />
              )}
              <span className="text-xs text-[#888]">{movie.maturityRating}</span>
            </div>

            {/* Title */}
            <h1 className="text-5xl md:text-7xl font-black text-white leading-none tracking-tight mb-4">
              {movie.title}
            </h1>

            {/* Meta row */}
            <div className="flex items-center gap-3 mb-5">
              <span className="text-emerald-400 font-bold text-sm">{Math.round(movie.rating * 10)}% Match</span>
              <span className="text-[#888] text-sm">{movie.year}</span>
              <span className="text-[#888] text-sm">{movie.runtime}m</span>
              <div className="flex gap-2">
                {movie.genres.slice(0, 3).map((g) => (
                  <span key={g} className="text-xs text-[#aaa] border border-white/10 px-2 py-0.5 rounded">
                    {g}
                  </span>
                ))}
              </div>
            </div>

            {/* Overview */}
            <p className="text-[#ccc] text-base leading-relaxed line-clamp-3 max-w-xl mb-8">
              {movie.overview}
            </p>

            {/* Action buttons */}
            <div className="flex items-center gap-3 flex-wrap">
              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => navigate(`/movie/${movie.id}`)}
                className="flex items-center gap-2 px-7 py-3.5 bg-white text-black font-bold text-sm rounded-lg hover:bg-gray-100 transition-colors"
              >
                <Play size={18} fill="currentColor" />
                Play
              </motion.button>

              <motion.button
                whileHover={{ scale: 1.03 }}
                whileTap={{ scale: 0.97 }}
                onClick={() => navigate(`/movie/${movie.id}`)}
                className="flex items-center gap-2 px-7 py-3.5 bg-white/20 text-white font-semibold text-sm rounded-lg border border-white/20 hover:bg-white/30 transition-colors backdrop-blur-sm"
              >
                <Info size={18} />
                More Info
              </motion.button>
            </div>

            {/* Director credit */}
            <p className="mt-6 text-xs text-[#666]">
              Directed by <span className="text-[#aaa]">{movie.director}</span>
              {' · '}
              {movie.cast.slice(0, 3).join(', ')}
            </p>
          </motion.div>
        </AnimatePresence>

        {/* Right side: hero index indicators + controls */}
        <div className="absolute right-6 md:right-10 bottom-16 flex flex-col items-end gap-4">
          {/* Mute button */}
          <button
            onClick={() => setMuted((m) => !m)}
            className="p-2.5 rounded-full border border-white/20 text-white hover:border-white/60 transition-colors backdrop-blur-sm bg-black/20"
          >
            {muted ? <VolumeX size={18} /> : <Volume2 size={18} />}
          </button>

          {/* Navigation arrows */}
          <div className="flex gap-2">
            <button
              onClick={prev}
              className="p-2.5 rounded-full border border-white/20 text-white hover:border-white/60 transition-colors backdrop-blur-sm bg-black/20"
            >
              <ChevronLeft size={18} />
            </button>
            <button
              onClick={next}
              className="p-2.5 rounded-full border border-white/20 text-white hover:border-white/60 transition-colors backdrop-blur-sm bg-black/20"
            >
              <ChevronRight size={18} />
            </button>
          </div>

          {/* Dot indicators */}
          <div className="flex gap-1.5 mt-1">
            {movies.map((_, i) => (
              <button
                key={i}
                onClick={() => setCurrent(i)}
                className={`rounded-full transition-all duration-300 ${
                  i === current ? 'w-6 h-1.5 bg-white' : 'w-1.5 h-1.5 bg-white/30 hover:bg-white/60'
                }`}
              />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

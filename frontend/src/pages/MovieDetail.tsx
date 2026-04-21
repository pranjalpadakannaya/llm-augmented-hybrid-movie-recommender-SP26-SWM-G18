import { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Play, Plus, ArrowLeft, Star, Clock, Calendar, Film, Share2, Info } from 'lucide-react';
import { MOVIES } from '../data/mockData';
import { Movie } from '../types';
import RecommendationBadge from '../components/RecommendationBadge';
import MovieCard from '../components/MovieCard';
import { fetchMovieById, fetchRecommendations } from '../api/client';

const MODEL_COLORS: Record<string, string> = {
  OCCF: '#3B82F6',
  GRU4Rec: '#10B981',
  KnowledgeGraph: '#8B5CF6',
  Hybrid: '#F59E0B',
  Trending: '#EF4444',
};

const MODEL_LABELS: Record<string, string> = {
  OCCF: 'Collaborative Filtering (OCCF)',
  GRU4Rec: 'Session-Based (GRU4Rec)',
  KnowledgeGraph: 'Knowledge Graph',
  Hybrid: 'Hybrid Fusion',
  Trending: 'Trending Signal',
};

export default function MovieDetail() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { state } = useLocation() as { state?: { movie?: Movie } };

  const [movie, setMovie] = useState<Movie | null>(state?.movie ?? null);
  const [similar, setSimilar] = useState<Movie[]>([]);
  const [loadingMovie, setLoadingMovie] = useState(!state?.movie);

  useEffect(() => {
    window.scrollTo(0, 0);
  }, [id]);

  useEffect(() => {
    if (movie) return;
    const numId = Number(id);

    // Try mock data first (IDs 1–20)
    const mock = MOVIES.find((m) => m.id === numId);
    if (mock) {
      setMovie(mock);
      setLoadingMovie(false);
      return;
    }

    // Fetch from API
    fetchMovieById(numId)
      .then((m) => setMovie(m))
      .catch(() => setMovie(null))
      .finally(() => setLoadingMovie(false));
  }, [id, movie]);

  // Fetch similar movies via KG once we know the movie title
  useEffect(() => {
    if (!movie?.title) return;
    fetchRecommendations('kg', 1, 8, movie.title)
      .then((movies) => setSimilar(movies.filter((m) => m.id !== movie.id).slice(0, 8)))
      .catch(() => {
        // fallback: pick from mock
        setSimilar(MOVIES.filter((m) => m.id !== movie.id).slice(0, 8));
      });
  }, [movie]);

  if (loadingMovie) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <div className="w-10 h-10 border-2 border-[#E50914] border-t-transparent rounded-full animate-spin" />
          <p className="text-[#888] text-sm">Loading movie…</p>
        </div>
      </div>
    );
  }

  if (!movie) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="text-center">
          <p className="text-[#888] text-xl mb-4">Movie not found</p>
          <button onClick={() => navigate('/')} className="text-[#E50914] hover:underline">
            Back to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-[#0f0f0f]"
    >
      {/* Hero section */}
      <div className="relative h-[70vh] min-h-[500px] overflow-hidden">
        <div
          className="absolute inset-0"
          style={{
            background: `
              radial-gradient(ellipse 90% 90% at 65% 40%, ${movie.gradient[1]}aa 0%, transparent 65%),
              linear-gradient(135deg, ${movie.gradient[0]} 0%, #0f0f0f 100%)
            `,
          }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#0f0f0f] via-[#0f0f0f]/50 to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0f0f0f] via-transparent to-[#0f0f0f]/40" />

        <div
          className="absolute right-24 top-1/2 -translate-y-1/2 w-96 h-96 rounded-full blur-[120px] opacity-15 pointer-events-none"
          style={{ background: movie.accentColor }}
        />

        <div className="absolute top-20 left-6 md:left-10 z-10">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center gap-2 text-sm text-[#aaa] hover:text-white transition-colors group"
          >
            <ArrowLeft size={18} className="group-hover:-translate-x-1 transition-transform" />
            Back
          </button>
        </div>

        <div className="relative h-full flex items-end pb-16 px-6 md:px-10 max-w-screen-2xl mx-auto">
          <div className="flex gap-8 items-end w-full">
            {/* Poster card */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="hidden md:block shrink-0 w-48 h-72 rounded-xl overflow-hidden shadow-2xl border border-white/10 relative"
              style={{
                background: `linear-gradient(160deg, ${movie.gradient[0]} 0%, ${movie.gradient[1]} 100%)`,
              }}
            >
              <div
                className="absolute top-0 left-0 right-0 h-1"
                style={{ background: movie.accentColor }}
              />
              <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-black/90 to-transparent">
                <p className="text-white font-bold text-sm leading-tight">{movie.title}</p>
                <p className="text-[#888] text-xs mt-1">{movie.year}</p>
              </div>
            </motion.div>

            {/* Info */}
            <motion.div
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15 }}
              className="flex-1 min-w-0"
            >
              <div className="flex flex-wrap items-center gap-3 mb-3">
                {movie.recommendationSources?.map((src) => (
                  <RecommendationBadge key={src.model} model={src.model} size="md" />
                ))}
                <span className="text-xs border border-white/20 text-[#aaa] px-2 py-0.5 rounded">
                  {movie.maturityRating}
                </span>
              </div>

              <h1 className="text-4xl md:text-6xl font-black text-white tracking-tight mb-3">
                {movie.title}
              </h1>

              <div className="flex flex-wrap items-center gap-4 mb-4 text-sm">
                {movie.rating > 0 && (
                  <div className="flex items-center gap-1.5 text-yellow-400 font-bold">
                    <Star size={14} fill="currentColor" />
                    {movie.rating}/10
                  </div>
                )}
                {movie.rating > 0 && (
                  <span className="text-emerald-400 font-bold">{Math.round(movie.rating * 10)}% Match</span>
                )}
                {movie.year > 0 && (
                  <div className="flex items-center gap-1 text-[#aaa]">
                    <Calendar size={13} />
                    {movie.year}
                  </div>
                )}
                {movie.runtime > 0 && (
                  <div className="flex items-center gap-1 text-[#aaa]">
                    <Clock size={13} />
                    {movie.runtime}m
                  </div>
                )}
                {movie.director && (
                  <div className="flex items-center gap-1 text-[#aaa]">
                    <Film size={13} />
                    {movie.director}
                  </div>
                )}
              </div>

              <div className="flex flex-wrap gap-2 mb-5">
                {movie.genres.map((g) => (
                  <span key={g} className="text-xs border border-white/15 text-[#bbb] px-3 py-1 rounded-full">
                    {g}
                  </span>
                ))}
              </div>

              {movie.overview && (
                <p className="text-[#ccc] text-base leading-relaxed max-w-2xl mb-6">
                  {movie.overview}
                </p>
              )}

              <div className="flex flex-wrap gap-3">
                <motion.button
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className="flex items-center gap-2 px-7 py-3 bg-white text-black font-bold rounded-lg hover:bg-gray-100 transition-colors"
                >
                  <Play size={18} fill="currentColor" />
                  Play
                </motion.button>
                <motion.button
                  whileHover={{ scale: 1.03 }}
                  whileTap={{ scale: 0.97 }}
                  className="flex items-center gap-2 px-6 py-3 bg-white/15 text-white font-semibold rounded-lg border border-white/20 hover:bg-white/25 transition-colors backdrop-blur-sm"
                >
                  <Plus size={18} />
                  My List
                </motion.button>
                <button className="flex items-center gap-2 px-4 py-3 bg-white/10 text-[#aaa] rounded-lg border border-white/10 hover:text-white hover:border-white/20 transition-colors backdrop-blur-sm">
                  <Share2 size={16} />
                </button>
              </div>
            </motion.div>
          </div>
        </div>
      </div>

      {/* Details section */}
      <div className="max-w-screen-2xl mx-auto px-6 md:px-10 py-10 space-y-12">
        {/* Cast */}
        {movie.cast.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-lg font-bold text-white mb-4">Cast</h2>
            <div className="flex flex-wrap gap-3">
              {movie.cast.map((name) => (
                <div key={name} className="flex items-center gap-2 px-3 py-2 bg-[#1a1a1a] rounded-lg border border-white/10">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-[#333] to-[#222] flex items-center justify-center text-[10px] font-bold text-[#888]">
                    {name.split(' ').map((n) => n[0]).join('').slice(0, 2)}
                  </div>
                  <span className="text-sm text-[#ccc]">{name}</span>
                </div>
              ))}
            </div>
          </motion.section>
        )}

        {/* Why Recommended */}
        {movie.recommendationSources && movie.recommendationSources.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <div className="flex items-center gap-2 mb-5">
              <Info size={18} className="text-[#888]" />
              <h2 className="text-lg font-bold text-white">Why This Was Recommended</h2>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {movie.recommendationSources.map((src) => (
                <motion.div
                  key={src.model}
                  initial={{ opacity: 0, scale: 0.97 }}
                  whileInView={{ opacity: 1, scale: 1 }}
                  viewport={{ once: true }}
                  className="p-4 bg-[#1a1a1a] rounded-xl border border-white/10 space-y-3"
                >
                  <div className="flex items-center justify-between">
                    <RecommendationBadge model={src.model} size="md" />
                    <span
                      className="text-sm font-bold"
                      style={{ color: MODEL_COLORS[src.model] }}
                    >
                      {Math.round(src.score * 100)}%
                    </span>
                  </div>
                  <p className="text-xs text-[#888]">{MODEL_LABELS[src.model]}</p>
                  <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      whileInView={{ width: `${src.score * 100}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.8, delay: 0.2 }}
                      className="h-full rounded-full"
                      style={{ background: MODEL_COLORS[src.model] }}
                    />
                  </div>
                  <p className="text-xs text-[#aaa] leading-relaxed">{src.reason}</p>
                </motion.div>
              ))}
            </div>
          </motion.section>
        )}

        {/* More like this */}
        {similar.length > 0 && (
          <motion.section
            initial={{ opacity: 0, y: 16 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
          >
            <h2 className="text-lg font-bold text-white mb-4">More Like This</h2>
            <div className="flex gap-4 overflow-x-auto hide-scrollbar pb-4">
              {similar.map((m) => (
                <MovieCard key={m.id} movie={m} size="md" />
              ))}
            </div>
          </motion.section>
        )}
      </div>
    </motion.div>
  );
}

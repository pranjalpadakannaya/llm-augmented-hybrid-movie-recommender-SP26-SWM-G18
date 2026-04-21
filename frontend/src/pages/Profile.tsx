import { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Film, Clock, BarChart3, Layers, Settings, Star } from 'lucide-react';
import MovieCard from '../components/MovieCard';
import RecommendationBadge from '../components/RecommendationBadge';
import { fetchProfile } from '../api/client';
import { UserProfile } from '../types';

export default function Profile({ userId }: { userId: number }) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    fetchProfile(userId)
      .then((data) => {
        if (!cancelled) {
          setProfile(data);
          setError('');
        }
      })
      .catch(() => {
        if (!cancelled) {
          setError('Profile data is unavailable until the backend API is running with ratings loaded.');
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [userId]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] pt-24 pb-20 px-6 md:px-10 flex items-center justify-center">
        <div className="text-center">
          <div className="w-10 h-10 border-2 border-[#E50914] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white text-lg font-semibold">Loading profile</p>
          <p className="text-[#666] text-sm mt-2">Building your stats from the backend ratings dataset.</p>
        </div>
      </div>
    );
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] pt-24 pb-20 px-6 md:px-10 flex items-center justify-center">
        <div className="text-center max-w-md">
          <p className="text-white text-lg font-semibold">No profile data available</p>
          <p className="text-[#666] text-sm mt-2">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-[#0f0f0f] pt-24 pb-20 px-6 md:px-10"
    >
      <div className="max-w-screen-xl mx-auto space-y-12">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row items-start md:items-center gap-6"
        >
          <div
            className="w-24 h-24 rounded-2xl flex items-center justify-center text-2xl font-black text-white shadow-lg"
            style={{ background: `linear-gradient(135deg, ${profile.avatarColor}, #c10710)` }}
          >
            {profile.initials}
          </div>

          <div className="flex-1">
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-3xl font-black text-white">{profile.displayName}</h1>
              <span className="text-xs bg-[#E50914]/20 text-[#ff6b6b] border border-[#E50914]/30 px-2 py-0.5 rounded">
                Dataset User
              </span>
            </div>
            <p className="text-[#666] text-sm">{profile.id} · Member since {profile.memberSince}</p>

            <div className="flex flex-wrap gap-5 mt-4">
              <div className="text-center">
                <p className="text-2xl font-black text-white">{profile.totalWatched}</p>
                <p className="text-xs text-[#666] mt-0.5">Movies Watched</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="text-center">
                <p className="text-2xl font-black text-white">{profile.activeModels}</p>
                <p className="text-xs text-[#666] mt-0.5">Active Models</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="text-center">
                <p className="text-2xl font-black text-white">{profile.avgRating.toFixed(1)}</p>
                <p className="text-xs text-[#666] mt-0.5">Avg Rating Given</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="text-center">
                <p className="text-2xl font-black text-white">{profile.recentActivity}</p>
                <p className="text-xs text-[#666] mt-0.5">Ratings in 30 Days</p>
              </div>
            </div>
          </div>

          <button className="flex items-center gap-2 px-4 py-2.5 bg-[#1a1a1a] border border-white/10 text-[#aaa] text-sm rounded-lg hover:text-white hover:border-white/20 transition-colors">
            <Settings size={15} />
            Settings
          </button>
        </motion.div>

        <motion.section
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="flex items-center gap-2 mb-5">
            <Layers size={18} className="text-[#888]" />
            <h2 className="text-xl font-bold text-white">How Your Recommendations Work</h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {profile.modelContributions.map((mc, i) => (
              <motion.div
                key={mc.model}
                initial={{ opacity: 0, y: 12 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.1 }}
                className="p-5 bg-[#1a1a1a] rounded-xl border border-white/10"
              >
                <div className="flex items-center justify-between mb-3">
                  <RecommendationBadge model={mc.model} size="md" />
                  <span className="text-2xl font-black" style={{ color: mc.color }}>
                    {mc.percentage}%
                  </span>
                </div>
                <p className="text-sm font-semibold text-white mb-1">{mc.label}</p>
                <p className="text-xs text-[#666] leading-relaxed">{mc.description}</p>

                <div className="mt-4 h-1.5 bg-white/10 rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    whileInView={{ width: `${mc.percentage}%` }}
                    viewport={{ once: true }}
                    transition={{ duration: 0.9, delay: i * 0.1 + 0.2, ease: 'easeOut' }}
                    className="h-full rounded-full"
                    style={{ background: mc.color }}
                  />
                </div>
              </motion.div>
            ))}
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="flex items-center gap-2 mb-5">
            <BarChart3 size={18} className="text-[#888]" />
            <h2 className="text-xl font-bold text-white">Your Taste Profile</h2>
          </div>

          <div className="p-6 bg-[#1a1a1a] rounded-xl border border-white/10">
            <p className="text-xs text-[#555] uppercase tracking-widest mb-5">Genre Distribution</p>
            <div className="space-y-4">
              {profile.favoriteGenres.map((g, i) => (
                <motion.div
                  key={g.genre}
                  initial={{ opacity: 0, x: -12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08 }}
                  className="flex items-center gap-4"
                >
                  <span className="text-sm text-[#aaa] w-24 shrink-0">{g.genre}</span>
                  <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      whileInView={{ width: `${g.percentage}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 0.8, delay: i * 0.08 + 0.1, ease: 'easeOut' }}
                      className="h-full rounded-full"
                      style={{ background: g.color }}
                    />
                  </div>
                  <span className="text-sm font-bold text-white w-10 text-right">{g.percentage}%</span>
                </motion.div>
              ))}
            </div>

            <div className="mt-6 pt-5 border-t border-white/10 grid grid-cols-2 md:grid-cols-4 gap-4">
              {profile.summaryStats.map((stat) => (
                <div key={stat.label}>
                  <p className="text-xs text-[#555] mb-1">{stat.label}</p>
                  <p className="text-sm font-semibold text-[#ccc]">{stat.value}</p>
                </div>
              ))}
            </div>
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Clock size={18} className="text-[#888]" />
            <h2 className="text-xl font-bold text-white">Recently Watched</h2>
          </div>

          <div className="flex gap-4 overflow-x-auto hide-scrollbar pb-4">
            {profile.recentMovies.map((movie, i) => (
              <motion.div
                key={`${movie.id}-${movie.userRating ?? i}`}
                initial={{ opacity: 0, x: 16 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
                className="space-y-2"
              >
                <MovieCard movie={movie} size="md" />
                {movie.userRating !== undefined && (
                  <p className="text-xs text-[#777] text-center">You rated this {movie.userRating.toFixed(1)}</p>
                )}
              </motion.div>
            ))}
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Star size={18} className="text-[#888]" />
            <h2 className="text-xl font-bold text-white">Your Top-Rated</h2>
          </div>

          <div className="space-y-2">
            {profile.topRatedMovies.map((movie, i) => (
              <motion.div
                key={`${movie.id}-${movie.userRating ?? i}`}
                initial={{ opacity: 0, x: -12 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className="flex items-center gap-4 p-4 bg-[#1a1a1a] rounded-xl border border-white/10 hover:border-white/20 transition-all"
              >
                <span className="text-2xl font-black text-[#333] w-8 text-center">{i + 1}</span>
                <div
                  className="w-10 h-14 rounded-lg shrink-0 overflow-hidden"
                  style={{
                    background: `linear-gradient(160deg, ${movie.gradient[0]} 0%, ${movie.gradient[1]} 100%)`,
                  }}
                >
                  {movie.posterUrl && (
                    <img src={movie.posterUrl} alt={movie.title} className="w-full h-full object-cover" />
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">{movie.title}</p>
                  <p className="text-xs text-[#666]">{movie.year} · {movie.director || 'Unknown director'}</p>
                </div>
                <div className="flex items-center gap-3">
                  {movie.genres.slice(0, 1).map((g) => (
                    <span key={g} className="hidden md:block text-xs text-[#666] border border-white/10 px-2 py-0.5 rounded">
                      {g}
                    </span>
                  ))}
                  {movie.userRating !== undefined && (
                    <div className="flex items-center gap-1 text-yellow-400 text-sm font-bold">
                      <Star size={13} fill="currentColor" />
                      {movie.userRating.toFixed(1)}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </motion.section>

        <motion.section
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Film size={18} className="text-[#888]" />
            <h2 className="text-xl font-bold text-white">About Popcorn</h2>
          </div>

          <div className="p-6 bg-[#1a1a1a] rounded-xl border border-white/10">
            <p className="text-sm text-[#888] leading-relaxed mb-5">
              Popcorn is a research prototype implementing a hybrid recommendation system as part of
              ASU CSE 573 — Semantic Web Mining. This profile now reads user statistics, watch
              history, and top-rated movies directly from the backend ratings dataset.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                {
                  badge: 'OCCF' as const,
                  name: 'Collaborative Filtering',
                  desc: 'Implicit-feedback recommendation using the MovieLens interaction history.',
                  dataset: 'MovieLens ratings',
                  lib: 'implicit ALS',
                },
                {
                  badge: 'GRU4Rec' as const,
                  name: 'Session-Based GRU',
                  desc: 'Sequence-aware recommendations learned from the order of watched movies.',
                  dataset: 'Timestamped sessions',
                  lib: 'PyTorch',
                },
                {
                  badge: 'KnowledgeGraph' as const,
                  name: 'Knowledge Graph',
                  desc: 'TMDB-enriched semantic relationships across genres, cast, directors, and keywords.',
                  dataset: 'TMDB + MovieLens',
                  lib: 'Graph-based ranking',
                },
              ].map((item) => (
                <div key={item.name} className="p-4 bg-[#111] rounded-lg border border-white/10 space-y-2">
                  <RecommendationBadge model={item.badge} size="md" />
                  <p className="text-sm font-semibold text-white">{item.name}</p>
                  <p className="text-xs text-[#666] leading-relaxed">{item.desc}</p>
                  <div className="pt-2 border-t border-white/10 space-y-1">
                    <p className="text-[10px] text-[#555]">
                      <span className="text-[#888]">Dataset:</span> {item.dataset}
                    </p>
                    <p className="text-[10px] text-[#555]">
                      <span className="text-[#888]">Library:</span> {item.lib}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </motion.section>
      </div>
    </motion.div>
  );
}

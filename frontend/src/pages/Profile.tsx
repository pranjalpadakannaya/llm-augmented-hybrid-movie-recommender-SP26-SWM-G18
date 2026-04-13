import { motion } from 'framer-motion';
import { Film, Clock, BarChart3, Layers, Settings, Star } from 'lucide-react';
import { USER_PROFILE, MOVIES } from '../data/mockData';
import MovieCard from '../components/MovieCard';
import RecommendationBadge from '../components/RecommendationBadge';

const RECENTLY_WATCHED = [MOVIES[0], MOVIES[1], MOVIES[2], MOVIES[3], MOVIES[6], MOVIES[12]];

export default function Profile() {
  const user = USER_PROFILE;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-[#0f0f0f] pt-24 pb-20 px-6 md:px-10"
    >
      <div className="max-w-screen-xl mx-auto space-y-12">
        {/* Profile header */}
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-col md:flex-row items-start md:items-center gap-6"
        >
          {/* Avatar */}
          <div
            className="w-24 h-24 rounded-2xl flex items-center justify-center text-2xl font-black text-white shadow-lg"
            style={{ background: `linear-gradient(135deg, ${user.avatarColor}, #c10710)` }}
          >
            {user.initials}
          </div>

          {/* Info */}
          <div className="flex-1">
            <div className="flex items-center gap-3 mb-1">
              <h1 className="text-3xl font-black text-white">{user.name}</h1>
              <span className="text-xs bg-[#E50914]/20 text-[#ff6b6b] border border-[#E50914]/30 px-2 py-0.5 rounded">
                Member
              </span>
            </div>
            <p className="text-[#666] text-sm">{user.id} · Member since {user.memberSince}</p>

            <div className="flex flex-wrap gap-5 mt-4">
              <div className="text-center">
                <p className="text-2xl font-black text-white">{user.totalWatched}</p>
                <p className="text-xs text-[#666] mt-0.5">Movies Watched</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="text-center">
                <p className="text-2xl font-black text-white">3</p>
                <p className="text-xs text-[#666] mt-0.5">Active Models</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="text-center">
                <p className="text-2xl font-black text-white">8.4</p>
                <p className="text-xs text-[#666] mt-0.5">Avg Rating Given</p>
              </div>
              <div className="w-px bg-white/10" />
              <div className="text-center">
                <p className="text-2xl font-black text-white">94%</p>
                <p className="text-xs text-[#666] mt-0.5">Recommendation Accuracy</p>
              </div>
            </div>
          </div>

          <button className="flex items-center gap-2 px-4 py-2.5 bg-[#1a1a1a] border border-white/10 text-[#aaa] text-sm rounded-lg hover:text-white hover:border-white/20 transition-colors">
            <Settings size={15} />
            Settings
          </button>
        </motion.div>

        {/* Model contributions */}
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
            {user.modelContributions.map((mc, i) => (
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

                {/* Bar */}
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

        {/* Taste profile */}
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
              {user.favoriteGenres.map((g, i) => (
                <motion.div
                  key={g.genre}
                  initial={{ opacity: 0, x: -12 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ delay: i * 0.08 }}
                  className="flex items-center gap-4"
                >
                  <span className="text-sm text-[#aaa] w-20 shrink-0">{g.genre}</span>
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
              {[
                { label: 'Preferred Era', value: '2000s–Present' },
                { label: 'Avg Session Length', value: '2.3 hours' },
                { label: 'Top Director', value: 'Christopher Nolan' },
                { label: 'Favorite Theme', value: 'Mind-bending' },
              ].map((stat) => (
                <div key={stat.label}>
                  <p className="text-xs text-[#555] mb-1">{stat.label}</p>
                  <p className="text-sm font-semibold text-[#ccc]">{stat.value}</p>
                </div>
              ))}
            </div>
          </div>
        </motion.section>

        {/* Recently Watched */}
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
            {RECENTLY_WATCHED.map((movie, i) => (
              <motion.div
                key={movie.id}
                initial={{ opacity: 0, x: 16 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.06 }}
              >
                <MovieCard movie={movie} size="md" />
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* Top Rated by You */}
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
            {[MOVIES[1], MOVIES[19], MOVIES[0], MOVIES[5], MOVIES[12]].map((movie, i) => (
              <motion.div
                key={movie.id}
                initial={{ opacity: 0, x: -12 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true }}
                transition={{ delay: i * 0.08 }}
                className="flex items-center gap-4 p-4 bg-[#1a1a1a] rounded-xl border border-white/10 hover:border-white/20 transition-all cursor-pointer group"
              >
                <span className="text-2xl font-black text-[#333] w-8 text-center group-hover:text-[#555] transition-colors">
                  {i + 1}
                </span>
                <div
                  className="w-10 h-14 rounded-lg shrink-0"
                  style={{
                    background: `linear-gradient(160deg, ${movie.gradient[0]} 0%, ${movie.gradient[1]} 100%)`,
                  }}
                />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-semibold text-white truncate">{movie.title}</p>
                  <p className="text-xs text-[#666]">{movie.year} · {movie.director}</p>
                </div>
                <div className="flex items-center gap-3">
                  {movie.genres.slice(0, 1).map((g) => (
                    <span key={g} className="hidden md:block text-xs text-[#666] border border-white/10 px-2 py-0.5 rounded">
                      {g}
                    </span>
                  ))}
                  <div className="flex items-center gap-1 text-yellow-400 text-sm font-bold">
                    <Star size={13} fill="currentColor" />
                    {movie.rating.toFixed(1)}
                  </div>
                  {movie.recommendationSources?.[0] && (
                    <div className="hidden md:block">
                      <RecommendationBadge model={movie.recommendationSources[0].model} size="sm" />
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>
        </motion.section>

        {/* Model Info panel */}
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
        >
          <div className="flex items-center gap-2 mb-4">
            <Film size={18} className="text-[#888]" />
            <h2 className="text-xl font-bold text-white">About CineAI</h2>
          </div>

          <div className="p-6 bg-[#1a1a1a] rounded-xl border border-white/10">
            <p className="text-sm text-[#888] leading-relaxed mb-5">
              CineAI is a research prototype implementing a hybrid recommendation system as part of
              ASU CSE 573 — Semantic Web Mining. Recommendations are powered by three parallel models
              whose scores are fused and re-ranked using a weighted aggregation layer.
            </p>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                {
                  badge: 'OCCF' as const,
                  name: 'Collaborative Filtering',
                  desc: 'Implicit feedback matrix factorization using MovieLens 20M — captures long-term taste via confidence-weighted user–item interactions.',
                  dataset: 'MovieLens 20M',
                  lib: 'implicit / LightFM',
                },
                {
                  badge: 'GRU4Rec' as const,
                  name: 'Session-Based GRU',
                  desc: 'Gated Recurrent Unit model that predicts your next movie based on the temporal sequence of your current viewing session.',
                  dataset: 'Timestamped sessions',
                  lib: 'PyTorch / RecBole',
                },
                {
                  badge: 'KnowledgeGraph' as const,
                  name: 'Knowledge Graph',
                  desc: 'Neo4j graph of movies, genres, cast, directors, and keywords from TMDB. Enables semantic traversal and cold-start recommendations.',
                  dataset: 'TMDB API (~24K movies)',
                  lib: 'Neo4j / PyKEEN',
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

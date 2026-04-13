import { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Sparkles, X, SlidersHorizontal, Star, ChevronDown } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { Movie, ModelType } from '../types';
import { MOVIES, ALL_GENRES, EXAMPLE_QUERIES } from '../data/mockData';
import RecommendationBadge from '../components/RecommendationBadge';

const MODEL_FILTERS: { label: string; value: ModelType | 'All' }[] = [
  { label: 'All Models', value: 'All' },
  { label: 'OCCF', value: 'OCCF' },
  { label: 'GRU4Rec', value: 'GRU4Rec' },
  { label: 'Knowledge Graph', value: 'KnowledgeGraph' },
  { label: 'Hybrid', value: 'Hybrid' },
];

function simulateSearch(query: string): { interpreted: string; filters: string[]; results: Movie[] } {
  const q = query.toLowerCase();
  let results = [...MOVIES];
  const filters: string[] = [];
  let interpreted = query;

  if (q.includes('sci-fi') || q.includes('science fiction') || q.includes('space') || q.includes('future')) {
    results = results.filter((m) => m.genres.includes('Sci-Fi'));
    filters.push('Genre: Sci-Fi');
    interpreted = `Science Fiction films — speculative, futuristic, or conceptually ambitious`;
  } else if (q.includes('nolan') || q.includes('christopher')) {
    results = results.filter((m) => m.director.toLowerCase().includes('nolan'));
    filters.push('Director: Christopher Nolan');
    interpreted = `Films directed by Christopher Nolan — known for non-linear storytelling`;
  } else if (q.includes('thriller') || q.includes('suspense') || q.includes('dark')) {
    results = results.filter((m) => m.genres.includes('Thriller') || m.genres.includes('Crime'));
    filters.push('Genre: Thriller / Crime');
    interpreted = `Dark, suspenseful thrillers with psychological depth`;
  } else if (q.includes('drama')) {
    results = results.filter((m) => m.genres.includes('Drama'));
    filters.push('Genre: Drama');
    interpreted = `Character-driven dramas with emotional depth`;
  } else if (q.includes('inception') || q.includes('mind') || q.includes('complex')) {
    results = results.filter((m) => m.genres.includes('Sci-Fi') || m.genres.includes('Thriller'));
    filters.push('Theme: Mind-bending / Complex narrative');
    interpreted = `Mind-bending films with complex, layered narratives`;
  } else if (q.includes('parasite') || q.includes('class') || q.includes('social')) {
    results = results.filter((m) =>
      ['Parasite', 'Joker', 'Get Out', 'Fight Club', 'Pulp Fiction'].includes(m.title)
    );
    filters.push('Theme: Social commentary');
    interpreted = `Films exploring class divide, inequality, and social critique`;
  } else if (q.length > 0) {
    // Generic relevance sort
    results = results.sort(() => Math.random() - 0.4);
    interpreted = `Movies matching: "${query}"`;
  }

  return { interpreted, filters, results: results.slice(0, 12) };
}

export default function Search() {
  const [query, setQuery] = useState('');
  const [submitted, setSubmitted] = useState(false);
  const [isInterpreting, setIsInterpreting] = useState(false);
  const [interpretedQuery, setInterpretedQuery] = useState('');
  const [appliedFilters, setAppliedFilters] = useState<string[]>([]);
  const [results, setResults] = useState<Movie[]>([]);
  const [activeGenres, setActiveGenres] = useState<string[]>([]);
  const [minRating, setMinRating] = useState(0);
  const [activeModel, setActiveModel] = useState<ModelType | 'All'>('All');
  const [showFilters, setShowFilters] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const handleSearch = async (q: string = query) => {
    if (!q.trim()) return;
    setQuery(q);
    setSubmitted(true);
    setIsInterpreting(true);
    setResults([]);
    setInterpretedQuery('');

    // Simulate LLM interpretation delay
    await new Promise((r) => setTimeout(r, 900));
    const { interpreted, filters, results: res } = simulateSearch(q);
    setInterpretedQuery(interpreted);
    setAppliedFilters(filters);
    setIsInterpreting(false);
    setResults(res);
  };

  const filteredResults = results
    .filter((m) => activeGenres.length === 0 || activeGenres.some((g) => m.genres.includes(g)))
    .filter((m) => m.rating >= minRating)
    .filter((m) =>
      activeModel === 'All' ||
      m.recommendationSources?.some((s) => s.model === activeModel)
    );

  const clearSearch = () => {
    setQuery('');
    setSubmitted(false);
    setResults([]);
    setInterpretedQuery('');
    setAppliedFilters([]);
    setActiveGenres([]);
    setMinRating(0);
    setActiveModel('All');
    inputRef.current?.focus();
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-[#0f0f0f] pt-24 pb-20 px-6 md:px-10"
    >
      <div className="max-w-screen-xl mx-auto">
        {/* Page header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles size={18} className="text-amber-400" />
            <span className="text-xs font-semibold text-amber-400 uppercase tracking-widest">
              LLM-Powered Search
            </span>
          </div>
          <h1 className="text-3xl font-bold text-white">Discover Movies</h1>
          <p className="text-[#666] text-sm mt-1">
            Describe what you're in the mood for — our LLM interprets your query across all three recommendation models.
          </p>
        </div>

        {/* Search input */}
        <div className="relative mb-4">
          <div className="flex items-center gap-3 px-5 py-4 bg-[#1a1a1a] border border-white/10 rounded-2xl
                          focus-within:border-white/30 focus-within:bg-[#1d1d1d] transition-all duration-200">
            <Search size={20} className="text-[#666] shrink-0" />
            <input
              ref={inputRef}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Try: 'mind-bending sci-fi like Inception' or 'movies directed by Nolan'"
              className="flex-1 bg-transparent text-white text-base placeholder:text-[#555] outline-none"
            />
            {query && (
              <button onClick={clearSearch} className="text-[#666] hover:text-white transition-colors">
                <X size={18} />
              </button>
            )}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => handleSearch()}
              className="px-5 py-2 bg-[#E50914] text-white text-sm font-semibold rounded-xl hover:bg-[#f40612] transition-colors shrink-0"
            >
              Search
            </motion.button>
          </div>
        </div>

        {/* Example queries */}
        {!submitted && (
          <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            <p className="text-xs text-[#555] mb-3 uppercase tracking-widest">Try asking:</p>
            <div className="flex flex-wrap gap-2">
              {EXAMPLE_QUERIES.map((q) => (
                <button
                  key={q}
                  onClick={() => handleSearch(q)}
                  className="text-sm text-[#aaa] border border-white/10 px-4 py-2 rounded-full
                             hover:border-white/30 hover:text-white hover:bg-white/5 transition-all duration-200"
                >
                  {q}
                </button>
              ))}
            </div>
          </motion.div>
        )}

        {/* LLM Interpretation Panel */}
        <AnimatePresence>
          {submitted && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="mt-6 p-4 rounded-xl border border-amber-500/20 bg-amber-500/5"
            >
              <div className="flex items-start gap-3">
                <div className="w-7 h-7 rounded-lg bg-amber-500/20 flex items-center justify-center shrink-0 mt-0.5">
                  <Sparkles size={14} className="text-amber-400" />
                </div>
                <div className="flex-1">
                  <p className="text-xs font-semibold text-amber-400 uppercase tracking-widest mb-1">
                    LLM Interpretation
                  </p>
                  {isInterpreting ? (
                    <div className="flex items-center gap-2">
                      <div className="flex gap-1">
                        {[0, 1, 2].map((i) => (
                          <motion.div
                            key={i}
                            className="w-1.5 h-1.5 rounded-full bg-amber-400"
                            animate={{ opacity: [0.3, 1, 0.3] }}
                            transition={{ duration: 1, delay: i * 0.2, repeat: Infinity }}
                          />
                        ))}
                      </div>
                      <span className="text-sm text-[#888]">Interpreting your query with LLM...</span>
                    </div>
                  ) : (
                    <p className="text-sm text-[#ddd]">
                      "{interpretedQuery}"
                    </p>
                  )}
                  {appliedFilters.length > 0 && !isInterpreting && (
                    <div className="flex flex-wrap gap-2 mt-2">
                      {appliedFilters.map((f) => (
                        <span key={f} className="text-xs bg-amber-500/15 text-amber-300 border border-amber-500/25 px-2 py-0.5 rounded">
                          {f}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Filters bar */}
        <AnimatePresence>
          {submitted && !isInterpreting && results.length > 0 && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-5"
            >
              <div className="flex items-center justify-between mb-3">
                <p className="text-sm text-[#888]">
                  <span className="text-white font-medium">{filteredResults.length}</span> results
                </p>
                <button
                  onClick={() => setShowFilters((f) => !f)}
                  className="flex items-center gap-2 text-sm text-[#aaa] hover:text-white transition-colors"
                >
                  <SlidersHorizontal size={15} />
                  Filters
                  <ChevronDown
                    size={14}
                    className={`transition-transform ${showFilters ? 'rotate-180' : ''}`}
                  />
                </button>
              </div>

              {/* Expandable filters */}
              <AnimatePresence>
                {showFilters && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="p-4 bg-[#1a1a1a] rounded-xl border border-white/10 mb-4 space-y-4">
                      {/* Model filter */}
                      <div>
                        <p className="text-xs text-[#666] uppercase tracking-widest mb-2">Recommendation Model</p>
                        <div className="flex flex-wrap gap-2">
                          {MODEL_FILTERS.map((f) => (
                            <button
                              key={f.value}
                              onClick={() => setActiveModel(f.value)}
                              className={`text-xs px-3 py-1.5 rounded-full border transition-all ${
                                activeModel === f.value
                                  ? 'border-white/40 bg-white/10 text-white'
                                  : 'border-white/10 text-[#888] hover:border-white/20 hover:text-[#ccc]'
                              }`}
                            >
                              {f.label}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Genre filter */}
                      <div>
                        <p className="text-xs text-[#666] uppercase tracking-widest mb-2">Genre</p>
                        <div className="flex flex-wrap gap-2">
                          {ALL_GENRES.map((g) => (
                            <button
                              key={g}
                              onClick={() =>
                                setActiveGenres((prev) =>
                                  prev.includes(g) ? prev.filter((x) => x !== g) : [...prev, g]
                                )
                              }
                              className={`text-xs px-3 py-1.5 rounded-full border transition-all ${
                                activeGenres.includes(g)
                                  ? 'border-[#E50914]/60 bg-[#E50914]/10 text-[#ff6b6b]'
                                  : 'border-white/10 text-[#888] hover:border-white/20 hover:text-[#ccc]'
                              }`}
                            >
                              {g}
                            </button>
                          ))}
                        </div>
                      </div>

                      {/* Min rating */}
                      <div>
                        <p className="text-xs text-[#666] uppercase tracking-widest mb-2">
                          Min Rating: <span className="text-white">{minRating > 0 ? `${minRating}+` : 'Any'}</span>
                        </p>
                        <div className="flex gap-2">
                          {[0, 7, 7.5, 8, 8.5, 9].map((r) => (
                            <button
                              key={r}
                              onClick={() => setMinRating(r)}
                              className={`flex items-center gap-1 text-xs px-3 py-1.5 rounded-full border transition-all ${
                                minRating === r
                                  ? 'border-yellow-500/60 bg-yellow-500/10 text-yellow-400'
                                  : 'border-white/10 text-[#888] hover:border-white/20'
                              }`}
                            >
                              {r > 0 && <Star size={10} fill="currentColor" className="text-yellow-400" />}
                              {r === 0 ? 'Any' : `${r}+`}
                            </button>
                          ))}
                        </div>
                      </div>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Search Results Grid */}
        <AnimatePresence>
          {!isInterpreting && filteredResults.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mt-6 grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4"
            >
              {filteredResults.map((movie, i) => (
                <motion.div
                  key={movie.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  onClick={() => navigate(`/movie/${movie.id}`)}
                  className="cursor-pointer group"
                >
                  {/* Poster */}
                  <div
                    className="relative h-48 rounded-lg overflow-hidden mb-2 transition-transform duration-200 group-hover:scale-105"
                    style={{
                      background: `linear-gradient(160deg, ${movie.gradient[0]} 0%, ${movie.gradient[1]} 100%)`,
                    }}
                  >
                    <div className="absolute top-0 left-0 right-0 h-1" style={{ background: movie.accentColor }} />
                    <div className="absolute top-2 right-2 flex items-center gap-1 px-1.5 py-0.5 bg-black/60 rounded text-[10px] font-bold text-yellow-400">
                      <Star size={8} fill="currentColor" />
                      {movie.rating.toFixed(1)}
                    </div>
                    {movie.recommendationSources?.[0] && (
                      <div className="absolute top-2 left-2">
                        <RecommendationBadge model={movie.recommendationSources[0].model} size="sm" />
                      </div>
                    )}
                    <div className="absolute bottom-0 inset-x-0 p-3 bg-gradient-to-t from-black/90 to-transparent">
                      <p className="text-white text-xs font-bold leading-tight">{movie.title}</p>
                    </div>
                  </div>

                  <div>
                    <p className="text-[#888] text-xs">{movie.year} · {movie.genres[0]}</p>
                    {movie.recommendationSources?.[0] && (
                      <p className="text-[10px] text-[#555] mt-0.5 line-clamp-1">
                        {movie.recommendationSources[0].reason}
                      </p>
                    )}
                  </div>
                </motion.div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Empty state */}
        {submitted && !isInterpreting && filteredResults.length === 0 && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="mt-16 text-center"
          >
            <div className="w-16 h-16 rounded-2xl bg-[#1a1a1a] border border-white/10 flex items-center justify-center mx-auto mb-4">
              <Search size={28} className="text-[#444]" />
            </div>
            <p className="text-[#888] text-lg font-medium mb-2">No results found</p>
            <p className="text-[#555] text-sm">Try adjusting your filters or searching with different terms</p>
          </motion.div>
        )}
      </div>
    </motion.div>
  );
}

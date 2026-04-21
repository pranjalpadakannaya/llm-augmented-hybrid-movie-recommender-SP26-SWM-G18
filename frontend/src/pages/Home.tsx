import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import HeroBanner from '../components/HeroBanner';
import MovieRow from '../components/MovieRow';
import { checkHealth, fetchRecommendations } from '../api/client';
import { MOVIES, HOME_ROWS } from '../data/mockData';
import { Movie, RowConfig, ModelType } from '../types';

const ROW_DEFS: Array<{
  id: string;
  title: string;
  subtitle: string;
  apiModel: string;
  modelType: ModelType;
  query?: string;
}> = [
  {
    id: 'top-picks',
    title: 'Top Picks for You',
    subtitle: 'Based on your long-term viewing history · OCCF Model',
    apiModel: 'occf',
    modelType: 'OCCF',
  },
  {
    id: 'continue-session',
    title: 'Continue Your Session',
    subtitle: 'Next-item predictions from your watch pattern · GRU4Rec',
    apiModel: 'gru4rec',
    modelType: 'GRU4Rec',
  },
  {
    id: 'semantic-matches',
    title: 'Semantic Matches',
    subtitle: 'Connections via Knowledge Graph · TMDB metadata',
    apiModel: 'kg',
    modelType: 'KnowledgeGraph',
  },
  {
    id: 'trending',
    title: 'Trending Now',
    subtitle: 'Popular across all users this week',
    apiModel: 'trending',
    modelType: 'Trending',
  },
  {
    id: 'hybrid-fusion',
    title: 'Hybrid Fusion Picks',
    subtitle: 'Unified ranking from all three models combined',
    apiModel: 'hybrid',
    modelType: 'Hybrid',
  },
  {
    id: 'sci-fi',
    title: 'Sci-Fi Deep Cuts',
    subtitle: 'Semantic cluster: science fiction & speculative worlds',
    apiModel: 'kg',
    modelType: 'KnowledgeGraph',
    query: 'science fiction space future artificial intelligence dystopia',
  },
];

const MOCK_HERO: Movie[] = [MOVIES[1], MOVIES[6], MOVIES[9], MOVIES[0], MOVIES[3]];

export default function Home() {
  const [rows, setRows] = useState<RowConfig[]>(HOME_ROWS);
  const [heroMovies, setHeroMovies] = useState<Movie[]>(MOCK_HERO);
  const [warming, setWarming] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      const results = await Promise.allSettled(
        ROW_DEFS.map((def) => fetchRecommendations(def.apiModel, 1, 10, def.query)),
      );
      if (cancelled) return;

      const newRows: RowConfig[] = ROW_DEFS.map((def, i) => {
        const r = results[i];
        if (r.status === 'fulfilled' && r.value.length > 0) {
          return {
            id: def.id,
            title: def.title,
            subtitle: def.subtitle,
            model: def.modelType,
            movies: r.value,
          };
        }
        return HOME_ROWS[i] ?? HOME_ROWS[0];
      });

      setRows(newRows);

      const hybridResult = results[4];
      if (hybridResult.status === 'fulfilled' && hybridResult.value.length >= 5) {
        setHeroMovies(hybridResult.value.slice(0, 5));
      }
    }

    async function init() {
      try {
        const health = await checkHealth();
        if (!health.ready) {
          setWarming(true);
          pollRef.current = setInterval(async () => {
            try {
              const h = await checkHealth();
              if (h.ready && !cancelled) {
                clearInterval(pollRef.current!);
                setWarming(false);
                await loadData();
              }
            } catch {
              // keep polling
            }
          }, 8000);
          return;
        }
        await loadData();
      } catch {
        // API unavailable — keep mock data
      }
    }

    init();
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-[#0f0f0f]"
    >
      {warming && (
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 bg-[#1a1a1a] border border-amber-500/30 rounded-xl shadow-2xl">
          <div className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
          <span className="text-xs text-amber-300">Models warming up…</span>
        </div>
      )}

      <HeroBanner movies={heroMovies} />

      <div className="mt-4 space-y-8 pb-16">
        {rows.map((row, index) => (
          <MovieRow key={row.id} row={row} index={index} />
        ))}
      </div>
    </motion.div>
  );
}

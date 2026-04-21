import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import HeroBanner from '../components/HeroBanner';
import MovieRow from '../components/MovieRow';
import { checkHealth, fetchRecommendations } from '../api/client';
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
    id: 'hybrid-picks',
    title: 'Hybrid Picks For You',
    subtitle: 'Fusion ranking across collaborative, session, and knowledge-graph signals',
    apiModel: 'hybrid',
    modelType: 'Hybrid',
  },
  {
    id: 'hybrid-sci-fi',
    title: 'Hybrid Sci-Fi Picks',
    subtitle: 'Fusion model boosted by a science-fiction query',
    apiModel: 'hybrid',
    modelType: 'Hybrid',
    query: 'science fiction space future artificial intelligence dystopia',
  },
  {
    id: 'hybrid-thrillers',
    title: 'Hybrid Thriller Picks',
    subtitle: 'Fusion model boosted by suspense, crime, and psychological themes',
    apiModel: 'hybrid',
    modelType: 'Hybrid',
    query: 'psychological thriller crime suspense mystery dark',
  },
  {
    id: 'hybrid-drama',
    title: 'Hybrid Drama Picks',
    subtitle: 'Fusion model boosted by drama, emotion, and character-driven storytelling',
    apiModel: 'hybrid',
    modelType: 'Hybrid',
    query: 'drama emotional character relationships award-winning',
  },
  {
    id: 'hybrid-classics',
    title: 'Hybrid Classics',
    subtitle: 'Fusion model boosted by timeless, critically acclaimed cinema',
    apiModel: 'hybrid',
    modelType: 'Hybrid',
    query: 'classic masterpiece iconic cinema all-time great',
  },
  {
    id: 'hybrid-trending',
    title: 'Hybrid Trending',
    subtitle: 'Fusion model over popular and active taste signals',
    apiModel: 'hybrid',
    modelType: 'Hybrid',
    query: 'popular trending widely loved recent favorites',
  },
];

export default function Home({ userId }: { userId: number }) {
  const [rows, setRows] = useState<RowConfig[]>([]);
  const [heroMovies, setHeroMovies] = useState<Movie[]>([]);
  const [warming, setWarming] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      const results = await Promise.allSettled(
        ROW_DEFS.map((def) => fetchRecommendations(def.apiModel, userId, 10, def.query)),
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
        return null;
      }).filter((row): row is RowConfig => row !== null);

      setRows(newRows);

      const hybridResult = results[4];
      if (hybridResult.status === 'fulfilled' && hybridResult.value.length >= 5) {
        setHeroMovies(hybridResult.value.slice(0, 5));
      } else if (newRows.length > 0) {
        setHeroMovies(newRows[0].movies.slice(0, 5));
      }

      if (newRows.length === 0) {
        setError('The backend did not return any recommendation rows.');
      } else {
        setError('');
      }
      setLoading(false);
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
        if (!cancelled) {
          setError('The frontend could not reach the backend API.');
          setLoading(false);
        }
      }
    }

    init();
    return () => {
      cancelled = true;
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [userId]);

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

      {heroMovies.length > 0 ? (
        <HeroBanner movies={heroMovies} />
      ) : (
        <div className="min-h-[60vh] flex items-center justify-center px-6">
          <div className="text-center max-w-md">
            {loading || warming ? (
              <>
                <div className="w-10 h-10 border-2 border-[#E50914] border-t-transparent rounded-full animate-spin mx-auto mb-4" />
                <p className="text-white text-lg font-semibold">Loading recommendations</p>
                <p className="text-[#777] text-sm mt-2">The homepage will populate once the backend finishes loading models and metadata.</p>
              </>
            ) : (
              <>
                <p className="text-white text-lg font-semibold">No backend data available</p>
                <p className="text-[#777] text-sm mt-2">{error || 'Start the backend and load the processed dataset to see recommendations here.'}</p>
              </>
            )}
          </div>
        </div>
      )}

      <div className="mt-4 space-y-8 pb-16">
        {rows.map((row, index) => (
          <MovieRow key={row.id} row={row} index={index} />
        ))}
      </div>
    </motion.div>
  );
}

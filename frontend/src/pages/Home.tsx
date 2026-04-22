import { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import HeroBanner from '../components/HeroBanner';
import MovieRow from '../components/MovieRow';
import { checkHealth, fetchHome } from '../api/client';
import { Movie, RowConfig } from '../types';

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
      try {
        const data = await fetchHome(userId);
        if (cancelled) return;

        setHeroMovies(data.heroMovies || []);
        setRows(
          (data.rows || []).map((row: any) => ({
            id: row.id,
            title: row.title,
            subtitle: row.subtitle,
            model: 'Hybrid',
            movies: row.movies || [],
          }))
        );

        setError('');
      } catch {
        if (!cancelled) {
          setError('The frontend could not reach the backend API.');
        }
      } finally {
        if (!cancelled) setLoading(false);
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
                if (pollRef.current) clearInterval(pollRef.current);
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
        <div className="fixed bottom-6 right-6 z-50 flex items-center gap-3 rounded-xl border border-amber-500/30 bg-[#1a1a1a] px-4 py-3 shadow-2xl">
          <div className="h-2 w-2 animate-pulse rounded-full bg-amber-400" />
          <span className="text-xs text-amber-300">Models warming up…</span>
        </div>
      )}

      {heroMovies.length > 0 ? (
        <HeroBanner movies={heroMovies} />
      ) : (
        <div className="flex min-h-[60vh] items-center justify-center px-6">
          <div className="max-w-md text-center">
            {loading || warming ? (
              <>
                <div className="mx-auto mb-4 h-10 w-10 animate-spin rounded-full border-2 border-[#E50914] border-t-transparent" />
                <p className="text-lg font-semibold text-white">
                  Loading recommendations
                </p>
                <p className="mt-2 text-sm text-[#777]">
                  The homepage will populate once the backend finishes loading models and metadata.
                </p>
              </>
            ) : (
              <>
                <p className="text-lg font-semibold text-white">
                  No backend data available
                </p>
                <p className="mt-2 text-sm text-[#777]">
                  {error || 'Start the backend and load the processed dataset to see recommendations here.'}
                </p>
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
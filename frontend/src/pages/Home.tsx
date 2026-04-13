import { motion } from 'framer-motion';
import HeroBanner from '../components/HeroBanner';
import MovieRow from '../components/MovieRow';
import { MOVIES, HOME_ROWS } from '../data/mockData';

const HERO_MOVIES = [MOVIES[1], MOVIES[6], MOVIES[9], MOVIES[0], MOVIES[3]];

export default function Home() {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.4 }}
      className="min-h-screen bg-[#0f0f0f]"
    >
      {/* Hero banner */}
      <HeroBanner movies={HERO_MOVIES} />

      {/* Recommendation rows */}
      <div className="mt-4 space-y-8 pb-16">
        {HOME_ROWS.map((row, index) => (
          <MovieRow key={row.id} row={row} index={index} />
        ))}
      </div>
    </motion.div>
  );
}

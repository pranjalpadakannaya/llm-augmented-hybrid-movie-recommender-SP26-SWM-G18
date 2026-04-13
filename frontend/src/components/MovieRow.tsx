import { useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { RowConfig } from '../types';
import MovieCard from './MovieCard';
import RecommendationBadge from './RecommendationBadge';

interface Props {
  row: RowConfig;
  index?: number;
}

export default function MovieRow({ row, index = 0 }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(true);

  const scroll = (dir: 'left' | 'right') => {
    const el = ref.current;
    if (!el) return;
    const amount = el.clientWidth * 0.75;
    el.scrollBy({ left: dir === 'right' ? amount : -amount, behavior: 'smooth' });
  };

  const handleScroll = () => {
    const el = ref.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 0);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 10);
  };

  return (
    <motion.section
      initial={{ opacity: 0, y: 24 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.5, delay: index * 0.05 }}
      className="group/row"
    >
      {/* Row header */}
      <div className="flex items-end justify-between mb-3 px-6 md:px-10">
        <div>
          <div className="flex items-center gap-3 mb-1">
            <h2 className="text-lg font-bold text-white">{row.title}</h2>
            <RecommendationBadge model={row.model} size="sm" />
          </div>
          {row.subtitle && (
            <p className="text-xs text-[#666]">{row.subtitle}</p>
          )}
        </div>

        {/* Explore all */}
        <button className="text-xs text-[#aaa] hover:text-white opacity-0 group-hover/row:opacity-100 transition-all duration-200 whitespace-nowrap">
          Explore all →
        </button>
      </div>

      {/* Scroll container */}
      <div className="relative">
        {/* Left arrow */}
        {canScrollLeft && (
          <button
            onClick={() => scroll('left')}
            className="absolute left-0 top-0 bottom-0 z-20 w-14 flex items-center justify-center
                       bg-gradient-to-r from-[#0f0f0f] to-transparent
                       opacity-0 group-hover/row:opacity-100 transition-opacity duration-200"
          >
            <motion.div
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              className="w-9 h-9 rounded-full glass-card border border-white/10 flex items-center justify-center shadow-lg"
            >
              <ChevronLeft size={18} className="text-white" />
            </motion.div>
          </button>
        )}

        {/* Right arrow */}
        {canScrollRight && (
          <button
            onClick={() => scroll('right')}
            className="absolute right-0 top-0 bottom-0 z-20 w-14 flex items-center justify-center
                       bg-gradient-to-l from-[#0f0f0f] to-transparent
                       opacity-0 group-hover/row:opacity-100 transition-opacity duration-200"
          >
            <motion.div
              whileHover={{ scale: 1.1 }}
              whileTap={{ scale: 0.9 }}
              className="w-9 h-9 rounded-full glass-card border border-white/10 flex items-center justify-center shadow-lg"
            >
              <ChevronRight size={18} className="text-white" />
            </motion.div>
          </button>
        )}

        {/* Movie cards track */}
        <div
          ref={ref}
          onScroll={handleScroll}
          className="flex gap-3 overflow-x-auto hide-scrollbar px-6 md:px-10 pb-4"
        >
          {row.movies.map((movie, i) => (
            <motion.div
              key={movie.id}
              initial={{ opacity: 0, x: 20 }}
              whileInView={{ opacity: 1, x: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.35, delay: i * 0.04 }}
            >
              <MovieCard movie={movie} size="md" />
            </motion.div>
          ))}
        </div>
      </div>
    </motion.section>
  );
}

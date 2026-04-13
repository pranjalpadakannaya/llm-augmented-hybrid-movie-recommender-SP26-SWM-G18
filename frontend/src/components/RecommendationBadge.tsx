import { ModelType } from '../types';

interface Props {
  model: ModelType;
  size?: 'sm' | 'md';
}

const MODEL_CONFIG: Record<ModelType, { label: string; className: string; icon: string }> = {
  OCCF: {
    label: 'OCCF',
    className: 'bg-blue-500/20 text-blue-300 border-blue-500/40',
    icon: '◈',
  },
  GRU4Rec: {
    label: 'Session',
    className: 'bg-emerald-500/20 text-emerald-300 border-emerald-500/40',
    icon: '⟳',
  },
  KnowledgeGraph: {
    label: 'KG',
    className: 'bg-violet-500/20 text-violet-300 border-violet-500/40',
    icon: '⬡',
  },
  Hybrid: {
    label: 'Hybrid',
    className: 'bg-amber-500/20 text-amber-300 border-amber-500/40',
    icon: '◎',
  },
  Trending: {
    label: 'Trending',
    className: 'bg-red-500/20 text-red-300 border-red-500/40',
    icon: '↑',
  },
};

export default function RecommendationBadge({ model, size = 'sm' }: Props) {
  const config = MODEL_CONFIG[model];
  const sizeClass = size === 'sm' ? 'text-[10px] px-1.5 py-0.5' : 'text-xs px-2 py-1';

  return (
    <span
      className={`inline-flex items-center gap-1 rounded border font-semibold tracking-wide ${config.className} ${sizeClass}`}
    >
      <span>{config.icon}</span>
      {config.label}
    </span>
  );
}

export { MODEL_CONFIG };

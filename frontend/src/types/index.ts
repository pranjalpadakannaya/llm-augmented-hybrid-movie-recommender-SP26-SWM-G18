export type ModelType = 'OCCF' | 'GRU4Rec' | 'KnowledgeGraph' | 'Hybrid' | 'Trending';

export interface RecommendationSource {
  model: ModelType;
  score: number;
  reason: string;
}

export interface Movie {
  id: number;
  title: string;
  year: number;
  rating: number;
  userRating?: number;
  runtime: number;
  genres: string[];
  overview: string;
  gradient: [string, string];
  accentColor: string;
  director: string;
  cast: string[];
  tmdbId: number;
  movieLensId: number;
  maturityRating: string;
  posterPath: string;
  posterUrl: string;
  backdropPath: string;
  backdropUrl: string;
  recommendationSources?: RecommendationSource[];
}

export interface RowConfig {
  id: string;
  title: string;
  subtitle: string;
  model: ModelType;
  movies: Movie[];
}

export interface GenreStat {
  genre: string;
  percentage: number;
  color: string;
}

export interface ModelContribution {
  model: ModelType;
  label: string;
  percentage: number;
  color: string;
  description: string;
}

export interface UserProfile {
  userId: number;
  id: string;
  displayName: string;
  initials: string;
  avatarColor: string;
  historySummary: string;
  favoriteGenres: GenreStat[];
  totalWatched: number;
  memberSince: string;
  avgRating: number;
  activeModels: number;
  recentActivity: number;
  modelContributions: ModelContribution[];
  recentMovies: Movie[];
  topRatedMovies: Movie[];
  summaryStats: Array<{
    label: string;
    value: string;
  }>;
}

export interface UserOption {
  userId: number;
  displayName: string;
  initials: string;
  avatarColor: string;
  historySummary: string;
  favoriteGenres: GenreStat[];
}

export interface SearchState {
  query: string;
  interpretedQuery: string | null;
  appliedFilters: string[];
  results: Movie[];
  isLoading: boolean;
  activeGenres: string[];
  minRating: number;
  activeModel: ModelType | 'All';
}

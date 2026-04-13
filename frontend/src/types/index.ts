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
  id: string;
  name: string;
  initials: string;
  avatarColor: string;
  favoriteGenres: GenreStat[];
  totalWatched: number;
  memberSince: string;
  modelContributions: ModelContribution[];
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

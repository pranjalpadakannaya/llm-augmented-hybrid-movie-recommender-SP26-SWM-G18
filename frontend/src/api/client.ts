import { Movie, UserOption, UserProfile } from '../types';

const API = '/api';

export interface HealthResponse {
  ready: boolean;
  status: string;
}

export interface ParsedIntent {
  genres: string[];
  mood: string;
  seed_movies: string[];
  keywords: string[];
  constraints: Record<string, unknown>;
}

export interface SearchResponse {
  interpreted: string;
  filters: string[];
  parsedIntent?: ParsedIntent;
  movies: Movie[];
}

function toMovie(raw: Record<string, unknown>): Movie {
  return {
    id: raw.id as number,
    title: (raw.title as string) || '',
    year: (raw.year as number) || 0,
    rating: (raw.rating as number) || 0,
    userRating: raw.userRating as number | undefined,
    runtime: (raw.runtime as number) || 0,
    genres: (raw.genres as string[]) || [],
    overview: (raw.overview as string) || '',
    gradient: (raw.gradient as [string, string]) || ['#1a1a1a', '#2a2a2a'],
    accentColor: (raw.accentColor as string) || '#E50914',
    director: (raw.director as string) || '',
    cast: (raw.cast as string[]) || [],
    tmdbId: (raw.tmdbId as number) || 0,
    movieLensId: (raw.movieLensId as number) || (raw.id as number),
    maturityRating: (raw.maturityRating as string) || 'NR',
    posterPath: (raw.posterPath as string) || '',
    posterUrl: (raw.posterUrl as string) || '',
    backdropPath: (raw.backdropPath as string) || '',
    backdropUrl: (raw.backdropUrl as string) || '',
    recommendationSources: (raw.recommendationSources as Movie['recommendationSources']) || [],
  };
}

function toProfile(raw: Record<string, unknown>): UserProfile {
  return {
    userId: (raw.userId as number) || 0,
    id: (raw.id as string) || '',
    displayName: (raw.displayName as string) || 'Movie Viewer',
    initials: (raw.initials as string) || 'MV',
    avatarColor: (raw.avatarColor as string) || '#E50914',
    historySummary: (raw.historySummary as string) || '',
    favoriteGenres: (raw.favoriteGenres as UserProfile['favoriteGenres']) || [],
    totalWatched: (raw.totalWatched as number) || 0,
    memberSince: (raw.memberSince as string) || 'Unknown',
    avgRating: (raw.avgRating as number) || 0,
    activeModels: (raw.activeModels as number) || 0,
    recentActivity: (raw.recentActivity as number) || 0,
    modelContributions: (raw.modelContributions as UserProfile['modelContributions']) || [],
    recentMovies: ((raw.recentMovies || []) as Record<string, unknown>[]).map(toMovie),
    topRatedMovies: ((raw.topRatedMovies || []) as Record<string, unknown>[]).map(toMovie),
    summaryStats: (raw.summaryStats as UserProfile['summaryStats']) || [],
  };
}

function toUserOption(raw: Record<string, unknown>): UserOption {
  return {
    userId: (raw.userId as number) || 0,
    displayName: (raw.displayName as string) || 'Movie Viewer',
    initials: (raw.initials as string) || 'MV',
    avatarColor: (raw.avatarColor as string) || '#E50914',
    historySummary: (raw.historySummary as string) || '',
    favoriteGenres: (raw.favoriteGenres as UserOption['favoriteGenres']) || [],
  };
}

export async function checkHealth(): Promise<HealthResponse> {
  const res = await fetch(`${API}/health`);
  if (!res.ok) throw new Error(`health ${res.status}`);
  return res.json();
}

export async function fetchRecommendations(
  model: string,
  userId = 1,
  n = 10,
  query?: string,
): Promise<Movie[]> {
  const p = new URLSearchParams({ user_id: String(userId), model, n: String(n) });
  if (query) p.set('query', query);
  const res = await fetch(`${API}/recommendations?${p}`);
  if (!res.ok) throw new Error(`recs ${res.status}`);
  const data = await res.json();
  return ((data.movies || []) as Record<string, unknown>[]).map(toMovie);
}

export async function searchMovies(query: string, userId = 1): Promise<SearchResponse> {
  const p = new URLSearchParams({ query, user_id: String(userId) });
  const res = await fetch(`${API}/search?${p}`);
  if (!res.ok) throw new Error(`search ${res.status}`);
  const data = await res.json();
  return {
    interpreted: data.interpreted,
    filters: data.filters,
    parsedIntent: data.parsedIntent,
    movies: ((data.movies || []) as Record<string, unknown>[]).map(toMovie),
  };
}

export async function fetchMovieById(movieId: number): Promise<Movie> {
  const res = await fetch(`${API}/movies/${movieId}`);
  if (!res.ok) throw new Error(`movie ${res.status}`);
  return toMovie(await res.json());
}

export async function fetchProfile(userId = 1): Promise<UserProfile> {
  const p = new URLSearchParams({ user_id: String(userId) });
  const res = await fetch(`${API}/profile?${p}`);
  if (!res.ok) throw new Error(`profile ${res.status}`);
  return toProfile(await res.json());
}

export async function fetchUsers(limit = 8): Promise<UserOption[]> {
  const p = new URLSearchParams({ limit: String(limit) });
  const res = await fetch(`${API}/users?${p}`);
  if (!res.ok) throw new Error(`users ${res.status}`);
  const data = await res.json();
  return ((data.users || []) as Record<string, unknown>[]).map(toUserOption);
}

import { Movie } from '../types';

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
    recommendationSources: (raw.recommendationSources as Movie['recommendationSources']) || [],
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

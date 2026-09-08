import { createClient } from '@supabase/supabase-js';

const apiUrl = import.meta.env.VITE_API_URL;
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const publishableKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;

export const configurationError = [
  !apiUrl && 'VITE_API_URL',
  !supabaseUrl && 'VITE_SUPABASE_URL',
  !publishableKey && 'VITE_SUPABASE_PUBLISHABLE_KEY',
].filter(Boolean).join(', ');

export const supabase = configurationError ? null : createClient(supabaseUrl!, publishableKey!);

export class ApiRequestError extends Error {
  constructor(public status: number, public endpoint: string, message: string) { super(message); }
}

async function authHeaders(): Promise<Headers> {
  const headers = new Headers();
  const token = (await supabase?.auth.getSession())?.data.session?.access_token;
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return headers;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (configurationError) throw new Error(`Configuration manquante : ${configurationError}`);
  const headers = new Headers(init.headers);
  for (const [name, value] of (await authHeaders()).entries()) headers.set(name, value);
  const response = await fetch(`${apiUrl}/api${path}`, { ...init, headers });
  if (!response.ok) {
    const body = await response.text();
    let message = body;
    try { message = JSON.parse(body).detail || body; } catch { /* Plain-text backend error. */ }
    console.error('API request failed', { status: response.status, endpoint: path, message });
    throw new ApiRequestError(response.status, path, message);
  }
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined as T;
  }
  return response.json() as Promise<T>;
}

export function apiErrorLabel(error: unknown, fallback: string) {
  return error instanceof ApiRequestError ? `${fallback} : HTTP ${error.status}` : fallback;
}

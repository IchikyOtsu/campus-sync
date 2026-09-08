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
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export async function uploadIcs(file: File) {
  const form = new FormData();
  form.append('file', file);
  return api('/me/imports/ics-file', { method: 'POST', body: form });
}

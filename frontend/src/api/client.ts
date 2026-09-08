import { createClient } from '@supabase/supabase-js';
const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseKey = import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY;
export const supabase = supabaseUrl && supabaseKey ? createClient(supabaseUrl, supabaseKey) : null;
async function headers(): Promise<Headers> { const result = new Headers(); const token = (await supabase?.auth.getSession())?.data.session?.access_token; if (token) result.set("Authorization", `Bearer `); return result; }
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> { const response = await fetch(`${apiUrl}/api${path}`, { ...init, headers: new Headers([...(await headers()).entries(), ...new Headers(init.headers).entries()]) }); if (!response.ok) throw new Error(await response.text()); return response.json(); }
export async function uploadIcs(file: File) { const form = new FormData(); form.append('file', file); return api('/me/imports/ics-file', { method: 'POST', body: form }); }

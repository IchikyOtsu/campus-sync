import { For, Show, createResource, createSignal, onCleanup, onMount } from 'solid-js';
import type { Session } from '@supabase/supabase-js';
import { api, configurationError, supabase, uploadIcs } from './api/client';
import './style.css';

type Event = { id: string; title: string; start_at: string; end_at: string; room?: string; event_type?: string; course: { code: string; name: string; institution: string } };
type Profile = { id: string; display_name?: string; timezone: string };
const hour = (value: string) => new Intl.DateTimeFormat('fr-BE', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Brussels' }).format(new Date(value));
const cleanAuthUrl = () => { const url = new URL(window.location.href); if (url.searchParams.has("code") || /(access_token|refresh_token|type=)/.test(url.hash)) { url.searchParams.delete("code"); url.searchParams.delete("type"); url.hash = ""; window.history.replaceState({}, document.title, url); } };

function Auth() {
  const [mode, setMode] = createSignal<'login' | 'signup'>('login');
  const [email, setEmail] = createSignal(''); const [password, setPassword] = createSignal('');
  const [message, setMessage] = createSignal(''); const [loading, setLoading] = createSignal(false);
  const submit = async () => {
    if (!supabase) return;
    setMessage(''); setLoading(true);
    const credentials = { email: email(), password: password() };
    const result = mode() === 'signup'
      ? await supabase.auth.signUp({ ...credentials, options: { emailRedirectTo: `${window.location.origin}/` } })
      : await supabase.auth.signInWithPassword(credentials);
    setLoading(false);
    if (result.error) return setMessage(result.error.message);
    setMessage(mode() === 'signup' ? 'Compte créé. Consultez votre e-mail pour confirmer votre adresse.' : 'Connexion réussie.');
  };
  return <main class="login"><div class="logo">✣ campus-sync</div><h1>{mode() === 'signup' ? 'Créer un compte' : 'Se connecter'}</h1><p>Accédez à votre calendrier interuniversitaire.</p><label>E-mail<input type="email" autocomplete="email" placeholder="vous@universite.be" onInput={e => setEmail(e.currentTarget.value)} /></label><label>Mot de passe<input type="password" autocomplete={mode() === 'signup' ? 'new-password' : 'current-password'} onInput={e => setPassword(e.currentTarget.value)} /></label><button disabled={loading()} onClick={submit}>{loading() ? 'Patientez…' : mode() === 'signup' ? 'Créer mon compte' : 'Se connecter'}</button><Show when={message()}><small>{message()}</small></Show><button class="link" onClick={() => { setMode(mode() === 'signup' ? 'login' : 'signup'); setMessage(''); }}>{mode() === 'signup' ? 'J’ai déjà un compte' : 'Créer un compte'}</button><p class="note">L’authentification est assurée par Supabase.</p></main>;
}
function ConfigError() { return <main class="login"><div class="logo">✣ campus-sync</div><h1>Configuration requise</h1><p>Variables absentes : <b>{configurationError}</b></p><p>Copiez <code>.env.example</code> vers <code>.env</code>, renseignez les valeurs locales puis redémarrez Vite ou Docker.</p></main>; }
function App() {
  const [session, setSession] = createSignal<Session | null>();
  const [events, { refetch }] = createResource(() => session() ? api<Event[]>('/me/events') : Promise.resolve([]));
  const [courses] = createResource(() => session() ? api<any[]>('/me/courses') : Promise.resolve([]));
  const [conflicts] = createResource(() => session() ? api<any[]>('/me/conflicts') : Promise.resolve([]));
  const [profile] = createResource(() => session() ? api<Profile>('/me') : Promise.resolve(undefined));
  const [file, setFile] = createSignal<File>(); const [notice, setNotice] = createSignal('');
  onMount(async () => { if (!supabase) return; const initialSession = (await supabase.auth.getSession()).data.session; setSession(initialSession); if (initialSession) cleanAuthUrl(); const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => { setSession(nextSession); if (nextSession) cleanAuthUrl(); }); onCleanup(() => data.subscription.unsubscribe()); });
  const importFile = async () => { if (!file()) return; try { await uploadIcs(file()!); setNotice('Calendrier importé et synchronisé.'); refetch(); } catch { setNotice('Import impossible. Vérifiez le fichier ICS et votre connexion.'); } };
  if (configurationError) return <ConfigError />;
  if (!session()) return <Auth />;
  return <div class="app"><header><div class="logo">✣ campus-sync</div><nav>Calendrier <span>Mes cours</span><span>Programme</span></nav><span class="profile">{profile()?.display_name || 'Compte connecté'}</span><button onClick={() => supabase?.auth.signOut()}>Déconnexion</button></header><main><section class="hero"><div><label>MASTER EN CYBERSÉCURITÉ · M1</label><h1>Bonjour</h1><p>Votre calendrier provient de vos sources synchronisées.</p></div><div class="import"><b>Importer un calendrier ICS</b><input type="file" accept=".ics,text/calendar" onChange={e => setFile(e.currentTarget.files?.[0])} /><button onClick={importFile}>Importer</button></div></section><Show when={profile.error}><p class="notice">Impossible de créer ou charger votre profil local.</p></Show><Show when={notice()}><p class="notice">{notice()}</p></Show><section class="status"><div><b>Connecteurs</b><span>ICS · opérationnel</span><span>ULB TimeEdit · expérimental</span><span>UCLouvain / UNamur / HE2B · non implémenté</span></div><div class="conflict"><b>{conflicts()?.length || 0} conflit(s)</b><span>Calculés à partir de vos événements réels.</span></div></section><section class="calendar"><h2>Calendrier</h2><Show when={!events.loading} fallback={<p>Chargement…</p>}><Show when={events()?.length} fallback={<p class="empty">Aucun événement. Importez un fichier ICS pour commencer.</p>}><div class="event-list"><For each={events()}>{event => <article><time>{new Date(event.start_at).toLocaleDateString('fr-BE', { weekday: 'short', day: 'numeric', month: 'short' })}<strong>{hour(event.start_at)} — {hour(event.end_at)}</strong></time><div><span>{event.course.institution}</span><h3>{event.title}</h3><p>{event.course.code} · {event.event_type || 'Cours'} · {event.room || 'Salle non précisée'}</p></div></article>}</For></div></Show></Show></section><section class="courses"><h2>Mes cours</h2><For each={courses()}>{item => <div>{item.course.code} — {item.course.name}</div>}</For></section></main></div>;
}
import { render } from 'solid-js/web';
render(() => <App />, document.getElementById('root')!);

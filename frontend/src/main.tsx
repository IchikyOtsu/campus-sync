import { For, Show, createResource, createSignal, onCleanup, onMount } from 'solid-js';
import type { Session } from '@supabase/supabase-js';
import { api, configurationError, supabase, uploadIcs } from './api/client';
import './style.css';

type Event = { id: string; title: string; start_at: string; end_at: string; room?: string; event_type?: string; course: { code: string; name: string; institution: string } };
type Profile = { id: string; display_name?: string; timezone: string };
type AuthProps = { onAuthenticated: (session: Session) => void };
const hour = (value: string) => new Intl.DateTimeFormat('fr-BE', { hour: '2-digit', minute: '2-digit', timeZone: 'Europe/Brussels' }).format(new Date(value));
const cleanAuthUrl = () => { const url = new URL(window.location.href); if (url.searchParams.has('code') || /(access_token|refresh_token|type=)/.test(url.hash)) { url.searchParams.delete('code'); url.searchParams.delete('type'); url.hash = ''; window.history.replaceState({}, document.title, url); } };

function Loading() { return <main class="login"><div class="logo">✣ campus-sync</div><p>Chargement…</p></main>; }
function Auth(props: AuthProps) {
  const [mode, setMode] = createSignal<'login' | 'signup'>('login');
  const [email, setEmail] = createSignal(''); const [password, setPassword] = createSignal('');
  const [message, setMessage] = createSignal(''); const [loading, setLoading] = createSignal(false);
  const submit = async () => {
    if (!supabase) return;
    setMessage(''); setLoading(true);
    const credentials = { email: email(), password: password() };
    const { data, error } = mode() === 'signup'
      ? await supabase.auth.signUp({ ...credentials, options: { emailRedirectTo: `${window.location.origin}/` } })
      : await supabase.auth.signInWithPassword(credentials);
    setLoading(false);
    if (error) return setMessage(error.message);
    if (data.session) { props.onAuthenticated(data.session); cleanAuthUrl(); return; }
    setMessage('Compte créé. Consultez votre e-mail pour confirmer votre adresse.');
  };
  return <main class="login"><div class="logo">✣ campus-sync</div><h1>{mode() === 'signup' ? 'Créer un compte' : 'Se connecter'}</h1><p>Accédez à votre calendrier interuniversitaire.</p><label>E-mail<input type="email" autocomplete="email" placeholder="vous@universite.be" onInput={e => setEmail(e.currentTarget.value)} /></label><label>Mot de passe<input type="password" autocomplete={mode() === 'signup' ? 'new-password' : 'current-password'} onInput={e => setPassword(e.currentTarget.value)} /></label><button disabled={loading()} onClick={submit}>{loading() ? 'Patientez…' : mode() === 'signup' ? 'Créer mon compte' : 'Se connecter'}</button><Show when={message()}><small>{message()}</small></Show><button class="link" onClick={() => { setMode(mode() === 'signup' ? 'login' : 'signup'); setMessage(''); }}>{mode() === 'signup' ? 'J’ai déjà un compte' : 'Créer un compte'}</button><p class="note">L’authentification est assurée par Supabase.</p></main>;
}
function ConfigError() { return <main class="login"><div class="logo">✣ campus-sync</div><h1>Configuration requise</h1><p>Variables absentes : <b>{configurationError}</b></p></main>; }
function ApiError() { return <main class="login"><div class="logo">✣ campus-sync</div><h1>API inaccessible</h1><p>Connexion Supabase réussie, mais le profil campus-sync n’a pas pu être chargé. Vérifiez que l’API est démarrée et que son CORS autorise cette adresse.</p><button onClick={() => supabase?.auth.signOut()}>Déconnexion</button></main>; }
function App() {
  const [session, setSession] = createSignal<Session | null | undefined>(undefined);
  const [profile] = createResource(() => session() ? api<Profile>('/me') : Promise.resolve(undefined));
  const [events, { refetch }] = createResource(() => profile() ? api<Event[]>('/me/events') : Promise.resolve([]));
  const [courses] = createResource(() => profile() ? api<any[]>('/me/courses') : Promise.resolve([]));
  const [conflicts] = createResource(() => profile() ? api<any[]>('/me/conflicts') : Promise.resolve([]));
  const [file, setFile] = createSignal<File>(); const [notice, setNotice] = createSignal('');
  onMount(() => { if (!supabase) return; const timeout = window.setTimeout(() => { if (session() === undefined) setSession(null); }, 5000); void supabase.auth.getSession().then(({ data }) => { window.clearTimeout(timeout); setSession(data.session); if (data.session) cleanAuthUrl(); }).catch(() => { window.clearTimeout(timeout); setSession(null); }); const subscription = supabase.auth.onAuthStateChange((_event, nextSession) => { window.clearTimeout(timeout); setSession(nextSession); if (nextSession) cleanAuthUrl(); }); onCleanup(() => { window.clearTimeout(timeout); subscription.data.subscription.unsubscribe(); }); });
  const importFile = async () => { if (!file()) return; try { await uploadIcs(file()!); setNotice('Calendrier importé et synchronisé.'); refetch(); } catch { setNotice('Import impossible. Vérifiez le fichier ICS et votre connexion.'); } };
  const view = () => {
    if (configurationError) return <ConfigError />;
    if (session() === undefined) return <Loading />;
    if (session() === null) return <Auth onAuthenticated={setSession} />;
    if (profile.loading) return <Loading />;
    if (profile.error) return <ApiError />;
    const user = session()!;
    return <div class="app"><header><div class="logo">✣ campus-sync</div><nav>Calendrier <span>Mes cours</span><span>Programme</span></nav><span class="profile">{profile()?.display_name || user.user.email || 'Compte connecté'}</span><button onClick={() => supabase?.auth.signOut()}>Déconnexion</button></header><main><section class="hero"><div><label>MON ESPACE</label><h1>Bonjour {profile()?.display_name || user.user.email}</h1><p>Votre calendrier interuniversitaire.</p></div><div class="import"><b>Importer un calendrier ICS</b><input type="file" accept=".ics,text/calendar" onChange={e => setFile(e.currentTarget.files?.[0])} /><button onClick={importFile}>Importer</button></div></section><Show when={notice()}><p class="notice">{notice()}</p></Show><section class="status"><div><b>Connecteurs</b><span>ICS · opérationnel</span><span>ULB TimeEdit · expérimental</span><span>UCLouvain / UNamur / HE2B · non implémenté</span></div><div class="conflict"><b>{conflicts()?.length || 0} conflit(s)</b><span>Calculés à partir de vos événements réels.</span></div></section><Show when={courses()?.length} fallback={<section class="courses"><h2>Aucun cours configuré.</h2><p>Commencez par importer votre programme, ajouter un cours ou importer un calendrier ICS.</p><button>Importer mon programme</button> <button>Ajouter un cours</button> <button onClick={() => document.querySelector<HTMLInputElement>('input[type=file]')?.click()}>Importer un calendrier ICS</button></section>}><section class="calendar"><h2>Calendrier</h2><Show when={!events.loading} fallback={<p>Chargement…</p>}><Show when={events()?.length} fallback={<p class="empty">Aucun événement synchronisé.</p>}><div class="event-list"><For each={events()}>{event => <article><time>{new Date(event.start_at).toLocaleDateString('fr-BE', { weekday: 'short', day: 'numeric', month: 'short' })}<strong>{hour(event.start_at)} — {hour(event.end_at)}</strong></time><div><span>{event.course.institution}</span><h3>{event.title}</h3><p>{event.course.code} · {event.event_type || 'Cours'} · {event.room || 'Salle non précisée'}</p></div></article>}</For></div></Show></Show></section><section class="courses"><h2>Mes cours</h2><For each={courses()}>{item => <div>{item.course.code} — {item.course.name}</div>}</For></section></Show></main></div>;
  };
  return <>{view()}</>;
}
import { render } from 'solid-js/web';
render(() => <App />, document.getElementById('root')!);

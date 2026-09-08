import { For, Show, createResource, createSignal, onCleanup, onMount } from 'solid-js';
import type { Session } from '@supabase/supabase-js';
import { api, configurationError, supabase, uploadIcs } from './api/client';
import './style.css';

type Event = { id: string; title: string; start_at: string; end_at: string; room?: string; event_type?: string; course: { code: string; name: string; institution: string } };
type Profile = { id: string; display_name?: string; timezone: string };
type AuthProps = { onAuthenticated: (session: Session) => void };
type TimeEditCourse = { code: string; name: string; external_id: string; academic_year: string; object_type: string };
type CourseSearchProps = { onAdded: () => void };
type ProgramSummary = { id: string; code: string; name: string; academic_year: string; institution: string };
type ProgramDetail = ProgramSummary & { courses: { id: string; home_code: string; provider: string; provider_code: string; name: string; semester: string; connector_status: string; user_status: string }[] };
type ProgramProps = { programs: () => ProgramSummary[] | undefined; onChanged: () => void };
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
function CourseSearch(props: CourseSearchProps) {
  const [query, setQuery] = createSignal(''); const [results, setResults] = createSignal<TimeEditCourse[]>([]);
  const [message, setMessage] = createSignal(''); const [loading, setLoading] = createSignal(false);
  const academicYear = '2026-2027';
  const search = async () => { if (!query().trim()) return setMessage('Saisissez un code ou un nom de cours.'); setLoading(true); setMessage(''); try { const found = await api<TimeEditCourse[]>(`/institutions/ulb/courses/search?q=${encodeURIComponent(query())}&academic_year=${academicYear}`); setResults(found); if (!found.length) setMessage('Cours introuvable dans TimeEdit ULB pour 2026-2027.'); } catch { setMessage('Recherche TimeEdit indisponible. Réessayez plus tard.'); } finally { setLoading(false); } };
  const add = async (course: TimeEditCourse) => { setLoading(true); setMessage(''); try { await api('/institutions/ulb/courses/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: course.code, external_id: course.external_id, academic_year: course.academic_year }) }); setMessage(`${course.code} a été ajouté et synchronisé.`); props.onAdded(); } catch { setMessage('Ajout impossible : TimeEdit n’a retourné aucun événement de cours ou la source est indisponible.'); } finally { setLoading(false); } };
  return <section class="course-search"><div><label>AJOUT AUTOMATIQUE</label><h2>Ajouter un cours</h2></div><div class="course-fields"><label>Établissement<select disabled><option>ULB · TimeEdit public</option></select></label><label>Année académique<select disabled><option>{academicYear}</option></select></label><label>Code ou nom<input value={query()} placeholder="ELEC-H550" onInput={e => setQuery(e.currentTarget.value)} onKeyDown={e => e.key === 'Enter' && search()} /></label><button disabled={loading()} onClick={search}>{loading() ? 'Recherche…' : 'Rechercher'}</button></div><Show when={message()}><p class="search-message">{message()}</p></Show><For each={results()}>{course => <article class="course-result"><div><span>ULB · {course.academic_year}</span><h3>{course.code}</h3><p>{course.name}</p></div><button disabled={loading()} onClick={() => add(course)}>Ajouter à mes cours</button></article>}</For></section>;
}
function ProgramSection(props: ProgramProps) {
  const [detail, setDetail] = createSignal<ProgramDetail>(); const [message, setMessage] = createSignal(''); const [loading, setLoading] = createSignal(false);
  const load = async (program: ProgramSummary) => { try { setDetail(await api<ProgramDetail>(`/me/programs/${program.id}`)); } catch { setMessage('Impossible de charger ce programme.'); } };
  const importProgram = async () => { setLoading(true); setMessage(''); try { const available = await api<ProgramSummary[]>('/programs'); const target = available.find(item => item.code === 'M-SECUC' && item.academic_year === '2026-2027'); if (!target) throw new Error(); const response = await api<ProgramDetail>(`/me/programs/${target.id}`, { method: 'POST' }); setDetail(response); props.onChanged(); } catch { setMessage('Import du programme impossible.'); } finally { setLoading(false); } };
  const addCourse = async (course: ProgramDetail['courses'][number]) => { const program = detail(); if (!program) return; setLoading(true); try { await api(`/me/programs/${program.id}/courses/${course.id}/add`, { method: 'POST' }); setDetail(await api<ProgramDetail>(`/me/programs/${program.id}`)); props.onChanged(); } catch { setMessage('Ajout automatique impossible pour ce cours ULB.'); } finally { setLoading(false); } };
  const current = () => detail() || (props.programs()?.[0] ? (void load(props.programs()![0]), undefined) : undefined);
  return <section class="program-section"><div><label>MON PROGRAMME</label><h2>Programme académique</h2></div><Show when={current()} fallback={<div class="program-empty"><p>Ajoutez votre programme ULB pour voir les cours prévus et leur établissement fournisseur.</p><button disabled={loading()} onClick={importProgram}>{loading() ? 'Import…' : 'Importer M-SECUC · 2026-2027'}</button></div>}><div class="program-title"><b>{detail()?.code}</b><span>{detail()?.name} · {detail()?.academic_year}</span></div><h3>Q1</h3><div class="program-courses"><For each={detail()?.courses.filter(course => course.semester === 'Q1')}>{course => <article><span class={course.user_status === 'added' ? 'status added' : 'status'}>{course.user_status === 'added' ? '✓' : '○'}</span><div><b>{course.home_code}</b><p>{course.provider.toUpperCase()} · {course.provider_code}</p><small>{course.name}</small></div><em>{course.user_status === 'added' ? 'Déjà ajouté' : course.connector_status === 'available' ? <button disabled={loading()} onClick={() => addCourse(course)}>Ajouter à mes cours</button> : 'Connecteur à venir'}</em></article>}</For></div></Show><Show when={message()}><p class="search-message">{message()}</p></Show></section>;
}
function ConfigError() { return <main class="login"><div class="logo">✣ campus-sync</div><h1>Configuration requise</h1><p>Variables absentes : <b>{configurationError}</b></p></main>; }
function ApiError() { return <main class="login"><div class="logo">✣ campus-sync</div><h1>API inaccessible</h1><p>Connexion Supabase réussie, mais le profil campus-sync n’a pas pu être chargé. Vérifiez que l’API est démarrée et que son CORS autorise cette adresse.</p><button onClick={() => supabase?.auth.signOut()}>Déconnexion</button></main>; }
function App() {
  const [session, setSession] = createSignal<Session | null | undefined>(undefined);
  const [profile] = createResource(() => session() ? api<Profile>('/me') : Promise.resolve(undefined));
  const [events, { refetch }] = createResource(() => profile() ? api<Event[]>('/me/events') : Promise.resolve([]));
  const [courses, { refetch: refetchCourses }] = createResource(() => profile() ? api<any[]>('/me/courses') : Promise.resolve([]));
  const [conflicts, { refetch: refetchConflicts }] = createResource(() => profile() ? api<any[]>('/me/conflicts') : Promise.resolve([]));
  const [userPrograms, { refetch: refetchUserPrograms }] = createResource(() => profile() ? api<ProgramSummary[]>('/me/programs') : Promise.resolve([]));
  const [file, setFile] = createSignal<File>(); const [notice, setNotice] = createSignal('');
  const refreshDashboard = () => { void refetch(); void refetchCourses(); void refetchConflicts(); void refetchUserPrograms(); };
  onMount(() => { if (!supabase) return; const timeout = window.setTimeout(() => { if (session() === undefined) setSession(null); }, 5000); void supabase.auth.getSession().then(({ data }) => { window.clearTimeout(timeout); setSession(data.session); if (data.session) cleanAuthUrl(); }).catch(() => { window.clearTimeout(timeout); setSession(null); }); const subscription = supabase.auth.onAuthStateChange((_event, nextSession) => { window.clearTimeout(timeout); setSession(nextSession); if (nextSession) cleanAuthUrl(); }); onCleanup(() => { window.clearTimeout(timeout); subscription.data.subscription.unsubscribe(); }); });
  const importFile = async () => { if (!file()) return; try { await uploadIcs(file()!); setNotice('Calendrier importé et synchronisé.'); refetch(); } catch { setNotice('Import impossible. Vérifiez le fichier ICS et votre connexion.'); } };
  const view = () => {
    if (configurationError) return <ConfigError />;
    if (session() === undefined) return <Loading />;
    if (session() === null) return <Auth onAuthenticated={setSession} />;
    if (profile.loading) return <Loading />;
    if (profile.error) return <ApiError />;
    const user = session()!;
    return <div class="app"><header><div class="logo">✣ campus-sync</div><nav>Calendrier <span>Mes cours</span><span>Programme</span></nav><span class="profile">{profile()?.display_name || user.user.email || 'Compte connecté'}</span><button onClick={() => supabase?.auth.signOut()}>Déconnexion</button></header><main><section class="hero"><div><label>MON ESPACE</label><h1>Bonjour {profile()?.display_name || user.user.email}</h1><p>Votre calendrier interuniversitaire.</p></div></section><CourseSearch onAdded={refreshDashboard} /><ProgramSection programs={userPrograms} onChanged={refreshDashboard} /><Show when={notice()}><p class="notice">{notice()}</p></Show><section class="manual-import"><b>Import manuel / dépannage</b><span>La synchronisation automatique ne fonctionne pas ? Importez un calendrier ICS.</span><input type="file" accept=".ics,text/calendar" onChange={e => setFile(e.currentTarget.files?.[0])} /><button onClick={importFile}>Importer un fichier ICS</button></section><section class="status"><div><b>Connecteurs</b><span>ICS · opérationnel</span><span>ULB TimeEdit · expérimental</span><span>UCLouvain / UNamur / HE2B · non implémenté</span></div><div class="conflict"><b>{conflicts()?.length || 0} conflit(s)</b><span>Calculés à partir de vos événements réels.</span></div></section><Show when={courses()?.length} fallback={<section class="courses"><h2>Aucun cours configuré.</h2><p>Commencez par importer votre programme, ajouter un cours ou importer un calendrier ICS.</p><button>Importer mon programme</button> <button>Ajouter un cours</button> <button onClick={() => document.querySelector<HTMLInputElement>('input[type=file]')?.click()}>Importer un calendrier ICS</button></section>}><section class="calendar"><h2>Calendrier</h2><Show when={!events.loading} fallback={<p>Chargement…</p>}><Show when={events()?.length} fallback={<p class="empty">Aucun événement synchronisé.</p>}><div class="event-list"><For each={events()}>{event => <article><time>{new Date(event.start_at).toLocaleDateString('fr-BE', { weekday: 'short', day: 'numeric', month: 'short' })}<strong>{hour(event.start_at)} — {hour(event.end_at)}</strong></time><div><span>{event.course.institution}</span><h3>{event.title}</h3><p>{event.course.code} · {event.event_type || 'Cours'} · {event.room || 'Salle non précisée'}</p></div></article>}</For></div></Show></Show></section><section class="courses"><h2>Mes cours</h2><For each={courses()}>{item => <div>{item.course.code} — {item.course.name}</div>}</For></section></Show></main></div>;
  };
  return <>{view()}</>;
}
import { render } from 'solid-js/web';
render(() => <App />, document.getElementById('root')!);

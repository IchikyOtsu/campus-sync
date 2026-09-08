import { For, Show, createMemo, createResource, createSignal, onCleanup, onMount } from 'solid-js';
import type { Session } from '@supabase/supabase-js';
import { api, apiErrorLabel, configurationError, supabase, uploadIcs } from './api/client';
import './style.css';

type Event = { id: string; title: string; start_at: string; end_at: string; room?: string; event_type?: string; course: { code: string; name: string; institution: string } };
type Profile = { id: string; display_name?: string; timezone: string };
type PAE = { id: string; academic_year: string; name?: string; course_count: number };
type AuthProps = { onAuthenticated: (session: Session) => void };
type TimeEditCourse = { code: string; name: string; external_id: string; academic_year: string; object_type: string };
type PAEOffering = { id: string; academic_year: string; semester?: string; course: { id: string; code: string; name: string; credits?: number; institution: { slug: string; name: string; provider: string } } };
type CourseSearchProps = { courses: () => PAEOffering[] | undefined; onAdded: () => Promise<void>; onAddedOffering: (pae: PAE, offering: PAEOffering) => void };
type ProgramSummary = { id: string; code: string; name: string; academic_year: string; institution: string };
type ProgramDetail = ProgramSummary & { courses: { id: string; home_code: string; provider: string; provider_code: string; name: string; semester: string; connector_status: string; user_status: string }[] };
type ProgramProps = { programs: () => ProgramSummary[] | undefined; onChanged: () => Promise<void> };
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
  const normalized = (value: string) => value.toLowerCase().replace(/[^a-z0-9]/g, '');
  const alreadyAdded = (course: TimeEditCourse) => props.courses()?.some(item => normalized(item.course.code) === normalized(course.code));
  const search = async () => { if (!query().trim()) return setMessage('Saisissez un code ou un nom de cours.'); setLoading(true); setMessage(''); try { const found = await api<TimeEditCourse[]>(`/institutions/ulb/courses/search?q=${encodeURIComponent(query())}&academic_year=${academicYear}`); setResults(found); if (!found.length) setMessage('Cours introuvable dans TimeEdit ULB pour 2026-2027.'); } catch (error) { setMessage(apiErrorLabel(error, 'Recherche TimeEdit indisponible')); } finally { setLoading(false); } };
  const add = async (course: TimeEditCourse) => { setLoading(true); setMessage(''); try { const result = await api<{ pae: PAE; offering: PAEOffering; already_in_pae: boolean }>('/institutions/ulb/courses/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ code: course.code, external_id: course.external_id, academic_year: course.academic_year }) }); props.onAddedOffering(result.pae, result.offering); await props.onAdded(); setMessage(result.already_in_pae ? `${course.code} est déjà dans votre PAE.` : `${course.code} a été ajouté au PAE (${result.pae.course_count} cours).`); } catch (error) { setMessage(apiErrorLabel(error, `Impossible d’ajouter ${course.code}`)); } finally { setLoading(false); } };
  return <section id="course-search" class="course-search"><div><label>AJOUT AUTOMATIQUE</label><h2>Ajouter un cours au PAE</h2></div><div class="course-fields"><label>Établissement<select disabled><option>ULB · TimeEdit public</option></select></label><label>Année académique<select disabled><option>{academicYear}</option></select></label><label>Code ou nom<input value={query()} placeholder="ELEC-H550" onInput={e => setQuery(e.currentTarget.value)} onKeyDown={e => e.key === 'Enter' && search()} /></label><button disabled={loading()} onClick={search}>{loading() ? 'Recherche…' : 'Rechercher'}</button></div><Show when={message()}><p class="search-message">{message()}</p></Show><For each={results()}>{course => <article class="course-result"><div><span>ULB · {course.academic_year}</span><h3>{course.code}</h3><p>{course.name}</p></div><button disabled={loading() || alreadyAdded(course)} onClick={() => add(course)}>{alreadyAdded(course) ? 'Déjà dans le PAE' : 'Ajouter au PAE'}</button></article>}</For></section>;
}
function ProgramSection(props: ProgramProps) {
  const [detail, setDetail] = createSignal<ProgramDetail>(); const [message, setMessage] = createSignal(''); const [loading, setLoading] = createSignal(false);
  const load = async (program: ProgramSummary) => { try { setDetail(await api<ProgramDetail>(`/me/programs/${program.id}`)); } catch { setMessage('Impossible de charger ce programme.'); } };
  const importProgram = async () => { setLoading(true); setMessage(''); try { const available = await api<ProgramSummary[]>('/programs'); const target = available.find(item => item.code === 'M-SECUC' && item.academic_year === '2026-2027'); if (!target) throw new Error(); const response = await api<ProgramDetail>(`/me/programs/${target.id}`, { method: 'POST' }); setDetail(response); await props.onChanged(); } catch { setMessage('Import du programme impossible.'); } finally { setLoading(false); } };
  const addCourse = async (course: ProgramDetail['courses'][number]) => { const program = detail(); if (!program) return; setLoading(true); try { await api(`/me/programs/${program.id}/courses/${course.id}/add`, { method: 'POST' }); setDetail(await api<ProgramDetail>(`/me/programs/${program.id}`)); await props.onChanged(); } catch { setMessage('Ajout automatique impossible pour ce cours ULB.'); } finally { setLoading(false); } };
  const removeProgram = async () => { const program = detail(); if (!program) return; setLoading(true); try { await api(`/me/programs/${program.id}`, { method: 'DELETE' }); await props.onChanged(); setDetail(undefined); setMessage('Programme supprimé. Les cours déjà présents dans votre PAE sont conservés.'); } catch (error) { setMessage(apiErrorLabel(error, 'Impossible de supprimer le programme')); } finally { setLoading(false); } };
  const current = () => detail() || (props.programs()?.[0] ? (void load(props.programs()![0]), undefined) : undefined);
  return <section class="program-section"><div><label>MON PROGRAMME</label><h2>Programme académique</h2></div><Show when={current()} fallback={<div class="program-empty"><p>Ajoutez votre programme ULB pour voir les cours prévus et leur établissement fournisseur.</p><button disabled={loading()} onClick={importProgram}>{loading() ? 'Import…' : 'Importer M-SECUC · 2026-2027'}</button></div>}><div class="program-title"><b>{detail()?.code}</b><span>{detail()?.name} · {detail()?.academic_year}</span><button disabled={loading()} onClick={removeProgram}>Supprimer le programme</button></div><h3>Q1</h3><div class="program-courses"><For each={detail()?.courses.filter(course => course.semester === 'Q1')}>{course => <article><span class={course.user_status === 'added' ? 'status added' : 'status'}>{course.user_status === 'added' ? '✓' : '○'}</span><div><b>{course.home_code}</b><p>{course.provider.toUpperCase()} · {course.provider_code}</p><small>{course.name}</small></div><em>{course.user_status === 'added' ? 'Déjà ajouté' : course.connector_status === 'available' ? <button disabled={loading()} onClick={() => addCourse(course)}>Ajouter au PAE</button> : 'Connecteur à venir'}</em></article>}</For></div></Show><Show when={message()}><p class="search-message">{message()}</p></Show></section>;
}

const eventDateKey = (value: string) => {
  const parts = new Intl.DateTimeFormat('fr-BE', { timeZone: 'Europe/Brussels', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(new Date(value));
  const part = (type: string) => parts.find(item => item.type === type)?.value || '';
  return `${part('year')}-${part('month')}-${part('day')}`;
};
const cellDateKey = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
function CalendarPage(props: { events: () => Event[] | undefined; loading: () => boolean; error: () => unknown }) {
  const [month, setMonth] = createSignal(new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const cells = createMemo(() => {
    const first = month();
    const mondayOffset = (first.getDay() + 6) % 7;
    const start = new Date(first.getFullYear(), first.getMonth(), 1 - mondayOffset);
    return Array.from({ length: 42 }, (_, index) => new Date(start.getFullYear(), start.getMonth(), start.getDate() + index));
  });
  const moveMonth = (offset: number) => setMonth(current => new Date(current.getFullYear(), current.getMonth() + offset, 1));
  const eventsFor = (date: Date) => (props.events() || []).filter(event => eventDateKey(event.start_at) === cellDateKey(date));
  return <section class="calendar-page"><div class="calendar-toolbar"><div><label>CALENDRIER DU PAE</label><h1>{new Intl.DateTimeFormat('fr-BE', { month: 'long', year: 'numeric' }).format(month())}</h1></div><div><button onClick={() => moveMonth(-1)} aria-label="Mois précédent">←</button><button onClick={() => setMonth(new Date(new Date().getFullYear(), new Date().getMonth(), 1))}>Aujourd’hui</button><button onClick={() => moveMonth(1)} aria-label="Mois suivant">→</button></div></div><Show when={props.error()}><p class="search-message">{apiErrorLabel(props.error(), 'Impossible de charger le calendrier du PAE')}</p></Show><Show when={props.loading()}><p>Chargement du calendrier…</p></Show><div class="calendar-grid"><For each={['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim']}>{day => <div class="weekday">{day}</div>}</For><For each={cells()}>{date => <article classList={{ 'calendar-day': true, outside: date.getMonth() !== month().getMonth(), today: cellDateKey(date) === cellDateKey(new Date()) }}><time>{date.getDate()}</time><div class="day-events"><For each={eventsFor(date)}>{event => <div class="calendar-event"><b>{hour(event.start_at)}</b><span>{event.course.code}</span><small>{event.title}</small><small>{event.room || 'Salle non précisée'}</small></div>}</For></div></article>}</For></div></section>;
}

function ConfigError() { return <main class="login"><div class="logo">✣ campus-sync</div><h1>Configuration requise</h1><p>Variables absentes : <b>{configurationError}</b></p></main>; }
function ApiError() { return <main class="login"><div class="logo">✣ campus-sync</div><h1>API inaccessible</h1><p>Connexion Supabase réussie, mais le profil campus-sync n’a pas pu être chargé. Vérifiez que l’API est démarrée et que son CORS autorise cette adresse.</p><button onClick={() => supabase?.auth.signOut()}>Déconnexion</button></main>; }
function App() {
  const [session, setSession] = createSignal<Session | null | undefined>(undefined);
  const [page, setPage] = createSignal<'pae' | 'calendar'>(window.location.pathname === '/calendrier' ? 'calendar' : 'pae');
  const [profile] = createResource(() => session()?.access_token, () => api<Profile>('/me'));
  const [pae, { mutate: mutatePae, refetch: refetchPae }] = createResource(() => profile()?.id, () => api<PAE>('/me/pae'));
  const [events, { refetch: refetchEvents }] = createResource(() => profile()?.id, () => api<Event[]>('/me/pae/events'));
  const [courses, { mutate: mutateCourses, refetch: refetchCourses }] = createResource(() => profile()?.id, () => api<PAEOffering[]>('/me/pae/courses'));
  const [conflicts, { refetch: refetchConflicts }] = createResource(() => profile()?.id, () => api<any[]>('/me/conflicts'));
  const [userPrograms, { refetch: refetchUserPrograms }] = createResource(() => profile()?.id, () => api<ProgramSummary[]>('/me/programs'));
  const [file, setFile] = createSignal<File>(); const [notice, setNotice] = createSignal('');
  const refreshDashboard = async () => { await Promise.allSettled([refetchPae(), refetchCourses(), refetchEvents(), refetchConflicts(), refetchUserPrograms()]); };
  const navigate = (next: 'pae' | 'calendar') => { setPage(next); const path = next === 'calendar' ? '/calendrier' : '/'; if (window.location.pathname !== path) window.history.pushState({}, '', path); };
  onMount(() => { if (!supabase) return; const timeout = window.setTimeout(() => { if (session() === undefined) setSession(null); }, 5000); void supabase.auth.getSession().then(({ data }) => { window.clearTimeout(timeout); setSession(data.session); if (data.session) cleanAuthUrl(); }).catch(() => { window.clearTimeout(timeout); setSession(null); });
  onMount(() => { const syncPage = () => setPage(window.location.pathname === '/calendrier' ? 'calendar' : 'pae'); window.addEventListener('popstate', syncPage); onCleanup(() => window.removeEventListener('popstate', syncPage)); }); const subscription = supabase.auth.onAuthStateChange((_event, nextSession) => { window.clearTimeout(timeout); setSession(nextSession); if (nextSession) cleanAuthUrl(); }); onCleanup(() => { window.clearTimeout(timeout); subscription.data.subscription.unsubscribe(); }); });
  const importFile = async () => { if (!file()) return; try { await uploadIcs(file()!); await refreshDashboard(); setNotice('Calendrier importé et synchronisé.'); } catch (error) { setNotice(apiErrorLabel(error, 'Import impossible')); } };
  const view = () => {
    if (configurationError) return <ConfigError />;
    if (session() === undefined) return <Loading />;
    if (session() === null) return <Auth onAuthenticated={setSession} />;
    if (profile.loading) return <Loading />;
    if (profile.error) return <ApiError />;
    const user = session()!;
    const year = () => pae()?.academic_year || '2026-2027';
    return <div class="app"><header><div class="logo">✣ campus-sync</div><nav><button classList={{ active: page() === 'pae' }} onClick={() => navigate('pae')}>Mon PAE</button><button classList={{ active: page() === 'calendar' }} onClick={() => navigate('calendar')}>Calendrier</button><button onClick={() => { navigate('pae'); window.setTimeout(() => document.querySelector('.program-section')?.scrollIntoView(), 0); }}>Programme</button></nav><span class="profile">{profile()?.display_name || user.user.email || 'Compte connecté'}</span><button onClick={() => supabase?.auth.signOut()}>Déconnexion</button></header><main><Show when={page() === 'calendar'}><CalendarPage events={events} loading={() => events.loading} error={() => events.error} /></Show><Show when={page() === 'pae'}><section class="hero"><div><label>MON ESPACE</label><h1>Bonjour {profile()?.display_name || user.user.email}</h1><p>Votre calendrier interuniversitaire.</p></div></section><CourseSearch courses={courses} onAdded={refreshDashboard} onAddedOffering={(nextPae, offering) => { mutatePae(nextPae); mutateCourses(current => current?.some(item => item.id === offering.id) ? current : [...(current || []), offering]); }} /><ProgramSection programs={userPrograms} onChanged={refreshDashboard} /><Show when={notice()}><p class="notice">{notice()}</p></Show><section class="courses"><h2>Mon PAE · {year()}</h2><p>{pae()?.course_count ?? 0} cours</p><Show when={pae.error}><p class="search-message">{apiErrorLabel(pae.error, 'Impossible de charger le PAE')}</p></Show><Show when={courses.error}><p class="search-message">{apiErrorLabel(courses.error, 'Impossible de charger les cours du PAE')}</p></Show><Show when={courses.loading}><p>Chargement des cours…</p></Show><Show when={!courses.loading && !courses.error && !courses()?.length}><p>Votre PAE est vide.</p><button onClick={() => document.getElementById('course-search')?.scrollIntoView()}>Ajouter un cours</button></Show><For each={courses() || []}>{item => <div>{item.course.code} — {item.course.name}<small> · {item.course.institution.name}</small><button onClick={async () => { try { await api(`/me/pae/courses/${item.id}`, { method: 'DELETE' }); mutateCourses(current => current?.filter(course => course.id !== item.id)); mutatePae(current => current ? { ...current, course_count: Math.max(0, current.course_count - 1) } : current); await refreshDashboard(); setNotice(`${item.course.code} a été retiré du PAE.`); } catch (error) { setNotice(apiErrorLabel(error, `Impossible de retirer ${item.course.code}`)); } }}>Retirer</button></div>}</For></section><section class="manual-import"><b>Import manuel / dépannage</b><span>La synchronisation automatique ne fonctionne pas ? Importez un calendrier ICS.</span><input type="file" accept=".ics,text/calendar" onChange={e => setFile(e.currentTarget.files?.[0])} /><button onClick={importFile}>Importer un fichier ICS</button></section><section class="status"><div><b>Connecteurs</b><span>ICS · opérationnel</span><span>ULB TimeEdit · expérimental</span><span>UCLouvain / UNamur / HE2B · non implémenté</span></div><div class="conflict"><b>{conflicts()?.length || 0} conflit(s)</b><span>Calculés à partir de votre PAE.</span></div></section></Show></main></div>;
  };
  return <>{view()}</>;
}
import { render } from 'solid-js/web';
render(() => <App />, document.getElementById('root')!);

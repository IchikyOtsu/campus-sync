# ULB TimeEdit public connector

## Public endpoints

- Landing page: `https://cloud.timeedit.net/be_ulb/web/public/`
- Course schedule UI: `ri1Q50.html`
- Search: `objects.html?max=100&fr=t&partajax=t&im=f&sid=10&search_text=<query>&types=5`
- Events: `ri.ics?sid=10&p=<start>.x,<end>.x&objects=<external_id>`

`types=5` identifies ULB's **UE** course objects and `sid=10` is the public schedule profile. Search results contain a TimeEdit object identifier such as `181733.5`, plus a display name in the form `CODE, title, 202627`. The connector maps `2026-2027` to `202627` and filters results locally. Administrative codes containing a hyphen, such as `ELEC-H550`, are searched as `ELECH550`, because the public index omits the hyphen; matching during add is likewise canonicalized.

The iCalendar export is preferred over reservation HTML. It is parsed through the shared ICS connector and stored by UID/external ID, making synchronization idempotent.

## Limitations and risks

- Live validation on 8 September 2026 returned `ELECH550` / `Embedded System Security` (object `178081.5`, 23 teaching events) and `MATHF307` / `Mathématiques discrètes` (object `179780.5`, 43 teaching events) for `2026-2027`.
- Future timetables can be absent or contain only calendar-level information. An offering with no dated teaching event is rejected by the add route.
- `sid`, object type, HTML attributes and export parameters are public implementation details and can change. The connector raises a provider error rather than guessing.
- Requests use public endpoints only; no ULB/MonULB credential is used.

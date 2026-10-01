-- Row Level Security for the public sites (dashboard + report pages).
--
-- The browser uses the Supabase anon key, which is public. These rules limit what anyone
-- holding that key can do. The report worker uses the service role key and the crawler
-- import connects as the database owner, so both bypass these rules.
--
-- Run in the Supabase SQL editor (or psql). Safe to re-run.

begin;

-- ---------------------------------------------------------------------------------------
-- gambling_urls: dashboard data. Anonymous visitors may only read sites flagged illegal.
-- ---------------------------------------------------------------------------------------
alter table public.gambling_urls enable row level security;

revoke all on public.gambling_urls from anon, authenticated;
grant select on public.gambling_urls to anon, authenticated;

drop policy if exists "Public can read illegal sites" on public.gambling_urls;
create policy "Public can read illegal sites" on public.gambling_urls
    for select to anon, authenticated
    using (is_illegal = true);

-- ---------------------------------------------------------------------------------------
-- report_requests: the public report flow.
--   insert  : a new report (url only, status 'submitted')
--   select  : read a report by its (unguessable uuid) id; also needed for Realtime updates
--   update  : only status / reason / detected_keywords, and only the transitions the UI uses
--   delete  : not allowed
-- ---------------------------------------------------------------------------------------
alter table public.report_requests enable row level security;

drop policy if exists "Allow all" on public.report_requests;

revoke all on public.report_requests from anon, authenticated;
grant select on public.report_requests to anon, authenticated;
grant insert (url, status) on public.report_requests to anon, authenticated;
grant update (status, reason, detected_keywords) on public.report_requests to anon, authenticated;

drop policy if exists "Public can read reports" on public.report_requests;
create policy "Public can read reports" on public.report_requests
    for select to anon, authenticated
    using (true);

drop policy if exists "Public can submit reports" on public.report_requests;
create policy "Public can submit reports" on public.report_requests
    for insert to anon, authenticated
    with check (status = 'submitted');

drop policy if exists "Public can update open reports" on public.report_requests;
create policy "Public can update open reports" on public.report_requests
    for update to anon, authenticated
    using (status in ('submitted', 'analyzed'))
    with check (status in ('analyzed', 'confirmed', 'cancel'));

-- Enforce the exact status transitions the report pages perform:
--   submitted -> cancel                         (cancel while analyzing / analysis timeout)
--   analyzed  -> analyzed                       (edit reason / keywords)
--   analyzed  -> confirmed | cancel             (report / cancel on the confirm page)
create or replace function public.check_public_report_update()
returns trigger
language plpgsql
as $$
begin
    if current_user not in ('anon', 'authenticated') then
        return new;  -- worker (service_role) and database owner are not restricted
    end if;

    if not (
        (old.status = 'submitted' and new.status = 'cancel')
        or (old.status = 'analyzed' and new.status in ('analyzed', 'confirmed', 'cancel'))
    ) then
        raise exception 'Report status change % -> % is not allowed', old.status, new.status;
    end if;

    if old.status <> 'analyzed'
       and (new.reason is distinct from old.reason
            or new.detected_keywords is distinct from old.detected_keywords) then
        raise exception 'Report details can only be edited after analysis';
    end if;

    return new;
end;
$$;

drop trigger if exists check_public_report_update on public.report_requests;
create trigger check_public_report_update
    before update on public.report_requests
    for each row execute function public.check_public_report_update();

-- ---------------------------------------------------------------------------------------
-- illegal_sites: no longer used by the app. Close it to anonymous access.
-- ---------------------------------------------------------------------------------------
alter table public.illegal_sites enable row level security;
drop policy if exists "Allow all" on public.illegal_sites;
revoke all on public.illegal_sites from anon, authenticated;

commit;

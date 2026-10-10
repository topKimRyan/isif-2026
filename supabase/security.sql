-- Row Level Security and access rules for the public sites (dashboard + report pages).
--
-- The browser uses the Supabase anon key, which is public. These rules limit what anyone
-- holding that key can do. The report worker uses the service role key and the crawler
-- import connects as the database owner, so both bypass these rules.
--
-- Run in the Supabase SQL editor (or psql). Safe to re-run.
-- Deploy order: run this file, then deploy the matching front-end (report_page/, docs/).
-- The old front-end stops working once this runs, because it reads the table directly.

begin;

-- ---------------------------------------------------------------------------------------
-- gambling_urls: dashboard data. Anonymous visitors may only read sites flagged illegal,
-- and only the columns the dashboard shows (gemini_error and similar stay private).
-- ---------------------------------------------------------------------------------------
alter table public.gambling_urls enable row level security;

-- operator = runs illegal gambling, promotion = advertises/steers to it (e.g. 먹튀검증 pages)
alter table public.gambling_urls add column if not exists category text;
alter table public.report_requests add column if not exists category text;

revoke all on public.gambling_urls from anon, authenticated;
grant select (url, keyword_used, gemini_confidence, collected_at, detected_keywords,
              screenshot_url, gemini_reason, is_illegal, category)
    on public.gambling_urls to anon, authenticated;

drop policy if exists "Public can read illegal sites" on public.gambling_urls;
create policy "Public can read illegal sites" on public.gambling_urls
    for select to anon, authenticated
    using (is_illegal = true);

-- ---------------------------------------------------------------------------------------
-- report_requests: the public report flow.
--
-- Anonymous visitors get NO direct table access. Every report has a secret access_token that
-- is handed out once, when the report is created. The browser then works through the
-- functions below, which only act on a report when both its id and its token match.
-- Nobody can list reports, and knowing a report id alone is not enough to read or change it.
-- ---------------------------------------------------------------------------------------
alter table public.report_requests enable row level security;

alter table public.report_requests
    add column if not exists access_token uuid not null default gen_random_uuid();

drop policy if exists "Allow all" on public.report_requests;
drop policy if exists "Public can read reports" on public.report_requests;
drop policy if exists "Public can submit reports" on public.report_requests;
drop policy if exists "Public can update open reports" on public.report_requests;

-- Replaced by the status checks inside the functions below.
drop trigger if exists check_public_report_update on public.report_requests;
drop function if exists public.check_public_report_update();

revoke all on public.report_requests from anon, authenticated;

-- ---------------------------------------------------------------------------------------
-- Rate limiting for new reports (also protects the Gemini quota).
-- Counts per client IP (hashed) and overall, per hour. Adjust the limits in create_report.
-- ---------------------------------------------------------------------------------------
create table if not exists public.report_rate_limits (
    bucket       text        not null,
    window_start timestamptz not null,
    hits         integer     not null default 0,
    primary key (bucket, window_start)
);

alter table public.report_rate_limits enable row level security;
revoke all on public.report_rate_limits from anon, authenticated;

-- ---------------------------------------------------------------------------------------
-- Functions called from the browser. All run with the owner's rights (security definer),
-- so they must validate everything themselves.
-- ---------------------------------------------------------------------------------------

-- Create a report. Returns {"id": ..., "token": ...}; the token is never shown again.
create or replace function public.create_report(p_url text)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
    c_per_ip  constant integer := 10;    -- reports per IP per hour
    c_global  constant integer := 300;   -- reports from everyone per hour
    v_url     text := btrim(coalesce(p_url, ''));
    v_headers json;
    v_ip      text;
    v_window  timestamptz := date_trunc('hour', now());
    v_hits    integer;
    v_id      uuid;
    v_token   uuid;
begin
    if char_length(v_url) > 2048 or v_url !~* '^https?://[^[:space:]]+$' then
        raise exception 'invalid_url' using errcode = '22023';
    end if;

    begin
        v_headers := nullif(current_setting('request.headers', true), '')::json;
    exception when others then
        v_headers := null;
    end;
    -- Set by the proxy in front of Supabase, so a client cannot choose it.
    v_ip := coalesce(v_headers ->> 'cf-connecting-ip', v_headers ->> 'x-real-ip', 'unknown');

    insert into public.report_rate_limits as r (bucket, window_start, hits)
    values ('ip:' || encode(sha256(convert_to(v_ip, 'utf8')), 'hex'), v_window, 1)
    on conflict (bucket, window_start) do update set hits = r.hits + 1
    returning r.hits into v_hits;
    if v_hits > c_per_ip then
        raise exception 'rate_limited' using errcode = 'PT429';
    end if;

    insert into public.report_rate_limits as r (bucket, window_start, hits)
    values ('global', v_window, 1)
    on conflict (bucket, window_start) do update set hits = r.hits + 1
    returning r.hits into v_hits;
    if v_hits > c_global then
        raise exception 'rate_limited' using errcode = 'PT429';
    end if;

    delete from public.report_rate_limits where window_start < now() - interval '1 day';

    insert into public.report_requests (url, status)
    values (v_url, 'submitted')
    returning id, access_token into v_id, v_token;

    return jsonb_build_object('id', v_id, 'token', v_token);
end;
$$;

-- Read one report. Returns null when the id/token pair does not match.
-- Internal error text written by the worker is never returned.
create or replace function public.get_report(p_id uuid, p_token uuid)
returns jsonb
language sql
stable
security definer
set search_path = ''
as $$
    select jsonb_build_object(
        'status', status,
        'url', url,
        'is_illegal', is_illegal,
        'reason', case when status = 'error' then null else reason end,
        'detected_keywords', detected_keywords
    )
    from public.report_requests
    where id = p_id and access_token = p_token;
$$;

-- Cancel a report that has not been confirmed yet.
create or replace function public.cancel_report(p_id uuid, p_token uuid)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_rows integer;
begin
    update public.report_requests
       set status = 'cancel'
     where id = p_id and access_token = p_token
       and status in ('submitted', 'analyzed');
    get diagnostics v_rows = row_count;
    return v_rows = 1;
end;
$$;

-- Edit the reason / keywords after analysis, before confirming.
create or replace function public.update_report_details(
    p_id uuid, p_token uuid, p_reason text, p_keywords jsonb)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_rows integer;
begin
    if char_length(coalesce(p_reason, '')) > 2000 then
        raise exception 'reason_too_long' using errcode = '22023';
    end if;
    if p_keywords is not null and (
        jsonb_typeof(p_keywords) <> 'array'
        or jsonb_array_length(p_keywords) > 30
        or exists (
            select 1 from jsonb_array_elements(p_keywords) e
            where jsonb_typeof(e) <> 'string' or char_length(e #>> '{}') > 100
        )
    ) then
        raise exception 'invalid_keywords' using errcode = '22023';
    end if;

    update public.report_requests
       set reason = p_reason, detected_keywords = p_keywords
     where id = p_id and access_token = p_token
       and status = 'analyzed';
    get diagnostics v_rows = row_count;
    return v_rows = 1;
end;
$$;

-- Confirm a report the AI judged illegal; the worker then takes the screenshot.
create or replace function public.confirm_report(p_id uuid, p_token uuid)
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
    v_rows integer;
begin
    update public.report_requests
       set status = 'confirmed'
     where id = p_id and access_token = p_token
       and status = 'analyzed' and is_illegal is true;
    get diagnostics v_rows = row_count;
    return v_rows = 1;
end;
$$;

-- Functions are executable by everyone by default; allow only the browser roles.
revoke all on function public.create_report(text) from public;
revoke all on function public.get_report(uuid, uuid) from public;
revoke all on function public.cancel_report(uuid, uuid) from public;
revoke all on function public.update_report_details(uuid, uuid, text, jsonb) from public;
revoke all on function public.confirm_report(uuid, uuid) from public;

grant execute on function public.create_report(text) to anon, authenticated;
grant execute on function public.get_report(uuid, uuid) to anon, authenticated;
grant execute on function public.cancel_report(uuid, uuid) to anon, authenticated;
grant execute on function public.update_report_details(uuid, uuid, text, jsonb) to anon, authenticated;
grant execute on function public.confirm_report(uuid, uuid) to anon, authenticated;

-- ---------------------------------------------------------------------------------------
-- illegal_sites: no longer used by the app. Close it to anonymous access.
-- ---------------------------------------------------------------------------------------
alter table public.illegal_sites enable row level security;
drop policy if exists "Allow all" on public.illegal_sites;
revoke all on public.illegal_sites from anon, authenticated;

commit;

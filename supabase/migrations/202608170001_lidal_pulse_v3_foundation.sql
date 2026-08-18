-- LIDAL Pulse V3 — fondation PostgreSQL/Supabase.
-- Cree manuellement car le CLI Supabase n'est pas installe dans ce worktree.
-- Les nouvelles tables sont explicitement accordees a authenticated, car leur
-- exposition automatique au Data API n'est plus garantie depuis mai 2026.

create extension if not exists pgcrypto with schema extensions;
create extension if not exists vector with schema extensions;

create type public.lidal_membership_role as enum ('owner', 'admin', 'analyst', 'operator', 'viewer');
create type public.lidal_work_status as enum ('open', 'in_progress', 'blocked', 'resolved', 'closed');
create type public.lidal_signal_status as enum ('new', 'investigating', 'confirmed', 'dismissed', 'converted');
create type public.lidal_signal_severity as enum ('critical', 'high', 'medium', 'low');

create table public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) between 2 and 160),
  deployment_region text not null default 'pilot_sanitized',
  created_at timestamptz not null default now()
);

create table public.organization_memberships (
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role public.lidal_membership_role not null default 'viewer',
  created_at timestamptz not null default now(),
  primary key (organization_id, user_id)
);

-- Fonctions SECURITY DEFINER minimales : elles évitent la récursion RLS sur la
-- table des memberships et acceptent soit un membership réel, soit les claims
-- app_metadata signées par Supabase. Aucun rôle ne vient de user_metadata.
create or replace function public.lidal_is_org_member(target_organization_id uuid)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.organization_memberships membership
    where membership.organization_id = target_organization_id
      and membership.user_id = (select auth.uid())
  ) or (
    (select auth.uid()) is not null
    and auth.jwt() -> 'app_metadata' ->> 'organization_id' = target_organization_id::text
  );
$$;

create or replace function public.lidal_has_org_role(
  target_organization_id uuid,
  allowed_roles text[]
)
returns boolean
language sql
stable
security definer
set search_path = ''
as $$
  select exists (
    select 1
    from public.organization_memberships membership
    where membership.organization_id = target_organization_id
      and membership.user_id = (select auth.uid())
      and membership.role::text = any(allowed_roles)
  ) or (
    auth.jwt() -> 'app_metadata' ->> 'organization_id' = target_organization_id::text
    and auth.jwt() -> 'app_metadata' ->> 'role' = any(allowed_roles)
  );
$$;

revoke all on function public.lidal_is_org_member(uuid) from public, anon;
revoke all on function public.lidal_has_org_role(uuid, text[]) from public, anon;
grant execute on function public.lidal_is_org_member(uuid) to authenticated;
grant execute on function public.lidal_has_org_role(uuid, text[]) to authenticated;

create table public.monitors (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  name text not null,
  objective text not null check (objective in ('customer_experience','reputation','campaign','competition','issue')),
  target_type text not null check (target_type in ('brand','organization','product','campaign','competitor','subject')),
  target_name text not null,
  aliases jsonb not null default '[]'::jsonb,
  exclusions jsonb not null default '[]'::jsonb,
  languages jsonb not null default '["fr","ar","darija"]'::jsonb,
  territories jsonb not null default '["DZ"]'::jsonb,
  sources jsonb not null default '[]'::jsonb,
  competitors jsonb not null default '[]'::jsonb,
  frequency_minutes integer not null default 360 check (frequency_minutes >= 15),
  max_monthly_documents integer not null default 100000 check (max_monthly_documents > 0),
  max_monthly_cost_dzd numeric(14,2) not null default 0 check (max_monthly_cost_dzd >= 0),
  active boolean not null default true,
  last_collected_at timestamptz,
  coverage_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.mentions (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  monitor_id uuid not null references public.monitors(id) on delete cascade,
  external_id text,
  canonical_url text,
  content_hash text not null,
  text text not null,
  source text not null check (source in ('facebook','tiktok','youtube','google_maps')),
  source_url text,
  published_at timestamptz not null,
  collected_at timestamptz not null default now(),
  language text not null,
  territory text,
  validation_status text not null check (validation_status in ('valid','pending','failed','overridden')),
  is_exploitable boolean not null default false,
  business_relevance text not null default 'aucune',
  requires_parent_context boolean not null default false,
  author_role text not null default 'inconnu',
  sentiment text check (sentiment in ('positif','negatif','neutre','mixte')),
  aspects jsonb not null default '[]'::jsonb,
  annotation jsonb,
  author_pseudonym text,
  expires_at timestamptz,
  unique (organization_id, source, content_hash)
);

create table public.observations (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  monitor_id uuid not null references public.monitors(id) on delete cascade,
  title text not null,
  summary text not null,
  mention_count integer not null check (mention_count > 0),
  sentiment text not null check (sentiment in ('positif','negatif','neutre','mixte')),
  aspects jsonb not null default '[]'::jsonb,
  evidence_ids jsonb not null default '[]'::jsonb,
  first_seen_at timestamptz not null,
  last_seen_at timestamptz not null
);

create table public.signals (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  monitor_id uuid not null references public.monitors(id) on delete cascade,
  title text not null,
  summary text not null,
  severity public.lidal_signal_severity not null,
  status public.lidal_signal_status not null default 'new',
  signal_type text not null,
  detected_at timestamptz not null default now(),
  mention_count integer not null default 0,
  velocity_percent numeric(8,2),
  confidence numeric(5,4) not null check (confidence between 0 and 1),
  territory text,
  observation_ids jsonb not null default '[]'::jsonb,
  evidence_ids jsonb not null default '[]'::jsonb check (jsonb_array_length(evidence_ids) > 0),
  explanation text not null,
  priority_score numeric(5,2) not null check (priority_score between 0 and 100),
  priority_factors jsonb not null
);

create table public.signal_mentions (
  organization_id uuid not null references public.organizations(id) on delete cascade,
  signal_id uuid not null references public.signals(id) on delete cascade,
  mention_id uuid not null references public.mentions(id) on delete cascade,
  primary key (signal_id, mention_id)
);

create table public.cases (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  signal_id uuid not null unique references public.signals(id),
  title text not null,
  status public.lidal_work_status not null default 'open',
  priority public.lidal_signal_severity not null,
  owner_id uuid references auth.users(id),
  owner_name text,
  due_at timestamptz,
  expected_outcome text,
  opened_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.case_comments (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  case_id uuid not null references public.cases(id) on delete cascade,
  author_id uuid not null references auth.users(id),
  body text not null check (char_length(body) between 1 and 5000),
  created_at timestamptz not null default now()
);

create table public.action_items (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  case_id uuid not null references public.cases(id) on delete cascade,
  title text not null,
  description text not null,
  status public.lidal_work_status not null default 'open',
  owner_id uuid references auth.users(id),
  owner_name text,
  due_at timestamptz,
  expected_impact text,
  metric_id text,
  baseline_value numeric,
  result_value numeric,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.timeline_events (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  entity_type text not null,
  entity_id uuid not null,
  event_type text not null,
  actor_id uuid not null references auth.users(id),
  payload jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table public.metric_snapshots (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  monitor_id uuid references public.monitors(id) on delete cascade,
  metric_key text not null,
  value numeric,
  numerator numeric,
  denominator numeric,
  period_start timestamptz not null,
  period_end timestamptz not null,
  dimensions jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  check (period_end > period_start)
);

create table public.reports (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  title text not null,
  report_type text not null check (report_type in ('daily','weekly','crisis','reputation','territory','product')),
  period_start timestamptz not null,
  period_end timestamptz not null,
  status text not null check (status in ('draft','ready','failed')),
  generated_at timestamptz,
  download_url text,
  evidence_count integer not null default 0,
  check (period_end > period_start)
);

create table public.notifications (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  user_id uuid references auth.users(id),
  title text not null,
  body text not null,
  kind text not null,
  read boolean not null default false,
  href text,
  created_at timestamptz not null default now()
);

create table public.idempotency_keys (
  organization_id uuid not null references public.organizations(id) on delete cascade,
  key text not null,
  operation text not null,
  response jsonb not null,
  created_at timestamptz not null default now(),
  primary key (organization_id, key)
);

create index mentions_org_monitor_published_idx on public.mentions (organization_id, monitor_id, published_at desc);
create index signals_org_status_detected_idx on public.signals (organization_id, status, detected_at desc);
create index actions_org_status_due_idx on public.action_items (organization_id, status, due_at);
create index timeline_org_entity_idx on public.timeline_events (organization_id, entity_type, entity_id, created_at);

-- Les clés composites empêchent les relations croisées entre deux tenants,
-- même lorsqu'un utilisateur appartient légitimement aux deux organisations.
alter table public.monitors add constraint monitors_id_org_unique unique (id, organization_id);
alter table public.mentions add constraint mentions_id_org_unique unique (id, organization_id);
alter table public.signals add constraint signals_id_org_unique unique (id, organization_id);
alter table public.cases add constraint cases_id_org_unique unique (id, organization_id);
alter table public.mentions add constraint mentions_monitor_tenant_fk foreign key (monitor_id, organization_id) references public.monitors(id, organization_id) on delete cascade;
alter table public.observations add constraint observations_monitor_tenant_fk foreign key (monitor_id, organization_id) references public.monitors(id, organization_id) on delete cascade;
alter table public.signals add constraint signals_monitor_tenant_fk foreign key (monitor_id, organization_id) references public.monitors(id, organization_id) on delete cascade;
alter table public.signal_mentions add constraint signal_mentions_signal_tenant_fk foreign key (signal_id, organization_id) references public.signals(id, organization_id) on delete cascade;
alter table public.signal_mentions add constraint signal_mentions_mention_tenant_fk foreign key (mention_id, organization_id) references public.mentions(id, organization_id) on delete cascade;
alter table public.cases add constraint cases_signal_tenant_fk foreign key (signal_id, organization_id) references public.signals(id, organization_id);
alter table public.case_comments add constraint case_comments_case_tenant_fk foreign key (case_id, organization_id) references public.cases(id, organization_id) on delete cascade;
alter table public.action_items add constraint action_items_case_tenant_fk foreign key (case_id, organization_id) references public.cases(id, organization_id) on delete cascade;
alter table public.metric_snapshots add constraint metric_snapshots_monitor_tenant_fk foreign key (monitor_id, organization_id) references public.monitors(id, organization_id) on delete cascade;

-- Les vues analytiques obeissent aux politiques des tables sous-jacentes.
create view public.eligible_mentions with (security_invoker = true) as
select * from public.mentions
where validation_status = 'valid'
  and is_exploitable
  and business_relevance <> 'aucune'
  and not requires_parent_context;

-- Aucune table metier n'est publique.
revoke all on all tables in schema public from anon;
grant select, insert, update, delete on
  public.organizations, public.organization_memberships, public.monitors,
  public.mentions, public.observations, public.signals, public.signal_mentions,
  public.cases, public.case_comments, public.action_items, public.timeline_events,
  public.metric_snapshots, public.reports, public.notifications, public.idempotency_keys
to authenticated;
grant select on public.eligible_mentions to authenticated;

alter table public.organizations enable row level security;
alter table public.organization_memberships enable row level security;
alter table public.monitors enable row level security;
alter table public.mentions enable row level security;
alter table public.observations enable row level security;
alter table public.signals enable row level security;
alter table public.signal_mentions enable row level security;
alter table public.cases enable row level security;
alter table public.case_comments enable row level security;
alter table public.action_items enable row level security;
alter table public.timeline_events enable row level security;
alter table public.metric_snapshots enable row level security;
alter table public.reports enable row level security;
alter table public.notifications enable row level security;
alter table public.idempotency_keys enable row level security;

-- Le token ne peut utiliser que app_metadata, jamais user_metadata.
create policy organizations_member_select on public.organizations for select to authenticated
using (public.lidal_is_org_member(id));

create policy memberships_same_org_select on public.organization_memberships for select to authenticated
using (
  public.lidal_is_org_member(organization_id)
  and (user_id = (select auth.uid()) or public.lidal_has_org_role(organization_id, array['owner','admin']))
);

-- Chaque table metier applique le meme predicat d'organisation. Les ecritures
-- sont autorisees uniquement aux roles operationnels; les viewers restent read-only.
do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'monitors','mentions','observations','signals','signal_mentions','cases',
    'case_comments','action_items','timeline_events','metric_snapshots','reports',
    'notifications','idempotency_keys'
  ] loop
    execute format(
      'create policy %I on public.%I for select to authenticated using '
      || '(public.lidal_is_org_member(organization_id))',
      table_name || '_tenant_select', table_name
    );
    execute format(
      'create policy %I on public.%I for insert to authenticated with check '
      || '(public.lidal_has_org_role(organization_id, array[''owner'',''admin'',''analyst'',''operator'']))',
      table_name || '_tenant_insert', table_name
    );
    execute format(
      'create policy %I on public.%I for update to authenticated using '
      || '(public.lidal_has_org_role(organization_id, array[''owner'',''admin'',''analyst'',''operator''])) '
      || 'with check (public.lidal_has_org_role(organization_id, array[''owner'',''admin'',''analyst'',''operator'']))',
      table_name || '_tenant_update', table_name
    );
  end loop;
end $$;

-- La suppression est volontairement reservee aux administrateurs. Les objets
-- operationnels sont normalement clos ou desactives, pas effaces.
do $$
declare
  table_name text;
begin
  foreach table_name in array array[
    'monitors','mentions','observations','signals','signal_mentions','cases',
    'case_comments','action_items','metric_snapshots','reports','notifications'
  ] loop
    execute format(
      'create policy %I on public.%I for delete to authenticated using '
      || '(public.lidal_has_org_role(organization_id, array[''owner'',''admin'']))',
      table_name || '_tenant_delete', table_name
    );
  end loop;
end $$;

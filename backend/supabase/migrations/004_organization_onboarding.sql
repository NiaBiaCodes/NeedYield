-- Organization onboarding, approval, and weekly need reporting.
alter type public.user_role add value if not exists 'organization';
alter table public.profiles add column if not exists is_admin boolean not null default false;

create table if not exists public.organization_applications (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null unique references auth.users(id) on delete cascade,
  organization_name text not null,
  organization_type text not null,
  address text not null,
  borough text not null,
  neighborhood text not null,
  contact_name text not null,
  phone text not null,
  accepted_categories text[] not null default '{}',
  opening_time text not null,
  closing_time text not null,
  notes text not null default '',
  status text not null default 'PENDING' check (status in ('PENDING', 'APPROVED', 'REJECTED')),
  location_id text references public.locations(id),
  review_note text not null default '',
  created_at timestamptz not null default now(),
  reviewed_at timestamptz
);

alter table public.organization_applications enable row level security;
create policy "organizations read own application" on public.organization_applications for select to authenticated using (user_id = auth.uid());
create policy "organizations submit own application" on public.organization_applications for insert to authenticated with check (user_id = auth.uid());
create policy "admins review applications" on public.organization_applications for all to authenticated
using (exists (select 1 from public.profiles where id = auth.uid() and is_admin))
with check (exists (select 1 from public.profiles where id = auth.uid() and is_admin));

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path = public as $$
declare requested_role public.user_role;
begin
  requested_role := case
    when new.raw_user_meta_data->>'role' = 'gardener' then 'gardener'::public.user_role
    when new.raw_user_meta_data->>'role' = 'organization' then 'organization'::public.user_role
    else 'neighbor'::public.user_role
  end;
  insert into public.profiles (id, role, display_name)
  values (new.id, requested_role, coalesce(nullif(trim(new.raw_user_meta_data->>'display_name'), ''), split_part(new.email, '@', 1), 'NeedYield user'));
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created after insert on auth.users
for each row execute procedure public.handle_new_user();

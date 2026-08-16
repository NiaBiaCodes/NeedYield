create extension if not exists pgcrypto;

create type public.user_role as enum ('neighbor', 'gardener', 'organization');
create type public.need_level as enum ('none', 'low', 'medium', 'high');
create type public.reservation_status as enum ('RESERVED', 'PICKED_UP', 'EXPIRED', 'RELEASED');
create type public.donation_status as enum ('DRAFT', 'ANALYZED', 'MATCHED', 'CONFIRMED', 'DELIVERED');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  role public.user_role not null default 'neighbor',
  display_name text not null check (char_length(display_name) between 1 and 80),
  created_at timestamptz not null default now()
);

create table public.locations (
  id text primary key,
  name text not null, address text not null, borough text not null, neighborhood text not null,
  latitude double precision not null, longitude double precision not null,
  opening_time text not null, closing_time text not null,
  accepted_categories text[] not null default array['vegetables']::text[],
  verified_partner boolean not null default false,
  participating boolean not null default false,
  accepts_saturday boolean not null default false,
  demo boolean not null default true,
  community_need_score double precision not null default 0.5 check (community_need_score between 0 and 1),
  community_need_source text not null default 'seeded fallback',
  created_at timestamptz not null default now()
);

create table public.organization_location_members (
  user_id uuid not null references public.profiles(id) on delete cascade,
  location_id text not null references public.locations(id) on delete cascade,
  primary key (user_id, location_id)
);

create table public.organization_needs (
  id uuid primary key default gen_random_uuid(),
  location_id text not null references public.locations(id) on delete cascade,
  produce_name text not null,
  need_level public.need_level not null,
  requested_quantity integer check (requested_quantity is null or requested_quantity >= 0),
  distribution_date date not null default current_date,
  updated_at timestamptz not null default now(),
  unique (location_id, produce_name, distribution_date)
);

create table public.inventory (
  id uuid primary key default gen_random_uuid(),
  location_id text not null references public.locations(id) on delete cascade,
  produce_name text not null,
  quantity integer not null default 0 check (quantity >= 0),
  unit text not null default 'count',
  updated_at timestamptz not null default now(),
  unique (location_id, produce_name)
);

create table public.reservations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.profiles(id) on delete set null,
  location_id text not null references public.locations(id),
  produce_name text not null,
  quantity integer not null check (quantity > 0),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  status public.reservation_status not null default 'RESERVED'
);

create table public.donations (
  id uuid primary key default gen_random_uuid(),
  gardener_id uuid references public.profiles(id) on delete set null,
  demo_gardener_id text,
  preferred_location_id text references public.locations(id),
  radius_miles double precision not null check (radius_miles > 0),
  status public.donation_status not null default 'DRAFT',
  created_at timestamptz not null default now()
);

create table public.donation_items (
  id uuid primary key default gen_random_uuid(),
  donation_id uuid not null references public.donations(id) on delete cascade,
  produce_name text not null,
  quantity integer not null check (quantity > 0),
  unit text not null default 'count'
);

create table public.allocations (
  id uuid primary key default gen_random_uuid(),
  donation_id uuid not null references public.donations(id) on delete cascade,
  location_id text not null references public.locations(id),
  produce_name text not null,
  quantity integer not null check (quantity >= 0),
  score double precision not null check (score between 0 and 1),
  confirmed boolean not null default false,
  created_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.locations enable row level security;
alter table public.organization_location_members enable row level security;
alter table public.organization_needs enable row level security;
alter table public.inventory enable row level security;
alter table public.reservations enable row level security;
alter table public.donations enable row level security;
alter table public.donation_items enable row level security;
alter table public.allocations enable row level security;

create policy "public locations are readable" on public.locations for select to anon, authenticated using (true);
create policy "public inventory is readable" on public.inventory for select to anon, authenticated using (true);
create policy "public needs are readable" on public.organization_needs for select to anon, authenticated using (true);
create policy "profiles read own" on public.profiles for select to authenticated using (id = auth.uid());
create policy "profiles update own" on public.profiles for update to authenticated using (id = auth.uid()) with check (id = auth.uid());
create policy "members read own" on public.organization_location_members for select to authenticated using (user_id = auth.uid());
create policy "users read own reservations" on public.reservations for select to authenticated using (user_id = auth.uid());
create policy "users create own reservations" on public.reservations for insert to authenticated with check (user_id = auth.uid());
create policy "users update own reservations" on public.reservations for update to authenticated using (user_id = auth.uid()) with check (user_id = auth.uid());
create policy "gardeners read own donations" on public.donations for select to authenticated using (gardener_id = auth.uid());
create policy "gardeners create own donations" on public.donations for insert to authenticated with check (gardener_id = auth.uid());
create policy "gardeners update own donations" on public.donations for update to authenticated using (gardener_id = auth.uid()) with check (gardener_id = auth.uid());
create policy "gardeners manage own donation items" on public.donation_items for all to authenticated using (exists (select 1 from public.donations d where d.id = donation_id and d.gardener_id = auth.uid())) with check (exists (select 1 from public.donations d where d.id = donation_id and d.gardener_id = auth.uid()));
create policy "gardeners read own allocations" on public.allocations for select to authenticated using (exists (select 1 from public.donations d where d.id = donation_id and d.gardener_id = auth.uid()));
create policy "organizations manage their needs" on public.organization_needs for all to authenticated using (exists (select 1 from public.organization_location_members m where m.location_id = organization_needs.location_id and m.user_id = auth.uid())) with check (exists (select 1 from public.organization_location_members m where m.location_id = organization_needs.location_id and m.user_id = auth.uid()));

create index reservations_user_id_idx on public.reservations(user_id);
create index reservations_location_id_idx on public.reservations(location_id);
create index inventory_location_id_idx on public.inventory(location_id);
create index donations_gardener_id_idx on public.donations(gardener_id);
create index allocations_donation_id_idx on public.allocations(donation_id);


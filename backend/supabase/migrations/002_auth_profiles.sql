-- Run after 001_initial_schema.sql. New Auth users receive a profile from
-- trusted signup metadata. Public organization registration is excluded.
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer set search_path = public
as $$
declare
  requested_role public.user_role;
begin
  requested_role := case
    when new.raw_user_meta_data->>'role' = 'gardener' then 'gardener'::public.user_role
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

-- Atomic, user-owned reservation creation. Run after 001 and 002.
create or replace function public.reserve_inventory_atomic(
  p_location_id text,
  p_produce text,
  p_quantity integer,
  p_user_id uuid,
  p_expires_at timestamptz
)
returns table(reservation_id uuid, remaining_quantity integer)
language plpgsql
security definer
set search_path = public
as $$
declare
  current_quantity integer;
  new_reservation_id uuid;
begin
  if p_quantity <= 0 then raise exception 'Quantity must be positive'; end if;
  if not exists (select 1 from public.profiles where id = p_user_id and role = 'neighbor') then
    raise exception 'A neighbor account is required';
  end if;

  select quantity into current_quantity
  from public.inventory
  where location_id = p_location_id and produce_name = lower(trim(p_produce))
  for update;

  if current_quantity is null then raise exception 'Inventory item not found'; end if;
  if current_quantity < p_quantity then raise exception 'Insufficient inventory'; end if;

  update public.inventory
  set quantity = quantity - p_quantity, updated_at = now()
  where location_id = p_location_id and produce_name = lower(trim(p_produce));

  insert into public.reservations(user_id, location_id, produce_name, quantity, expires_at)
  values (p_user_id, p_location_id, lower(trim(p_produce)), p_quantity, p_expires_at)
  returning id into new_reservation_id;

  return query select new_reservation_id, current_quantity - p_quantity;
end;
$$;

revoke all on function public.reserve_inventory_atomic(text, text, integer, uuid, timestamptz) from public, anon, authenticated;
grant execute on function public.reserve_inventory_atomic(text, text, integer, uuid, timestamptz) to service_role;

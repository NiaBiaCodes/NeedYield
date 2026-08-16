# Supabase setup

1. Create a Supabase project.
2. Run `migrations/001_initial_schema.sql` in the Supabase SQL Editor.
3. Copy the project URL and server-side service-role key into `backend/.env`.
4. Restart FastAPI. When the database has no locations, the backend seeds the six clearly labeled demo partners.

The service-role key is backend-only and must never use a `VITE_` prefix. RLS protects browser-facing access. Demo reservations and donations have nullable user IDs; backend writes use the service role.

Run migrations in order: `001_initial_schema.sql`, `002_auth_profiles.sql`, then `003_atomic_reservations.sql`.

For real signup and login, copy `frontend/.env.example` to `frontend/.env.local`, then add the project URL and public anon key as `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY`. The anon key is intentionally public; never place the service-role key in the frontend. Without these values, the app keeps fully functional Demo Neighbor and Demo Gardener paths.

For production concurrency, inventory decrement/release should move into Postgres transaction functions. The hackathon backend currently serializes mutations inside the FastAPI process and then persists the resulting quantity.

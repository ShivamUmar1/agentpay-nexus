-- Protect the legacy profiles table from public Data API access.
-- The application currently does not use Supabase Data API for profiles.
-- No anon or authenticated policies should be created.
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;

# Database Migration Instructions

## Prerequisites

- Supabase project set up
- Supabase CLI installed (optional but recommended)
- Access to Supabase SQL Editor (via dashboard)

## Migration Files

Located in `urban futures/supabase/migrations/`:

1. **001_initial_schema.sql** - Core tables (should already be applied)
2. **002_community_leaders.sql** - New community leader features

## How to Apply Migrations

### Option 1: Using Supabase Dashboard (Easiest)

1. Go to your Supabase project dashboard
2. Click "SQL Editor" in the left sidebar
3. Click "New Query"
4. Open `002_community_leaders.sql` in a text editor
5. Copy the entire contents
6. Paste into the SQL Editor
7. Click "Run" at the bottom right
8. Wait for confirmation (should see "Success. No rows returned")

### Option 2: Using Supabase CLI

```bash
# Navigate to project directory
cd "urban futures"

# Login to Supabase (if not already logged in)
supabase login

# Link to your project (if not already linked)
supabase link --project-ref YOUR_PROJECT_REF

# Apply migrations
supabase db push
```

### Option 3: Using psql (Advanced)

```bash
# Get connection string from Supabase dashboard
psql "postgresql://postgres:[YOUR-PASSWORD]@[YOUR-PROJECT-REF].supabase.co:5432/postgres"

# Run migration
\i 'urban futures/supabase/migrations/002_community_leaders.sql'
```

## Verifying Migration

After applying the migration, verify it worked:

### Check Tables Created

```sql
-- In Supabase SQL Editor, run:
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public' 
  AND table_name IN (
    'organizations',
    'community_leaders',
    'community_leader_zipcodes',
    'organization_zipcodes',
    'events',
    'event_zipcodes'
  );
```

You should see all 6 tables listed.

### Check Views Created

```sql
SELECT table_name 
FROM information_schema.views 
WHERE table_schema = 'public' 
  AND table_name IN (
    'organizations_by_zipcode',
    'events_by_zipcode'
  );
```

You should see both views.

### Check Storage Buckets

1. Go to Supabase Dashboard → Storage
2. Verify these buckets exist:
   - `event-images`
   - `profile-images`

If they don't exist, create them manually:
1. Click "New bucket"
2. Name: `event-images`, Public: Yes
3. Repeat for `profile-images`

### Check RLS Policies

```sql
SELECT schemaname, tablename, policyname 
FROM pg_policies 
WHERE schemaname = 'public'
  AND tablename IN (
    'organizations',
    'community_leaders',
    'community_leader_zipcodes',
    'organization_zipcodes',
    'events',
    'event_zipcodes'
  );
```

You should see multiple policies for each table.

## Troubleshooting

### Error: "relation already exists"

This means the migration was partially applied. Options:

1. **Drop and recreate** (⚠️ This deletes data):
```sql
-- Only if you're sure you want to start fresh
DROP TABLE IF EXISTS event_zipcodes CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS organization_zipcodes CASCADE;
DROP TABLE IF EXISTS community_leader_zipcodes CASCADE;
DROP TABLE IF EXISTS community_leaders CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

-- Then re-run the migration
```

2. **Apply remaining parts**: Comment out the parts that succeeded and run the rest

### Error: "function already exists"

The trigger function `update_updated_at_column` should already exist from migration 001. If you get this error:

```sql
-- Check if it exists
SELECT routine_name 
FROM information_schema.routines 
WHERE routine_schema = 'public' 
  AND routine_name = 'update_updated_at_column';
```

If it exists, remove this part from the migration:
```sql
-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Error: "permission denied"

Make sure you're running as the postgres user or have sufficient privileges. In Supabase dashboard, you should have full access.

### Storage bucket creation fails

If storage bucket creation via SQL fails:
1. Comment out the storage bucket creation in the SQL
2. Create buckets manually in the Supabase dashboard
3. Apply storage policies via SQL after buckets exist

### RLS policies not working

Verify RLS is enabled:
```sql
SELECT tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN (
    'organizations',
    'community_leaders',
    'events'
  );
```

All should show `rowsecurity = true`.

## Rolling Back (if needed)

To remove all community leader features:

```sql
-- ⚠️ WARNING: This will delete all data in these tables!

-- Drop views
DROP VIEW IF EXISTS events_by_zipcode;
DROP VIEW IF EXISTS organizations_by_zipcode;

-- Drop tables (in order due to foreign keys)
DROP TABLE IF EXISTS event_zipcodes CASCADE;
DROP TABLE IF EXISTS events CASCADE;
DROP TABLE IF EXISTS organization_zipcodes CASCADE;
DROP TABLE IF EXISTS community_leader_zipcodes CASCADE;
DROP TABLE IF EXISTS community_leaders CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

-- Drop trigger function
DROP FUNCTION IF EXISTS sync_organization_zipcodes CASCADE;

-- Revert user_type constraint
ALTER TABLE public.user_profiles 
DROP CONSTRAINT IF EXISTS user_profiles_user_type_check;

ALTER TABLE public.user_profiles
ADD CONSTRAINT user_profiles_user_type_check 
CHECK (user_type IN ('regular', 'corporate', 'guest'));
```

## Post-Migration Steps

After successful migration:

1. **Test the frontend**:
   - Try signing up as a community leader
   - Complete the setup process
   - Create a test event
   - View organizations and events in the UI

2. **Monitor for errors**:
   - Check browser console for JS errors
   - Check Supabase logs for database errors
   - Test image uploads

3. **Populate initial data** (optional):
   - Create a few organizations
   - Add sample events
   - Test with real zipcodes

## Sample Data (Optional)

To test with sample data:

```sql
-- Create sample organization
INSERT INTO public.organizations (name, description, website_url)
VALUES (
  'Green Brooklyn Initiative',
  'Working to make Brooklyn greener and more sustainable',
  'https://greenbrooklyn.org'
)
RETURNING id;

-- Note the returned ID, then use it below
-- Create sample community leader (replace USER_ID with actual user ID)
INSERT INTO public.community_leaders (id, organization_id, role)
VALUES (
  'USER_ID_HERE',
  'ORG_ID_FROM_ABOVE',
  'Community Coordinator'
);

-- Add zipcode for leader
INSERT INTO public.community_leader_zipcodes (community_leader_id, zipcode)
VALUES ('USER_ID_HERE', '11201');
```

## Support

If you encounter issues not covered here:
1. Check Supabase logs in dashboard
2. Review the migration SQL file for syntax errors
3. Ensure you're using PostgreSQL 13+ (Supabase default)
4. Check Supabase status page for service issues

## Success Checklist

✅ All 6 tables created
✅ Both views created  
✅ Trigger created
✅ RLS enabled on all tables
✅ RLS policies created
✅ Storage buckets created
✅ Storage policies created
✅ No errors in Supabase logs
✅ Frontend can sign up community leaders
✅ Community leader setup flow works
✅ Events can be created and viewed

Once all items are checked, your migration is complete! 🎉

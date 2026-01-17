-- Fix for user_profiles constraint to allow community_leader type
-- Run this in Supabase SQL Editor BEFORE running 002_community_leaders.sql

-- Drop the old constraint
ALTER TABLE public.user_profiles 
DROP CONSTRAINT IF EXISTS user_profiles_user_type_check;

-- Add the new constraint with community_leader included
ALTER TABLE public.user_profiles
ADD CONSTRAINT user_profiles_user_type_check 
CHECK (user_type IN ('regular', 'corporate', 'guest', 'community_leader'));

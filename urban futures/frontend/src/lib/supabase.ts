import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL || 'https://cypxvoflvseljxevetqz.supabase.co';
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY || 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImN5cHh2b2ZsdnNlbGp4ZXZldHF6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njg1MTU2MzEsImV4cCI6MjA4NDA5MTYzMX0.9Clu6E57mJmDylI9_XaU04dllOPD8_1ML6H3_NvaO4k';

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Types
export interface UserProfile {
  id: string;
  email: string;
  user_type: 'regular' | 'corporate' | 'guest' | 'community_leader';
  company_domain?: string;
  company_logo_url?: string;
  zipcode?: string;
  created_at: string;
  updated_at: string;
}

export interface Organization {
  id: string;
  name: string;
  description?: string;
  website_url?: string;
  twitter_url?: string;
  instagram_url?: string;
  facebook_url?: string;
  created_by?: string;
  is_verified: boolean;
  created_at: string;
  updated_at: string;
}

export interface CommunityLeader {
  id: string;
  organization_id: string;
  role?: string;
  bio?: string;
  profile_image_url?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  organization?: Organization;
  user_profile?: UserProfile;
}

export interface CommunityLeaderZipcode {
  id: string;
  community_leader_id: string;
  zipcode: string;
  created_at: string;
}

export interface Event {
  id: string;
  community_leader_id: string;
  organization_id: string;
  title: string;
  description: string;
  event_type: 'event' | 'news' | 'information' | 'announcement';
  event_date?: string;
  location?: string;
  image_url?: string;
  external_link?: string;
  is_published: boolean;
  created_at: string;
  updated_at: string;
  organization?: Organization;
  community_leader?: CommunityLeader;
}

export interface EventZipcode {
  id: string;
  event_id: string;
  zipcode: string;
  created_at: string;
}

export interface Review {
  id: string;
  user_id: string;
  zipcode: string;
  h3_cell?: string;
  rating: number;
  message: string;
  lives_here: boolean;
  created_at: string;
  updated_at: string;
  user_profile?: UserProfile;
}

export interface GreenInitiative {
  id: string;
  user_id: string;
  zipcode: string;
  h3_cell?: string;
  image_url: string;
  caption?: string;
  initiative_type: 'plant_flower' | 'hang_vines' | 'plant_tree' | 'general';
  created_at: string;
  updated_at: string;
  user_profile?: UserProfile;
}

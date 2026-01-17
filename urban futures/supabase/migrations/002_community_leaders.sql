-- Community Leaders and Organizations Migration

-- Organizations table
CREATE TABLE public.organizations (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name TEXT NOT NULL UNIQUE,
  description TEXT,
  website_url TEXT,
  twitter_url TEXT,
  instagram_url TEXT,
  facebook_url TEXT,
  created_by UUID REFERENCES public.user_profiles(id) ON DELETE SET NULL,
  is_verified BOOLEAN DEFAULT FALSE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  -- At least one social link or website is required
  CONSTRAINT at_least_one_link CHECK (
    website_url IS NOT NULL OR 
    twitter_url IS NOT NULL OR 
    instagram_url IS NOT NULL OR 
    facebook_url IS NOT NULL
  )
);

-- Community leaders table (extends user_profiles)
CREATE TABLE public.community_leaders (
  id UUID PRIMARY KEY REFERENCES public.user_profiles(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  role TEXT, -- Optional role within organization (e.g., "Director", "Volunteer Coordinator")
  bio TEXT,
  profile_image_url TEXT,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Zipcodes that community leaders work in
CREATE TABLE public.community_leader_zipcodes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  community_leader_id UUID NOT NULL REFERENCES public.community_leaders(id) ON DELETE CASCADE,
  zipcode TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(community_leader_id, zipcode)
);

-- Organization zipcodes (aggregated from community leaders)
CREATE TABLE public.organization_zipcodes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  zipcode TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(organization_id, zipcode)
);

-- Events posted by community leaders
CREATE TABLE public.events (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  community_leader_id UUID NOT NULL REFERENCES public.community_leaders(id) ON DELETE CASCADE,
  organization_id UUID NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT NOT NULL,
  event_type TEXT NOT NULL CHECK (event_type IN ('event', 'news', 'information', 'announcement')),
  event_date TIMESTAMP WITH TIME ZONE, -- Optional, only for actual events
  location TEXT, -- Optional location description
  image_url TEXT,
  external_link TEXT,
  is_published BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Event zipcodes (tags for where event is relevant)
CREATE TABLE public.event_zipcodes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  event_id UUID NOT NULL REFERENCES public.events(id) ON DELETE CASCADE,
  zipcode TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(event_id, zipcode)
);

-- Create indexes for performance
CREATE INDEX idx_organizations_name ON public.organizations(name);
CREATE INDEX idx_community_leaders_organization ON public.community_leaders(organization_id);
CREATE INDEX idx_community_leader_zipcodes_leader ON public.community_leader_zipcodes(community_leader_id);
CREATE INDEX idx_community_leader_zipcodes_zipcode ON public.community_leader_zipcodes(zipcode);
CREATE INDEX idx_organization_zipcodes_org ON public.organization_zipcodes(organization_id);
CREATE INDEX idx_organization_zipcodes_zipcode ON public.organization_zipcodes(zipcode);
CREATE INDEX idx_events_community_leader ON public.events(community_leader_id);
CREATE INDEX idx_events_organization ON public.events(organization_id);
CREATE INDEX idx_events_created_at ON public.events(created_at DESC);
CREATE INDEX idx_event_zipcodes_event ON public.event_zipcodes(event_id);
CREATE INDEX idx_event_zipcodes_zipcode ON public.event_zipcodes(zipcode);

-- Enable Row Level Security
ALTER TABLE public.organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_leaders ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.community_leader_zipcodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.organization_zipcodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.event_zipcodes ENABLE ROW LEVEL SECURITY;

-- RLS Policies for organizations
CREATE POLICY "Organizations are viewable by everyone"
  ON public.organizations FOR SELECT
  USING (true);

CREATE POLICY "Authenticated users can create organizations"
  ON public.organizations FOR INSERT
  WITH CHECK (auth.uid() = created_by);

CREATE POLICY "Organization creators can update their organizations"
  ON public.organizations FOR UPDATE
  USING (auth.uid() = created_by);

-- RLS Policies for community_leaders
CREATE POLICY "Community leaders are viewable by everyone"
  ON public.community_leaders FOR SELECT
  USING (true);

CREATE POLICY "Users can insert their own community leader profile"
  ON public.community_leaders FOR INSERT
  WITH CHECK (auth.uid() = id);

CREATE POLICY "Community leaders can update their own profile"
  ON public.community_leaders FOR UPDATE
  USING (auth.uid() = id);

CREATE POLICY "Community leaders can delete their own profile"
  ON public.community_leaders FOR DELETE
  USING (auth.uid() = id);

-- RLS Policies for community_leader_zipcodes
CREATE POLICY "Community leader zipcodes are viewable by everyone"
  ON public.community_leader_zipcodes FOR SELECT
  USING (true);

CREATE POLICY "Community leaders can manage their own zipcodes"
  ON public.community_leader_zipcodes FOR ALL
  USING (auth.uid() = community_leader_id);

-- RLS Policies for organization_zipcodes
CREATE POLICY "Organization zipcodes are viewable by everyone"
  ON public.organization_zipcodes FOR SELECT
  USING (true);

-- Allow automatic insertion via trigger
CREATE POLICY "Organization zipcodes can be auto-inserted"
  ON public.organization_zipcodes FOR INSERT
  WITH CHECK (true);

CREATE POLICY "Organization zipcodes can be auto-deleted"
  ON public.organization_zipcodes FOR DELETE
  USING (true);

-- RLS Policies for events
CREATE POLICY "Published events are viewable by everyone"
  ON public.events FOR SELECT
  USING (is_published = true OR auth.uid() = community_leader_id);

CREATE POLICY "Community leaders can create events"
  ON public.events FOR INSERT
  WITH CHECK (auth.uid() = community_leader_id);

CREATE POLICY "Community leaders can update their own events"
  ON public.events FOR UPDATE
  USING (auth.uid() = community_leader_id);

CREATE POLICY "Community leaders can delete their own events"
  ON public.events FOR DELETE
  USING (auth.uid() = community_leader_id);

-- RLS Policies for event_zipcodes
CREATE POLICY "Event zipcodes are viewable by everyone"
  ON public.event_zipcodes FOR SELECT
  USING (true);

CREATE POLICY "Event zipcodes can be managed with event"
  ON public.event_zipcodes FOR ALL
  USING (
    EXISTS (
      SELECT 1 FROM public.events
      WHERE events.id = event_zipcodes.event_id
      AND events.community_leader_id = auth.uid()
    )
  );

-- Function to sync organization zipcodes from community leader zipcodes
CREATE OR REPLACE FUNCTION sync_organization_zipcodes()
RETURNS TRIGGER AS $$
BEGIN
  -- When a community leader zipcode is added, add it to organization zipcodes
  IF (TG_OP = 'INSERT') THEN
    INSERT INTO public.organization_zipcodes (organization_id, zipcode)
    SELECT cl.organization_id, NEW.zipcode
    FROM public.community_leaders cl
    WHERE cl.id = NEW.community_leader_id
    ON CONFLICT (organization_id, zipcode) DO NOTHING;
    
  -- When a community leader zipcode is deleted, check if other leaders have it
  ELSIF (TG_OP = 'DELETE') THEN
    DELETE FROM public.organization_zipcodes oz
    WHERE oz.zipcode = OLD.zipcode
    AND oz.organization_id IN (
      SELECT organization_id FROM public.community_leaders WHERE id = OLD.community_leader_id
    )
    AND NOT EXISTS (
      SELECT 1 FROM public.community_leader_zipcodes clz
      JOIN public.community_leaders cl ON clz.community_leader_id = cl.id
      WHERE cl.organization_id = oz.organization_id
      AND clz.zipcode = OLD.zipcode
      AND clz.id != OLD.id
    );
  END IF;
  
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to sync organization zipcodes
CREATE TRIGGER sync_org_zipcodes_on_leader_zipcode_change
  AFTER INSERT OR DELETE ON public.community_leader_zipcodes
  FOR EACH ROW
  EXECUTE FUNCTION sync_organization_zipcodes();

-- Triggers for updated_at
CREATE TRIGGER update_organizations_updated_at
  BEFORE UPDATE ON public.organizations
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_community_leaders_updated_at
  BEFORE UPDATE ON public.community_leaders
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_events_updated_at
  BEFORE UPDATE ON public.events
  FOR EACH ROW
  EXECUTE FUNCTION update_updated_at_column();

-- View to get organizations with their community leaders by zipcode
CREATE OR REPLACE VIEW public.organizations_by_zipcode AS
SELECT
  oz.zipcode,
  o.id as organization_id,
  o.name as organization_name,
  o.description as organization_description,
  o.website_url,
  o.twitter_url,
  o.instagram_url,
  o.facebook_url,
  json_agg(
    json_build_object(
      'id', cl.id,
      'role', cl.role,
      'bio', cl.bio,
      'profile_image_url', cl.profile_image_url,
      'email', up.email
    )
  ) as community_leaders
FROM public.organization_zipcodes oz
JOIN public.organizations o ON oz.organization_id = o.id
JOIN public.community_leaders cl ON cl.organization_id = o.id
JOIN public.user_profiles up ON up.id = cl.id
JOIN public.community_leader_zipcodes clz ON clz.community_leader_id = cl.id AND clz.zipcode = oz.zipcode
WHERE cl.is_active = true
GROUP BY oz.zipcode, o.id, o.name, o.description, o.website_url, o.twitter_url, o.instagram_url, o.facebook_url;

-- View to get events by zipcode
CREATE OR REPLACE VIEW public.events_by_zipcode AS
SELECT DISTINCT
  ez.zipcode,
  e.id as event_id,
  e.title,
  e.description,
  e.event_type,
  e.event_date,
  e.location,
  e.image_url,
  e.external_link,
  e.created_at,
  o.id as organization_id,
  o.name as organization_name,
  cl.id as community_leader_id,
  up.email as posted_by_email
FROM public.event_zipcodes ez
JOIN public.events e ON ez.event_id = e.id
JOIN public.community_leaders cl ON e.community_leader_id = cl.id
JOIN public.organizations o ON e.organization_id = o.id
JOIN public.user_profiles up ON up.id = cl.id
WHERE e.is_published = true
ORDER BY e.created_at DESC;

-- Storage bucket for event images
INSERT INTO storage.buckets (id, name, public) 
VALUES ('event-images', 'event-images', true)
ON CONFLICT (id) DO NOTHING;

-- Storage bucket for profile images
INSERT INTO storage.buckets (id, name, public) 
VALUES ('profile-images', 'profile-images', true)
ON CONFLICT (id) DO NOTHING;

-- Storage policies for event images
CREATE POLICY "Event images are publicly accessible"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'event-images');

CREATE POLICY "Authenticated users can upload event images"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'event-images' AND auth.role() = 'authenticated');

CREATE POLICY "Users can update their own event images"
  ON storage.objects FOR UPDATE
  USING (bucket_id = 'event-images' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can delete their own event images"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'event-images' AND auth.uid()::text = (storage.foldername(name))[1]);

-- Storage policies for profile images
CREATE POLICY "Profile images are publicly accessible"
  ON storage.objects FOR SELECT
  USING (bucket_id = 'profile-images');

CREATE POLICY "Authenticated users can upload profile images"
  ON storage.objects FOR INSERT
  WITH CHECK (bucket_id = 'profile-images' AND auth.role() = 'authenticated');

CREATE POLICY "Users can update their own profile images"
  ON storage.objects FOR UPDATE
  USING (bucket_id = 'profile-images' AND auth.uid()::text = (storage.foldername(name))[1]);

CREATE POLICY "Users can delete their own profile images"
  ON storage.objects FOR DELETE
  USING (bucket_id = 'profile-images' AND auth.uid()::text = (storage.foldername(name))[1]);

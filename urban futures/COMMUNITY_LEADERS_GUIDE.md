# Community Leader Features - Implementation Guide

## Overview

This implementation adds a comprehensive community leader system to ReforestNYC, allowing community organizations to:
- Create and manage organizational profiles
- Sign up community leaders with specific zipcodes
- Post events, news, and announcements
- Display organization activities in neighborhood views
- Show events on the landing page and zipcode-specific sidebars

## Database Schema

### New Tables

1. **organizations**
   - Stores organization information
   - Requires at least one social link (website, Twitter, Instagram, or Facebook)
   - Can be verified by admins

2. **community_leaders**
   - Links users to organizations
   - Stores leader profiles (role, bio, profile image)
   - References user_profiles table

3. **community_leader_zipcodes**
   - Maps community leaders to the zipcodes they work in
   - Multiple zipcodes per leader supported

4. **organization_zipcodes**
   - Auto-synced aggregate of zipcodes from all leaders in an organization
   - Used for efficient queries

5. **events**
   - Posts created by community leaders
   - Types: event, news, information, announcement
   - Optional event date, location, image, external link

6. **event_zipcodes**
   - Tags events to specific zipcodes
   - Events can be tagged to multiple zipcodes

### Database Views

- **organizations_by_zipcode**: Pre-joined view showing organizations and their leaders by zipcode
- **events_by_zipcode**: Pre-joined view showing events with organization info by zipcode

### Triggers

- **sync_organization_zipcodes**: Automatically maintains organization_zipcodes table when leader zipcodes change

## File Structure

### Database Migration
- `urban futures/supabase/migrations/002_community_leaders.sql` - Full schema for community leader features
- Updated `001_initial_schema.sql` to support 'community_leader' user type

### Backend
- `urban futures/backend/src/api/communityLeaderRoutes.ts` - API routes (minimal, most logic in Supabase)
- Updated `urban futures/backend/src/index.ts` to include community leader routes

### Frontend Components

#### Setup & Dashboard
- `CommunityLeaderSetup.tsx` - Multi-step setup wizard
  - Organization selection/creation
  - Zipcode selection
  - Profile completion
- `CommunityLeaderDashboard.tsx` - Leader dashboard for managing events

#### Display Components
- `OrganizationsSection.tsx` - Shows organizations in zipcode sidebars
- `EventsSection.tsx` - Displays events (reusable for landing page and sidebars)

#### Styling
- `CommunityLeaderSetup.css`
- `CommunityLeaderDashboard.css`
- `OrganizationsSection.css`
- `EventsSection.css`

### Updates to Existing Files

#### `AuthContext.tsx`
- Added support for 'community_leader' user type in signup

#### `AuthModal.tsx`
- Added "Community Leader" signup option with icon
- Routes to setup flow after signup

#### `App.tsx`
- Detects community leader users
- Redirects to setup if profile incomplete
- Shows dashboard button for community leaders
- Handles setup completion flow

#### `Sidebar.tsx`
- Displays `OrganizationsSection` for zipcode
- Displays `EventsSection` for zipcode (limited to 5)

#### `LandingPage.tsx`
- Displays `EventsSection` showing all recent events (limit 20)

#### `lib/supabase.ts`
- Added TypeScript interfaces for:
  - Organization
  - CommunityLeader
  - CommunityLeaderZipcode
  - Event
  - EventZipcode

## User Flow

### Community Leader Signup

1. User clicks "Community Leader" option in auth modal
2. Creates account with email/password
3. Automatically redirected to setup flow
4. **Step 1: Organization**
   - Search existing organizations
   - Select existing or create new
   - New organizations require name + at least one social link
5. **Step 2: Zipcodes**
   - Select from NYC zipcodes list
   - Can select multiple zipcodes
6. **Step 3: Profile**
   - Optional: Add role, bio, profile image
   - Complete setup

### Post Events

1. Community leader clicks "Dashboard" button
2. Views statistics and existing posts
3. Clicks "Create Event/Post"
4. Fills out form:
   - Type (event, news, information, announcement)
   - Title and description
   - Optional: Date, location, image, external link
   - Tag to specific zipcodes
5. Post is immediately visible in tagged zipcodes

### Public View

#### In Neighborhood Sidebars
- Users viewing a specific zipcode see:
  - Organizations active in that area
  - Dropdown showing community leaders
  - Recent events tagged to that zipcode

#### On Landing Page
- All users see recent events from all organizations
- Events are expandable with full details
- Links to external resources if provided

## Security

### Row Level Security (RLS)

All tables have RLS enabled with appropriate policies:

- **Organizations**: Public read, creators can update
- **Community Leaders**: Public read, self-manage
- **Events**: Public read published events, leaders manage their own
- **Zipcodes**: Public read, leaders manage their own

### Storage Buckets

Two public storage buckets created:
- `event-images`: For event photos
- `profile-images`: For community leader profile photos

Policies ensure users can only modify their own uploads.

## API Endpoints

Most data access is handled via Supabase client directly from frontend. Backend provides:

- `GET /api/community-leaders/stats` - Placeholder for aggregated stats
- `GET /zipcodes` - List of NYC zipcodes (existing endpoint)

## Features Summary

### For Community Leaders
✅ Multi-step guided setup
✅ Organization management (create/join)
✅ Multiple zipcode coverage
✅ Event posting with rich media
✅ Event type categorization
✅ Geographic tagging of events
✅ Dashboard with statistics
✅ Event management (create, delete)

### For Regular Users
✅ View organizations in neighborhoods
✅ See community leaders and their roles
✅ Access organization social links
✅ Browse events by zipcode
✅ View all recent events on landing page
✅ Rich event details with images
✅ External links to event pages

## Future Enhancements

Potential additions:
- Event editing functionality
- Event image galleries
- RSVP/attendance tracking
- Email notifications for event updates
- Organization verification process
- Analytics dashboard for community leaders
- Event search and filtering
- Calendar view for events
- Integration with NYC open data for official events
- Community leader messaging system

## Testing Checklist

### Database
- [ ] Run migration 002_community_leaders.sql
- [ ] Verify all tables created
- [ ] Test organization creation with various social links
- [ ] Verify trigger syncs organization_zipcodes

### Authentication
- [ ] Sign up as community leader
- [ ] Verify setup flow appears
- [ ] Complete all setup steps
- [ ] Sign out and sign back in

### Organization Management
- [ ] Search for organizations
- [ ] Create new organization
- [ ] Verify social link validation
- [ ] Select multiple zipcodes

### Event Management
- [ ] Create event with all fields
- [ ] Create announcement without date/location
- [ ] Upload event image
- [ ] Tag to multiple zipcodes
- [ ] Delete event
- [ ] View event in sidebar
- [ ] View event on landing page

### Display
- [ ] View organizations in zipcode sidebar
- [ ] Expand organization to see leaders
- [ ] Click social links
- [ ] View events in zipcode sidebar
- [ ] View events on landing page
- [ ] Expand event details

## Deployment Notes

1. **Database Migration**
   - Run `001_initial_schema.sql` if not already run
   - Run `002_community_leaders.sql`
   - Verify storage buckets created

2. **Environment Variables**
   - No new variables required
   - Uses existing REACT_APP_SUPABASE_URL and REACT_APP_SUPABASE_ANON_KEY

3. **Storage Setup**
   - Ensure `event-images` and `profile-images` buckets are public
   - Verify storage policies are created

4. **Backend**
   - Rebuild TypeScript: `npm run build`
   - Restart server

5. **Frontend**
   - Install dependencies if needed: `npm install`
   - Rebuild: `npm run build`
   - Restart development server

## Support

For issues or questions:
- Check Supabase logs for database errors
- Verify RLS policies if permission errors occur
- Check browser console for frontend errors
- Verify storage bucket permissions for upload issues

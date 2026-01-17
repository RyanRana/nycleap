import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { supabase, Event, CommunityLeader, Organization } from '../lib/supabase';
import '../styles/CommunityLeaderDashboard.css';

interface CommunityLeaderDashboardProps {
  onNavigate?: (page: 'map' | 'leaderboard' | 'about') => void;
}

const CommunityLeaderDashboard: React.FC<CommunityLeaderDashboardProps> = ({ onNavigate }) => {
  const { user, profile, signOut } = useAuth();
  const [leaderProfile, setLeaderProfile] = useState<CommunityLeader | null>(null);
  const [organization, setOrganization] = useState<Organization | null>(null);
  const [events, setEvents] = useState<Event[]>([]);
  const [leaderZipcodes, setLeaderZipcodes] = useState<string[]>([]);
  const [allZipcodes, setAllZipcodes] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateEvent, setShowCreateEvent] = useState(false);
  
  // Event form state
  const [eventTitle, setEventTitle] = useState('');
  const [eventDescription, setEventDescription] = useState('');
  const [eventType, setEventType] = useState<'event' | 'news' | 'information' | 'announcement'>('event');
  const [eventDate, setEventDate] = useState('');
  const [eventLocation, setEventLocation] = useState('');
  const [eventImage, setEventImage] = useState<File | null>(null);
  const [eventExternalLink, setEventExternalLink] = useState('');
  const [selectedEventZipcodes, setSelectedEventZipcodes] = useState<string[]>([]);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadLeaderProfile();
  }, [user]);

  const loadLeaderProfile = async () => {
    if (!user) return;

    try {
      setLoading(true);

      // Load community leader profile
      const { data: leaderData, error: leaderError } = await supabase
        .from('community_leaders')
        .select('*, organization:organizations(*)')
        .eq('id', user.id)
        .single();

      if (leaderError) throw leaderError;
      
      setLeaderProfile(leaderData);
      setOrganization(leaderData.organization);

      // Load leader's zipcodes
      const { data: zipcodesData, error: zipcodesError } = await supabase
        .from('community_leader_zipcodes')
        .select('zipcode')
        .eq('community_leader_id', user.id);

      if (zipcodesError) throw zipcodesError;
      
      const zips = zipcodesData.map(z => z.zipcode);
      setLeaderZipcodes(zips);
      
      // Load all NYC zipcodes for event tagging
      const response = await fetch('http://localhost:3001/zipcodes');
      const data = await response.json();
      setAllZipcodes(data.zipcodes || []);

      // Load events
      await loadEvents();
    } catch (err) {
      console.error('Error loading leader profile:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadEvents = async () => {
    if (!user) return;

    try {
      const { data, error } = await supabase
        .from('events')
        .select('*')
        .eq('community_leader_id', user.id)
        .order('created_at', { ascending: false });

      if (error) throw error;
      setEvents(data || []);
    } catch (err) {
      console.error('Error loading events:', err);
    }
  };

  const handleCreateEvent = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!user || !organization) {
      setError('Missing user or organization information');
      return;
    }

    if (selectedEventZipcodes.length === 0) {
      setError('Please select at least one zipcode for this event');
      return;
    }

    setSaving(true);
    setError('');

    try {
      // Upload event image if provided
      let imageUrl: string | undefined;
      if (eventImage) {
        const fileExt = eventImage.name.split('.').pop();
        const fileName = `${user.id}/${Date.now()}.${fileExt}`;
        
        const { data: uploadData, error: uploadError } = await supabase.storage
          .from('event-images')
          .upload(fileName, eventImage);

        if (!uploadError && uploadData) {
          const { data: { publicUrl } } = supabase.storage
            .from('event-images')
            .getPublicUrl(fileName);
          imageUrl = publicUrl;
        }
      }

      // Create event
      const { data: eventData, error: eventError } = await supabase
        .from('events')
        .insert({
          community_leader_id: user.id,
          organization_id: organization.id,
          title: eventTitle,
          description: eventDescription,
          event_type: eventType,
          event_date: eventDate || null,
          location: eventLocation || null,
          image_url: imageUrl || null,
          external_link: eventExternalLink || null,
          is_published: true,
        })
        .select()
        .single();

      if (eventError) throw eventError;

      // Add zipcode tags
      const zipcodeInserts = selectedEventZipcodes.map(zipcode => ({
        event_id: eventData.id,
        zipcode: zipcode,
      }));

      const { error: zipcodeError } = await supabase
        .from('event_zipcodes')
        .insert(zipcodeInserts);

      if (zipcodeError) throw zipcodeError;

      // Reset form
      setEventTitle('');
      setEventDescription('');
      setEventType('event');
      setEventDate('');
      setEventLocation('');
      setEventImage(null);
      setEventExternalLink('');
      setSelectedEventZipcodes([]);
      setShowCreateEvent(false);

      // Reload events
      await loadEvents();
    } catch (err: any) {
      console.error('Error creating event:', err);
      setError(err.message || 'Failed to create event');
    } finally {
      setSaving(false);
    }
  };

  const handleDeleteEvent = async (eventId: string) => {
    if (!window.confirm('Are you sure you want to delete this event?')) return;

    try {
      const { error } = await supabase
        .from('events')
        .delete()
        .eq('id', eventId);

      if (error) throw error;
      
      await loadEvents();
    } catch (err) {
      console.error('Error deleting event:', err);
      alert('Failed to delete event');
    }
  };

  const toggleEventZipcode = (zipcode: string) => {
    setSelectedEventZipcodes(prev =>
      prev.includes(zipcode)
        ? prev.filter(z => z !== zipcode)
        : [...prev, zipcode]
    );
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <div className="spinner"></div>
        <p>Loading dashboard...</p>
      </div>
    );
  }

  if (!leaderProfile || !organization) {
    return (
      <div className="dashboard-error">
        <h2>Community Leader profile not found</h2>
        <p>Please complete the setup process first.</p>
      </div>
    );
  }

  return (
    <div className="community-leader-dashboard">
      <div className="dashboard-content">
        <div className="dashboard-header">
          <div className="header-content">
            <h1>{organization.name}</h1>
            {leaderProfile.role && <p className="role">{leaderProfile.role}</p>}
          </div>
          <button 
            className="btn-create-event"
            onClick={() => setShowCreateEvent(true)}
          >
            + Create Event/Post
          </button>
        </div>

        <div className="dashboard-stats">
        <div className="stat-card">
          <div className="stat-number">{leaderZipcodes.length}</div>
          <div className="stat-label">Active Zipcodes</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{events.length}</div>
          <div className="stat-label">Total Posts</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{events.filter(e => e.event_type === 'event').length}</div>
          <div className="stat-label">Events</div>
        </div>
      </div>

      {showCreateEvent && (
        <div className="modal-overlay" onClick={() => setShowCreateEvent(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <button 
              className="modal-close"
              onClick={() => setShowCreateEvent(false)}
            >
              ✕
            </button>
            
            <h2>Create New Post</h2>
            
            <form onSubmit={handleCreateEvent}>
              <div className="form-group">
                <label>Type *</label>
                <select 
                  value={eventType}
                  onChange={(e) => setEventType(e.target.value as any)}
                  required
                >
                  <option value="event">Event</option>
                  <option value="news">News</option>
                  <option value="information">Information</option>
                  <option value="announcement">Announcement</option>
                </select>
              </div>

              <div className="form-group">
                <label>Title *</label>
                <input
                  type="text"
                  value={eventTitle}
                  onChange={(e) => setEventTitle(e.target.value)}
                  required
                  placeholder="Enter title..."
                />
              </div>

              <div className="form-group">
                <label>Description *</label>
                <textarea
                  value={eventDescription}
                  onChange={(e) => setEventDescription(e.target.value)}
                  required
                  rows={4}
                  placeholder="Enter description..."
                />
              </div>

              {eventType === 'event' && (
                <>
                  <div className="form-group">
                    <label>Event Date</label>
                    <input
                      type="datetime-local"
                      value={eventDate}
                      onChange={(e) => setEventDate(e.target.value)}
                    />
                  </div>

                  <div className="form-group">
                    <label>Location</label>
                    <input
                      type="text"
                      value={eventLocation}
                      onChange={(e) => setEventLocation(e.target.value)}
                      placeholder="Event location..."
                    />
                  </div>
                </>
              )}

              <div className="form-group">
                <label>Image</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => {
                    const file = e.target.files?.[0];
                    if (file) {
                      if (file.size > 5 * 1024 * 1024) {
                        setError('Image must be less than 5MB');
                        return;
                      }
                      setEventImage(file);
                      setError('');
                    }
                  }}
                />
                {eventImage && (
                  <div className="image-preview">
                    <img src={URL.createObjectURL(eventImage)} alt="Event preview" />
                  </div>
                )}
              </div>

              <div className="form-group">
                <label>External Link</label>
                <input
                  type="url"
                  value={eventExternalLink}
                  onChange={(e) => setEventExternalLink(e.target.value)}
                  placeholder="https://..."
                />
              </div>

              <div className="form-group">
                <label>Tag Zipcodes * (where is this relevant?)</label>
                <div className="zipcode-tags">
                  <div className="quick-select">
                    <button
                      type="button"
                      className="btn-small"
                      onClick={() => setSelectedEventZipcodes([...leaderZipcodes])}
                    >
                      Select All My Zipcodes
                    </button>
                    <button
                      type="button"
                      className="btn-small"
                      onClick={() => setSelectedEventZipcodes([])}
                    >
                      Clear All
                    </button>
                  </div>
                  <div className="zipcode-grid">
                    {allZipcodes.map(zipcode => (
                      <div
                        key={zipcode}
                        className={`zipcode-tag ${selectedEventZipcodes.includes(zipcode) ? 'selected' : ''}`}
                        onClick={() => toggleEventZipcode(zipcode)}
                      >
                        {zipcode}
                      </div>
                    ))}
                  </div>
                </div>
                <small>Selected: {selectedEventZipcodes.length} zipcode(s)</small>
              </div>

              {error && <div className="error-message">{error}</div>}

              <div className="form-actions">
                <button 
                  type="button"
                  className="btn-secondary"
                  onClick={() => setShowCreateEvent(false)}
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  className="btn-primary"
                  disabled={saving}
                >
                  {saving ? 'Creating...' : 'Create Post'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      <div className="events-section">
        <h2>Your Posts</h2>
        {events.length === 0 ? (
          <div className="no-events">
            <p>You haven't created any posts yet.</p>
            <button onClick={() => setShowCreateEvent(true)}>
              Create Your First Post
            </button>
          </div>
        ) : (
          <div className="events-grid">
            {events.map(event => (
              <div key={event.id} className="event-card">
                {event.image_url && (
                  <div className="event-image">
                    <img src={event.image_url} alt={event.title} />
                  </div>
                )}
                <div className="event-content">
                  <div className="event-type-badge">{event.event_type}</div>
                  <h3>{event.title}</h3>
                  <p>{event.description}</p>
                  {event.event_date && (
                    <p className="event-date">
                      📅 {new Date(event.event_date).toLocaleString()}
                    </p>
                  )}
                  {event.location && (
                    <p className="event-location">📍 {event.location}</p>
                  )}
                  <div className="event-actions">
                    <button 
                      className="btn-delete"
                      onClick={() => handleDeleteEvent(event.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
    </div>
  );
};

export default CommunityLeaderDashboard;

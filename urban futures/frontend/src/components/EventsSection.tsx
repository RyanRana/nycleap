import React, { useState, useEffect } from 'react';
import { supabase } from '../lib/supabase';
import '../styles/EventsSection.css';

interface Event {
  zipcode: string;
  event_id: string;
  title: string;
  description: string;
  event_type: 'event' | 'news' | 'information' | 'announcement';
  event_date: string | null;
  location: string | null;
  image_url: string | null;
  external_link: string | null;
  created_at: string;
  organization_id: string;
  organization_name: string;
  community_leader_id: string;
  posted_by_email: string;
}

interface EventsSectionProps {
  zipcode?: string; // If provided, show events for this zipcode only
  limit?: number; // Limit number of events shown
  showAll?: boolean; // Show all events regardless of zipcode
}

const EventsSection: React.FC<EventsSectionProps> = ({ zipcode, limit = 10, showAll = false }) => {
  const [events, setEvents] = useState<Event[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadEvents();
  }, [zipcode, showAll]);

  const loadEvents = async () => {
    try {
      setLoading(true);
      
      let query = supabase
        .from('events_by_zipcode')
        .select('*')
        .order('created_at', { ascending: false });

      if (!showAll && zipcode) {
        query = query.eq('zipcode', zipcode);
      }

      if (limit) {
        query = query.limit(limit);
      }

      const { data, error } = await query;

      if (error) {
        console.error('Error loading events:', error);
        return;
      }

      // Remove duplicates by event_id
      const uniqueEvents = data?.reduce((acc: Event[], event: any) => {
        if (!acc.find(e => e.event_id === event.event_id)) {
          acc.push(event);
        }
        return acc;
      }, []) || [];

      setEvents(uniqueEvents);
    } catch (err) {
      console.error('Error loading events:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleEvent = (eventId: string) => {
    setExpandedEvents(prev => {
      const newSet = new Set(prev);
      if (newSet.has(eventId)) {
        newSet.delete(eventId);
      } else {
        newSet.add(eventId);
      }
      return newSet;
    });
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return null;
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', { 
      weekday: 'short',
      month: 'short', 
      day: 'numeric', 
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  };

  const getEventTypeIcon = (type: string, isLanding: boolean = false): React.ReactNode => {
    if (type === 'information' && isLanding) {
      return (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="16" x2="12" y2="12"></line>
          <line x1="12" y1="8" x2="12.01" y2="8"></line>
        </svg>
      );
    }
    switch (type) {
      case 'event': return '📅';
      case 'news': return '📰';
      case 'information': return 'ℹ️';
      case 'announcement': return '📢';
      default: return '📌';
    }
  };

  const getEventTypeColor = (type: string) => {
    switch (type) {
      case 'event': return '#14532d';
      case 'news': return '#166534';
      case 'information': return '#15803d';
      case 'announcement': return '#16a34a';
      default: return '#718096';
    }
  };

  if (loading) {
    return (
      <div className="events-section">
        <div className="section-header">
          <h3>Community Events & News</h3>
        </div>
        <div className="loading-text">Loading events...</div>
      </div>
    );
  }

  if (events.length === 0) {
    return null; // Don't show section if no events
  }

  // Landing page layout (showAll = true) - card grid like initiatives
  if (showAll) {
    return (
      <div className="events-section">
        <h2 className="subsection-title">Community Events & News</h2>
        <div className="events-grid-landing">
          {events.map((event) => (
            <div key={`${event.event_id}-${event.zipcode || 'all'}`} className="event-card-landing">
              <div className="event-image-wrapper-landing">
                {event.image_url ? (
                  <img src={event.image_url} alt={event.title} className="event-image-landing" />
                ) : (
                  <div className="event-image-placeholder-bg" />
                )}
                <div className="event-type-badge-landing">
                  {getEventTypeIcon(event.event_type, true)}
                </div>
              </div>
              <div className="event-content-landing">
                <div className="event-header-row-landing">
                  <div className="event-author-landing">
                    <div className="event-author-icon-landing">🌱</div>
                    <div className="event-author-info-landing">
                      <span className="event-author-name-landing">
                        {event.organization_name || event.posted_by_email?.split('@')[0]}
                      </span>
                      <span className="event-date-landing">{formatDate(event.created_at)}</span>
                    </div>
                  </div>
                </div>
                {event.description && (
                  <p className="event-caption-landing">{event.description}</p>
                )}
                <div className="event-location-landing">
                  📍 ZIP: {event.zipcode || 'N/A'}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  // Sidebar layout - expandable list
  return (
    <div className="events-section">
      <div className="section-header">
        <h3>
          {zipcode && !showAll 
            ? `Events & News in ${zipcode}` 
            : 'Community Events & News'}
        </h3>
        <div className="events-count">{events.length}</div>
      </div>
      
      <div className="events-list">
        {events.map((event) => (
          <div key={`${event.event_id}-${event.zipcode || 'all'}`} className="event-item">
            <div 
              className="event-header"
              onClick={() => toggleEvent(event.event_id)}
            >
              <div className="event-main-info">
                <div className="event-type-row">
                  <span 
                    className="event-type-badge"
                    style={{ background: getEventTypeColor(event.event_type) }}
                  >
                    {getEventTypeIcon(event.event_type)} {event.event_type}
                  </span>
                  <span className="event-org">{event.organization_name}</span>
                </div>
                <h4>{event.title}</h4>
                {event.event_date && (
                  <p className="event-date-preview">📅 {formatDate(event.event_date)}</p>
                )}
              </div>
              <button className="event-toggle">
                {expandedEvents.has(event.event_id) ? '−' : '+'}
              </button>
            </div>

            {expandedEvents.has(event.event_id) && (
              <div className="event-details">
                {event.image_url && (
                  <div className="event-image">
                    <img src={event.image_url} alt={event.title} />
                  </div>
                )}
                
                <div className="event-description">
                  {event.description}
                </div>

                {event.location && (
                  <div className="event-location">
                    📍 {event.location}
                  </div>
                )}

                {event.external_link && (
                  <a 
                    href={event.external_link} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="event-link"
                  >
                    Learn More →
                  </a>
                )}

                <div className="event-meta">
                  <span className="event-posted-by">
                    Posted by {event.posted_by_email}
                  </span>
                  <span className="event-posted-date">
                    {new Date(event.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default EventsSection;

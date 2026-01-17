import React, { useState, useEffect } from 'react';
import { supabase, Organization, CommunityLeader } from '../lib/supabase';
import '../styles/OrganizationsSection.css';

interface OrganizationsSectionProps {
  zipcode: string;
}

interface OrgData {
  zipcode: string;
  organization_id: string;
  organization_name: string;
  organization_description: string | null;
  website_url: string | null;
  twitter_url: string | null;
  instagram_url: string | null;
  facebook_url: string | null;
  community_leaders: Array<{
    id: string;
    role: string | null;
    bio: string | null;
    profile_image_url: string | null;
    email: string;
  }>;
}

const OrganizationsSection: React.FC<OrganizationsSectionProps> = ({ zipcode }) => {
  const [organizations, setOrganizations] = useState<OrgData[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedOrgs, setExpandedOrgs] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadOrganizations();
  }, [zipcode]);

  const loadOrganizations = async () => {
    if (!zipcode) return;

    try {
      setLoading(true);
      
      // Query the organizations_by_zipcode view
      const { data, error } = await supabase
        .from('organizations_by_zipcode')
        .select('*')
        .eq('zipcode', zipcode);

      if (error) {
        console.error('Error loading organizations:', error);
        return;
      }

      setOrganizations(data || []);
    } catch (err) {
      console.error('Error loading organizations:', err);
    } finally {
      setLoading(false);
    }
  };

  const toggleOrganization = (orgId: string) => {
    setExpandedOrgs(prev => {
      const newSet = new Set(prev);
      if (newSet.has(orgId)) {
        newSet.delete(orgId);
      } else {
        newSet.add(orgId);
      }
      return newSet;
    });
  };

  if (loading) {
    return (
      <div className="organizations-section">
        <div className="section-header">
          <h3>Local Organizations</h3>
        </div>
        <div className="loading-text">Loading organizations...</div>
      </div>
    );
  }

  if (organizations.length === 0) {
    return null; // Don't show section if no organizations
  }

  return (
    <div className="organizations-section">
      <div className="section-header">
        <h3>Active Organizations in {zipcode}</h3>
        <div className="org-count">{organizations.length}</div>
      </div>
      
      <div className="organizations-list">
        {organizations.map((org) => (
          <div key={org.organization_id} className="organization-item">
            <div 
              className="org-header"
              onClick={() => toggleOrganization(org.organization_id)}
            >
              <div className="org-main-info">
                <h4>{org.organization_name}</h4>
                {org.organization_description && (
                  <p className="org-description">{org.organization_description}</p>
                )}
              </div>
              <button className="org-toggle">
                {expandedOrgs.has(org.organization_id) ? '−' : '+'}
              </button>
            </div>

            {expandedOrgs.has(org.organization_id) && (
              <div className="org-details">
                {/* Social Links */}
                {(org.website_url || org.twitter_url || org.instagram_url || org.facebook_url) && (
                  <div className="org-links">
                    {org.website_url && (
                      <a href={org.website_url} target="_blank" rel="noopener noreferrer" className="org-link">
                        🌐 Website
                      </a>
                    )}
                    {org.twitter_url && (
                      <a href={org.twitter_url} target="_blank" rel="noopener noreferrer" className="org-link">
                        🐦 Twitter
                      </a>
                    )}
                    {org.instagram_url && (
                      <a href={org.instagram_url} target="_blank" rel="noopener noreferrer" className="org-link">
                        📷 Instagram
                      </a>
                    )}
                    {org.facebook_url && (
                      <a href={org.facebook_url} target="_blank" rel="noopener noreferrer" className="org-link">
                        👍 Facebook
                      </a>
                    )}
                  </div>
                )}

                {/* Community Leaders */}
                {org.community_leaders && org.community_leaders.length > 0 && (
                  <div className="leaders-section">
                    <h5>Community Leaders ({org.community_leaders.length})</h5>
                    <div className="leaders-list">
                      {org.community_leaders.map((leader) => (
                        <div key={leader.id} className="leader-card">
                          {leader.profile_image_url && (
                            <img 
                              src={leader.profile_image_url} 
                              alt={leader.email}
                              className="leader-avatar"
                            />
                          )}
                          <div className="leader-info">
                            <div className="leader-email">{leader.email}</div>
                            {leader.role && (
                              <div className="leader-role">{leader.role}</div>
                            )}
                            {leader.bio && (
                              <div className="leader-bio">{leader.bio}</div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};

export default OrganizationsSection;

import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { supabase, Organization } from '../lib/supabase';
import '../styles/CommunityLeaderSetup.css';

interface CommunityLeaderSetupProps {
  onComplete: () => void;
  onNavigate?: (page: 'map' | 'leaderboard' | 'about') => void;
}

const CommunityLeaderSetup: React.FC<CommunityLeaderSetupProps> = ({ onComplete, onNavigate }) => {
  const { user, profile, signOut } = useAuth();
  const [step, setStep] = useState<'organization' | 'zipcodes' | 'profile'>('organization');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  
  // Organization step
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const [showCreateOrg, setShowCreateOrg] = useState(false);
  const [newOrgName, setNewOrgName] = useState('');
  const [newOrgDescription, setNewOrgDescription] = useState('');
  const [newOrgWebsite, setNewOrgWebsite] = useState('');
  const [newOrgTwitter, setNewOrgTwitter] = useState('');
  const [newOrgInstagram, setNewOrgInstagram] = useState('');
  const [newOrgFacebook, setNewOrgFacebook] = useState('');
  
  // Zipcodes step
  const [allZipcodes, setAllZipcodes] = useState<string[]>([]);
  const [selectedZipcodes, setSelectedZipcodes] = useState<string[]>([]);
  const [zipcodeSearch, setZipcodeSearch] = useState('');
  
  // Profile step
  const [role, setRole] = useState('');
  const [bio, setBio] = useState('');
  const [profileImage, setProfileImage] = useState<File | null>(null);

  useEffect(() => {
    loadOrganizations();
    loadZipcodes();
  }, []);

  const loadOrganizations = async () => {
    try {
      const { data, error } = await supabase
        .from('organizations')
        .select('*')
        .order('name');
      
      if (error) throw error;
      setOrganizations(data || []);
    } catch (err) {
      console.error('Error loading organizations:', err);
    }
  };

  const loadZipcodes = async () => {
    try {
      const response = await fetch('http://localhost:3001/zipcodes');
      const data = await response.json();
      setAllZipcodes(data.zipcodes || []);
    } catch (err) {
      console.error('Error loading zipcodes:', err);
      // Fallback to common NYC zipcodes if API fails
      setAllZipcodes(['10001', '10002', '10003', '10004', '10005', '10009', '10010', '10011', '10012', '10013', '10014']);
    }
  };

  const handleCreateOrganization = async () => {
    if (!user || !newOrgName) {
      setError('Organization name is required');
      return;
    }

    // Validate at least one social link
    if (!newOrgWebsite && !newOrgTwitter && !newOrgInstagram && !newOrgFacebook) {
      setError('At least one link (website, Twitter, Instagram, or Facebook) is required');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const { data, error } = await supabase
        .from('organizations')
        .insert({
          name: newOrgName,
          description: newOrgDescription || null,
          website_url: newOrgWebsite || null,
          twitter_url: newOrgTwitter || null,
          instagram_url: newOrgInstagram || null,
          facebook_url: newOrgFacebook || null,
          created_by: user.id,
        })
        .select()
        .single();

      if (error) throw error;
      
      setSelectedOrgId(data.id);
      setShowCreateOrg(false);
      await loadOrganizations();
    } catch (err: any) {
      console.error('Error creating organization:', err);
      setError(err.message || 'Failed to create organization');
    } finally {
      setLoading(false);
    }
  };

  const handleOrganizationNext = () => {
    if (!selectedOrgId) {
      setError('Please select or create an organization');
      return;
    }
    setError('');
    setStep('zipcodes');
  };

  const handleZipcodesNext = () => {
    if (selectedZipcodes.length === 0) {
      setError('Please select at least one zipcode');
      return;
    }
    setError('');
    setStep('profile');
  };

  const handleComplete = async () => {
    if (!user || !selectedOrgId) {
      setError('Missing required information');
      return;
    }

    setLoading(true);
    setError('');

    try {
      // Upload profile image if provided
      let profileImageUrl: string | undefined;
      if (profileImage) {
        const fileExt = profileImage.name.split('.').pop();
        const fileName = `${user.id}/profile.${fileExt}`;
        
        const { data: uploadData, error: uploadError } = await supabase.storage
          .from('profile-images')
          .upload(fileName, profileImage, { upsert: true });

        if (!uploadError && uploadData) {
          const { data: { publicUrl } } = supabase.storage
            .from('profile-images')
            .getPublicUrl(fileName);
          profileImageUrl = publicUrl;
        }
      }

      // Create community leader profile
      const { error: leaderError } = await supabase
        .from('community_leaders')
        .insert({
          id: user.id,
          organization_id: selectedOrgId,
          role: role || null,
          bio: bio || null,
          profile_image_url: profileImageUrl || null,
        });

      if (leaderError) throw leaderError;

      // Add zipcodes
      const zipcodeInserts = selectedZipcodes.map(zipcode => ({
        community_leader_id: user.id,
        zipcode: zipcode,
      }));

      const { error: zipcodeError } = await supabase
        .from('community_leader_zipcodes')
        .insert(zipcodeInserts);

      if (zipcodeError) throw zipcodeError;

      onComplete();
    } catch (err: any) {
      console.error('Error completing setup:', err);
      setError(err.message || 'Failed to complete setup');
    } finally {
      setLoading(false);
    }
  };

  const filteredOrganizations = organizations.filter(org =>
    org.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const filteredZipcodes = allZipcodes.filter(zip =>
    zip.includes(zipcodeSearch)
  );

  const toggleZipcode = (zipcode: string) => {
    setSelectedZipcodes(prev =>
      prev.includes(zipcode)
        ? prev.filter(z => z !== zipcode)
        : [...prev, zipcode]
    );
  };

  const renderOrganizationStep = () => (
    <div className="setup-step">
      <h2>Select Your Organization</h2>
      <p className="step-description">
        Choose the organization you represent, or create a new one if it doesn't exist.
      </p>

      {!showCreateOrg ? (
        <>
          <div className="search-box">
            <input
              type="text"
              placeholder="Search organizations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          <div className="organization-list">
            {filteredOrganizations.length === 0 ? (
              <div className="no-results">
                <p>No organizations found.</p>
                <button 
                  className="btn-create-org"
                  onClick={() => setShowCreateOrg(true)}
                >
                  Create New Organization
                </button>
              </div>
            ) : (
              <>
                {filteredOrganizations.map(org => (
                  <div
                    key={org.id}
                    className={`organization-item ${selectedOrgId === org.id ? 'selected' : ''}`}
                    onClick={() => setSelectedOrgId(org.id)}
                  >
                    <div className="org-info">
                      <h3>{org.name}</h3>
                      {org.description && <p>{org.description}</p>}
                      <div className="org-links">
                        {org.website_url && <span>🌐 Website</span>}
                        {org.twitter_url && <span>🐦 Twitter</span>}
                        {org.instagram_url && <span>📷 Instagram</span>}
                        {org.facebook_url && <span>👍 Facebook</span>}
                      </div>
                    </div>
                    {org.is_verified && <span className="verified-badge">✓ Verified</span>}
                  </div>
                ))}
                <button 
                  className="btn-create-org secondary"
                  onClick={() => setShowCreateOrg(true)}
                >
                  + Create New Organization
                </button>
              </>
            )}
          </div>

          {error && <div className="error-message">{error}</div>}
          
          <div className="step-actions">
            <button 
              className="btn-primary"
              onClick={handleOrganizationNext}
              disabled={!selectedOrgId}
            >
              Next: Select Zipcodes
            </button>
          </div>
        </>
      ) : (
        <div className="create-org-form">
          <h3>Create New Organization</h3>
          
          <div className="form-group">
            <label>Organization Name *</label>
            <input
              type="text"
              value={newOrgName}
              onChange={(e) => setNewOrgName(e.target.value)}
              placeholder="Green Brooklyn Initiative"
              required
            />
          </div>

          <div className="form-group">
            <label>Description</label>
            <textarea
              value={newOrgDescription}
              onChange={(e) => setNewOrgDescription(e.target.value)}
              placeholder="Brief description of your organization..."
              rows={3}
            />
          </div>

          <div className="form-group">
            <label>Website URL</label>
            <input
              type="url"
              value={newOrgWebsite}
              onChange={(e) => setNewOrgWebsite(e.target.value)}
              placeholder="https://example.org"
            />
          </div>

          <div className="form-group">
            <label>Twitter URL</label>
            <input
              type="url"
              value={newOrgTwitter}
              onChange={(e) => setNewOrgTwitter(e.target.value)}
              placeholder="https://twitter.com/yourorg"
            />
          </div>

          <div className="form-group">
            <label>Instagram URL</label>
            <input
              type="url"
              value={newOrgInstagram}
              onChange={(e) => setNewOrgInstagram(e.target.value)}
              placeholder="https://instagram.com/yourorg"
            />
          </div>

          <div className="form-group">
            <label>Facebook URL</label>
            <input
              type="url"
              value={newOrgFacebook}
              onChange={(e) => setNewOrgFacebook(e.target.value)}
              placeholder="https://facebook.com/yourorg"
            />
          </div>

          <p className="form-hint">* At least one link (website or social media) is required</p>

          {error && <div className="error-message">{error}</div>}

          <div className="step-actions">
            <button 
              className="btn-secondary"
              onClick={() => {
                setShowCreateOrg(false);
                setError('');
              }}
            >
              Cancel
            </button>
            <button 
              className="btn-primary"
              onClick={handleCreateOrganization}
              disabled={loading}
            >
              {loading ? 'Creating...' : 'Create Organization'}
            </button>
          </div>
        </div>
      )}
    </div>
  );

  const renderZipcodesStep = () => (
    <div className="setup-step">
      <h2>Select Zipcodes You Work In</h2>
      <p className="step-description">
        Choose the NYC zipcodes where your organization is active. You can select multiple.
      </p>

      <div className="search-box">
        <input
          type="text"
          placeholder="Search zipcodes..."
          value={zipcodeSearch}
          onChange={(e) => setZipcodeSearch(e.target.value)}
        />
      </div>

      <div className="selected-count">
        Selected: {selectedZipcodes.length} zipcode{selectedZipcodes.length !== 1 ? 's' : ''}
      </div>

      <div className="zipcode-grid">
        {filteredZipcodes.map(zipcode => (
          <div
            key={zipcode}
            className={`zipcode-item ${selectedZipcodes.includes(zipcode) ? 'selected' : ''}`}
            onClick={() => toggleZipcode(zipcode)}
          >
            {zipcode}
            {selectedZipcodes.includes(zipcode) && <span className="check">✓</span>}
          </div>
        ))}
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="step-actions">
        <button 
          className="btn-secondary"
          onClick={() => setStep('organization')}
        >
          Back
        </button>
        <button 
          className="btn-primary"
          onClick={handleZipcodesNext}
          disabled={selectedZipcodes.length === 0}
        >
          Next: Complete Profile
        </button>
      </div>
    </div>
  );

  const renderProfileStep = () => (
    <div className="setup-step">
      <h2>Complete Your Profile</h2>
      <p className="step-description">
        Add some information about yourself (optional but recommended).
      </p>

      <div className="form-group">
        <label>Your Role</label>
        <input
          type="text"
          value={role}
          onChange={(e) => setRole(e.target.value)}
          placeholder="e.g., Director, Volunteer Coordinator, Community Organizer"
        />
      </div>

      <div className="form-group">
        <label>Bio</label>
        <textarea
          value={bio}
          onChange={(e) => setBio(e.target.value)}
          placeholder="Tell us about yourself and your work..."
          rows={4}
        />
      </div>

      <div className="form-group">
        <label>Profile Image</label>
        <input
          type="file"
          accept="image/*"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) {
              if (file.size > 2 * 1024 * 1024) {
                setError('Image must be less than 2MB');
                return;
              }
              setProfileImage(file);
              setError('');
            }
          }}
        />
        {profileImage && (
          <div className="image-preview">
            <img src={URL.createObjectURL(profileImage)} alt="Profile preview" />
          </div>
        )}
      </div>

      {error && <div className="error-message">{error}</div>}

      <div className="step-actions">
        <button 
          className="btn-secondary"
          onClick={() => setStep('zipcodes')}
        >
          Back
        </button>
        <button 
          className="btn-primary"
          onClick={handleComplete}
          disabled={loading}
        >
          {loading ? 'Completing...' : 'Complete Setup'}
        </button>
      </div>
    </div>
  );

  return (
    <div className="community-leader-setup">
      {/* Header Navigation */}
      <header className="setup-header-nav">
        <div className="header-left">
          <div className="brand-name">ReforestNYC</div>
        </div>
        <nav className="header-nav">
          {onNavigate && (
            <>
              <a href="#" onClick={(e) => { e.preventDefault(); onNavigate('map'); }} className="nav-link">Map</a>
              <a href="#" onClick={(e) => { e.preventDefault(); onNavigate('leaderboard'); }} className="nav-link">Leaderboard</a>
              <a href="#" onClick={(e) => { e.preventDefault(); onNavigate('about'); }} className="nav-link">Mission</a>
            </>
          )}
          <button onClick={signOut} className="nav-link logout-btn">
            Logout
          </button>
        </nav>
      </header>

      <div className="setup-container">
        <div className="setup-header">
          <h1>Community Leader Setup</h1>
          <div className="setup-progress">
            <div className={`progress-step ${step === 'organization' ? 'active' : ''} ${step !== 'organization' ? 'completed' : ''}`}>
              1. Organization
            </div>
            <div className={`progress-step ${step === 'zipcodes' ? 'active' : ''} ${step === 'profile' ? 'completed' : ''}`}>
              2. Zipcodes
            </div>
            <div className={`progress-step ${step === 'profile' ? 'active' : ''}`}>
              3. Profile
            </div>
          </div>
        </div>

        {step === 'organization' && renderOrganizationStep()}
        {step === 'zipcodes' && renderZipcodesStep()}
        {step === 'profile' && renderProfileStep()}
      </div>
    </div>
  );
};

export default CommunityLeaderSetup;

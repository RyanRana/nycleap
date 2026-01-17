import React, { useState, useEffect } from 'react';
import MapComponent from './components/MapComponent';
import Sidebar from './components/Sidebar';
import Information from './components/Information';
import LandingPage from './components/LandingPage';
import MapInstructions from './components/MapInstructions';
import AuthModal from './components/AuthModal';
import Leaderboard from './components/Leaderboard';
import CommunityLeaderSetup from './components/CommunityLeaderSetup';
import CommunityLeaderDashboard from './components/CommunityLeaderDashboard';
import { useAuth } from './contexts/AuthContext';
import { supabase } from './lib/supabase';
import './styles/App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:3001';

interface H3Data {
  h3_cell: string;
  location_name?: string;
  impact_per_dollar: number;
  recommended_tree_count: number;
  projected_temp_reduction_F: number;
  projected_pm25_reduction_lbs_per_year: number;
  priority_final: number;
  ej_score: number;
  features: any;
}

type Page = 'map' | 'information' | 'leaderboard' | 'community-leader-setup' | 'community-leader-dashboard';

function App() {
  const { user, profile, isGuest, loading: authLoading } = useAuth();
  const [showLanding, setShowLanding] = useState(true);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [selectedH3, setSelectedH3] = useState<H3Data | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentPage, setCurrentPage] = useState<Page>('map');
  const [instructionsDismissed, setInstructionsDismissed] = useState(false);
  const [isCommunityLeader, setIsCommunityLeader] = useState(false);
  const [needsSetup, setNeedsSetup] = useState(false);

  // Check if user is a community leader and if they need setup
  useEffect(() => {
    const checkCommunityLeaderStatus = async () => {
      if (!user || !profile) return;

      if (profile.user_type === 'community_leader') {
        setIsCommunityLeader(true);

        // Check if they have completed setup
        const { data, error } = await supabase
          .from('community_leaders')
          .select('id')
          .eq('id', user.id)
          .single();

        if (error || !data) {
          // They need to complete setup
          setNeedsSetup(true);
          setCurrentPage('community-leader-setup');
          setShowLanding(false);
        } else {
          setNeedsSetup(false);
        }
      }
    };

    checkCommunityLeaderStatus();
  }, [user, profile]);

  const handleCommunityLeaderSetupComplete = () => {
    setNeedsSetup(false);
    setCurrentPage('community-leader-dashboard');
  };

  const handleNavigateFromCommunityPages = (page: 'map' | 'leaderboard' | 'about') => {
    if (page === 'about') {
      setShowLanding(true);
      setCurrentPage('map');
    } else {
      setShowLanding(false);
      setCurrentPage(page);
    }
  };

  const handleLandingNavigate = (page: 'map' | 'leaderboard' | 'community-leader-dashboard') => {
    // Show auth modal if user is not logged in and not a guest (only for map)
    if (page === 'map' && !user && !isGuest && !authLoading) {
      setShowAuthModal(true);
    }
    
    if (page === 'community-leader-dashboard') {
      setShowLanding(false);
      setCurrentPage('community-leader-dashboard');
      return;
    }
    
    setShowLanding(false);
    setCurrentPage(page);
    // Clear any selected cell when navigating to map
    if (page === 'map') {
      setSelectedH3(null);
      setLoading(false);
    }
  };

  const handleAuthModalClose = () => {
    setShowAuthModal(false);
    // Always show map after closing modal (user selected an option or closed it)
    setShowLanding(false);
    setCurrentPage('map');
    // Clear any selected cell when opening map
    setSelectedH3(null);
    setLoading(false);
  };

  const handleBackToLanding = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setShowLanding(true);
    // Clear selected cell when going back to landing
    setSelectedH3(null);
    setLoading(false);
  };

  // Clear selected cell when switching away from map page
  useEffect(() => {
    if (currentPage !== 'map') {
      setSelectedH3(null);
      setLoading(false);
    }
  }, [currentPage]);

  const handleH3Click = async (h3Cell: string) => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/h3/${h3Cell}`);
      if (response.ok) {
        const data = await response.json();
        console.log('Received H3 data:', data);
        setSelectedH3(data);
      } else {
        console.error('Failed to fetch H3 data:', response.status);
      }
    } catch (error) {
      console.error('Error fetching H3 data:', error);
    } finally {
      setLoading(false);
    }
  };


  if (showLanding) {
    return <LandingPage onNavigate={handleLandingNavigate} />;
  }

  // Show community leader setup if needed
  if (needsSetup && currentPage === 'community-leader-setup') {
    return <CommunityLeaderSetup onComplete={handleCommunityLeaderSetupComplete} onNavigate={handleNavigateFromCommunityPages} />;
  }

  // Show community leader dashboard
  if (currentPage === 'community-leader-dashboard') {
    return <CommunityLeaderDashboard onNavigate={handleNavigateFromCommunityPages} />;
  }

  return (
    <div className="app">
      {showAuthModal && <AuthModal onClose={handleAuthModalClose} />}
      
      <header className="app-header">
        <div className="header-content">
          <button
            type="button"
            className="back-button"
            onClick={handleBackToLanding}
            onTouchStart={(e) => e.stopPropagation()}
          >
            <span className="back-icon">←</span>
            <span className="back-text">back</span>
          </button>
        </div>
      </header>
      <div className="app-content">
        {currentPage === 'map' && (
          <>
        <MapComponent
          onH3Click={handleH3Click}
          selectedH3={selectedH3}
        />
            {!selectedH3 && !loading && !instructionsDismissed && <MapInstructions onDismiss={() => setInstructionsDismissed(true)} />}
            {selectedH3 && <Sidebar h3Data={selectedH3} loading={loading} onClose={() => { setSelectedH3(null); setLoading(false); }} />}
          </>
        )}
        {currentPage === 'leaderboard' && <Leaderboard />}
        {currentPage === 'information' && <Information />}
      </div>
    </div>
  );
}

export default App;


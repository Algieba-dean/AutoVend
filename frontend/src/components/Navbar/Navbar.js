import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import './Navbar.css';

const Navbar = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const handleLogoClick = () => {
    navigate('/');
  };

  return (
    <header className="navbar-header">
      <nav className="navbar">
        <div className="logo-brand" onClick={handleLogoClick}>
          <div className="logo-icon">
            <i className="fa-solid fa-car-rear"></i>
          </div>
          <span className="logo-text">AUTO<span className="logo-highlight">VEND</span></span>
          <span className="logo-tag">AI SALES SUITE</span>
        </div>

        <div className="nav-links">
          <button 
            className={`nav-btn ${location.pathname === '/' ? 'active' : ''}`}
            onClick={() => navigate('/')}
          >
            <i className="fa-solid fa-house"></i> Home
          </button>
          <button 
            className={`nav-btn ${location.pathname.startsWith('/select-user') || location.pathname.startsWith('/chat') || location.pathname.startsWith('/user-profile') ? 'active' : ''}`}
            onClick={() => navigate('/select-user')}
          >
            <i className="fa-solid fa-robot"></i> Sales Agent
          </button>
          <button 
            className={`nav-btn ${location.pathname.startsWith('/dealer-portal') ? 'active' : ''}`}
            onClick={() => navigate('/dealer-portal')}
          >
            <i className="fa-solid fa-store"></i> 4S Dealer Portal
          </button>
          <button 
            className={`nav-btn ${location.pathname.startsWith('/voice-test') ? 'active' : ''}`}
            onClick={() => navigate('/voice-test')}
          >
            <i className="fa-solid fa-microphone-lines"></i> 语音实验室
          </button>
        </div>

        <div className="nav-system-status">
          <span className="status-dot-active"></span>
          <span className="status-label">RAG + Voice WS Active</span>
        </div>
      </nav>
    </header>
  );
};

export default Navbar;
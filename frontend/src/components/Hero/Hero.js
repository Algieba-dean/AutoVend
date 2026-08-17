import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Hero.css';

const Hero = () => {
  const navigate = useNavigate();

  const handleStartDemo = () => {
    navigate('/select-user');
  };

  const handleDealerPortal = () => {
    navigate('/dealer-portal');
  };

  return (
    <div className="hero-container">
      <div className="hero-content">
        <div className="hero-badge">
          <span className="badge-sparkle">✨</span>
          <span>NEXT-GEN AI AUTOMOTIVE AGENT</span>
        </div>

        <h1 className="hero-title">
          Intelligent Automotive <br />
          <span className="gradient-text">Sales & Discovery Suite</span>
        </h1>

        <p className="hero-subtitle">
          Driven by Hybrid RAG (Dense + Sparse + Structure), 1281 vehicle models data, 
          and full-duplex WebSocket real-time voice interaction for seamless 4S sales assistance.
        </p>

        <div className="hero-cta-group">
          <button className="btn-primary" onClick={handleStartDemo}>
            <i className="fa-solid fa-play"></i> Start Demo Experience
          </button>
          <button className="btn-secondary" onClick={handleDealerPortal}>
            <i className="fa-solid fa-chart-line"></i> 4S Dealer Portal
          </button>
        </div>

        <div className="hero-stats-grid">
          <div className="stat-card">
            <div className="stat-value">1,281</div>
            <div className="stat-label">Vehicle Models Indexed</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">56-Dim</div>
            <div className="stat-label">Structured Tag Filtering</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">Websocket</div>
            <div className="stat-label">Full-Duplex Voice Call</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">Groq / vLLM</div>
            <div className="stat-label">Hybrid LLM Router</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Hero;
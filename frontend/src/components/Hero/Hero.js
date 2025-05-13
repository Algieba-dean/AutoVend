import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Hero.css';

const Hero = () => {
  const navigate = useNavigate();

  const handleStartDemo = () => {
    navigate('/select-user');
  };

  return (
    <div className="hero">
      <div className="welcome">Welcome</div>
      <div className="title">
        <div className="title-line">Auto<span>mobile</span>,</div>
        <div className="title-line">Vend<span>ing machine</span>,</div>
        <div className="title-line"><span>AI Phone Assistant</span></div>
      </div>
      <div className="subtitle">Help you to find your beloved vehicles</div>
      <div className="cta-buttons">
        <button className="demo-btn" onClick={handleStartDemo}>Start the demo!</button>
        <button className="learn-btn">Learn More</button>
      </div>
    </div>
  );
};

export default Hero;
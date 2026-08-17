import React from 'react';
import { useNavigate } from 'react-router-dom';
import './UserSelect.css';

const UserSelect = () => {
  const navigate = useNavigate();

  const handleCardClick = (type) => {
    navigate('/user-profile', { state: { userType: type } });
  };

  return (
    <div className="user-select-container">
      <div className="user-select-header">
        <span className="select-step-badge">STEP 01 // SELECT CUSTOMER PROFILE</span>
        <h2 className="select-title">Choose Your Interaction Persona</h2>
        <p className="select-subtitle">Select a predefined profile, create a fresh session, or build a custom buyer profile for the AI Agent.</p>
      </div>

      <div className="user-cards-grid">
        <div className="user-card-item" onClick={() => handleCardClick('default')}>
          <div className="card-top-bar">
            <span className="card-badge default">Pre-configured</span>
          </div>
          <div className="card-icon-box default">
            <i className="fa-solid fa-user-gear"></i>
          </div>
          <h3>Default User Profile</h3>
          <p>Pre-populated with rich customer preferences, budget ranges, and driving habits to test immediate car recommendations.</p>
          <div className="card-action-link">
            <span>Select Default</span>
            <i className="fa-solid fa-arrow-right"></i>
          </div>
        </div>

        <div className="user-card-item" onClick={() => handleCardClick('empty')}>
          <div className="card-top-bar">
            <span className="card-badge empty">Fresh Start</span>
          </div>
          <div className="card-icon-box empty">
            <i className="fa-solid fa-user-plus"></i>
          </div>
          <h3>Empty User Profile</h3>
          <p>Start a brand new customer journey from scratch. The AI Sales Agent will discover your needs through natural dialogue.</p>
          <div className="card-action-link">
            <span>Start Fresh</span>
            <i className="fa-solid fa-arrow-right"></i>
          </div>
        </div>

        <div className="user-card-item" onClick={() => handleCardClick('custom')}>
          <div className="card-top-bar">
            <span className="card-badge custom">Custom Spec</span>
          </div>
          <div className="card-icon-box custom">
            <i className="fa-solid fa-sliders"></i>
          </div>
          <h3>Custom User Profile</h3>
          <p>Customize target driver, family size, car knowledge level (0-10), and price sensitivity for targeted test scenarios.</p>
          <div className="card-action-link">
            <span>Configure Spec</span>
            <i className="fa-solid fa-arrow-right"></i>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserSelect;
import React from 'react';
import { useNavigate } from 'react-router-dom';
import './UserSelect.css';

const UserSelect = () => {
  const navigate = useNavigate();

  const handleCardClick = (type) => {
    navigate('/user-profile', { state: { userType: type } });
  };

  return (
    <div className="user-select">
      <div className="user-cards">
        <div className="user-card" onClick={() => handleCardClick('default')}>
          <div className="card-icon">
            <i className="fas fa-comment"></i>
          </div>
          <h3>Default user</h3>
          <p>This pre-defined user profile can't be modified</p>
        </div>

        <div className="user-card" onClick={() => handleCardClick('empty')}>
          <div className="card-icon">
            <i className="fas fa-layer-group"></i>
          </div>
          <h3>Empty user</h3>
          <p>A brand new user profile to chat with our AI Assistant</p>
        </div>

        <div className="user-card" onClick={() => handleCardClick('custom')}>
          <div className="card-icon">
            <i className="fas fa-sync"></i>
          </div>
          <h3>Make your own choice!</h3>
          <p>Define your own user profile to chat with our AI Assistant</p>
        </div>
      </div>
    </div>
  );
};

export default UserSelect;
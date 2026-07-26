import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Navbar.css';

const Navbar = () => {
  const navigate = useNavigate();

  const handleLogoClick = () => {
    navigate('/');
  };

  return (
    <nav className="navbar">
      <div className="logo" onClick={handleLogoClick} style={{ cursor: 'pointer' }}>AUTOVEND</div>
      <div className="nav-links">
        <a href="/" className="active">Home</a>
      </div>
    </nav>
  );
};

export default Navbar;
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar/Navbar';
import Hero from './components/Hero/Hero';
import UserSelect from './components/UserSelect/UserSelect';
import UserProfile from './components/UserProfile/UserProfile';
import Chat from './components/Chat/Chat';
import './App.css';
import DealerPortal from './components/DealerPortal/DealerPortal';
import UserDetail from './components/DealerPortal/UserDetail';

function App() {
  return (
    <Router>
      <div className="app">
        <Navbar />
        <Routes>
          <Route path="/" element={<Hero />} />
          <Route path="/select-user" element={<UserSelect />} />
          <Route path="/user-profile" element={<UserProfile />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/dealer-portal" element={<DealerPortal />} />
          <Route path="/dealer-portal/user/:id" element={<UserDetail />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
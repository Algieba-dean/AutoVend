import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { profileService, chatService } from '../../services/api';
import './UserProfile.css';

const UserProfile = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const userType = location.state?.userType || 'default';
  const [phoneNumber, setPhoneNumber] = useState('');
  const [profile, setProfile] = useState({
    phone_number: '',
    user_title: '',
    name: '',
    target_driver: '',
    expertise: '',
    additional_information: {
      family_size: '',
      price_sensitivity: '',
      residence: '',
      parking_conditions: ''
    },
    connection_information: {
      connection_phone_number: '',
      connection_id_relationship: '',
      connection_user_name: ''
    }
  });
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadDefaultProfile = async () => {
      try {
        setIsLoading(true);
        const response = await profileService.getDefaultProfile();
        if (Array.isArray(response) && response[0]) {
          const profileData = response[0];
          setProfile(profileData);
        } else {
          console.error('No default profile date.');
        }
      } catch (error) {
        console.error('Failed to load the default profile:', error);
      } finally {
        setIsLoading(false);
      }
    };
    // Only call loadDefaultProfile when userType is default
    if (userType === 'default') {
      loadDefaultProfile();
    } else {
      setIsLoading(false); // For other types, directly set isLoading to false
    }
  }, [userType]); // Add userType as a dependency

  const createProfile = async () => {
    try {
      await profileService.createProfile(profile);
      return true; // Creation successful
    } catch (error) {
      console.error('Failed to save profile:', error);
      // Check error type to determine if user already exists
      if (error.response && error.response.status === 409) {
        if (userType === 'custom') {
          try {
            const existingProfile = await profileService.updateProfile(profile.phone_number, profile);
            setProfile(existingProfile);
            return true;
          } catch (fetchError) {
            console.error('Failed to fetch existing profile:', fetchError);
            setError('Unable to retrieve existing user profile, please try again');
            return false;
          }
        } else {
          setError('Phone number already exists, please use another number');
        }
      } else {
        setError('Save user failed, please try again');
      }
      return false; // Creation failed
    }
  };

  const handleBack = () => {
    navigate(-1);
  };

  const handlePhoneChange = (e) => {
    profile.phone_number = e.target.value;
    setPhoneNumber(e.target.value);
    setProfile(profile);
    setError(''); // Clear error message
  };

  const startSession = async () => {
    try {
      const sessionData = await chatService.startSession(profile.phone_number);
      // After successful storage, jump to the chat page and pass the session data
      navigate('/chat', {
        state: {
          sessionData,
          profile: sessionData.profile
        }
      });
    } catch (error) {
      setError('Failed to start chat session, please try again.');
      console.error('Error starting chat session:', error);
    }
  }

  const handleStartDemo = async () => {
    if (userType === 'custom') {
      // Verify all required fields for custom users
      if (!profile.phone_number.trim()) {
        setError('Please enter the phone number');
        return;
      }

      if (!/^\d+$/.test(profile.phone_number)) {
        setError('Please enter a valid numeric phone number');
        return;
      }

      try {
        const profileCreated = await createProfile();
        if (!profileCreated) {
          return; // If created failed, then return
        }
      } catch (error) {
        setError('Failed to save user information, please try again');
        console.error('Error saving user data:', error);
        return;
      }
    } else if (userType === 'empty') {
      // Empty User still needs to verify phone number
      if (!phoneNumber.trim()) {
        setError('Please enter the phone number');
        return;
      }

      if (!/^\d+$/.test(phoneNumber)) {
        setError('Please enter a valid phone number');
        return;
      }

      try {
        // Create the new empty user profile
        const profileCreated = await createProfile();
        if (!profileCreated) {
          return; // If creation failed, don't continue
        }
      } catch (error) {
        setError('Error saving phone number, please try again.');
        console.error('Error saving phone number:', error);
        return;
      }
    }
    startSession();
  };

  const getImageSrc = () => {
    switch (userType) {
      case 'empty':
        return process.env.PUBLIC_URL + '/images/video-chat-empty.png';
      case 'custom':
        return process.env.PUBLIC_URL + '/images/video-chat-empty.png';
      case 'default':
      default:
        return process.env.PUBLIC_URL + '/images/video-chat-default.png';
    }
  };

  const renderCustomProfileContent = () => {
    return (
      <>
        <div className="profile-header">
          <div className="red-line"></div>
          <h2>Custom User Profile</h2>
        </div>
        <div className="profile-info">
          <div className="info-item custom-item">
            <div className="input-group">
              <span className="input-label">Phone number:</span>
              <input
                type="tel"
                placeholder="Enter the phone number"
                value={profile.phone_number}
                onChange={(e) => setProfile({ ...profile, phone_number: e.target.value })}
                className="custom-input"
              />
            </div>
          </div>

          <div className="info-item custom-item">
            <div className="input-group">
              <span className="input-label">Title:</span>
              <select
                value={profile.user_title}
                onChange={(e) => {
                  const title = e.target.value;
                  setProfile(prevProfile => ({
                    ...prevProfile,
                    user_title: title
                  }));
                }}
                className="custom-input"
              >
                <option value="">Select the title</option>
                <option value="Mr.">Mr.</option>
                <option value="Mrs.">Mrs.</option>
                <option value="Miss.">Miss.</option>
                <option value="Ms.">Ms.</option>
              </select>
              <input
                type="text"
                placeholder="Name (e.g. Zhang)"
                value={profile.name}
                onChange={(e) => {
                  const name = e.target.value;
                  setProfile(prevProfile => ({
                    ...prevProfile,
                    name: name
                  }));
                }}
                className="custom-input"
                style={{ marginLeft: '10px' }}
              />
            </div>
          </div>

          <div className="info-item custom-item">
            <div className="input-group">
              <span className="input-label">Target driver:</span>
              <select
                value={profile.target_driver}
                onChange={(e) => setProfile({ ...profile, target_driver: e.target.value })}
                className="custom-input"
              >
                <option value="">Select target driver</option>
                <option value="Self">Self</option>
                <option value="Wife">Wife</option>
                <option value="Husband">Husband</option>
                <option value="Parents">Parents</option>
                <option value="Father">Father</option>
                <option value="Mother">Mother</option>
                <option value="Son">Son</option>
                <option value="Daughter">Daughter</option>
                <option value="Grandparents">Grandparents</option>
                <option value="Grandchildren">Grandchildren</option>
                <option value="Brother">Brother</option>
                <option value="Sister">Sister</option>
                <option value="Uncle">Uncle</option>
                <option value="Aunt">Aunt</option>
                <option value="Cousin">Cousin</option>
                <option value="Friend">Friend</option>
                <option value="Other">Other</option>
              </select>
            </div>
          </div>

          <div className="info-item custom-item">
            <div className="input-group">
              <span className="input-label">Expertise:</span>
              <select
                value={profile.expertise}
                onChange={(e) => setProfile({ ...profile, expertise: e.target.value })}
                className="custom-input"
              >
                <option value="">Select the expertise (0-10)</option>
                <option value="0">0 - Know nothing</option>
                <option value="1">1</option>
                <option value="2">2</option>
                <option value="3">3</option>
                <option value="4">4</option>
                <option value="5">5 - average</option>
                <option value="6">6</option>
                <option value="7">7</option>
                <option value="8">8</option>
                <option value="9">9</option>
                <option value="10">10 - Professional</option>
              </select>
            </div>
          </div>

          {/* <div className="section-header">
            <h3>Additional Information(Optional)</h3>
          </div>

          <div className="info-item custom-item">
            <div className="input-group">
              <span className="input-label">Family Size:</span>
              <input
                type="text"
                placeholder="e.g. 3"
                value={profile.additional_information.family_size}
                onChange={(e) => setProfile({
                  ...profile,
                  additional_information: {
                    ...profile.additional_information,
                    family_size: e.target.value
                  }
                })}
                className="custom-input"
              />
            </div>
          </div>

          <div className="info-item custom-item">
            <div className="input-group">
              <span className="input-label">Price Sensitivity:</span>
              <select
                value={profile.additional_information.price_sensitivity}
                onChange={(e) => setProfile({
                  ...profile,
                  additional_information: {
                    ...profile.additional_information,
                    price_sensitivity: e.target.value
                  }
                })}
                className="custom-input"
              >
                <option value="">Select price sensitivity</option>
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
              </select>
            </div>
          </div>

          <div className="info-item custom-item">
            <div className="input-group">
              <span className="input-label">Residence:</span>
              <input
                type="text"
                placeholder="e.g. China+Beijing+Haidian"
                value={profile.additional_information.residence}
                onChange={(e) => setProfile({
                  ...profile,
                  additional_information: {
                    ...profile.additional_information,
                    residence: e.target.value
                  }
                })}
                className="custom-input"
              />
            </div>
          </div>

          <div className="info-item custom-item">
            <div className="input-group">
              <span className="input-label">Parking Conditions:</span>
              <select
                value={profile.additional_information.parking_conditions}
                onChange={(e) => setProfile({
                  ...profile,
                  additional_information: {
                    ...profile.additional_information,
                    parking_conditions: e.target.value
                  }
                })}
                className="custom-input"
              >
                <option value="">Select parking conditions</option>
                <option value="Allocated Parking Space">Allocated Parking Space</option>
                <option value="Street Parking">Street Parking</option>
                <option value="Public Parking Lot">Public Parking Lot</option>
                <option value="No Parking">No Parking</option>
              </select>
            </div>
          </div> */}
        </div>
      </>
    );
  };

  const renderProfileContent = () => {
    switch (userType) {
      case 'custom':
        return renderCustomProfileContent();
      case 'empty':
        return (
          <>
            <div className="profile-header">
              <div className="red-line"></div>
              <h2>Empty User Profile</h2>
            </div>
            <div className="profile-info">
              <div className="info-item">
                <input
                  type="tel"
                  placeholder="Enter your phone number"
                  value={phoneNumber}
                  onChange={handlePhoneChange}
                  className={`phone-input ${error ? 'error' : ''}`}
                />
              </div>
            </div>
          </>
        );

      case 'default':
      default:
        return (
          <>
            <div className="profile-header">
              <div className="red-line"></div>
              <h2>Default User Profile</h2>
            </div>
            <div className="profile-info">
              {profile.name && (
                <div className="info-item">
                  <span className="info-label">Name: {profile.name}</span>
                </div>
              )}
              {profile.user_title && (
                <div className="info-item">
                  <span className="info-label">User title: {profile.user_title}</span>
                </div>
              )}
              {profile.phone_number && (
                <div className="info-item">
                  <span className="info-label">Phone number: {profile.phone_number}</span>
                </div>
              )}
              {profile.target_driver && (
                <div className="info-item">
                  <span className="info-label">Target driver: {profile.target_driver}</span>
                </div>
              )}
              {profile.expertise && (
                <div className="info-item">
                  <span className="info-label">Expertise: {profile.expertise}</span>
                </div>
              )}
              {profile.additional_information?.family_size && (
                <div className="info-item">
                  <span className="info-label">Family size: {profile.additional_information.family_size}</span>
                </div>
              )}
              {profile.additional_information?.price_sensitivity && (
                <div className="info-item">
                  <span className="info-label">Price Sensitivity: {profile.additional_information.price_sensitivity}</span>
                </div>
              )}
              {profile.additional_information?.residence && (
                <div className="info-item">
                  <span className="info-label">Residence: {profile.additional_information.residence}</span>
                </div>
              )}
              {profile.additional_information?.parking_conditions && (
                <div className="info-item">
                  <span className="info-label">Parking conditions: {profile.additional_information.parking_conditions}</span>
                </div>
              )}
            </div>
          </>
        );
    }
  };

  return (
    <div className="user-profile">
      <div className="back-button" onClick={handleBack}>
        ← Back
      </div>
      <div className="profile-container">
        <div className="profile-content">
          {renderProfileContent()}
          <button className="start-demo-btn" onClick={handleStartDemo}>
            Start the demo
          </button>
          {error && <div className="error-message global-error">{error}</div>}
        </div>
        <div className="profile-images">
          <img src={getImageSrc()} alt="Chat" className="chat-image" />
        </div>
      </div>
    </div>
  );
};

export default UserProfile;
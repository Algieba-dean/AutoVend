import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import './UserProfile.css';

const UserProfile = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const userType = location.state?.userType || 'default';
  const [phoneNumber, setPhoneNumber] = useState('');
  const [customInputs, setCustomInputs] = useState({
    name: '',
    job: '',
    phone: ''
  });
  const [error, setError] = useState('');

  const handleBack = () => {
    navigate(-1);
  };

  const handleCustomInputChange = (field, value) => {
    setCustomInputs(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handlePhoneChange = (e) => {
    setPhoneNumber(e.target.value);
    setError(''); // 清除错误信息
  };

  const handleStartDemo = async () => {
    if (userType === 'custom') {
      // 验证自定义用户的所有必填字段
      if (!customInputs.name.trim()) {
        setError('请输入姓名');
        return;
      }

      if (!customInputs.job.trim()) {
        setError('请输入职业');
        return;
      }

      if (!customInputs.phone.trim()) {
        setError('请输入电话号码');
        return;
      }

      if (!/^\d+$/.test(customInputs.phone)) {
        setError('请输入有效的数字电话号码');
        return;
      }

      // 验证额外字段
      for (const field of additionalFields) {
        if (!field.label.trim() || !field.value.trim()) {
          setError('请完整填写所有额外字段');
          return;
        }
      }

      try {
        // 将用户数据存储到后端
        await axios.post('/api/users', {
          ...customInputs,
          additionalFields,
          userType: 'custom'
        });

        // 存储成功后跳转到聊天页面
        navigate('/chat');
      } catch (error) {
        setError('保存用户信息失败，请重试');
        console.error('Error saving user data:', error);
      }
    } else if (userType === 'empty') {
      // 空用户需要验证电话号码
      if (!phoneNumber.trim()) {
        setError('Please enter the phone number');
        return;
      }

      if (!/^\d+$/.test(phoneNumber)) {
        setError('Please enter then valid phone number');
        return;
      }

      try {
        // 将电话号码存储到后端
        await axios.post('/api/users', {
          phoneNumber: phoneNumber,
          userType: 'empty'
        });

        // 存储成功后跳转到聊天页面，并传递用户信息
        navigate('/chat', { state: { userType: 'empty', phoneNumber } });
      } catch (error) {
        setError('Error saving phone number, please try it again.');
        console.error('Error saving phone number:', error);
      }
    } else {
      // default user 直接进入聊天页面，传递默认用户信息
      navigate('/chat', { state: { userType: 'default', phoneNumber: '123' } });
    }
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

  const nameOptions = ['Jane', 'John', 'Mike', '自定义'];
  const jobOptions = ['Car Engineer', 'Car Dealer', 'Car Designer', '自定义'];
  const phoneOptions = ['123-456-7890', '987-654-3210', '自定义'];

  const [additionalFields, setAdditionalFields] = useState([]);
  
  const labelOptions = [
    'Age',
    'Address',
    'Email',
    'Company',
    'Position',
    'Education'
  ];

  const handleAddField = () => {
    setAdditionalFields([...additionalFields, { label: '', value: '' }]);
  };

  const handleFieldChange = (index, field, value) => {
    const newFields = [...additionalFields];
    newFields[index][field] = value;
    setAdditionalFields(newFields);
  };

  const handleDeleteField = (index) => {
    const newFields = additionalFields.filter((_, i) => i !== index);
    setAdditionalFields(newFields);
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
              <span className="input-label">Name:</span>
              <input
                type="text"
                placeholder="Enter your name"
                value={customInputs.name}
                onChange={(e) => handleCustomInputChange('name', e.target.value)}
                className="custom-input"
              />
            </div>
          </div>
          <div className="info-item custom-item">
            <div className="input-group">
              <span className="input-label">Job:</span>
              <input
                type="text"
                placeholder="Enter your job"
                value={customInputs.job}
                onChange={(e) => handleCustomInputChange('job', e.target.value)}
                className="custom-input"
              />
            </div>
          </div>
          <div className="info-item custom-item">
            <div className="input-group">
              <span className="input-label">Phone:</span>
              <input
                type="tel"
                placeholder="Enter your phone number"
                value={customInputs.phone}
                onChange={(e) => handleCustomInputChange('phone', e.target.value)}
                className="custom-input"
              />
            </div>
          </div>
          
          {additionalFields.map((field, index) => (
            <div key={index} className="info-item custom-item">
              <div className="input-group">
                <select
                  value={field.label}
                  onChange={(e) => handleFieldChange(index, 'label', e.target.value)}
                  className="label-select"
                >
                  <option value="">Select label</option>
                  {labelOptions.map(option => (
                    <option key={option} value={option}>{option}</option>
                  ))}
                </select>
                <input
                  type="text"
                  placeholder="Enter value"
                  value={field.value}
                  onChange={(e) => handleFieldChange(index, 'value', e.target.value)}
                  className="custom-input"
                />
                <button 
                  className="delete-field-btn"
                  onClick={() => handleDeleteField(index)}
                >
                  -
                </button>
              </div>
            </div>
          ))}
          
          <button className="add-field-btn" onClick={handleAddField}>
            + Add label
          </button>
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
                {error && <div className="error-message">{error}</div>}
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
              <div className="info-item">
                <span className="info-label">Name: Jane</span>
              </div>
              <div className="info-item">
                <span className="info-label">Job: Car Engineer</span>
              </div>
              <div className="info-item">
                <span className="info-label">Phone number: 123</span>
              </div>
            </div>
          </>
        );
    }
  };

  // Remove this duplicate declaration
  // const handleStartDemo = () => {
  //   navigate('/chat');
  // };

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
        </div>
        <div className="profile-images">
          <img src={getImageSrc()} alt="Video chat" className="chat-image" />
        </div>
      </div>
    </div>
  );
};

export default UserProfile;
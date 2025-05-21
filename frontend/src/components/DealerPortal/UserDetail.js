import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './UserDetail.css';

const UserDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [userInfo, setUserInfo] = useState({
    name: '',
    carBrand: '',
    carModel: '',
    date: '',
    status: '',
    details: {
      phone: '',
      address: '',
      notes: ''
    }
  });
  const [isEditing, setIsEditing] = useState(false);

  useEffect(() => {
    // 模拟从后端获取用户数据
    const fetchUserData = () => {
      setUserInfo({
        name: 'John Smith',
        carBrand: 'BMW',
        carModel: 'X5 M Sport',
        date: '2024-03-15',
        status: 'pending',
        details: {
          phone: '+1 234 567 890',
          address: '123 Main St, City',
          notes: 'Preferred time: afternoon'
        }
      });
    };
    fetchUserData();
  }, [id]);

  const handleEdit = () => {
    setIsEditing(true);
  };

  const handleSave = async () => {
    try {
      // 这里添加保存到后端的逻辑
      setIsEditing(false);
    } catch (error) {
      console.error('保存失败:', error);
    }
  };

  const handleCancel = () => {
    setIsEditing(false);
  };

  const handleInputChange = (field, value) => {
    if (field.includes('.')) {
      const [parent, child] = field.split('.');
      setUserInfo(prev => ({
        ...prev,
        [parent]: {
          ...prev[parent],
          [child]: value
        }
      }));
    } else {
      setUserInfo(prev => ({
        ...prev,
        [field]: value
      }));
    }
  };

  return (
    <div className="user-detail">
      <div className="detail-header">
        <button className="back-btn" onClick={() => navigate(-1)}>← Back</button>
        <h1>User Detail</h1>
        {!isEditing ? (
          <button className="edit-btn" onClick={handleEdit}>Edit</button>
        ) : (
          <div className="action-buttons">
            <button className="save-btn" onClick={handleSave}>Save</button>
            <button className="cancel-btn" onClick={handleCancel}>Cancel</button>
          </div>
        )}
      </div>

      <div className="detail-content">
        <div className="detail-section">
          <h2>Basic Information</h2>
          <div className="info-grid">
            <div className="info-item">
              <label>Name</label>
              {isEditing ? (
                <input
                  type="text"
                  value={userInfo.name}
                  onChange={(e) => handleInputChange('name', e.target.value)}
                />
              ) : (
                <span>{userInfo.name}</span>
              )}
            </div>
            <div className="info-item">
              <label>Phone Number</label>
              {isEditing ? (
                <input
                  type="tel"
                  value={userInfo.details.phone}
                  onChange={(e) => handleInputChange('details.phone', e.target.value)}
                />
              ) : (
                <span>{userInfo.details.phone}</span>
              )}
            </div>
          </div>
        </div>
        <div className="detail-section">
          <h2>Contact Details</h2>
          <div className="info-grid">
            <div className="info-item">
              <label>Car Brand</label>
              {isEditing ? (
                <input
                  type="text"
                  value={userInfo.carBrand}
                  onChange={(e) => handleInputChange('carBrand', e.target.value)}
                />
              ) : (
                <span>{userInfo.carBrand}</span>
              )}
            </div>
            <div className="info-item">
              <label>Car Model</label>
              {isEditing ? (
                <input
                  type="text"
                  value={userInfo.carModel}
                  onChange={(e) => handleInputChange('carModel', e.target.value)}
                />
              ) : (
                <span>{userInfo.carModel}</span>
              )}
            </div>
            <div className="info-item">
              <label>Appointment Date</label>
              {isEditing ? (
                <input
                  type="date"
                  value={userInfo.date}
                  onChange={(e) => handleInputChange('date', e.target.value)}
                />
              ) : (
                <span>{userInfo.date}</span>
              )}
            </div>
            <div className="info-item">
              <label>Test Drive Location</label>
              {isEditing ? (
                <input
                  type="text"
                  value={userInfo.details.address}
                  onChange={(e) => handleInputChange('details.address', e.target.value)}
                />
              ) : (
                <span>{userInfo.details.address}</span>
              )}
            </div>
          </div>
        </div>

        <div className="detail-section">
          <h2>Notes</h2>
          <div className="notes-area">
            {isEditing ? (
              <textarea
                value={userInfo.details.notes}
                onChange={(e) => handleInputChange('details.notes', e.target.value)}
                rows="4"
              />
            ) : (
              <p>{userInfo.details.notes}</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default UserDetail;
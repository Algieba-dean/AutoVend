import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import './UserDetail.css';
import { reservationService } from '../../services/api';

const UserDetail = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const location = useLocation();
    const [userInfo, setUserInfo] = useState({
        name: '',
        carBrand: '',
        carModel: '',
        date: '',
        status: '',
        phone: '',
        address: '',
        notes: '',
        time: ''
    });
    const [isEditing, setIsEditing] = useState(false);
    const [errors, setErrors] = useState({});
    const [loading, setLoading] = useState(false);
    const [successMessage, setSuccessMessage] = useState('');

    useEffect(() => {
        // 检查是否有通过location.state传递的用户数据
        if (location.state && location.state.userInfo) {
            const { userInfo: userData } = location.state;

            // 使用传递的数据更新状态
            setUserInfo({
                name: userData.name || '',
                carBrand: userData.carBrand || '',
                carModel: userData.carModel || '',
                date: userData.date || '',
                status: userData.status || '',
                phone: userData.phone || '',
                address: userData.address || '',
                notes: userData.notes || '',
                time: userData.time || ''
            });
        } else {
            // 如果没有传递数据，则尝试通过API获取
            const fetchUserData = async () => {
                try {
                    // 这里可以添加通过API获取用户数据的逻辑
                    // 例如: const userData = await reservationService.getReservation(id);

                    // 暂时使用模拟数据作为后备
                    setUserInfo({
                        name: 'John Smith',
                        carBrand: 'BMW',
                        carModel: 'X5 M Sport',
                        date: '2024-03-15',
                        status: 'pending',
                        phone: '+1 234 567 890',
                        address: '123 Main St, City',
                        notes: 'Preferred time: afternoon'
                    });
                } catch (error) {
                    console.error('Failed to get user data:', error);
                }
            };

            fetchUserData();
        }
    }, [id, location.state]);

    const handleEdit = () => {
        setIsEditing(true);
    };

    const validateForm = () => {
        const newErrors = {};
        
        // Validate all required fields
        if (!userInfo.name.trim()) newErrors.name = 'Name cannot be empty';
        if (!userInfo.carBrand.trim()) newErrors.carBrand = 'Car brand cannot be empty';
        if (!userInfo.carModel.trim()) newErrors.carModel = 'Car model cannot be empty';
        if (!userInfo.date.trim()) newErrors.date = 'Date cannot be empty';
        
        // Validate phone number
        if (!userInfo.phone.trim()) {
            newErrors.phone = 'Phone number cannot be empty';
        } else if (!/^\d+$/.test(userInfo.phone.trim())) {
            newErrors.phone = 'Phone number can only contain digits';
        }
        
        // Validate address and notes
        if (!userInfo.address.trim()) newErrors.address = 'Address cannot be empty';
        
        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSave = async () => {
        // Validate form
        if (!validateForm()) {
            return;
        }
        
        setLoading(true);
        try {
            // Prepare data to update
            const reservationData = {
                test_driver: userInfo.name,
                brand: userInfo.carBrand,
                selected_car_model: userInfo.carModel,
                reservation_date: userInfo.date,
                status: userInfo.status || 'Pending',
                reservation_phone_number: userInfo.phone,
                reservation_location: userInfo.address,
                notes: userInfo.notes,
                time: userInfo.time
            };
            
            // Call API to update reservation information
            await reservationService.updateReservation(userInfo.phone, reservationData);
            
            // Show success message
            setSuccessMessage('Reservation information has been successfully updated');
            setTimeout(() => setSuccessMessage(''), 3000); // Clear message after 3 seconds
            
            // Exit edit mode
            setIsEditing(false);
        } catch (error) {
            console.error('Failed to update reservation:', error);
            setErrors({ submit: 'Failed to update reservation, please try again later' });
        } finally {
            setLoading(false);
        }
    };

    const handleCancel = () => {
        // Reset to original data
        if (location.state && location.state.userInfo) {
            const { userInfo: userData } = location.state;
            setUserInfo({
                name: userData.name || '',
                carBrand: userData.carBrand || '',
                carModel: userData.carModel || '',
                date: userData.date || '',
                status: userData.status || '',
                phone: userData.phone || '',
                address: userData.address || '',
                notes: userData.notes || ''
            });
        }
        
        // Clear errors
        setErrors({});
        
        // Exit edit mode
        setIsEditing(false);
    };

    const handleInputChange = (field, value) => {
        setUserInfo(prev => ({
            ...prev,
            [field]: value
        }));
        
        // Clear error for this field
        if (errors[field]) {
            setErrors(prev => ({
                ...prev,
                [field]: null
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
                        <button className="save-btn" onClick={handleSave} disabled={loading}>
                            {loading ? '保存中...' : 'Save'}
                        </button>
                        <button className="cancel-btn" onClick={handleCancel}>Cancel</button>
                    </div>
                )}
            </div>

            {successMessage && (
                <div className="success-message">{successMessage}</div>
            )}
            
            {errors.submit && (
                <div className="error-message">{errors.submit}</div>
            )}

            <div className="detail-content">
                <div className="detail-section">
                    <h2>Basic Information</h2>
                    <div className="info-grid">
                        <div className="info-item">
                            <label>Name</label>
                            {isEditing ? (
                                <div>
                                    <input
                                        type="text"
                                        value={userInfo.name}
                                        onChange={(e) => handleInputChange('name', e.target.value)}
                                        className={errors.name ? 'error' : ''}
                                    />
                                    {errors.name && <div className="error-text">{errors.name}</div>}
                                </div>
                            ) : (
                                <span>{userInfo.name}</span>
                            )}
                        </div>
                        <div className="info-item">
                            <label>Phone Number</label>
                            {isEditing ? (
                                <div>
                                    <input
                                        type="tel"
                                        value={userInfo.phone}
                                        onChange={(e) => handleInputChange('phone', e.target.value)}
                                        className={errors.phone ? 'error' : ''}
                                    />
                                    {errors.phone && <div className="error-text">{errors.phone}</div>}
                                </div>
                            ) : (
                                <span>{userInfo.phone}</span>
                            )}
                        </div>
                    </div>
                </div>
                <div className="detail-section">
                    <h2>Test Drive Details</h2>
                    <div className="info-grid">
                        <div className="info-item">
                            <label>Car Brand</label>
                            {isEditing ? (
                                <div>
                                    <input
                                        type="text"
                                        value={userInfo.carBrand}
                                        onChange={(e) => handleInputChange('carBrand', e.target.value)}
                                        className={errors.carBrand ? 'error' : ''}
                                    />
                                    {errors.carBrand && <div className="error-text">{errors.carBrand}</div>}
                                </div>
                            ) : (
                                <span>{userInfo.carBrand}</span>
                            )}
                        </div>
                        <div className="info-item">
                            <label>Car Model</label>
                            {isEditing ? (
                                <div>
                                    <input
                                        type="text"
                                        value={userInfo.carModel}
                                        onChange={(e) => handleInputChange('carModel', e.target.value)}
                                        className={errors.carModel ? 'error' : ''}
                                    />
                                    {errors.carModel && <div className="error-text">{errors.carModel}</div>}
                                </div>
                            ) : (
                                <span>{userInfo.carModel}</span>
                            )}
                        </div>
                        <div className="info-item">
                            <label>Appointment Date</label>
                            {isEditing ? (
                                <div>
                                    <input
                                        type="date"
                                        value={userInfo.date}
                                        onChange={(e) => handleInputChange('date', e.target.value)}
                                        className={errors.date ? 'error' : ''}
                                    />
                                    {errors.date && <div className="error-text">{errors.date}</div>}
                                </div>
                            ) : (
                                <span>{userInfo.date}</span>
                            )}
                        </div>
                        <div className="info-item">
                            <label>Appointment Time</label>
                            {isEditing ? (
                                <div>
                                    <input
                                        type="time"
                                        value={userInfo.time}
                                        onChange={(e) => handleInputChange('time', e.target.value)}
                                        className={errors.time ? 'error' : ''}
                                    />
                                    {errors.time && <div className="error-text">{errors.time}</div>}
                                </div>
                            ) : (
                                <span>{userInfo.time || ''}</span>
                            )}
                        </div>
                        <div className="info-item">
                            <label>Test Drive Location</label>
                            {isEditing ? (
                                <div>
                                    <input
                                        type="text"
                                        value={userInfo.address}
                                        onChange={(e) => handleInputChange('address', e.target.value)}
                                        className={errors.address ? 'error' : ''}
                                    />
                                    {errors.address && <div className="error-text">{errors.address}</div>}
                                </div>
                            ) : (
                                <span>{userInfo.address}</span>
                            )}
                        </div>
                        <div className="info-item">
                            <label>Status</label>
                            {isEditing ? (
                                <div>
                                    <select
                                        value={userInfo.status}
                                        onChange={(e) => handleInputChange('status', e.target.value)}
                                        className={errors.status ? 'error' : ''}
                                    >
                                        <option value="Pending">Pending</option>
                                        <option value="Confirmed">Confirmed</option>
                                        <option value="Completed">Completed</option>
                                    </select>
                                    {errors.status && <div className="error-text">{errors.status}</div>}
                                </div>
                            ) : (
                                <span className={`status-badge ${userInfo.status?.toLowerCase()}`}>
                                    {userInfo.status === 'Pending' ? 'Pending' : 
                                     userInfo.status === 'Confirmed' ? 'Confirmed' : 
                                     userInfo.status === 'Completed' ? 'Completed' : userInfo.status}
                                </span>
                            )}
                        </div>
                    </div>
                </div>
                <div className="detail-section">
                    <h2>Notes</h2>
                    <div className="notes-area">
                        {isEditing ? (
                            <div>
                                <textarea
                                    value={userInfo.notes}
                                    onChange={(e) => handleInputChange('notes', e.target.value)}
                                    rows="4"
                                    className={errors.notes ? 'error' : ''}
                                />
                                {errors.notes && <div className="error-text">{errors.notes}</div>}
                            </div>
                        ) : (
                            <p>{userInfo.notes}</p>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default UserDetail;
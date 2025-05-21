import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './DealerPortal.css';

// 将模拟数据移到组件外部
const mockUsers = [
  {
    id: 1,
    name: "John Smith",
    avatar: "https://randomuser.me/api/portraits/men/1.jpg",
    carBrand: "BMW",
    carModel: "X5 M Sport",
    date: "2024-03-15",
    status: "pending"
  },
  {
    id: 2,
    name: "Emma Wilson",
    avatar: "https://randomuser.me/api/portraits/women/2.jpg",
    carBrand: "Mercedes-Benz",
    carModel: "E300L AMG",
    date: "2024-03-16",
    status: "confirmed"
  },
  {
    id: 3,
    name: "Michael Brown",
    avatar: "https://randomuser.me/api/portraits/men/3.jpg",
    carBrand: "Audi",
    carModel: "Q7 Premium Plus",
    date: "2024-03-17",
    status: "completed"
  },
  {
    id: 4,
    name: "Sarah Davis",
    avatar: "https://randomuser.me/api/portraits/women/4.jpg",
    carBrand: "BMW",
    carModel: "740Li xDrive",
    date: "2024-03-18",
    status: "pending"
  },
  {
    id: 5,
    name: "James Wilson",
    avatar: "https://randomuser.me/api/portraits/men/5.jpg",
    carBrand: "Mercedes-Benz",
    carModel: "GLC 300 4MATIC",
    date: "2024-03-19",
    status: "confirmed"
  },
  {
    id: 6,
    name: "Linda Chen",
    avatar: "https://randomuser.me/api/portraits/women/6.jpg",
    carBrand: "Audi",
    carModel: "RS e-tron GT",
    date: "2024-03-20",
    status: "pending"
  }
];

// 将状态样式映射移到组件外部
const statusStyles = {
  pending: { color: '#FFA500', background: '#FFF3E0' },
  confirmed: { color: '#4CAF50', background: '#E8F5E9' },
  completed: { color: '#2196F3', background: '#E3F2FD' }
};

const DealerPortal = () => {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBrand, setSelectedBrand] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  const handleRowClick = (userId) => {
    navigate(`/dealer-portal/user/${userId}`);
  };

  // 过滤用户列表的函数
  const filteredUsers = mockUsers.filter(user => {
    const matchBrand = !selectedBrand || user.carBrand === selectedBrand;
    const matchDate = !selectedDate || user.date === selectedDate;
    const matchStatus = !selectedStatus || user.status === selectedStatus;
    const matchSearch = !searchTerm || 
      user.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.carBrand.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.carModel.toLowerCase().includes(searchTerm.toLowerCase());
    
    return matchBrand && matchDate && matchStatus && matchSearch;
  });

  return (
    <div className="dealer-portal">
      <div className="portal-header">
        <h1>Test drive user management system</h1>
      </div>
      
      <div className="search-filters">
        <div className="filter-group">
          <select 
            value={selectedBrand} 
            onChange={(e) => setSelectedBrand(e.target.value)}
            placeholder="Select Brand"
          >
            <option value="">Select Brand</option>
            <option value="Audi">Audi</option>
            <option value="BMW">BMW</option>
            <option value="BYD">BYD</option>
            <option value="Cadillac">Cadillac</option>
            <option value="Great Wall">Great Wall</option>
            <option value="Geely">Geely</option>
            <option value="Honda">Honda</option>
            <option value="Li Auto">Li Auto</option>
            <option value="Mercedes-Benz">Mercedes-Benz</option>
            <option value="Nissan">Nissan</option>
            <option value="NIO">NIO</option>
            <option value="Toyota">Toyota</option>
            <option value="Tesla">Tesla</option>
            <option value="Xpeng">Xpeng</option>
          </select>

          <input 
            type="date" 
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
          />

          <select 
            value={selectedStatus} 
            onChange={(e) => setSelectedStatus(e.target.value)}
          >
            <option value="">Appointment Status</option>
            <option value="pending">Pending</option>
            <option value="confirmed">Confirmed</option>
            <option value="completed">Completed</option>
          </select>
        </div>

        <div className="search-group">
          <input
            type="text"
            placeholder="Search for users..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="user-table">
        <table>
          <thead>
            <tr>
              <th><input type="checkbox" /></th>
              <th>User</th>
              <th>Car brand</th>
              <th>Car model</th>
              <th>Date</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.map(user => (
              // 在表格行中添加点击事件
              <tr key={user.id} onClick={() => handleRowClick(user.id)} style={{ cursor: 'pointer' }}>
                <td><input type="checkbox" /></td>
                <td>
                  <div className="user-info">
                    <div className="user-name">{user.name}</div>
                  </div>
                </td>
                <td>{user.carBrand}</td>
                <td>{user.carModel}</td>
                <td>{user.date}</td>
                <td>
                  <span className="status-badge" style={statusStyles[user.status]}>
                    {user.status.charAt(0).toUpperCase() + user.status.slice(1)}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="pagination">
        <span>Display per page: 10</span>
        <div className="page-numbers">
          <button>&lt;</button>
          <span>1-10 of 11</span>
          <button>&gt;</button>
        </div>
      </div>
    </div>
  );
};

export default DealerPortal;
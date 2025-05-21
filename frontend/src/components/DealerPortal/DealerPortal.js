import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './DealerPortal.css';
import { reservationService } from '../../services/api';

// 将模拟数据移到组件外部
const mockUsers = [
  {
    id: 1,
    name: "John Smith",
    carBrand: "BMW",
    carModel: "X5 M Sport",
    date: "2024-03-15",
    status: "Pending"
  },
  {
    id: 2,
    name: "Emma Wilson",
    carBrand: "Mercedes-Benz",
    carModel: "E300L AMG",
    date: "2024-03-16",
    status: "Confirmed"
  },
  {
    id: 3,
    name: "Michael Brown",
    carBrand: "Audi",
    carModel: "Q7 Premium Plus",
    date: "2024-03-17",
    status: "Completed"
  },
  {
    id: 4,
    name: "Sarah Davis",
    carBrand: "BMW",
    carModel: "740Li xDrive",
    date: "2024-03-18",
    status: "Pending"
  },
  {
    id: 5,
    name: "James Wilson",
    carBrand: "Mercedes-Benz",
    carModel: "GLC 300 4MATIC",
    date: "2024-03-19",
    status: "Confirmed"
  },
  {
    id: 6,
    name: "Linda Chen",
    carBrand: "Audi",
    carModel: "RS e-tron GT",
    date: "2024-03-20",
    status: "Pending"
  }
];

// 将状态样式映射移到组件外部
const statusStyles = {
  Pending: { color: '#FFA500', background: '#FFF3E0' },
  Confirmed: { color: '#4CAF50', background: '#E8F5E9' },
  Completed: { color: '#2196F3', background: '#E3F2FD' }
};

const DealerPortal = () => {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    // 从API获取预约数据
    const fetchReservations = async () => {
      try {
        setLoading(true);
        const test_drives = await reservationService.getAllReservations();
        
        // 将预约数据转换为组件所需的格式
        const formattedUsers = test_drives.map((test_drive, index) => ({
          id: index + 1, // 添加id字段
          name: test_drive.test_drive_info.test_driver,
          carBrand: test_drive.test_drive_info.brand,
          carModel: test_drive.test_drive_info.selected_car_model,
          date: test_drive.test_drive_info.reservation_date,
          status: test_drive.test_drive_info.status,
          phone: test_drive.test_drive_info.reservation_phone_number,
          address: test_drive.test_drive_info.reservation_location,
          time: test_drive.test_drive_info.reservation_time
        }));
        
        setUsers(formattedUsers);
        setError(null);
      } catch (error) {
        console.error('获取预约数据失败:', error);
        setError('无法加载预约数据，请稍后再试');
        // 如果API调用失败，使用模拟数据作为备用
        setUsers(mockUsers);
      } finally {
        setLoading(false);
      }
    };

    fetchReservations();
  }, []);

  const handleUserClick = (userId) => {
    navigate(`/dealer-portal/user/${userId}`);
  };
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBrand, setSelectedBrand] = useState('');
  const [selectedDate, setSelectedDate] = useState('');
  const [selectedStatus, setSelectedStatus] = useState('');

  const handleRowClick = (userId) => {
    // 找到对应的用户数据
    const selectedUser = users.find(user => user.id === userId);
    // 导航到用户详情页面并传递用户数据
    navigate(`/dealer-portal/user/${userId}`, { state: { userInfo: selectedUser } });
  };

  // 过滤用户列表的函数
  const filteredUsers = users.filter(user => {
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
            <option value="Pending">Pending</option>
            <option value="Confirmed">Confirmed</option>
            <option value="Completed">Completed</option>
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
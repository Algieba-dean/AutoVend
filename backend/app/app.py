from flask import Flask, send_from_directory, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 存储用户数据（在实际生产环境中应该使用数据库）
users = {
    'default': {
        'name': 'Jane',
        'job': 'Car Engineer',
        'phoneNumber': '123'
    }
}

@app.route('/')
def serve():
    return send_from_directory('../../frontend/src/build', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('../../frontend/src/build', path)

# 添加新用户
@app.route('/api/users', methods=['POST'])
def create_user():
    data = request.get_json()
    user_type = data.get('userType')
    
    if user_type == 'custom':
        # 验证自定义用户的必填字段
        required_fields = ['name', 'job', 'phone']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400

        # 存储自定义用户数据
        users[user_type] = {
            'name': data['name'],
            'job': data['job'],
            'phoneNumber': data['phone'],
            'additionalFields': data.get('additionalFields', [])
        }
    else:
        # 处理空用户的电话号码
        phone_number = data.get('phoneNumber')
        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400
        users[user_type] = {
            'phoneNumber': phone_number
        }

    return jsonify({'message': 'User created successfully'}), 201

# 获取用户信息
@app.route('/api/users/<user_type>', methods=['GET'])
def get_user(user_type):
    user = users.get(user_type)
    
    if not user:
        return jsonify({'error': 'User not found'}), 404

    return jsonify(user)

if __name__ == '__main__':
    app.run(debug=True)
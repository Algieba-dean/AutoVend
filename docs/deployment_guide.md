# AutoVend 部署与联调指南

## 目录

1. [环境要求](#1-环境要求)
2. [后端部署](#2-后端部署)
3. [前端部署](#3-前端部署)
4. [前后端联调](#4-前后端联调)
5. [接口对照表](#5-接口对照表)
6. [常见问题排查](#6-常见问题排查)

---

## 1. 环境要求

| 组件 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.12+ | 后端运行时 |
| Node.js | 18+ | 前端构建 |
| uv | latest | Python 包管理 |
| npm | 9+ | 前端包管理 |
| Git | 2.30+ | 版本控制 |

### 1.1 外部依赖

| 服务 | 用途 | 必须 |
|------|------|------|
| DeepSeek API | LLM 推理（OpenAI-compatible） | ✅ |
| HuggingFace (bge-m3) | 向量嵌入模型（本地下载） | ✅ |
| ChromaDB | 向量数据库（本地持久化） | ✅ |
| Edge TTS | 语音合成（免费在线服务） | ❌ 语音功能 |

---

## 2. 后端部署

### 2.1 安装依赖

```bash
cd backend
uv sync --all-extras
```

### 2.2 配置环境变量

在项目根目录 `AutoVend/` 下创建 `.env` 文件：

```env
# LLM 配置 (DeepSeek, OpenAI-compatible)
OPENAI_API_KEY=sk-your-deepseek-api-key
OPENAI_MODEL=deepseek-chat
OPENAI_URL=https://api.deepseek.com/v1

# 嵌入模型 (本地 HuggingFace)
EMBEDDING_MODEL=BAAI/bge-m3

# ChromaDB
CHROMA_PERSIST_DIR=backend/data/chroma_db
CHROMA_COLLECTION_NAME=vehicle_knowledge

# 车辆数据目录
VEHICLE_DATA_DIR=DataInUse/VehicleData

# 应用设置
APP_ENVIRONMENT=development
DEBUG=True
HOST=0.0.0.0
PORT=8000
```

### 2.3 构建车辆知识索引

首次部署或数据更新后需要构建向量索引：

```bash
cd backend
uv run python -m scripts.build_index
```

> 注意：首次运行会下载 bge-m3 嵌入模型（约 2GB），请确保网络通畅。

验证索引构建成功：
```bash
uv run python -c "
from app.rag.vehicle_index import get_vehicle_index
idx = get_vehicle_index()
print('Index loaded successfully')
"
```

### 2.4 启动后端服务

```bash
cd backend
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

验证后端启动：
```bash
# 健康检查
curl http://localhost:8000/health

# 预期响应
# {"status":"ok","components":{"agent":"ok","rag_index":"ok","voice":"ok"},...}

# API 文档
# 浏览器打开 http://localhost:8000/docs
```

---

## 3. 前端部署

### 3.1 安装依赖

```bash
cd frontend
npm install
```

### 3.2 开发模式启动

```bash
cd frontend
npm start
```

前端默认运行在 `http://localhost:3000`，通过 `package.json` 中的 `proxy` 配置自动代理 API 请求到后端 `http://localhost:8000`。

### 3.3 生产构建

```bash
cd frontend
npm run build
```

构建产物在 `frontend/build/` 目录，可通过 Nginx 等静态服务器部署。

---

## 4. 前后端联调

### 4.1 联调启动顺序

```
1. 启动后端 (port 8000)  →  2. 启动前端 (port 3000)
```

```bash
# Terminal 1: 后端
cd backend && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: 前端
cd frontend && npm start
```

### 4.2 联调验证清单

| # | 验证项 | 操作 | 预期结果 |
|---|--------|------|----------|
| 1 | 后端健康检查 | `curl http://localhost:8000/health` | `{"status":"ok",...}` |
| 2 | 前端可访问 | 浏览器打开 `http://localhost:3000` | 看到首页 Hero 页面 |
| 3 | API 代理正常 | 前端控制台无 CORS/proxy 错误 | 无网络错误 |
| 4 | 创建会话 | 选择 Default User → Start Demo | 跳转聊天页，收到欢迎消息 |
| 5 | 发送消息 | 在聊天框输入消息并发送 | 收到 AI 回复 |
| 6 | Profile 更新 | 在对话中提供姓名等信息 | 右侧面板显示 Profile 更新 |
| 7 | Needs 更新 | 在对话中描述购车需求 | 右侧面板显示需求分析 |
| 8 | 车辆推荐 | 提供足够需求后 | 右侧面板显示匹配车辆 |
| 9 | 结束会话 | 点击 Hang Up 按钮 | 会话正常结束，返回上一页 |

### 4.3 Nginx 生产部署配置

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/frontend/build;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket 代理（语音功能）
    location /api/voice/ws/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }

    # API 文档
    location /docs {
        proxy_pass http://127.0.0.1:8000;
    }
}
```

---

## 5. 接口对照表

### 5.1 前端调用 ↔ 后端路由

| 前端 (api.js) | HTTP 方法 | 后端路由 | 状态 |
|---------------|-----------|----------|------|
| `profileService.getDefaultProfile()` | GET | `/api/profile/default` | ⚠️ 不一致 |
| `profileService.getUserProfile(phone)` | GET | `/api/profile/{phone}` | ✅ |
| `profileService.createProfile(data)` | POST | `/api/profile` | ✅ |
| `profileService.updateProfile(phone, data)` | PUT | `/api/profile/{phone}` | ✅ |
| `profileService.deleteProfile(phone)` | DELETE | `/api/profile/{phone}` | ✅ |
| `profileService.getAllProfiles()` | GET | `/api/profiles` | ⚠️ 路径不匹配 |
| `chatService.startSession(phone)` | POST | `/api/chat/session` | ✅ |
| `chatService.sendMessage(sid, msg)` | POST | `/api/chat/message` | ✅ |
| `chatService.getMessages(sid)` | GET | `/api/chat/session/{sid}/messages` | ⚠️ 响应格式不一致 |
| `chatService.endSession(sid)` | PUT | `/api/chat/session/{sid}/end` | ✅ |
| `reservationService.createReservation()` | POST | `/api/test-drive` | ⚠️ 请求体不一致 |
| `needsService.*` | - | 无后端路由 | ❌ 未实现 |
| `recommendationService.*` | - | 无后端路由 | ❌ 未实现 |

### 5.2 已知接口问题

#### P1: `getDefaultProfile` 返回格式不一致

- **前端期望**: `response` 为数组 `[profileObj]`
- **后端返回**: 单个 `UserProfile` 对象
- **影响**: Default User 加载失败

#### P2: `getAllProfiles` 路径不匹配

- **前端请求**: `GET /api/profiles`
- **后端路由**: `GET /api/profile`（返回手机号列表）
- **影响**: DealerPortal 列表页加载失败

#### P3: `getMessages` 响应格式不匹配

- **前端期望**: `{ messages: [{sender_type, content, message_id}], stage, profile, needs, matched_car_models, reservation_info }`
- **后端返回**: `{ session_id, history, stage }` （纯文本 history）
- **影响**: 消息轮询无法正确解析

#### P4: `reservationService.createReservation` 请求体不一致

- **前端发送**: `{ test_drive_info: {...} }`
- **后端期望**: `TestDriveRequest` 扁平结构
- **影响**: 预约创建失败

#### P5: `needsService` / `recommendationService` 无后端实现

- 前端定义了需求和推荐的 CRUD API，但后端无对应路由
- 当前需求和推荐通过 chat/message 接口的响应体传递
- **影响**: 这些独立 API 调用会 404

---

## 6. 常见问题排查

### Q: 后端启动报 "Vehicle index not available"
索引未构建。运行 `uv run python -m scripts.build_index`。

### Q: 前端请求返回 CORS 错误
确保 `package.json` 中 `"proxy": "http://localhost:8000"` 配置正确，且后端运行在 8000 端口。

### Q: LLM 返回空响应或超时
检查 `.env` 中 `OPENAI_API_KEY` 是否有效，`OPENAI_URL` 是否可达。

### Q: 嵌入模型下载失败
检查网络连接。可设置 HuggingFace 镜像：
```bash
export HF_ENDPOINT=https://hf-mirror.com
```

### Q: 语音服务初始化失败
语音模块需要 `faster-whisper` 和 `edge-tts`。首次加载 Whisper 模型会自动下载。确保磁盘空间充足。

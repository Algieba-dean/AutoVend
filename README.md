# AutoVend

智能汽车销售助手，基于大语言模型(LLM)和检索增强生成(RAG)技术。

AutoVend 通过多阶段对话引导客户 - 从问候和画像收集，到需求分析和车辆推荐，再到试驾预约 - 全程由解耦的AI智能体驱动。

## 🏗️ 新架构 (v2.0)

```
┌─────────────────────────────────────────────────────┐
│  用户界面 (未来扩展)                                    │
│  聊天界面 · 用户画像 · 经销商门户                        │
└──────────────────────┬──────────────────────────────┘
                       │ 直接调用
┌──────────────────────┴──────────────────────────────┐
│  AutoVend Core (RAG + Agent)                        │
│  ┌────────────────────────────────────────────────┐ │
│  │  src/agent/ (纯AI逻辑，零后端依赖)               │ │
│  │  SalesAgent · StageManager · Memory             │ │
│  │  ResponseGenerator · Groq LLM                   │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │  src/rag/ (检索增强生成)                         │ │
│  │  EmbeddingManager · VectorStore · Retriever     │ │
│  │  SentenceTransformers · ChromaDB                │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │  src/models/ (数据模型)                          │ │
│  │  Chat · Vehicle · UserProfile                   │ │
│  │  Pydantic Models                               │ │
│  └────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────┐ │
│  │  src/utils/ (工具函数)                          │ │
│  │  DataLoader · Logger · Config                   │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
                       │
┌──────────────────────┴──────────────────────────────┐
│  数据存储                                            │
│  DataInUse/VehicleData/ (TOML格式)                   │
│  ChromaDB/ (向量数据库)                              │
│  .env (配置文件)                                    │
└─────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.11+
- uv (Python包管理器)
- Groq API密钥

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd AutoVend
   ```

2. **安装依赖**
   ```bash
   uv install
   ```

3. **配置环境变量**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入你的 Groq API 密钥
   ```

4. **构建向量索引**
   ```bash
   python src/main.py build
   # 或使用脚本
   python scripts/build_index.py --validate
   ```

5. **启动系统**
   ```bash
   python src/main.py
   ```

### 基本使用

```bash
# 启动交互式对话
python src/main.py

# 构建向量索引
python src/main.py build

# 查看系统状态
python src/main.py status

# 测试Agent功能
python src/main.py test

# 显示帮助
python src/main.py help
```

## 🧠 核心功能

### RAG检索系统

- **嵌入模型**: SentenceTransformers (多语言支持)
- **向量数据库**: ChromaDB (持久化存储)
- **智能检索**: 基于语义相似度和过滤条件
- **车辆推荐**: 根据用户画像个性化推荐

### Agent智能体

- **多阶段对话**: 7个精心设计的对话阶段
- **用户画像**: 实时提取和更新用户特征
- **记忆管理**: 长短期记忆结合，智能总结
- **响应生成**: 基于Groq LLM的自然对话

### 数据管理

- **车辆数据**: TOML格式，结构化存储
- **配置管理**: Pydantic + dotenv，类型安全
- **日志系统**: Rich控制台输出，结构化日志

## 📁 项目结构

```
AutoVend/
├── src/                          # 核心代码
│   ├── agent/                    # Agent系统
│   │   ├── sales_agent.py        # 主Agent
│   │   ├── stages.py             # 阶段管理
│   │   ├── memory.py             # 记忆管理
│   │   └── response_generator.py # 响应生成
│   ├── rag/                      # RAG系统
│   │   ├── embeddings.py         # 嵌入管理
│   │   ├── vector_store.py       # 向量存储
│   │   ├── retriever.py          # 检索器
│   │   └── index_builder.py      # 索引构建
│   ├── models/                   # 数据模型
│   │   ├── chat.py               # 聊天模型
│   │   └── vehicle.py            # 车辆模型
│   ├── utils/                    # 工具函数
│   │   ├── data_loader.py        # 数据加载
│   │   ├── logger.py             # 日志配置
│   │   └── config.py             # 配置管理
│   └── main.py                   # 主程序入口
├── scripts/                      # 脚本工具
│   └── build_index.py           # 索引构建
├── DataInUse/                    # 车辆数据
│   └── VehicleData/              # TOML格式车辆数据
├── pyproject.toml                # 项目配置
├── .env.example                  # 环境变量示例
├── SYSTEM_E2E.md                 # 系统设计文档
└── README.md                     # 项目说明
```

## 🔧 配置说明

### 环境变量 (.env)

```env
# Groq配置
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.1-70b-versatile

# ChromaDB配置
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=autovend_vehicles

# 嵌入模型配置
EMBEDDING_MODEL_NAME=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2

# 数据配置
VEHICLE_DATA_DIR=./DataInUse/VehicleData

# 应用配置
DEBUG=true
LOG_LEVEL=INFO
```

### 车辆数据格式

车辆数据以TOML格式存储在 `DataInUse/VehicleData/` 目录下：

```toml
id = "toyota_rav4_2024"

[spec]
brand = "丰田"
model = "RAV4"
year = 2024
vehicle_type = "SUV"
fuel_type = "汽油"
price_min = 180000
price_max = 250000
length = 4600
width = 1855
height = 1685
engine = "2.0L 自然吸气"
power = 126
seating_capacity = 5
fuel_consumption_combined = 6.8

description = "丰田RAV4是一款紧凑型SUV，以可靠性和燃油经济性著称。"

features = [
    "Toyota Safety Sense智行安全系统",
    "全景天窗",
    "自动空调",
    "无钥匙进入",
    "倒车影像"
]

[[dealer_info]]
name = "丰田4S店"
address = "北京市朝阳区"
phone = "010-12345678"
```

## 🤖 Agent对话阶段

1. **欢迎阶段** - 问候用户，介绍功能，引导提供基本信息
2. **画像分析** - 分析用户信息，提取关键特征，识别缺失信息
3. **需求分析** - 深入理解具体需求，分析优先级，识别隐性需求
4. **车辆选择** - 根据需求推荐车型，详细介绍，对比优缺点
5. **预约4S店** - 确认选择车辆，收集预约信息，提供4S店详情
6. **预约确认** - 确认所有信息，提供预约编号，说明注意事项
7. **告别阶段** - 总结对话成果，提供后续服务，友好结束

## 🧪 测试和验证

### 运行测试

```bash
# 测试Agent功能
python src/main.py test

# 验证索引质量
python scripts/build_index.py --validate --sample-size 100

# 查看系统状态
python src/main.py status
```

### 性能监控

系统提供详细的性能指标：

- 响应时间统计
- 检索准确率
- 用户画像完整度
- 对话阶段转换率

## 📊 系统架构特点

### 解耦设计

- **Agent纯逻辑**: 零后端依赖，可独立测试和部署
- **RAG模块化**: 嵌入、存储、检索完全分离
- **配置统一**: Pydantic模型确保类型安全

### 可扩展性

- **多模型支持**: 轻松切换不同的LLM和嵌入模型
- **数据格式灵活**: TOML格式易于维护和扩展
- **插件化架构**: 各模块可独立开发和优化

### 性能优化

- **向量缓存**: 嵌入向量智能缓存机制
- **批处理**: 大规模数据批量处理
- **内存管理**: 对话记忆智能压缩和总结

## 🔮 未来规划

- [ ] Web界面集成
- [ ] 多语言支持增强
- [ ] 实时协作功能
- [ ] 高级分析仪表板
- [ ] 移动端应用
- [ ] API服务化

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 📞 支持

如有问题或建议，请通过以下方式联系：

- 📧 Email: support@autovend.ai
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/autovend/issues)
- 📖 文档: [SYSTEM_E2E.md](SYSTEM_E2E.md)

---

**AutoVend** - 让汽车销售更智能，让客户体验更美好。 🚗✨
│  └────────────────────┬───────────────────────────┘ │
│                       │ protocol boundary            │
│  ┌────────────────────┴───────────────────────────┐ │
│  │  app/  (FastAPI, Storage, RAG Index)           │ │
│  │  Routes → SalesAgent · RAG retrieval           │ │
│  │  Session lifecycle · JSON file storage         │ │
│  └────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer       | Technology                                      |
|-------------|------------------------------------------------|
| Frontend    | React 18, Material-UI, Axios                   |
| Backend     | FastAPI, Pydantic v2, Uvicorn                   |
| AI Agent    | LlamaIndex, DeepSeek LLM (OpenAI-compatible)   |
| Embeddings  | bge-m3 (HuggingFace, Chinese + English)         |
| Vector Store| ChromaDB (persistent local)                     |
| CI          | GitHub Actions (Ruff lint, pytest, KPI report)  |

## Quick Start

### Prerequisites

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/) (Python project manager)
- Node.js ≥ 18 (for frontend)

### Backend

```bash
cd backend
uv sync --extra dev
cp .env.example ../.env   # Edit ../.env and set OPENAI_API_KEY
python -m scripts.build_index   # Build vehicle knowledge index
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm start
```

Opens at http://localhost:3000 (proxies API requests to backend on port 8000).

## Project Structure

```
AutoVend/
├── backend/                # FastAPI backend + AI agent
│   ├── agent/              # Standalone AI agent (zero backend deps)
│   ├── app/                # FastAPI app (routes, models, RAG, config)
│   ├── tests/              # Full test suite (unit, KPI, e2e)
│   ├── docs/               # Architecture & KPI documentation
│   ├── scripts/            # Index building scripts
│   └── pyproject.toml
├── frontend/               # React frontend
│   ├── src/components/     # Chat, UserProfile, DealerPortal, etc.
│   ├── src/services/       # API client (api.js)
│   └── package.json
├── DataInUse/              # Vehicle data (TOML files)
├── Doc/                    # Project documentation & design docs
├── .github/workflows/      # CI pipeline
└── README.md
```

## Testing

```bash
cd backend

# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=agent --cov=app --cov-report=term-missing

# Architecture isolation check
uv run pytest tests/test_agent_isolation.py -v

# KPI report
uv run python tests/kpi_report.py
```

## Conversation Stages

```
WELCOME → PROFILE_ANALYSIS → NEEDS_ANALYSIS → CAR_SELECTION
                                                    ↓ ↑
                                          RESERVATION_4S
                                                    ↓ ↑
                                    RESERVATION_CONFIRMATION → FAREWELL
```

## Documentation

- [Backend README](backend/README.md) — API endpoints, setup, architecture details
- [Architecture v2](backend/docs/v2_architecture.md) — Decoupled Agent/Backend design
- [KPI Testing Guide](backend/docs/kpi_testing_guide.md) — How to run and interpret KPI tests
- [CI Pipeline](.github/workflows/ci.yml) — Lint, test, coverage, KPI report, arch guard

## License

MIT

# AutoVend RAG 系统测试指南

## 📋 概述

本文档介绍如何运行AutoVend RAG系统的各种测试，包括性能测试、单元测试和集成测试。

## 🧪 测试类型

### 1. 性能测试 (Performance Tests)

测试系统的各项性能指标，包括响应时间、准确率、并发性能等。

#### 运行性能测试

```bash
# 运行完整性能测试套件
uv run python tests/test_performance_metrics.py

# 或者使用pytest
uv run pytest tests/test_performance_metrics.py -v
```

#### 性能测试内容

- **嵌入模型性能**: 测试BGE-M3模型的嵌入生成速度
- **检索性能**: 测试向量检索的响应时间和准确性
- **并发性能**: 测试多线程并发处理能力
- **内存使用**: 监控系统内存消耗
- **准确性指标**: 评估检索结果的准确性

#### 性能基准值

| 指标 | 基准值 | 当前值 | 状态 |
|------|--------|--------|------|
| 单次嵌入时间 | < 0.3s | 0.28s | ✅ |
| 批量嵌入时间 | < 0.01s/文本 | 0.001s/文本 | ✅ |
| 平均检索时间 | < 0.05s | 0.018s | ✅ |
| QPS | > 20 | 17.87 | ⚠️ |
| 类别准确率 | > 80% | 25% | ❌ |

### 2. 单元测试 (Unit Tests)

测试各个模块的功能正确性。

#### 运行单元测试

```bash
# 运行所有单元测试
uv run pytest tests/ -v

# 运行特定测试文件
uv run pytest tests/test_embeddings.py -v

# 运行带覆盖率的测试
uv run pytest tests/ --cov=src --cov-report=html
```

#### 单元测试覆盖范围

- 数据模型验证
- 嵌入模型功能
- 向量存储操作
- 检索器逻辑
- 配置管理
- 日志系统

### 3. 集成测试 (Integration Tests)

测试系统各组件之间的协作。

#### 运行集成测试

```bash
# 运行集成测试
uv run pytest tests/integration/ -v

# 端到端测试
uv run pytest tests/integration/test_e2e.py -v
```

#### 集成测试场景

- 完整的索引构建流程
- 端到端检索流程
- 错误处理和恢复
- 数据一致性验证

## 🚀 GitHub Actions 自动化测试

### 工作流程概述

项目配置了完整的CI/CD流程，包括：

1. **性能测试** (`performance-tests.yml`)
   - 每次push和PR触发
   - 每日定时运行
   - 手动触发选项

2. **代码质量检查**
   - 代码格式检查
   - 类型检查
   - 静态分析

3. **回归测试**
   - PR对比基准分支
   - 性能回归检测

### GitHub Actions 工作流程

#### 1. 性能测试工作流程

```yaml
# .github/workflows/performance-tests.yml
name: Performance Tests

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]
  schedule:
    - cron: '0 2 * * *'  # 每日UTC 02:00
  workflow_dispatch:
    inputs:
      test_type:
        description: 'Type of performance test to run'
        # ...
```

#### 2. 性能检查阈值

| 指标 | 警告阈值 | 错误阈值 |
|------|----------|----------|
| 检索时间 | > 0.05s | > 0.1s |
| QPS | < 20 | < 10 |
| 内存使用 | > 2.5GB | > 3GB |
| 类别准确率 | < 80% | < 70% |

#### 3. 测试报告生成

- 自动生成性能报告
- PR评论中显示测试结果
- 上传测试结果作为artifacts
- 更新性能徽标

### 本地运行GitHub Actions

```bash
# 安装act工具（本地GitHub Actions运行器）
brew install act  # macOS
# 或
curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# 运行特定工作流程
act -j performance-tests

# 查看可用工作流程
act -l
```

## 📊 性能监控

### 实时监控指标

系统提供以下实时监控指标：

1. **响应时间指标**
   - P50, P95, P99响应时间
   - 平均响应时间
   - 最大响应时间

2. **吞吐量指标**
   - QPS (每秒查询数)
   - 并发用户数
   - 请求成功率

3. **资源使用指标**
   - CPU使用率
   - 内存使用量
   - GPU使用率（如适用）

4. **准确性指标**
   - 类别识别准确率
   - 品牌识别准确率
   - 价格匹配准确率

### 监控工具配置

#### Prometheus + Grafana

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'autovend-rag'
    static_configs:
      - targets: ['localhost:8000']
```

#### 日志聚合

```yaml
# docker-compose.yml for ELK Stack
version: '3.8'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    # ...
  
  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    # ...
  
  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    # ...
```

## 🔧 测试环境配置

### 本地开发环境

```bash
# 1. 克隆项目
git clone <repository-url>
cd AutoVend

# 2. 安装依赖
uv sync --dev

# 3. 设置环境变量
cp .env.example .env
# 编辑 .env 文件

# 4. 构建索引
uv run python src/main.py build

# 5. 运行测试
uv run python tests/test_performance_metrics.py
```

### Docker测试环境

```dockerfile
# Dockerfile.test
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml ./
COPY . .

RUN pip install uv && \
    uv sync --dev && \
    uv run python src/main.py build

CMD ["uv", "run", "python", "tests/test_performance_metrics.py"]
```

```bash
# 构建测试镜像
docker build -f Dockerfile.test -t autovend-test .

# 运行测试
docker run --rm autovend-test
```

## 📈 性能优化建议

### 1. 嵌入模型优化

- **模型量化**: 使用INT8量化减少内存使用
- **模型缓存**: 缓存常用查询的嵌入向量
- **批处理优化**: 调整批次大小平衡内存和速度

```python
# 示例：启用模型量化
embedding_model = BGEEmbeddingModel(
    model_name="BAAI/bge-m3",
    device="cuda",
    quantize=True  # 启用量化
)
```

### 2. 向量存储优化

- **索引优化**: 选择合适的索引算法
- **分片策略**: 大数据集分片存储
- **缓存策略**: 热点数据缓存

```python
# 示例：配置索引参数
vector_store = ChromaVectorStore(
    index_type="HNSW",  # 高性能索引
    M=16,              # HNSW参数
    ef_construction=200
)
```

### 3. 并发处理优化

- **连接池**: 数据库连接池管理
- **异步处理**: 使用asyncio提高并发
- **负载均衡**: 多实例部署

```python
# 示例：异步检索器
class AsyncVehicleRetriever:
    async def search(self, query: Query) -> SearchResponse:
        # 异步检索实现
        pass
```

## 🐛 故障排除

### 常见问题

#### 1. 模型加载失败

**问题**: `CUDA out of memory`
**解决**: 
```python
# 减少批次大小或使用CPU
embedding_model = BGEEmbeddingModel(device="cpu")
```

#### 2. 检索速度慢

**问题**: 检索响应时间过长
**解决**:
```python
# 增加相似度阈值
retriever = VehicleRetriever(similarity_threshold=0.5)
```

#### 3. 准确率低

**问题**: 检索结果不准确
**解决**:
```python
# 调整匹配权重
retriever = VehicleRetriever(
    semantic_weight=0.6,
    category_weight=0.3,
    price_weight=0.1
)
```

### 调试工具

#### 1. 性能分析

```bash
# 使用cProfile分析性能
uv run python -m cProfile -o profile.stats tests/test_performance_metrics.py

# 查看分析结果
uv run python -c "
import pstats
p = pstats.Stats('profile.stats')
p.sort_stats('cumulative').print_stats(20)
"
```

#### 2. 内存分析

```bash
# 使用memory_profiler
pip install memory_profiler
uv run python -m memory_profiler tests/test_performance_metrics.py
```

#### 3. 网络分析

```bash
# 使用strace跟踪系统调用
strace -c -p <pid>

# 使用lsof查看文件描述符
lsof -p <pid>
```

## 📋 测试清单

### 发布前检查清单

- [ ] 运行完整性能测试套件
- [ ] 验证所有性能指标在基准范围内
- [ ] 检查代码覆盖率 > 80%
- [ ] 运行安全扫描
- [ ] 验证文档更新
- [ ] 检查依赖版本兼容性
- [ ] 运行集成测试
- [ ] 验证生产环境配置

### 日常维护清单

- [ ] 检查GitHub Actions运行状态
- [ ] 监控性能指标趋势
- [ ] 更新性能基准值
- [ ] 审查测试覆盖率报告
- [ ] 检查依赖更新
- [ ] 清理测试数据

## 📚 相关文档

- [性能指标文档](./PERFORMANCE_METRICS.md)
- [API文档](./API_REFERENCE.md)
- [部署指南](./DEPLOYMENT_GUIDE.md)
- [开发指南](./DEVELOPMENT_GUIDE.md)

## 🤝 贡献指南

### 添加新测试

1. 在`tests/`目录下创建测试文件
2. 遵循现有测试命名约定
3. 添加适当的测试文档
4. 更新性能基准值（如适用）

### 报告问题

如果发现测试问题或性能回归：

1. 检查现有issues
2. 创建新issue并标记`bug`或`performance`
3. 提供详细的复现步骤
4. 包含相关的日志和指标

### 性能优化贡献

1. 分析性能瓶颈
2. 实现优化方案
3. 添加性能测试验证
4. 更新文档和基准值

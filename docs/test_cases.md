# AutoVend 端到端测试用例

## 目录

1. [后端单元测试](#1-后端单元测试)
2. [API 接口测试](#2-api-接口测试)
3. [前后端联调测试](#3-前后端联调测试)
4. [RAG 检索测试](#4-rag-检索测试)
5. [Agent 对话流程测试](#5-agent-对话流程测试)
6. [语音模块测试](#6-语音模块测试)
7. [性能测试](#7-性能测试)
8. [自动化测试命令](#8-自动化测试命令)

---

## 1. 后端单元测试

### 运行方式

```bash
cd backend
uv run pytest tests/ --ignore=tests/performance -v
```

### 现有测试覆盖

| 测试文件 | 测试数 | 覆盖模块 |
|----------|--------|----------|
| `tests/test_workflow.py` | 约 25 | 阶段转换、记忆管理、响应生成 |
| `tests/test_agent_isolation.py` | 3 | 架构隔离（agent 无 app 依赖） |
| `tests/test_voice.py` | 43 | 语音 ASR/TTS/Pipeline/Routes |

---

## 2. API 接口测试

### 2.1 健康检查

| 编号 | 用例 | 请求 | 预期响应 |
|------|------|------|----------|
| HC-01 | 服务正常启动 | `GET /health` | `{"status":"ok", "components":{"agent":"ok","rag_index":"ok","voice":"ok"}}` |
| HC-02 | 无索引启动 | `GET /health` (未构建索引) | `{"status":"degraded", "components":{"agent":"ok","rag_index":"unavailable",...}}` |

```bash
# HC-01
curl -s http://localhost:8000/health | python -m json.tool
```

### 2.2 用户 Profile

| 编号 | 用例 | 请求 | 预期 |
|------|------|------|------|
| PF-01 | 获取默认 Profile | `GET /api/profile/default` | 200, 空 UserProfile 对象 |
| PF-02 | 创建 Profile | `POST /api/profile` `{"phone_number":"13800001111","name":"张三"}` | 201, 返回创建的 Profile |
| PF-03 | 获取 Profile | `GET /api/profile/13800001111` | 200, 返回 Profile |
| PF-04 | 更新 Profile | `PUT /api/profile/13800001111` `{"name":"李四"}` | 200, name 更新 |
| PF-05 | 删除 Profile | `DELETE /api/profile/13800001111` | 200, 删除成功 |
| PF-06 | 获取不存在的 Profile | `GET /api/profile/99999999999` | 404 |
| PF-07 | 重复创建 Profile | `POST /api/profile` (同手机号) | 409, "Profile already exists" |
| PF-08 | 创建无手机号 Profile | `POST /api/profile` `{"name":"test"}` | 400, "Phone number required" |

```bash
# PF-02
curl -X POST http://localhost:8000/api/profile \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"13800001111","name":"张三"}'

# PF-03
curl -s http://localhost:8000/api/profile/13800001111

# PF-05
curl -X DELETE http://localhost:8000/api/profile/13800001111
```

### 2.3 聊天会话

| 编号 | 用例 | 请求 | 预期 |
|------|------|------|------|
| CH-01 | 创建会话 | `POST /api/chat/session` `{"phone_number":"13800001111"}` | 200, `{session_id, message, stage, profile}` |
| CH-02 | 发送消息 | `POST /api/chat/message` `{"session_id":"xxx","message":"你好"}` | 200, `{message, response, stage, profile, needs, matched_car_models}` |
| CH-03 | 获取消息历史 | `GET /api/chat/session/{sid}/messages` | 200, 历史记录 |
| CH-04 | 结束会话 | `PUT /api/chat/session/{sid}/end` | 200, "Session ended" |
| CH-05 | 结束不存在的会话 | `PUT /api/chat/session/fake/end` | 404 |
| CH-06 | 无 session_id 发消息 | `POST /api/chat/message` `{"session_id":"new-id","message":"hi"}` | 200, 自动创建会话 |

```bash
# CH-01
SESSION=$(curl -s -X POST http://localhost:8000/api/chat/session \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"13800001111"}' | python -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "Session ID: $SESSION"

# CH-02
curl -s -X POST http://localhost:8000/api/chat/message \
  -H "Content-Type: application/json" \
  -d "{\"session_id\":\"$SESSION\",\"message\":\"你好，我想买车\"}" | python -m json.tool

# CH-04
curl -s -X PUT "http://localhost:8000/api/chat/session/$SESSION/end"
```

### 2.4 试驾预约

| 编号 | 用例 | 请求 | 预期 |
|------|------|------|------|
| TD-01 | 创建预约 | `POST /api/test-drive` `{"phone_number":"138...","test_driver":"张三",...}` | 201 |
| TD-02 | 获取预约 | `GET /api/test-drive/13800001111` | 200 |
| TD-03 | 更新预约 | `PUT /api/test-drive/13800001111` | 200 |
| TD-04 | 删除预约 | `DELETE /api/test-drive/13800001111` | 200 |
| TD-05 | 获取不存在的预约 | `GET /api/test-drive/99999` | 404 |

### 2.5 语音接口

| 编号 | 用例 | 请求 | 预期 |
|------|------|------|------|
| VO-01 | 创建语音会话 | `POST /api/voice/session?phone_number=138...` | 200, `{session_id}` |
| VO-02 | 转录音频 | `POST /api/voice/transcribe` (multipart file) | 200, `{text, language}` |
| VO-03 | 文本合成语音 | `POST /api/voice/synthesize?text=你好` | 200, MP3 audio |
| VO-04 | 结束语音会话 | `DELETE /api/voice/session/{sid}` | 200 |

---

## 3. 前后端联调测试

### 3.1 用户选择流程

| 编号 | 场景 | 步骤 | 预期结果 |
|------|------|------|----------|
| E2E-01 | Default 用户完整流程 | 首页→Select User→Default User→Start Demo→对话→Hang Up | 全流程无报错 |
| E2E-02 | Empty 用户完整流程 | 首页→Select User→Empty User→输入手机号→Start Demo→对话 | 创建空 Profile，进入对话 |
| E2E-03 | Custom 用户完整流程 | 首页→Select User→Custom→填写信息→Start Demo→对话 | 创建自定义 Profile |
| E2E-04 | 重复手机号 Custom | 用已存在手机号创建 Custom | 自动加载已有 Profile |

### 3.2 对话阶段流转

| 编号 | 场景 | 用户输入示例 | 预期阶段变化 |
|------|------|-------------|-------------|
| STG-01 | Welcome → Profile | (系统自动) | welcome → profile_analysis |
| STG-02 | Profile → Needs | "我叫张三，买车自己开" | profile_analysis → needs_analysis |
| STG-03 | Needs → CarSelection | "预算20万，想要SUV，纯电" | needs_analysis → car_selection_confirmation |
| STG-04 | CarSelection → Reservation | (推荐车辆后) | car_selection → reservation4s |
| STG-05 | Reservation → Confirmation | "周六下午2点，浦东4S店" | reservation4s → reservation_confirmation |
| STG-06 | Confirmation → Farewell | (确认预约信息) | reservation_confirmation → farewell |

### 3.3 右侧面板数据更新

| 编号 | 场景 | 验证点 |
|------|------|--------|
| PNL-01 | Profile 面板 | 输入姓名后，右侧 Profile 显示 name |
| PNL-02 | Needs 面板 | 描述需求后，右侧显示显式/隐式需求 |
| PNL-03 | Matched Cars 面板 | 进入车辆推荐阶段后，右侧显示匹配车型 |
| PNL-04 | Reservation 面板 | 进入预约阶段后，右侧切换为预约表单 |

### 3.4 异常场景

| 编号 | 场景 | 预期 |
|------|------|------|
| ERR-01 | 后端未启动时前端操作 | 显示错误提示，不白屏 |
| ERR-02 | 网络超时 | 显示友好错误消息 |
| ERR-03 | 快速连续发送消息 | 消息按序显示，无重复 |
| ERR-04 | 刷新页面 | 会话丢失，回到首页或显示提示 |
| ERR-05 | 返回按钮 | 确认弹窗→结束会话→返回上一页 |

---

## 4. RAG 检索测试

| 编号 | 查询 | 预期结果 |
|------|------|----------|
| RAG-01 | "20万以内的纯电SUV" | 返回价格≤20万的电动SUV车型 |
| RAG-02 | "特斯拉" | 返回包含 Tesla 品牌的车型 |
| RAG-03 | "家用7座" | 返回7座车型，family_friendliness=High |
| RAG-04 | "运动轿车" | 返回设计风格为运动型的轿车 |
| RAG-05 | 空查询（无需求） | 返回通用推荐 "recommend a good vehicle" |
| RAG-06 | 带 metadata filter | brand=BYD → 仅返回比亚迪车型 |

```bash
# 直接测试 RAG 检索
cd backend
uv run python -c "
from app.rag.vehicle_index import get_vehicle_index
from app.rag.query_engine import retrieve_vehicles, format_retrieval_results

index = get_vehicle_index()
results = retrieve_vehicles(index, '20万以内纯电SUV', top_k=5)
formatted = format_retrieval_results(results)
for car in formatted:
    print(f\"{car['car_model']} (score={car['score']})\")
"
```

---

## 5. Agent 对话流程测试

### 5.1 信息提取准确性

| 编号 | 用户输入 | 预期提取 |
|------|----------|----------|
| EXT-01 | "我叫张三" | profile.name = "张三" |
| EXT-02 | "给我老婆买的" | profile.target_driver = "老婆"/"Wife" |
| EXT-03 | "预算15-20万" | needs.explicit.prize = "15-20万" |
| EXT-04 | "想要特斯拉" | needs.explicit.brand = "Tesla"/"特斯拉" |
| EXT-05 | "纯电动" | needs.explicit.powertrain_type 包含 "electric" |
| EXT-06 | "周六下午两点" | reservation.reservation_date, reservation_time 填充 |
| EXT-07 | "一家五口" | profile.family_size = "5" |
| EXT-08 | 中英文混合 "我要买 SUV" | needs.explicit.vehicle_category_bottom 包含 "SUV" |

### 5.2 阶段转换正确性

```bash
cd backend
uv run pytest tests/test_workflow.py -v -k "test_valid_transitions or test_advance"
```

### 5.3 响应质量

| 编号 | 场景 | 验证点 |
|------|------|--------|
| RSP-01 | 欢迎阶段 | 回复自然、友好，引导用户提供信息 |
| RSP-02 | 信息不足时 | 不重复追问，有针对性地补充 |
| RSP-03 | 车辆推荐 | 推荐理由与用户需求匹配，对比差异 |
| RSP-04 | 语言一致 | 用户用中文则回复中文，用英文则回复英文 |
| RSP-05 | 错误兜底 | LLM 异常时返回友好的默认消息 |

---

## 6. 语音模块测试

```bash
cd backend
uv run pytest tests/test_voice.py -v
```

| 测试类 | 测试数 | 说明 |
|--------|--------|------|
| TestWhisperASR | 8 | 模型初始化、懒加载、转录 |
| TestEdgeTTSService | 10 | 合成、语言检测、语音选择 |
| TestVoicePipeline | 7 | 端到端管道、指标 |
| TestVoiceRoutes | 3 | 会话创建/销毁 |
| TestVoiceIntegration | 6 | 完整对话轮次 |

---

## 7. 性能测试

### 7.1 响应延迟基准

| 指标 | 目标 | 测量方式 |
|------|------|----------|
| 首次响应时间 (TTFR) | < 3s | 从发送消息到收到回复 |
| RAG 检索延迟 | < 500ms | `retrieve_vehicles()` 执行时间 |
| LLM 提取延迟 | < 2s | 单次 `extract_with_llm()` 调用 |
| LLM 生成延迟 | < 2s | 单次 `generate_response()` 调用 |
| 语音端到端 | < 3s | ASR + Agent + TTS 总延迟 |

### 7.2 延迟测量脚本

```bash
cd backend
uv run python -c "
import time
from app.rag.vehicle_index import get_vehicle_index
from app.rag.query_engine import retrieve_vehicles

index = get_vehicle_index()

start = time.time()
results = retrieve_vehicles(index, 'SUV 纯电 20万', top_k=5)
elapsed = (time.time() - start) * 1000
print(f'RAG retrieval: {elapsed:.0f}ms, {len(results)} results')
"
```

### 7.3 并发测试

```bash
# 使用 wrk 或 ab 进行并发测试
ab -n 100 -c 10 http://localhost:8000/health
```

---

## 8. 自动化测试命令

```bash
# 全量测试
cd backend && uv run pytest tests/ --ignore=tests/performance -v

# 仅工作流测试
uv run pytest tests/test_workflow.py -v

# 仅语音测试
uv run pytest tests/test_voice.py -v

# 架构隔离测试
uv run pytest tests/test_agent_isolation.py -v

# Lint 检查
uv run ruff check .
uv run ruff format --check .

# 覆盖率报告
uv run pytest tests/ --ignore=tests/performance --cov=agent --cov=app --cov-report=term-missing
```

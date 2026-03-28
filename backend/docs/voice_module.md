# AutoVend 语音模块文档

## 概述

语音模块为 AutoVend 智能销售助手提供实时语音交互能力，集成了开源 ASR（语音识别）和 TTS（语音合成）服务，与现有 SalesAgent 对话管道无缝对接。

## 架构

```
用户语音 → [ASR: faster-whisper] → 文本 → [SalesAgent] → 回复文本 → [TTS: edge-tts] → 语音回复
```

### 核心组件

| 组件 | 文件 | 说明 |
|------|------|------|
| **ASR** | `agent/voice/asr.py` | 基于 faster-whisper (CTranslate2) 的语音识别 |
| **TTS** | `agent/voice/tts.py` | 基于 edge-tts 的神经语音合成（免费，无需 API Key） |
| **Pipeline** | `agent/voice/pipeline.py` | ASR → Agent → TTS 端到端管道 |
| **Routes** | `app/routes/voice.py` | REST + WebSocket API 端点 |

## 技术选型

### ASR: faster-whisper

- **模型**: OpenAI Whisper (base 模型，可配置)
- **后端**: CTranslate2（比原版快 4x，内存占用减半）
- **特性**: 多语言自动检测、VAD 语音活动检测、词级时间戳
- **量化**: INT8（CPU 友好，适合实时场景）

### TTS: edge-tts

- **服务**: 微软 Edge 在线 TTS 服务
- **优势**: 免费、无需 API Key、高质量神经语音
- **语音**: 中文 `zh-CN-XiaoxiaoNeural`，英文 `en-US-AriaNeural`
- **格式**: MP3 输出

## API 端点

### REST 端点

#### `POST /api/voice/transcribe`
上传音频文件，返回转录结果。

```bash
curl -X POST http://localhost:8000/api/voice/transcribe \
  -F "file=@audio.wav"
```

响应:
```json
{
  "text": "你好，我想买车",
  "language": "zh",
  "language_probability": 0.97,
  "duration_seconds": 2.5,
  "processing_time_ms": 350.0,
  "segments": [{"text": "你好，我想买车", "start": 0.0, "end": 2.5, "confidence": 0.95}]
}
```

#### `POST /api/voice/synthesize?text=你好`
文本合成语音，返回 MP3 音频。

```bash
curl -X POST "http://localhost:8000/api/voice/synthesize?text=欢迎来到AutoVend" \
  --output response.mp3
```

#### `POST /api/voice/session`
创建语音会话。

```bash
curl -X POST "http://localhost:8000/api/voice/session?phone_number=13800138000"
```

#### `POST /api/voice/process?session_id=xxx`
单轮语音处理: 上传音频 → ASR → Agent → TTS → 返回结果。

#### `GET /api/voice/session/{session_id}/metrics`
获取语音会话累计指标。

#### `DELETE /api/voice/session/{session_id}`
结束语音会话。

### WebSocket 端点

#### `WS /api/voice/ws/{session_id}`

实时语音交互协议：

| 方向 | 类型 | 说明 |
|------|------|------|
| Client → Server | binary | 音频数据块（WAV/PCM 16kHz 16-bit mono） |
| Client → Server | JSON `{"type": "end_turn"}` | 通知结束本轮说话 |
| Client → Server | JSON `{"type": "ping"}` | 心跳检测 |
| Client → Server | JSON `{"type": "end_session"}` | 结束会话 |
| Server → Client | JSON `{"type": "transcription", ...}` | ASR 转录结果 |
| Server → Client | JSON `{"type": "response", ...}` | Agent 回复文本 |
| Server → Client | JSON `{"type": "tts_start", ...}` | TTS 音频即将发送 |
| Server → Client | binary | TTS 音频数据（MP3） |

## 使用示例

### Python 调用示例

```python
from agent.voice.asr import WhisperASR
from agent.voice.tts import EdgeTTSService
from agent.voice.pipeline import VoicePipeline
from agent.sales_agent import SalesAgent
from agent.schemas import SessionState

# 初始化
asr = WhisperASR(model_size="base")
tts = EdgeTTSService()
agent = SalesAgent(llm=your_llm)
pipeline = VoicePipeline(agent=agent, asr=asr, tts=tts)

# 单轮语音处理
state = SessionState(session_id="demo")
result = pipeline.process_audio_file("user_audio.wav", state)

print(f"用户说: {result.user_text}")
print(f"Agent回复: {result.agent_response}")
print(f"音频大小: {len(result.audio_bytes)} bytes")
print(f"总延迟: {result.total_time_ms:.0f}ms")

# 查看指标
metrics = pipeline.get_session_metrics("demo")
print(f"平均延迟: {metrics.avg_turn_latency_ms:.0f}ms")
```

## 测试

### 运行语音模块测试

```bash
# 仅语音测试 (43 tests)
.venv/bin/python -m pytest tests/test_voice.py -v

# 全量测试 (344 tests)
.venv/bin/python -m pytest tests/ --ignore=tests/performance -v
```

### 测试覆盖

| 测试类 | 测试数 | 覆盖范围 |
|--------|--------|----------|
| `TestWhisperASR` | 8 | 初始化、懒加载、文件/字节/numpy 转录 |
| `TestEdgeTTSService` | 10 | 初始化、语言检测、异步合成、文件输出 |
| `TestDataclasses` | 4 | 数据结构序列化 |
| `TestVoiceSessionMetrics` | 5 | 指标累计、多轮统计 |
| `TestVoicePipeline` | 7 | 端到端管道、跳过 TTS、检索车辆注入 |
| `TestVoiceRoutes` | 3 | 会话创建/销毁/查找 |
| `TestVoiceIntegration` | 6 | 完整对话轮次、多轮会话、双语支持 |

## 性能指标

| 指标 | 目标 | 说明 |
|------|------|------|
| ASR 延迟 | < 500ms | base 模型，INT8 量化 |
| TTS 延迟 | < 1000ms | edge-tts 网络请求 |
| 端到端延迟 | < 3000ms | ASR + Agent + TTS |
| ASR 准确率 | > 90% | 中文/英文混合场景 |
| 支持语言 | zh/en | 自动检测 |

## 配置

### Whisper 模型选择

| 模型 | 大小 | 速度 | 准确率 | 适用场景 |
|------|------|------|--------|----------|
| `tiny` | 39M | 最快 | 一般 | 快速原型 |
| `base` | 74M | 快 | 良好 | **推荐（默认）** |
| `small` | 244M | 中等 | 较好 | 高准确率 |
| `medium` | 769M | 慢 | 很好 | 专业场景 |
| `large-v3` | 1.5G | 最慢 | 最佳 | 离线批处理 |

### TTS 语音列表

```python
import asyncio
from agent.voice.tts import EdgeTTSService

# 查看所有中文语音
voices = asyncio.run(EdgeTTSService.list_voices("zh"))
for v in voices:
    print(f"{v['ShortName']}: {v['Gender']}")
```

## 依赖

```
faster-whisper>=1.0.0   # ASR (CTranslate2 Whisper)
edge-tts>=6.1.0         # TTS (Microsoft Edge)
soundfile>=0.12.0       # 音频读写
numpy>=1.24.0           # 音频数组处理
```

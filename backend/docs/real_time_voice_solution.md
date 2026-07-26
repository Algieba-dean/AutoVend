# AutoVend 实时语音通话技术方案

## 概述

本文档提出了一套完整的实时语音通话解决方案，支持高并发、低延迟的语音交互，集成ASR（语音识别）、TTS（语音合成）和流式处理，为AutoVend智能销售助手提供真正的实时对话体验。

## 技术架构

### 整体架构图

```
┌─────────────────┐    WebSocket    ┌─────────────────┐
│   前端客户端      │ ◄──────────────► │   FastAPI后端    │
│                 │                 │                 │
│ • WebRTC音频    │                 │ • WebSocket处理  │
│ • 音频流管理    │                 │ • 会话管理       │
│ • 实时UI更新    │                 │ • 音频路由       │
└─────────────────┘                 └─────────────────┘
                                            │
                                            ▼
┌─────────────────┐    HTTP/gRPC     ┌─────────────────┐
│   ASR服务       │ ◄──────────────► │   AI处理服务     │
│                 │                 │                 │
│ • Whisper实时   │                 │ • LlamaIndex RAG │
│ • 流式识别      │                 │ • 对话管理       │
│ • 语言检测      │                 │ • 上下文维护     │
└─────────────────┘                 └─────────────────┘
                                            │
                                            ▼
┌─────────────────┐    HTTP/gRPC     ┌─────────────────┐
│   TTS服务       │ ◄──────────────► │   缓存服务       │
│                 │                 │                 │
│ • Azure Speech  │                 │ • Redis缓存      │
│ • 神经语音合成  │                 │ • 会话状态       │
│ • 流式合成      │                 │ • 音频缓存       │
└─────────────────┘                 └─────────────────┘
```

## 核心技术组件

### 1. 实时音频通信层

#### 1.1 WebRTC音频流
```python
# 前端WebRTC配置
class WebRTCAudioManager:
    def __init__(self):
        self.peer_connection = None
        self.audio_stream = None
        self.ws_connection = None
    
    async def initialize_connection(self):
        """初始化WebRTC连接"""
        configuration = RTCConfiguration({
            "iceServers": [{"urls": "stun:stun.l.google.com:19302"}]
        })
        self.peer_connection = RTCPeerConnection(configuration)
        
        # 添加音频轨道
        self.audio_stream = await self.get_user_media()
        audio_track = self.audio_stream.getAudioTracks()[0]
        self.peer_connection.addTrack(audio_track)
        
        # 设置数据通道用于信令
        data_channel = self.peer_connection.createDataChannel("control")
        
    async def start_audio_stream(self):
        """开始音频流传输"""
        # 16kHz, 16bit, mono格式
        target_sample_rate = 16000
        audio_context = AudioContext()
        
        # 实时音频处理
        processor = audio_context.createScriptProcessor(4096, 1, 1)
        processor.onaudioprocess = self.process_audio_chunk
        audio_stream.connect(processor)
        processor.connect(audio_context.destination)
```

#### 1.2 FastAPI WebSocket处理
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
import asyncio
import json

app = FastAPI()

class VoiceConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.session_states: Dict[str, SessionState] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """建立WebSocket连接"""
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.session_states[session_id] = SessionState(
            session_id=session_id,
            stage="welcome",
            audio_buffer=AudioBuffer()
        )
    
    async def disconnect(self, session_id: str):
        """断开连接"""
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.session_states:
            del self.session_states[session_id]
    
    async def send_audio(self, session_id: str, audio_data: bytes):
        """发送音频数据"""
        if session_id in self.active_connections:
            websocket = self.active_connections[session_id]
            await websocket.send_bytes(audio_data)

manager = VoiceConnectionManager()

@app.websocket("/ws/voice/{session_id}")
async def voice_websocket(websocket: WebSocket, session_id: str):
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # 接收音频数据
            data = await websocket.receive_bytes()
            
            # 异步处理音频
            asyncio.create_task(process_audio_stream(session_id, data))
            
    except WebSocketDisconnect:
        await manager.disconnect(session_id)

async def process_audio_stream(session_id: str, audio_data: bytes):
    """处理音频流"""
    session_state = manager.session_states[session_id]
    
    # 1. 音频预处理
    processed_audio = preprocess_audio(audio_data)
    
    # 2. ASR识别
    transcription = await asr_service.transcribe_stream(
        processed_audio, 
        session_id
    )
    
    # 3. AI处理
    if transcription.text:
        response = await ai_agent.process_voice_input(
            session_id, 
            transcription.text
        )
        
        # 4. TTS合成
        audio_response = await tts_service.synthesize_stream(
            response.text,
            session_id
        )
        
        # 5. 发送回客户端
        await manager.send_audio(session_id, audio_response)
```

### 2. 实时ASR服务

#### 2.1 Whisper流式识别
```python
import whisper
import numpy as np
from collections import deque
import threading

class StreamingWhisperASR:
    def __init__(self, model_name="turbo"):
        self.model = whisper.load_model(model_name)
        self.audio_buffer = deque(maxlen=30 * 16000)  # 30秒缓冲
        self.is_processing = False
        self.last_transcription = ""
        
    async def transcribe_stream(self, audio_chunk: bytes, session_id: str):
        """流式语音识别"""
        # 转换音频格式
        audio_array = np.frombuffer(audio_chunk, dtype=np.float32)
        
        # 添加到缓冲区
        self.audio_buffer.extend(audio_array)
        
        # 检查是否有足够的音频进行处理
        if len(self.audio_buffer) >= 16000 * 2 and not self.is_processing:  # 2秒
            self.is_processing = True
            
            # 异步处理
            threading.Thread(
                target=self._process_audio_chunk,
                args=(session_id,)
            ).start()
    
    def _process_audio_chunk(self, session_id: str):
        """处理音频块"""
        try:
            # 获取音频数据
            audio_data = np.array(list(self.audio_buffer))
            
            # Whisper识别
            result = self.model.transcribe(
                audio_data,
                language=None,  # 自动检测
                task="transcribe",
                word_timestamps=True,
                initial_prompt=self.last_transcription
            )
            
            # 更新最后转录结果
            if result["text"].strip():
                self.last_transcription = result["text"]
                
                # 发送转录结果
                asyncio.create_task(
                    self._send_transcription_result(session_id, result)
                )
                
        except Exception as e:
            print(f"ASR处理错误: {e}")
        finally:
            self.is_processing = False
    
    async def _send_transcription_result(self, session_id: str, result: dict):
        """发送转录结果"""
        transcription_event = {
            "type": "transcription",
            "text": result["text"],
            "language": result["language"],
            "words": result.get("words", []),
            "confidence": self._calculate_confidence(result)
        }
        
        # 通过WebSocket发送
        await voice_manager.send_event(session_id, transcription_event)

# ASR服务实例
asr_service = StreamingWhisperASR()
```

#### 2.2 音频预处理
```python
import librosa
import numpy as np

class AudioPreprocessor:
    def __init__(self, target_sr=16000):
        self.target_sr = target_sr
    
    def preprocess_audio(self, audio_data: bytes) -> np.ndarray:
        """音频预处理"""
        # 转换为numpy数组
        audio = np.frombuffer(audio_data, dtype=np.float32)
        
        # 重采样到16kHz
        if len(audio.shape) > 1:
            audio = np.mean(audio, axis=1)
        
        audio = librosa.resample(
            audio, 
            orig_sr=44100,  # 假设原始采样率
            target_sr=self.target_sr
        )
        
        # 降噪处理
        audio = self._noise_reduction(audio)
        
        # 音量标准化
        audio = self._normalize_volume(audio)
        
        return audio
    
    def _noise_reduction(self, audio: np.ndarray) -> np.ndarray:
        """简单降噪"""
        # 使用谱减法降噪
        stft = librosa.stft(audio)
        magnitude = np.abs(stft)
        phase = np.angle(stft)
        
        # 估计噪声谱（使用前0.5秒）
        noise_frames = int(0.5 * self.target_sr / 512)
        noise_spectrum = np.mean(magnitude[:, :noise_frames], axis=1, keepdims=True)
        
        # 谱减法
        enhanced_magnitude = magnitude - 0.3 * noise_spectrum
        enhanced_magnitude = np.maximum(enhanced_magnitude, 0.1 * magnitude)
        
        # 重构音频
        enhanced_stft = enhanced_magnitude * np.exp(1j * phase)
        enhanced_audio = librosa.istft(enhanced_stft)
        
        return enhanced_audio
    
    def _normalize_volume(self, audio: np.ndarray) -> np.ndarray:
        """音量标准化"""
        # 计算RMS
        rms = np.sqrt(np.mean(audio ** 2))
        
        # 标准化到目标RMS
        target_rms = 0.1
        if rms > 0:
            audio = audio * (target_rms / rms)
        
        # 限幅
        audio = np.clip(audio, -1.0, 1.0)
        
        return audio

audio_preprocessor = AudioPreprocessor()
```

### 3. 实时TTS服务

#### 3.1 Azure Speech神经TTS
```python
import azure.cognitiveservices.speech as speechsdk
import asyncio
from io import BytesIO

class StreamingAzureTTS:
    def __init__(self):
        self.speech_config = None
        self.synthesizers = {}  # 每个会话一个合成器
        self._initialize_config()
    
    def _initialize_config(self):
        """初始化Azure Speech配置"""
        # 使用WebSocket v2端点降低延迟
        tts_endpoint = f"wss://{os.getenv('AZURE_TTS_REGION')}.tts.speech.microsoft.com/cognitiveservices/websocket/v2"
        self.speech_config = speechsdk.SpeechConfig(
            endpoint=tts_endpoint,
            subscription=os.getenv("AZURE_TTS_API_KEY")
        )
        
        # 设置语音参数
        self.speech_config.speech_synthesis_voice_name = "zh-CN-XiaoxiaoNeural"
        self.speech_config.speech_synthesis_output_format = speechsdk.SpeechSynthesisOutputFormat.Audio24Khz96KBitRateMonoMp3
        self.speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_SynthEnableAudio3D, "true")
    
    async def synthesize_stream(self, text: str, session_id: str) -> bytes:
        """流式语音合成"""
        if session_id not in self.synthesizers:
            self.synthesizers[session_id] = self._create_synthesizer(session_id)
        
        synthesizer = self.synthesizers[session_id]
        
        # 创建音频流
        audio_stream = BytesIO()
        
        # 设置合成事件
        def synthesis_started(evt):
            print(f"合成开始: {session_id}")
        
        def synthesizing(evt):
            """实时接收音频块"""
            if evt.result.audio:
                audio_stream.write(evt.result.audio)
                # 立即发送音频块
                asyncio.create_task(
                    self._send_audio_chunk(session_id, evt.result.audio)
                )
        
        def synthesis_completed(evt):
            print(f"合成完成: {session_id}")
        
        # 注册事件
        synthesizer.synthesis_started.connect(synthesis_started)
        synthesizer.synthesizing.connect(synthesizing)
        synthesizer.synthesis_completed.connect(synthesis_completed)
        
        # 开始合成
        result = synthesizer.start_speaking_text_async(text).get()
        
        if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
            return audio_stream.getvalue()
        else:
            raise Exception(f"TTS合成失败: {result.reason}")
    
    def _create_synthesizer(self, session_id: str):
        """为会话创建合成器"""
        # 使用流式音频配置
        stream_config = speechsdk.audio.AudioOutputFormat(
            speechsdk.SpeechSynthesisOutputFormat.Audio24Khz96KBitRateMonoMp3
        )
        
        synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=None  # 使用流式输出
        )
        
        return synthesizer
    
    async def _send_audio_chunk(self, session_id: str, audio_chunk: bytes):
        """发送音频块"""
        await voice_manager.send_audio(session_id, audio_chunk)

tts_service = StreamingAzureTTS()
```

#### 3.2 本地TTS备选方案
```python
import torch
from transformers import VitsModel, AutoTokenizer
import io

class LocalVitsTTS:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = VitsModel.from_pretrained("facebook/vits-vi-cantonese")
        self.tokenizer = AutoTokenizer.from_pretrained("facebook/vits-vi-cantonese")
        self.model.to(self.device)
    
    async def synthesize_stream(self, text: str, session_id: str) -> bytes:
        """本地VITS语音合成"""
        inputs = self.tokenizer(text, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        
        with torch.no_grad():
            output = self.model(**inputs)
            waveform = output.waveform[0].cpu().numpy()
        
        # 转换为字节流
        audio_bytes = self._wav_to_bytes(waveform, 22050)
        
        # 分块发送
        chunk_size = 1024
        for i in range(0, len(audio_bytes), chunk_size):
            chunk = audio_bytes[i:i+chunk_size]
            await voice_manager.send_audio(session_id, chunk)
        
        return audio_bytes
    
    def _wav_to_bytes(self, waveform: np.ndarray, sample_rate: int) -> bytes:
        """将波形转换为WAV字节"""
        import wave
        
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # 单声道
            wav_file.setsampwidth(2)  # 16位
            wav_file.setframerate(sample_rate)
            wav_file.writeframes((waveform * 32767).astype(np.int16))
        
        return buffer.getvalue()

# 本地TTS备选
local_tts_service = LocalVitsTTS()
```

### 4. AI处理服务集成

#### 4.1 实时对话处理
```python
from agent.sales_agent import SalesAgent
from agent.schemas import AgentInput, SessionState

class RealtimeVoiceAgent:
    def __init__(self):
        self.sales_agent = SalesAgent()
        self.conversation_contexts = {}
    
    async def process_voice_input(self, session_id: str, text: str) -> VoiceResponse:
        """处理语音输入"""
        # 获取或创建会话状态
        session_state = self._get_session_state(session_id)
        
        # 检测打断（如果用户正在说话）
        if self._is_speaking(session_id):
            await self._interrupt_current_response(session_id)
        
        # 处理输入
        agent_input = AgentInput(
            session_state=session_state,
            user_message=text,
            retrieved_cars=[]  # 可以后续集成RAG
        )
        
        result = self.sales_agent.process(agent_input)
        
        # 更新会话状态
        self.conversation_contexts[session_id] = result.session_state
        
        # 创建语音响应
        voice_response = VoiceResponse(
            text=result.response_text,
            stage=result.session_state.stage.value,
            needs_analysis=result.session_state.needs,
            confidence=self._calculate_response_confidence(result)
        )
        
        return voice_response
    
    def _get_session_state(self, session_id: str) -> SessionState:
        """获取会话状态"""
        if session_id not in self.conversation_contexts:
            self.conversation_contexts[session_id] = SessionState(
                session_id=session_id,
                stage="welcome"
            )
        return self.conversation_contexts[session_id]
    
    def _is_speaking(self, session_id: str) -> bool:
        """检查是否正在说话"""
        # 实现语音活动检测逻辑
        return False
    
    async def _interrupt_current_response(self, session_id: str):
        """打断当前回复"""
        await voice_manager.send_event(session_id, {
            "type": "interrupt",
            "action": "stop_speaking"
        })
    
    def _calculate_response_confidence(self, result) -> float:
        """计算响应置信度"""
        # 基于多个因素计算置信度
        base_confidence = 0.8
        
        # 根据阶段调整
        if result.session_state.stage in ["welcome", "profile_analysis"]:
            base_confidence += 0.1
        
        # 根据提取质量调整
        if result.session_state.profile.name:
            base_confidence += 0.05
        
        return min(base_confidence, 1.0)

voice_agent = RealtimeVoiceAgent()
```

#### 4.2 智能打断处理
```python
class VoiceActivityDetector:
    def __init__(self):
        self.is_speaking_threshold = 0.05
        self.silence_duration = 0.5  # 0.5秒静音认为说话结束
        self.last_audio_time = {}
    
    async def detect_voice_activity(self, session_id: str, audio_chunk: bytes):
        """语音活动检测"""
        # 计算音频能量
        audio_array = np.frombuffer(audio_chunk, dtype=np.float32)
        energy = np.mean(audio_array ** 2)
        
        current_time = time.time()
        
        if energy > self.is_speaking_threshold:
            self.last_audio_time[session_id] = current_time
            if not self._is_currently_speaking(session_id):
                await self._on_speech_start(session_id)
        else:
            if self._is_currently_speaking(session_id):
                silence_duration = current_time - self.last_audio_time.get(session_id, 0)
                if silence_duration > self.silence_duration:
                    await self._on_speech_end(session_id)
    
    def _is_currently_speaking(self, session_id: str) -> bool:
        """检查当前是否在说话"""
        last_time = self.last_audio_time.get(session_id, 0)
        return (time.time() - last_time) < self.silence_duration
    
    async def _on_speech_start(self, session_id: str):
        """语音开始事件"""
        await voice_manager.send_event(session_id, {
            "type": "voice_activity",
            "status": "speaking"
        })
    
    async def _on_speech_end(self, session_id: str):
        """语音结束事件"""
        await voice_manager.send_event(session_id, {
            "type": "voice_activity", 
            "status": "silence"
        })

vad = VoiceActivityDetector()
```

## 前端集成

### React组件实现
```typescript
// VoiceChat.tsx
import React, { useState, useEffect, useRef } from 'react';
import { VoiceConnection } from '../services/voiceConnection';

interface VoiceChatProps {
  sessionId: string;
  onTranscription: (text: string) => void;
  onStageChange: (stage: string) => void;
}

export const VoiceChat: React.FC<VoiceChatProps> = ({
  sessionId,
  onTranscription,
  onStageChange
}) => {
  const [isConnected, setIsConnected] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [currentTranscription, setCurrentTranscription] = useState('');
  
  const voiceConnectionRef = useRef<VoiceConnection>();
  const audioContextRef = useRef<AudioContext>();
  const analyserRef = useRef<AnalyserNode>();

  useEffect(() => {
    initializeVoiceChat();
    return () => {
      cleanup();
    };
  }, []);

  const initializeVoiceChat = async () => {
    try {
      // 初始化音频上下文
      audioContextRef.current = new AudioContext();
      analyserRef.current = audioContextRef.current.createAnalyser();
      analyserRef.current.fftSize = 2048;

      // 创建语音连接
      voiceConnectionRef.current = new VoiceConnection();
      
      await voiceConnectionRef.current.connect(sessionId);
      
      // 设置事件监听
      voiceConnectionRef.current.on('transcription', (data) => {
        setCurrentTranscription(data.text);
        onTranscription(data.text);
      });
      
      voiceConnectionRef.current.on('stage_change', (data) => {
        onStageChange(data.stage);
      });
      
      voiceConnectionRef.current.on('voice_activity', (data) => {
        setIsSpeaking(data.status === 'speaking');
      });
      
      voiceConnectionRef.current.on('audio_chunk', (audioData) => {
        playAudioChunk(audioData);
      });
      
      setIsConnected(true);
    } catch (error) {
      console.error('语音连接初始化失败:', error);
    }
  };

  const playAudioChunk = async (audioData: ArrayBuffer) => {
    if (!audioContextRef.current) return;
    
    try {
      const audioBuffer = await audioContextRef.current.decodeAudioData(audioData);
      const source = audioContextRef.current.createBufferSource();
      source.buffer = audioBuffer;
      source.connect(analyserRef.current);
      analyserRef.current.connect(audioContextRef.current.destination);
      source.start();
    } catch (error) {
      console.error('音频播放失败:', error);
    }
  };

  const toggleMute = () => {
    if (voiceConnectionRef.current) {
      voiceConnectionRef.current.toggleMute();
    }
  };

  const cleanup = () => {
    if (voiceConnectionRef.current) {
      voiceConnectionRef.current.disconnect();
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
  };

  return (
    <div className="voice-chat">
      <div className="connection-status">
        <span className={`status-indicator ${isConnected ? 'connected' : 'disconnected'}`} />
        {isConnected ? '已连接' : '连接中...'}
      </div>
      
      <div className="voice-activity">
        <div className={`speaking-indicator ${isSpeaking ? 'speaking' : ''}`}>
          {isSpeaking ? '正在说话...' : '静音'}
        </div>
      </div>
      
      <div className="transcription">
        <h3>语音识别:</h3>
        <p>{currentTranscription}</p>
      </div>
      
      <div className="controls">
        <button onClick={toggleMute}>
          静音/取消静音
        </button>
      </div>
      
      {/* 音频可视化 */}
      <canvas 
        ref={(canvas) => {
          if (canvas && analyserRef.current) {
            drawWaveform(canvas, analyserRef.current);
          }
        }}
        className="audio-visualizer"
      />
    </div>
  );
};

// 绘制音频波形
const drawWaveform = (canvas: HTMLCanvasElement, analyser: AnalyserNode) => {
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  
  const bufferLength = analyser.frequencyBinCount;
  const dataArray = new Uint8Array(bufferLength);
  
  const draw = () => {
    requestAnimationFrame(draw);
    
    analyser.getByteTimeDomainData(dataArray);
    
    ctx.fillStyle = 'rgb(20, 20, 20)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    
    ctx.lineWidth = 2;
    ctx.strokeStyle = 'rgb(0, 255, 0)';
    ctx.beginPath();
    
    const sliceWidth = canvas.width / bufferLength;
    let x = 0;
    
    for (let i = 0; i < bufferLength; i++) {
      const v = dataArray[i] / 128.0;
      const y = v * canvas.height / 2;
      
      if (i === 0) {
        ctx.moveTo(x, y);
      } else {
        ctx.lineTo(x, y);
      }
      
      x += sliceWidth;
    }
    
    ctx.lineTo(canvas.width, canvas.height / 2);
    ctx.stroke();
  };
  
  draw();
};
```

## 性能优化策略

### 1. 音频流优化
```python
class AudioStreamOptimizer:
    def __init__(self):
        self.adaptive_bitrate = True
        self.compression_enabled = True
        self.buffer_size = 1024
        
    def optimize_audio_chunk(self, audio_data: bytes, network_quality: str) -> bytes:
        """根据网络质量优化音频块"""
        if network_quality == "poor":
            # 降低比特率
            audio_data = self._compress_audio(audio_data, quality=0.6)
        elif network_quality == "excellent":
            # 提高质量
            audio_data = self._enhance_audio(audio_data)
        
        return audio_data
    
    def _compress_audio(self, audio_data: bytes, quality: float) -> bytes:
        """音频压缩"""
        # 使用Opus编码器压缩
        import opuslib
        
        encoder = opuslib.Encoder(16000, 1, opuslib.APPLICATION_AUDIO)
        compressed = encoder.encode(audio_data, self.buffer_size)
        return compressed
    
    def _enhance_audio(self, audio_data: bytes) -> bytes:
        """音频增强"""
        # 应用音频增强算法
        return audio_data

stream_optimizer = AudioStreamOptimizer()
```

### 2. 缓存策略
```python
import redis
import pickle
from typing import Optional

class VoiceCacheManager:
    def __init__(self):
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0)
        self.tts_cache_ttl = 3600  # 1小时
        self.asr_cache_ttl = 300   # 5分钟
    
    async def get_cached_tts(self, text_hash: str) -> Optional[bytes]:
        """获取缓存的TTS音频"""
        cached = self.redis_client.get(f"tts:{text_hash}")
        if cached:
            return pickle.loads(cached)
        return None
    
    async def cache_tts(self, text_hash: str, audio_data: bytes):
        """缓存TTS音频"""
        self.redis_client.setex(
            f"tts:{text_hash}",
            self.tts_cache_ttl,
            pickle.dumps(audio_data)
        )
    
    async def get_cached_asr(self, audio_hash: str) -> Optional[str]:
        """获取缓存的ASR结果"""
        cached = self.redis_client.get(f"asr:{audio_hash}")
        if cached:
            return pickle.loads(cached)
        return None
    
    async def cache_asr(self, audio_hash: str, transcription: str):
        """缓存ASR结果"""
        self.redis_client.setex(
            f"asr:{audio_hash}",
            self.asr_cache_ttl,
            pickle.dumps(transcription)
        )

voice_cache = VoiceCacheManager()
```

## 部署和扩展性

### 1. 微服务架构
```yaml
# docker-compose.yml
version: '3.8'

services:
  voice-api:
    build: ./voice-api
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - AZURE_TTS_API_KEY=${AZURE_TTS_API_KEY}
      - AZURE_TTS_REGION=${AZURE_TTS_REGION}
    depends_on:
      - redis
      - asr-service
      - tts-service
  
  asr-service:
    build: ./asr-service
    ports:
      - "8001:8001"
    volumes:
      - ./models:/app/models
    environment:
      - MODEL_PATH=/app/models/whisper-turbo
  
  tts-service:
    build: ./tts-service
    ports:
      - "8002:8002"
    environment:
      - AZURE_TTS_API_KEY=${AZURE_TTS_API_KEY}
      - AZURE_TTS_REGION=${AZURE_TTS_REGION}
  
  redis:
    image: redis:alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  redis_data:
```

### 2. 负载均衡和扩展
```python
# 使用Kubernetes部署
apiVersion: apps/v1
kind: Deployment
metadata:
  name: voice-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: voice-api
  template:
    metadata:
      labels:
        app: voice-api
    spec:
      containers:
      - name: voice-api
        image: autovend/voice-api:latest
        ports:
        - containerPort: 8000
        env:
        - name: REDIS_URL
          value: "redis://redis-service:6379"
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "1Gi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: voice-api-service
spec:
  selector:
    app: voice-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## 监控和调试

### 1. 性能监控
```python
import time
from prometheus_client import Counter, Histogram, Gauge

# 指标定义
VOICE_REQUESTS_TOTAL = Counter('voice_requests_total', 'Total voice requests')
VOICE_LATENCY = Histogram('voice_latency_seconds', 'Voice processing latency')
ACTIVE_CONNECTIONS = Gauge('active_voice_connections', 'Active voice connections')
ASR_ACCURACY = Gauge('asr_accuracy', 'ASR accuracy rate')
TTS_LATENCY = Histogram('tts_latency_seconds', 'TTS processing latency')

class VoiceMetrics:
    @staticmethod
    def record_request():
        VOICE_REQUESTS_TOTAL.inc()
    
    @staticmethod
    def record_latency(start_time: float):
        VOICE_LATENCY.observe(time.time() - start_time)
    
    @staticmethod
    def update_active_connections(count: int):
        ACTIVE_CONNECTIONS.set(count)
    
    @staticmethod
    def update_asr_accuracy(accuracy: float):
        ASR_ACCURACY.set(accuracy)
    
    @staticmethod
    def record_tts_latency(start_time: float):
        TTS_LATENCY.observe(time.time() - start_time)
```

### 2. 日志和调试
```python
import logging
import json
from datetime import datetime

class VoiceLogger:
    def __init__(self):
        self.logger = logging.getLogger('voice_service')
        self.logger.setLevel(logging.INFO)
        
        # 创建文件处理器
        handler = logging.FileHandler('voice_service.log')
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
    
    def log_voice_event(self, session_id: str, event_type: str, data: dict):
        """记录语音事件"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'session_id': session_id,
            'event_type': event_type,
            'data': data
        }
        self.logger.info(json.dumps(log_entry))
    
    def log_performance(self, session_id: str, component: str, duration: float):
        """记录性能指标"""
        self.log_voice_event(session_id, 'performance', {
            'component': component,
            'duration': duration
        })
    
    def log_error(self, session_id: str, error: str, context: dict):
        """记录错误"""
        self.log_voice_event(session_id, 'error', {
            'error': error,
            'context': context
        })

voice_logger = VoiceLogger()
```

## 安全和隐私

### 1. 音频数据加密
```python
from cryptography.fernet import Fernet
import base64

class AudioEncryption:
    def __init__(self):
        self.key = Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt_audio(self, audio_data: bytes) -> bytes:
        """加密音频数据"""
        return self.cipher.encrypt(audio_data)
    
    def decrypt_audio(self, encrypted_data: bytes) -> bytes:
        """解密音频数据"""
        return self.cipher.decrypt(encrypted_data)
    
    def get_public_key(self) -> str:
        """获取公钥用于密钥交换"""
        return base64.b64encode(self.key).decode()

audio_encryption = AudioEncryption()
```

### 2. 数据隐私保护
```python
class VoicePrivacyManager:
    def __init__(self):
        self.retention_days = 30
        self.anonymization_enabled = True
    
    def anonymize_voice_data(self, audio_data: bytes) -> bytes:
        """匿名化语音数据"""
        if self.anonymization_enabled:
            # 应用语音匿名化技术
            audio_data = self._apply_voice_conversion(audio_data)
        return audio_data
    
    def schedule_data_deletion(self, session_id: str):
        """安排数据删除"""
        deletion_date = datetime.utcnow() + timedelta(days=self.retention_days)
        # 实现定时删除逻辑
        pass
    
    def _apply_voice_conversion(self, audio_data: bytes) -> bytes:
        """应用语音转换保护隐私"""
        # 使用语音转换技术改变声纹特征
        return audio_data

voice_privacy = VoicePrivacyManager()
```

## 实施路线图

### Phase 1: 基础实时通信（2-3周）
- [ ] 实现WebSocket音频传输
- [ ] 集成基础ASR（Whisper）
- [ ] 实现基础TTS（Azure或本地）
- [ ] 前端WebRTC集成

### Phase 2: 优化和增强（3-4周）
- [ ] 实现流式处理
- [ ] 添加智能打断
- [ ] 优化音频质量
- [ ] 实现缓存策略

### Phase 3: 高级功能（4-6周）
- [ ] 多语言支持
- [ ] 情感识别
- [ ] 个性化语音
- [ ] 高级降噪

### Phase 4: 扩展和监控（持续）
- [ ] 微服务部署
- [ ] 性能监控
- [ ] 安全加固
- [ ] 负载测试

## 成功指标

### 技术指标
- **端到端延迟**: <500ms
- **ASR准确率**: >95%
- **TTS自然度**: MOS >4.0
- **并发连接**: >1000

### 用户体验指标
- **对话完成率**: >90%
- **用户满意度**: >4.5/5
- **中断响应时间**: <200ms
- **音频质量**: PESQ >3.5

## 结论

这套实时语音通话解决方案将为AutoVend提供：
1. **真正的实时对话体验**，延迟控制在500ms以内
2. **高质量的语音交互**，集成先进的ASR和TTS技术
3. **智能的对话管理**，支持打断和上下文理解
4. **可扩展的架构**，支持大规模并发用户
5. **完善的安全保护**，确保用户隐私和数据安全

通过分阶段实施，可以逐步将AutoVend从文本对话升级为真正的语音智能销售助手，为用户提供更自然、更高效的购车咨询体验。

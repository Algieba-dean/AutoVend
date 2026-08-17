import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { voiceService } from '../../services/api';
import './VoiceTest.css';

const VoiceTest = () => {
  const navigate = useNavigate();

  // TTS State
  const [ttsText, setTtsText] = useState('您好！我是AutoVend智能售车助手，很高兴为您服务！');
  const [ttsVoice, setTtsVoice] = useState('zh-CN-XiaoxiaoNeural');
  const [ttsLoading, setTtsLoading] = useState(false);
  const [ttsAudioUrl, setTtsAudioUrl] = useState(null);
  const [ttsMetrics, setTtsMetrics] = useState(null);
  const [ttsError, setTtsError] = useState(null);

  // ASR State
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [audioBlob, setAudioBlob] = useState(null);
  const [audioLevel, setAudioLevel] = useState(0);
  const [asrLoading, setAsrLoading] = useState(false);
  const [asrResult, setAsrResult] = useState(null);
  const [asrError, setAsrError] = useState(null);

  // WS Debugger State
  const [wsActive, setWsActive] = useState(false);
  const [wsLogs, setWsLogs] = useState([]);
  const [wsStatus, setWsStatus] = useState('idle');
  const wsRef = useRef(null);
  const wsRecorderRef = useRef(null);
  const wsStreamRef = useRef(null);
  const animFrameRef = useRef(null);

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const recordingTimerRef = useRef(null);
  const audioCtxRef = useRef(null);

  // Log logger helper
  const addWsLog = (tag, msg, type = 'info') => {
    const timestamp = new Date().toLocaleTimeString();
    setWsLogs(prev => [...prev.slice(-40), { timestamp, tag, msg, type }]);
  };

  // ─────────────────────────────────────────────────────────────
  // 1. TTS 语音合成测试 handler
  // ─────────────────────────────────────────────────────────────
  const handleTestTTS = async () => {
    if (!ttsText.trim()) return;
    setTtsLoading(true);
    setTtsError(null);
    setTtsAudioUrl(null);
    setTtsMetrics(null);

    const startTime = Date.now();
    try {
      const response = await fetch(`http://localhost:8000/api/voice/synthesize?text=${encodeURIComponent(ttsText)}&voice=${encodeURIComponent(ttsVoice)}`, {
        method: 'POST'
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}: ${await response.text()}`);
      }

      const timeMs = Date.now() - startTime;
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      setTtsAudioUrl(url);

      const voiceHeader = response.headers.get('X-TTS-Voice') || ttsVoice;
      const serverTimeHeader = response.headers.get('X-TTS-Processing-Time-Ms') || timeMs;

      setTtsMetrics({
        sizeKb: (blob.size / 1024).toFixed(1),
        serverTimeMs: serverTimeHeader,
        networkTimeMs: timeMs,
        voice: voiceHeader
      });

      // Play audio automatically
      const audio = new Audio(url);
      audio.play().catch(e => console.error('TTS Audio play error:', e));

    } catch (err) {
      console.error('TTS Test Failed:', err);
      setTtsError(err.message || 'TTS 语音合成失败');
    } finally {
      setTtsLoading(false);
    }
  };

  // ─────────────────────────────────────────────────────────────
  // 2. ASR 单次录音识别测试 handler
  // ─────────────────────────────────────────────────────────────
  const handleStartRecording = async () => {
    setAsrResult(null);
    setAsrError(null);
    setAudioBlob(null);
    audioChunksRef.current = [];

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      audioCtxRef.current = new (window.AudioContext || window.webkitAudioContext)();
      const source = audioCtxRef.current.createMediaStreamSource(stream);
      const analyser = audioCtxRef.current.createAnalyser();
      analyser.fftSize = 256;
      source.connect(analyser);

      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = () => {
        const mimeType = recorder.mimeType || 'audio/webm';
        const blob = new Blob(audioChunksRef.current, { type: mimeType });
        setAudioBlob(blob);
        stream.getTracks().forEach(track => track.stop());
      };

      recorder.start();
      setIsRecording(true);
      setRecordingTime(0);

      recordingTimerRef.current = setInterval(() => {
        setRecordingTime(prev => prev + 1);
      }, 1000);

      // Audio volume loop
      const dataArray = new Uint8Array(analyser.frequencyBinCount);
      const updateVolume = () => {
        if (!mediaRecorderRef.current || mediaRecorderRef.current.state !== 'recording') return;
        analyser.getByteFrequencyData(dataArray);
        let sum = 0;
        for (let i = 0; i < dataArray.length; i++) sum += dataArray[i];
        const avg = sum / dataArray.length;
        setAudioLevel(Math.min(100, Math.round(avg * 2.5)));
        animFrameRef.current = requestAnimationFrame(updateVolume);
      };
      updateVolume();

    } catch (err) {
      console.error('Microphone error:', err);
      setAsrError('无法访问麦克风: ' + err.message);
    }
  };

  const handleStopRecording = () => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    setAudioLevel(0);
    if (recordingTimerRef.current) {
      clearInterval(recordingTimerRef.current);
      recordingTimerRef.current = null;
    }
  };

  const handleUploadASR = async () => {
    if (!audioBlob) return;
    setAsrLoading(true);
    setAsrError(null);

    const formData = new FormData();
    formData.append('file', audioBlob, `recording.${audioBlob.type.includes('webm') ? 'webm' : 'wav'}`);

    try {
      const response = await fetch('http://localhost:8000/api/voice/transcribe', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        throw new Error(`HTTP error ${response.status}: ${await response.text()}`);
      }

      const json = await response.json();
      setAsrResult(json);
    } catch (err) {
      console.error('ASR Upload Failed:', err);
      setAsrError(err.message || 'ASR 识别失败');
    } finally {
      setAsrLoading(false);
    }
  };

  // ─────────────────────────────────────────────────────────────
  // 3. WebSocket 全双工实时语音联调诊断
  // ─────────────────────────────────────────────────────────────
  const handleStartWsDebug = async () => {
    setWsActive(true);
    setWsStatus('connecting');
    addWsLog('SYS', '正在创建测试语音 Session...');

    try {
      const sessionData = await voiceService.createVoiceSession('13888888888');
      const sid = sessionData.session_id;
      addWsLog('SYS', `Session 创建成功: ${sid}`);

      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      } catch (e) {
        addWsLog('WARN', '硬件麦克风不可用，启动 WebAudio 模拟音轨降级...', 'warn');
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator();
        const dest = ctx.createMediaStreamDestination();
        osc.connect(dest);
        osc.start();
        stream = dest.stream;
      }
      wsStreamRef.current = stream;

      const wsClient = voiceService.createVoiceWebSocket(sid, {
        onOpen: () => {
          setWsStatus('connected');
          addWsLog('WS', '🟢 WebSocket 握手成功 (State: OPEN)', 'success');

          const recorder = new MediaRecorder(stream);
          wsRecorderRef.current = recorder;

          recorder.ondataavailable = (e) => {
            if (e.data && e.data.size > 0) {
              e.data.arrayBuffer().then(buf => {
                wsClient.sendAudio(buf);
                addWsLog('OUT', `发送音频切片: ${buf.byteLength} bytes`, 'debug');
              });
            }
          };
          recorder.start(250);
          addWsLog('REC', 'MediaRecorder 开始录音 (timeslice 250ms)');
        },
        onJson: (json) => {
          addWsLog('IN_JSON', JSON.stringify(json), json.type === 'error' ? 'error' : 'success');
        },
        onAudio: (arrayBuffer) => {
          addWsLog('IN_BIN', `收到 TTS 音频 MP3 字节数据包: ${arrayBuffer.byteLength} bytes`, 'success');
          const blob = new Blob([arrayBuffer], { type: 'audio/mp3' });
          const url = URL.createObjectURL(blob);
          const audio = new Audio(url);
          audio.play().catch(err => console.error('WS Audio playback error:', err));
        },
        onError: (err) => {
          addWsLog('WS_ERR', 'WebSocket 遇到网络错误', 'error');
        },
        onClose: () => {
          setWsStatus('closed');
          setWsActive(false);
          addWsLog('WS', '🔴 WebSocket 连接已关闭');
        }
      });

      wsRef.current = wsClient;
    } catch (err) {
      addWsLog('ERR', err.message, 'error');
      setWsStatus('error');
      setWsActive(false);
    }
  };

  const [isSimulating, setIsSimulating] = useState(false);

  const handleSimulateWsTurn = async (presetText = '我想买一辆20万到30万的高性价比新能源SUV') => {
    if (!wsRef.current) {
      alert('请先点击 "▶️ 建立 WS 测试连接并开麦"');
      return;
    }

    setIsSimulating(true);
    addWsLog('SIM', `正在生成模拟测试语音流: "${presetText}"...`, 'warn');

    try {
      // 1. Fetch TTS MP3 audio for preset phrase to emulate user mic speech
      const response = await fetch(`http://localhost:8000/api/voice/synthesize?text=${encodeURIComponent(presetText)}&voice=zh-CN-XiaoxiaoNeural`, {
        method: 'POST'
      });
      if (!response.ok) throw new Error('Failed to generate simulation audio');

      const audioArrayBuffer = await response.arrayBuffer();
      addWsLog('SIM', `生成语音包成功 (${audioArrayBuffer.byteLength} bytes)，准备逐帧推入 WebSocket...`, 'info');

      // Send start_turn signal
      wsRef.current.startTurn();
      addWsLog('OUT_JSON', '发送起点信号: {"type": "start_turn"}', 'info');

      // 2. Stream audio in 4KB chunks over WebSocket every 50ms
      const chunkSize = 4096;
      for (let i = 0; i < audioArrayBuffer.byteLength; i += chunkSize) {
        const slice = audioArrayBuffer.slice(i, i + chunkSize);
        wsRef.current.sendAudio(slice);
        await new Promise(r => setTimeout(r, 50));
      }

      addWsLog('SIM', '模拟语音切片全数推入完成，触发展示 ASR + Agent + TTS 全链路回答...', 'info');

      // 3. Send end_turn signal
      wsRef.current.endTurn();
      addWsLog('OUT_JSON', '发送终点信号: {"type": "end_turn"}', 'warn');

    } catch (err) {
      console.error('Simulate Voice Stream Error:', err);
      addWsLog('SIM_ERR', err.message, 'error');
    } finally {
      setIsSimulating(false);
    }
  };

  const handleSendWsEndTurn = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'end_turn' }));
      addWsLog('OUT', '手动触发 JSON: {"type": "end_turn"}', 'warn');
    }
  };

  const handleStopWsDebug = () => {
    if (wsRecorderRef.current && wsRecorderRef.current.state === 'recording') {
      wsRecorderRef.current.stop();
    }
    if (wsStreamRef.current) {
      wsStreamRef.current.getTracks().forEach(t => t.stop());
    }
    if (wsRef.current) {
      wsRef.current.close();
    }
    setWsActive(false);
    setWsStatus('idle');
  };

  useEffect(() => {
    return () => {
      if (recordingTimerRef.current) clearInterval(recordingTimerRef.current);
      if (wsStreamRef.current) wsStreamRef.current.getTracks().forEach(t => t.stop());
    };
  }, []);

  return (
    <div className="voice-test-page">
      <div className="test-header">
        <button className="back-btn" onClick={() => navigate('/')}>← 返回首页</button>
        <h2>🎙️ AutoVend ASR & TTS 独立诊断测试台</h2>
        <p className="subtitle">用于精准测试 Faster-Whisper ASR 识别、Edge-TTS 语音合成与全双工 WebSocket 消息通路</p>
      </div>

      <div className="test-grid">
        {/* ── 1. TTS 测试模块 ───────────────────────────── */}
        <div className="test-card tts-card">
          <div className="card-header">
            <h3><i className="fa-solid fa-volume-high"></i> Edge-TTS 语音合成独立测试</h3>
            <span className="badge tts">TTS Module</span>
          </div>
          <div className="card-body">
            <div className="form-group">
              <label>待合成文本：</label>
              <textarea
                value={ttsText}
                onChange={(e) => setTtsText(e.target.value)}
                placeholder="请输入要合成为语音的文字..."
                rows={3}
              />
            </div>
            <div className="form-group row">
              <label>发音人 (Voice):</label>
              <select value={ttsVoice} onChange={(e) => setTtsVoice(e.target.value)}>
                <option value="zh-CN-XiaoxiaoNeural">zh-CN-XiaoxiaoNeural (中文女声)</option>
                <option value="zh-CN-YunxiNeural">zh-CN-YunxiNeural (中文男声)</option>
                <option value="en-US-AriaNeural">en-US-AriaNeural (英文女声)</option>
              </select>
            </div>

            <button
              className="action-btn tts-btn"
              onClick={handleTestTTS}
              disabled={ttsLoading || !ttsText.trim()}
            >
              {ttsLoading ? '⚡ 正在合成语音...' : '🔊 合成并播放语音'}
            </button>

            {ttsError && (
              <div className="error-box"><i className="fa-solid fa-circle-exclamation"></i> {ttsError}</div>
            )}

            {ttsMetrics && (
              <div className="result-box tts-result">
                <h4><i className="fa-solid fa-circle-check"></i> TTS 合成成功</h4>
                <div className="metrics-grid">
                  <div className="metric"><span>音频体积:</span> <strong>{ttsMetrics.sizeKb} KB</strong></div>
                  <div className="metric"><span>服务端耗时:</span> <strong>{ttsMetrics.serverTimeMs} ms</strong></div>
                  <div className="metric"><span>总网络耗时:</span> <strong>{ttsMetrics.networkTimeMs} ms</strong></div>
                  <div className="metric"><span>发音人:</span> <strong>{ttsMetrics.voice}</strong></div>
                </div>
                {ttsAudioUrl && (
                  <audio controls src={ttsAudioUrl} className="audio-player" />
                )}
              </div>
            )}
          </div>
        </div>

        {/* ── 2. ASR 测试模块 ───────────────────────────── */}
        <div className="test-card asr-card">
          <div className="card-header">
            <h3><i className="fa-solid fa-microphone"></i> Faster-Whisper ASR 语音识别测试</h3>
            <span className="badge asr">ASR Module</span>
          </div>
          <div className="card-body">
            <div className="record-controls">
              <button
                className={`record-btn ${isRecording ? 'recording' : ''}`}
                onClick={isRecording ? handleStopRecording : handleStartRecording}
              >
                {isRecording ? `🔴 停止录音 (${recordingTime}s)` : '🎤 开始麦克风录音'}
              </button>

              {isRecording && (
                <div className="volume-meter-bar">
                  <div className="volume-fill" style={{ width: `${audioLevel}%` }}></div>
                </div>
              )}
            </div>

            {audioBlob && (
              <div className="blob-info-box">
                <span><i className="fa-solid fa-file-audio"></i> 已捕获录音包: {(audioBlob.size / 1024).toFixed(1)} KB ({audioBlob.type})</span>
                <button className="upload-btn" onClick={handleUploadASR} disabled={asrLoading}>
                  {asrLoading ? '⚡ 识别中...' : '🚀 发送给 ASR 进行识别'}
                </button>
              </div>
            )}

            {asrError && (
              <div className="error-box"><i className="fa-solid fa-circle-exclamation"></i> {asrError}</div>
            )}

            {asrResult && (
              <div className="result-box asr-result">
                <h4><i className="fa-solid fa-circle-check"></i> ASR 识别结果</h4>
                <div className="recognized-text-box">
                  <strong>识别出的文字：</strong>
                  <p className="text-highlight">"{asrResult.text || '(未识别出文字/环境静音)'}"</p>
                </div>
                <div className="metrics-grid">
                  <div className="metric"><span>识别耗时:</span> <strong>{asrResult.processing_time_ms} ms</strong></div>
                  <div className="metric"><span>检测语言:</span> <strong>{asrResult.language}</strong></div>
                  <div className="metric"><span>音频时长:</span> <strong>{asrResult.duration_seconds ? asrResult.duration_seconds.toFixed(1) : 0} s</strong></div>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* ── 3. WebSocket 实时日志与终端诊断 ───────────── */}
        <div className="test-card ws-card full-width">
          <div className="card-header">
            <h3><i className="fa-solid fa-terminal"></i> WebSocket 实时全双工消息抓包与诊断 Console</h3>
            <span className={`badge ws-badge ${wsStatus}`}>{wsStatus.toUpperCase()}</span>
          </div>
          <div className="card-body">
            <div className="ws-btn-group">
              <button className="action-btn ws-start" onClick={handleStartWsDebug} disabled={wsActive}>
                ▶️ 建立 WS 测试连接并开麦
              </button>
              <button className="action-btn ws-sim" onClick={() => handleSimulateWsTurn()} disabled={wsStatus !== 'connected' || isSimulating}>
                {isSimulating ? '⚡ 正在推入模拟语音流...' : '⚡ 一键测试全双工语音流 ("我想买一辆20万到30万的SUV")'}
              </button>
              <button className="action-btn ws-turn" onClick={handleSendWsEndTurn} disabled={!wsActive}>
                ⚡ 触发 end_turn
              </button>
              <button className="action-btn ws-stop" onClick={handleStopWsDebug} disabled={!wsActive}>
                ⏹️ 关闭 WS 测试
              </button>
            </div>

            <div className="log-console">
              {wsLogs.length === 0 ? (
                <div className="empty-log">点击“建立 WS 测试连接并开麦”查看控制台传输日志...</div>
              ) : (
                wsLogs.map((log, index) => (
                  <div key={index} className={`log-line ${log.type}`}>
                    <span className="log-time">[{log.timestamp}]</span>
                    <span className="log-tag">[{log.tag}]</span>
                    <span className="log-msg">{log.msg}</span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default VoiceTest;

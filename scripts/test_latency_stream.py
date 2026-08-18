#!/usr/bin/env python3
"""
Detailed Streaming Latency & Throughput Benchmark for AutoVend API.
Measures TTFB (Time to First Byte / Metadata), TTFT (Time to First Token), Total E2E Latency, and TPS.
"""

import json
import time
import requests
import sys

API_URL = "http://localhost:8000/api/chat/stream"

def test_stream_latency(session_id: str, message: str):
    print(f"\n==================================================")
    print(f"📊 正在测试消息: \"{message}\"")
    print(f"==================================================")
    sys.stdout.flush()

    start_time = time.perf_counter()
    ttfb = None
    ttft = None
    first_token_time = None
    token_count = 0
    full_text = ""
    stage_info = ""

    payload = {"session_id": session_id, "message": message}
    headers = {"Content-Type": "application/json"}

    with requests.post(API_URL, json=payload, headers=headers, stream=True) as response:
        if response.status_code != 200:
            print(f"❌ 请求失败: HTTP {response.status_code}")
            return

        current_event = "message"

        for line in response.iter_lines(decode_unicode=True):
            now = time.perf_counter()
            if ttfb is None:
                ttfb = now - start_time

            if not line:
                continue

            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:].strip()
                try:
                    parsed = json.loads(data_str)
                    if current_event == "metadata":
                        stage_info = parsed.get("stage", {}).get("current_stage", "")
                    elif current_event == "token":
                        delta = parsed.get("delta", "")
                        if delta:
                            if ttft is None:
                                ttft = now - start_time
                                first_token_time = now
                            token_count += len(delta)
                            full_text += delta
                    elif current_event == "done":
                        break
                except Exception:
                    pass

    end_time = time.perf_counter()
    total_time = end_time - start_time
    gen_time = (end_time - first_token_time) if first_token_time else 0.001
    tps = token_count / gen_time if gen_time > 0 else 0

    print(f"⚡ 首字节/元数据延迟 (TTFB / Metadata) : {ttfb * 1000:.2f} ms ({ttfb:.2f} s)")
    print(f"🚀 首字生成延迟   (TTFT / First Token): {ttft * 1000:.2f} ms ({ttft:.2f} s)" if ttft else "🚀 首字延迟: N/A")
    print(f"⏱️ 总端到端响应耗时 (Total E2E Latency) : {total_time * 1000:.2f} ms ({total_time:.2f} s)")
    print(f"📈 生成吞吐速率    (Generation Speed): {tps:.2f} 字/秒 ({token_count} 字 / {gen_time:.2f}秒)")
    print(f"📍 当前 SOP 阶段: [{stage_info}]")
    print(f"💬 完整回复内容: {full_text}")
    print(f"--------------------------------------------------")
    sys.stdout.flush()

if __name__ == "__main__":
    sid = f"stream_bench_{int(time.time())}"
    test_stream_latency(sid, "你好，我想选购一台家用 SUV")
    test_stream_latency(sid, "我叫张伟，手机号 13800008888，家里 3 口人")

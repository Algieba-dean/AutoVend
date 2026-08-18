#!/usr/bin/env python3
"""
End-to-End Latency Benchmark for AutoVend Hybrid RAG + Agent Architecture.

Measures turn-by-turn response time when routing control-path tasks to local vLLM.
"""

import json
import time
import urllib.request
from pathlib import Path

API_URL = "http://localhost:8000/api/chat/message"
SESSION_ID = f"latency_test_session_{int(time.time())}"

TURNS = [
    "你好，我想选购一台家用 SUV。",
    "我叫张伟，手机号 13800008888，家里 3 口人，主要我开。",
    "预算 35万左右，想要中大型纯电 SUV，续航 600km 以上，零百加速 4.5s 左右。",
    "不错，我想选 AutoVend EV7，预约这周六下午 14:00 在上海徐汇店试驾。",
    "好的，确认试驾人张伟，试驾时间周六下午14:00。",
    "非常感谢，再见！",
]

def benchmark():
    print("=" * 70)
    print("🚀 AutoVend 全链路 (Hybrid RAG + Agent + Local vLLM) 延迟性能测试")
    print("=" * 70)
    print(f"会话 ID  : {SESSION_ID}")
    print(f"请求接口: {API_URL}")
    print("=" * 70)

    latencies = []

    for idx, user_msg in enumerate(TURNS, 1):
        print(f"\n【Turn {idx}】 用户: \"{user_msg}\"")
        payload = json.dumps({
            "session_id": SESSION_ID,
            "message": user_msg
        }).encode("utf-8")

        req = urllib.request.Request(
            API_URL,
            data=payload,
            headers={"Content-Type": "application/json"}
        )

        start_time = time.perf_counter()
        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                latencies.append(elapsed_ms)

                stage_info = data.get("stage", {})
                curr_stage = stage_info.get("current_stage", "UNKNOWN")
                response_text = data.get("response", {}).get("content", "")
                
                print(f"⏱️ 响应延迟: {elapsed_ms:.2f} ms ({elapsed_ms / 1000:.2f} 秒)")
                print(f"📍 当前 SOP 阶段: [{curr_stage}]")
                print(f"🤖 算法回复摘要: {response_text[:80]}...")

        except Exception as e:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            print(f"❌ 请求失败 (耗时 {elapsed_ms:.2f} ms): {e}")

    print("\n" + "=" * 70)
    print("📊 端到端链路延迟统计结果汇总:")
    print("=" * 70)
    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        min_lat = min(latencies)
        max_lat = max(latencies)
        print(f"总测试轮次: {len(latencies)} 轮")
        print(f"平均端到端延迟: {avg_lat:.2f} ms ({avg_lat / 1000:.2f} s)")
        print(f"最小端到端延迟: {min_lat:.2f} ms ({min_lat / 1000:.2f} s)")
        print(f"最大端到端延迟: {max_lat:.2f} ms ({max_lat / 1000:.2f} s)")
        print("=" * 70)

if __name__ == "__main__":
    benchmark()

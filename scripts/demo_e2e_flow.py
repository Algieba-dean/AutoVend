"""
Full End-to-End Sales SOP Dialogue Test Script with Sub-DAG Stage Workflows.

Drives a complete multi-turn sales interaction:
WELCOME -> PROFILE_ANALYSIS -> NEEDS_ANALYSIS -> CAR_SELECTION (Sub-DAG) -> RESERVATION_4S (Sub-DAG) -> RESERVATION_CONFIRMATION -> FAREWELL
"""

import json
import urllib.request

API_URL = "http://localhost:8000/api/chat/message"
SESSION_ID = "e2e_full_session_001"

turns = [
    # Turn 1: Initial contact -> PROFILE_ANALYSIS
    "你好，我想选购一台家用 SUV。",
    # Turn 2: User profile & contact info -> NEEDS_ANALYSIS
    "我叫张伟，手机号 13800008888，家里 3 口人，主要我开。",
    # Turn 3: Vehicle needs & budget -> CAR_SELECTION (Triggers Sub-DAG: Multi-car comparison)
    "预算 35万左右，想要中大型纯电 SUV，续航 600km 以上，零百加速 4.5s 左右。",
    # Turn 4: Selecting vehicle -> RESERVATION_4S (Triggers Sub-DAG: Qualification check & 4S stock)
    "不错，我想选 AutoVend EV7，预约这周六下午 14:00 在上海徐汇店试驾。",
    # Turn 5: Confirming reservation details -> RESERVATION_CONFIRMATION
    "好的，试驾人张伟，电话 13800008888，试驾时间 2026-08-08 14:00，地点上海徐汇店，确认预约。",
    # Turn 6: Goodbye -> FAREWELL
    "非常感谢，再见！",
]


def send_turn(turn_idx: int, user_message: str):
    print(f"\n==================================================")
    print(f"【Turn {turn_idx + 1}】 用户输入: {user_message}")
    print(f"--------------------------------------------------")

    payload = json.dumps({
        "session_id": SESSION_ID,
        "message": user_message
    }).encode("utf-8")

    req = urllib.request.Request(
        API_URL,
        data=payload,
        headers={"Content-Type": "application/json"}
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

            stage_info = data.get("stage", {})
            prev_stage = stage_info.get("previous_stage", "")
            curr_stage = stage_info.get("current_stage", "")

            response_content = data.get("response", {}).get("content", "")
            matched_cars = data.get("matched_car_models", [])
            reservation = data.get("reservation_info", {})

            print(f"📍 状态流转: [{prev_stage}] ➔ [{curr_stage}]")
            if matched_cars:
                print(f"🚗 匹配车型: {[c.get('model_name', c) for c in matched_cars[:2]]}")
            if reservation.get("reservation_location"):
                print(f"📅 预约地点: {reservation.get('reservation_location')} | 顾问: {reservation.get('salesman')}")

            print(f"\n🤖 AutoVend 算法回复:\n{response_content}")

    except Exception as e:
        print(f"❌ 请求失败: {e}")


def main():
    print("🚀 启动 E2E 完整 sales FSM + Sub-DAG 对话链路测试...")
    for idx, msg in enumerate(turns):
        send_turn(idx, msg)
    print("\n✅ E2E 完整对话链路测试运行完毕！")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
测试LlamaIndex + Groq连接
"""

import os

from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

from llama_index.llms.openai_like import OpenAILike


def test_groq_connection():
    """测试Groq连接"""
    print("🔗 测试Groq连接...")

    # 获取配置
    api_key = os.getenv("GROQ_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

    if not api_key:
        print("❌ 错误: 请设置GROQ_API_KEY环境变量")
        return False

    print("📋 配置信息:")
    print(f"   模型: {model}")
    print(f"   API地址: {base_url}")
    print(f"   API密钥: {'*' * 20}{api_key[-10:]}")

    try:
        # 创建LLM实例
        llm = OpenAILike(model=model, api_base=base_url, api_key=api_key)

        # 测试简单对话
        print("\n💬 测试对话...")
        response = llm.complete("你好，请简单介绍一下你自己。")

        print("✅ 连接成功!")
        print(f"🤖 响应: {response.text}")

        return True

    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False


def main():
    """主函数"""
    print("🧪 LlamaIndex + Groq 连接测试")
    print("=" * 50)

    success = test_groq_connection()

    if success:
        print("\n🎉 测试通过! LlamaIndex + Groq 连接正常")
    else:
        print("\n💥 测试失败! 请检查配置")

    return 0 if success else 1


if __name__ == "__main__":
    exit(main())

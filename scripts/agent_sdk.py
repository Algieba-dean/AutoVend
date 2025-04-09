from openai import AsyncOpenAI
from agents import OpenAIChatCompletionsModel,Agent,Runner,set_default_openai_client
from agents.model_settings import ModelSettings
import asyncio

API_KEY= "sk-40f9ea6f41bd4cbbae8a9d4adb07fbf8"

external_client = AsyncOpenAI(
    base_url = "https://api.deepseek.com",
    api_key=API_KEY, 
)
set_default_openai_client(external_client)

deepseek_model = OpenAIChatCompletionsModel(
    model="deepseek-chat",
    openai_client=external_client)

agent = Agent(name="Assistant", 
              instructions="you are a smart automobile sealer",
              model=deepseek_model)

async def main():
    result = await Runner.run(agent, "try to sale a car to me") 
    print(result.final_output)
asyncio.run(main())
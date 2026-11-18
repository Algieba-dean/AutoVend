"""
LangChain-facing view of the HybridRouter and legacy LlamaIndex LLM adapters.

Provides:
1. `RoutedChatModel(BaseChatModel)`: Native LangChain chat model backed by
   AutoVend's `HybridRouter` (local vLLM for extraction/control, cloud API for
   customer-facing response generation), with full sync/async and token
   streaming support.
2. `LegacyLLMChatAdapter(BaseChatModel)`: Bridges LlamaIndex `LLM` instances
   (including `MockLLM` and `MagicMock` test doubles) to LangChain's
   `BaseChatModel` protocol.
3. `build_langchain_llms(router)`: Builds `(extraction_chat_model, generation_chat_model)`.
4. `ensure_chat_model(llm)`: Normalizes either a LangChain `BaseChatModel` or
   a LlamaIndex/mock LLM into a `BaseChatModel`.
"""

import asyncio
import json
from typing import Any, AsyncIterator, Dict, Iterator, List, Optional, Sequence, Tuple, Type, Union

from langchain_core.callbacks import (
    AsyncCallbackManagerForLLMRun,
    CallbackManagerForLLMRun,
)
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from langchain_core.runnables import Runnable, RunnableLambda
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, ConfigDict, Field

from src.llm.router import HybridRouter, Task


def _messages_to_openai_dicts(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """Convert LangChain BaseMessage list to OpenAI-compatible role/content/tool dicts."""
    payload: List[Dict[str, Any]] = []
    for msg in messages:
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        if isinstance(msg, ToolMessage):
            payload.append(
                {
                    "role": "tool",
                    "tool_call_id": msg.tool_call_id,
                    "content": content,
                }
            )
            continue
        if isinstance(msg, AIMessage):
            entry: Dict[str, Any] = {"role": "assistant", "content": content}
            tool_calls = getattr(msg, "tool_calls", None) or []
            if tool_calls:
                entry["tool_calls"] = [
                    {
                        "id": tc.get("id", f"call_{i}"),
                        "type": "function",
                        "function": {
                            "name": tc.get("name", ""),
                            "arguments": json.dumps(tc.get("args", {}), ensure_ascii=False)
                            if not isinstance(tc.get("args"), str)
                            else tc["args"],
                        },
                    }
                    for i, tc in enumerate(tool_calls)
                ]
                if not content:
                    entry["content"] = None
            payload.append(entry)
            continue
        if isinstance(msg, SystemMessage):
            role = "system"
        elif isinstance(msg, HumanMessage):
            role = "user"
        else:
            role = getattr(msg, "type", "user")
            if role == "human":
                role = "user"
            elif role == "ai":
                role = "assistant"
        payload.append({"role": role, "content": content})
    return payload


def _messages_to_prompt(messages: List[BaseMessage]) -> str:
    """Flatten LangChain messages into a single prompt string for completion-style mocks."""
    parts = []
    for msg in messages:
        content = msg.content if isinstance(msg.content, str) else str(msg.content)
        if content:
            parts.append(content)
    return "\n\n".join(parts)


class RoutedChatModel(BaseChatModel):
    """LangChain `BaseChatModel` whose calls route through `HybridRouter`."""

    router: Any = Field(exclude=True)
    task: Any = Field(default=Task.RESPONSE_GENERATION)
    model_name: str = "routed"
    max_tokens: int = 512

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def _llm_type(self) -> str:
        return "autovend-routed-chat"

    @property
    def _identifying_params(self) -> Dict[str, Any]:
        task_val = self.task.value if hasattr(self.task, "value") else str(self.task)
        return {"task": task_val, "model_name": self.model_name, "max_tokens": self.max_tokens}

    def _filter_router_kwargs(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Strip LangChain-internal kwargs while preserving OpenAI `tools`/`tool_choice`."""
        filtered = dict(kwargs)
        filtered.pop("ls_structured_output_format", None)
        return filtered

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Runnable:
        formatted = [convert_to_openai_tool(t) for t in tools]
        return self.bind(tools=formatted, **({"tool_choice": tool_choice} if tool_choice else {}), **kwargs)

    def with_structured_output(
        self,
        schema: Union[Dict[str, Any], Type[BaseModel]],
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable:
        return _StructuredOutputRunnable(chat_model=self, schema=schema, include_raw=include_raw)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = _messages_to_openai_dicts(messages)
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        call_kwargs = self._filter_router_kwargs(kwargs)
        if call_kwargs.get("tools") and hasattr(self.router, "chat_message"):
            res = self.router.chat_message(self.task, payload, max_tokens=max_tokens, **call_kwargs)
            msg = AIMessage(content=res.get("content", ""), tool_calls=res.get("tool_calls", []))
            return ChatResult(generations=[ChatGeneration(message=msg)])
        text = self.router.chat(self.task, payload, max_tokens=max_tokens, **call_kwargs)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        payload = _messages_to_openai_dicts(messages)
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        call_kwargs = self._filter_router_kwargs(kwargs)
        for token in self.router.stream_chat(self.task, payload, max_tokens=max_tokens, **call_kwargs):
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
            if run_manager:
                run_manager.on_llm_new_token(token, chunk=chunk)
            yield chunk

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        payload = _messages_to_openai_dicts(messages)
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        call_kwargs = self._filter_router_kwargs(kwargs)
        if call_kwargs.get("tools") and hasattr(self.router, "achat_message"):
            res = await self.router.achat_message(
                self.task, payload, max_tokens=max_tokens, **call_kwargs
            )
            msg = AIMessage(content=res.get("content", ""), tool_calls=res.get("tool_calls", []))
            return ChatResult(generations=[ChatGeneration(message=msg)])
        text = await self.router.achat(self.task, payload, max_tokens=max_tokens, **call_kwargs)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    async def _astream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> AsyncIterator[ChatGenerationChunk]:
        payload = _messages_to_openai_dicts(messages)
        max_tokens = kwargs.pop("max_tokens", self.max_tokens)
        call_kwargs = self._filter_router_kwargs(kwargs)
        if call_kwargs.get("tools") and hasattr(self.router, "achat_message"):
            res = await self.router.achat_message(
                self.task, payload, max_tokens=max_tokens, **call_kwargs
            )
            tc_chunks = [
                {
                    "name": tc["name"],
                    "args": json.dumps(tc.get("args", {}), ensure_ascii=False),
                    "id": tc.get("id", f"call_{i}"),
                    "index": i,
                }
                for i, tc in enumerate(res.get("tool_calls") or [])
            ]
            msg_chunk = AIMessageChunk(content=res.get("content", ""), tool_call_chunks=tc_chunks)
            yield ChatGenerationChunk(message=msg_chunk)
            return
        async for token in self.router.astream_chat(
            self.task, payload, max_tokens=max_tokens, **call_kwargs
        ):
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=token))
            if run_manager:
                await run_manager.on_llm_new_token(token, chunk=chunk)
            yield chunk


class _StructuredOutputRunnable(RunnableLambda):
    """Structured output wrapper using `parse_llm_json` + Pydantic validation."""

    def __init__(
        self,
        chat_model: BaseChatModel,
        schema: Union[Dict[str, Any], Type[BaseModel]],
        include_raw: bool = False,
    ):
        self._chat_model = chat_model
        self._schema = schema
        self._include_raw = include_raw

        def _sync_parse(input_val: Any) -> Any:
            raw_msg = self._chat_model.invoke(input_val)
            return self._parse_message(raw_msg)

        async def _async_parse(input_val: Any) -> Any:
            raw_msg = await self._chat_model.ainvoke(input_val)
            return self._parse_message(raw_msg)

        super().__init__(func=_sync_parse, afunc=_async_parse)

    def _parse_message(self, raw_msg: Any) -> Any:
        text = raw_msg.content if hasattr(raw_msg, "content") else str(raw_msg)
        data = _extract_json_dict(text)
        if isinstance(self._schema, type) and issubclass(self._schema, BaseModel):
            parsed = self._schema.model_validate(data)
        else:
            parsed = data
        if self._include_raw:
            return {"raw": raw_msg, "parsed": parsed, "parsing_error": None}
        return parsed


def _extract_json_dict(response_text: str) -> Dict[str, Any]:
    text = (response_text or "").strip()
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()
    try:
        loaded = json.loads(text)
        return loaded if isinstance(loaded, dict) else {}
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            loaded = json.loads(text[start : end + 1])
            return loaded if isinstance(loaded, dict) else {}
        raise


class LegacyLLMChatAdapter(BaseChatModel):
    """
    Adapts a LlamaIndex `LLM` or test `MagicMock` (`complete`/`chat`) into
    a LangChain `BaseChatModel`.
    """

    legacy_llm: Any = Field(exclude=True)
    model_name: str = "legacy-adapter"

    model_config = ConfigDict(arbitrary_types_allowed=True)

    @property
    def _llm_type(self) -> str:
        return "autovend-legacy-adapter"

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: Optional[Union[str, Dict[str, Any]]] = None,
        **kwargs: Any,
    ) -> Runnable:
        formatted = [convert_to_openai_tool(t) for t in tools]
        return self.bind(tools=formatted, **({"tool_choice": tool_choice} if tool_choice else {}), **kwargs)

    def with_structured_output(
        self,
        schema: Union[Dict[str, Any], Type[BaseModel]],
        *,
        include_raw: bool = False,
        **kwargs: Any,
    ) -> Runnable:
        return _StructuredOutputRunnable(chat_model=self, schema=schema, include_raw=include_raw)

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        prompt = _messages_to_prompt(messages)
        if hasattr(self.legacy_llm, "complete"):
            resp = self.legacy_llm.complete(prompt)
            text = getattr(resp, "text", str(resp))
        elif hasattr(self.legacy_llm, "invoke"):
            res = self.legacy_llm.invoke(messages)
            text = getattr(res, "content", str(res))
        else:
            text = str(self.legacy_llm(prompt))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    def _stream(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        prompt = _messages_to_prompt(messages)
        if hasattr(self.legacy_llm, "stream_complete"):
            yielded = False
            try:
                for resp in self.legacy_llm.stream_complete(prompt):
                    delta = getattr(resp, "delta", None)
                    if delta is None:
                        delta = getattr(resp, "text", "")
                    if delta:
                        yielded = True
                        chunk = ChatGenerationChunk(message=AIMessageChunk(content=delta))
                        if run_manager:
                            run_manager.on_llm_new_token(delta, chunk=chunk)
                        yield chunk
                if yielded:
                    return
            except Exception:
                pass
        res = self._generate(messages, stop=stop, **kwargs)
        text = res.generations[0].message.content
        if isinstance(text, str) and text:
            yield ChatGenerationChunk(message=AIMessageChunk(content=text))

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[AsyncCallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        return await asyncio.to_thread(self._generate, messages, stop=stop, **kwargs)


def build_langchain_llms(
    router: Optional[HybridRouter] = None,
) -> Tuple[RoutedChatModel, RoutedChatModel]:
    """Build `(extraction_chat_model, generation_chat_model)` backed by `HybridRouter`."""
    from src.llm.router import build_default_router

    resolved_router = router or build_default_router()
    ext_backend, _, _ = resolved_router.backend_for(Task.EXTRACTION)
    gen_backend, _, _ = resolved_router.backend_for(Task.RESPONSE_GENERATION)
    return (
        RoutedChatModel(
            router=resolved_router,
            task=Task.EXTRACTION,
            model_name=getattr(ext_backend, "model", "extraction-routed"),
        ),
        RoutedChatModel(
            router=resolved_router,
            task=Task.RESPONSE_GENERATION,
            model_name=getattr(gen_backend, "model", "generation-routed"),
        ),
    )


def ensure_chat_model(llm: Any) -> BaseChatModel:
    """Return `llm` if already a `BaseChatModel`, else wrap it in `LegacyLLMChatAdapter`."""
    if isinstance(llm, BaseChatModel):
        return llm
    return LegacyLLMChatAdapter(legacy_llm=llm)

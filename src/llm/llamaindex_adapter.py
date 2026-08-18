"""
LlamaIndex-facing view of the hybrid router.

`src/agent` speaks the LlamaIndex `LLM` protocol — `llm.complete(prompt).text` —
and must keep doing so: the architecture guard in
`tests/test_agent_isolation.py` forbids it from importing anything under
`src.llm`, which is what keeps the agent independently testable. So instead of
teaching the agent about routing, the backend hands it two LlamaIndex LLMs that
happen to be routed, one per task.

That split is also why routing stays honest here. The agent decides *what* to
do; whoever constructs it decides *where* each kind of work runs.
"""

from typing import Any, Optional, Sequence

from llama_index.core.base.llms.types import (
    ChatMessage,
    ChatResponse,
    ChatResponseGen,
    CompletionResponse,
    CompletionResponseGen,
    LLMMetadata,
)
from llama_index.core.llms.callbacks import llm_chat_callback, llm_completion_callback
from llama_index.core.llms.custom import CustomLLM

from src.llm.router import HybridRouter, Task

#: Context window advertised to LlamaIndex. Kept at the local server's
#: --max-model-len so a prompt that would overflow the local model is rejected
#: by LlamaIndex rather than silently truncated by vLLM.
DEFAULT_CONTEXT_WINDOW = 8192
DEFAULT_NUM_OUTPUT = 512


class RoutedLLM(CustomLLM):
    """A LlamaIndex LLM whose calls go through `HybridRouter` for one task."""

    router: Any
    task: Any
    context_window: int = DEFAULT_CONTEXT_WINDOW
    num_output: int = DEFAULT_NUM_OUTPUT

    def __init__(
        self,
        router: HybridRouter,
        task: Task,
        context_window: int = DEFAULT_CONTEXT_WINDOW,
        num_output: int = DEFAULT_NUM_OUTPUT,
        **kwargs: Any,
    ):
        super().__init__(
            router=router,
            task=task,
            context_window=context_window,
            num_output=num_output,
            **kwargs,
        )

    @property
    def metadata(self) -> LLMMetadata:
        backend, _, _ = self.router.backend_for(self.task)
        return LLMMetadata(
            context_window=self.context_window,
            num_output=self.num_output,
            model_name=getattr(backend, "model", "routed"),
            is_chat_model=True,
        )

    @llm_completion_callback()
    def complete(self, prompt: str, formatted: bool = False, **kwargs: Any) -> CompletionResponse:
        text = self.router.complete(
            self.task, prompt, max_tokens=kwargs.pop("max_tokens", self.num_output), **kwargs
        )
        return CompletionResponse(text=text)

    def stream_complete(
        self, prompt: str, formatted: bool = False, **kwargs: Any
    ) -> CompletionResponseGen:
        """
        Token-by-token stream. Yields CompletionResponse with delta for each token chunk.
        """
        messages = [{"role": "user", "content": prompt}]
        full_text = ""
        for token in self.router.stream_chat(
            self.task, messages, max_tokens=kwargs.pop("max_tokens", self.num_output), **kwargs
        ):
            full_text += token
            yield CompletionResponse(text=full_text, delta=token)

    @llm_chat_callback()
    def chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponse:
        payload = [{"role": m.role.value, "content": m.content or ""} for m in messages]
        text = self.router.chat(
            self.task, payload, max_tokens=kwargs.pop("max_tokens", self.num_output), **kwargs
        )
        return ChatResponse(message=ChatMessage(role="assistant", content=text))

    @llm_chat_callback()
    def stream_chat(self, messages: Sequence[ChatMessage], **kwargs: Any) -> ChatResponseGen:
        yield self.chat(messages, **kwargs)


def build_agent_llms(router: Optional[HybridRouter] = None) -> tuple:
    """
    Build the (extraction, generation) pair the SalesAgent takes.

    Extraction is schema-constrained and runs on every turn, so it routes local;
    generation is what the customer reads, so it routes cloud.
    """
    from src.llm.router import build_default_router

    router = router or build_default_router()
    return (
        RoutedLLM(router, Task.EXTRACTION),
        RoutedLLM(router, Task.RESPONSE_GENERATION),
    )

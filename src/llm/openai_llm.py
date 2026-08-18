"""
OpenAI-compatible LLM implementation for AutoVend.

Serves both backends the router uses — Groq in the cloud and vLLM locally —
since both expose the OpenAI chat-completions protocol. Only the base URL and
model name differ.

Calls stream by default so that time-to-first-token is *measured* rather than
inferred. TTFT is the metric that justifies routing the control path to a local
model, and total latency is not a substitute for it: a short reply and a long
one can share a TTFT while differing tenfold end to end.
"""

import json
import time
from typing import Any, Dict, List, Optional

import requests
import urllib3
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .base_llm import BaseLLM

# Disable SSL warnings for corporate networks
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DEFAULT_TIMEOUT_S = 60


def extra_body_for_local() -> Dict[str, Any]:
    """
    Request fields the local vLLM server needs but the cloud API rejects.

    Reasoning models (Qwen3 and friends) emit a `<think>...</think>` block
    before the answer unless told otherwise. On the control path that is pure
    waste and actively harmful: the JSON parser has to strip it, TTFT measures
    the first *reasoning* token rather than the first useful one, and a single
    extraction call balloons from ~40 completion tokens to ~185 (measured on
    Qwen3-8B: 1.4s -> 5.5s for the same extraction).

    vLLM forwards unknown keys to the chat template, so this is a no-op for
    models that do not implement `enable_thinking`.
    """
    return {"chat_template_kwargs": {"enable_thinking": False}}


class OpenAILLM(BaseLLM):
    """OpenAI-compatible LLM implementation"""

    def __init__(self, model: str, api_key: str, base_url: Optional[str] = None, **kwargs):
        super().__init__(model, api_key, base_url, **kwargs)
        self.base_url = base_url or "https://api.openai.com/v1"
        self.timeout = kwargs.get("timeout", DEFAULT_TIMEOUT_S)
        # Vendor-specific request fields merged into every payload. Used to turn
        # off reasoning-model chain-of-thought on the local server; see
        # `extra_body_for_local()`.
        self.extra_body: Dict[str, Any] = dict(kwargs.get("extra_body") or {})
        self.session = self._create_session()

        # Populated after every call, read by the telemetry layer.
        self.last_usage: Optional[Dict[str, int]] = None
        self.last_ttft_s: Optional[float] = None

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy"""
        session = requests.Session()
        session.verify = False  # Disable SSL verification for corporate networks

        # Set up retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def complete(self, prompt: str, **kwargs) -> str:
        """Complete a text prompt"""
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, **kwargs)

    def chat(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Chat with a list of messages.

        Streams unless `stream=False` is passed. Streaming costs nothing here —
        the whole reply is still accumulated before returning — and it is the
        only way to observe TTFT.
        """
        self.last_usage = None
        self.last_ttft_s = None

        if kwargs.pop("stream", True):
            return self._chat_streaming(messages, **kwargs)
        return self._chat_blocking(messages, **kwargs)

    # ── request plumbing ──────────────────────────────────────────────

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "AutoVend/1.0",
        }

    def _payload(self, messages: List[Dict[str, str]], **kwargs) -> Dict[str, Any]:
        payload = {
            "messages": messages,
            "model": self.model,
            "max_tokens": kwargs.get("max_tokens", 1000),
            "temperature": kwargs.get("temperature", 0.7),
        }
        payload.update(self.extra_body)
        return payload

    def _chat_blocking(self, messages: List[Dict[str, str]], **kwargs) -> str:
        try:
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(messages, **kwargs),
                timeout=self.timeout,
            )
            if response.status_code != 200:
                raise Exception(f"API Error: {response.status_code} - {response.text}")

            result = response.json()
            self.last_usage = result.get("usage")
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"LLM request failed: {e}")

    def _chat_streaming(self, messages: List[Dict[str, str]], **kwargs) -> str:
        payload = self._payload(messages, **kwargs)
        payload["stream"] = True
        # Both Groq and vLLM emit a final usage-only chunk when asked; without
        # it a streamed call would report no token counts and drop out of the
        # cost accounting entirely.
        payload["stream_options"] = {"include_usage": True}

        started = time.perf_counter()
        chunks: List[str] = []

        try:
            with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
                stream=True,
            ) as response:
                if response.status_code != 200:
                    raise Exception(f"API Error: {response.status_code} - {response.text}")

                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[len("data: ") :]
                    if data == "[DONE]":
                        break

                    event = json.loads(data)
                    if event.get("usage"):
                        self.last_usage = event["usage"]

                    for choice in event.get("choices", []):
                        piece = (choice.get("delta") or {}).get("content")
                        if piece:
                            if self.last_ttft_s is None:
                                self.last_ttft_s = time.perf_counter() - started
                            chunks.append(piece)

            return "".join(chunks)
        except Exception as e:
            raise Exception(f"LLM request failed: {e}")

    def chat_stream_tokens(self, messages: List[Dict[str, str]], **kwargs):
        """Yield token chunks as they arrive from the API stream."""
        payload = self._payload(messages, **kwargs)
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}

        started = time.perf_counter()

        try:
            with self.session.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
                stream=True,
            ) as response:
                if response.status_code != 200:
                    raise Exception(f"API Error: {response.status_code} - {response.text}")

                for line in response.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data: "):
                        continue
                    data = line[len("data: ") :]
                    if data == "[DONE]":
                        break

                    event = json.loads(data)
                    if event.get("usage"):
                        self.last_usage = event["usage"]

                    for choice in event.get("choices", []):
                        piece = (choice.get("delta") or {}).get("content")
                        if piece:
                            if self.last_ttft_s is None:
                                self.last_ttft_s = time.perf_counter() - started
                            yield piece
        except Exception as e:
            raise Exception(f"LLM request failed: {e}")

    def is_available(self) -> bool:
        """Check if the LLM service is available"""
        try:
            response = self.session.get(
                f"{self.base_url}/models", headers=self._headers(), timeout=10
            )
            return response.status_code == 200
        except Exception:
            return False

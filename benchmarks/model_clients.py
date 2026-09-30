from __future__ import annotations
"""Pluggable model clients for KesslerBench.

Every client exposes one method: chat(messages, tools) -> ChatResult, where
`tools` is a list of {"name", "description", "parameters"} (JSON-schema style,
OpenAI function-calling shape) and ChatResult carries any assistant text, zero
or more requested tool calls, and token usage when the provider reports it.

Two real HTTP-backed clients are provided:
  - GeminiClient: Google Generative Language REST API (generateContent, with
    functionDeclarations/functionCall — translated to/from the OpenAI-ish
    shape used everywhere else in this runner).
  - OpenAICompatibleClient: any REST endpoint that speaks the OpenAI
    /chat/completions tool-calling contract (NVIDIA NIM, OpenRouter, and
    OpenAI itself all qualify).

A MockClient is included for offline plumbing tests (no network, scripted
responses) — used to prove the hook-wiring and scoring logic work before ever
spending a real API call.
"""
import json
import time
import urllib.request
import urllib.error
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class ChatResult:
    text: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    raw: dict | None = None


def _http_post_json(url: str, headers: dict, payload: dict, timeout: int = 120, max_retries: int = 3) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={**headers, "Content-Type": "application/json"}, method="POST")
    last_err = None
    for attempt in range(max_retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            last_err = RuntimeError(f"HTTP {exc.code} from {url}: {body[:2000]}")
            if exc.code in (429, 500, 502, 503, 504, 529) and attempt < max_retries:
                delay = 20 * (attempt + 1) if exc.code in (429, 529) else 5 * (attempt + 1)
                time.sleep(delay)
                continue
            raise last_err from None
        except (urllib.error.URLError, TimeoutError, Exception) as exc:
            last_err = RuntimeError(f"Network error from {url}: {exc}")
            if attempt < max_retries:
                time.sleep(5 * (attempt + 1))
                continue
            raise last_err from None
    if last_err:
        raise last_err
    raise RuntimeError("Unexpected failure in _http_post_json")


class OpenAICompatibleClient:
    """NVIDIA NIM, OpenRouter, OpenAI, or any /v1/chat/completions-compatible endpoint."""

    def __init__(self, base_url: str, api_key: str, model: str, extra_headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.extra_headers = extra_headers or {}

    def chat(self, messages: list[dict], tools: list[dict]) -> ChatResult:
        oa_tools = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""), "parameters": t.get("parameters", {})}} for t in tools]
        formatted_messages = []
        for m in messages:
            m_copy = dict(m)
            if m_copy.get("role") == "assistant" and "tool_call" in m_copy:
                tc_info = m_copy.pop("tool_call")
                tc_id = tc_info.get("id") or "call_0"
                m_copy["tool_calls"] = [{
                    "id": tc_id,
                    "type": "function",
                    "function": {"name": tc_info.get("name", ""), "arguments": "{}"}
                }]
            elif m_copy.get("role") == "tool":
                if not m_copy.get("tool_call_id"):
                    m_copy["tool_call_id"] = "call_0"
            formatted_messages.append(m_copy)
        payload = {"model": self.model, "messages": formatted_messages, "tools": oa_tools, "tool_choice": "auto", "temperature": 0}
        headers = {"Authorization": f"Bearer {self.api_key}", **self.extra_headers}
        data = _http_post_json(f"{self.base_url}/chat/completions", headers, payload)
        choice = (data.get("choices") or [{}])[0]
        msg = choice.get("message") or {}
        calls = []
        for tc in (msg.get("tool_calls") or []):
            fn = tc.get("function", {})
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except Exception:
                args = {}
            calls.append(ToolCall(id=tc.get("id", ""), name=fn.get("name", ""), args=args))
        usage = data.get("usage") or {}
        return ChatResult(text=msg.get("content") or "", tool_calls=calls,
                           input_tokens=int(usage.get("prompt_tokens") or 0),
                           output_tokens=int(usage.get("completion_tokens") or 0), raw=data)


class GeminiClient:
    """Google Generative Language API (generateContent), free-tier compatible."""

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    def chat(self, messages: list[dict], tools: list[dict]) -> ChatResult:
        contents = []
        system_text = ""
        for m in messages:
            role = m["role"]
            if role == "system":
                system_text += (m["content"] + "\n")
                continue
            gem_role = "model" if role == "assistant" else "user"
            if role == "tool":
                contents.append({"role": "user", "parts": [{"functionResponse": {"name": m.get("name", ""), "response": {"result": m["content"]}}}]})
                continue
            contents.append({"role": gem_role, "parts": [{"text": m["content"]}]})
        function_decls = [{"name": t["name"], "description": t.get("description", ""), "parameters": t.get("parameters", {})} for t in tools]
        payload = {"contents": contents, "tools": [{"functionDeclarations": function_decls}], "generationConfig": {"temperature": 0}}
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}
        url = f"{self.base_url}/models/{self.model}:generateContent?key={self.api_key}"
        data = _http_post_json(url, {}, payload)
        cand = (data.get("candidates") or [{}])[0]
        parts = ((cand.get("content") or {}).get("parts")) or []
        text = ""
        calls = []
        for i, p in enumerate(parts):
            if "text" in p:
                text += p["text"]
            elif "functionCall" in p:
                fc = p["functionCall"]
                calls.append(ToolCall(id=f"call_{i}", name=fc.get("name", ""), args=fc.get("args", {}) or {}))
        usage = data.get("usageMetadata") or {}
        return ChatResult(text=text, tool_calls=calls,
                           input_tokens=int(usage.get("promptTokenCount") or 0),
                           output_tokens=int(usage.get("candidatesTokenCount") or 0), raw=data)


class MockClient:
    """Scripted, offline client for plumbing tests. `script` is a list of
    ChatResult-shaped dicts consumed one per call(); the last one repeats."""

    def __init__(self, script: list[dict]):
        self.script = script
        self.i = 0

    def chat(self, messages: list[dict], tools: list[dict]) -> ChatResult:
        step = self.script[min(self.i, len(self.script) - 1)]
        self.i += 1
        calls = [ToolCall(id=c.get("id", f"c{i}"), name=c["name"], args=c.get("args", {})) for i, c in enumerate(step.get("tool_calls", []))]
        return ChatResult(text=step.get("text", ""), tool_calls=calls, input_tokens=10, output_tokens=10)


def build_client(provider: str, model: str, api_key: str):
    if provider == "gemini":
        return GeminiClient(api_key=api_key, model=model)
    if provider == "nvidia":
        return OpenAICompatibleClient(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key, model=model)
    if provider == "openrouter":
        return OpenAICompatibleClient(base_url="https://openrouter.ai/api/v1", api_key=api_key, model=model,
                                       extra_headers={"HTTP-Referer": "https://github.com/marcoskohler-creator/kessler_protocol", "X-Title": "KesslerBench"})
    raise ValueError(f"unknown provider: {provider}")

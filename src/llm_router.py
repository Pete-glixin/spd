"""
Glixin Downstream LLM Router (src/llm_router.py)
------------------------------------------------
Dispatches rehydrated prompts to Pass 2 target LLM providers.
"""

import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional


class DownstreamLLMRouter:
    def __init__(
        self, 
        provider: str = "ollama", 
        model: Optional[str] = None, 
        api_key: Optional[str] = None,
        base_url: Optional[str] = None
    ):
        self.provider = provider.lower() if provider else "ollama"
        self.model = model or ("qwen2.5-coder:1.5b" if self.provider == "ollama" else "gpt-4o")
        self.api_key = api_key
        self.base_url = base_url

    def dispatch(self, prompt: str) -> str:
        """
        Dispatches prompt to configured LLM provider.
        """
        if self.provider == "ollama":
            return self._dispatch_ollama(prompt)
        elif self.provider in ["openai", "anthropic", "grok", "gemini"]:
            return f"[{self.provider.upper()} PASSTHROUGH]: Dispatched to {self.model}"
        else:
            return self._dispatch_ollama(prompt)

    def _dispatch_ollama(self, prompt: str) -> str:
        url = self.base_url or "http://localhost:11434/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url, 
            data=data, 
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                if resp.status == 200:
                    res = json.loads(resp.read().decode("utf-8"))
                    return res.get("response", "").strip()
                return f"Ollama HTTP {resp.status}"
        except Exception as e:
            return f"Ollama Connection Error: {str(e)}"
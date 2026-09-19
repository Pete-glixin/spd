import os
import json
import urllib.request
import urllib.error

class DownstreamLLMRouter:
    def __init__(self, provider="ollama", model=None, api_key=None, base_url=None):
        self.provider = provider.lower()
        self.model = model
        self.api_key = api_key
        self.base_url = base_url

    def dispatch(self, prompt: str) -> dict:
        """Routes the dehydrated prompt to the selected LLM provider using stdlib urllib."""
        if self.provider == "anthropic":
            return self._call_anthropic(prompt)
        elif self.provider == "grok":
            return self._call_openai_compatible(
                prompt, 
                endpoint=self.base_url or "https://api.x.ai/v1/chat/completions",
                default_model="grok-2-latest",
                env_key_var="XAI_API_KEY"
            )
        elif self.provider == "gemini":
            return self._call_gemini(prompt)
        elif self.provider == "openai":
            return self._call_openai_compatible(
                prompt,
                endpoint=self.base_url or "https://api.openai.com/v1/chat/completions",
                default_model="gpt-4o",
                env_key_var="OPENAI_API_KEY"
            )
        else: # Default: Ollama Local
            return self._call_ollama(prompt)

    def _call_anthropic(self, prompt: str) -> dict:
        key = self.api_key or os.getenv("ANTHROPIC_API_KEY")
        if not key:
            return {"error": "Missing API Key for Anthropic. Set ANTHROPIC_API_KEY environment variable or use --api-key."}

        url = self.base_url or "https://api.anthropic.com/v1/messages"
        model = self.model or "claude-3-5-sonnet-20241022"

        payload = {
            "model": model,
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": prompt}]
        }

        headers = {
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                content = res_data.get("content", [{}])[0].get("text", "")
                return {
                    "text": content,
                    "usage": res_data.get("usage", {})
                }
        except urllib.error.HTTPError as e:
            return {"error": f"Anthropic HTTP {e.code}: {e.read().decode('utf-8')}"}
        except Exception as e:
            return {"error": f"Anthropic connection error: {str(e)}"}

    def _call_gemini(self, prompt: str) -> dict:
        key = self.api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            return {"error": "Missing API Key for Gemini. Set GEMINI_API_KEY environment variable or use --api-key."}

        model = self.model or "gemini-1.5-flash"
        url = self.base_url or f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"

        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

        headers = {"Content-Type": "application/json"}

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                candidates = res_data.get("candidates", [{}])
                parts = candidates[0].get("content", {}).get("parts", [{}])
                text = parts[0].get("text", "")
                return {
                    "text": text,
                    "usage": res_data.get("usageMetadata", {})
                }
        except urllib.error.HTTPError as e:
            return {"error": f"Gemini HTTP {e.code}: {e.read().decode('utf-8')}"}
        except Exception as e:
            return {"error": f"Gemini connection error: {str(e)}"}

    def _call_openai_compatible(self, prompt, endpoint, default_model, env_key_var):
        key = self.api_key or os.getenv(env_key_var) or os.getenv("OPENAI_API_KEY")
        if not key:
            return {"error": f"Missing API Key for {self.provider}. Set {env_key_var} environment variable or use --api-key."}

        payload = {
            "model": self.model or default_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        
        req = urllib.request.Request(
            endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return {
                    "text": res_data["choices"][0]["message"]["content"],
                    "usage": res_data.get("usage", {})
                }
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}: {e.read().decode('utf-8')}"}
        except Exception as e:
            return {"error": f"Connection error: {str(e)}"}

    def _call_ollama(self, prompt):
        url = self.base_url or "http://localhost:11434/api/generate"
        payload = {
            "model": self.model or "llama3.3",
            "prompt": prompt,
            "stream": False
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        try:
            with urllib.request.urlopen(req) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return {"text": res_data.get("response", ""), "usage": {}}
        except Exception as e:
            return {"error": f"Ollama connection failed: {str(e)}"}
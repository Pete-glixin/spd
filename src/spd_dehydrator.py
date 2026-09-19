"""
Glixin Semiotic Prompt Dehydrator (src/spd_dehydrator.py)
---------------------------------------------------------
Phase 2 Universal Semiotic Compiler.
Dehydrates conversational prompts via AWS Lambda (Glixin_SPD_Orchestrator)
into structured Peircean Triadic Graphs:
  - Firstness: Operational Intent / Core Verb Action
  - Secondness: Target Entities, Context, & Data Pointers
  - Thirdness: Governing Rules, Schemas, & Constraints
"""

import sys
import os
import re
import json
import time
import hashlib
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional
from enum import Enum


LAMBDA_ORCHESTRATOR_URL = "https://cxckt5nvxmitev5oidwhx3c2uq0akykp.lambda-url.us-east-1.on.aws/"


class SemioticCategory(Enum):
    FIRSTNESS_INTENT = "Firstness"    # F: Conceptual/Operational Intent
    SECONDNESS_FACT = "Secondness"    # S: Empirical Fact / Target Entity / Data
    THIRDNESS_RULE = "Thirdness"      # T: Governing Schema / Output Constraint


class TriadicSchema:
    """
    Structured container for a parsed Peircean Triad.
    """
    def __init__(
        self,
        intent: str,
        facts: List[str],
        rules: List[str],
        raw_prompt: str = ""
    ):
        self.intent = intent.strip() if intent else ""
        self.facts = [f.strip() for f in facts if f and f.strip()]
        self.rules = [r.strip() for r in rules if r and r.strip()]
        self.raw_prompt = raw_prompt

    def to_dict(self) -> Dict[str, Any]:
        return {
            "firstness_intent": self.intent,
            "secondness_facts": self.facts,
            "thirdness_rules": self.rules
        }

    def rehydrate_for_llm(self) -> str:
        """
        Reconstructs triadic components into a minimal core prompt.
        """
        parts = []
        if self.intent:
            clean_intent = re.sub(r'\[(CONTEXT|CONSTRAINTS)\]:\s*None', '', self.intent, flags=re.IGNORECASE).strip()
            clean_intent = re.sub(r'^\[INTENT\]:\s*', '', clean_intent, flags=re.IGNORECASE).strip()
            if clean_intent:
                parts.append(f"Task: {clean_intent}")

        valid_facts = [f for f in self.facts if f.lower() not in ["none", "n/a", "null", ""]]
        if valid_facts:
            parts.append(f"Context: {' | '.join(valid_facts)}")

        valid_rules = [r for r in self.rules if r.lower() not in ["none", "n/a", "null", ""]]
        if valid_rules:
            parts.append(f"Rules: {' | '.join(valid_rules)}")

        return " | ".join(parts) if parts else self.intent


def estimate_tokens(text: str) -> int:
    """Estimates token count (~1.3 tokens per word)."""
    if not text:
        return 0
    return int(len(text.split()) * 1.3)


class SemioticPromptDehydrator:
    """
    Client interface for the Glixin Semiotic Prompt Dehydrator.
    Routes Pass 1 dehydration directly to the AWS Lambda Orchestrator endpoint.
    """
    def __init__(self, slm_endpoint: Optional[str] = None):
        self.endpoint_url = slm_endpoint or LAMBDA_ORCHESTRATOR_URL

    def dehydrate(
        self, 
        raw_prompt: str, 
        use_slm: bool = True, 
        router: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
        value_share_fraction: float = 0.15,
        customer_id: str = "LOCAL_CLI_DEMO"
    ) -> Dict[str, Any]:
        """
        Primary entry point. Sends raw prompt to AWS Lambda Orchestrator over HTTPS
        and formats the response to match local metrics & schema expectations.
        """
        start_time = time.time()
        prompt_hash = hashlib.sha256(raw_prompt.encode('utf-8')).hexdigest()[:16]

        payload = {
            "raw_prompt": raw_prompt,
            "customer_id": customer_id
        }

        req = urllib.request.Request(
            self.endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as response:
                if response.status == 200:
                    res_data = json.loads(response.read().decode("utf-8"))
                    
                    dehydrated_core = res_data.get("dehydrated_prompt") or res_data.get("dehydrated_core") or raw_prompt
                    metrics = res_data.get("metrics", {})
                    schema_raw = res_data.get("triadic_schema", {})

                    # Reconstruct TriadicSchema object
                    intent = schema_raw.get("firstness_intent") or schema_raw.get("intent") or ""
                    facts = schema_raw.get("secondness_facts") or schema_raw.get("facts") or []
                    rules = schema_raw.get("thirdness_rules") or schema_raw.get("rules") or []
                    schema = TriadicSchema(intent=intent, facts=facts, rules=rules, raw_prompt=raw_prompt)

                    raw_tokens = metrics.get("raw_token_count", estimate_tokens(raw_prompt))
                    dehydrated_tokens = metrics.get("dehydrated_token_count", estimate_tokens(dehydrated_core))
                    llm_tokens_saved = max(0, raw_tokens - dehydrated_tokens)
                    reduction_pct = round((llm_tokens_saved / max(1, raw_tokens)) * 100, 1)

                    ggt_from_savings = round(llm_tokens_saved * value_share_fraction, 2)
                    ggt_charged = metrics.get("ggt_charged", int(round(1 + ggt_from_savings)))

                    elapsed_ms = round((time.time() - start_time) * 1000, 2)

                    return {
                        "status": "SPD_SUCCESS",
                        "prompt_hash": prompt_hash,
                        "latency_ms": elapsed_ms,
                        "metrics": {
                            "raw_token_count": raw_tokens,
                            "dehydrated_token_count": dehydrated_tokens,
                            "llm_tokens_saved": llm_tokens_saved,
                            "reduction_pct": f"{reduction_pct}%",
                            "ggt_base_fee": 1,
                            "ggt_value_share": ggt_from_savings,
                            "ggt_charged": ggt_charged
                        },
                        "triadic_schema": schema.to_dict(),
                        "dehydrated_core": dehydrated_core,
                        "dehydrated_prompt": dehydrated_core
                    }
                else:
                    err_msg = response.read().decode('utf-8')
                    return self._error_fallback(raw_prompt, prompt_hash, start_time, f"Lambda HTTP {response.status}: {err_msg}")

        except urllib.error.HTTPError as e:
            err_msg = e.read().decode('utf-8') if e.fp else str(e)
            return self._error_fallback(raw_prompt, prompt_hash, start_time, f"Lambda HTTP {e.code}: {err_msg}")
        except Exception as e:
            return self._error_fallback(raw_prompt, prompt_hash, start_time, f"Orchestrator connection failed: {str(e)}")

    def _error_fallback(self, raw_prompt: str, prompt_hash: str, start_time: float, err_msg: str) -> Dict[str, Any]:
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        raw_tokens = estimate_tokens(raw_prompt)
        schema = TriadicSchema(intent=raw_prompt, facts=[], rules=[], raw_prompt=raw_prompt)
        return {
            "status": "SPD_ERROR",
            "prompt_hash": prompt_hash,
            "latency_ms": elapsed_ms,
            "error_message": err_msg,
            "metrics": {
                "raw_token_count": raw_tokens,
                "dehydrated_token_count": raw_tokens,
                "llm_tokens_saved": 0,
                "reduction_pct": "0%",
                "ggt_base_fee": 0,
                "ggt_value_share": 0,
                "ggt_charged": 0
            },
            "triadic_schema": schema.to_dict(),
            "dehydrated_core": raw_prompt,
            "dehydrated_prompt": raw_prompt
        }


# Alias for backwards compatibility
SPDDehydrator = SemioticPromptDehydrator

# Module instance for easy import
spd_engine = SemioticPromptDehydrator()
dehydrate_prompt = spd_engine.dehydrate
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


LAMBDA_ORCHESTRATOR_URL = "https://cxckt5nvxmitev5oidwhx3c2uq0akykp.lambda-url.us-east-1.on.aws/"


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
    def __init__(self, endpoint_url: Optional[str] = None):
        self.endpoint_url = endpoint_url or LAMBDA_ORCHESTRATOR_URL

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
        Primary entry point. Sends raw prompt to AWS Lambda Orchestrator over HTTPS.
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
                    
                    dehydrated_core = res_data.get("dehydrated_prompt", raw_prompt)
                    metrics = res_data.get("metrics", {})
                    schema_dict = res_data.get("triadic_schema", {})

                    elapsed_ms = round((time.time() - start_time) * 1000, 2)

                    return {
                        "status": "SPD_SUCCESS",
                        "prompt_hash": prompt_hash,
                        "latency_ms": elapsed_ms,
                        "metrics": metrics,
                        "triadic_schema": schema_dict,
                        "dehydrated_core": dehydrated_core
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
            "triadic_schema": {
                "firstness_intent": "",
                "secondness_facts": [],
                "thirdness_rules": []
            },
            "dehydrated_core": raw_prompt
        }


# Module instance for easy import
spd_engine = SemioticPromptDehydrator()
dehydrate_prompt = spd_engine.dehydrate
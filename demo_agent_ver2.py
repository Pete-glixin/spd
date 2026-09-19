"""
Glixin SPD Benchmark Agent v2 (demo_agent_ver2.py)
--------------------------------------------------
Tests Pass 1 dehydration against a heavily bloated, multi-paragraph prompt.
Highlights massive token compression ratios, context retention, and net latency savings.
"""

import json
import subprocess
import sys
import time
import urllib.request

# Local Ollama endpoint for Pass 2 execution
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5-coder:1.5b"

# Heavily bloated prompt payload (Corporate email + log dump + conversational filler)
BLOATED_RAW_PROMPT = """Good morning team,

I hope you are all having a wonderful and productive week so far! I am reaching out to you today because we have run into a critical operational issue that requires urgent attention from the engineering on-call engineer. 

First off, let me say how much we appreciate your hard work on the recent Q3 backend optimizations. However, early this morning around 04:15 UTC, our automated monitoring systems flagged an anomaly in the primary payment gateway microservice (payment-svc-v2). Customers in the US-East region are reporting intermittent 504 Gateway Timeouts when attempting to complete checkout transactions using saved credit card profiles.

Upon reviewing the initial telemetry and database logs, our DevOps squad identified that the connection pool for the primary PostgreSQL instance (db-prod-east-01) reached 100% capacity due to unclosed database handles in the authorization worker thread pool. 

Could you please perform an immediate audit on the connection pool configuration for db-prod-east-01, scale up the max_connections limit from 200 to 500 as a temporary mitigation, and deploy a hotfix patch to release stale handles? Please make sure to output your status report in a clean Markdown table format with columns for Component, Action Taken, and Current Status.

Thank you so much for your quick response and dedication to keeping our systems running smoothly!

Best regards,
Operations Support Team"""


def call_ollama(prompt: str) -> dict:
    """Sends prompt payload directly to local Ollama instance."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        OLLAMA_URL, 
        data=data, 
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    start_time = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            elapsed = round(time.time() - start_time, 2)
            if resp.status == 200:
                res = json.loads(resp.read().decode("utf-8"))
                return {
                    "response": res.get("response", "").strip(),
                    "eval_count": res.get("eval_count", 0),
                    "prompt_eval_count": res.get("prompt_eval_count", 0),
                    "latency_sec": elapsed
                }
            return {"error": f"HTTP {resp.status}", "latency_sec": elapsed}
    except Exception as e:
        return {"error": str(e), "latency_sec": round(time.time() - start_time, 2)}


def run_spd_cli(raw_prompt: str) -> dict:
    """Invokes main.py directly to bypass binary compilation issues."""
    start_time = time.time()
    
    # Clean whitespace and line breaks into a single continuous stream
    clean_stdin_input = " ".join(raw_prompt.split())
    
    try:
        # Run main.py using Python directly
        result = subprocess.run(
            [sys.executable, "main.py"],
            input=clean_stdin_input,
            text=True,
            capture_output=True,
            timeout=30
        )
        elapsed_ms = round((time.time() - start_time) * 1000, 2)
        
        if result.returncode == 0 and result.stdout.strip():
            res_json = json.loads(result.stdout)
            res_json["spd_cli_latency_ms"] = elapsed_ms
            return res_json
        else:
            error_msg = result.stderr.strip() or "No output returned from main.py"
            print(f"⚠️ CLI Execution Warning: {error_msg}")
            return {"status": "SPD_ERROR", "error": error_msg, "spd_cli_latency_ms": elapsed_ms}
    except Exception as e:
        return {"status": "SPD_ERROR", "error": str(e), "spd_cli_latency_ms": round((time.time() - start_time) * 1000, 2)}


def main():
    print("\n" + "="*70)
    print("      HEAVY BLOAT BENCHMARK: RAW PROMPT vs. SPD DEHYDRATED PROMPT")
    print("="*70 + "\n")

    # Pipeline 1: Raw Bloated Prompt directly to SLM
    print("Running Pipeline 1: Raw Bloated Prompt...")
    p1_res = call_ollama(BLOATED_RAW_PROMPT)

    # Pipeline 2: Run Pass 1 Dehydration then send Dehydrated Prompt to SLM
    print("Executing Pass 1 Dehydration on Bloated Prompt...")
    spd_out = run_spd_cli(BLOATED_RAW_PROMPT)
    
    # Prioritize dehydrated_prompt to capture full Task | Context | Rules schema
    dehydrated_prompt = spd_out.get("dehydrated_prompt") or spd_out.get("dehydrated_core") or BLOATED_RAW_PROMPT
    
    print("Running Pipeline 2: SPD Dehydrated Prompt...")
    p2_res = call_ollama(dehydrated_prompt)

    # Calculate metrics
    p1_in_tokens = p1_res.get("prompt_eval_count", 0)
    p2_in_tokens = p2_res.get("prompt_eval_count", 0)
    tokens_saved = max(0, p1_in_tokens - p2_in_tokens)
    pct_reduction = round((tokens_saved / max(1, p1_in_tokens)) * 100, 1)

    # Pull latency from response JSON (checking top-level and nested metrics keys)
    metrics = spd_out.get("metrics", {}) if isinstance(spd_out.get("metrics"), dict) else {}
    
    candidates = [
        spd_out.get("latency_ms"),
        metrics.get("latency_ms"),
        metrics.get("lambda_overhead_ms"),
        spd_out.get("spd_cli_latency_ms")
    ]
    
    # Select the first candidate that isn't None
    aws_api_latency = next((val for val in candidates if val is not None), "N/A")

    print("\n" + "-"*70)
    print("                     BENCHMARK RESULTS SUMMARY")
    print("-"*70)
    print(f"🌐 AWS Lambda API Latency       : {aws_api_latency} ms")
    print(f"⚡ Total Pass 1 Execution Time  : {spd_out.get('spd_cli_latency_ms', 0)} ms")
    print(f"📉 Input Token Reduction       : {p1_in_tokens} -> {p2_in_tokens} ({pct_reduction}% reduction)")
    print(f"💾 Total LLM Tokens Saved      : {tokens_saved} tokens")
    print("-"*70)

    print("\n" + "="*70)
    print(" PIPELINE 1: RAW BLOATED PROMPT PAYLOAD")
    print("="*70)
    print(f" Input Tokens  : {p1_in_tokens}")
    print(f" Output Tokens : {p1_res.get('eval_count', 0)}")
    print(f" SLM Latency   : {p1_res.get('latency_sec', 0)}s")
    print("-" * 70)
    print(" SLM OUTPUT:")
    print(p1_res.get("response", ""))

    print("\n" + "="*70)
    print(" PIPELINE 2: SPD DEHYDRATED PROMPT PAYLOAD")
    print("="*70)
    print(f" Input Tokens  : {p2_in_tokens}")
    print(f" Output Tokens : {p2_res.get('eval_count', 0)}")
    print(f" SLM Latency   : {p2_res.get('latency_sec', 0)}s")
    print("-" * 70)
    print(" DEHYDRATED PAYLOAD SENT TO SLM:")
    print(f" {dehydrated_prompt}")
    print("-" * 70)
    print(" SLM OUTPUT:")
    print(p2_res.get("response", ""))
    print("="*70 + "\n")


if __name__ == "__main__":
    main()
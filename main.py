"""
Glixin Semiotic Prompt Dehydrator (SPD) - Main CLI Entrypoint
-----------------------------------------------------------
"""

import argparse
import sys
import json
import os
import urllib.request
import urllib.error
import socket
import base64
import sqlite3
from pathlib import Path

# Import core modules from src/ and local worker
from src.llm_router import DownstreamLLMRouter
from src.spd_dehydrator import SemioticPromptDehydrator
import audit_worker


def parse_args():
    parser = argparse.ArgumentParser(
        description="Glixin Semiotic Prompt Dehydrator (SPD) - Pass 1 Compressor",
        epilog="Be Verbose Without the Bill! | https://glixin.com"
    )

    # Input options
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-p", "--prompt", help="Raw prompt string to dehydrate.")
    group.add_argument("-f", "--file", help="Path to a text file containing the raw prompt.")

    # Config & Output options
    parser.add_argument("-c", "--config", help="Path to license and router config JSON.")
    parser.add_argument("-o", "--output", choices=["text", "json"], default="json",
                        help="Output format: 'json' (includes metrics) or 'text' (dehydrated prompt only).")

    # Provider & Routing options
    parser.add_argument("--provider", choices=["openai", "anthropic", "grok", "gemini", "ollama"], default="anthropic",
                        help="Target LLM provider for passthrough or cost metrics.")
    parser.add_argument("--model", help="Specific model name (e.g. gpt-4o, claude-3.5-sonnet).")
    parser.add_argument("--api-key", help="Override API key for the selected provider.")
    parser.add_argument("--passthrough", action="store_true", help="Execute Pass 2 target LLM after Pass 1 dehydration.")

    return parser.parse_args()


def flush_offline_queue(url):
    """Flushes queued offline usage reports to the backend."""
    appdata_dir = Path(os.path.expanduser("~/AppData/Roaming/Glixin/SPD"))
    db_path = appdata_dir / "spd_wallet.db"
    
    if not db_path.exists():
        return

    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT id, customer_id, tokens_used FROM offline_queue")
        rows = cur.fetchall()

        for row in rows:
            event_id, customer_id, tokens = row
            payload = json.dumps({"customer_id": customer_id, "tokens_used": tokens}).encode('utf-8')
            req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'}, method='POST')
            try:
                with urllib.request.urlopen(req, timeout=2) as resp:
                    if resp.status == 200:
                        cur.execute("DELETE FROM offline_queue WHERE id = ?", (event_id,))
            except Exception:
                break  # Stop processing if connection drops mid-flush

        conn.commit()
        conn.close()
    except Exception:
        pass


def report_usage_to_backend(tokens_used):
    """Reports usage to backend. Queues locally in AppData if offline and flushes on success."""
    appdata_dir = Path(os.path.expanduser("~/AppData/Roaming/Glixin/SPD"))
    appdata_dir.mkdir(parents=True, exist_ok=True)
    
    license_path = appdata_dir / "license.json"
    
    if not license_path.exists():
        return  
        
    try:
        with open(license_path, "r") as f:
            license_data = json.load(f)
        customer_id = license_data.get("customer_id")
    except Exception:
        return

    if not customer_id:
        return  

    db_path = appdata_dir / "spd_wallet.db"

    def init_queue():
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS offline_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id TEXT,
                    tokens_used INT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception:
            pass

    init_queue()

    payload = {
        "customer_id": customer_id,
        "tokens_used": tokens_used
    }
    data = json.dumps(payload).encode('utf-8')
    url = "http://127.0.0.1:5000/report-usage"
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={'Content-Type': 'application/json'}, 
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=2) as response:
            if response.status == 200:
                flush_offline_queue(url)
    except (urllib.error.URLError, socket.timeout, Exception):
        try:
            conn = sqlite3.connect(db_path)
            cur = conn.cursor()
            cur.execute("INSERT INTO offline_queue (customer_id, tokens_used) VALUES (?, ?)", (customer_id, tokens_used))
            conn.commit()
            conn.close()
        except Exception:
            pass


def main():
    args = parse_args()

    raw_prompt = ""
    if args.prompt:
        raw_prompt = args.prompt.strip()
    elif args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: Input file '{args.file}' not found.", file=sys.stderr, flush=True)
            sys.exit(1)
        raw_prompt = file_path.read_text(encoding="utf-8").strip()
    elif not sys.stdin.isatty():
        raw_prompt = sys.stdin.read().strip()

    if not raw_prompt:
        print("Error: No prompt provided. Use --prompt, --file, or pipe input via STDIN.", file=sys.stderr, flush=True)
        sys.exit(1)

    # CRITICAL FIX: Sanitize internal newlines/CRLF to clean space-separated text before transmission
    raw_prompt = " ".join(raw_prompt.split())


    # Initialize dehydrator pointing directly to AWS Lambda Function URL
    dehydrator = SemioticPromptDehydrator()
    res = dehydrator.dehydrate(raw_prompt)
    execution_mode = "AWS_LAMBDA_BEDROCK"

    dehydrated_text = res.get("dehydrated_core") or res.get("dehydrated_prompt") or raw_prompt
    prompt_hash = res.get("prompt_hash", "00000000")
    metrics = res.get("metrics", {})

    raw_tokens = metrics.get("raw_token_count", len(raw_prompt) // 4)
    dehydrated_tokens = metrics.get("dehydrated_token_count", len(dehydrated_text) // 4)
    ggt_charged = metrics.get("ggt_charged", 1)

    # Execute audit worker logging
    payload_dict = {
        "prompt_hash": prompt_hash,
        "raw_tokens": raw_tokens,
        "dehydrated_tokens": dehydrated_tokens
    }
    b64_payload = base64.b64encode(json.dumps(payload_dict).encode('utf-8')).decode('utf-8')
    try:
        settlement_res = audit_worker.execute_audit(b64_payload)
        if isinstance(settlement_res, dict) and "ggt_charged" in settlement_res:
            ggt_charged = settlement_res["ggt_charged"]
    except Exception as e:
        audit_worker.log_status(f"AUDIT EXECUTION ERROR: {e}")

    metrics["ggt_charged"] = ggt_charged
    report_usage_to_backend(ggt_charged)

    if args.passthrough:
        router = DownstreamLLMRouter(provider=args.provider, model=args.model, api_key=args.api_key)
        llm_response = router.dispatch(dehydrated_text)
        result = {
            "status": "SUCCESS",
            "execution_mode": execution_mode,
            "passthrough": True,
            "provider": args.provider,
            "model": args.model or "default",
            "dehydrated_prompt": dehydrated_text,
            "dehydrated_core": dehydrated_text,
            "llm_response": llm_response,
            "metrics": metrics
        }
    else:
        result = {
            "status": res.get("status", "SPD_SUCCESS"),
            "execution_mode": execution_mode,
            "prompt_hash": prompt_hash,
            "metrics": {
                "raw_character_count": len(raw_prompt),
                "dehydrated_character_count": len(dehydrated_text),
                "raw_token_count": raw_tokens,
                "dehydrated_token_count": dehydrated_tokens,
                "llm_tokens_saved": metrics.get("llm_tokens_saved", max(0, raw_tokens - dehydrated_tokens)),
                "compression_ratio": metrics.get("reduction_pct", "0.0%"),
                "ggt_charged": ggt_charged,
                "audit_status": "SETTLED"
            },
            "triadic_schema": res.get("triadic_schema", {}),
            "dehydrated_prompt": dehydrated_text,
            "dehydrated_core": dehydrated_text,
            "headers": {
                "X-Glixin-SPD-Executed": "true"
            }
        }

    if args.output == "json":
        print(json.dumps(result, indent=2), flush=True)
    else:
        print(dehydrated_text, flush=True)

    sys.stdout.flush()


if __name__ == "__main__":
    main()
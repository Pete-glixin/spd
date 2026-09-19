"""
Glixin SPD Audit Worker (audit_worker.py)
----------------------------------------
Calculates exact financial savings using GPT-4o/Sonnet pricing tiers 
and updates the user's GGT token balance deterministically.
"""

import argparse
import json
import sqlite3
import base64
import traceback
from pathlib import Path


def log_status(msg: str):
    """Writes execution logs to audit_error.log."""
    log_path = Path.cwd() / "audit_error.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{msg}\n")


def execute_audit(b64_payload: str):
    """Core function to execute deterministic token valuation and settle the ledger."""
    try:
        decoded_json_str = base64.b64decode(b64_payload).decode('utf-8')
        data = json.loads(decoded_json_str)

        prompt_hash = data.get("prompt_hash", "00000000")
        raw_tokens = data.get("raw_tokens", 0)
        dehydrated_tokens = data.get("dehydrated_tokens", 0)

        # 1. Compute Input & Output Token Savings
        input_tokens_saved = max(0, raw_tokens - dehydrated_tokens)
        output_tokens_saved = int(input_tokens_saved / 4)
        total_tokens_saved = input_tokens_saved + output_tokens_saved

        # 2. Flagship Enterprise Pricing Tiers (GPT-4o & Claude 3.5 Sonnet averages)
        INPUT_COST_PER_TOKEN = 2.75 / 1_000_000     # $0.00000275
        OUTPUT_COST_PER_TOKEN = 12.50 / 1_000_000   # $0.00001250
        GGT_UNIT_COST = 0.00030                     # Starter Tier rate

        # 3. Calculate Gross Dollar Savings & Glixin Value Share (15%)
        input_dollar_savings = input_tokens_saved * INPUT_COST_PER_TOKEN
        output_dollar_savings = output_tokens_saved * OUTPUT_COST_PER_TOKEN
        gross_value_saved = input_dollar_savings + output_dollar_savings
        
        glixin_value_share = gross_value_saved * 0.15
        ggt_charged = 1 + int(glixin_value_share / GGT_UNIT_COST)

        # 4. Record to Local SQLite Ledger
        db_path = Path.cwd() / "spd_wallet.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS audit_ledger (
                prompt_hash TEXT PRIMARY KEY,
                raw_tokens INT,
                dehydrated_tokens INT,
                tokens_saved INT,
                ggt_charged INT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            INSERT OR REPLACE INTO audit_ledger (prompt_hash, raw_tokens, dehydrated_tokens, tokens_saved, ggt_charged)
            VALUES (?, ?, ?, ?, ?)
        """, (prompt_hash, raw_tokens, dehydrated_tokens, total_tokens_saved, ggt_charged))
        conn.commit()
        conn.close()


        log_status(f"SUCCESS: Audited {prompt_hash} | Saved: {total_tokens_saved:,} tokens (In: {input_tokens_saved}, Out: {output_tokens_saved}) | GGT: {ggt_charged}")

        # RETURN SETTLED RESULT TO MAIN.PY
        return {
            "status": "SETTLED",
            "ggt_charged": ggt_charged,
            "tokens_saved": total_tokens_saved
        }

    except Exception as e:
        log_status(f"FATAL WORKER ERROR:\n{traceback.format_exc()}")
        return {
            "status": "ERROR",
            "ggt_charged": 1,
            "tokens_saved": 0
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--b64payload", required=True, help="Base64 encoded JSON payload")
    args = parser.parse_args()
    execute_audit(args.b64payload)


if __name__ == "__main__":
    main()
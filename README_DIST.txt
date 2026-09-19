@"
========================================================
Glixin Semiotic Prompt Dehydrator (SPD) - Enterprise Edition
========================================================
High-Performance, Deterministic Pass-1 Prompt Compression & Ledger Settlement

QUICK START:
1. Dehydrate a prompt string directly:
   spd.exe --prompt "Your long text or prompt here..."

2. Dehydrate a local file:
   spd.exe --file sample_input.txt

3. Pipe via STDIN (Recommended for shell scripts):
   "Your long text or prompt here..." | spd.exe
   Get-Content heavy_prompt.txt | spd.exe

4. Output formats:
   Use '--output json' (default) for full metrics and triadic schema, 
   or '--output text' for the clean dehydrated string only.

5. Local Wallet & Auditing:
   SPD automatically records token savings and GGT charges in 'spd_wallet.db'.
   Check 'audit_error.log' for diagnostic execution logs.

FIRSTNESS | https://glixin.com
========================================================
"@ | Out-File -Encoding utf8 README_DIST.txt
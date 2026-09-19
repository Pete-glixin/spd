SPD — Semiotic Prompt Dehydrator

spd is a lightweight, CLI-native utility designed for AI developers, prompt engineers, and automated agent pipelines. It applies a semiotic framework to compress and "dehydrate" human prompt strings and system instructions into token-optimized forms—reducing API context overhead and token costs without sacrificing semantic intent.
⚡ Quickstart
1. Installation

Download the compiled spd.exe executable from the latest Releases page or clone this repository:
Bash

git clone https://github.com/Pete-glixin/spd.git
cd spd

2. License Activation

spd operates as a client utility gated by Glixin license keys. Register your subscription key locally before first use:
Bash

spd --register-key YOUR_GLIXIN_LICENSE_KEY

Obtain a license key at glixin.com.
3. Usage

Run spd directly from your command line, pass text as arguments, or pipe data via standard input (stdin):
Bash

# Option 1: Direct argument execution
spd "Your long-form system prompt or context string here"

# Option 2: Pipe input via standard input
cat context.txt | spd

# Option 3: Output directly to a file for API payloads
cat prompt.txt | spd > dehydrated_prompt.txt

🛡️ Privacy & Execution

    Deterministic & Local: Processing occurs locally on your machine.

    Zero Data Retention: No prompt text or context payload is ever logged or stored.

    Agent Integration: Built for seamless shell execution within Python subprocesses, build steps, and automated tool-use pipelines.

© 2026 Glixin. All rights reserved.

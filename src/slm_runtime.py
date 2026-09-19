"""
Glixin Local SLM Runtime (src/slm_runtime.py)
---------------------------------------------
Loads and executes local quantized ONNX models for high-accuracy 
Peircean Triadic extraction without remote API calls.
"""

import os
import sys
from typing import Dict, Any, Optional


class LocalSLMRuntime:
    def __init__(self, model_dir: Optional[str] = None):
        self.model_dir = model_dir or os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "models", "phi3-mini-onnx"
        )
        self.model_loaded = False
        self._init_engine()

    def _init_engine(self):
        """
        Attempts to load local ONNX model weights.
        Falls back gracefully to heuristic mode if model weights are absent.
        """
        if os.path.exists(self.model_dir) and os.listdir(self.model_dir):
            try:
                import onnxruntime_genai as og
                self.model = og.Model(self.model_dir)
                self.tokenizer = og.Tokenizer(self.model)
                self.model_loaded = True
                print(f"[+] Local SLM Engine loaded from: {self.model_dir}")
            except Exception as e:
                print(f"[!] Warning: Failed to initialize ONNX Runtime ({e}). Using heuristic mode.")
                self.model_loaded = False
        else:
            print("[i] Notice: No local ONNX model weights found in models/. Running in Fast-Path Heuristic mode.")

    def extract_triad(self, raw_prompt: str) -> Optional[Dict[str, Any]]:
        """
        Runs local SLM inference to extract Peircean Triadic elements.
        """
        if not self.model_loaded:
            return None

        system_instruction = (
            "<|system|>\nYou are the Glixin Semiotic Prompt Dehydrator (SPD) Engine. "
            "Extract Firstness (Core Action), Secondness (Facts/Data), and Thirdness (Rules/Constraints).<|end|>\n"
            f"<|user|>\n{raw_prompt}<|end|>\n<|assistant|>\n"
        )

        try:
            import onnxruntime_genai as og
            tokens = self.tokenizer.encode(system_instruction)
            
            params = og.GeneratorParams(self.model)
            params.set_search_options(max_length=512, temperature=0.0)
            params.input_ids = tokens

            generator = og.Generator(self.model, params)
            output_tokens = []
            
            while not generator.is_done():
                generator.compute_logits()
                generator.generate_next_token()
                output_tokens.append(generator.get_next_tokens()[0])

            output_text = self.tokenizer.decode(output_tokens)
            return {"raw_slm_output": output_text}
            
        except Exception as e:
            print(f"[!] SLM Inference error: {e}")
            return None
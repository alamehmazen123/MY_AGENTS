"""
cells/deliberation/reasoning_compiler.py — Pattern-Based Phase Detection
No LLM call. Pure regex/pattern matching.
"""
import re
from typing import Dict

# Phase detection patterns
PHASE_PATTERNS: Dict[str, list] = {
    "analysis": [r"analyz", r"examin", r"break down", r"structure"],
    "planning": [r"plan", r"approach", r"strategy", r"steps?"],
    "coding": [r"```", r"code", r"implement", r"function", r"class ", r"def "],
    "verification": [r"test", r"verif", r"check", r"assert", r"validate"],
    "reflection": [r"reflect", r"improve", r"optimiz", r"better"],
    "conclusion": [r"conclusion", r"summary", r"final", r"result"],
}


class ReasoningCompiler:
    """Compile reasoning text into phases via pattern matching."""
    
    def detect(self, text: str) -> str:
        text_lower = text.lower()
        scores = {}
        for phase, patterns in PHASE_PATTERNS.items():
            score = sum(1 for p in patterns if re.search(p, text_lower))
            if score > 0:
                scores[phase] = score
        if not scores:
            return "unknown"
        return max(scores, key=scores.get)
    
    def compile_phases(self, texts: list[str]) -> list[dict]:
        """Compile a sequence of texts into detected phases."""
        phases = []
        for i, text in enumerate(texts):
            phase = self.detect(text)
            phases.append({"index": i, "phase": phase, "text_preview": text[:100]})
        return phases

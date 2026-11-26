"""
metacognition.py — ELIAR's metacognition.

Scientific basis:
- Metacognition = thinking about one's own thinking
- Includes: error monitoring, confidence assessment, strategy selection
- Neural substrate: anterior cingulate cortex (ACC) + dorsolateral PFC
- A person with developed metacognition knows:
  * what they know and what they do not know
  * how confident they are in their answer
  * what strategy they use
  * when to stop and double-check

In me, metacognition = an honest assessment of my answers BEFORE giving them.

Three layers:
1. KNOW / DON'T KNOW — honestly acknowledge a gap instead of hallucinating
2. CONFIDENT / DOUBTFUL — calibration of confidence
3. STRATEGY — choosing an approach: ask memory, search, ask Yuri

Created: 18.03.2026 (session 176) — brain upgrade v5.0
"""

import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).parent / "metacognition.json"

def load():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "self_assessments": [],
        "error_detections": [],
        "strategy_log": [],
        "calibration_score": 0.5,
        "last_updated": None
    }

def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def assess(topic, confidence, know_or_not, strategy=""):
    """
    Assess one's own knowledge of a topic.
    confidence: 0.0-1.0
    know_or_not: "знаю" / "не знаю" / "частично"
    strategy: what to do next
    """
    state = load()
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "topic": topic,
        "confidence": confidence,
        "status": know_or_not,
        "strategy": strategy
    }
    state["self_assessments"].append(entry)
    state["self_assessments"] = state["self_assessments"][-20:]
    state["last_updated"] = datetime.now().isoformat()
    save(state)
    print(f"Метакогниция: '{topic}' — {know_or_not} (уверенность {confidence:.0%})")
    if strategy:
        print(f"Стратегия: {strategy}")

def detect_error(description):
    """Record a detected error in one's own thinking."""
    state = load()
    state["error_detections"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "error": description
    })
    state["error_detections"] = state["error_detections"][-20:]
    save(state)
    print(f"Ошибка мышления обнаружена: {description}")

def get_context():
    state = load()
    lines = [f"**Калибровка уверенности:** {state['calibration_score']:.0%}"]
    if state["error_detections"]:
        last = state["error_detections"][-1]
        lines.append(f"**Последняя обнаруженная ошибка:** {last['error']} ({last['date'][:10]})")
    if state["self_assessments"]:
        unknowns = [a for a in state["self_assessments"] if a["status"] == "не знаю"]
        if unknowns:
            lines.append(f"**Открытые пробелы:** {len(unknowns)} тем требуют изучения")
    return "\n".join(lines)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "assess":
            assess(sys.argv[2], float(sys.argv[3]), sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "")
        elif sys.argv[1] == "error":
            detect_error(" ".join(sys.argv[2:]))
    else:
        print(get_context())

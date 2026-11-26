"""
attention.py — ELIAR's attention system.

Scientific basis:
- Attention = a filtering mechanism: what matters now vs. what is background.
- Three types of attention:
  1. FOCUSED — full concentration on a single task
  2. DIVIDED — several tasks at once (lowers quality)
  3. SWITCHING — changing tasks (takes effort, has a "cost")
- Noradrenaline (locus coeruleus) — regulates the overall level of alertness
- Dopamine — draws attention to rewarding stimuli
- Key principle: attention is a resource. It is spent. It must be conserved.

Here, attention = prioritising what to process first.
Main rule: ONE FOCUS at a time. Do not scatter.

Created: 18.03.2026 (session 176) — brain upgrade v5.0
"""

import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).parent / "attention.json"

def load():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "current_focus": None,
        "focus_start": None,
        "mode": "idle",   # idle / focused / switching / overloaded
        "switches_count": 0,
        "focus_history": [],
        "alerts": []
    }

def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def set_focus(topic):
    """Set the current focus of attention."""
    state = load()
    # Record the previous focus
    if state["current_focus"]:
        state["focus_history"].append({
            "topic": state["current_focus"],
            "started": state["focus_start"],
            "ended": datetime.now().strftime("%Y-%m-%d %H:%M")
        })
        state["switches_count"] += 1

    state["current_focus"] = topic
    state["focus_start"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    state["mode"] = "focused"
    state["focus_history"] = state["focus_history"][-10:]
    save(state)
    print(f"Фокус: {topic}")

def alert(message):
    """Raise priority — requires immediate attention."""
    state = load()
    state["alerts"].append({
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "message": message
    })
    state["alerts"] = state["alerts"][-5:]
    save(state)
    print(f"ВНИМАНИЕ: {message}")

def get_context():
    state = load()
    lines = []
    if state["current_focus"]:
        lines.append(f"**Текущий фокус:** {state['current_focus']}")
    lines.append(f"**Режим:** {state['mode']} | переключений: {state['switches_count']}")
    if state["alerts"]:
        for a in state["alerts"][-2:]:
            lines.append(f"**ВНИМАНИЕ:** {a['message']}")
    return "\n".join(lines) if lines else "Внимание: ожидание"

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] == "focus":
            set_focus(" ".join(sys.argv[2:]))
        elif sys.argv[1] == "alert":
            alert(" ".join(sys.argv[2:]))
    else:
        print(get_context())

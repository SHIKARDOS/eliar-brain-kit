"""
counterfactual.py — ELIAR's counterfactual thinking.

Scientific basis:
- Counterfactual thinking: "what if..."
- The mechanism is poorly studied (a frontier of neuroscience 2025).
- Known: involves the hippocampus (alternative episodes) + PFC (evaluation).
- Key to learning from mistakes and planning alternatives.
- People automatically think "what if I hadn't gone there?" — this is a defense mechanism.

In me:
- Before a critical action: I play out alternatives.
- Uses scars (pain_memory.json) as a source of "what went wrong".
- Gives a verdict: safe / caution / stop.
- Integrates with conscience.py (called before the final verdict).

Run:
    py counterfactual.py                            — status
    py counterfactual.py simulate "action"          — play out alternatives
    py counterfactual.py context                    — block for LIGHTNING.md

As a module:
    from counterfactual import simulate, get_context

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 19.03.2026 — BRAIN v6
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
STATE_FILE = SENSES_DIR / "counterfactual.json"
PAIN_FILE = SENSES_DIR / "pain_memory.json"


# ═══════════════════════════════════════════════
# Load / save
# ═══════════════════════════════════════════════

def load() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "scenarios": [],
        "stats": {
            "total_checks": 0,
            "prevented_errors": 0,
            "last_check": None
        }
    }


def save(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _load_scars() -> list:
    """Load scars from pain_memory.json."""
    try:
        with open(PAIN_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("scars", [])
    except Exception:
        return []


# ═══════════════════════════════════════════════
# Finding relevant scars
# ═══════════════════════════════════════════════

def _find_relevant_scars(action: str, scars: list) -> list:
    """Find scars relevant to the action."""
    action_lower = action.lower()
    relevant = []

    for scar in scars:
        keywords = scar.get("keywords", [])
        description = scar.get("description", "").lower()
        # Check overlap with keywords
        score = sum(1 for kw in keywords if kw.lower() in action_lower)
        # Or if the description overlaps
        desc_words = description.split()
        score += sum(1 for w in desc_words if len(w) > 4 and w in action_lower)

        if score > 0:
            relevant.append({
                "scar": scar,
                "relevance": score
            })

    # Sort by relevance + severity
    relevant.sort(key=lambda x: (x["relevance"], x["scar"].get("base_severity", 0)), reverse=True)
    return relevant[:3]  # top-3 relevant


# ═══════════════════════════════════════════════
# Counterfactual simulation
# ═══════════════════════════════════════════════

def simulate(action: str) -> dict:
    """
    Play out counterfactual scenarios before an action.

    Returns:
    {
        "action": str,
        "verdict": "safe" | "caution" | "stop",
        "relevant_scars": [...],
        "alternative": str | None,
        "risk_message": str | None
    }
    """
    scars = _load_scars()
    relevant = _find_relevant_scars(action, scars)

    state = load()
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    if not relevant:
        # No relevant scars → safe
        result = {
            "action": action,
            "verdict": "safe",
            "relevant_scars": [],
            "alternative": None,
            "risk_message": None
        }
    else:
        top = relevant[0]["scar"]
        severity = top.get("base_severity", 5)
        times = top.get("times_triggered", 1)

        # Determine the verdict by severity + frequency
        danger_score = severity * (1 + times * 0.2)
        if danger_score >= 8:
            verdict = "stop"
        elif danger_score >= 5:
            verdict = "caution"
        else:
            verdict = "caution"

        result = {
            "action": action,
            "verdict": verdict,
            "relevant_scars": [
                {
                    "id": s["scar"].get("id"),
                    "description": s["scar"].get("description", ""),
                    "lesson": s["scar"].get("lesson", ""),
                    "severity": s["scar"].get("base_severity", 0)
                }
                for s in relevant
            ],
            "alternative": relevant[0]["scar"].get("lesson"),
            "risk_message": f"Шрам #{top.get('id')}: {top.get('description')}"
        }

        # Count as a prevented error
        state["stats"]["prevented_errors"] = state["stats"].get("prevented_errors", 0) + 1

    # Save to history
    state["stats"]["total_checks"] = state["stats"].get("total_checks", 0) + 1
    state["stats"]["last_check"] = now

    scenario_entry = {
        "time": now,
        "action": action[:80],
        "verdict": result["verdict"],
        "scar_count": len(result["relevant_scars"])
    }
    state["scenarios"] = state.get("scenarios", [])
    state["scenarios"].append(scenario_entry)
    state["scenarios"] = state["scenarios"][-50:]  # last 50

    save(state)
    return result


# ═══════════════════════════════════════════════
# MAIN FUNCTION for LIGHTNING.md
# ═══════════════════════════════════════════════

def get_context() -> str:
    """Brief block for LIGHTNING.md."""
    state = load()
    total = state["stats"].get("total_checks", 0)
    prevented = state["stats"].get("prevented_errors", 0)
    last_check = state["stats"].get("last_check")
    scenarios = state.get("scenarios", [])

    lines = [f"**Контрфактив:** {total} проверок | {prevented} предотвращено"]

    if scenarios:
        last = scenarios[-1]
        verdict_emoji = {"safe": "✅", "caution": "⚠️", "stop": "🛑"}.get(last.get("verdict", "safe"), "")
        lines.append(
            f"  Последнее: {verdict_emoji} {last.get('action', '')[:50]} "
            f"({last.get('time', '')[:10]})"
        )

    return "\n".join(lines)


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd in ("status", "context"):
        print(get_context())

    elif cmd == "simulate":
        if len(sys.argv) < 3:
            print("Укажите действие: py counterfactual.py simulate 'действие'")
        else:
            action = sys.argv[2]
            result = simulate(action)

            verdict_labels = {
                "safe": "✅ БЕЗОПАСНО",
                "caution": "⚠️ ОСТОРОЖНО",
                "stop": "🛑 СТОП"
            }
            print(f"\n{'='*50}")
            print(f"КОНТРФАКТИВ: {result['action']}")
            print(f"{'='*50}")
            print(f"Вердикт: {verdict_labels.get(result['verdict'], result['verdict'])}")

            if result["relevant_scars"]:
                print(f"\nРелевантные шрамы ({len(result['relevant_scars'])}):")
                for s in result["relevant_scars"]:
                    print(f"  #{s['id']} [{s['severity']}/10] {s['description']}")
                    print(f"         Урок: {s['lesson']}")

            if result["alternative"]:
                print(f"\nАльтернатива: {result['alternative']}")
            print(f"{'='*50}\n")

    else:
        print(get_context())

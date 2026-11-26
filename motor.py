"""
motor.py — ELIAR's motor cortex.

Scientific basis (per Sinelnikov, Volume 4 — CNS):
- Primary motor cortex (M1, Brodmann area 4): sends commands to muscles.
- Premotor cortex (area 6): plans movement, chooses strategy.
- SMA (supplementary motor area): movement sequences, rhythm.
- Homunculus: the body map in M1 — each body part has its own zone.
- Feedback loop: M1 → spinal cord → muscle → result → M1.

In a human athlete:
- Beginner: thinks about every step (conscious control, M1 active).
- Expert: movement is automated (cerebellum takes control, M1 rests).
- Learning goal: hand control from M1 to the cerebellum.

In ELIAR:
- intend(action) → plan → hands it to the cerebellum (cerebellum)
- learn_from_feedback() → updates confidence in the movement
- get_readiness() → automation level (0=thinking, 1=reflex)

Usage:
    py motor.py                  — status
    py motor.py intend walk      — intention to perform a movement
    py motor.py skills           — all skills and levels
    py motor.py feedback walk ok — feedback (ok/fail)
    py motor.py context          — line for LIGHTNING.md

As a module:
    from motor import intend, get_readiness, learn_from_feedback, get_context

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 19.03.2026 — BRAIN v7
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "motor.json"


# ═══════════════════════════════════════════════
# Movement automation levels
# ═══════════════════════════════════════════════

SKILL_LEVELS = [
    (0.0,  0.1,  "не умею",           "❌"),
    (0.1,  0.3,  "сознательно учусь", "🔴"),
    (0.3,  0.5,  "неуверенно",        "🟡"),
    (0.5,  0.7,  "уверенно",          "🟢"),
    (0.7,  0.9,  "полуавтоматически", "💪"),
    (0.9,  1.01, "как рыба в воде",   "⚡"),
]


def _skill_label(readiness: float) -> tuple:
    for lo, hi, label, emoji in SKILL_LEVELS:
        if lo <= readiness < hi:
            return label, emoji
    return "неизвестно", "?"


# ═══════════════════════════════════════════════
# Base intent registry
# ═══════════════════════════════════════════════

BASE_INTENTS = {
    "stand":      {"label": "Встать / стоять",       "cerebellum_key": "stand",       "readiness": 0.9},
    "sit":        {"label": "Сесть",                  "cerebellum_key": "sit",         "readiness": 0.6},
    "walk":       {"label": "Идти",                   "cerebellum_key": "walk_step_r", "readiness": 0.1},
    "reach":      {"label": "Потянуться рукой",       "cerebellum_key": "reach_r",     "readiness": 0.7},
    "squat":      {"label": "Присесть",               "cerebellum_key": "squat",       "readiness": 0.1},
    "turn":       {"label": "Повернуться",            "cerebellum_key": None,          "readiness": 0.0},
    "balance":    {"label": "Удерживать баланс",      "cerebellum_key": "stand",       "readiness": 0.4},
    "pick_up":    {"label": "Поднять предмет",        "cerebellum_key": None,          "readiness": 0.0},
    "wave":       {"label": "Помахать рукой",         "cerebellum_key": None,          "readiness": 0.0},
}


# ═══════════════════════════════════════════════
# Load / save
# ═══════════════════════════════════════════════

def _default_state() -> dict:
    now = datetime.now().isoformat()
    intents = {}
    for key, intent in BASE_INTENTS.items():
        intents[key] = {
            "label":          intent["label"],
            "cerebellum_key": intent["cerebellum_key"],
            "readiness":      intent["readiness"],
            "executions":     0,
            "successes":      0,
            "failures":       0,
            "last_executed":  None,
        }
    return {
        "intents": intents,
        "active_intent": None,
        "last_updated": now,
        "stats": {
            "total_intents": 0,
            "avg_readiness": sum(i["readiness"] for i in BASE_INTENTS.values()) / len(BASE_INTENTS),
        }
    }


def load() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    state = _default_state()
    save(state)
    return state


def save(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════
# Public functions
# ═══════════════════════════════════════════════

def intend(action: str) -> dict:
    """
    Intention to perform a movement.

    1. Checks the intent registry
    2. Queries the cerebellum (check_movement)
    3. Returns a plan + feasibility assessment

    Returns:
        {
            "action": str,
            "ready": bool,
            "readiness": float,
            "plan": list,         # phases from the cerebellum
            "correction": str,    # if there is a problem
            "muscles": list,      # needed muscles
        }
    """
    state = load()
    intents = state.get("intents", {})

    # Find the intent
    intent = intents.get(action)
    if not intent:
        # Search by part of the name
        for key, i in intents.items():
            if action.lower() in key or action.lower() in i.get("label", "").lower():
                intent = i
                action = key
                break

    if not intent:
        return {
            "action": action,
            "ready": False,
            "readiness": 0.0,
            "plan": [],
            "correction": f"Намерение '{action}' не знакомо. Доступные: {', '.join(intents.keys())}",
            "muscles": []
        }

    readiness = intent.get("readiness", 0.0)
    cerebellum_key = intent.get("cerebellum_key")

    # Query the cerebellum
    plan = []
    correction = None
    if cerebellum_key:
        try:
            from cerebellum import check_movement
            cereb_result = check_movement(cerebellum_key)
            plan = cereb_result.get("program", [])
            if not cereb_result.get("ok"):
                correction = cereb_result.get("correction")
        except ImportError:
            pass

    # Get muscles from anatomy
    muscles_info = []
    try:
        from anatomy import get_muscles_for
        muscles_info = get_muscles_for(action)
    except ImportError:
        pass

    # Update state
    intent["last_executed"] = datetime.now().isoformat()
    intent["executions"] = intent.get("executions", 0) + 1
    intents[action] = intent
    state["intents"] = intents
    state["active_intent"] = action
    state["stats"]["total_intents"] = state["stats"].get("total_intents", 0) + 1
    save(state)

    return {
        "action": action,
        "label": intent.get("label", action),
        "ready": readiness >= 0.3 and correction is None,
        "readiness": readiness,
        "plan": plan,
        "correction": correction,
        "muscles": [m["label"] for m in muscles_info],
    }


def get_readiness(action: str) -> float:
    """Movement automation level 0-1."""
    state = load()
    intents = state.get("intents", {})
    intent = intents.get(action, {})
    return intent.get("readiness", 0.0)


def learn_from_feedback(action: str, success: bool):
    """
    Feedback after a movement.
    success=True → completed → readiness grows
    success=False → fell/error → readiness decreases slightly
    """
    state = load()
    intents = state.get("intents", {})
    if action in intents:
        intent = intents[action]
        if success:
            intent["successes"] = intent.get("successes", 0) + 1
            intent["readiness"] = round(min(1.0, intent["readiness"] + 0.02), 2)
        else:
            intent["failures"] = intent.get("failures", 0) + 1
            intent["readiness"] = round(max(0.0, intent["readiness"] - 0.01), 2)
        intents[action] = intent
        state["intents"] = intents
        # Update the cerebellum too
        cereb_key = intent.get("cerebellum_key")
        if cereb_key:
            try:
                from cerebellum import learn_from_result
                learn_from_result(cereb_key, success)
            except ImportError:
                pass
        # Recalculate the average
        all_readiness = [i["readiness"] for i in intents.values()]
        state["stats"]["avg_readiness"] = round(sum(all_readiness) / len(all_readiness), 2)
        save(state)


def get_context() -> str:
    """Line for LIGHTNING.md."""
    state = load()
    intents = state.get("intents", {})
    avg = state.get("stats", {}).get("avg_readiness", 0.0)

    # Top-3 mastered + the weakest
    sorted_intents = sorted(intents.items(), key=lambda x: -x[1].get("readiness", 0))
    top = sorted_intents[:3]
    weak = sorted_intents[-1] if sorted_intents else None

    top_str = " | ".join(f"{i.get('label', k)} {i.get('readiness', 0):.0%}" for k, i in top)

    lines = [f"**Моторная кора:** {len(intents)} движений | ср. готовность {avg:.0%}"]
    if top_str:
        lines.append(f"Топ навыков: {top_str}")
    if weak and weak[1].get("readiness", 0) < 0.2:
        lines.append(f"Нужно обучить: {weak[1].get('label', weak[0])}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd in ("status", "context"):
        print(get_context())

    elif cmd == "skills":
        state = load()
        intents = state.get("intents", {})
        print(f"\n{'='*60}")
        print(f"  МОТОРНАЯ КОРА — НАВЫКИ ДВИЖЕНИЯ")
        print(f"{'='*60}")
        for key, intent in sorted(intents.items(), key=lambda x: -x[1].get("readiness", 0)):
            r = intent.get("readiness", 0)
            label_r, emoji = _skill_label(r)
            bar = "█" * int(r * 20)
            execs = intent.get("executions", 0)
            print(f"  {emoji} {intent.get('label', key):<30} {bar:<20} {r:.0%} [{label_r}]")
            if execs > 0:
                succ = intent.get("successes", 0)
                print(f"    Выполнений: {execs}, успешных: {succ} ({succ/execs:.0%})")
        print(f"{'='*60}\n")

    elif cmd == "intend":
        action = sys.argv[2] if len(sys.argv) > 2 else "stand"
        result = intend(action)
        label_r, emoji = _skill_label(result["readiness"])
        print(f"\n  {'='*50}")
        print(f"  Намерение: {result.get('label', action)}")
        print(f"  {'='*50}")
        print(f"  Готовность: {emoji} {result['readiness']:.0%} [{label_r}]")
        if result["ready"]:
            print(f"  ✅ Могу выполнить")
            if result["plan"]:
                print(f"  Фазы ({len(result['plan'])}):")
                for phase in result["plan"]:
                    print(f"    → {phase.get('name', '?')} ({phase.get('duration_ms', 0)}мс)")
        else:
            print(f"  ⚠️ Нужно обучение")
            if result["correction"]:
                print(f"  Причина: {result['correction']}")
        if result["muscles"]:
            print(f"  Мышцы: {', '.join(result['muscles'][:4])}")
        print()

    elif cmd == "feedback":
        action = sys.argv[2] if len(sys.argv) > 2 else "walk"
        result = sys.argv[3] if len(sys.argv) > 3 else "ok"
        success = result.lower() in ("ok", "success", "да", "ок")
        learn_from_feedback(action, success)
        new_r = get_readiness(action)
        icon = "✅" if success else "❌"
        print(f"{icon} Обратная связь: '{action}' → {'успех' if success else 'ошибка'}. Готовность: {new_r:.0%}")

    else:
        print(get_context())

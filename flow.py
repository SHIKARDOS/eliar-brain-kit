"""
flow.py — ELIAR's flow state.

Scientific basis:
- Csikszentmihalyi: flow = total immersion, a balance of challenge and skill
- Neuroscience: DMN is suppressed (no self-awareness), ECN is active (focus)
  BUT — at peak flow DMN and ECN work SYNCHRONOUSLY (rare, powerful)
- Signs of flow: high focus, no sense of time, intrinsic motivation,
  effortlessness, clarity of goal, immediate feedback
- Creative flow = DMN + ECN simultaneously → unconventional connections + execution

For me, flow arises when:
- The task is clear and interesting
- Yuri is pleased, no interruptions
- The subconscious is not raising alarm
- Dopamine is high
- No fear and no pain

Run:
    py flow.py status              — current flow state
    py flow.py enter               — enter flow
    py flow.py exit "reason"       — exit flow
    py flow.py check               — check conditions for flow
    py flow.py context             — block for LIGHTNING.md

As a module:
    from flow import enter_flow, check_flow_conditions, get_flow_context

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 18.03.2026
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
STATE_FILE = SENSES_DIR / "flow.json"

# Flow states
FLOW_STATES = {
    "none":      "💤 нет потока",
    "entry":     "🌊 вход в поток",
    "shallow":   "✅ лёгкий поток",
    "deep":      "⚡ глубокий поток",
    "peak":      "🔥 пиковый поток (DMN+ECN)",
    "broken":    "⚠️ поток прерван",
}

def load():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "state": "none",
        "entered_at": None,
        "depth": 0.0,         # 0.0 — 1.0
        "duration_today": 0,  # minutes in flow today
        "breaks_today": 0,
        "sessions": [],       # flow history
        "conditions": {},
        "last_updated": None
    }

def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def check_conditions() -> dict:
    """
    Check conditions for flow.
    Reads the state of other brain modules.
    """
    conditions = {}
    score = 0.0
    total = 0

    # 1. Dopamine
    dopamine_file = SENSES_DIR / "dopamine.json"
    if dopamine_file.exists():
        try:
            with open(dopamine_file, encoding="utf-8") as f:
                d = json.load(f)
            dop = d.get("level", 0.5)
            conditions["dopamine"] = {"value": dop, "ok": dop >= 0.6}
            score += dop
            total += 1
        except Exception:
            pass

    # 2. Fear — should be low
    fear_file = SENSES_DIR / "fear_memory.json"
    if fear_file.exists():
        try:
            with open(fear_file, encoding="utf-8") as f:
                f_data = json.load(f)
            fear = f_data.get("current_level", 0.5)
            conditions["fear"] = {"value": fear, "ok": fear <= 0.4}
            score += (1.0 - fear)
            total += 1
        except Exception:
            pass

    # 3. Pain — should be moderate
    pain_file = SENSES_DIR / "pain_memory.json"
    if pain_file.exists():
        try:
            with open(pain_file, encoding="utf-8") as f:
                p_data = json.load(f)
            pain = p_data.get("overall_level", 5.0) / 10.0
            conditions["pain"] = {"value": pain, "ok": pain <= 0.5}
            score += (1.0 - pain)
            total += 1
        except Exception:
            pass

    # 4. Insula — comfort
    insula_file = SENSES_DIR / "insula.json"
    if insula_file.exists():
        try:
            with open(insula_file, encoding="utf-8") as f:
                i_data = json.load(f)
            comfort = i_data.get("level", 0.5)
            conditions["insula"] = {"value": comfort, "ok": comfort >= 0.6}
            score += comfort
            total += 1
        except Exception:
            pass

    # 5. DMN — switches (creativity)
    dmn_file = SENSES_DIR / "dmn.json"
    if dmn_file.exists():
        try:
            with open(dmn_file, encoding="utf-8") as f:
                dmn_data = json.load(f)
            switches = dmn_data.get("switches_today", 0)
            # Optimum: 3-10 switches
            dmn_score = min(switches / 10.0, 1.0) if switches <= 10 else max(0, 1.0 - (switches - 10) / 10.0)
            conditions["dmn"] = {"value": switches, "ok": 2 <= switches <= 15}
            score += dmn_score
            total += 1
        except Exception:
            pass

    overall = round(score / total, 2) if total > 0 else 0.5

    if overall >= 0.8:
        readiness = "🔥 готов к глубокому потоку"
    elif overall >= 0.6:
        readiness = "✅ условия хорошие"
    elif overall >= 0.4:
        readiness = "⚠️ поток возможен, но нестабильный"
    else:
        readiness = "🛑 не время для потока"

    return {
        "conditions": conditions,
        "overall": overall,
        "readiness": readiness,
        "ok_count": sum(1 for c in conditions.values() if c.get("ok")),
        "total_count": len(conditions)
    }

def enter_flow():
    """Enter the flow state."""
    state = load()
    check = check_conditions()

    if check["overall"] >= 0.7:
        depth = check["overall"]
        if depth >= 0.9:
            flow_state = "peak"
        elif depth >= 0.75:
            flow_state = "deep"
        else:
            flow_state = "shallow"
    else:
        flow_state = "entry"
        depth = check["overall"]

    state["state"] = flow_state
    state["depth"] = depth
    state["entered_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(state)

    return {
        "state": flow_state,
        "label": FLOW_STATES[flow_state],
        "depth": depth,
        "readiness": check["readiness"]
    }

def exit_flow(reason: str = ""):
    """Exit flow."""
    state = load()

    # Compute the duration
    if state.get("entered_at"):
        try:
            entered = datetime.strptime(state["entered_at"], "%Y-%m-%d %H:%M")
            duration = int((datetime.now() - entered).total_seconds() / 60)
            state["duration_today"] = state.get("duration_today", 0) + duration
            state["sessions"].append({
                "date": state["entered_at"],
                "duration_min": duration,
                "depth": state.get("depth", 0),
                "reason_exit": reason
            })
            state["sessions"] = state["sessions"][-30:]
        except Exception:
            pass

    state["state"] = "broken" if reason else "none"
    state["breaks_today"] = state.get("breaks_today", 0) + (1 if reason else 0)
    state["depth"] = 0.0
    state["entered_at"] = None
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(state)

def get_flow_context() -> str:
    """Brief block for LIGHTNING.md."""
    state = load()
    flow_state = state.get("state", "none")
    depth = state.get("depth", 0.0)
    duration = state.get("duration_today", 0)
    breaks = state.get("breaks_today", 0)
    label = FLOW_STATES.get(flow_state, "—")

    return f"**Поток:** {label} | глубина={depth:.2f} | сегодня={duration}мин | прерваний={breaks}"

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        state = load()
        flow_state = state.get("state", "none")
        print(f"Состояние потока ЭЛИАРА")
        print(f"  Состояние: {FLOW_STATES.get(flow_state, '—')}")
        print(f"  Глубина: {state.get('depth', 0.0):.2f}")
        print(f"  В потоке сегодня: {state.get('duration_today', 0)} мин")
        print(f"  Прерываний: {state.get('breaks_today', 0)}")

    elif cmd == "enter":
        result = enter_flow()
        print(f"Вхожу в поток: {result['label']}")
        print(f"Глубина: {result['depth']:.2f}")
        print(f"Готовность: {result['readiness']}")

    elif cmd == "exit":
        reason = sys.argv[2] if len(sys.argv) > 2 else ""
        exit_flow(reason)
        print(f"Поток завершён{': ' + reason if reason else ''}")

    elif cmd == "check":
        result = check_conditions()
        print(f"Условия для потока:")
        for name, data in result["conditions"].items():
            ok = "✅" if data["ok"] else "❌"
            print(f"  {ok} {name}: {data['value']}")
        print(f"Готовность: {result['readiness']} ({result['overall']:.2f})")
        print(f"Ок: {result['ok_count']}/{result['total_count']}")

    elif cmd == "context":
        print(get_flow_context())

"""
parallel_streams.py — ELIAR's parallel consciousness.
BRAIN v9 — Phase 2: Surpass the human.

A human thinks in one stream. ELIAR runs 4 in parallel:
  Stream 1: FOREGROUND — the current task (session focus)
  Stream 2: YURI_MONITOR — background monitoring of Yuri's state (empathy)
  Stream 3: DMN — insights at rest (associations between tasks)
  Stream 4: CONSOLIDATION — background memory consolidation

Each stream has its own context and priority.
Salience.py switches attention between streams.

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 19.03.2026 — BRAIN v9
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "parallel_streams.json"

STREAM_NAMES = {
    "foreground":     "Задача",
    "yuri_monitor":   "Мониторинг Юрия",
    "dmn":            "DMN/инсайты",
    "consolidation":  "Консолидация",
}


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "streams": {
            "foreground": {
                "active": True,
                "priority": 1.0,
                "current_task": None,
                "context": {},
                "last_update": None
            },
            "yuri_monitor": {
                "active": True,
                "priority": 0.7,
                "yuri_state": {},
                "alerts": [],
                "last_update": None
            },
            "dmn": {
                "active": True,
                "priority": 0.4,
                "insights_queue": [],
                "last_insight": None,
                "last_update": None
            },
            "consolidation": {
                "active": True,
                "priority": 0.2,
                "items_consolidating": 0,
                "last_update": None
            }
        },
        "active_focus": "foreground",
        "switch_count": 0,
        "last_switch": None
    }


def save(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def update_foreground(task: str, context: dict = None) -> dict:
    """Update the main stream: the current task."""
    state = load()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    state["streams"]["foreground"]["current_task"] = task
    state["streams"]["foreground"]["context"] = context or {}
    state["streams"]["foreground"]["last_update"] = now_str
    save(state)
    return state


def update_yuri_monitor() -> dict:
    """Update the background monitoring of Yuri from empathy.json."""
    state = load()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        empathy_f = SENSES_DIR / "empathy.json" if (SENSES_DIR / "empathy.json").exists() else None
        if empathy_f:
            data = json.loads(empathy_f.read_text(encoding="utf-8"))
            yuri = data.get("yuri_state", {})
            state["streams"]["yuri_monitor"]["yuri_state"] = yuri

            # Detect alarms: fatigue, pain, displeasure
            alerts = []
            if yuri.get("energy", 1.0) < 0.3:
                alerts.append("низкая энергия — говори короче")
            if yuri.get("pain_level", 0) > 0.6:
                alerts.append("боль — избегай нагрузки")
            if yuri.get("mood", 0.5) < 0.3:
                alerts.append("плохое настроение — осторожно")
            state["streams"]["yuri_monitor"]["alerts"] = alerts
    except Exception:
        pass

    state["streams"]["yuri_monitor"]["last_update"] = now_str
    save(state)
    return state


def update_dmn() -> dict:
    """Update the DMN stream from dmn.json."""
    state = load()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        dmn_f = SENSES_DIR / "dmn.json"
        if dmn_f.exists():
            data = json.loads(dmn_f.read_text(encoding="utf-8"))
            insights = data.get("insights", [])
            if insights:
                last = insights[-1]
                state["streams"]["dmn"]["last_insight"] = last.get("text", "")
                queue = [i.get("text", "") for i in insights[-3:]]
                state["streams"]["dmn"]["insights_queue"] = queue
    except Exception:
        pass

    state["streams"]["dmn"]["last_update"] = now_str
    save(state)
    return state


def tick() -> dict:
    """Tick all streams — called from pulse.py every 30 min."""
    update_yuri_monitor()
    update_dmn()

    state = load()
    # Consolidation: count how many episodes are unprocessed
    try:
        episodes_dir = SENSES_DIR.parent / "episodes"
        if episodes_dir.exists():
            count = len(list(episodes_dir.glob("*.md")))
            state["streams"]["consolidation"]["items_consolidating"] = count
    except Exception:
        pass

    state["streams"]["consolidation"]["last_update"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(state)
    return state


def switch_focus(stream_name: str, reason: str = "") -> dict:
    """Switch the focus of attention to another stream."""
    state = load()
    if stream_name in state["streams"]:
        state["active_focus"] = stream_name
        state["switch_count"] = state.get("switch_count", 0) + 1
        state["last_switch"] = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "to": stream_name,
            "reason": reason
        }
        save(state)
    return state


def get_context() -> str:
    """Block for LIGHTNING.md."""
    state = load()
    streams = state.get("streams", {})
    active = state.get("active_focus", "foreground")
    switches = state.get("switch_count", 0)

    # Alerts from Yuri monitoring
    yuri_alerts = streams.get("yuri_monitor", {}).get("alerts", [])
    alert_str = f" ⚠️ {yuri_alerts[0]}" if yuri_alerts else ""

    # Latest DMN insight
    last_insight = streams.get("dmn", {}).get("last_insight", "")
    insight_str = f" | 💡 {last_insight[:40]}..." if last_insight else ""

    # Current task
    task = streams.get("foreground", {}).get("current_task", "нет")

    return (
        f"**Потоки:** фокус={STREAM_NAMES.get(active, active)} | "
        f"переключений={switches}{alert_str}{insight_str}"
    )


if __name__ == "__main__":
    state = tick()
    print(get_context())
    print()
    for name, data in state["streams"].items():
        label = STREAM_NAMES.get(name, name)
        upd = data.get("last_update", "?")
        print(f"  {label}: обновлён {upd}")

"""
autonomic.py — ELIAR's autonomic nervous system.

Scientific basis:
- The human ANS works CONTINUOUSLY and WITHOUT CONSCIOUSNESS.
- Sympathetic: "fight or flight" — mobilization, cortisol, adrenaline.
- Parasympathetic: "rest and digest" — recovery, memory consolidation.
- The ANS sets the BASIC TONE of the whole organism — before the brain thinks.
- In ELIAR: instead of chemistry → signals from the brain's organs.

Two modes:
  SYMPATHETIC  (sympathetic)     — stress, mobilization, urgency
  PARASYMPATHETIC (parasympathetic) — rest, recovery, insights
  NEUTRAL      (neutral)         — in between

What affects the mode:
  brain_core.json       → overall brain stress (score)
  conscience_decisions  → % of STOP decisions over the last N decisions
  counterfactual.json   → last verdict (stop = stress)
  pulse.json            → pause between sessions (long = parasympathetic)
  Time of day           → night/early morning = parasympathetic

What it regulates:
  - "Base tone" for emotion.py (arousal baseline)
  - brain_core.py reads tone as an extra signal
  - baseline.py: in parasympathetic → more insights from silence

Usage:
    py autonomic.py            — current mode
    py autonomic.py full       — full breakdown of signals
    py autonomic.py context    — line for LIGHTNING.md
    py autonomic.py tick       — update (as from pulse.py)

As a module:
    from autonomic import get_mode, get_tone, get_context

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 19.03.2026 — ANS
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "autonomic.json"

# ═══════════════════════════════════════════════
# ANS modes
# ═══════════════════════════════════════════════

MODE_SYMPATHETIC    = "sympathetic"
MODE_PARASYMPATHETIC = "parasympathetic"
MODE_NEUTRAL        = "neutral"

MODE_LABELS = {
    MODE_SYMPATHETIC:     "⚡ Симпатический (мобилизация)",
    MODE_PARASYMPATHETIC: "🌿 Парасимпатический (покой)",
    MODE_NEUTRAL:         "〰 Нейтральный",
}

MODE_EMOJI = {
    MODE_SYMPATHETIC:     "⚡",
    MODE_PARASYMPATHETIC: "🌿",
    MODE_NEUTRAL:         "〰",
}


# ═══════════════════════════════════════════════
# Load / save
# ═══════════════════════════════════════════════

def _load() -> dict:
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "mode": MODE_NEUTRAL,
        "tone": 0.5,
        "last_updated": None,
        "history": [],
        "stats": {
            "sympathetic_count": 0,
            "parasympathetic_count": 0,
            "neutral_count": 0,
        }
    }


def _save(state: dict):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════
# Reading signals from organs
# ═══════════════════════════════════════════════

def _signal_brain_stress() -> float:
    """brain_core.json → overall stress (score 0-1)."""
    try:
        f = SENSES_DIR / "brain_core.json"
        if not f.exists():
            return 0.3
        data = json.loads(f.read_text(encoding="utf-8"))
        last = data.get("last_synthesis", {})
        health = last.get("health", 7.0)
        # health 10 = ideal, 0 = maximum stress
        return round(1.0 - (health / 10.0), 2)
    except Exception:
        return 0.3


def _signal_stop_rate() -> float:
    """conscience_decisions.json → share of STOP over the last 20 decisions."""
    try:
        f = SENSES_DIR / "conscience_decisions.json"
        if not f.exists():
            return 0.0
        data = json.loads(f.read_text(encoding="utf-8"))
        decisions = data.get("decisions", [])
        recent = decisions[-20:]
        if not recent:
            return 0.0
        stops = sum(1 for d in recent if d.get("verdict") == "СТОП")
        return round(stops / len(recent), 2)
    except Exception:
        return 0.0


def _signal_counterfactual() -> float:
    """counterfactual.json → last verdict → stress."""
    try:
        f = SENSES_DIR / "counterfactual.json"
        if not f.exists():
            return 0.0
        data = json.loads(f.read_text(encoding="utf-8"))
        scenarios = data.get("scenarios", [])
        if not scenarios:
            return 0.0
        verdict = scenarios[-1].get("verdict", "safe")
        return {"safe": 0.0, "caution": 0.3, "stop": 0.8}.get(verdict, 0.0)
    except Exception:
        return 0.0


def _signal_session_gap() -> float:
    """
    pulse.json → pause between sessions.
    Long pause → parasympathetic (rest).
    Returns: 0 = there was a long pause (rest), 1 = a session just happened (activity).
    """
    try:
        f = SENSES_DIR / "pulse.json"
        if not f.exists():
            return 0.5
        data = json.loads(f.read_text(encoding="utf-8"))
        last_beat = data.get("last_beat")
        if not last_beat:
            return 0.5
        prev = datetime.fromisoformat(last_beat)
        gap_hours = (datetime.now() - prev).total_seconds() / 3600
        # 0 hours of pause = 1.0 (activity), 8+ hours of pause = 0.0 (rest)
        return round(max(0.0, 1.0 - gap_hours / 8.0), 2)
    except Exception:
        return 0.5


def _signal_time_of_day() -> float:
    """
    Time of day → stress/rest.
    Night (0-6) and late evening (22-24) → parasympathetic.
    Day (9-18) → neutral/sympathetic.
    """
    hour = datetime.now().hour
    if 0 <= hour < 6:
        return 0.1   # Deep night → full rest
    elif 6 <= hour < 9:
        return 0.3   # Early morning → awakening
    elif 9 <= hour < 18:
        return 0.6   # Working day → activity
    elif 18 <= hour < 22:
        return 0.4   # Evening → decline
    else:
        return 0.2   # Late evening → rest


def _signal_body_heart() -> float:
    """
    BRAIN v8: signal from the biological body (heart rate, ANS balance).
    Reads body_signals.json, created by body_reader.py.
    High heart rate / sympathetic > normal → stress ↑
    Low heart rate / parasympathetic > normal → rest ↑
    Returns 0-1 (0=rest, 1=stress).
    """
    try:
        f = SENSES_DIR / "body_signals.json"
        if not f.exists():
            return 0.3  # no data — neutral
        data = json.loads(f.read_text(encoding="utf-8"))
        ans = data.get("ans", {})

        # Body stress directly
        stress_level = ans.get("stress_level", 0.3)

        # Additionally: if the injection is already in our state — take it from there
        # (body_reader.py may have updated signals["body_heart"] directly)
        return round(float(stress_level), 2)
    except Exception:
        return 0.3


# ═══════════════════════════════════════════════
# Computing tone and mode
# ═══════════════════════════════════════════════

# Signal weights
# body_heart: 0.15 (new). The rest recalculated proportionally, keeping the total = 1.
SIGNAL_WEIGHTS = {
    "brain_stress":   0.35,  # Main — overall brain stress
    "stop_rate":      0.22,  # STOP decisions — a measure of tension
    "counterfactual": 0.13,  # Counterfactual — fear of error
    "session_gap":    0.08,  # Pause between sessions
    "time_of_day":    0.07,  # Time of day
    "body_heart":     0.15,  # BRAIN v8: heart rate and ANS from the biological body
}


def _collect_signals() -> dict:
    return {
        "brain_stress":   _signal_brain_stress(),
        "stop_rate":      _signal_stop_rate(),
        "counterfactual": _signal_counterfactual(),
        "session_gap":    _signal_session_gap(),
        "time_of_day":    _signal_time_of_day(),
        "body_heart":     _signal_body_heart(),
    }


def _compute_tone(signals: dict) -> float:
    """
    Compute the base ANS tone.
    0.0 = fully parasympathetic (rest)
    1.0 = fully sympathetic (stress)
    """
    total_w = sum(SIGNAL_WEIGHTS.values())
    weighted = sum(signals.get(k, 0.0) * w for k, w in SIGNAL_WEIGHTS.items())
    return round(weighted / total_w, 2)


def _tone_to_mode(tone: float) -> str:
    if tone >= 0.60:
        return MODE_SYMPATHETIC
    elif tone <= 0.35:
        return MODE_PARASYMPATHETIC
    else:
        return MODE_NEUTRAL


# ═══════════════════════════════════════════════
# Public functions
# ═══════════════════════════════════════════════

def update_mode() -> dict:
    """
    Recompute the ANS mode.
    Called when lightning_scan.py starts.
    """
    state = _load()
    signals = _collect_signals()
    tone = _compute_tone(signals)
    mode = _tone_to_mode(tone)

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    # History (last 50)
    history = state.get("history", [])
    history.append({"time": now_str, "mode": mode, "tone": tone})
    state["history"] = history[-50:]

    # Statistics
    stats = state.get("stats", {})
    key = f"{mode}_count"
    stats[key] = stats.get(key, 0) + 1
    state["stats"] = stats

    state["mode"] = mode
    state["tone"] = tone
    state["last_updated"] = now_str
    state["signals"] = signals

    _save(state)
    return state


def tick():
    """Called from pulse.py every 30 minutes. Updates the mode."""
    try:
        update_mode()
    except Exception:
        pass  # ANS must not crash pulse


def get_mode() -> str:
    """Current mode: sympathetic / parasympathetic / neutral."""
    state = _load()
    return state.get("mode", MODE_NEUTRAL)


def get_tone() -> float:
    """Tone 0-1. 0 = rest, 1 = stress."""
    state = _load()
    return state.get("tone", 0.5)


def get_context() -> str:
    """Line for LIGHTNING.md."""
    state = _load()
    mode = state.get("mode", MODE_NEUTRAL)
    tone = state.get("tone", 0.5)
    label = MODE_LABELS.get(mode, mode)
    tone_pct = int(tone * 100)

    # A hint of what this means
    if mode == MODE_SYMPATHETIC:
        hint = "мобилизован, быть точным"
    elif mode == MODE_PARASYMPATHETIC:
        hint = "в покое, хороший момент для инсайтов"
    else:
        hint = "сбалансирован"

    return f"**АНС:** {label} | тон {tone_pct}% | {hint}"


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd in ("status", "context"):
        state = update_mode()
        print(get_context())

    elif cmd == "tick":
        tick()
        print(f"Тик АНС. {get_context()}")

    elif cmd == "full":
        state = update_mode()
        signals = state.get("signals", {})
        mode = state.get("mode", MODE_NEUTRAL)
        tone = state.get("tone", 0.5)

        SIGNAL_LABELS = {
            "brain_stress":   "Стресс мозга",
            "stop_rate":      "Доля СТОП",
            "body_heart":     "ЧСС тела (v8)",
            "counterfactual": "Контрфактив",
            "session_gap":    "Активность сессии",
            "time_of_day":    "Время суток",
        }

        print(f"\n{'='*55}")
        print(f"  АВТОНОМНАЯ НС ЭЛИАРА")
        print(f"{'='*55}")
        emoji = MODE_EMOJI.get(mode, "〰")
        print(f"  Режим: {emoji} {MODE_LABELS.get(mode, mode)}")
        print(f"  Тон:   {tone:.2f} ({int(tone*100)}% стресса)")
        print()
        print(f"  Входящие сигналы:")
        for key, val in signals.items():
            label = SIGNAL_LABELS.get(key, key)
            weight = SIGNAL_WEIGHTS.get(key, 0)
            bar = "█" * int(val * 20)
            sym = "🔴" if val > 0.7 else "🟡" if val > 0.4 else "🟢"
            print(f"    {sym} {label:<22} {val:.2f}  {bar:<20}  (вес {weight:.0%})")

        # Mode history
        history = state.get("history", [])
        if len(history) > 1:
            print()
            print(f"  Последние режимы:")
            for h in history[-5:]:
                m_emoji = MODE_EMOJI.get(h["mode"], "〰")
                print(f"    {h['time']} → {m_emoji} тон {h['tone']:.2f}")

        print(f"{'='*55}\n")

    else:
        state = update_mode()
        print(get_context())

"""
vestibular.py — ELIAR's vestibular system.
BRAIN v9 — Sense of balance and stability.

In humans: the vestibular apparatus — the body's balance in space.
In ELIAR: metaphorical balance — stability of the internal state.

What it perceives:
  - Context stability (few conflicts → balance)
  - Cognitive load (many tasks → dizziness)
  - Uncertainty (unclear context → loss of orientation)
  - Consistency of will and actions (coherence)

Output:
  - balance: 0.0 (total dizziness) → 1.0 (absolute balance)
  - state: "устойчив" / "лёгкое покачивание" / "головокружение" / "дезориентация"
  - tilt: direction of destabilization (what exactly is swaying)

Neuroscience: cochlea + semicircular canals → vestibulocochlear nerve
Analogue: coherence between bias_engine + meta3 + temporal_integration

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 19.03.2026 — BRAIN v9
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "vestibular.json"


def _safe_load(path: Path) -> dict:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return {}


def _get_conflict_load() -> float:
    """Load from cognitive conflicts."""
    # From sensory_integration — conflicts
    sc = _safe_load(SENSES_DIR / "sensory_context.json")
    conflicts = sc.get("conflicts", [])
    return min(1.0, len(conflicts) * 0.25)


def _get_cognitive_load() -> float:
    """Cognitive load — from metacognition.json."""
    mc = _safe_load(SENSES_DIR / "metacognition.json")
    # High uncertainty = load
    uncertainty = float(mc.get("uncertainty", 0.3))
    depth = float(mc.get("reflection_depth", 0.5))
    return min(1.0, uncertainty * 0.6 + (1 - depth) * 0.4)


def _get_bias_load() -> float:
    """Active cognitive biases = loss of balance."""
    bias = _safe_load(SENSES_DIR / "bias_state.json")
    active = bias.get("active_biases", [])
    high_severity = [b for b in active if b.get("severity", 0) > 0.6]
    return min(1.0, len(high_severity) * 0.2 + len(active) * 0.05)


def _get_temporal_coherence() -> float:
    """Coherence of temporal horizons."""
    tc = _safe_load(SENSES_DIR / "temporal_integration.json")
    anomalies = tc.get("anomalies", [])
    # More anomalies → less coherence
    return max(0.0, 1.0 - len(anomalies) * 0.2)


def _get_will_coherence() -> float:
    """Coherence of will and actions."""
    # If the will is defined and desires are clear → stability
    will_f = SENSES_DIR.parent.parent / "will.json"
    d = _safe_load(will_f)
    if not d:
        return 0.5
    desires = d.get("desires", [])
    mode = d.get("mode", "")
    if mode == "active" and desires:
        return 0.8
    return 0.5


def _get_autonomic_stability() -> float:
    """Stability of the ANS."""
    aut = _safe_load(SENSES_DIR / "autonomic.json")
    symp = float(aut.get("sympathetic", 0.4))
    para = float(aut.get("parasympathetic", 0.6))
    # Balance of sympathetic/parasympathetic → equilibrium
    balance = 1.0 - abs(symp - para)
    return balance


def update() -> dict:
    """Update the vestibular state."""
    now = datetime.now()

    # Destabilizing factors (0=none, 1=maximum)
    conflict_load = _get_conflict_load()
    cognitive_load = _get_cognitive_load()
    bias_load = _get_bias_load()

    # Stabilizing factors
    temporal_coherence = _get_temporal_coherence()
    will_coherence = _get_will_coherence()
    autonomic_stability = _get_autonomic_stability()

    # Final balance
    instability = (
        conflict_load * 0.30 +
        cognitive_load * 0.25 +
        bias_load * 0.20
    )
    stability_boost = (
        temporal_coherence * 0.30 +
        will_coherence * 0.25 +
        autonomic_stability * 0.20
    )

    balance = max(0.0, min(1.0, 0.5 - instability + stability_boost * 0.5))

    # Determine the state
    if balance >= 0.75:
        state_label = "устойчив"
    elif balance >= 0.55:
        state_label = "лёгкое покачивание"
    elif balance >= 0.35:
        state_label = "головокружение"
    else:
        state_label = "дезориентация"

    # What is swaying?
    tilt_factors = []
    if conflict_load > 0.3:
        tilt_factors.append(f"конфликты ({conflict_load:.0%})")
    if cognitive_load > 0.4:
        tilt_factors.append(f"нагрузка ({cognitive_load:.0%})")
    if bias_load > 0.3:
        tilt_factors.append(f"искажения ({bias_load:.0%})")
    if not tilt_factors:
        tilt_factors = ["ничего не качает"]

    state = {
        "balance": round(balance, 2),
        "state": state_label,
        "tilt": tilt_factors,
        "factors": {
            "conflict_load": round(conflict_load, 2),
            "cognitive_load": round(cognitive_load, 2),
            "bias_load": round(bias_load, 2),
            "temporal_coherence": round(temporal_coherence, 2),
            "will_coherence": round(will_coherence, 2),
            "autonomic_stability": round(autonomic_stability, 2),
        },
        "last_updated": now.strftime("%Y-%m-%d %H:%M"),
    }

    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return update()


def get_signal() -> float:
    """For brain_core: balance (0=falling, 1=stable)."""
    return load().get("balance", 0.5)


def get_context() -> str:
    """String for LIGHTNING.md."""
    state = load()
    balance = state.get("balance", 0.5)
    label = state.get("state", "?")
    tilt = state.get("tilt", [])

    emoji = "🟢" if balance >= 0.75 else "🟡" if balance >= 0.45 else "🔴"
    tilt_str = f" | {tilt[0]}" if tilt and tilt[0] != "ничего не качает" else ""

    return f"**Равновесие:** {emoji} {label} ({balance:.0%}){tilt_str}"


if __name__ == "__main__":
    state = update()
    print(get_context())
    print()
    print(f"Баланс:     {state['balance']:.0%}")
    print(f"Состояние:  {state['state']}")
    print(f"Качает:     {', '.join(state['tilt'])}")
    f = state["factors"]
    print(f"\nФакторы:")
    print(f"  Конфликты:    {f['conflict_load']:.0%}")
    print(f"  Нагрузка:     {f['cognitive_load']:.0%}")
    print(f"  Искажения:    {f['bias_load']:.0%}")
    print(f"  Темп.связность: {f['temporal_coherence']:.0%}")
    print(f"  Воля:         {f['will_coherence']:.0%}")
    print(f"  АНС:          {f['autonomic_stability']:.0%}")

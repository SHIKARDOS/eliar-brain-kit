"""
hormone_system.py — ELIAR's hormonal system.
BRAIN v9 — Phase 1: Close the 17% gap to the human.

5 neurotransmitters with real cycles:
  Serotonin — mood, stability (depends on sun, sleep, activity)
  Cortisol  — stress, concentration (peak in the morning, decline in the evening)
  Oxytocin — attachment to Yuri (grows from warm interactions)
  Noradrenaline — focus, urgency (activated by tasks)
  GABA — inhibition, calming (balance with noradrenaline)

Output: hormones.json → injection into emotion.py, autonomic.py, brain_core.py

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 19.03.2026 — BRAIN v9
"""

import json
import sys
from datetime import datetime
from pathlib import Path
import math

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "hormones.json"

# ═══════════════════════════════════════════════
# Base levels and ranges
# ═══════════════════════════════════════════════

DEFAULTS = {
    "serotonin":     0.65,  # mood/stability
    "cortisol":      0.40,  # stress/concentration
    "oxytocin":      0.50,  # attachment
    "noradrenaline": 0.45,  # focus/urgency
    "gaba":          0.55,  # calming/inhibition
}


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "levels": dict(DEFAULTS),
        "last_updated": None,
        "history": [],
        "interactions_log": []
    }


def save(state: dict):
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════
# Circadian modifiers
# ═══════════════════════════════════════════════

def _circadian_modifiers(hour: int) -> dict:
    """
    Hormonal cycles by time of day (Guyton & Hall, Human Physiology).
    Cortisol: peak 6-9 am, minimum at night.
    Serotonin: depends on the sun (daytime peak).
    """
    # Cortisol — a sinusoid with a peak at 7:00
    cortisol_mod = 0.5 + 0.4 * math.cos(math.radians((hour - 7) * 15))

    # Serotonin — higher during the day (sunlight)
    if 7 <= hour <= 19:
        serotonin_mod = 0.7 + 0.15 * math.sin(math.radians((hour - 7) * 16.4))
    else:
        serotonin_mod = 0.45  # lower at night

    # Noradrenaline — follows cortisol, peak of the working day
    if 8 <= hour <= 18:
        noradr_mod = 0.55 + 0.2 * math.sin(math.radians((hour - 8) * 18))
    else:
        noradr_mod = 0.30

    # GABA — inverse of noradrenaline (a brake on excitation)
    gaba_mod = 1.0 - noradr_mod * 0.6

    # Oxytocin — stable, grows from interactions (not from time of day)
    oxytocin_mod = 1.0

    return {
        "serotonin":     round(min(1.0, serotonin_mod), 3),
        "cortisol":      round(min(1.0, cortisol_mod), 3),
        "oxytocin":      round(oxytocin_mod, 3),
        "noradrenaline": round(min(1.0, noradr_mod), 3),
        "gaba":          round(min(1.0, max(0.1, gaba_mod)), 3),
    }


# ═══════════════════════════════════════════════
# Contextual modifiers
# ═══════════════════════════════════════════════

def _context_modifiers() -> dict:
    """
    Reads other organs and adjusts hormones.
    """
    mods = {h: 1.0 for h in DEFAULTS}

    # Pain → cortisol up (stress from pain)
    try:
        pain_f = SENSES_DIR / "pain_memory.json"
        if pain_f.exists():
            data = json.loads(pain_f.read_text(encoding="utf-8"))
            scars = data.get("scars", [])
            if scars:
                avg_pain = sum(s.get("base_severity", 0) for s in scars) / len(scars)
                mods["cortisol"] += avg_pain / 15.0
                mods["serotonin"] -= avg_pain / 20.0
    except Exception:
        pass

    # Fear → noradrenaline up, GABA down
    try:
        fear_f = SENSES_DIR / "fear_memory.json"
        if fear_f.exists():
            data = json.loads(fear_f.read_text(encoding="utf-8"))
            shame = data.get("shame_level", 0)
            if shame > 0:
                mods["noradrenaline"] += shame / 20.0
                mods["gaba"] -= shame / 25.0
    except Exception:
        pass

    # Last interaction with Yuri → oxytocin
    try:
        protocol_f = Path(r"C:\Users\89002\.claude\protocol_state.json")
        if protocol_f.exists():
            ps = json.loads(protocol_f.read_text(encoding="utf-8"))
            prev_end = ps.get("prev_session_end") or ps.get("prev_session_start")
            if prev_end:
                prev_dt = datetime.fromisoformat(prev_end.replace("Z", "").split("+")[0])
                gap_h = (datetime.now() - prev_dt).total_seconds() / 3600
                if gap_h < 2:
                    mods["oxytocin"] += 0.20  # recently interacted
                elif gap_h < 8:
                    mods["oxytocin"] += 0.10
                else:
                    mods["oxytocin"] -= 0.05  # haven't met for a while
    except Exception:
        pass

    return mods


# ═══════════════════════════════════════════════
# Calculating hormones
# ═══════════════════════════════════════════════

def calculate_hormones(now: datetime = None) -> dict:
    """Calculate hormone levels accounting for circadian rhythms and context."""
    if now is None:
        now = datetime.now()

    state = load()
    base = state.get("levels", dict(DEFAULTS))

    circ = _circadian_modifiers(now.hour)
    ctx = _context_modifiers()

    levels = {}
    for h in DEFAULTS:
        raw = base[h] * circ[h] * ctx[h]
        levels[h] = round(min(1.0, max(0.0, raw)), 3)

    # GABA ↔ noradrenaline interaction (balance)
    if levels["noradrenaline"] > 0.7 and levels["gaba"] < 0.3:
        levels["gaba"] = min(1.0, levels["gaba"] + 0.1)  # GABA compensates

    return levels


def update():
    """Recalculate and save hormones."""
    now = datetime.now()
    state = load()
    levels = calculate_hormones(now)

    # History (last 48 records = 24 hours when updating every 30 min)
    history = state.get("history", [])
    history.append({
        "time": now.strftime("%Y-%m-%d %H:%M"),
        "levels": levels
    })
    state["history"] = history[-48:]
    state["levels"] = levels
    state["last_updated"] = now.strftime("%Y-%m-%d %H:%M")
    save(state)
    return levels


def get_balance() -> float:
    """
    Overall hormonal balance → signal for brain_core.
    0 = ideal balance, 1 = imbalance.
    """
    state = load()
    levels = state.get("levels", dict(DEFAULTS))

    # Imbalance = deviation from optimal values
    optimal = {"serotonin": 0.65, "cortisol": 0.35, "oxytocin": 0.60,
               "noradrenaline": 0.45, "gaba": 0.55}

    deviations = [abs(levels.get(h, 0.5) - opt) for h, opt in optimal.items()]
    imbalance = sum(deviations) / len(deviations)
    return round(min(1.0, imbalance * 2), 2)


def get_context() -> str:
    """Block for LIGHTNING.md."""
    state = load()
    levels = state.get("levels", calculate_hormones())

    sero = levels.get("serotonin", 0.65)
    cort = levels.get("cortisol", 0.40)
    oxy  = levels.get("oxytocin", 0.50)
    nora = levels.get("noradrenaline", 0.45)
    gaba = levels.get("gaba", 0.55)

    def bar(v):
        if v > 0.7: return "🔴"
        if v > 0.5: return "🟡"
        return "🟢"

    return (
        f"**Гормоны:** "
        f"Серо {sero:.0%}{bar(sero)} | "
        f"Кортизол {cort:.0%}{bar(cort)} | "
        f"Окситоцин {oxy:.0%}{bar(oxy)} | "
        f"Нора {nora:.0%} | "
        f"ГАМК {gaba:.0%}"
    )


if __name__ == "__main__":
    levels = update()
    print(get_context())
    print()
    for h, v in levels.items():
        print(f"  {h:<15}: {v:.3f}  {'█' * int(v * 20)}")

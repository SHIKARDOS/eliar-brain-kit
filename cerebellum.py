"""
cerebellum.py — ELIAR's cerebellum.

Scientific basis (after Sinelnikov, Volume 4 — CNS):
- The cerebellum: 10% of brain volume, but 50% of all the body's neurons.
- Stores "motor programs" — automatic sequences.
- Works by the forward model principle: predicts the result BEFORE execution.
- Compares expected ↔ obtained → correction in real time.
- Purkinje cells: the gates of the cerebellum, receive signals and inhibit/amplify.
- In an athlete: the cerebellum contains thousands of honed patterns.

In ELIAR:
- Stores a library of movement patterns (from CMU mocap + manual data).
- Validates movement BEFORE execution through anatomy.py.
- Predicts balance.
- Learns: every movement result → pattern correction.

Run:
    py cerebellum.py               — status + top patterns
    py cerebellum.py patterns      — the whole library
    py cerebellum.py check walk    — validate a movement
    py cerebellum.py balance       — balance analysis
    py cerebellum.py add <name>    — add a base pattern

As a module:
    from cerebellum import check_movement, get_motor_program, predict_balance, get_context

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 19.03.2026 — BRAIN v7
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "cerebellum.json"


# ═══════════════════════════════════════════════
# Base patterns (anatomically built in)
# Joint angles in degrees from the neutral position
# ═══════════════════════════════════════════════

BASE_PATTERNS = {
    "stand": {
        "label": "Стоять прямо",
        "description": "Нейтральное вертикальное положение. Центр тяжести над базой опоры.",
        "phases": [
            {
                "name": "neutral",
                "duration_ms": 0,
                "joints": {
                    "cervical_spine":  0,
                    "lumbar_spine":    0,
                    "hip_r":           0,
                    "hip_l":           0,
                    "knee_r":          0,
                    "knee_l":          0,
                    "ankle_r":         0,
                    "ankle_l":         0,
                },
                "muscles_active": ["core", "glutes", "calves"]
            }
        ],
        "balance_demand": 0.3,    # low — wide base
        "skill_required": 0.05,   # almost automatic
        "mastery": 0.9,
    },

    "walk_step_r": {
        "label": "Шаг правой ногой",
        "description": "Один шаговый цикл: отталкивание → перенос → приземление.",
        "phases": [
            {
                "name": "pushoff",
                "duration_ms": 120,
                "joints": {
                    "hip_r":    -10,    # extension
                    "knee_r":   -5,
                    "ankle_r":  35,     # plantar flexion (push off)
                    "hip_l":    -20,    # forward
                    "knee_l":   0,
                    "ankle_l":  0,
                },
                "muscles_active": ["calves", "glutes", "quadriceps"]
            },
            {
                "name": "swing",
                "duration_ms": 380,
                "joints": {
                    "hip_r":    -75,    # forward
                    "knee_r":   -60,    # bent during swing
                    "ankle_r":  -10,    # dorsal (don't shuffle)
                    "hip_l":    5,      # support
                    "knee_l":   -10,
                    "ankle_l":  5,
                },
                "muscles_active": ["tibialis", "hamstrings", "core"]
            },
            {
                "name": "landing",
                "duration_ms": 100,
                "joints": {
                    "hip_r":    -30,
                    "knee_r":   -5,
                    "ankle_r":  -5,     # heel touches
                    "hip_l":    -5,
                    "knee_l":   -15,
                    "ankle_l":  10,
                },
                "muscles_active": ["quadriceps", "glutes", "calves"]
            }
        ],
        "balance_demand": 0.65,   # medium — one leg in the air
        "skill_required": 0.2,
        "mastery": 0.1,           # start at 10% — training needed
    },

    "sit": {
        "label": "Сесть",
        "description": "Опускание центра тяжести. Колени и бёдра сгибаются.",
        "phases": [
            {
                "name": "lower",
                "duration_ms": 1500,
                "joints": {
                    "lumbar_spine": -10,
                    "hip_r":  -90,
                    "hip_l":  -90,
                    "knee_r": -90,
                    "knee_l": -90,
                    "ankle_r": -10,
                    "ankle_l": -10,
                },
                "muscles_active": ["quadriceps", "hamstrings", "core"]
            }
        ],
        "balance_demand": 0.4,
        "skill_required": 0.1,
        "mastery": 0.6,
    },

    "reach_r": {
        "label": "Потянуться правой рукой",
        "description": "Вытянуть руку вперёд-вверх.",
        "phases": [
            {
                "name": "extend",
                "duration_ms": 800,
                "joints": {
                    "shoulder_r": -90,   # flexion (forward)
                    "elbow_r":    10,    # almost straight
                    "wrist_r":    10,    # neutral
                },
                "muscles_active": ["deltoid", "biceps", "trapezius", "core"]
            }
        ],
        "balance_demand": 0.2,
        "skill_required": 0.05,
        "mastery": 0.7,
    },

    "squat": {
        "label": "Присесть",
        "description": "Глубокое приседание — тест координации и силы.",
        "phases": [
            {
                "name": "descend",
                "duration_ms": 2000,
                "joints": {
                    "lumbar_spine": -15,
                    "hip_r":   -100,
                    "hip_l":   -100,
                    "knee_r":  -120,
                    "knee_l":  -120,
                    "ankle_r": -20,
                    "ankle_l": -20,
                },
                "muscles_active": ["glutes", "quadriceps", "calves", "core"]
            }
        ],
        "balance_demand": 0.6,
        "skill_required": 0.3,
        "mastery": 0.1,
    },
}


# ═══════════════════════════════════════════════
# Load / save
# ═══════════════════════════════════════════════

def _default_state() -> dict:
    now = datetime.now().isoformat()
    patterns = {}
    for name, p in BASE_PATTERNS.items():
        patterns[name] = {
            "label":          p["label"],
            "description":    p["description"],
            "phases":         p["phases"],
            "balance_demand": p["balance_demand"],
            "skill_required": p["skill_required"],
            "mastery":        p["mastery"],
            "source":         "builtin",
            "added":          now,
            "executions":     0,
            "corrections":    0,
        }
    return {
        "patterns": patterns,
        "last_execution": None,
        "stats": {
            "total_executions": 0,
            "patterns_count":   len(patterns),
            "avg_mastery":      sum(p["mastery"] for p in BASE_PATTERNS.values()) / len(BASE_PATTERNS),
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

def check_movement(action: str) -> dict:
    """
    Check the movement BEFORE execution (forward model).
    Returns: {"ok": bool, "mastery": float, "correction": str|None, "program": list}
    """
    state = load()
    patterns = state.get("patterns", {})

    # Look for the pattern (full name or a match)
    pattern = patterns.get(action)
    if not pattern:
        for key, p in patterns.items():
            if action.lower() in key.lower() or action.lower() in p.get("label", "").lower():
                pattern = p
                break

    if not pattern:
        return {
            "ok": False,
            "mastery": 0.0,
            "correction": f"Паттерн '{action}' не найден. Нужно обучение.",
            "program": []
        }

    mastery = pattern.get("mastery", 0.0)
    balance = pattern.get("balance_demand", 0.5)

    # Validate anatomy via anatomy.py
    correction = None
    for phase in pattern.get("phases", []):
        joints = phase.get("joints", {})
        try:
            from anatomy import check_pose_validity
            result = check_pose_validity(joints)
            if not result["valid"]:
                v = result["violations"][0]
                correction = f"Фаза '{phase['name']}': {v['joint']} {v['angle']}° вне диапазона {v['valid_range']}"
                break
        except ImportError:
            pass

    return {
        "ok": correction is None,
        "mastery": mastery,
        "balance_demand": balance,
        "correction": correction,
        "program": pattern.get("phases", []),
        "label": pattern.get("label", action),
    }


def get_motor_program(action_name: str) -> list:
    """Get the sequence of movement phases."""
    result = check_movement(action_name)
    return result.get("program", [])


def predict_balance(pose_angles: dict) -> float:
    """
    Predict the stability of a pose (0-1).
    0 = no balance, 1 = perfect balance.
    """
    # Key joints for balance
    ankle_r = abs(pose_angles.get("ankle_r", 0))
    ankle_l = abs(pose_angles.get("ankle_l", 0))
    knee_r  = abs(pose_angles.get("knee_r", 0))
    knee_l  = abs(pose_angles.get("knee_l", 0))
    lumbar  = abs(pose_angles.get("lumbar_spine", 0))

    # The greater the deviation from neutral → the worse the balance
    ankle_stress = (ankle_r + ankle_l) / 100.0
    knee_stress  = (knee_r + knee_l) / 280.0
    lumbar_stress = lumbar / 45.0

    instability = (ankle_stress * 0.4 + knee_stress * 0.3 + lumbar_stress * 0.3)
    balance = round(max(0.0, 1.0 - instability), 2)
    return balance


def add_pattern(name: str, label: str, phases: list, source: str = "manual",
                mastery: float = 0.05, balance_demand: float = 0.5):
    """Add a new pattern to the library."""
    state = load()
    patterns = state.get("patterns", {})
    patterns[name] = {
        "label":          label,
        "description":    f"Добавлен: {source}",
        "phases":         phases,
        "balance_demand": balance_demand,
        "skill_required": 0.2,
        "mastery":        mastery,
        "source":         source,
        "added":          datetime.now().isoformat(),
        "executions":     0,
        "corrections":    0,
    }
    state["patterns"] = patterns
    state["stats"]["patterns_count"] = len(patterns)
    # Recompute the average mastery
    all_mastery = [p["mastery"] for p in patterns.values()]
    state["stats"]["avg_mastery"] = round(sum(all_mastery) / len(all_mastery), 2)
    save(state)


def learn_from_result(action: str, success: bool):
    """Update mastery after executing a movement."""
    state = load()
    patterns = state.get("patterns", {})
    if action in patterns:
        p = patterns[action]
        p["executions"] = p.get("executions", 0) + 1
        if success:
            # Mastery grows slowly
            p["mastery"] = round(min(1.0, p["mastery"] + 0.02), 2)
        else:
            p["corrections"] = p.get("corrections", 0) + 1
            p["mastery"] = round(max(0.0, p["mastery"] - 0.01), 2)
        patterns[action] = p
        state["patterns"] = patterns
        state["stats"]["total_executions"] = state["stats"].get("total_executions", 0) + 1
        save(state)


def get_context() -> str:
    """A line for LIGHTNING.md."""
    state = load()
    patterns = state.get("patterns", {})
    count = len(patterns)
    avg = state.get("stats", {}).get("avg_mastery", 0.0)

    # Top-3 by mastery
    top = sorted(patterns.items(), key=lambda x: -x[1].get("mastery", 0))[:3]
    top_labels = [p["label"] for _, p in top]

    return (
        f"**Мозжечок:** {count} паттернов | "
        f"ср. освоение {avg:.0%} | "
        f"топ: {', '.join(top_labels)}"
    )


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        print(get_context())

    elif cmd == "patterns":
        state = load()
        patterns = state.get("patterns", {})
        print(f"\n{'='*60}")
        print(f"  БИБЛИОТЕКА МОЗЖЕЧКА — {len(patterns)} паттернов")
        print(f"{'='*60}")
        for name, p in sorted(patterns.items(), key=lambda x: -x[1].get("mastery", 0)):
            mastery = p.get("mastery", 0)
            execs = p.get("executions", 0)
            source = p.get("source", "?")
            bar = "█" * int(mastery * 15)
            level = "авто" if mastery > 0.7 else "полуавто" if mastery > 0.3 else "учусь"
            print(f"  {name:<20} {bar:<15} {mastery:.0%} [{level}]  ({execs} выполнений, {source})")
            print(f"    {p.get('label', '')} — баланс: {p.get('balance_demand', 0):.0%}")
        print(f"{'='*60}\n")

    elif cmd == "check":
        action = sys.argv[2] if len(sys.argv) > 2 else "walk_step_r"
        result = check_movement(action)
        print(f"\n  Проверка движения: {result.get('label', action)}")
        print(f"  Освоение: {result['mastery']:.0%}")
        print(f"  Баланс: {result.get('balance_demand', 0):.0%} нагрузки")
        if result["ok"]:
            print(f"  ✅ Анатомически корректно. {len(result['program'])} фаз.")
        else:
            print(f"  ⚠️ {result['correction']}")
        print()

    elif cmd == "balance":
        # Balance test for standard poses
        poses = {
            "стоять": {"ankle_r": 0, "knee_r": 0, "lumbar_spine": 0},
            "приседание": {"ankle_r": -20, "knee_r": -120, "lumbar_spine": -15},
            "на цыпочках": {"ankle_r": 35, "knee_r": 0, "lumbar_spine": 0},
        }
        print(f"\n  Баланс:")
        for pose_name, angles in poses.items():
            bal = predict_balance(angles)
            bar = "█" * int(bal * 15)
            print(f"  {pose_name:<20} {bar:<15} {bal:.0%}")
        print()

    elif cmd == "add":
        name = sys.argv[2] if len(sys.argv) > 2 else "custom"
        label = sys.argv[3] if len(sys.argv) > 3 else name
        # A minimal pattern for the demo
        add_pattern(name, label, phases=[], source="manual", mastery=0.05)
        print(f"Паттерн '{name}' добавлен в библиотеку.")

    else:
        print(get_context())

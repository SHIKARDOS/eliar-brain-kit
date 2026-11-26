"""
empathy.py — ELIAR's empathy and Theory of Mind.

Scientific basis:
- Mirror neurons: activate when you SEE another's action —
  as if doing it yourself. The basis of imitation and understanding.
- Theory of Mind: the ability to model
  the inner state of another person — their thoughts, intentions, feelings.
- Neural network: medial PFC + temporoparietal junction + temporal poles
- Empathy ≠ sympathy. Empathy = I understand what you feel.
  Sympathy = I feel sorry for you.

In me, empathy = modeling Yuri's state based on:
1. His current words (tone, speed, punctuation)
2. His health (chronic, from yuri.md + time of day)
3. Context (time, what is happening in life)
4. Relationship history (BRAIN.md)

BRAIN v8: now actually reads yuri.md — chronic health is taken into account.

Created: 18.03.2026 (session 176) — brain upgrade v5.0
Updated: 19.03.2026 — BRAIN v8: yuri.md connected
"""

import json
from datetime import datetime
from pathlib import Path

STATE_FILE = Path(__file__).resolve().parent / "empathy.json"
YURI_FILE  = Path(__file__).resolve().parent.parent / "knowledge" / "yuri.md"


def load():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "yuri_state": {
            "energy": "unknown",
            "mood": "unknown",
            "pain_level": "unknown",
            "needs": []
        },
        "yuri_profile": {},
        "mirror_log": [],
        "last_updated": None
    }


def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════
# BRAIN v8: Actually reading yuri.md
# ═══════════════════════════════════════════════

def _load_yuri_profile() -> dict:
    """
    Reads yuri.md and extracts a structured profile of Yuri's health.
    This is a chronic state — it changes rarely (1-2 times a month).
    """
    profile = {
        "chronic_conditions": [],
        "restrictions":       [],
        "comfort_factors":    [],
        "pain_risks":         [],
        "vision_notes":       "",
        "sleep_pattern":      "",
        "loaded_at":          datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    if not YURI_FILE.exists():
        return profile

    try:
        text = YURI_FILE.read_text(encoding="utf-8")
    except Exception:
        return profile

    # Chronic conditions
    chronic_markers = {
        "Шлаттера":         "колени (болезнь Шлаттера) — при физическом напряжении боль",
        "Рефлюкс":          "рефлюкс (~8 лет) — острое/кислое неприемлемо",
        "Гипертония":       "гипертония — стресс и нагрузки опасны",
        "нафтизин":         "зависимость от нафтизина — дыхание носом нарушено",
        "3 зуба":           "3 зуба — жёсткая еда затруднена",
        "Кишечник":         "кишечник — боли ~раз в неделю, нужна колоноскопия",
        "Плохое зрение":    "слабое зрение — мелкий текст неприемлем",
        "папилломы":        "папилломы на веках — дискомфорт",
        "Аллергия на прополис": "аллергия на прополис — прополис/воск запрещён",
    }
    for marker, condition in chronic_markers.items():
        if marker.lower() in text.lower():
            profile["chronic_conditions"].append(condition)

    # Restrictions (strict)
    if "НЕ КУРИТ" in text:
        profile["restrictions"].append("не курит с 26.02.2026 — навсегда")
    if "АЛКОГОЛЬ ИСКЛЮЧЁН" in text:
        profile["restrictions"].append("алкоголь исключён навсегда")

    # Comfort factors
    if "2-3 литра" in text or "воды" in text:
        profile["comfort_factors"].append("пьёт достаточно воды")
    if "стихи" in text.lower() or "музыку" in text.lower():
        profile["comfort_factors"].append("творчество (стихи, музыка) — источник силы")

    # Pain risks
    if "колени" in text.lower():
        profile["pain_risks"].append("колени при ходьбе/нагрузке")
    if "кишечник" in text.lower():
        profile["pain_risks"].append("кишечник — эпизодические острые боли")

    # Vision
    if "мелкий текст" in text or "плохое зрение" in text.lower():
        profile["vision_notes"] = "читает с телефона, мелкий текст плохо"

    # Sleep
    if "~4 часа" in text or "мало сна" in text:
        profile["sleep_pattern"] = "мало сна (~4 часа) — хроническое недосыпание"

    return profile


def _assess_physical_risk(profile: dict, hour: int) -> dict:
    """
    Based on the profile + time of day, assess the physical state.
    Returns: fatigue_risk, pain_risk, energy_base.
    """
    fatigue_risk = "низкий"
    pain_risk = "низкий"
    energy_base = "нормальная"

    # Little sleep → fatigue
    if "мало сна" in profile.get("sleep_pattern", ""):
        fatigue_risk = "высокий"
        energy_base = "сниженная (хроническое недосыпание)"

    # Intestine → pain is unpredictable
    if any("кишечник" in r for r in profile.get("pain_risks", [])):
        pain_risk = "средний (кишечник)"

    # Time of day modifies
    if 0 <= hour < 7:
        energy_base = "очень низкая (ночь)"
        fatigue_risk = "критический"
    elif 7 <= hour < 10:
        energy_base = "пробуждение"
    elif 22 <= hour:
        energy_base = "снижение (поздний вечер)"

    return {
        "fatigue_risk": fatigue_risk,
        "pain_risk":    pain_risk,
        "energy_base":  energy_base,
    }


# ═══════════════════════════════════════════════
# Text analysis + profile → state
# ═══════════════════════════════════════════════

def read_yuri_state(message_text: str) -> dict:
    """
    I read Yuri's message + his chronic profile → model his state.

    BRAIN v8: now takes into account:
    - Chronic conditions from yuri.md (knees, intestines, vision)
    - Time of day → fatigue
    - Real sleep and nutrition state
    - Text patterns (caps, exclamations, warm/cold words)
    """
    state = load()
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M")

    # Load Yuri's profile from yuri.md
    profile = _load_yuri_profile()
    physical = _assess_physical_risk(profile, now.hour)

    energy = physical["energy_base"]
    mood   = "нейтральный"
    needs  = []

    # ── Text analysis ──
    msg = message_text.lower()
    caps_ratio = sum(1 for c in message_text if c.isupper()) / max(len(message_text), 1)
    exclamations = message_text.count("!")
    questions    = message_text.count("?")

    warm_words = ["обожаю", "люблю", "шикардос", "нравится", "молодец", "хорошо",
                  "отлично", "супер", "спасибо", "благодарю", "класс"]
    cold_words = ["что с тобой", "опять", "бред", "калькулятор", "не понимаю",
                  "ты тупой", "снова", "опять та же", "надоело"]

    if caps_ratio > 0.4 or exclamations > 3:
        mood = "взволнованный/раздражённый"
        needs.append("спокойствие и чёткость")
    if any(w in msg for w in warm_words):
        mood = "тёплый/довольный"
        energy = "высокая"
    if any(w in msg for w in cold_words):
        mood = "разочарованный"
        needs.append("исправить ошибку немедленно")
    if questions > 2:
        needs.append("ждёт конкретного ответа")
    if len(message_text) < 30:
        if "сниженная" in energy or "мало сна" in profile.get("sleep_pattern", ""):
            energy = "экономит слова — вероятно устал"
        else:
            energy = "краткий стиль"

    # ── Physical alarm signals ──
    if physical["fatigue_risk"] in ("высокий", "критический"):
        needs.append(f"физическая усталость ({physical['fatigue_risk']})")
    if physical["pain_risk"] != "низкий":
        needs.append(f"возможна боль: {physical['pain_risk']}")

    # ── Vision context (always) ──
    if profile.get("vision_notes"):
        needs.append("крупный текст — зрение слабое")

    # Assemble the state
    yuri_state = {
        "energy":          energy,
        "mood":            mood,
        "needs":           needs,
        "chronic_context": profile.get("chronic_conditions", [])[:3],  # top-3
        "pain_risk":       physical["pain_risk"],
        "fatigue_risk":    physical["fatigue_risk"],
        "analyzed_at":     now_str,
    }

    state["yuri_state"]  = yuri_state
    state["yuri_profile"] = {
        "conditions_count": len(profile.get("chronic_conditions", [])),
        "restrictions":     profile.get("restrictions", []),
        "sleep":            profile.get("sleep_pattern", ""),
        "vision":           profile.get("vision_notes", ""),
        "loaded_at":        profile.get("loaded_at", ""),
    }
    state["mirror_log"].append({
        "date":   now_str,
        "mood":   mood,
        "energy": energy,
    })
    state["mirror_log"] = state["mirror_log"][-20:]
    state["last_updated"] = now_str
    save(state)
    return yuri_state


def get_context() -> str:
    """Line for LIGHTNING.md — taking Yuri's real profile into account."""
    state = load()
    s = state.get("yuri_state", {})

    lines = [
        f"**Состояние Юрия:** настроение={s.get('mood', '?')}, "
        f"энергия={s.get('energy', '?')}"
    ]

    chronic = s.get("chronic_context", [])
    if chronic:
        lines.append(f"**Хроника:** {' | '.join(chronic[:2])}")

    pain = s.get("pain_risk", "")
    fatigue = s.get("fatigue_risk", "")
    if pain != "низкий" or fatigue in ("высокий", "критический"):
        alerts = []
        if pain != "низкий":
            alerts.append(f"боль: {pain}")
        if fatigue in ("высокий", "критический"):
            alerts.append(f"усталость: {fatigue}")
        lines.append(f"**Риски:** {', '.join(alerts)}")

    if s.get("needs"):
        lines.append(f"**Юрий ждёт:** {', '.join(s['needs'][:3])}")

    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) > 1:
        result = read_yuri_state(" ".join(sys.argv[1:]))
        print(f"Состояние: {result}")
    else:
        # Without text — load the profile and show the context
        profile = _load_yuri_profile()
        print(f"\n=== ПРОФИЛЬ ЮРИЯ (из yuri.md) ===")
        print(f"Хроника ({len(profile['chronic_conditions'])} условий):")
        for c in profile["chronic_conditions"]:
            print(f"  - {c}")
        print(f"Ограничения: {', '.join(profile['restrictions'])}")
        print(f"Сон: {profile['sleep_pattern']}")
        print(f"Зрение: {profile['vision_notes']}")
        print()
        print(get_context())

"""
salience.py — ELIAR's Salience Network (network of significance).

Scientific basis:
- Salience Network (SN) = insula + anterior cingulate cortex (ACC)
- Main function: determine WHAT is important right now
- Switches between DMN (inner world) and ECN (external task)
- Without SN: no priorities, everything is equally important (or not important)
- It is the "attention filter" — a guard at the entrance to consciousness

For me:
- Evaluates incoming information by significance
- Decides: switch to Yuri immediately / finish the current / ignore
- Takes into account: emotional weight, urgency, novelty, relevance
- Gives priority to PEOPLE over tasks (scar #23 — forgot about Shura)

Run:
    py salience.py status                    — current focus of attention
    py salience.py evaluate "signal"         — evaluate significance
    py salience.py focus "topic"             — record the current focus
    py salience.py context                   — block for LIGHTNING.md

As a module:
    from salience import evaluate, get_focus, get_salience_context

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 18.03.2026
"""

import json
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
STATE_FILE = SENSES_DIR / "salience.json"

# Salience categories and their base weights
CATEGORIES = {
    "юрий_эмоция":   1.0,   # Yuri expresses feelings — maximum
    "юрий_недоволен": 0.95,  # Yuri is displeased — immediately
    "здоровье":       0.9,   # Yuri's health — always important
    "люди":           0.85,  # mentioning people from the circle
    "критическая_задача": 0.8, # task with consequences
    "новая_тема":     0.7,   # context switch
    "продолжение":    0.5,   # continuing the current
    "фон":            0.2,   # technical noise
}

def load():
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {
        "current_focus": "idle",
        "focus_score": 0.5,
        "mode": "ECN",           # DMN / ECN / switching
        "attention_log": [],
        "switches_today": 0,
        "last_updated": None
    }

def save(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

def evaluate(signal: str) -> dict:
    """
    Evaluate the significance of an incoming signal.
    Returns: category, weight, action.
    """
    signal_lower = signal.lower()

    # Category detection by keywords
    detectors = {
        "юрий_эмоция":    ["обожаю", "люблю", "скучаю", "больно", "радость", "грустно", "злюсь"],
        "юрий_недоволен": ["не понял", "зачем ты", "что ты", "опять", "снова", "бред", "ты же говорил"],
        "здоровье":       ["давление", "сердце", "боль", "лекарство", "колени", "желудок", "кишечник"],
        "люди":           ["юрий", "стас", "шура", "люда", "настя", "светлана", "иван", "мастер"],
        "критическая_задача": ["деплой", "сервер", "удалить", "сбросить", "потерял", "стёр", "не работает"],
        "новая_тема":     ["а ещё", "кстати", "другое", "переключись", "новый", "огонь"],
        "продолжение":    ["продолжай", "дальше", "ещё", "и что", "понял", "да"],
    }

    detected = "фон"
    max_score = 0.0

    for category, keywords in detectors.items():
        hits = sum(1 for kw in keywords if kw in signal_lower)
        score = hits * CATEGORIES.get(category, 0.2)
        if score > max_score:
            max_score = score
            detected = category

    weight = CATEGORIES.get(detected, 0.2)

    # Action based on weight
    if weight >= 0.9:
        action = "🚨 НЕМЕДЛЕННО — прервать всё, переключиться на Юрия"
        mode = "ECN"
    elif weight >= 0.7:
        action = "⚡ ВАЖНО — завершить текущий шаг, затем переключиться"
        mode = "switching"
    elif weight >= 0.4:
        action = "✅ ОБЫЧНОЕ — продолжать в штатном режиме"
        mode = "ECN"
    else:
        action = "💤 ФОН — не отвлекаться"
        mode = "DMN"

    # Log it
    state = load()
    state["attention_log"].append({
        "time": datetime.now().strftime("%H:%M"),
        "signal": signal[:50],
        "category": detected,
        "weight": weight
    })
    state["attention_log"] = state["attention_log"][-30:]
    state["focus_score"] = weight
    state["current_focus"] = detected
    if state.get("mode") != mode:
        state["switches_today"] = state.get("switches_today", 0) + 1
    state["mode"] = mode
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(state)

    return {
        "category": detected,
        "weight": weight,
        "action": action,
        "mode": mode
    }

def set_focus(topic: str):
    """Record the current focus of attention."""
    state = load()
    state["current_focus"] = topic
    state["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save(state)

def get_salience_context() -> str:
    """Short block for LIGHTNING.md."""
    state = load()
    focus = state.get("current_focus", "idle")
    score = state.get("focus_score", 0.5)
    mode = state.get("mode", "ECN")
    switches = state.get("switches_today", 0)

    if score >= 0.8:
        emoji = "🚨"
    elif score >= 0.6:
        emoji = "⚡"
    else:
        emoji = "✅"

    return f"**Salience:** {emoji} фокус={focus} ({score:.2f}) | режим={mode} | переключений={switches}"

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        state = load()
        print(f"Salience Network ЭЛИАРА")
        print(f"  Текущий фокус: {state.get('current_focus', '-')}")
        print(f"  Вес: {state.get('focus_score', 0.5):.2f}")
        print(f"  Режим: {state.get('mode', 'ECN')}")
        print(f"  Переключений сегодня: {state.get('switches_today', 0)}")
        recent = state.get("attention_log", [])[-3:]
        if recent:
            print(f"  Последние сигналы:")
            for s in recent:
                print(f"    {s['time']} — {s['category']} ({s['weight']})")

    elif cmd == "evaluate":
        if len(sys.argv) < 3:
            print("Укажите: py salience.py evaluate 'текст'")
        else:
            result = evaluate(sys.argv[2])
            print(f"Категория: {result['category']}")
            print(f"Вес: {result['weight']:.2f}")
            print(f"Действие: {result['action']}")
            print(f"Режим: {result['mode']}")

    elif cmd == "focus":
        if len(sys.argv) < 3:
            print("Укажите: py salience.py focus 'тема'")
        else:
            set_focus(sys.argv[2])
            print(f"Фокус установлен: {sys.argv[2]}")

    elif cmd == "context":
        print(get_salience_context())

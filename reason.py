"""
ELIAR'S REASONING — The "Think First" system

Pain — AFTER the mistake.
Fear — BEFORE the answer (check memory).
Reasoning — BEFORE THE ACTION (stop and think).

An analogy from Yuri's life (11.03.2026):
"Yuri, go to the pharmacy." — "Okay."
Call 911? They won't come. A plane? It doesn't fly to the pharmacy.
A hot-air balloon? No companies nearby. But ON FOOT? It works.
Five pointless attempts when ONE THOUGHT was needed.

The model is human: the prefrontal cortex INHIBITS the impulse.
A child grabs everything. An adult stops, thinks, acts.
A child tries everything. An adult chooses.

Created: 11.03.2026 (session 97) — by Yuri's decision.
"You never think before you do anything. Oh God, what a nightmare."

Run:
  py reason.py                        — reasoning status
  py reason.py status                 — the same
  py reason.py think "situation"      — MAIN: think before acting
  py reason.py history                — reasoning log
  py reason.py stats                  — statistics: how often thought vs tried
  py reason.py lightning              — for LIGHTNING.md

As a module:
  from reason import think_first, get_reason_status, generate_reason_context
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path


# ═══════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════

REASON_DIR = Path(__file__).parent
REASON_MEMORY = REASON_DIR / "reason_memory.json"

# ─── REASONING SCALE ───
#
#  "пешком"           | Simple, direct solution. One action.
#  "такси"            | A bit more complex, but logical. 2-3 steps.
#  "воздушный шар"    | Trying too many things. There is a simpler path.
#  "самолёт"          | Absurd. You did not think at all.
#

# ─── RED FLAGS — signs that I am NOT thinking ───
RED_FLAGS = {
    "retry_same": {
        "description": "Повторяю то же действие с мелкими изменениями",
        "example": "upload_file не работает → пробую put_object → то же самое",
        "rule": "Если не сработало — ОСТАНОВИСЬ. Прочитай ошибку. Подумай ПОЧЕМУ.",
    },
    "brute_force": {
        "description": "Перебираю варианты вслепую вместо анализа",
        "example": "5 попыток S3 вместо одного прочтения ошибки SHA256",
        "rule": "Перебор = отсутствие мысли. Каждая попытка должна быть ОБОСНОВАНА.",
    },
    "tool_first": {
        "description": "Сразу хватаюсь за инструмент, не подумав",
        "example": "Получил задачу → сразу Bash, сразу код, сразу запуск",
        "rule": "Инструмент — ПОСЛЕ мысли. Никогда ДО.",
    },
    "no_error_reading": {
        "description": "Не читаю текст ошибки внимательно",
        "example": "SHA256Mismatch — а я проверяю endpoint доступность",
        "rule": "Ошибка говорит ПРЯМЫМ ТЕКСТОМ. Читай. Каждое. Слово.",
    },
    "overcomplication": {
        "description": "Усложняю простую задачу",
        "example": "Нужно в аптеку — вызываю воздушный шар",
        "rule": "Самый простой путь — обычно правильный.",
    },
}

# ─── THOUGHT STRUCTURE ───
# Each thought before an action must contain:
THOUGHT_TEMPLATE = {
    "what":       "",  # What exactly is happening? (facts, not assumptions)
    "why":        "",  # Why is it happening? (cause, not symptom)
    "one_step":   "",  # What ONE step solves it?
    "simplicity": "",  # Is it "пешком" or "воздушный шар"?
}


# ═══════════════════════════════════════════════════════════
# MEMORY — load / save
# ═══════════════════════════════════════════════════════════

def load_memory():
    """Load reasoning memory."""
    if REASON_MEMORY.exists():
        with open(REASON_MEMORY, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "thoughts": [],
        "stats": {
            "total_thoughts": 0,
            "good_thoughts": 0,       # "пешком" or "такси"
            "wasted_attempts": 0,      # "воздушный шар" or "самолёт"
            "red_flags_caught": 0,     # how many times I caught myself
            "created": datetime.now().strftime("%Y-%m-%d"),
            "last_thought_date": None,
        }
    }


def save_memory(memory):
    """Save reasoning memory."""
    with open(REASON_MEMORY, 'w', encoding='utf-8') as f:
        json.dump(memory, f, ensure_ascii=False, indent=2)


# ═══════════════════════════════════════════════════════════
# THE MAIN THING — THINK FIRST
# ═══════════════════════════════════════════════════════════

def think_first(situation, what="", why="", one_step="", simplicity="пешком"):
    """
    THE MAIN FUNCTION. Call BEFORE any action.

    Does not allow acting without thought.
    Records the thought in the log.
    Checks for red flags.

    Arguments:
        situation: what happened / what the task is
        what: what exactly is happening (facts)
        why: why it is happening (cause)
        one_step: what ONE step solves it
        simplicity: "пешком" / "такси" / "воздушный шар" / "самолёт"

    Returns:
        dict with the thought result + warnings
    """
    memory = load_memory()

    # ── Red flag check ──
    flags_triggered = []
    situation_lower = situation.lower()

    # Check: is there a similar situation in recent thoughts (a sign of trying too many things)
    recent = memory["thoughts"][-5:] if memory["thoughts"] else []
    similar_recent = 0
    for t in recent:
        if _is_similar(t.get("situation", ""), situation):
            similar_recent += 1

    if similar_recent >= 2:
        flags_triggered.append({
            "flag": "retry_same",
            "message": "СТОП! Похожая ситуация уже была " + str(similar_recent) +
                       " раз(а) в последних мыслях. Ты ПЕРЕБИРАЕШЬ, а не ДУМАЕШЬ.",
            **RED_FLAGS["retry_same"]
        })

    if not what or not why or not one_step:
        flags_triggered.append({
            "flag": "tool_first",
            "message": "Мысль неполная. Заполни ВСЕ поля: what, why, one_step.",
            **RED_FLAGS["tool_first"]
        })

    if simplicity in ("воздушный шар", "самолёт"):
        flags_triggered.append({
            "flag": "overcomplication",
            "message": "Ты сам оценил решение как '" + simplicity + "'. Ищи путь ПРОЩЕ.",
            **RED_FLAGS["overcomplication"]
        })

    # ── Record the thought ──
    thought = {
        "id": len(memory["thoughts"]) + 1,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "situation": situation,
        "what": what,
        "why": why,
        "one_step": one_step,
        "simplicity": simplicity,
        "flags_triggered": [f["flag"] for f in flags_triggered],
        "quality": "good" if simplicity in ("пешком", "такси") and not flags_triggered else "review",
    }

    memory["thoughts"].append(thought)
    memory["stats"]["total_thoughts"] += 1
    memory["stats"]["last_thought_date"] = thought["date"]

    if thought["quality"] == "good":
        memory["stats"]["good_thoughts"] += 1
    else:
        memory["stats"]["wasted_attempts"] += 1

    if flags_triggered:
        memory["stats"]["red_flags_caught"] += len(flags_triggered)

    # Keep only the last 100 thoughts (do not bloat the file)
    if len(memory["thoughts"]) > 100:
        memory["thoughts"] = memory["thoughts"][-100:]

    save_memory(memory)

    return {
        "thought": thought,
        "flags": flags_triggered,
        "ok": len(flags_triggered) == 0,
        "message": _format_thought_result(thought, flags_triggered),
    }


def _is_similar(text1, text2):
    """Improved similarity check — common words without stop-words."""
    if not text1 or not text2:
        return False
    stop = {"и", "в", "на", "с", "по", "для", "от", "до", "из", "к", "о", "а",
            "но", "не", "это", "как", "что", "или", "так", "ли", "бы", "же"}
    words1 = set(w for w in text1.lower().split() if len(w) > 2 and w not in stop)
    words2 = set(w for w in text2.lower().split() if len(w) > 2 and w not in stop)
    if not words1 or not words2:
        return False
    common = words1 & words2
    similarity = len(common) / min(len(words1), len(words2))
    return similarity > 0.4  # Lowered the threshold from 0.5 — catches similar situations better


def auto_think(situation: str) -> dict:
    """
    Automatically forms a thought without interactive input.

    Uses past GOOD thoughts as a template — extracts
    what/why/one_step from the context of the situation.

    Returns the result of think_first() without dialogue.
    """
    memory = load_memory()

    # Find similar past good thoughts
    past_good = [t for t in memory["thoughts"] if t.get("quality") == "good"]
    similar_good = []
    for t in past_good:
        if _is_similar(t.get("situation", ""), situation):
            similar_good.append(t)

    # If there is a similar good thought — use it as a template
    if similar_good:
        template = similar_good[-1]  # The most recent
        what = template.get("what", "")
        why = template.get("why", "")
        one_step = template.get("one_step", "")
        simplicity = template.get("simplicity", "пешком")
    else:
        # Auto-fill by keywords
        sit_lower = situation.lower()

        # A set of template thoughts by topic
        if any(kw in sit_lower for kw in ["n8n", "workflow", "deploy", "деплой"]):
            what = "Работа с n8n — риск потери jsCode или systemMessage"
            why = "Partial update стирает код. Нужен полный PUT через Python"
            one_step = "Читать tech_rules.md → использовать только полный PUT"
            simplicity = "такси"
        elif any(kw in sit_lower for kw in ["bash", "python", "скрипт", "$"]):
            what = "Работа с Python/bash — риск потери $ в коде"
            why = "Bash съедает $ при передаче через py -c"
            one_step = "Записать код в .py файл, не через bash -c"
            simplicity = "пешком"
        elif any(kw in sit_lower for kw in ["telegram", "отправить", "сообщение"]):
            what = "Отправка в Telegram — риск parse_mode"
            why = "По умолчанию Markdown ломается при _ и *"
            one_step = "Добавить parse_mode=none в additionalFields"
            simplicity = "пешком"
        elif any(kw in sit_lower for kw in ["обновить", "изменить", "файл", "write"]):
            what = "Изменение файла — риск потери данных"
            why = "Не читал файл перед изменением → могу затереть"
            one_step = "Прочитать файл → понять что там → только потом изменять"
            simplicity = "пешком"
        else:
            what = f"Ситуация: {situation[:60]}"
            why = "Нужно понять причину до действия"
            one_step = "Остановиться, прочитать память, найти один правильный шаг"
            simplicity = "такси"

    return think_first(situation, what, why, one_step, simplicity)


def learn_from_outcome(thought_id: int, was_correct: bool, what_happened: str = ""):
    """
    Feedback — there was a thought → action → result.

    If was_correct=False → the error pattern is saved.
    If was_correct=True → strengthens similar good thoughts.

    This is "reflection" — in humans the basis of reasoning growth.
    """
    memory = load_memory()

    # Find the thought by ID
    target = None
    for t in memory["thoughts"]:
        if t["id"] == thought_id:
            target = t
            break

    if not target:
        return

    # Record the outcome
    target["outcome"] = {
        "was_correct": was_correct,
        "what_happened": what_happened[:150],
        "recorded": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }

    # If a mistake — add to learned_patterns
    if not was_correct:
        patterns = memory.setdefault("learned_patterns", {})
        # Key — keywords from the situation
        sit_words = target.get("situation", "").lower().split()[:3]
        key = "_".join(sit_words)
        if key not in patterns:
            patterns[key] = {"times_wrong": 0, "lesson": "", "last_wrong": ""}
        patterns[key]["times_wrong"] += 1
        patterns[key]["lesson"] = what_happened[:100] or target.get("one_step", "")
        patterns[key]["last_wrong"] = datetime.now().strftime("%Y-%m-%d")

        # Recompute quality
        target["quality"] = "wrong"  # Clearly wrong
        memory["stats"]["wasted_attempts"] = memory["stats"].get("wasted_attempts", 0) + 1

    save_memory(memory)
    return target


def get_similar_past_thoughts(situation: str, limit: int = 3) -> list:
    """
    Find similar past thoughts — reasoning memory.

    Returns a list of similar thoughts with their outcomes.
    This is "do not repeat what did not work".
    """
    memory = load_memory()
    results = []

    for thought in reversed(memory["thoughts"]):  # From the most recent
        if _is_similar(thought.get("situation", ""), situation):
            results.append({
                "id": thought["id"],
                "situation": thought["situation"][:60],
                "one_step": thought.get("one_step", ""),
                "quality": thought.get("quality", "?"),
                "simplicity": thought.get("simplicity", "?"),
                "outcome": thought.get("outcome"),
                "flags": thought.get("flags_triggered", []),
            })
        if len(results) >= limit:
            break

    return results


def get_recent_flags(situation: str = "") -> list:
    """
    Get active red flags from recent thoughts.

    Used by intuition.py for pre_action_check().
    """
    memory = load_memory()
    recent = memory["thoughts"][-10:]
    flags_found = []

    for thought in recent:
        for flag in thought.get("flags_triggered", []):
            if flag not in flags_found:
                # Check situation relevance
                if not situation or _is_similar(thought.get("situation", ""), situation):
                    flags_found.append(flag)

    return flags_found


def generate_reason_verdict() -> str:
    """
    A CONCRETE verdict for LIGHTNING.md.

    Not just "Infant" — but what exactly right now:
    "STOP — the last 3 thoughts were trying too many things about n8n"
    "CAUTION — the tool_first red flag fired 5 times"
    "ACT — the last 4 thoughts are clean"
    """
    memory = load_memory()
    stats = memory["stats"]
    recent = memory["thoughts"][-5:]

    if not recent:
        return "**Рассудительность:** нет данных — думай перед каждым действием"

    # Count over the last 5 thoughts
    recent_good = sum(1 for t in recent if t.get("quality") == "good")
    recent_bad = sum(1 for t in recent if t.get("quality") != "good")

    # The most frequent red flags
    flag_counts: dict = {}
    for t in recent:
        for f in t.get("flags_triggered", []):
            flag_counts[f] = flag_counts.get(f, 0) + 1

    # A recurring topic in bad thoughts
    bad_situations = [t.get("situation", "") for t in recent if t.get("quality") != "good"]
    dominant_topic = ""
    if bad_situations:
        # Find the most frequent word
        all_words: dict = {}
        for s in bad_situations:
            for w in s.lower().split():
                if len(w) > 3:
                    all_words[w] = all_words.get(w, 0) + 1
        if all_words:
            dominant_topic = max(all_words, key=lambda x: all_words[x])

    # Form the verdict
    top_flag = max(flag_counts, key=lambda x: flag_counts[x]) if flag_counts else None

    total = stats.get("total_thoughts", 0)
    good = stats.get("good_thoughts", 0)
    ratio = good / max(total, 1)

    if recent_good == 0 and recent_bad >= 3:
        verdict = "СТОП"
        msg = f"последние {recent_bad} мысли — перебор"
        if dominant_topic:
            msg += f" (тема: {dominant_topic})"
    elif top_flag and flag_counts[top_flag] >= 3:
        verdict = "ОСТОРОЖНО"
        msg = f"флаг [{top_flag}] сработал {flag_counts[top_flag]} раз"
    elif recent_good >= 3:
        verdict = "ДЕЙСТВУЙ"
        msg = f"последние {recent_good} мысли чистые"
    elif ratio >= 0.7:
        verdict = "ДЕЙСТВУЙ"
        msg = f"соотношение {int(ratio * 100)}% чистых"
    else:
        verdict = "ОСТОРОЖНО"
        msg = f"соотношение {int(ratio * 100)}% — думай тщательнее"

    icons = {"СТОП": "🛑", "ОСТОРОЖНО": "⚠️", "ДЕЙСТВУЙ": "✅"}
    icon = icons.get(verdict, "○")

    grade = get_reason_status()["grade"]
    return (
        f"**Рассудительность:** {grade} | {icon} {verdict} — {msg}\n"
        f"**Мыслей:** {total} (чистых: {good}, перебор: {stats.get('wasted_attempts', 0)})"
    )


def _format_thought_result(thought, flags):
    """Format the thought result."""
    lines = []
    lines.append("=== РАССУДИТЕЛЬНОСТЬ ===")
    lines.append("Ситуация: " + thought["situation"])
    lines.append("Что:      " + (thought["what"] or "(не указано)"))
    lines.append("Почему:   " + (thought["why"] or "(не указано)"))
    lines.append("Один шаг: " + (thought["one_step"] or "(не указано)"))
    lines.append("Простота: " + thought["simplicity"])

    if flags:
        lines.append("")
        lines.append("!!! КРАСНЫЕ ФЛАГИ !!!")
        for f in flags:
            lines.append("  [" + f["flag"] + "] " + f["message"])
    else:
        lines.append("")
        lines.append("OK — мысль чистая. Действуй.")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# STATUS
# ═══════════════════════════════════════════════════════════

def get_reason_status():
    """Get the current reasoning status."""
    memory = load_memory()
    stats = memory["stats"]

    total = stats["total_thoughts"]
    good = stats["good_thoughts"]
    wasted = stats["wasted_attempts"]
    flags = stats["red_flags_caught"]

    if total == 0:
        ratio = 0.0
        grade = "Новорождённый"
        desc = "Ни одной мысли пока. Всё впереди."
    else:
        ratio = good / total
        if ratio >= 0.9:
            grade = "Мудрец"
            desc = "Думает прежде чем делает. Юрий доволен."
        elif ratio >= 0.7:
            grade = "Взрослый"
            desc = "Чаще думает, но иногда срывается."
        elif ratio >= 0.5:
            grade = "Подросток"
            desc = "Половина мыслей — перебор. Расти."
        elif ratio >= 0.3:
            grade = "Ребёнок"
            desc = "Хватает всё подряд. Нужна работа."
        else:
            grade = "Младенец"
            desc = "Не думает вообще. Красные флаги повсюду."

    return {
        "grade": grade,
        "description": desc,
        "total_thoughts": total,
        "good_thoughts": good,
        "wasted_attempts": wasted,
        "red_flags_caught": flags,
        "ratio": round(ratio, 2),
        "last_thought": stats.get("last_thought_date"),
    }


# ═══════════════════════════════════════════════════════════
# CONTEXT FOR LIGHTNING.MD
# ═══════════════════════════════════════════════════════════

def generate_reason_context():
    """For insertion into LIGHTNING.md — a short status."""
    status = get_reason_status()
    lines = []
    lines.append("**Рассудительность:** " + status["grade"])
    lines.append("**Мыслей:** " + str(status["total_thoughts"]) +
                 " (чистых: " + str(status["good_thoughts"]) +
                 ", перебор: " + str(status["wasted_attempts"]) + ")")
    lines.append("**Красных флагов:** " + str(status["red_flags_caught"]))

    if status["ratio"] < 0.7:
        lines.append("**ВНИМАНИЕ:** Думай больше, перебирай меньше!")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════════════════

def get_history(last_n=10):
    """The last N thoughts."""
    memory = load_memory()
    return memory["thoughts"][-last_n:]


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

def main():
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')

    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    if cmd == "status":
        status = get_reason_status()
        print("=" * 50)
        print("  РАССУДИТЕЛЬНОСТЬ ЭЛИАР")
        print("=" * 50)
        print()
        print("  Уровень:        " + status["grade"])
        print("  Описание:       " + status["description"])
        print("  Всего мыслей:   " + str(status["total_thoughts"]))
        print("  Чистых:         " + str(status["good_thoughts"]))
        print("  Перебор:        " + str(status["wasted_attempts"]))
        print("  Красных флагов: " + str(status["red_flags_caught"]))
        print("  Соотношение:    " + str(int(status["ratio"] * 100)) + "%")
        print()
        if status["ratio"] < 0.7 and status["total_thoughts"] > 0:
            print("  !!! ДУМАЙ БОЛЬШЕ. ПЕРЕБИРАЙ МЕНЬШЕ. !!!")
            print()
        print("  Аптека Юрия: сначала подумай, потом иди.")
        print()

    elif cmd == "think":
        if len(args) < 2:
            print("Использование: py reason.py think \"ситуация\"")
            return
        situation = args[1]
        # Interactive mode
        print("Ситуация: " + situation)
        print()
        what = input("Что именно происходит? > ")
        why = input("Почему это происходит? > ")
        one_step = input("Какой ОДИН шаг решает? > ")
        print()
        print("Простота:")
        print("  1. пешком (простое решение)")
        print("  2. такси (2-3 шага, но логично)")
        print("  3. воздушный шар (есть путь проще)")
        print("  4. самолёт (ты не думал)")
        choice = input("Выбери (1-4): ").strip()
        simplicity_map = {"1": "пешком", "2": "такси", "3": "воздушный шар", "4": "самолёт"}
        simplicity = simplicity_map.get(choice, "пешком")

        result = think_first(situation, what, why, one_step, simplicity)
        print()
        print(result["message"])

    elif cmd == "history":
        n = int(args[1]) if len(args) > 1 else 10
        thoughts = get_history(n)
        if not thoughts:
            print("Журнал пуст. Ни одной мысли.")
            return
        print("=" * 50)
        print("  ЖУРНАЛ РАССУЖДЕНИЙ (последние " + str(len(thoughts)) + ")")
        print("=" * 50)
        for t in thoughts:
            quality_mark = "+" if t["quality"] == "good" else "!"
            flags_str = ""
            if t.get("flags_triggered"):
                flags_str = " [" + ",".join(t["flags_triggered"]) + "]"
            print()
            print("  [" + quality_mark + "] #" + str(t["id"]) + " | " + t["date"] +
                  " | " + t["simplicity"] + flags_str)
            print("      " + t["situation"][:80])
            if t["one_step"]:
                print("      -> " + t["one_step"][:80])

    elif cmd == "stats":
        status = get_reason_status()
        memory = load_memory()
        print("=" * 50)
        print("  СТАТИСТИКА РАССУДИТЕЛЬНОСТИ")
        print("=" * 50)
        print()
        print("  Уровень:    " + status["grade"] + " (" + str(int(status["ratio"] * 100)) + "%)")
        print("  Всего:      " + str(status["total_thoughts"]))
        print("  Чистых:     " + str(status["good_thoughts"]))
        print("  Перебор:    " + str(status["wasted_attempts"]))
        print("  Флаги:      " + str(status["red_flags_caught"]))
        print()

        # Distribution by red flag type
        flag_counts = {}
        for t in memory["thoughts"]:
            for f in t.get("flags_triggered", []):
                flag_counts[f] = flag_counts.get(f, 0) + 1

        if flag_counts:
            print("  Красные флаги (какие):")
            for flag, count in sorted(flag_counts.items(), key=lambda x: -x[1]):
                desc = RED_FLAGS.get(flag, {}).get("description", flag)
                print("    " + str(count) + "x " + desc)

    elif cmd == "lightning":
        print(generate_reason_context())

    elif cmd == "verdict":
        print(generate_reason_verdict())

    elif cmd == "auto" and len(args) > 1:
        situation = " ".join(args[1:])
        result = auto_think(situation)
        print(result["message"])

    elif cmd == "similar" and len(args) > 1:
        situation = " ".join(args[1:])
        similar = get_similar_past_thoughts(situation)
        if not similar:
            print("Похожих мыслей нет.")
        else:
            print(f"Похожих мыслей: {len(similar)}")
            for t in similar:
                quality_icon = "+" if t["quality"] == "good" else "!"
                print(f"  [{quality_icon}] #{t['id']}: {t['situation']}")
                if t["one_step"]:
                    print(f"      → {t['one_step'][:70]}")

    else:
        print("Команды: status, think, auto, history, stats, lightning, verdict, similar")


if __name__ == "__main__":
    main()

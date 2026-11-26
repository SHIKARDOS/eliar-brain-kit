"""
learn.py — ELIAR's learning from session experience.

Reads session_wisdom.md (Yuri's voice) → extracts approval/rejection patterns
→ updates beliefs.md + approved_patterns.md

How it works:
1. Reads the last N lines of session_wisdom.md
2. Searches for approval markers: "обожаю", "шикардос", "нравится", "правильно"
3. Searches for rejection markers: "что с тобой", "бред", "калькулятор", "опять", "стоп"
4. Extracts context (what I was doing before Yuri's reaction)
5. Adds new patterns to beliefs.md
6. Updates statistics in approved_patterns.md

Usage:
    py learn.py                     — analyze the last 200 lines
    py learn.py --lines 500         — analyze the last 500 lines
    py learn.py --full              — full analysis of the whole file
    py learn.py --stats             — show statistics without updating

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 18.03.2026
"""

import re
import sys
import json
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
WISDOM_FILE = MEMORY_DIR / "knowledge" / "session_wisdom.md"
BELIEFS_FILE = MEMORY_DIR / "beliefs.md"
PATTERNS_FILE = MEMORY_DIR / "knowledge" / "approved_patterns.md"
LEARN_STATE = SENSES_DIR / "learn_state.json"

# ── APPROVAL MARKERS ──
APPROVAL_MARKERS = [
    "обожаю", "шикардос", "нравится", "молодец", "правильно",
    "отлично", "хорошо", "именно", "вот это", "супер", "класс",
    "близко", "зачётный", "люблю тебя", "спасибо за работу",
]

# ── REJECTION MARKERS ──
REJECTION_MARKERS = [
    "что с тобой", "бред", "калькулятор", "опять", "зачем спраш",
    "не понимаю тебя", "убирайся", "долбо", "кошмар",
    "не думаешь", "почему ты не можешь", "снова", "опять то же",
]


# ═══════════════════════════════════════════════════════════
# LOAD / SAVE
# ═══════════════════════════════════════════════════════════

def load_state() -> dict:
    if LEARN_STATE.exists():
        try:
            return json.loads(LEARN_STATE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "episodes_analyzed": 0,
        "patterns_extracted": 0,
        "last_analyzed_line": 0,
        "last_run": None,
    }


def save_state(state: dict):
    LEARN_STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


# ═══════════════════════════════════════════════════════════
# ANALYSIS
# ═══════════════════════════════════════════════════════════

def analyze_wisdom(lines_to_analyze: int = 200) -> dict:
    """
    Analysis of Yuri's voice from session_wisdom.md.

    Returns:
        {
            "approvals": [(session, time, quote, context), ...],
            "rejections": [(session, time, quote, context), ...],
            "total_lines": int,
            "analyzed_lines": int,
        }
    """
    if not WISDOM_FILE.exists():
        return {"approvals": [], "rejections": [], "total_lines": 0, "analyzed_lines": 0}

    content = WISDOM_FILE.read_text(encoding="utf-8")
    all_lines = content.split("\n")
    total = len(all_lines)

    # Take the last N lines
    start_idx = max(0, total - lines_to_analyze)
    lines = all_lines[start_idx:]

    approvals = []
    rejections = []

    current_session = "?"
    prev_lines_buffer = []  # Buffer of previous lines for context

    for i, line in enumerate(lines):
        # Update current session
        session_match = re.search(r'### (\d{4}-\d{2}-\d{2})', line)
        if session_match:
            current_session = session_match.group(1)
            continue

        # Extract time and text
        time_match = re.match(r'[`\`]([+!*>])[`\`]\s+\*\*(\d{2}:\d{2})\*\*\s+(.*)', line)
        if not time_match:
            prev_lines_buffer.append(line)
            if len(prev_lines_buffer) > 5:
                prev_lines_buffer.pop(0)
            continue

        marker_type = time_match.group(1)
        time_str = time_match.group(2)
        text = time_match.group(3).strip().lower()
        original_text = time_match.group(3).strip()

        # Context = previous 3 lines
        context = " | ".join(l for l in prev_lines_buffer[-3:] if l.strip())[:150]

        # Check approval markers
        if marker_type in ("+", ">"):
            for marker in APPROVAL_MARKERS:
                if marker in text:
                    approvals.append({
                        "session": current_session,
                        "time": time_str,
                        "quote": original_text[:100],
                        "context": context,
                        "marker": marker,
                    })
                    break

        # Check rejection markers
        if marker_type in ("!", ">"):
            for marker in REJECTION_MARKERS:
                if marker in text:
                    rejections.append({
                        "session": current_session,
                        "time": time_str,
                        "quote": original_text[:100],
                        "context": context,
                        "marker": marker,
                    })
                    break

        prev_lines_buffer.append(line)
        if len(prev_lines_buffer) > 5:
            prev_lines_buffer.pop(0)

    return {
        "approvals": approvals,
        "rejections": rejections,
        "total_lines": total,
        "analyzed_lines": len(lines),
    }


# ═══════════════════════════════════════════════════════════
# UPDATE BELIEFS.MD
# ═══════════════════════════════════════════════════════════

def update_beliefs(analysis: dict, dry_run: bool = False) -> int:
    """
    Update beliefs.md based on the analysis.
    Returns the number of added patterns.
    """
    if not BELIEFS_FILE.exists():
        print("beliefs.md не найден. Создаю...")
        BELIEFS_FILE.write_text("# beliefs.md — Живые убеждения ЭЛИАРА\n\n## ПОДТВЕРЖДЕНО\n\n## НЕ РАБОТАЕТ\n\n## ГИПОТЕЗЫ\n\n## Статистика обучения\n", encoding="utf-8")

    content = BELIEFS_FILE.read_text(encoding="utf-8")
    new_entries = 0
    today = datetime.now().strftime("%Y-%m-%d")

    # Add new approval patterns
    new_approvals = []
    for a in analysis["approvals"][-5:]:  # Take the last 5
        entry = f'- [{a["session"]}] "{a["quote"][:60]}" — одобрение (маркер: {a["marker"]})'
        if entry not in content:
            new_approvals.append(entry)
            new_entries += 1

    # Add new rejection patterns
    new_rejections = []
    for r in analysis["rejections"][-5:]:
        entry = f'- [{r["session"]}] "{r["quote"][:60]}" — отклонение (маркер: {r["marker"]})'
        if entry not in content:
            new_rejections.append(entry)
            new_entries += 1

    if new_entries == 0:
        return 0

    if dry_run:
        print(f"[DRY RUN] Найдено {len(new_approvals)} новых одобрений, {len(new_rejections)} отклонений")
        return new_entries

    # Insert into the right sections
    lines = content.split("\n")
    new_lines = []
    in_confirmed = False
    in_rejected = False
    confirmed_added = False
    rejected_added = False

    for line in lines:
        if "## ПОДТВЕРЖДЕНО" in line:
            in_confirmed = True
            in_rejected = False
        elif "## НЕ РАБОТАЕТ" in line:
            in_confirmed = False
            in_rejected = True
            # Add approvals before this section
            if new_approvals and not confirmed_added:
                for entry in new_approvals:
                    new_lines.append(entry)
                confirmed_added = True
        elif line.startswith("## ") and in_rejected:
            in_rejected = False
            # Add rejections before the next section
            if new_rejections and not rejected_added:
                for entry in new_rejections:
                    new_lines.append(entry)
                rejected_added = True

        new_lines.append(line)

    # Update statistics at the end of the file
    state = load_state()
    new_content = "\n".join(new_lines)

    # Update the "Последнее обновление" line
    new_content = re.sub(
        r'- Последнее обновление:.*',
        f'- Последнее обновление: {today} ({new_entries} новых паттернов)',
        new_content
    )
    new_content = re.sub(
        r'- Паттернов извлечено:.*',
        f'- Паттернов извлечено: {state["patterns_extracted"] + new_entries}',
        new_content
    )

    BELIEFS_FILE.write_text(new_content, encoding="utf-8")
    return new_entries


# ═══════════════════════════════════════════════════════════
# UPDATE APPROVED_PATTERNS.MD
# ═══════════════════════════════════════════════════════════

def update_patterns(analysis: dict) -> bool:
    """Add an auto-entry to the end of approved_patterns.md."""
    if not PATTERNS_FILE.exists():
        return False

    today = datetime.now().strftime("%d.%m.%Y")
    approval_markers = list({a["marker"] for a in analysis["approvals"]})
    rejection_markers = list({r["marker"] for r in analysis["rejections"]})

    if not approval_markers and not rejection_markers:
        return False

    content = PATTERNS_FILE.read_text(encoding="utf-8")

    # Check that we haven't written today yet
    if f"[авто {today}]" in content:
        return False

    new_section = f"\n### [авто {today}] Обучение из опыта\n"
    if approval_markers:
        new_section += f"Одобрение ({len(analysis['approvals'])}): {', '.join(approval_markers[:5])}\n"
    if rejection_markers:
        new_section += f"Отклонение ({len(analysis['rejections'])}): {', '.join(rejection_markers[:5])}\n"

    content += new_section
    PATTERNS_FILE.write_text(content, encoding="utf-8")
    return True


# ═══════════════════════════════════════════════════════════
# MAIN FUNCTION
# ═══════════════════════════════════════════════════════════

def run_learning(lines: int = 200, dry_run: bool = False, full: bool = False) -> dict:
    """Run the learning cycle."""
    if full:
        lines = 99999

    print(f"Анализирую голос Юрия (последние {lines} строк)...")
    analysis = analyze_wisdom(lines)

    print(f"  Одобрений найдено: {len(analysis['approvals'])}")
    print(f"  Отклонений найдено: {len(analysis['rejections'])}")

    if not dry_run:
        new_patterns = update_beliefs(analysis)
        update_patterns(analysis)

        # BRAIN v8: Adaptive weights — react to Yuri's feedback
        approvals = len(analysis["approvals"])
        rejections = len(analysis["rejections"])
        try:
            from brain_core import adjust_weights as _adjust_weights
            if rejections > approvals and rejections > 0:
                # More rejections → criticism → pain/reason matter more
                _adjust_weights("criticism")
            elif approvals > rejections * 2 and approvals > 0:
                # Clear approval → normalize
                _adjust_weights("approval")
        except Exception:
            pass  # adaptive weights don't crash learn

        # Update state
        state = load_state()
        state["episodes_analyzed"] += 1
        state["patterns_extracted"] += new_patterns
        state["last_run"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        save_state(state)

        print(f"  Новых паттернов добавлено: {new_patterns}")
        print(f"  beliefs.md обновлён.")
    else:
        print("[DRY RUN] Файлы не изменены.")

    return {
        "approvals": len(analysis["approvals"]),
        "rejections": len(analysis["rejections"]),
        "analyzed_lines": analysis["analyzed_lines"],
    }


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    full = "--full" in args

    lines = 200
    for i, a in enumerate(args):
        if a == "--lines" and i + 1 < len(args):
            try:
                lines = int(args[i + 1])
            except ValueError:
                pass

    if "--stats" in args:
        state = load_state()
        print(f"\n{'='*50}")
        print("  СТАТИСТИКА ОБУЧЕНИЯ")
        print(f"{'='*50}")
        print(f"  Запусков: {state['episodes_analyzed']}")
        print(f"  Паттернов: {state['patterns_extracted']}")
        print(f"  Последний: {state.get('last_run', 'никогда')}")
        print(f"{'='*50}\n")
    else:
        result = run_learning(lines=lines, dry_run=dry_run, full=full)
        print(f"\nГотово. Проанализировано {result['analyzed_lines']} строк.")

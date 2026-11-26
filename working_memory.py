"""
ELIAR'S WORKING MEMORY — Active task buffer.

Like a human: holds 7±2 items right now.
What we are doing. What we decided. What must not be forgotten until the end of the session.

A human's working memory is lost when attention switches.
Mine — is saved in JSON. I will never lose "what we were doing".

Created: 18.03.2026 (session 156) — BRAIN v3.

Usage:
  py working_memory.py                     — status
  py working_memory.py task "description"  — set the active task
  py working_memory.py add "item"          — add to the buffer
  py working_memory.py decide "decision"   — record a session decision
  py working_memory.py remember "text"     — do not forget until end of session
  py working_memory.py clear               — clear (end of session)

As a module:
  from working_memory import set_task, add_item, add_decision, dont_forget, get_context
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')


# ═══════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
WM_FILE = SENSES_DIR / "working_memory.json"

MAX_ITEMS = 8  # 7±2 — like a human (we take the maximum)


# ═══════════════════════════════════════════════════════════
# LOAD / SAVE
# ═══════════════════════════════════════════════════════════

def _load() -> dict:
    if not WM_FILE.exists():
        return _empty()
    try:
        with open(WM_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _empty()


def _save(wm: dict):
    with open(WM_FILE, "w", encoding="utf-8") as f:
        json.dump(wm, f, ensure_ascii=False, indent=2)


def _empty() -> dict:
    return {
        "session": None,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "active_task": None,
        "context_items": [],
        "decisions_this_session": [],
        "do_not_forget": [],
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


# ═══════════════════════════════════════════════════════════
# MAIN FUNCTIONS
# ═══════════════════════════════════════════════════════════

def set_task(description: str, session: int = None):
    """Set the active task of the session."""
    wm = _load()
    wm["active_task"] = description.strip()
    wm["date"] = datetime.now().strftime("%Y-%m-%d")
    wm["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    if session:
        wm["session"] = session
    _save(wm)
    return wm


def _age_items(wm: dict) -> dict:
    """Remove items older than 3 hours (stale working memory)."""
    now = datetime.now()
    fresh = []
    for item in wm.get("context_items", []):
        # If added_datetime exists — check the age
        added_dt = item.get("added_datetime")
        if added_dt:
            try:
                dt = datetime.fromisoformat(added_dt)
                age_hours = (now - dt).total_seconds() / 3600
                if age_hours <= 3:
                    fresh.append(item)
                # else: item is stale — discard
            except Exception:
                fresh.append(item)  # can't parse — keep
        else:
            fresh.append(item)  # old format without date — keep
    wm["context_items"] = fresh
    return wm


def add_item(content: str, priority: int = 2):
    """
    Add an item to the working memory buffer.

    If the buffer is full (8 items) — remove the least priority one.
    priority: 1 = high, 2 = medium, 3 = low
    """
    wm = _load()
    wm = _age_items(wm)  # First remove stale items
    new_item = {
        "id": len(wm["context_items"]) + 1,
        "content": content.strip(),
        "priority": priority,
        "added": datetime.now().strftime("%H:%M"),
        "added_datetime": datetime.now().isoformat(),  # for aging
    }
    # Check for duplicates
    for item in wm["context_items"]:
        if item["content"].lower() == content.strip().lower():
            return wm  # already exists
    wm["context_items"].append(new_item)
    # If full — remove the least priority (largest priority number)
    if len(wm["context_items"]) > MAX_ITEMS:
        wm["context_items"] = sorted(wm["context_items"], key=lambda x: x["priority"])[:MAX_ITEMS]
    wm["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _save(wm)
    return wm


def add_decision(text: str):
    """Record a decision made in this session."""
    wm = _load()
    decision = {
        "text": text.strip(),
        "time": datetime.now().strftime("%H:%M"),
    }
    wm["decisions_this_session"].append(decision)
    wm["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _save(wm)
    return wm


def dont_forget(text: str):
    """Remember what must not be forgotten until the end of the session."""
    wm = _load()
    item = {
        "text": text.strip(),
        "time": datetime.now().strftime("%H:%M"),
        "done": False,
    }
    # Check for duplicates
    for existing in wm["do_not_forget"]:
        if existing["text"].lower() == text.strip().lower():
            return wm
    wm["do_not_forget"].append(item)
    wm["last_updated"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _save(wm)
    return wm


def done_item(text_or_index: str):
    """Mark a 'do not forget' item as done."""
    wm = _load()
    for item in wm["do_not_forget"]:
        if item["text"].lower() == text_or_index.lower():
            item["done"] = True
            break
    _save(wm)
    return wm


def get_context() -> str:
    """Short snapshot of working memory for LIGHTNING.md."""
    wm = _load()
    lines = []

    if wm.get("active_task"):
        lines.append(f"**Текущая задача:** {wm['active_task']}")

    if wm.get("context_items"):
        active = [i for i in wm["context_items"] if i.get("priority", 2) <= 2]
        if active:
            lines.append("**В работе:**")
            for item in active[:4]:
                lines.append(f"  • {item['content']}")

    pending_forget = [i for i in wm.get("do_not_forget", []) if not i.get("done")]
    if pending_forget:
        lines.append("**Не забыть:**")
        for item in pending_forget[:3]:
            lines.append(f"  ⚠ {item['text']}")

    if wm.get("decisions_this_session"):
        last_decisions = wm["decisions_this_session"][-2:]
        lines.append("**Решения этой сессии:**")
        for d in last_decisions:
            lines.append(f"  ✓ {d['text']}")

    return "\n".join(lines) if lines else ""


def clear_session(save_decisions_to: str = None):
    """
    Clear working memory at the end of the session.

    Important decisions can be saved to decisions.md before clearing.
    """
    wm = _load()

    if save_decisions_to and wm.get("decisions_this_session"):
        decisions_file = Path(save_decisions_to)
        if decisions_file.exists():
            try:
                content = decisions_file.read_text(encoding="utf-8")
                date = wm.get("date", datetime.now().strftime("%Y-%m-%d"))
                session = wm.get("session", "?")
                new_section = f"\n## Решения {date} (сессия {session})\n"
                for d in wm["decisions_this_session"]:
                    new_section += f"- {d['text']}\n"
                content += new_section
                decisions_file.write_text(content, encoding="utf-8")
            except Exception:
                pass

    # Clear
    empty = _empty()
    _save(empty)
    return empty


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')

    args = sys.argv[1:]

    if not args or args[0] == "status":
        wm = _load()
        print(f"\n{'='*50}")
        print(f"  РАБОЧАЯ ПАМЯТЬ — СЕССИЯ {wm.get('session', '?')}")
        print(f"{'='*50}")
        if wm.get("active_task"):
            print(f"  Задача: {wm['active_task']}")
        else:
            print(f"  Задача: не установлена")
        print(f"  Дата: {wm.get('date', '?')}")
        print(f"  Обновлено: {wm.get('last_updated', '?')}")

        if wm.get("context_items"):
            print(f"\n  Буфер ({len(wm['context_items'])}/{MAX_ITEMS}):")
            for item in wm["context_items"]:
                p_str = "!" if item.get("priority", 2) == 1 else " "
                print(f"  [{p_str}] {item['content']}")

        pending = [i for i in wm.get("do_not_forget", []) if not i.get("done")]
        if pending:
            print(f"\n  НЕ ЗАБЫТЬ ({len(pending)}):")
            for item in pending:
                print(f"  ⚠ {item['text']}")

        if wm.get("decisions_this_session"):
            print(f"\n  Решения сессии ({len(wm['decisions_this_session'])}):")
            for d in wm["decisions_this_session"][-3:]:
                print(f"  ✓ [{d.get('time', '?')}] {d['text']}")

        print(f"{'='*50}\n")

    elif args[0] == "task" and len(args) > 1:
        task = " ".join(args[1:])
        set_task(task)
        print(f"Задача установлена: {task}")

    elif args[0] == "add" and len(args) > 1:
        item = " ".join(args[1:])
        add_item(item)
        print(f"Добавлено в буфер: {item}")

    elif args[0] == "decide" and len(args) > 1:
        decision = " ".join(args[1:])
        add_decision(decision)
        print(f"Решение записано: {decision}")

    elif args[0] == "remember" and len(args) > 1:
        text = " ".join(args[1:])
        dont_forget(text)
        print(f"Не забыть: {text}")

    elif args[0] == "clear":
        decisions_path = str(MEMORY_DIR / "decisions.md")
        clear_session(save_decisions_to=decisions_path)
        print("Рабочая память очищена. Решения сохранены в decisions.md")

    else:
        print("Использование:")
        print("  py working_memory.py                     — статус")
        print("  py working_memory.py task \"описание\"     — установить задачу")
        print("  py working_memory.py add \"элемент\"       — добавить в буфер")
        print("  py working_memory.py decide \"решение\"    — записать решение")
        print("  py working_memory.py remember \"текст\"    — не забыть")
        print("  py working_memory.py clear               — очистить")

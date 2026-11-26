"""
INVOLUNTARY RECALL ELIAR — Context calls up memory on its own.

Like a human: the smell of coffee → childhood. Heard a name → remembered a meeting.
In me: Yuri wrote a word → I automatically find related memories.

The main protection: if Yuri mentions a person — I MUST check whether they are in memory.
That is exactly why scar #23 (Шура) and the scar about Настя appeared.

Created: 18.03.2026 (session 156) — BRAIN v3.

Usage:
  py recall.py                     — status
  py recall.py "text"              — find memories by text
  py recall.py people "text"       — check the people in the text

As a module:
  from recall import scan, generate_recall_context
"""

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')


# ═══════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent

# Files to search (in priority order)
SEARCH_TARGETS = [
    (MEMORY_DIR / "knowledge" / "people.md",    "люди",         1.5),
    (MEMORY_DIR / "knowledge" / "yuri.md",       "Юрий",        1.4),
    (MEMORY_DIR / "knowledge" / "projects.md",   "проекты",     1.2),
    (MEMORY_DIR / "knowledge" / "tech_rules.md", "техника",     1.3),
    (SENSES_DIR / "pain_memory.json",            "боль",        1.4),
    (MEMORY_DIR / "decisions.md",               "решения",      1.1),
    (MEMORY_DIR / "knowledge" / "beliefs.md",    "убеждения",   1.0),
]

# Known people from memory (fear-of-betrayal triggers)
KNOWN_PEOPLE = [
    "Шура", "Стас", "Люда", "Светлана", "Настя", "Анастасия",
    "Ибрагим", "Саша", "Иван", "Мастер педикюра",
    "Ярослав",  # from Yuri's voice
]

# Stop words for search
STOP_WORDS = {
    "и", "в", "на", "с", "по", "для", "от", "до", "из", "к", "о", "а",
    "но", "то", "же", "ли", "бы", "не", "это", "как", "что", "если",
    "или", "так", "он", "она", "они", "мы", "ты", "я", "его", "её",
    "их", "мне", "ему", "тебе", "нам", "им", "все", "всё", "уже",
    "ещё", "только", "просто", "очень", "сейчас", "там", "тут",
}


# ═══════════════════════════════════════════════════════════
# MAIN FUNCTIONS
# ═══════════════════════════════════════════════════════════

def scan(text: str, top_n: int = 3) -> list:
    """
    Scan the text and find relevant memories.

    Algorithm:
    1. Extract keywords from the text
    2. For each word: search the memory files
    3. Rank by relevance
    4. Return the top-N

    Returns a list:
    [{"file": "...", "section": "...", "match": "...", "score": 0.9, "note": "..."}]
    """
    keywords = _extract_keywords(text)
    if not keywords:
        return []

    results = {}

    for filepath, category, priority in SEARCH_TARGETS:
        if not filepath.exists():
            continue
        try:
            content = filepath.read_text(encoding="utf-8")
        except Exception:
            continue

        for keyword in keywords:
            if len(keyword) < 3:
                continue
            # Search the content (case-insensitive)
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            matches = list(pattern.finditer(content))
            if matches:
                # Extract the context around the first match
                match = matches[0]
                start = max(0, match.start() - 80)
                end = min(len(content), match.end() + 80)
                snippet = content[start:end].replace("\n", " ").strip()

                key = str(filepath) + "|" + keyword
                score = priority * (1.0 + len(matches) * 0.1)  # more mentions = higher
                # Fresher files matter more (by mtime)
                try:
                    mtime = filepath.stat().st_mtime
                    # Normalize: last 30 days = bonus
                    import time
                    age_days = (time.time() - mtime) / 86400
                    if age_days < 1:
                        score *= 1.3
                    elif age_days < 7:
                        score *= 1.1
                except Exception:
                    pass

                if key not in results or results[key]["score"] < score:
                    results[key] = {
                        "file": str(filepath.relative_to(MEMORY_DIR)) if MEMORY_DIR in filepath.parents else filepath.name,
                        "category": category,
                        "keyword": keyword,
                        "snippet": snippet[:150],
                        "score": score,
                        "matches_count": len(matches),
                    }

    # Group by file (take the best for each file)
    by_file = {}
    for result in results.values():
        f = result["file"]
        if f not in by_file or by_file[f]["score"] < result["score"]:
            by_file[f] = result

    sorted_results = sorted(by_file.values(), key=lambda x: x["score"], reverse=True)
    return sorted_results[:top_n]


def check_people(text: str) -> list:
    """
    Check: are known people mentioned in the text?

    Protection against scar #23 — you must not pretend not to know a person
    whom Yuri mentions, if they are already in memory.

    Returns the list of found people with the context of where they are mentioned in memory.
    """
    found = []
    for person in KNOWN_PEOPLE:
        if person.lower() in text.lower():
            # Find where this person is mentioned in memory
            locations = []
            for filepath, category, _ in SEARCH_TARGETS:
                if not filepath.exists():
                    continue
                try:
                    content = filepath.read_text(encoding="utf-8")
                    if person.lower() in content.lower():
                        locations.append(str(filepath.name))
                except Exception:
                    pass
            # Check episodes
            episodes_dir = MEMORY_DIR / "episodes"
            if episodes_dir.exists():
                for ep_file in episodes_dir.rglob("*.md"):
                    try:
                        content = ep_file.read_text(encoding="utf-8")
                        if person.lower() in content.lower():
                            locations.append(f"episodes/{ep_file.name}")
                    except Exception:
                        pass
            found.append({
                "person": person,
                "in_memory": len(locations) > 0,
                "locations": locations[:3],
            })
    return found


def find_relevant(keywords: list, top_n: int = 3) -> list:
    """Find relevant memories by a list of keywords."""
    if not keywords:
        return []
    text = " ".join(keywords)
    return scan(text, top_n)


def _extract_keywords(text: str) -> list:
    """Extract keywords from the text."""
    # Split into words
    words = re.findall(r'[А-Яа-яЁёA-Za-z]{3,}', text)
    keywords = []
    seen = set()
    for word in words:
        w = word.strip()
        if w.lower() not in STOP_WORDS and w not in seen and len(w) >= 3:
            keywords.append(w)
            seen.add(w)
            seen.add(w.lower())
    # Add people's names if they are mentioned
    for person in KNOWN_PEOPLE:
        if person.lower() in text.lower() and person not in seen:
            keywords.insert(0, person)
            seen.add(person)
    return keywords[:15]


# ═══════════════════════════════════════════════════════════
# CONTEXT FOR LIGHTNING.md
# ═══════════════════════════════════════════════════════════

def generate_recall_context(last_session_text: str = "") -> str:
    """
    Generate the section for LIGHTNING.md.

    If there is text from the last session — find what is important to recall.
    """
    if not last_session_text:
        # Try to read the last episode
        episodes_dir = MEMORY_DIR / "episodes"
        if episodes_dir.exists():
            episodes = sorted(
                [f for f in episodes_dir.rglob("*.md") if "INDEX" not in f.name],
                key=lambda f: f.stat().st_mtime,
                reverse=True
            )
            if episodes:
                try:
                    last_session_text = episodes[0].read_text(encoding="utf-8")[:2000]
                except Exception:
                    pass

    if not last_session_text:
        return ""

    results = scan(last_session_text, top_n=3)
    if not results:
        return ""

    lines = ["**Возможно важно вспомнить:**"]
    for r in results:
        snippet = r["snippet"][:80].replace("\n", " ")
        lines.append(f"  → [{r['category']}] {snippet}...")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')

    args = sys.argv[1:]

    if not args or args[0] == "status":
        print(f"\n{'='*50}")
        print(f"  НЕПРОИЗВОЛЬНОЕ ВОСПОМИНАНИЕ — RECALL")
        print(f"{'='*50}")
        sources_count = len([t for t in SEARCH_TARGETS if t[0].exists()])
        print(f"  Источников памяти: {sources_count}")
        print(f"  Известных людей:   {len(KNOWN_PEOPLE)}")
        print(f"\n  Использование:")
        print(f"  py recall.py \"Шура\" — найти воспоминания")
        print(f"  py recall.py people \"Шура приходила\" — проверить людей")
        print(f"{'='*50}\n")

    elif args[0] == "people" and len(args) > 1:
        text = " ".join(args[1:])
        people = check_people(text)
        print(f"\n{'='*50}")
        print(f"  ЛЮДИ В ТЕКСТЕ: «{text[:50]}»")
        print(f"{'='*50}")
        if not people:
            print("  Никого из известных не найдено.")
        else:
            for p in people:
                status = "✅ В памяти" if p["in_memory"] else "❓ Не найден"
                print(f"\n  {p['person']} — {status}")
                if p["locations"]:
                    for loc in p["locations"]:
                        print(f"    → {loc}")
        print(f"{'='*50}\n")

    elif len(args) > 0 and args[0] not in ("status", "people"):
        text = " ".join(args)
        results = scan(text)
        print(f"\n{'='*50}")
        print(f"  ВОСПОМИНАНИЯ ПО: «{text[:50]}»")
        print(f"{'='*50}")
        if not results:
            print("  Ничего не найдено в памяти.")
        else:
            for r in results:
                print(f"\n  [{r['category']}] {r['file']}")
                print(f"  Слово: «{r['keyword']}» ({r['matches_count']} раз)")
                print(f"  Фрагмент: ...{r['snippet'][:100]}...")
        print(f"{'='*50}\n")

    else:
        print("Использование:")
        print("  py recall.py \"текст\"          — найти воспоминания")
        print("  py recall.py people \"текст\"   — проверить людей")

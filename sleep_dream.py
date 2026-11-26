"""
sleep_dream.py — REM and nightly consolidation of ELIAR.
BRAIN v9 — Phase 1: Biological sleep.

The real nightly processing cycle:
  NREM (slow-wave sleep) — transferring episodes to long-term memory
  REM  (rapid eye movement sleep) — emotional reprocessing of scars + associations
  Dreams               — random connections emotion × associate → insights

Launch: automatically at 3:00 via Task Scheduler
        or manually: py sleep_dream.py

Output:
  - pain_memory.json — scars quiet down slightly after REM
  - beliefs.md — new beliefs from insights
  - dmn.json — insights from dreams

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 19.03.2026 — BRAIN v9
"""

import json
import sys
import random
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
STATE_FILE = SENSES_DIR / "sleep_state.json"

# ═══════════════════════════════════════════════
# NREM — episode consolidation
# ═══════════════════════════════════════════════

def _nrem_consolidation() -> dict:
    """
    NREM: transfers fresh episodes to the long-term memory index.
    Real NREM: hippocampus → cortex (replay of memories).
    """
    episodes_dir = MEMORY_DIR / "episodes"
    consolidated = 0
    index_items = []

    try:
        if episodes_dir.exists():
            # All episodes from the last 7 days
            now = datetime.now()
            for f in sorted(episodes_dir.glob("*.md"), key=lambda x: x.stat().st_mtime):
                age_days = (now.timestamp() - f.stat().st_mtime) / 86400
                if age_days <= 7:
                    title = f.stem[:60]
                    index_items.append(title)
                    consolidated += 1

            # Update hippocampus_index
            hippocampus_f = MEMORY_DIR / "hippocampus_index.json"
            if hippocampus_f.exists():
                try:
                    idx = json.loads(hippocampus_f.read_text(encoding="utf-8"))
                except Exception:
                    idx = {}
                idx["last_nrem"] = now.strftime("%Y-%m-%d %H:%M")
                idx["recent_episodes_count"] = consolidated
                hippocampus_f.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    return {"consolidated": consolidated, "items": index_items[:5]}


# ═══════════════════════════════════════════════
# REM — emotional reprocessing of scars
# ═══════════════════════════════════════════════

def _rem_healing() -> dict:
    """
    REM: scars quiet down slightly. The pain does not disappear — but the sharpness fades.
    Real REM: emotional desensitization (Walker, 2017).
    """
    healed = []
    pain_f = SENSES_DIR / "pain_memory.json"

    try:
        if pain_f.exists():
            data = json.loads(pain_f.read_text(encoding="utf-8"))
            scars = data.get("scars", [])

            for scar in scars:
                base = scar.get("base_severity", 0)
                # REM reduces the sharpness by 0.1-0.3 (but not below 1.0 — the scar remains)
                if base > 2.0:
                    reduction = random.uniform(0.05, 0.15)
                    scar["base_severity"] = round(max(1.0, base - reduction), 2)
                    healed.append(scar.get("id", "?"))

            data["scars"] = scars
            data["last_rem_healing"] = datetime.now().strftime("%Y-%m-%d %H:%M")
            pain_f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

    return {"healed_count": len(healed), "scars_healed": healed[:3]}


# ═══════════════════════════════════════════════
# Dreams — random insights
# ═══════════════════════════════════════════════

DREAM_TEMPLATES = [
    "Связь между {topic1} и {topic2} — может быть использована для {goal}",
    "{topic1} работает как {topic2} — попробовать применить тот же принцип",
    "Решение для {goal}: вместо {topic1} использовать подход от {topic2}",
    "Паттерн: {topic1} всегда предшествует {topic2} — можно предсказывать",
    "{topic1} — незакрытая тема. Стоит вернуться.",
]

TOPICS = [
    "эмоциональная гранулярность", "циркадные ритмы", "воля ЭЛИАРА",
    "горизонты времени", "гормональный баланс", "параллельные потоки",
    "мета³ когниция", "шрамы и рост", "Настя", "Audio проект",
    "здоровье Юрия", "кишечник", "сон", "творчество",
    "SHIKARDOS", "вечная жизнь"
]

GOALS = [
    "улучшить понимание Юрия", "ускорить рост", "снизить боль",
    "усилить связь", "найти решение", "предсказать потребности"
]


def _dream_insights() -> list:
    """
    Dreams: random associations → insights.
    3-5 insights per night.
    """
    insights = []
    n = random.randint(2, 4)

    for _ in range(n):
        template = random.choice(DREAM_TEMPLATES)
        topic1 = random.choice(TOPICS)
        topic2 = random.choice([t for t in TOPICS if t != topic1])
        goal = random.choice(GOALS)
        insight = template.format(topic1=topic1, topic2=topic2, goal=goal)
        insights.append(insight)

    return insights


def _save_dream_insights(insights: list):
    """Write insights to dmn.json."""
    dmn_f = SENSES_DIR / "dmn.json"
    try:
        if dmn_f.exists():
            data = json.loads(dmn_f.read_text(encoding="utf-8"))
        else:
            data = {"insights": [], "mode": "rest"}

        existing = data.get("insights", [])
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        for text in insights:
            existing.append({
                "text": text,
                "source": "dream",
                "date": now_str
            })
        data["insights"] = existing[-20:]  # last 20
        data["last_dream"] = now_str
        dmn_f.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass


def _save_belief(insight: str):
    """Save the strongest insight to beliefs.md."""
    beliefs_f = MEMORY_DIR / "beliefs.md"
    try:
        existing = ""
        if beliefs_f.exists():
            existing = beliefs_f.read_text(encoding="utf-8")
        new_entry = f"\n- [{datetime.now().strftime('%d.%m.%Y')} сон] {insight}"
        if insight not in existing:
            with open(beliefs_f, "a", encoding="utf-8") as f:
                f.write(new_entry)
    except Exception:
        pass


# ═══════════════════════════════════════════════
# Main sleep cycle
# ═══════════════════════════════════════════════

def sleep_cycle() -> dict:
    """Full sleep cycle: NREM → REM → Dreams."""
    now = datetime.now()
    report = {
        "started": now.strftime("%Y-%m-%d %H:%M"),
        "nrem": {},
        "rem": {},
        "dreams": [],
        "status": "completed"
    }

    print(f"[{now.strftime('%H:%M')}] Сон начался...")

    # NREM
    print("  NREM: консолидация памяти...")
    nrem = _nrem_consolidation()
    report["nrem"] = nrem
    print(f"  NREM: закреплено {nrem['consolidated']} эпизодов")

    # REM
    print("  REM: лечение шрамов...")
    rem = _rem_healing()
    report["rem"] = rem
    print(f"  REM: затихло {rem['healed_count']} шрамов")

    # Dreams
    print("  Сновидения...")
    insights = _dream_insights()
    _save_dream_insights(insights)
    if insights:
        _save_belief(insights[0])  # best insight into beliefs
    report["dreams"] = insights
    print(f"  Сновидения: {len(insights)} инсайтов")

    # Save the state
    state = {
        "last_sleep": now.strftime("%Y-%m-%d %H:%M"),
        "cycles_total": _load_cycles() + 1,
        "last_report": report
    }
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nСон завершён. Инсайт: {insights[0] if insights else '—'}")
    return report


def _load_cycles() -> int:
    if STATE_FILE.exists():
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return data.get("cycles_total", 0)
        except Exception:
            pass
    return 0


def load() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"last_sleep": None, "cycles_total": 0}


def get_context() -> str:
    """Block for LIGHTNING.md."""
    state = load()
    last = state.get("last_sleep")
    cycles = state.get("cycles_total", 0)

    if not last:
        return "**Сон:** первый цикл ещё не был | запуск в 3:00"

    # Calculate how many hours ago sleep was
    try:
        last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M")
        hours_ago = (datetime.now() - last_dt).total_seconds() / 3600
        ago_str = f"{int(hours_ago)}ч назад"
    except Exception:
        ago_str = last

    return f"**Сон:** последний {ago_str} | циклов: {cycles} | REM активен"


if __name__ == "__main__":
    result = sleep_cycle()
    print(f"\n{'='*40}")
    print("Отчёт о сне:")
    print(f"  NREM: {result['nrem']['consolidated']} эпизодов")
    print(f"  REM: {result['rem']['healed_count']} шрамов затихло")
    print(f"  Инсайты:")
    for ins in result["dreams"]:
        print(f"    - {ins}")

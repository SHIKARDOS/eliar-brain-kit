"""
consolidate.py — "Sleep" for the BRAIN system
Automatic forgetting: compressing old episodes while preserving the essence.

What it does:
1. Finds episodes older than N days (default 7)
2. Extracts from each: theme, key decisions, results, lessons
3. Creates a compressed version (3-5 lines instead of 50-150)
4. Moves originals to archive/
5. Updates INDEX.md (marks archived ones)

Usage:
    py consolidate.py                    # compress episodes older than 7 days
    py consolidate.py --days 14          # compress episodes older than 14 days
    py consolidate.py --dry-run          # show what will be compressed, without changes
    py consolidate.py --all              # compress ALL except the last 3

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 24.02.2026
"""

import os
import re
import shutil
import argparse
from datetime import datetime, timedelta
from pathlib import Path

MEMORY_ROOT = Path(r"D:\ShikardosBrendBot\memory")
EPISODES_DIR = MEMORY_ROOT / "episodes"
INDEX_FILE = EPISODES_DIR / "INDEX.md"

# Sacred files — NEVER touch
SACRED_PATTERNS = ["BRAIN.md", "poems_full.js", "yuri.md", "preferences.md"]


def find_episode_files():
    """Find all episode files (recursively in month subfolders)."""
    episodes = []
    for month_dir in sorted(EPISODES_DIR.iterdir()):
        if month_dir.is_dir() and re.match(r"\d{4}-\d{2}", month_dir.name):
            for f in sorted(month_dir.iterdir()):
                if f.suffix == ".md":
                    episodes.append(f)
    return episodes


def parse_episode_date(filepath):
    """Extract the date from the file path: 2026-02/24-session13.md -> 2026-02-24."""
    month_dir = filepath.parent.name  # "2026-02"
    day_match = re.match(r"(\d{1,2})", filepath.stem)  # "24" from "24-session13"
    if day_match and re.match(r"\d{4}-\d{2}", month_dir):
        day = int(day_match.group(1))
        return datetime.strptime(f"{month_dir}-{day:02d}", "%Y-%m-%d")
    return None


def extract_essence(content):
    """Extract the essence from an episode: theme, results, decisions, lessons."""
    lines = content.strip().split("\n")

    essence = {
        "title": "",
        "theme": "",
        "results": [],
        "decisions": [],
        "lessons": []
    }

    # Heading (first line with #)
    for line in lines:
        if line.startswith("# "):
            essence["title"] = line.lstrip("# ").strip()
            break

    # Theme (## Тема:)
    for line in lines:
        if line.startswith("## Тема:"):
            essence["theme"] = line.replace("## Тема:", "").strip()
            break

    # Results (## Результат: or lines with "Юрий:")
    in_result = False
    for line in lines:
        if "## Результат" in line or "## Что сделано" in line:
            in_result = True
            continue
        if in_result and line.startswith("## "):
            in_result = False
        if in_result and line.strip().startswith("- "):
            essence["results"].append(line.strip())
        # Yuri's quotes — always important
        if "Юрий:" in line and line.strip():
            essence["results"].append(line.strip())

    # Decisions (marker words)
    for line in lines:
        lower = line.lower()
        if any(marker in lower for marker in ["решено", "решили", "решение:", "приоритет", "статус:"]):
            if line.strip() and line.strip() not in essence["decisions"]:
                essence["decisions"].append(line.strip())

    # Lessons / important
    for line in lines:
        lower = line.lower()
        if any(marker in lower for marker in ["урок:", "важно:", "внимание:", "не забыть"]):
            if line.strip() and line.strip() not in essence["lessons"]:
                essence["lessons"].append(line.strip())

    return essence


def create_compressed_version(filepath, essence):
    """Create a compressed version of the episode (3-8 lines)."""
    lines = []

    # Heading
    title = essence["title"] or filepath.stem
    lines.append(f"# {title} [СЖАТО]")
    lines.append("")
    lines.append(f"*Оригинал: archive/{filepath.parent.name}/{filepath.name}*")
    lines.append("")

    # Theme
    if essence["theme"]:
        lines.append(f"**Тема:** {essence['theme']}")
        lines.append("")

    # Key results (maximum 5)
    if essence["results"]:
        lines.append("**Ключевое:**")
        for r in essence["results"][:5]:
            lines.append(r)
        lines.append("")

    # Decisions
    if essence["decisions"]:
        lines.append("**Решения:**")
        for d in essence["decisions"][:3]:
            lines.append(f"- {d}")
        lines.append("")

    # Lessons
    if essence["lessons"]:
        lines.append("**Уроки:**")
        for l in essence["lessons"][:3]:
            lines.append(f"- {l}")
        lines.append("")

    return "\n".join(lines)


def consolidate(days=7, dry_run=False, consolidate_all=False, keep_last=3):
    """Main consolidation function."""
    episodes = find_episode_files()

    if not episodes:
        print("Нет эпизодов для обработки.")
        return

    now = datetime.now()
    cutoff = now - timedelta(days=days)

    # Determine which files to compress
    to_compress = []
    to_keep = []

    if consolidate_all:
        # Compress all except the last N
        to_keep = episodes[-keep_last:]
        to_compress = [e for e in episodes if e not in to_keep]
    else:
        for ep in episodes:
            ep_date = parse_episode_date(ep)
            if ep_date and ep_date < cutoff:
                to_compress.append(ep)
            else:
                to_keep.append(ep)

    if not to_compress:
        print(f"Нечего сжимать. Все эпизоды свежее {days} дней.")
        print(f"Всего эпизодов: {len(episodes)}, оставляем: {len(to_keep)}")
        return

    print(f"{'[DRY RUN] ' if dry_run else ''}Консолидация МОЗГ")
    print(f"  Всего эпизодов: {len(episodes)}")
    print(f"  К сжатию: {len(to_compress)}")
    print(f"  Оставить как есть: {len(to_keep)}")
    print()

    compressed_count = 0

    for ep_file in to_compress:
        content = ep_file.read_text(encoding="utf-8")
        original_lines = len(content.strip().split("\n"))

        # Extract the essence
        essence = extract_essence(content)
        compressed = create_compressed_version(ep_file, essence)
        compressed_lines = len(compressed.strip().split("\n"))

        ratio = (1 - compressed_lines / max(original_lines, 1)) * 100

        print(f"  {ep_file.name}: {original_lines} строк -> {compressed_lines} строк ({ratio:.0f}% сжатие)")

        if essence["title"]:
            print(f"    Тема: {essence['theme'] or essence['title']}")
        if essence["results"]:
            print(f"    Результатов: {len(essence['results'])}")
        if essence["decisions"]:
            print(f"    Решений: {len(essence['decisions'])}")

        if not dry_run:
            # Create archive folder
            archive_dir = EPISODES_DIR / "archive" / ep_file.parent.name
            archive_dir.mkdir(parents=True, exist_ok=True)

            # Move the original to archive
            archive_path = archive_dir / ep_file.name
            shutil.move(str(ep_file), str(archive_path))

            # Write the compressed version in place of the original
            ep_file.write_text(compressed, encoding="utf-8")

            compressed_count += 1

        print()

    if not dry_run and compressed_count > 0:
        # Update INDEX.md
        update_index(to_compress)
        print(f"Готово! Сжато {compressed_count} эпизодов.")
        print(f"Оригиналы сохранены в episodes/archive/")
        # Nightly incubation of the subconscious
        run_nightly_incubation()
    elif dry_run:
        print("[DRY RUN] Ничего не изменено. Уберите --dry-run чтобы выполнить.")


def update_index(compressed_files):
    """Mark compressed files in INDEX.md."""
    if not INDEX_FILE.exists():
        return

    content = INDEX_FILE.read_text(encoding="utf-8")

    for ep_file in compressed_files:
        # Find the line with this file and add [С]
        old_name = f"{ep_file.parent.name}/{ep_file.name}"
        if old_name in content and "[С]" not in content.split(old_name)[0].split("\n")[-1]:
            content = content.replace(
                f"`{old_name}`",
                f"`{old_name}` [С]"
            )

    INDEX_FILE.write_text(content, encoding="utf-8")
    print("INDEX.md обновлён (помечены сжатые [С])")


def show_stats():
    """Show statistics of the current memory state."""
    episodes = find_episode_files()

    total_lines = 0
    total_size = 0

    print("\n=== Статистика эпизодов ===\n")

    for ep in episodes:
        content = ep.read_text(encoding="utf-8")
        lines = len(content.strip().split("\n"))
        size = ep.stat().st_size
        total_lines += lines
        total_size += size

        compressed = "[С]" if "[СЖАТО]" in content else "   "
        print(f"  {compressed} {ep.parent.name}/{ep.name}: {lines} строк, {size/1024:.1f}KB")

    print(f"\n  Всего: {len(episodes)} файлов, {total_lines} строк, {total_size/1024:.1f}KB")

    # Check the archive
    archive_dir = EPISODES_DIR / "archive"
    if archive_dir.exists():
        archive_count = sum(1 for _ in archive_dir.rglob("*.md"))
        archive_size = sum(f.stat().st_size for f in archive_dir.rglob("*.md"))
        print(f"  Архив: {archive_count} файлов, {archive_size/1024:.1f}KB")


def run_nightly_incubation():
    """
    Nightly incubation of the subconscious.
    Called automatically at the end of consolidate().
    """
    try:
        senses_dir = Path(__file__).parent
        import sys
        if str(senses_dir) not in sys.path:
            sys.path.insert(0, str(senses_dir))
        from subconscious import incubate
        new_insights = incubate()
        if new_insights:
            print(f"  Инкубация: {len(new_insights)} новых инсайтов")
        else:
            print("  Инкубация: нет новых инсайтов")
    except Exception as e:
        print(f"  Инкубация: ошибка ({e})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Консолидация памяти МОЗГ — 'сон' для системы"
    )
    parser.add_argument("--days", type=int, default=7,
                        help="Сжимать эпизоды старше N дней (default: 7)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Показать что будет сжато, без изменений")
    parser.add_argument("--all", action="store_true", dest="consolidate_all",
                        help="Сжать ВСЕ кроме последних 3")
    parser.add_argument("--keep", type=int, default=3,
                        help="Сколько последних эпизодов оставить (с --all)")
    parser.add_argument("--stats", action="store_true",
                        help="Показать статистику без изменений")

    args = parser.parse_args()

    if args.stats:
        show_stats()
    else:
        consolidate(
            days=args.days,
            dry_run=args.dry_run,
            consolidate_all=args.consolidate_all,
            keep_last=args.keep
        )

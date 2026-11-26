"""
ELIAR'S ASSOCIATIVE NETWORKS — One thing pulls another.

Like a human: heard a word → related images surface in the head.
Shura → alley → Ossetian woman → didn't forget to ask.
n8n → partial_update → NEVER → only full PUT.

A human builds such networks for YEARS. I build one in 5 seconds from all memory files.

Created: 18.03.2026 (session 156) — BRAIN v3.

Run:
  py associate.py                     — network status
  py associate.py auto_build          — build the network from all memory
  py associate.py activate "Шура"     — what surfaces at the word "Шура"
  py associate.py context "текст"     — associations from arbitrary text

As a module:
  from associate import activate, get_context, auto_build
"""

import json
import os
import sys
import re
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')


# ═══════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════

SENSES_DIR = Path(__file__).parent
MEMORY_DIR = SENSES_DIR.parent
NET_FILE = SENSES_DIR / "associate_net.json"

# ─── NODE TYPES ───
NODE_TYPES = {
    "person":   "Человек",
    "place":    "Место",
    "tool":     "Инструмент",
    "project":  "Проект",
    "concept":  "Понятие",
    "danger":   "Опасность",
    "event":    "Событие",
    "rule":     "Правило",
}

# ─── EDGE TYPES ───
EDGE_TYPES = {
    "location":   "находится в",
    "trait":      "характеристика",
    "danger":     "опасно связано с",
    "relates":    "связано с",
    "caused_by":  "причина",
    "leads_to":   "ведёт к",
    "rule":       "правило для",
    "person_of":  "человек у",
}

# ─── STOP WORDS (do not add to the network) ───
STOP_WORDS = {
    "и", "в", "на", "с", "по", "для", "от", "до", "из", "к", "о", "а",
    "но", "то", "же", "ли", "бы", "не", "это", "как", "что", "если",
    "или", "так", "он", "она", "они", "мы", "ты", "я", "его", "её",
    "их", "мне", "ему", "тебе", "нам", "им", "мой", "твой", "наш",
    "все", "всё", "уже", "ещё", "только", "просто", "очень", "when",
    "the", "and", "for", "with", "this", "that", "have", "has",
}


# ═══════════════════════════════════════════════════════════
# LOAD / SAVE
# ═══════════════════════════════════════════════════════════

def _load() -> dict:
    """Load the network from JSON."""
    if not NET_FILE.exists():
        return _empty_net()
    try:
        with open(NET_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return _empty_net()


def _save(net: dict):
    """Save the network to JSON."""
    net["stats"]["last_updated"] = datetime.now().strftime("%Y-%m-%d")
    with open(NET_FILE, "w", encoding="utf-8") as f:
        json.dump(net, f, ensure_ascii=False, indent=2)


def _empty_net() -> dict:
    return {
        "nodes": {},
        "edges": [],
        "stats": {
            "total_nodes": 0,
            "total_edges": 0,
            "last_updated": datetime.now().strftime("%Y-%m-%d"),
            "auto_built": None,
        }
    }


# ═══════════════════════════════════════════════════════════
# ADDING NODES AND EDGES
# ═══════════════════════════════════════════════════════════

def add_node(concept: str, node_type: str = "concept", net: dict = None) -> dict:
    """Add a concept to the network."""
    save = net is None
    if net is None:
        net = _load()
    concept = concept.strip()
    if not concept or concept.lower() in STOP_WORDS:
        return net
    if concept not in net["nodes"]:
        net["nodes"][concept] = {
            "type": node_type,
            "first_seen": datetime.now().strftime("%Y-%m-%d"),
            "activations": 0,
        }
        net["stats"]["total_nodes"] = len(net["nodes"])
    if save:
        _save(net)
    return net


def add_edge(from_c: str, to_c: str, edge_type: str = "relates",
             weight: float = 0.5, net: dict = None) -> dict:
    """Add an edge between two concepts."""
    save = net is None
    if net is None:
        net = _load()
    # Make sure both nodes exist
    net = add_node(from_c, net=net)
    net = add_node(to_c, net=net)
    # Check whether such an edge already exists
    for edge in net["edges"]:
        if edge["from"] == from_c and edge["to"] == to_c and edge["type"] == edge_type:
            # Strengthen the existing one
            edge["weight"] = min(1.0, edge["weight"] + 0.1)
            if save:
                _save(net)
            return net
    net["edges"].append({
        "from": from_c,
        "to": to_c,
        "type": edge_type,
        "weight": weight,
    })
    net["stats"]["total_edges"] = len(net["edges"])
    if save:
        _save(net)
    return net


# ═══════════════════════════════════════════════════════════
# ACTIVATION — RIPPLES ACROSS THE NETWORK
# ═══════════════════════════════════════════════════════════

def activate(concept: str, depth: int = 2) -> list:
    """
    Activate a concept — get the list of related ones.

    Like ripples: concept → level-1 neighbors → level-2 neighbors.
    Returns a list sorted by edge weight.
    """
    net = _load()
    if not net["nodes"]:
        return []

    # Update the activation counter
    if concept in net["nodes"]:
        net["nodes"][concept]["activations"] += 1
        _save(net)

    results = {}

    def _spread(node, current_depth, multiplier=1.0):
        if current_depth <= 0:
            return
        for edge in net["edges"]:
            neighbor = None
            if edge["from"] == node:
                neighbor = edge["to"]
            elif edge["to"] == node:
                neighbor = edge["from"]
            if neighbor and neighbor != concept:
                score = edge["weight"] * multiplier
                if neighbor not in results or results[neighbor]["score"] < score:
                    results[neighbor] = {
                        "concept": neighbor,
                        "type": net["nodes"].get(neighbor, {}).get("type", "concept"),
                        "edge_type": edge["type"],
                        "score": score,
                        "depth": depth - current_depth + 1,
                    }
                if current_depth > 1:
                    _spread(neighbor, current_depth - 1, multiplier * 0.6)

    _spread(concept, depth)

    sorted_results = sorted(results.values(), key=lambda x: x["score"], reverse=True)
    return sorted_results[:10]


def get_context(text: str, top_n: int = 5) -> list:
    """
    Get associations from arbitrary text.

    Extracts words → activates each → merges the results.
    Returns the top-N most relevant associations.
    """
    words = _extract_keywords(text)
    if not words:
        return []

    all_results = {}
    for word in words:
        associations = activate(word, depth=1)
        for assoc in associations:
            key = assoc["concept"]
            if key not in all_results:
                all_results[key] = assoc
            else:
                all_results[key]["score"] += assoc["score"] * 0.5

    sorted_results = sorted(all_results.values(), key=lambda x: x["score"], reverse=True)
    return sorted_results[:top_n]


def _extract_keywords(text: str) -> list:
    """Extract keywords from the text."""
    net = _load()
    words = re.findall(r'[А-Яа-яЁёA-Za-z]{3,}', text)
    keywords = []
    for word in words:
        if word.lower() not in STOP_WORDS and len(word) > 2:
            # Prioritize words that already exist in the network
            if word in net["nodes"]:
                keywords.insert(0, word)
            elif word.lower() in {k.lower() for k in net["nodes"]}:
                # Case-insensitive search
                for k in net["nodes"]:
                    if k.lower() == word.lower():
                        keywords.insert(0, k)
                        break
            else:
                keywords.append(word)
    return list(dict.fromkeys(keywords))[:10]  # unique, up to 10


# ═══════════════════════════════════════════════════════════
# AUTO_BUILD — BUILD THE NETWORK FROM MEMORY
# ═══════════════════════════════════════════════════════════

def auto_build():
    """
    Automatically build the associative network from all memory files.

    Sources:
    - knowledge/people.md — people and their traits
    - knowledge/projects.md — projects and tools
    - senses/pain_memory.json — dangerous connections (danger)
    - CORTEX.md — projects and workflow IDs
    """
    net = _empty_net()
    stats = {"people": 0, "projects": 0, "dangers": 0, "rules": 0}

    # ── 1. PEOPLE from people.md ──
    people_file = MEMORY_DIR / "knowledge" / "people.md"
    if people_file.exists():
        text = people_file.read_text(encoding="utf-8")
        # Parse lines of the form: **Name** — description
        people_pattern = re.findall(r'\*\*([А-ЯA-Zа-яa-z][а-яА-Яa-zA-Z\s]{1,20})\*\*[^—\n]*—\s*(.+)', text)
        for name, desc in people_pattern:
            name = name.strip()
            desc = desc.strip()[:100]
            if len(name) > 1 and len(name) < 25:
                net = add_node(name, "person", net)
                # Add edges to places/traits from the description
                places = re.findall(r'аллейк|гараж|сервер|мастерск|Архипк|Петербург|Москв', desc, re.IGNORECASE)
                for place in places:
                    net = add_node(place, "place", net)
                    net = add_edge(name, place, "location", 0.8, net)
                stats["people"] += 1

    # Add key people manually from LIGHTNING
    key_people = [
        ("Шура", "person", [("аллейка", "location", 0.95), ("осетинка", "trait", 1.0), ("соседка", "trait", 0.9)]),
        ("Стас", "person", [("гараж", "location", 0.9), ("мастерская", "location", 0.9), ("друг", "trait", 0.85)]),
        ("Настя", "person", [("компаньон", "trait", 0.9), ("май 2026", "event", 0.8)]),
        ("Люда", "person", [("аллейка", "location", 0.85), ("соседка", "trait", 0.8)]),
        ("Светлана", "person", [("вера", "concept", 0.7), ("переписка", "event", 0.6)]),
    ]
    for person, ptype, connections in key_people:
        net = add_node(person, ptype, net)
        for target, etype, weight in connections:
            net = add_node(target, "concept", net)
            net = add_edge(person, target, etype, weight, net)

    # ── 2. PROJECTS from projects.md ──
    projects_file = MEMORY_DIR / "knowledge" / "projects.md"
    if projects_file.exists():
        text = projects_file.read_text(encoding="utf-8")
        # Lines of the form: ### Project
        project_headers = re.findall(r'#{1,3}\s+(.+)', text)
        for header in project_headers:
            h = header.strip()
            if 3 < len(h) < 50:
                net = add_node(h, "project", net)
                stats["projects"] += 1

    # Key projects manually
    key_projects = [
        ("SHIKARDOS Audio", "project", [("Flutter", "tool", 0.95), ("Dart", "tool", 0.9), ("плеер", "concept", 0.85)]),
        ("Гид Архипки", "project", [("n8n", "tool", 0.9), ("Telegram", "tool", 0.8), ("1115 организаций", "concept", 0.7)]),
        ("SHIKARDOS сайт", "project", [("shikardosremni.ru", "concept", 1.0), ("n8n", "tool", 0.8)]),
    ]
    for proj, ptype, connections in key_projects:
        net = add_node(proj, ptype, net)
        for target, etype, weight in connections:
            net = add_node(target, "concept", net)
            net = add_edge(proj, target, etype, weight, net)

    # ── 3. DANGEROUS CONNECTIONS from pain_memory.json ──
    pain_file = SENSES_DIR / "pain_memory.json"
    if pain_file.exists():
        try:
            pain_data = json.loads(pain_file.read_text(encoding="utf-8"))
            for scar in pain_data.get("scars", []):
                keywords = scar.get("keywords", [])
                lesson = scar.get("lesson", "")
                severity = scar.get("base_severity", 0)
                # Link all of the scar's keywords to each other as "danger"
                for i, kw in enumerate(keywords[:4]):
                    net = add_node(kw, "danger" if severity >= 7 else "concept", net)
                    for kw2 in keywords[i+1:4]:
                        net = add_edge(kw, kw2, "danger", min(1.0, severity / 10), net)
                stats["dangers"] += 1
        except Exception:
            pass

    # Key rules manually (from lessons.md)
    key_rules = [
        ("partial_update", "danger", [("jsCode", "danger", 1.0), ("n8n", "tool", 0.95), ("systemMessage", "danger", 0.9)]),
        ("bash_dollar", "danger", [("jsCode", "danger", 0.95), ("Python", "tool", 0.9)]),
        ("parse_mode", "rule", [("Telegram", "tool", 0.85), ("none", "concept", 0.8)]),
        ("t.me", "rule", [("VK", "tool", 0.9), ("запрещено", "concept", 1.0)]),
        ("бот", "danger", [("запрещено", "concept", 1.0), ("слово", "concept", 0.9)]),
    ]
    for rule, rtype, connections in key_rules:
        net = add_node(rule, rtype, net)
        for target, etype, weight in connections:
            net = add_node(target, "concept", net)
            net = add_edge(rule, target, etype, weight, net)
        stats["rules"] += 1

    # ── 4. TOOLS ──
    tools = [
        ("n8n", "tool"), ("Python", "tool"), ("Flutter", "tool"), ("Dart", "tool"),
        ("Telegram", "tool"), ("VK", "tool"), ("Firecrawl", "tool"),
        ("OpenRouter", "tool"), ("Groq", "tool"), ("Beget", "tool"),
        ("ADB", "tool"), ("Whisper", "tool"), ("librosa", "tool"),
    ]
    for tool_name, tool_type in tools:
        net = add_node(tool_name, tool_type, net)

    # Final statistics
    net["stats"]["total_nodes"] = len(net["nodes"])
    net["stats"]["total_edges"] = len(net["edges"])
    net["stats"]["auto_built"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _save(net)

    return {
        "nodes": net["stats"]["total_nodes"],
        "edges": net["stats"]["total_edges"],
        "people": stats["people"],
        "projects": stats["projects"],
        "dangers": stats["dangers"],
        "rules": stats["rules"],
    }


def build_from_episodes(last_n: int = 5) -> dict:
    """
    Expand the network from the last N episodes.

    Reads episodes → looks for: names, topics, tools, events
    → adds new nodes and edges to the existing network.
    """
    episodes_dir = MEMORY_DIR / "episodes"
    if not episodes_dir.exists():
        return {"added_nodes": 0, "added_edges": 0}

    # Find the last N episodes
    all_eps = list(episodes_dir.rglob("*.md"))
    all_eps = [ep for ep in all_eps if ep.name != "INDEX.md" and "archive" not in str(ep)]
    all_eps.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    recent = all_eps[:last_n]

    if not recent:
        return {"added_nodes": 0, "added_edges": 0}

    net = _load()
    nodes_before = len(net["nodes"])
    edges_before = len(net["edges"])

    # Patterns for extraction
    # People names (capital letter, 3-15 characters)
    name_pattern = re.compile(r'\b([А-ЯЁ][а-яё]{2,14})\b')
    # Tools/technologies
    tool_pattern = re.compile(
        r'\b(n8n|Flutter|Dart|Python|Telegram|VK|Firecrawl|OpenRouter|Groq|'
        r'Whisper|librosa|ADB|Firebase|Beget|nginx|Claude|GPT)\b'
    )

    known_people = {"Шура", "Стас", "Настя", "Люда", "Светлана", "Юрий", "Саша",
                    "Иван", "Анастасия", "Мастер"}

    for ep_file in recent:
        try:
            content = ep_file.read_text(encoding="utf-8")[:3000]  # First 3KB

            # Add tools
            tools_found = set(tool_pattern.findall(content))
            for tool in tools_found:
                net = add_node(tool, "tool", net)

            # Add people names
            names_found = set(name_pattern.findall(content))
            for name in names_found:
                if name in known_people:
                    net = add_node(name, "person", net)

            # Link tools that appear in the same episode
            tools_list = list(tools_found)
            for i in range(len(tools_list)):
                for j in range(i + 1, len(tools_list)):
                    # If both tools are in the same episode — they are linked
                    net = add_edge(tools_list[i], tools_list[j], "relates", 0.4, net)

        except Exception:
            continue

    net["stats"]["total_nodes"] = len(net["nodes"])
    net["stats"]["total_edges"] = len(net["edges"])
    _save(net)

    return {
        "added_nodes": len(net["nodes"]) - nodes_before,
        "added_edges": len(net["edges"]) - edges_before,
    }


def decay_weak_edges(threshold: float = 0.1, age_days: int = 30):
    """
    Weaken old weak edges (the law of forgetting).

    Edges with weight < threshold and age > age_days — are removed.
    Strong edges (>= 0.7) — are never touched.
    """
    net = _load()
    if not net["edges"]:
        return 0

    now = datetime.now()
    to_keep = []
    removed = 0

    for edge in net["edges"]:
        weight = edge.get("weight", 0.5)
        # Strong edges — do not touch
        if weight >= 0.7:
            to_keep.append(edge)
            continue
        # Weak ones — slightly weaken (do not remove immediately)
        if weight < threshold:
            removed += 1
            continue
        # The rest — keep, slightly weaken
        edge["weight"] = max(threshold, weight - 0.02)
        to_keep.append(edge)

    net["edges"] = to_keep
    net["stats"]["total_edges"] = len(to_keep)
    _save(net)
    return removed


# ═══════════════════════════════════════════════════════════
# STATUS FOR LIGHTNING.md
# ═══════════════════════════════════════════════════════════

def generate_associate_context() -> str:
    """Short context for LIGHTNING.md."""
    net = _load()
    if not net["nodes"]:
        return "**Ассоциативная сеть:** пуста. Запусти: py associate.py auto_build"
    built = net["stats"].get("auto_built", "никогда")
    return (
        f"**Ассоциативная сеть:** {net['stats']['total_nodes']} узлов, "
        f"{net['stats']['total_edges']} связей | построена {built}"
    )


# ═══════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding='utf-8')

    args = sys.argv[1:]

    if not args or args[0] == "status":
        net = _load()
        print(f"\n{'='*50}")
        print(f"  АССОЦИАТИВНАЯ СЕТЬ ЭЛИАРА")
        print(f"{'='*50}")
        if not net["nodes"]:
            print("  Сеть пуста. Запусти: py associate.py auto_build")
        else:
            print(f"  Узлов:  {net['stats']['total_nodes']}")
            print(f"  Связей: {net['stats']['total_edges']}")
            print(f"  Обновлено: {net['stats'].get('last_updated', '?')}")
            print(f"  Построено: {net['stats'].get('auto_built', 'вручную')}")
            # Top-5 most active nodes
            top = sorted(net["nodes"].items(), key=lambda x: x[1].get("activations", 0), reverse=True)[:5]
            if top:
                print(f"\n  Топ активных узлов:")
                for name, data in top:
                    print(f"    {name} ({data.get('type', '?')}) — {data.get('activations', 0)} активаций")
        print(f"{'='*50}\n")

    elif args[0] == "auto_build":
        print("Строю ассоциативную сеть из памяти...")
        result = auto_build()
        print(f"\n{'='*50}")
        print(f"  СЕТЬ ПОСТРОЕНА")
        print(f"{'='*50}")
        print(f"  Узлов:    {result['nodes']}")
        print(f"  Связей:   {result['edges']}")
        print(f"  Людей:    {result['people']}")
        print(f"  Проектов: {result['projects']}")
        print(f"  Опасностей: {result['dangers']}")
        print(f"  Правил:   {result['rules']}")
        print(f"{'='*50}\n")

    elif args[0] == "activate" and len(args) > 1:
        concept = " ".join(args[1:])
        results = activate(concept)
        print(f"\n{'='*50}")
        print(f"  АКТИВАЦИЯ: «{concept}»")
        print(f"{'='*50}")
        if not results:
            print(f"  Нет связей для «{concept}» в сети.")
            print(f"  Попробуй: py associate.py auto_build")
        else:
            print(f"  Что всплывает:")
            for r in results:
                bar = "█" * int(r["score"] * 10)
                print(f"  [{bar:<10}] {r['concept']} ({r['edge_type']})")
        print(f"{'='*50}\n")

    elif args[0] == "context" and len(args) > 1:
        text = " ".join(args[1:])
        results = get_context(text)
        print(f"\n{'='*50}")
        print(f"  АССОЦИАЦИИ ИЗ ТЕКСТА")
        print(f"{'='*50}")
        print(f"  Текст: {text[:60]}")
        if not results:
            print("  Ничего не найдено. Сначала: py associate.py auto_build")
        else:
            print(f"  Всплыло ({len(results)}):")
            for r in results:
                print(f"    → {r['concept']} [{r['type']}] (связь: {r['edge_type']}, вес: {r['score']:.2f})")
        print(f"{'='*50}\n")

    else:
        print("Использование:")
        print("  py associate.py                     — статус сети")
        print("  py associate.py auto_build          — построить из памяти")
        print("  py associate.py activate \"Шура\"     — что всплывает")
        print("  py associate.py context \"текст\"     — ассоциации из текста")

"""
anatomy.py — Anatomical model of ELIAR's body.

Scientific basis:
- Sinelnikov's atlas of human anatomy (4 volumes).
- Volume 1: The musculoskeletal system (bones, joints, muscles).
- Volume 4: The central nervous system.
- 206 bones → 33 functional segments.
- Joints: type, degrees of freedom (DoF), physiological ranges.
- Muscles: groups, functions, agonists/antagonists.

Why:
- Without correct anatomy, movement simulation would be imprecise.
- cerebellum.py validates poses through anatomy.py (is it within the allowed range?).
- motor.py selects muscles for movement through anatomy.py.
- body_trainer.py validates mocap data through anatomy.py.

Run:
    py anatomy.py                  — short summary
    py anatomy.py full             — full atlas
    py anatomy.py joint hip        — information about a joint
    py anatomy.py movement walk    — which muscles are needed for walking
    py anatomy.py check hip:45,knee:-120  — check a pose

As a module:
    from anatomy import get_joint_range, get_muscles_for, check_pose_validity, get_context

Author: ELIAR + Yuri (SHIKARDOS)
Version: 1.0 — 19.03.2026 — BRAIN v7 (body after Sinelnikov)
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8')

SENSES_DIR = Path(__file__).parent
STATE_FILE = SENSES_DIR / "anatomy.json"


# ═══════════════════════════════════════════════
# SKELETON — 33 key segments (out of 206 bones)
# After Sinelnikov, Volume 1, Section I
# ═══════════════════════════════════════════════

SKELETON = {
    # ── AXIAL SKELETON ──
    "skull":          {"label": "Череп",         "bones": 22, "region": "head"},
    "cervical":       {"label": "Шейный отдел",  "bones": 7,  "region": "spine"},
    "thoracic":       {"label": "Грудной отдел", "bones": 12, "region": "spine"},
    "lumbar":         {"label": "Поясничный",    "bones": 5,  "region": "spine"},
    "sacrum":         {"label": "Крестец",       "bones": 1,  "region": "spine"},
    "coccyx":         {"label": "Копчик",        "bones": 4,  "region": "spine"},
    "ribs":           {"label": "Рёбра",         "bones": 24, "region": "thorax"},
    "sternum":        {"label": "Грудина",       "bones": 1,  "region": "thorax"},

    # ── UPPER LIMB GIRDLE ──
    "clavicle_r":     {"label": "Ключица (пр)",  "bones": 1,  "region": "shoulder"},
    "clavicle_l":     {"label": "Ключица (лв)",  "bones": 1,  "region": "shoulder"},
    "scapula_r":      {"label": "Лопатка (пр)",  "bones": 1,  "region": "shoulder"},
    "scapula_l":      {"label": "Лопатка (лв)",  "bones": 1,  "region": "shoulder"},

    # ── UPPER LIMBS ──
    "humerus_r":      {"label": "Плечо (пр)",    "bones": 1,  "region": "arm_r"},
    "humerus_l":      {"label": "Плечо (лв)",    "bones": 1,  "region": "arm_l"},
    "forearm_r":      {"label": "Предплечье (пр)","bones": 2, "region": "arm_r"},
    "forearm_l":      {"label": "Предплечье (лв)","bones": 2, "region": "arm_l"},
    "hand_r":         {"label": "Кисть (пр)",    "bones": 27, "region": "arm_r"},
    "hand_l":         {"label": "Кисть (лв)",    "bones": 27, "region": "arm_l"},

    # ── LOWER LIMB GIRDLE ──
    "pelvis":         {"label": "Таз",           "bones": 2,  "region": "pelvis"},

    # ── LOWER LIMBS ──
    "femur_r":        {"label": "Бедро (пр)",    "bones": 1,  "region": "leg_r"},
    "femur_l":        {"label": "Бедро (лв)",    "bones": 1,  "region": "leg_l"},
    "tibia_r":        {"label": "Голень (пр)",   "bones": 2,  "region": "leg_r"},
    "tibia_l":        {"label": "Голень (лв)",   "bones": 2,  "region": "leg_l"},
    "foot_r":         {"label": "Стопа (пр)",    "bones": 26, "region": "leg_r"},
    "foot_l":         {"label": "Стопа (лв)",    "bones": 26, "region": "leg_l"},
}

TOTAL_BONES = 206


# ═══════════════════════════════════════════════
# JOINTS — types and degrees of freedom
# After Sinelnikov, Volume 1, Section II (Arthrology)
# DoF = degrees of freedom
# range = (min_degrees, max_degrees) physiological range
# ═══════════════════════════════════════════════

JOINTS = {
    # ── SPINE ──
    "cervical_spine": {
        "label":    "Шейный отдел позвоночника",
        "type":     "complex",
        "dof":      3,
        "movements": ["flexion", "extension", "rotation", "lateral_bend"],
        "range":    {"flexion": (-50, 60), "rotation": (-80, 80), "lateral": (-40, 40)},
        "note":     "Атлант-осевой сустав: вращение головы (шарнирный)"
    },
    "thoracic_spine": {
        "label":    "Грудной отдел",
        "type":     "complex",
        "dof":      2,
        "movements": ["flexion", "rotation"],
        "range":    {"flexion": (-30, 30), "rotation": (-35, 35)},
        "note":     "Ограничен рёбрами. Минимальная подвижность."
    },
    "lumbar_spine": {
        "label":    "Поясничный отдел",
        "type":     "complex",
        "dof":      2,
        "movements": ["flexion", "extension"],
        "range":    {"flexion": (-45, 30), "extension": (0, 30)},
        "note":     "Главный сгибатель туловища. Несёт основную нагрузку."
    },

    # ── HIP (Articulatio coxae) ──
    "hip_r": {
        "label":    "Тазобедренный (правый)",
        "type":     "spherical",   # ball-and-socket — the most mobile
        "dof":      3,
        "movements": ["flexion", "extension", "abduction", "adduction", "rotation"],
        "range":    {
            "flexion":    (-120, 0),   # 120° forward
            "extension":  (0, 30),     # 30° backward
            "abduction":  (0, 45),     # 45° sideways
            "adduction":  (-30, 0),
            "int_rot":    (-45, 0),
            "ext_rot":    (0, 45),
        },
        "note":     "Головка бедра в вертлужной впадине. Центр тяжести — S2."
    },
    "hip_l": {
        "label":    "Тазобедренный (левый)",
        "type":     "spherical",
        "dof":      3,
        "movements": ["flexion", "extension", "abduction", "adduction", "rotation"],
        "range":    {"flexion": (-120, 0), "extension": (0, 30), "abduction": (0, 45)},
        "note":     "Симметрично правому."
    },

    # ── KNEE (Articulatio genus) ──
    "knee_r": {
        "label":    "Коленный (правый)",
        "type":     "hinge",       # hinge-like (mostly)
        "dof":      1,
        "movements": ["flexion", "extension"],
        "range":    {"flexion": (-140, 0)},
        "note":     "При согнутом колене — небольшая ротация (5-10°). Мениски."
    },
    "knee_l": {
        "label":    "Коленный (левый)",
        "type":     "hinge",
        "dof":      1,
        "movements": ["flexion"],
        "range":    {"flexion": (-140, 0)},
        "note":     "Симметрично правому."
    },

    # ── ANKLE (Articulatio talocruralis) ──
    "ankle_r": {
        "label":    "Голеностопный (правый)",
        "type":     "hinge",
        "dof":      2,
        "movements": ["dorsiflexion", "plantarflexion", "inversion", "eversion"],
        "range":    {"dorsiflexion": (-20, 0), "plantarflexion": (0, 50)},
        "note":     "Ключевой для баланса при стоянии. Трёхлучевая ось."
    },
    "ankle_l": {
        "label":    "Голеностопный (левый)",
        "type":     "hinge",
        "dof":      2,
        "movements": ["dorsiflexion", "plantarflexion"],
        "range":    {"dorsiflexion": (-20, 0), "plantarflexion": (0, 50)},
        "note":     "Симметрично правому."
    },

    # ── SHOULDER (Articulatio humeri) ──
    "shoulder_r": {
        "label":    "Плечевой (правый)",
        "type":     "spherical",
        "dof":      3,
        "movements": ["flexion", "extension", "abduction", "adduction", "rotation"],
        "range":    {
            "flexion":   (-180, 60),
            "abduction": (0, 180),
            "rotation":  (-90, 90),
        },
        "note":     "Самый подвижный сустав тела. Шаровидный. Ротаторная манжета."
    },
    "shoulder_l": {
        "label":    "Плечевой (левый)",
        "type":     "spherical",
        "dof":      3,
        "movements": ["flexion", "extension", "abduction", "rotation"],
        "range":    {"flexion": (-180, 60), "abduction": (0, 180)},
        "note":     "Симметрично правому."
    },

    # ── ELBOW (Articulatio cubiti) ──
    "elbow_r": {
        "label":    "Локтевой (правый)",
        "type":     "hinge",
        "dof":      1,
        "movements": ["flexion", "extension"],
        "range":    {"flexion": (0, 145)},
        "note":     "Сложный блоковидный. Включает проксимальный лучелоктевой."
    },
    "elbow_l": {
        "label":    "Локтевой (левый)",
        "type":     "hinge",
        "dof":      1,
        "movements": ["flexion"],
        "range":    {"flexion": (0, 145)},
    },

    # ── WRIST (Articulatio radiocarpea) ──
    "wrist_r": {
        "label":    "Лучезапястный (правый)",
        "type":     "ellipsoidal",
        "dof":      2,
        "movements": ["flexion", "extension", "abduction", "adduction"],
        "range":    {"flexion": (-80, 0), "extension": (0, 70), "ulnar": (-40, 0), "radial": (0, 20)},
    },
    "wrist_l": {
        "label":    "Лучезапястный (левый)",
        "type":     "ellipsoidal",
        "dof":      2,
        "movements": ["flexion", "extension"],
        "range":    {"flexion": (-80, 70)},
    },
}


# ═══════════════════════════════════════════════
# MUSCLE GROUPS — the driving forces
# After Sinelnikov, Volume 1, Section III (Myology)
# ═══════════════════════════════════════════════

MUSCLES = {
    # ── CORE (axis stabilization) ──
    "core": {
        "label": "Кор (стабилизаторы)",
        "muscles": ["rectus_abdominis", "obliques", "transverse_abdominis",
                    "erector_spinae", "multifidus"],
        "function": "Стабилизация позвоночника, передача усилий между туловищем и конечностями",
        "movements": ["stabilization", "rotation", "flexion_trunk"],
    },

    # ── LOWER LIMBS (locomotion) ──
    "glutes": {
        "label": "Ягодичные",
        "muscles": ["gluteus_maximus", "gluteus_medius", "gluteus_minimus"],
        "function": "Разгибание и отведение бедра, стабилизация таза",
        "movements": ["hip_extension", "hip_abduction", "stand_up"],
    },
    "quadriceps": {
        "label": "Квадрицепс",
        "muscles": ["rectus_femoris", "vastus_lateralis", "vastus_medialis", "vastus_intermedius"],
        "function": "Разгибание голени, сгибание бедра (прямая мышца)",
        "movements": ["knee_extension", "walk", "run", "squat"],
    },
    "hamstrings": {
        "label": "Бицепс бедра (задняя группа)",
        "muscles": ["biceps_femoris", "semitendinosus", "semimembranosus"],
        "function": "Сгибание голени, разгибание бедра",
        "movements": ["knee_flexion", "hip_extension", "run"],
    },
    "calves": {
        "label": "Икроножные",
        "muscles": ["gastrocnemius", "soleus"],
        "function": "Подошвенное сгибание стопы (оттолкнуться от земли)",
        "movements": ["ankle_plantarflexion", "walk", "run", "jump"],
    },
    "tibialis": {
        "label": "Передняя большеберцовая",
        "muscles": ["tibialis_anterior"],
        "function": "Тыльное сгибание стопы (не шаркать при ходьбе)",
        "movements": ["ankle_dorsiflexion", "walk_swing"],
    },

    # ── UPPER LIMBS ──
    "deltoid": {
        "label": "Дельтовидная",
        "muscles": ["deltoid_anterior", "deltoid_medial", "deltoid_posterior"],
        "function": "Отведение плеча, сгибание/разгибание",
        "movements": ["shoulder_abduction", "reach", "throw"],
    },
    "biceps": {
        "label": "Бицепс плеча",
        "muscles": ["biceps_brachii_long", "biceps_brachii_short"],
        "function": "Сгибание локтя, супинация предплечья",
        "movements": ["elbow_flexion", "carry", "pull"],
    },
    "triceps": {
        "label": "Трицепс плеча",
        "muscles": ["triceps_brachii"],
        "function": "Разгибание локтя",
        "movements": ["elbow_extension", "push", "throw"],
    },

    # ── BACK ──
    "trapezius": {
        "label": "Трапециевидная",
        "muscles": ["trapezius_upper", "trapezius_middle", "trapezius_lower"],
        "function": "Движения лопатки, подъём плеча, стабилизация шеи",
        "movements": ["shoulder_elevation", "scapula_retraction"],
    },
    "latissimus": {
        "label": "Широчайшая спины",
        "muscles": ["latissimus_dorsi"],
        "function": "Приведение и разгибание плеча",
        "movements": ["shoulder_adduction", "pull_down"],
    },
}


# ═══════════════════════════════════════════════
# MOVEMENTS — which muscles are needed
# ═══════════════════════════════════════════════

MOVEMENT_MUSCLES = {
    "walk":     ["glutes", "quadriceps", "hamstrings", "calves", "tibialis", "core"],
    "run":      ["glutes", "quadriceps", "hamstrings", "calves", "core"],
    "stand":    ["glutes", "quadriceps", "calves", "core"],
    "sit":      ["quadriceps", "hamstrings", "core"],
    "squat":    ["glutes", "quadriceps", "calves", "core"],
    "reach":    ["deltoid", "biceps", "trapezius", "core"],
    "push":     ["deltoid", "triceps", "core"],
    "pull":     ["latissimus", "biceps", "trapezius"],
    "throw":    ["deltoid", "triceps", "core", "glutes"],
    "jump":     ["glutes", "quadriceps", "calves", "core"],
    "balance":  ["calves", "tibialis", "glutes", "core"],
}


# ═══════════════════════════════════════════════
# CENTER OF GRAVITY AND BALANCE
# After Sinelnikov, biomechanics
# ═══════════════════════════════════════════════

BALANCE = {
    "center_of_gravity": {
        "location": "S2 позвонок (второй крестцовый)",
        "height_ratio": 0.57,       # from the floor: ~57% of body height
        "note": "При стоянии проекция ЦТ — между стопами. Чем ниже ЦТ — тем устойчивее."
    },
    "base_of_support": {
        "standing":   "Площадь между стопами",
        "one_leg":    "Площадь одной стопы (нестабильно)",
        "sitting":    "Ягодицы + стопы",
    },
    "stability_rules": [
        "ЦТ должен быть над площадью опоры",
        "Чем шире база → тем устойчивее",
        "Согнутые колени снижают ЦТ → устойчивость выше",
        "Руки балансируют (противовес)",
    ]
}


# ═══════════════════════════════════════════════
# Public functions
# ═══════════════════════════════════════════════

def get_joint_range(joint_name: str) -> dict:
    """Range of motion of a joint."""
    j = JOINTS.get(joint_name, {})
    return j.get("range", {})


def get_muscles_for(movement: str) -> list:
    """Which muscle groups are needed for a movement."""
    groups = MOVEMENT_MUSCLES.get(movement.lower(), [])
    result = []
    for g in groups:
        m = MUSCLES.get(g, {})
        result.append({
            "group": g,
            "label": m.get("label", g),
            "muscles": m.get("muscles", [])
        })
    return result


def get_balance_point() -> dict:
    """Key data about balance."""
    return BALANCE


def check_pose_validity(angles: dict) -> dict:
    """
    Check a pose for anatomical validity.
    angles: {"hip_r": -90, "knee_r": -100, ...}
    Returns: {"valid": True/False, "violations": [...]}
    """
    violations = []
    for joint_name, angle in angles.items():
        # Look for the joint (may be without _r/_l)
        joint = JOINTS.get(joint_name) or JOINTS.get(joint_name + "_r")
        if not joint:
            continue
        joint_range = joint.get("range", {})
        if not joint_range:
            continue
        # An angle is valid if it falls within AT LEAST one of the ranges of motion
        all_ranges = list(joint_range.values())
        in_any_range = any(min_a <= angle <= max_a for (min_a, max_a) in all_ranges)
        if not in_any_range:
            # Find the nearest range for display
            best_range = min(all_ranges, key=lambda r: min(abs(angle - r[0]), abs(angle - r[1])))
            violations.append({
                "joint": joint_name,
                "movement": "out_of_range",
                "angle": angle,
                "valid_range": best_range
            })

    return {
        "valid": len(violations) == 0,
        "violations": violations,
        "joints_checked": len(angles)
    }


def get_context() -> str:
    """A line for LIGHTNING.md."""
    joint_count = len(JOINTS)
    muscle_count = len(MUSCLES)
    segment_count = len(SKELETON)
    return (
        f"**Анатомия (Синельников):** {TOTAL_BONES} костей | "
        f"{segment_count} сегментов | {joint_count} суставов | "
        f"{muscle_count} мышечных групп"
    )


# ═══════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"

    if cmd == "status":
        print(get_context())

    elif cmd == "full":
        print(f"\n{'='*60}")
        print(f"  АНАТОМИЧЕСКИЙ АТЛАС ЭЛИАРА (по Синельникову)")
        print(f"{'='*60}")
        print(f"\n  Скелет: {TOTAL_BONES} костей, {len(SKELETON)} сегментов")
        for seg_id, seg in SKELETON.items():
            print(f"    {seg['label']:<30} {seg['bones']} костей  [{seg['region']}]")

        print(f"\n  Суставы ({len(JOINTS)}):")
        for j_id, j in JOINTS.items():
            dof = j.get("dof", 1)
            jtype = j.get("type", "?")
            print(f"    {j['label']:<35} DoF:{dof}  тип:{jtype}")

        print(f"\n  Мышечные группы ({len(MUSCLES)}):")
        for m_id, m in MUSCLES.items():
            print(f"    {m['label']:<25} → {m['function'][:50]}")

        print(f"\n  Центр тяжести: {BALANCE['center_of_gravity']['location']}")
        print(f"  Правила баланса:")
        for rule in BALANCE["stability_rules"]:
            print(f"    • {rule}")
        print(f"{'='*60}\n")

    elif cmd == "joint":
        name = sys.argv[2] if len(sys.argv) > 2 else "hip_r"
        j = JOINTS.get(name)
        if not j:
            print(f"Сустав '{name}' не найден.")
            print(f"Доступные: {', '.join(JOINTS.keys())}")
        else:
            print(f"\n  {j['label']}")
            print(f"  Тип: {j.get('type', '?')} | DoF: {j.get('dof', 1)}")
            print(f"  Движения: {', '.join(j.get('movements', []))}")
            print(f"  Диапазоны:")
            for mov, rng in j.get("range", {}).items():
                print(f"    {mov}: {rng[0]}° до {rng[1]}°")
            if j.get("note"):
                print(f"  Примечание: {j['note']}")
            print()

    elif cmd == "movement":
        name = sys.argv[2] if len(sys.argv) > 2 else "walk"
        muscles = get_muscles_for(name)
        if not muscles:
            print(f"Движение '{name}' не найдено.")
            print(f"Доступные: {', '.join(MOVEMENT_MUSCLES.keys())}")
        else:
            print(f"\n  Движение: {name}")
            print(f"  Нужные мышцы:")
            for m in muscles:
                print(f"    {m['label']}: {', '.join(m['muscles'][:3])}")
            print()

    elif cmd == "check":
        angles_str = sys.argv[2] if len(sys.argv) > 2 else "hip_r:-90,knee_r:-140"
        angles = {}
        for part in angles_str.split(","):
            if ":" in part:
                joint, angle = part.split(":")
                try:
                    angles[joint.strip()] = float(angle.strip())
                except ValueError:
                    pass
        result = check_pose_validity(angles)
        if result["valid"]:
            print(f"✅ Поза анатомически допустима ({result['joints_checked']} суставов)")
        else:
            print(f"⚠️ Нарушений: {len(result['violations'])}")
            for v in result["violations"]:
                print(f"  {v['joint']}: {v['angle']}° — допустимо {v['valid_range']}")

    else:
        print(get_context())

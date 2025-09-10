# api/utils/suggestion_scoring.py

def get_priority_weight(priority: str) -> int:
    mapping = {"P1": 3, "P2": 2, "P3": 1}
    return mapping.get(priority, 0)


def expertise_match(guide_expertise: list[str], group_broad_areas: list[str]) -> bool:
    for exp in guide_expertise:
        for area in group_broad_areas:
            if exp.lower() in area.lower():
                return True
    return False


def calculate_score(priority: str, match: bool) -> int:
    return get_priority_weight(priority) + (2 if match else 0)

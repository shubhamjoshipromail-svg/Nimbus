import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.json"


def load_seed() -> dict[str, Any]:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def get_reference_now(seed: dict[str, Any] | None = None) -> datetime:
    current_seed = seed or load_seed()
    latest_logged_day = datetime.fromisoformat(current_seed["sleep_log"][-1]["date"])
    return latest_logged_day + timedelta(days=1, hours=9)


def _format_recent_sleep(seed: dict[str, Any], days: int = 7) -> str:
    recent_sleep = seed["sleep_log"][-days:]
    return "; ".join(
        f"{entry['date']}: {entry['hours']}h (bed {entry['bedtime']}, up {entry['wake_time']})"
        for entry in recent_sleep
    )


def _format_recent_check_ins(seed: dict[str, Any], days: int = 7) -> str:
    recent_check_ins = seed["check_ins"][-days:]
    formatted = []
    for entry in recent_check_ins:
        note = f" - note: {entry['note']}" if entry.get("note") else ""
        formatted.append(f"{entry['date']}: load {entry['load_rating']}{note}")
    return "; ".join(formatted)


def _format_screen_shift(seed: dict[str, Any], days: int = 7) -> str:
    baseline = seed["baseline"]
    recent = seed["screen_time_log"][-days:]
    avg_total = sum(entry["total_hours"] for entry in recent) / len(recent)
    avg_late = sum(entry["late_night_hours"] for entry in recent) / len(recent)
    avg_social = sum(entry["social_media_hours"] for entry in recent) / len(recent)
    return (
        f"Last {days} days average {avg_total:.1f}h total vs baseline {baseline['avg_screen_time_hours']:.1f}h; "
        f"late-night {avg_late:.1f}h vs {baseline['avg_late_night_screen_hours']:.1f}h baseline; "
        f"social {avg_social:.1f}h vs {baseline['avg_social_media_hours']:.1f}h baseline."
    )


def _format_upcoming_deadlines(seed: dict[str, Any], days: int = 7) -> str:
    now = get_reference_now(seed)
    window_end_date = now.date() + timedelta(days=days)
    deadlines = []
    for event in seed["calendar_events"]:
        if event["type"] != "deadline":
            continue
        start = datetime.fromisoformat(event["start"])
        if now <= start and start.date() <= window_end_date:
            deadlines.append(f"{start.strftime('%Y-%m-%d %a %I:%M%p')}: {event['title']}")
    if not deadlines:
        return "None in the next 7 days."
    return "; ".join(deadlines)


def get_context_summary() -> str:
    seed = load_seed()
    user_profile = seed["user_profile"]
    stress_signal = seed["current_stress_signal"]

    return "\n".join(
        [
            f"STUDENT: {user_profile['name']}, CS Year 3",
            f"CURRENT STATE: {stress_signal['summary']}",
            f"LAST 7 DAYS SLEEP: {_format_recent_sleep(seed)}",
            f"LAST 7 DAYS LOAD CHECK-INS: {_format_recent_check_ins(seed)}",
            f"SCREEN TIME SHIFT: {_format_screen_shift(seed)}",
            f"UPCOMING DEADLINES (next 7 days): {_format_upcoming_deadlines(seed)}",
            f"BASELINE FOR COMPARISON: {json.dumps(seed['baseline'])}",
            f"KNOWN COPING PREFERENCES: {', '.join(user_profile['coping_preferences'])}",
        ]
    )


def log_interaction(user_msg: str, agent_response: str, tool_calls: list[Any]) -> None:
    seed = load_seed()
    seed.setdefault("interaction_history", []).append(
        {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "user_message": user_msg,
            "agent_response": agent_response,
            "tool_calls": tool_calls,
        }
    )
    with DATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(seed, file, indent=2)

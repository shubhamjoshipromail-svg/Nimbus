import json
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

try:
    import psycopg
    from psycopg.types.json import Json
except ImportError:  # pragma: no cover - optional in local-only mode
    psycopg = None
    Json = None


DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.json"
INTERACTIONS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS interaction_history (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    user_message TEXT NOT NULL,
    agent_response TEXT NOT NULL,
    tool_calls JSONB NOT NULL DEFAULT '[]'::jsonb
);
"""


def _get_database_url() -> str | None:
    database_url = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL")
    if database_url and psycopg is not None:
        return database_url
    return None


def _ensure_interactions_table(connection: Any) -> None:
    with connection.cursor() as cursor:
        cursor.execute(INTERACTIONS_TABLE_SQL)
    connection.commit()


def _load_interactions_from_db(limit: int = 50) -> list[dict[str, Any]]:
    database_url = _get_database_url()
    if not database_url:
        return []

    with psycopg.connect(database_url) as connection:
        _ensure_interactions_table(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT timestamp, user_message, agent_response, tool_calls
                FROM interaction_history
                ORDER BY timestamp ASC
                LIMIT %s
                """,
                (limit,),
            )
            rows = cursor.fetchall()

    return [
        {
            "timestamp": timestamp.isoformat(timespec="seconds"),
            "user_message": user_message,
            "agent_response": agent_response,
            "tool_calls": tool_calls or [],
        }
        for timestamp, user_message, agent_response, tool_calls in rows
    ]


def load_seed() -> dict[str, Any]:
    with DATA_PATH.open("r", encoding="utf-8") as file:
        seed = json.load(file)

    db_interactions = _load_interactions_from_db()
    if db_interactions:
        seed["interaction_history"] = db_interactions

    return seed


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
    database_url = _get_database_url()
    if database_url:
        with psycopg.connect(database_url) as connection:
            _ensure_interactions_table(connection)
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO interaction_history (user_message, agent_response, tool_calls)
                    VALUES (%s, %s, %s)
                    """,
                    (user_msg, agent_response, Json(tool_calls)),
                )
            connection.commit()
        return

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

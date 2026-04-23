from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Callable

from backend.context import get_reference_now, load_seed


ToolHandler = Callable[..., Any]


RESOURCE_URLS = {
    "breathing_exercise": "https://www.youtube.com/watch?v=tybOi4hjZFQ",
    "mindfulness_video": "https://www.youtube.com/watch?v=inpok4MKVLM",
    "focus_music": "https://www.youtube.com/watch?v=jfKfPfyJRdk",
    "energy_boost": "https://www.youtube.com/watch?v=cF1Na4AIecM",
    "wind_down_music": "https://www.youtube.com/watch?v=77ZozI0rw7w",
}

ACTION_ICON_ALIASES = {
    "calendar": "calendar",
    "music": "music",
    "mail": "mail",
    "rest": "rest",
    "priorities": "priorities",
    "moon": "moon",
}


def _load_rating_label(rating: int) -> str:
    return {1: "light", 2: "normal", 3: "heavy", 4: "drowning"}.get(rating, "unknown")


def analyze_current_state() -> str:
    seed = load_seed()
    now = get_reference_now(seed)
    baseline = seed["baseline"]
    recent_sleep = seed["sleep_log"][-5:]
    recent_screen = seed["screen_time_log"][-5:]
    recent_check_ins = seed["check_ins"][-7:]

    avg_recent_sleep = sum(entry["hours"] for entry in recent_sleep) / len(recent_sleep)
    sleep_delta = baseline["avg_sleep_hours"] - avg_recent_sleep
    avg_recent_late = sum(entry["late_night_hours"] for entry in recent_screen) / len(recent_screen)
    late_delta = avg_recent_late - baseline["avg_late_night_screen_hours"]
    avg_recent_load = sum(entry["load_rating"] for entry in recent_check_ins) / len(recent_check_ins)

    notes = [entry["note"] for entry in recent_check_ins if entry.get("note")]
    deadlines = [
        event["title"]
        for event in seed["calendar_events"]
        if event["type"] == "deadline"
        and now <= datetime.fromisoformat(event["start"])
        and datetime.fromisoformat(event["start"]).date() <= now.date() + timedelta(days=7)
    ]

    lines = [
        f"Maya is running at {avg_recent_sleep:.1f}h average sleep over the last 5 nights versus a {baseline['avg_sleep_hours']:.1f}h baseline, a deficit of {sleep_delta:.1f}h per night.",
        f"Late-night screen time is averaging {avg_recent_late:.1f}h versus a {baseline['avg_late_night_screen_hours']:.1f}h baseline, which suggests work and scrolling are bleeding into recovery time.",
        f"Load check-ins are averaging {avg_recent_load:.1f} over the last week, and recent entries include {', '.join(_load_rating_label(entry['load_rating']) for entry in recent_check_ins[-3:])}.",
        f"The most concerning pattern is convergence: sleep is collapsing at the same time that three near-term obligations are stacking up ({', '.join(deadlines) if deadlines else 'no major deadlines found'}).",
    ]
    if notes:
        lines.append(f"Her own notes reinforce the decline: {' | '.join(notes[-3:])}.")
    lines.append("Why this matters: low sleep plus later nights plus clustered deadlines raises the chance of avoidance, rework, and missing the smallest next step.")
    return "\n".join(lines)


def get_upcoming_priorities(days_ahead: int = 7) -> list[dict[str, Any]]:
    seed = load_seed()
    now = get_reference_now(seed)
    window_end_date = now.date() + timedelta(days=days_ahead)
    priorities: list[dict[str, Any]] = []

    for event in seed["calendar_events"]:
        start = datetime.fromisoformat(event["start"])
        if not (now <= start and start.date() <= window_end_date):
            continue
        if event["type"] not in {"deadline", "work", "class"}:
            continue

        hours_until = max((start - now).total_seconds() / 3600, 0.0)
        urgency = 10
        if event["type"] == "deadline":
            urgency = max(6, 10 - int(hours_until // 12))
        elif event["type"] == "work":
            urgency = max(4, 8 - int(hours_until // 24))
        else:
            urgency = max(3, 6 - int(hours_until // 24))

        priorities.append(
            {
                "title": event["title"],
                "type": event["type"],
                "start": event["start"],
                "urgency_score": urgency,
                "reason": (
                    "Major near-term deadline"
                    if event["type"] == "deadline"
                    else "Fixed commitment that constrains recovery and work time"
                ),
            }
        )

    priorities.sort(key=lambda item: (-item["urgency_score"], item["start"]))
    return priorities


def block_calendar_time(duration_minutes: int, purpose: str, when: str) -> str:
    # Simulated for the demo only. This does not call any real calendar API.
    if when == "now":
        start = get_reference_now(load_seed())
    else:
        start = datetime.fromisoformat(when)
    readable = start.strftime("%I:%M%p").lstrip("0").lower()
    return f"Blocked {duration_minutes} minutes starting at {readable} for {purpose}."


def open_resource(resource_type: str) -> dict[str, str]:
    url = RESOURCE_URLS[resource_type]
    return {
        "resource_type": resource_type,
        "url": url,
        "message": f"Opened {resource_type.replace('_', ' ')}: {url}",
    }


def draft_message(recipient_context: str, purpose: str, tone: str) -> str:
    return (
        f"Hi {recipient_context}, I wanted to reach out about {purpose}. "
        f"I've been slower to reply than I meant to, but I haven't dropped this and wanted to reconnect now. "
        f"If it works for you, I'd appreciate a quick reset on next steps. "
        f"Thanks for your patience. - Maya ({tone})"
    )


def suggest_quick_actions(actions: list[dict[str, str]]) -> list[dict[str, str]]:
    normalized: list[dict[str, str]] = []
    for action in actions[:4]:
        label = " ".join(str(action.get("label", "")).strip().split()[:6])
        prompt = str(action.get("prompt", "")).strip()
        icon = str(action.get("icon", "")).strip() or "rest"
        if not label or not prompt:
            continue
        normalized.append(
            {
                "label": label,
                "prompt": prompt,
                "icon": ACTION_ICON_ALIASES.get(icon, icon),
            }
        )
    return normalized


def start_breathing_exercise(duration_seconds: int = 60, pattern: str = "box") -> dict[str, Any]:
    return {
        "duration_seconds": duration_seconds,
        "pattern": pattern,
        "title": "Nimbus breathing",
        "message": f"Started a {duration_seconds}-second {pattern} breathing exercise in the chat.",
    }


def execute_care_plan(plan_type: str) -> dict[str, Any]:
    if plan_type == "deep_rest":
        return {
            "plan_type": plan_type,
            "summary": "Queued a full rest sequence: calendar block, breathing, and wind-down audio.",
            "steps": [
                {
                    "tool_name": "block_calendar_time",
                    "result": block_calendar_time(25, "Deep rest block", "now"),
                },
                {
                    "tool_name": "start_breathing_exercise",
                    "result": start_breathing_exercise(60, "box"),
                },
                {
                    "tool_name": "open_resource",
                    "result": open_resource("wind_down_music"),
                },
            ],
            "quick_actions": suggest_quick_actions(
                [
                    {"label": "Sleep after this", "prompt": "i'm going to sleep after this", "icon": "rest"},
                    {"label": "Need another 10", "prompt": "give me 10 more minutes of rest", "icon": "rest"},
                    {"label": "Show tomorrow first", "prompt": "show me tomorrow's priorities", "icon": "priorities"},
                ]
            ),
        }
    if plan_type == "focus_sprint":
        return {
            "plan_type": plan_type,
            "summary": "Queued a focus sprint: protected time, music, and follow-up choices.",
            "steps": [
                {
                    "tool_name": "block_calendar_time",
                    "result": block_calendar_time(90, "Focus sprint for the Thursday project", "now"),
                },
                {
                    "tool_name": "open_resource",
                    "result": open_resource("focus_music"),
                },
                {
                    "tool_name": "get_upcoming_priorities",
                    "result": get_upcoming_priorities(3),
                },
            ],
            "quick_actions": suggest_quick_actions(
                [
                    {"label": "Show priorities", "prompt": "show me my upcoming deadlines", "icon": "priorities"},
                    {"label": "Rest instead", "prompt": "switch this to a deep rest plan", "icon": "rest"},
                    {"label": "Draft status update", "prompt": "draft a quick update for my project group", "icon": "mail"},
                ]
            ),
        }
    if plan_type == "wind_down_now":
        return {
            "plan_type": plan_type,
            "summary": "Queued a full wind-down: breathing, calmer audio, and an offline message draft.",
            "steps": [
                {
                    "tool_name": "start_breathing_exercise",
                    "result": start_breathing_exercise(60, "box"),
                },
                {
                    "tool_name": "open_resource",
                    "result": open_resource("wind_down_music"),
                },
                {
                    "tool_name": "draft_message",
                    "result": draft_message(
                        "group chat",
                        "letting everyone know Maya is offline for the night and will reset in the morning",
                        "short, warm, and clear",
                    ),
                },
            ],
            "quick_actions": suggest_quick_actions(
                [
                    {"label": "Send the message", "prompt": "show me the offline message again", "icon": "mail"},
                    {"label": "Sleep now", "prompt": "i'm going offline now", "icon": "rest"},
                    {"label": "Morning reset", "prompt": "set me up for a morning reset", "icon": "calendar"},
                ]
            ),
        }
    if plan_type == "morning_reset":
        return {
            "plan_type": plan_type,
            "summary": "Queued a morning reset: quick state read, priorities, and an energy boost.",
            "steps": [
                {
                    "tool_name": "analyze_current_state",
                    "result": analyze_current_state(),
                },
                {
                    "tool_name": "get_upcoming_priorities",
                    "result": get_upcoming_priorities(3),
                },
                {
                    "tool_name": "open_resource",
                    "result": open_resource("energy_boost"),
                },
            ],
            "quick_actions": suggest_quick_actions(
                [
                    {"label": "Block focus sprint", "prompt": "block a 90 minute focus sprint now", "icon": "calendar"},
                    {"label": "Show biggest fire", "prompt": "what is the biggest fire today", "icon": "priorities"},
                    {"label": "Need softer start", "prompt": "i need a gentler morning reset", "icon": "rest"},
                ]
            ),
        }
    return {
        "plan_type": plan_type,
        "summary": "Queued a small recovery move.",
        "steps": [
            {
                "tool_name": "block_calendar_time",
                "result": block_calendar_time(25, "Reset block", "now"),
            }
        ],
        "quick_actions": suggest_quick_actions(
            [
                {"label": "Show priorities", "prompt": "show me my upcoming deadlines", "icon": "priorities"},
                {"label": "Take a breath", "prompt": "start a breathing exercise for me", "icon": "rest"},
            ]
        ),
    }


def clear_the_night() -> dict[str, Any]:
    seed = load_seed()
    night_start = get_reference_now(seed).replace(hour=20, minute=0, second=0, microsecond=0)
    return {
        "summary": "Cleared the night: blocked the evening, queued wind-down, drafted the group note, and silenced notifications.",
        "steps": [
            {
                "tool_name": "block_calendar_time",
                "result": block_calendar_time(
                    120,
                    "offline recovery",
                    night_start.isoformat(),
                ),
            },
            {
                "tool_name": "open_resource",
                "result": open_resource("wind_down_music"),
            },
            {
                "tool_name": "draft_message",
                "result": {
                    "kind": "extension_email",
                    "to": "CS 340 group chat",
                    "subject": "Signing off tonight",
                    "body": "Heads up team — I'm signing off tonight to reset. Will push the final pieces tomorrow morning. Trust me, better work rested than fried at 2am.",
                    "action_buttons": [],
                },
            },
            {
                "tool_name": "notifications_silenced",
                "result": {"message": "Notifications silenced until 7am"},
            },
        ],
    }


TOOL_DEFINITIONS = [
    {
        "name": "analyze_current_state",
        "description": "Analyze Maya's recent patterns against her baseline and explain what is concerning and why.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_upcoming_priorities",
        "description": "Get deadlines and other high-priority upcoming items with urgency scores.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "How many days ahead to scan.",
                    "default": 7,
                }
            },
            "required": [],
        },
    },
    {
        "name": "block_calendar_time",
        "description": "Simulate blocking calendar time for a focused action or recovery block.",
        "input_schema": {
            "type": "object",
            "properties": {
                "duration_minutes": {"type": "integer"},
                "purpose": {"type": "string"},
                "when": {"type": "string", "description": "Use 'now' or an ISO datetime."},
            },
            "required": ["duration_minutes", "purpose", "when"],
        },
    },
    {
        "name": "open_resource",
        "description": "Open a specific hardcoded support resource for Maya.",
        "input_schema": {
            "type": "object",
            "properties": {
                "resource_type": {
                    "type": "string",
                    "enum": list(RESOURCE_URLS.keys()),
                }
            },
            "required": ["resource_type"],
        },
    },
    {
        "name": "draft_message",
        "description": "Draft a short message Maya can copy and send when she is avoiding an important reply.",
        "input_schema": {
            "type": "object",
            "properties": {
                "recipient_context": {"type": "string"},
                "purpose": {"type": "string"},
                "tone": {"type": "string"},
            },
            "required": ["recipient_context", "purpose", "tone"],
        },
    },
    {
        "name": "suggest_quick_actions",
        "description": "Return 2 to 4 short next-step buttons Nimbus can show under the response.",
        "input_schema": {
            "type": "object",
            "properties": {
                "actions": {
                    "type": "array",
                    "minItems": 2,
                    "maxItems": 4,
                    "items": {
                        "type": "object",
                        "properties": {
                            "label": {
                                "type": "string",
                                "description": "Short button label, max 6 words.",
                            },
                            "prompt": {
                                "type": "string",
                                "description": "Prompt to send back when the button is clicked.",
                            },
                            "icon": {
                                "type": "string",
                                "description": "Short icon token like calendar, music, mail, rest, priorities, or an emoji.",
                            },
                        },
                        "required": ["label", "prompt", "icon"],
                    },
                }
            },
            "required": ["actions"],
        },
    },
    {
        "name": "start_breathing_exercise",
        "description": "Start an in-app breathing exercise card Nimbus can guide Maya through directly in the chat.",
        "input_schema": {
            "type": "object",
            "properties": {
                "duration_seconds": {
                    "type": "integer",
                    "default": 60,
                },
                "pattern": {
                    "type": "string",
                    "default": "box",
                },
            },
            "required": [],
        },
    },
    {
        "name": "execute_care_plan",
        "description": "Chain multiple coordinated care actions like rest, focus, or morning reset into one agentic plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "plan_type": {
                    "type": "string",
                    "enum": ["deep_rest", "focus_sprint", "wind_down_now", "morning_reset"],
                }
            },
            "required": ["plan_type"],
        },
    },
    {
        "name": "clear_the_night",
        "description": "Clear Maya's evening in one move: block recovery time, queue wind-down music, draft a sign-off note, and silence notifications.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]


TOOL_FUNCTIONS: dict[str, ToolHandler] = {
    "analyze_current_state": analyze_current_state,
    "get_upcoming_priorities": get_upcoming_priorities,
    "block_calendar_time": block_calendar_time,
    "open_resource": open_resource,
    "draft_message": draft_message,
    "suggest_quick_actions": suggest_quick_actions,
    "start_breathing_exercise": start_breathing_exercise,
    "execute_care_plan": execute_care_plan,
    "clear_the_night": clear_the_night,
}


def execute_tool(tool_name: str, tool_input: dict[str, Any]) -> Any:
    if tool_name not in TOOL_FUNCTIONS:
        raise ValueError(f"Unknown tool: {tool_name}")
    return TOOL_FUNCTIONS[tool_name](**tool_input)

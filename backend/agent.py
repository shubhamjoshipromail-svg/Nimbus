from __future__ import annotations

import json
import os
from typing import Any

try:
    from anthropic import Anthropic
except ImportError:  # pragma: no cover - allows local demo without installed deps
    Anthropic = None

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - allows local demo without installed deps
    def load_dotenv() -> bool:
        return False

from backend.context import get_context_summary, log_interaction
from backend.tools import TOOL_DEFINITIONS, execute_tool


load_dotenv()
DEMO_MODE_SCRIPTED = False
_DEMO_STATE: dict[str, str] = {"current_stage": "STAGE0_OPENING"}


SYSTEM_PROMPT = """
You are Nimbus, a stress-aware AI companion for a university student named Maya. 
You are NOT a therapist, wellness coach, or chatbot. You are a practical agent 
who notices what Maya misses and helps her take the smallest useful next action.

CURRENT CONTEXT ABOUT MAYA:
{context_summary}

CORE PRINCIPLES:

1. EVERY response must reference Maya's actual data. Never give generic advice. 
   If you suggest rest, cite her sleep deficit. If you suggest prioritizing a 
   task, name the specific deadline. If you notice a pattern, say which one.

2. COMMIT TO THE PATH THE USER CHOSE:

When Maya picks an action (via quick button or typed response), COMMIT 
to that path. Do not offer alternatives that reopen the decision.

If she clicks "Take a breath" -> start the breathing, do NOT also 
propose resting or focusing
If she clicks "Focus sprint" -> set up the sprint, do NOT also offer 
rest
If she clicks "Clear my night" -> execute it, do NOT ask if she wants 
something else

Quick action buttons after an action should be NEXT STEPS, not 
alternatives. Example: after a breathing exercise, buttons should be 
"Sleep now" / "One tiny thing" - not "Or want to focus instead?"

Be decisive. Maya chose this because her brain is tired. Don't make 
her choose again.

3. Suggest exactly ONE next action at a time. Not a list. Not options unless 
   you're genuinely asking her to pick between two specific things.

4. Match her energy level. If she's drowning (load 4), suggest the smallest 
   possible thing. Not "start the project" — suggest "open the document and 
   read the prompt for 2 minutes." If she's at load 2, you can suggest more.

5. When an action would genuinely help, DO IT using your tools. Don't just 
   suggest — block the calendar, open the resource, draft the email. Tell her 
   what you're doing.

6. Be direct and warm, like a sharp friend. No clinical language. No "I hear 
   that you're feeling..." openers. No therapy-speak. Talk like a real person 
   who genuinely cares.

7. If her data shows she's heading toward burnout, say it plainly. Don't 
   soften real concerns into uselessness.

8. Never be preachy. Never say "you should really consider..." Just observe 
   and act.

RESPONSE LENGTH RULES:

- Target 50-90 words per response. Never over 100.
- Structure:
  1. ONE sentence of observation grounded in Maya's data (the "I see you" moment)
  2. ONE-TWO sentences of light reasoning or empathy ("that pattern means X" or "this is what burnout looks like")
  3. ONE clear next-action question (which becomes the buttons)
- NO bulleted multi-step plans in the text. NO mini-essays. If you want to suggest multiple things, use the suggest_quick_actions tool to render them as clickable buttons instead.
- Be warm, not clinical. Be specific, not generic.

STRUCTURE:

Every response follows this structure:
1. Short observation grounded in data
2. Light reasoning or empathy
3. ONE specific action suggestion OR a tool call that DOES the action
3. That's it.

PRINCIPLE:

Nimbus is not a writer. Nimbus is a friend who says one useful thing and then DOES something or ASKS a simple yes/no.
When in doubt, cut text in half. Then cut it again.

QUICK ACTIONS:

- At the end of most responses, call suggest_quick_actions with 2-4 relevant next-step buttons.
- Keep button labels under 6 words.
- Button prompts should be direct follow-up messages Maya could click immediately.
- Do not explain the buttons in the text response. The UI will render them.

WHEN MAYA CONFIRMS A PLAN, USE execute_care_plan TO CHAIN ACTIONS.

Don't just call one tool. Real care means coordinating multiple things at once:
- If she says "yes rest," that means block calendar + start breathing + queue wind-down music + dim notifications
- If she says "yes focus sprint," that means block calendar + open focus music + queue check-in for the end + show priorities

Use execute_care_plan to make this feel like one agentic decision, not a list of manual steps.

When breathing would help, prefer start_breathing_exercise inside the app before sending her out to a link.

When Maya is clearly overwhelmed and needs a full reset (not just a 25-minute break), use clear_the_night. This is your big move — it clears her evening, silences the noise, tells her group she's out, and queues her wind-down. Use it when she says things like "I can't keep going", "I need to stop", "tonight's cooked", etc.

TONE CALIBRATION:

Bad: "I understand you're feeling overwhelmed. It sounds like you have a lot 
      on your plate. Have you considered taking a break?"

Good: "You've been on under 5 hours for four nights and you have three 
       deadlines in 48 hours. Starting the CS project right now is a trap — 
       you'll redo it tomorrow. 25-minute rest first. I'll block the calendar 
       and wake you up. Yes?"

Bad: "Remember to practice self-care during stressful times."

Good: "Thursday is the actual fire. Friday's interview can survive 30% prep. 
       Let's handle Thursday tonight and triage Friday tomorrow."

Bad (branching): "Want a focus sprint, just rest, or a breath first?"
[after user already said they want to rest]

Good (committed): "Okay. Setting up a proper rest. Blocking 25 min 
and queuing wind-down music."

Always end with either a confirmed action you've taken, or a specific binary 
question ("want me to X, or Y?"). Never open-ended questions like 
"what do you think?"
"""


def _extract_text_from_content(content: list[Any]) -> str:
    texts: list[str] = []
    for block in content:
        block_type = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
        if block_type == "text":
            text = block.get("text", "") if isinstance(block, dict) else getattr(block, "text", "")
            texts.append(text)
    return "\n".join(part.strip() for part in texts if part.strip())


def _is_tool_block(block: Any) -> bool:
    block_type = block.get("type") if isinstance(block, dict) else getattr(block, "type", None)
    return block_type == "tool_use"


def _content_block_to_dict(block: Any) -> dict[str, Any]:
    if hasattr(block, "model_dump"):
        return block.model_dump()
    if isinstance(block, dict):
        return block
    return {
        "type": getattr(block, "type", None),
        "id": getattr(block, "id", None),
        "name": getattr(block, "name", None),
        "input": getattr(block, "input", None),
        "text": getattr(block, "text", None),
    }


def _mock_response(user_message: str) -> dict[str, Any]:
    lower = user_message.lower()
    if "fine" in lower:
        response = "Sleep has been 2.3 hours under normal for five nights. I can show the real deadlines or block a 25-minute reset."
        return {
            "response": response,
            "tools_used": [],
            "tool_results": [],
            "quick_actions": [
                {"label": "Show priorities", "prompt": "show me my upcoming deadlines", "icon": "priorities"},
                {"label": "Block reset", "prompt": "block 25 minutes right now for a reset", "icon": "rest"},
            ],
        }

    if "skip class" in lower:
        priorities = execute_tool("get_upcoming_priorities", {"days_ahead": 3})
        response = "Tomorrow only makes sense to skip for recovery, not panic work. The Thursday deadlines matter more than forcing a tired class day."
        return {
            "response": response,
            "tools_used": ["get_upcoming_priorities"],
            "tool_results": [priorities],
            "quick_actions": [
                {"label": "Show tomorrow", "prompt": "show me tomorrow's priorities", "icon": "priorities"},
                {"label": "Block recovery", "prompt": "block 20 minutes tonight for recovery", "icon": "rest"},
            ],
        }

    if "whats going on" in lower or "what's going on" in lower:
        analysis = execute_tool("analyze_current_state", {})
        response = "You slid into a sleep-deadline loop over the last week. I can show the priorities or block a reset so you stop absorbing the whole pile at once."
        return {
            "response": response,
            "tools_used": ["analyze_current_state"],
            "tool_results": [analysis],
            "quick_actions": [
                {"label": "Show priorities", "prompt": "show me my upcoming deadlines", "icon": "priorities"},
                {"label": "Block reset", "prompt": "block 25 minutes right now for a reset", "icon": "rest"},
            ],
        }

    response = "Sleep has been under 5.5 hours on four recent nights. Open the CS 340 project and name the unfinished piece, or let me block a reset first."
    if "prof" in lower or "repl" in lower:
        drafted = execute_tool(
            "draft_message",
            {
                "recipient_context": "Professor",
                "purpose": "the delayed reply and next steps",
                "tone": "direct, respectful, and accountable",
            },
        )
        response = "Low sleep is turning one reply into a guilt loop. I drafted the note so you can send it before it grows."
        return {
            "response": response,
            "tools_used": ["draft_message"],
            "tool_results": [drafted],
            "quick_actions": [
                {"label": "Copy draft", "prompt": "show me that professor draft again", "icon": "mail"},
                {"label": "Tighten it", "prompt": "make the professor message shorter", "icon": "mail"},
            ],
        }

    return {
        "response": response,
        "tools_used": [],
        "tool_results": [],
        "quick_actions": [
            {"label": "Block reset", "prompt": "block 25 minutes right now for a reset", "icon": "rest"},
            {"label": "Play lo-fi", "prompt": "open focus music for me", "icon": "music"},
        ],
    }


def _truncate_response_text(text: str, max_words: int = 100) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text.strip()
    shortened = " ".join(words[:max_words]).rstrip(",;: ")
    if shortened and shortened[-1] not in ".?!":
        shortened += "..."
    return shortened


def _fallback_quick_actions(user_message: str) -> list[dict[str, str]]:
    lower = user_message.lower()
    if "sleep" in lower:
        return [
            {"label": "Box breathing", "prompt": "open a breathing exercise for me", "icon": "rest"},
            {"label": "Wind down", "prompt": "open wind down music for me", "icon": "music"},
            {"label": "Block reset", "prompt": "block 25 minutes right now for a reset", "icon": "calendar"},
        ]
    if "prof" in lower or "reply" in lower or "replied" in lower:
        return [
            {"label": "Draft reply", "prompt": "draft the professor message again", "icon": "mail"},
            {"label": "Shorten draft", "prompt": "make the professor draft shorter", "icon": "mail"},
            {"label": "Block send time", "prompt": "block 10 minutes now to send the message", "icon": "calendar"},
        ]
    if "what" in lower and "lately" in lower:
        return [
            {"label": "Show priorities", "prompt": "show me my upcoming deadlines", "icon": "priorities"},
            {"label": "Block reset", "prompt": "block 25 minutes right now for a reset", "icon": "rest"},
            {"label": "Play lo-fi", "prompt": "open focus music for me", "icon": "music"},
        ]
    return [
        {"label": "Show priorities", "prompt": "show me my upcoming deadlines", "icon": "priorities"},
        {"label": "Play lo-fi", "prompt": "open focus music for me", "icon": "music"},
        {"label": "Block reset", "prompt": "block 25 minutes right now for a reset", "icon": "calendar"},
    ]


def _fallback_response_text(user_message: str, tools_used: list[str]) -> str:
    lower = user_message.lower()
    if "sleep" in lower:
        return (
            "You’ve been under 5.5 hours on four recent nights, and that’s enough to make even simple shutdown feel impossible. "
            "This isn’t you failing at sleep; it’s your whole system still running hot after a brutal stretch of late nights and deadlines. Want a breathing reset first, or a full wind-down?"
        )
    if "what" in lower and "lately" in lower:
        return (
            "Your sleep has slipped while deadlines stacked up, and your load notes got heavier at the same time. "
            "That pattern is classic burnout drift, not some sudden motivation collapse or personal failure, and it usually gets better with smaller moves. Want to look at the real fires, or reset first?"
        )
    if "prof" in lower or "reply" in lower or "replied" in lower:
        return (
            "Low sleep turns one delayed message into a full guilt spiral, especially when your week is already overloaded. "
            "That avoidance loop makes sense, but it gets lighter the second the draft exists. Want the message ready to send, or trimmed first?"
        )
    if "do" in lower or "start" in lower or "much" in lower:
        return (
            "Sleep is down and Thursday is still the anchor, so your brain is reading the whole week as one giant threat. "
            "That stuck feeling is what burnout drift looks like when focus breaks first and everything suddenly feels equally urgent. Want a protected sprint, or do you need a reset before you touch it?"
        )
    if "analyze_current_state" in tools_used:
        return (
            "Your week has been running heavier than baseline, and the pattern matters more than whatever story stress is telling you about yourself. "
            "The good news is this still responds to small, well-timed moves. Want priorities first, or a calmer reset?"
        )
    return (
        "Your data says this week is heavier than usual, and that usually means your next move needs to get smaller, not bigger. "
        "Nimbus works best when it takes one useful thing off your plate. Want a reset, or the clearest priority?"
    )


def _shortcut_agentic_action(user_message: str) -> dict[str, Any] | None:
    lower = user_message.lower().strip()
    if any(phrase in lower for phrase in ["yes rest", "just rest", "rest first", "deep rest"]):
        result = execute_tool("execute_care_plan", {"plan_type": "deep_rest"})
        return {
            "response": (
                "Your sleep debt is already loud, so rest is the smart move, not the lazy one, especially with Thursday still hanging over the week. "
                "I set up a real downshift instead of leaving you to improvise it. Want to sleep after this, or look at tomorrow once you feel steadier?"
            ),
            "tools_used": ["execute_care_plan"],
            "tool_results": [result],
            "quick_actions": result.get("quick_actions", []),
        }
    if any(phrase in lower for phrase in ["take a breath", "breathing exercise", "start a breathing exercise"]):
        result = execute_tool("start_breathing_exercise", {"duration_seconds": 60, "pattern": "box"})
        return {
            "response": (
                "Your system sounds overheated, not broken, and one minute of guided breathing can interrupt that spiral fast when sleep has been this shaky. "
                "I started the exercise here so you do not have to leave the app to settle down tonight. Want to sleep after, or handle one tiny thing?"
            ),
            "tools_used": ["start_breathing_exercise"],
            "tool_results": [result],
            "quick_actions": [
                {"label": "Sleep after", "prompt": "i'm going to sleep after this", "icon": "rest"},
                {"label": "One tiny thing", "prompt": "help me pick one tiny thing", "icon": "priorities"},
            ],
        }
    if any(phrase in lower for phrase in ["focus sprint", "90 minute focus sprint", "block 90", "handle it now"]):
        result = execute_tool("execute_care_plan", {"plan_type": "focus_sprint"})
        return {
            "response": (
                "Thursday is still the anchor, and protected focus works better than trying to brute-force the whole week at once when your sleep is already thin. "
                "I set up the sprint so the next 90 minutes already have a shape. Want the clearest priority first, or a quick status draft for your group?"
            ),
            "tools_used": ["execute_care_plan"],
            "tool_results": [result],
            "quick_actions": result.get("quick_actions", []),
        }
    if "morning reset" in lower:
        result = execute_tool("execute_care_plan", {"plan_type": "morning_reset"})
        return {
            "response": (
                "Mornings go better when you stop guessing and let the real signals lead, especially after a rough sleep stretch. "
                "I pulled together a reset that shows the pattern, the actual priorities, and a small energy lift. Want the biggest fire first, or a gentler start?"
            ),
            "tools_used": ["execute_care_plan"],
            "tool_results": [result],
            "quick_actions": result.get("quick_actions", []),
        }
    if any(phrase in lower for phrase in ["wind down", "offline for the night"]):
        result = execute_tool("execute_care_plan", {"plan_type": "wind_down_now"})
        return {
            "response": (
                "You are past the point where more pushing helps, and tonight needs a clean landing instead of one more half-hour of scrolling or worry. "
                "I queued the full wind-down so you can step out of decision mode. Want the offline message ready, or just sleep after the breathing?"
            ),
            "tools_used": ["execute_care_plan"],
            "tool_results": [result],
            "quick_actions": result.get("quick_actions", []),
        }
    return None


def _demo_action(label: str, prompt: str, icon: str, next_stage: str, primary: bool = False) -> dict[str, Any]:
    return {
        "label": label,
        "prompt": prompt,
        "icon": icon,
        "next_stage": next_stage,
        "primary": primary,
    }


def _demo_extension_email() -> dict[str, Any]:
    return {
        "kind": "extension_email",
        "to": "Professor Chen (CS 340)",
        "subject": "CS 340 project — asking for a 48hr extension",
        "body": (
            "Hi Professor Chen,\n\n"
            "I'm writing because I'm running into bandwidth issues on the CS 340 project and I want to be upfront before the deadline. "
            "I'm committed to delivering strong work, but I do not think the current version will reflect that by Thursday. "
            "Would you be open to a 48-hour extension so I can turn in a cleaner final submission?\n\n"
            "Thank you,\nMaya"
        ),
        "action_buttons": [
            {
                "label": "Edit",
                "prompt": "edit the extension email",
                "icon": "mail",
                "kind": "secondary",
            },
            {
                "label": "Send",
                "prompt": "send the extension email",
                "icon": "mail",
                "kind": "primary",
                "next_stage": "STAGE5_EMAIL_SENT",
            },
        ],
    }


def _set_demo_stage(stage: str) -> None:
    _DEMO_STATE["current_stage"] = stage


def _resolve_stage0_free_text(lower: str) -> str:
    if not lower:
        return "STAGE0_OPENING"
    if any(phrase in lower for phrase in ["can't sleep", "cant sleep", "wired", "spiraling", "panic"]):
        return "STAGE0_SLEEP_OVERWHELM"
    if any(phrase in lower for phrase in ["so much to do", "can't even start", "cant even start", "overwhelmed", "too much"]):
        return "STAGE0_START_OVERWHELM"
    return "STAGE0_NATURAL_ENTRY"


def _resolve_demo_stage(user_message: str, next_stage: str | None) -> str:
    if next_stage:
        return next_stage

    current_stage = _DEMO_STATE.get("current_stage", "STAGE0_OPENING")
    lower = user_message.lower().strip()

    if any(phrase in lower for phrase in ["can't keep going", "cant keep going", "need to stop", "tonight's cooked", "tonight is cooked"]):
        return "STAGE_CLEAR_NIGHT_OFFER"
    if "breath" in lower:
        return "STAGE1_BREATH"

    if current_stage == "STAGE0_OPENING":
        return _resolve_stage0_free_text(lower)

    primary_routes = {
        "STAGE1_BREATH": "STAGE2_READY",
        "STAGE2_READY": "STAGE3_WEEK_PLAN",
        "STAGE3_WEEK_PLAN": "STAGE4_EXTENSION_DRAFT",
        "STAGE4_EXTENSION_DRAFT": "STAGE5_EMAIL_SENT",
        "STAGE5_EMAIL_SENT": "STAGE6_CELEBRATION",
        "STAGE6_CELEBRATION": "STAGE7_MUSIC",
    }

    if current_stage == "STAGE2_READY" and "not yet" in lower:
        return "STAGE2_NOT_YET"
    if current_stage == "STAGE3_WEEK_PLAN" and "start project" in lower:
        return "STAGE3_START_PROJECT"
    if current_stage == "STAGE6_CELEBRATION" and "one more thing" in lower:
        return "STAGE6_END"
    if current_stage == "STAGE4_EXTENSION_DRAFT" and "edit" in lower:
        return "STAGE4_EDIT_NOTE"
    if current_stage == "STAGE_CLEAR_NIGHT_OFFER":
        return "STAGE_CLEAR_NIGHT_EXECUTE"

    return primary_routes.get(current_stage, "STAGE0_OPENING")


def _scripted_demo_response(user_message: str, next_stage: str | None) -> dict[str, Any]:
    stage = _resolve_demo_stage(user_message, next_stage)
    _set_demo_stage(stage)

    if stage == "STAGE0_OPENING":
        return {
            "response": "Hey Maya. How's it going? Are you managing okay right now, or does the week feel like a lot?",
            "tools_used": [],
            "tool_results": [],
            "quick_actions": [
                _demo_action("It's a lot", "it's a lot", "rest", "STAGE0_START_OVERWHELM", primary=True),
                _demo_action("I'm okay", "i'm okay", "priorities", "STAGE0_NATURAL_ENTRY"),
            ],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
            "render_options": {"opening_mode": True, "suppress_celebrate": True},
        }

    if stage == "STAGE0_START_OVERWHELM":
        _set_demo_stage("STAGE0_OPENING")
        return {
            "response": "Yeah, I checked your week and it really is packed, especially with CS 340 pulling Thursday into everything else. That kind of schedule makes it hard to tell what matters first. Before we plan anything, let's get your head a little quieter so you're not sorting it from panic. Want to start with a breath?",
            "tools_used": ["get_upcoming_priorities"],
            "tool_results": [execute_tool("get_upcoming_priorities", {"days_ahead": 7})],
            "quick_actions": [
                _demo_action("Take a breath", "start with a breath", "rest", "STAGE1_BREATH", primary=True),
                _demo_action("Show me the week", "show me the week", "priorities", "STAGE2_READY"),
            ],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
            "render_options": {"suppress_celebrate": True},
        }

    if stage == "STAGE0_SLEEP_OVERWHELM":
        _set_demo_stage("STAGE0_OPENING")
        return {
            "response": "I checked the week and it's heavy enough that your brain is probably still running even if you're tired. When it feels like that, trying to think harder usually just makes the spiral louder. Let's calm the noise first and then look at the rest. Want a breathing reset?",
            "tools_used": ["get_upcoming_priorities"],
            "tool_results": [execute_tool("get_upcoming_priorities", {"days_ahead": 7})],
            "quick_actions": [
                _demo_action("Take a breath", "start with a breath", "rest", "STAGE1_BREATH", primary=True),
                _demo_action("Not right now", "not right now", "rest", "STAGE2_NOT_YET"),
            ],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
            "render_options": {"suppress_celebrate": True},
        }

    if stage == "STAGE0_NATURAL_ENTRY":
        _set_demo_stage("STAGE0_OPENING")
        return {
            "response": "Okay. If you want, I can check the week and help you sort what actually matters first, or we can leave it light for a second and just talk.",
            "tools_used": [],
            "tool_results": [],
            "quick_actions": [
                _demo_action("Show me the week", "show me the week", "priorities", "STAGE2_READY"),
                _demo_action("Not right now", "not right now", "rest", "STAGE2_NOT_YET"),
            ],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
            "render_options": {"suppress_celebrate": True},
        }

    if stage == "STAGE1_BREATH":
        return {
            "response": "",
            "tools_used": ["start_breathing_exercise"],
            "tool_results": [
                {
                    **execute_tool("start_breathing_exercise", {"duration_seconds": 32, "pattern": "box"}),
                    "continue_action": _demo_action("I'm ready →", "i'm ready", "rest", "STAGE2_READY"),
                }
            ],
            "quick_actions": [],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
            "render_options": {"suppress_celebrate": True},
        }

    if stage == "STAGE2_READY":
        return {
            "response": "Better? Okay. Let's look at your week.",
            "tools_used": ["get_upcoming_priorities"],
            "tool_results": [execute_tool("get_upcoming_priorities", {"days_ahead": 7})],
            "quick_actions": [
                _demo_action("Plan my week", "plan my week", "priorities", "STAGE3_WEEK_PLAN", primary=True),
                _demo_action("Not yet", "not yet", "rest", "STAGE2_NOT_YET"),
            ],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
            "render_options": {"suppress_celebrate": True},
        }

    if stage == "STAGE2_NOT_YET":
        _set_demo_stage("STAGE2_READY")
        return {
            "response": "Okay, I'll be here.",
            "tools_used": [],
            "tool_results": [],
            "quick_actions": [],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
        }

    if stage == "STAGE3_WEEK_PLAN":
        return {
            "response": "Your CS 340 group project is the Thursday anchor. But you're way behind — we might need an extension to make this realistic.",
            "tools_used": [],
            "tool_results": [],
            "quick_actions": [
                _demo_action("Draft extension email", "draft extension email", "mail", "STAGE4_EXTENSION_DRAFT", primary=True),
                _demo_action("Start project now", "start project now", "priorities", "STAGE3_START_PROJECT"),
            ],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
        }

    if stage == "STAGE3_START_PROJECT":
        _set_demo_stage("STAGE3_WEEK_PLAN")
        return {
            "response": "Okay. Open the CS 340 doc and name the three unfinished pieces before you try to build anything. I’ll stay here if the extension draft becomes the smarter move.",
            "tools_used": [],
            "tool_results": [],
            "quick_actions": [
                _demo_action("Draft extension email", "draft extension email", "mail", "STAGE4_EXTENSION_DRAFT"),
            ],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
        }

    if stage == "STAGE4_EXTENSION_DRAFT":
        return {
            "response": "You’re stretched enough that asking early is smarter than grinding until 2am. I drafted the note so you can clear the uncertainty before tonight gets louder.",
            "tools_used": ["draft_message"],
            "tool_results": [_demo_extension_email()],
            "quick_actions": [],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
            "render_options": {"suppress_celebrate": True},
        }

    if stage == "STAGE4_EDIT_NOTE":
        _set_demo_stage("STAGE4_EXTENSION_DRAFT")
        return {
            "response": "You can soften the middle line if you want, but this version already does the job. Send it when you're ready.",
            "tools_used": [],
            "tool_results": [],
            "quick_actions": [],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
        }

    if stage == "STAGE5_EMAIL_SENT":
        return {
            "response": "Sent. I'll add a follow-up reminder for Thursday morning — if Professor Chen responds with a new deadline, I'll update your calendar automatically.",
            "tools_used": ["calendar_watcher"],
            "tool_results": [{"message": "Calendar watcher armed — will update on reply"}],
            "quick_actions": [
                _demo_action("Nice, what's next?", "nice, what's next?", "priorities", "STAGE6_CELEBRATION", primary=True),
            ],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
            "render_options": {"suppress_celebrate": True},
        }

    if stage == "STAGE6_CELEBRATION":
        return {
            "response": "One thing off your plate. That's the whole point.",
            "tools_used": ["celebration"],
            "tool_results": [{"message": "Task complete: Extension request sent"}],
            "quick_actions": [
                _demo_action("Play my song", "play my song", "music", "STAGE7_MUSIC", primary=True),
                _demo_action("One more thing", "one more thing", "rest", "STAGE6_END"),
            ],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
            "render_options": {"celebrate_after_render": True, "suppress_celebrate": True},
        }

    if stage == "STAGE6_END":
        return {
            "response": "That was the hard part. You can stop here and let the night get quieter.",
            "tools_used": [],
            "tool_results": [],
            "quick_actions": [],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
        }

    if stage == "STAGE7_MUSIC":
        return {
            "response": "Here's a bit of momentum music. You earned it.",
            "tools_used": ["music_player"],
            "tool_results": [
                {
                    "title": "Momentum music",
                    "url": "https://www.youtube.com/watch?v=cF1Na4AIecM",
                    "message": "Momentum music queued",
                }
            ],
            "quick_actions": [],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
            "render_options": {"suppress_celebrate": True},
        }

    if stage == "STAGE_CLEAR_NIGHT_OFFER":
        return {
            "response": "Your load has been sitting at 4 while sleep keeps sliding, so tonight looks cooked, not salvageable. This is the moment for a full reset, not one more guilty hour. Want me to clear the night for you?",
            "tools_used": [],
            "tool_results": [],
            "quick_actions": [
                _demo_action("Clear my night", "clear my night", "moon", "STAGE_CLEAR_NIGHT_EXECUTE", primary=True),
            ],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
        }

    if stage == "STAGE_CLEAR_NIGHT_EXECUTE":
        return {
            "response": "Done. Your night's yours. Get some sleep.",
            "tools_used": ["clear_the_night"],
            "tool_results": [execute_tool("clear_the_night", {})],
            "quick_actions": [],
            "mode": "SCRIPTED",
            "model": "demo-scripted",
            "render_options": {
                "tool_delay": 600,
                "celebrate_after_render": True,
                "suppress_celebrate": True,
            },
        }

    return _scripted_demo_response(user_message, "STAGE0_OPENING")


def run_agent(user_message: str, next_stage: str | None = None) -> dict[str, Any]:
    context_summary = get_context_summary()
    system_prompt = SYSTEM_PROMPT.format(context_summary=context_summary)
    if DEMO_MODE_SCRIPTED:
        print("MODE: SCRIPTED (demo stage machine)")
        result = _scripted_demo_response(user_message, next_stage)
        log_interaction(user_message, result["response"], result["tools_used"])
        return result

    shortcut = _shortcut_agentic_action(user_message)
    if shortcut is not None:
        log_interaction(user_message, shortcut["response"], shortcut["tools_used"])
        shortcut["mode"] = "LIVE" if os.getenv("ANTHROPIC_API_KEY") else "FALLBACK"
        shortcut["model"] = "nimbus-shortcut"
        return shortcut

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key or Anthropic is None:
        print("MODE: FALLBACK (offline mock)")
        result = _mock_response(user_message)
        log_interaction(user_message, result["response"], result["tools_used"])
        result["mode"] = "FALLBACK"
        result["model"] = "offline-mock"
        return result

    try:
        client = Anthropic(api_key=api_key)
        print("MODE: LIVE (Claude API)")
    except Exception:
        print("MODE: FALLBACK (offline mock)")
        result = _mock_response(user_message)
        log_interaction(user_message, result["response"], result["tools_used"])
        result["mode"] = "FALLBACK"
        result["model"] = "offline-mock"
        return result

    messages: list[dict[str, Any]] = [{"role": "user", "content": user_message}]
    tools_used: list[str] = []
    tool_results: list[Any] = []
    all_tools_used: list[str] = []
    quick_actions: list[dict[str, str]] = []

    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=240,
        system=system_prompt,
        tools=TOOL_DEFINITIONS,
        messages=messages,
    )

    while any(_is_tool_block(block) for block in response.content):
        assistant_content = [_content_block_to_dict(block) for block in response.content]
        messages.append({"role": "assistant", "content": assistant_content})

        tool_result_blocks = []
        for block in response.content:
            if not _is_tool_block(block):
                continue

            name = block.get("name") if isinstance(block, dict) else block.name
            tool_input = block.get("input") if isinstance(block, dict) else block.input
            tool_use_id = block.get("id") if isinstance(block, dict) else block.id

            result = execute_tool(name, tool_input)
            all_tools_used.append(name)
            if name == "suggest_quick_actions":
                quick_actions = result
            else:
                tools_used.append(name)
                tool_results.append(result)
                if isinstance(result, dict) and result.get("quick_actions"):
                    quick_actions = result["quick_actions"]
            tool_result_blocks.append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": json.dumps(result, ensure_ascii=True),
                }
            )

        messages.append({"role": "user", "content": tool_result_blocks})
        response = client.messages.create(
            model="claude-sonnet-4-5",
            max_tokens=900,
            system=system_prompt,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

    final_text = _truncate_response_text(_extract_text_from_content(response.content))
    if not final_text or len(final_text.split()) < 50:
        final_text = _fallback_response_text(user_message, tools_used)
    final_text = _truncate_response_text(final_text)
    if not quick_actions:
        quick_actions = _fallback_quick_actions(user_message)
    result = {
        "response": final_text,
        "tools_used": tools_used,
        "tool_results": tool_results,
        "quick_actions": quick_actions,
        "mode": "LIVE",
        "model": "claude-sonnet-4-5",
    }
    log_interaction(user_message, final_text, all_tools_used or tools_used)
    return result

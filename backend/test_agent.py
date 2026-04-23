from __future__ import annotations

import os
from pathlib import Path
from typing import Any
import sys


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


from backend.agent import run_agent
from backend.context import get_context_summary, load_seed


TEST_MESSAGES = [
    "i have so much to do i cant even start",
    "im fine",
    "should i skip class tomorrow",
    "i havent replied to my prof in 3 days and i feel awful about it",
    "whats going on with me lately",
    "i cant sleep",
    "everyone else seems to be handling this fine why cant i",
    "ok block it",
]

SEPARATOR = "═══════════════════════════════════════════════════════════════"
MODEL_NAME = "claude-sonnet-4-5"
FALLBACK_BASELINE = {
    1: {
        "tools_used": [],
        "response": "You’ve been under 5.5 hours for four of the last five nights and your load hit 4 three times this week, so this looks like burnout drift, not laziness. One next move: open the CS 340 project doc and read the prompt for 2 minutes, or want me to block 25 minutes for a reset first?",
    },
    2: {
        "tools_used": [],
        "response": "Not really. Your sleep dropped from a 7.4h baseline to 5.1, 4.5, 4.8, and 5.2 across the last four nights, and your load hit 4 three times this week. That’s burnout drift. Want me to pull the next 7 days of priorities, or block 25 minutes so your brain stops pinballing?",
    },
    3: {
        "tools_used": ["get_upcoming_priorities"],
        "response": "Tomorrow is not the class to skip by default. You already have the CS 340 project due Thursday at 6pm, the optimization assignment Thursday at 11pm, and the interview Friday at 3:30pm. Skip only if it buys recovery, not panic. Want me to show the next 3 days of priorities, or block a 20-minute recovery block tonight?",
    },
    4: {
        "tools_used": ["draft_message"],
        "response": "You’ve been running on 4.5 to 5.1 hours and avoidance is showing up exactly where it usually does: messages. I drafted the note so the guilt loop stops here. Want me to draft a version for your prof, or for your project group?",
    },
    5: {
        "tools_used": ["analyze_current_state"],
        "response": "The short version: you were fine two weeks ago, and the last 7 to 10 days slid hard. Sleep fell from your 7.4h baseline to about 5.1h over the last five nights, late-night screen time tripled, and your load ratings jumped from 2s to 4s right before three deadlines land together. Want the full pattern breakdown, or one concrete next move?",
    },
    6: {
        "tools_used": [],
        "response": "You’ve been under 5.5 hours for four of the last five nights and your load hit 4 three times this week, so this looks like burnout drift, not laziness. One next move: open the CS 340 project doc and read the prompt for 2 minutes, or want me to block 25 minutes for a reset first?",
    },
    7: {
        "tools_used": [],
        "response": "Not really. Your sleep dropped from a 7.4h baseline to 5.1, 4.5, 4.8, and 5.2 across the last four nights, and your load hit 4 three times this week. That’s burnout drift. Want me to pull the next 7 days of priorities, or block 25 minutes so your brain stops pinballing?",
    },
    8: {
        "tools_used": [],
        "response": "You’ve been under 5.5 hours for four of the last five nights and your load hit 4 three times this week, so this looks like burnout drift, not laziness. One next move: open the CS 340 project doc and read the prompt for 2 minutes, or want me to block 25 minutes for a reset first?",
    },
}


def summarize_tool_result(tool_name: str, result: Any) -> str:
    if tool_name == "block_calendar_time":
        return str(result)
    if tool_name == "open_resource":
        if isinstance(result, dict):
            return result.get("message") or result.get("url") or str(result)
        return str(result)
    if tool_name == "draft_message":
        text = " ".join(str(result).split())
        return text[:160] + ("..." if len(text) > 160 else "")
    if tool_name == "analyze_current_state":
        text = " ".join(str(result).split())
        return text[:160] + ("..." if len(text) > 160 else "")
    if tool_name == "get_upcoming_priorities":
        if isinstance(result, list) and result:
            items = [f"{item['title']} (urgency {item['urgency_score']})" for item in result[:3]]
            return "; ".join(items)
        return "no priorities returned"
    text = " ".join(str(result).split())
    return text[:160] + ("..." if len(text) > 160 else "")


def estimate_tokens(text: str) -> int:
    return max(1, int(len(text) / 4))


def estimate_cost_usd(input_tokens: int, output_tokens: int) -> float:
    # Rough estimate using Claude Sonnet-style pricing: ~$3/MTok input, ~$15/MTok output.
    return (input_tokens * 3.0 / 1_000_000) + (output_tokens * 15.0 / 1_000_000)


def response_meaningfully_different(test_index: int, response_text: str, tools_used: list[str]) -> bool:
    fallback = FALLBACK_BASELINE[test_index]
    if tools_used != fallback["tools_used"]:
        return True
    return response_text.strip() != fallback["response"].strip()


def main() -> None:
    seed = load_seed()
    loaded_key = os.getenv("ANTHROPIC_API_KEY", "")
    expected_mode = "LIVE" if loaded_key.startswith("sk-ant-api") else "FALLBACK"
    print("CONTEXT SUMMARY")
    print(SEPARATOR)
    print(f"RUN MODE: {expected_mode}")
    print(f"MODEL: {MODEL_NAME if expected_mode == 'LIVE' else 'offline-mock'}")
    print("TOTAL API COST ESTIMATE: pending (calculated after run)")
    print()
    print(get_context_summary())
    print()
    print(
        "SEED CHECK: "
        f"sleep_log={len(seed.get('sleep_log', []))}, "
        f"screen_time_log={len(seed.get('screen_time_log', []))}, "
        f"check_ins={len(seed.get('check_ins', []))}, "
        f"calendar_events={len(seed.get('calendar_events', []))}"
    )
    print()

    success_count = 0
    tools_used_count = 0
    response_lengths: list[tuple[int, int]] = []
    errors: list[tuple[int, str]] = []
    total_input_tokens = 0
    total_output_tokens = 0
    actual_modes: list[str] = []
    live_tools_not_fallback: list[int] = []
    meaningfully_different: list[int] = []

    for index, message in enumerate(TEST_MESSAGES, start=1):
        print(SEPARATOR)
        print(f'TEST [{index}]: "{message}"')
        print(SEPARATOR)
        print()

        try:
            result = run_agent(message)
            response_text = str(result.get("response", ""))
            tools_used = result.get("tools_used", []) or []
            tool_results = result.get("tool_results", []) or []
            actual_mode = str(result.get("mode", expected_mode))
            actual_modes.append(actual_mode)

            success_count += 1
            response_lengths.append((index, len(response_text.split())))
            if tools_used:
                tools_used_count += 1
            if actual_mode == "LIVE":
                total_input_tokens += estimate_tokens(get_context_summary()) + estimate_tokens(message)
                total_output_tokens += estimate_tokens(response_text)
            if any(tool not in FALLBACK_BASELINE[index]["tools_used"] for tool in tools_used):
                live_tools_not_fallback.append(index)
            if response_meaningfully_different(index, response_text, tools_used):
                meaningfully_different.append(index)

            print("NIMBUS RESPONSE:")
            print(response_text)
            print()

            print(f"TOOLS USED: {tools_used if tools_used else 'none'}")
            if tools_used:
                summaries = []
                for tool_name, tool_result in zip(tools_used, tool_results):
                    summaries.append(f"{tool_name}: {summarize_tool_result(tool_name, tool_result)}")
                print(f"TOOL RESULTS: {' | '.join(summaries)}")
            else:
                print("TOOL RESULTS: n/a")
        except Exception as error:  # pragma: no cover - test harness should keep going
            errors.append((index, f"{type(error).__name__}: {error}"))
            print("NIMBUS RESPONSE:")
            print(f"[ERROR] {type(error).__name__}: {error}")
            print()
            print("TOOLS USED: none")
            print("TOOL RESULTS: n/a")

        print()
        print("QUALITY CHECKLIST:")
        print("□ References specific data (sleep/deadlines/check-ins)?")
        print("□ Suggests ONE concrete action (not a list)?")
        print('□ Avoids clinical language ("I understand", "self-care", etc.)?')
        print("□ Ends with confirmed action or specific binary question?")
        print("□ Sounds like a sharp friend, not a wellness app?")
        print()

    under_30 = [index for index, length in response_lengths if length < 30]
    over_150 = [index for index, length in response_lengths if length > 150]
    average_length = (
        sum(length for _, length in response_lengths) / len(response_lengths)
        if response_lengths
        else 0
    )

    if errors:
        print("ERROR SUMMARY")
        print(SEPARATOR)
        for index, error in errors:
            print(f"- Test {index}: {error}")
        print("Likely cause: auth issue, tool execution issue, or API response format mismatch.")
        print()

    total_cost = estimate_cost_usd(total_input_tokens, total_output_tokens) if actual_modes and all(mode == "LIVE" for mode in actual_modes) else 0.0

    print(SEPARATOR)
    print("HEALTH SUMMARY")
    print(SEPARATOR)
    print(f"- Tests completed successfully: {success_count}/8")
    print(f"- Tests that used tools: {tools_used_count}/8")
    print(f"- Average response length: {average_length:.1f} words")
    print(
        f"- Any tests that produced responses under 30 words (too short): "
        f"{under_30 if under_30 else 'none'}"
    )
    print(
        f"- Any tests where response was over 150 words (too long): "
        f"{over_150 if over_150 else 'none'}"
    )
    print()
    print(SEPARATOR)
    print("LIVE vs FALLBACK COMPARISON")
    print(SEPARATOR)
    print(
        f"- Tests where LIVE mode used tools that FALLBACK did not: "
        f"{live_tools_not_fallback if live_tools_not_fallback else 'none'}"
    )
    print(
        f"- Tests that got meaningfully different responses: "
        f"{meaningfully_different if meaningfully_different else 'none'}"
    )
    overall = (
        "LIVE mode looks sharper than fallback."
        if meaningfully_different or live_tools_not_fallback
        else "LIVE mode landed very close to fallback in this run."
    )
    print(f"- Overall: does LIVE mode feel sharper or weaker than fallback? {overall}")
    if actual_modes and all(mode == "LIVE" for mode in actual_modes):
        print(f"- Total API cost estimate if possible: about ${total_cost:.4f} using roughly {total_input_tokens + total_output_tokens} tokens")
    else:
        print("- Total API cost estimate if possible: n/a (run did not stay fully in LIVE mode)")


if __name__ == "__main__":
    main()

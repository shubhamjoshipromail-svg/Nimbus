from backend.agent import run_agent


TEST_MESSAGES = [
    "i have so much to do i cant even start",
    "im fine",
    "should i skip class tomorrow",
    "i havent replied to my prof in 3 days and i feel awful about it",
    "whats going on with me lately",
]


def main() -> None:
    for index, message in enumerate(TEST_MESSAGES, start=1):
        result = run_agent(message)
        print(f"\n=== Test {index} ===")
        print(f"User: {message}")
        print(f"Response: {result['response']}")
        print(f"Tools used: {result['tools_used']}")
        print(f"Tool results: {result['tool_results']}")


if __name__ == "__main__":
    main()

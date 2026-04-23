# Nimbus

Nimbus is a local AI companion prototype for student burnout.

The current build is centered on one idea: an assistant should not feel like a dashboard, a chatbot, or a wellness worksheet. It should feel like a tiny companion that notices patterns, reacts to real context, and helps a student take the smallest useful next action.

This project currently follows Maya, a third-year Computer Science student drifting toward burnout across a realistic 14-day dataset. Nimbus reads that context, surfaces what matters, and responds with practical support like prioritization, simulated calendar blocking, in-app breathing guidance, and draft messages.

## What Nimbus Does Today

- Local FastAPI backend with a simple HTML/CSS/JS frontend
- Context-aware agent responses grounded in `data/seed.json`
- Rich seed data for Maya:
  - sleep
  - screen time
  - daily load check-ins
  - calendar events
  - stress signal summary
- Stress-aware tool layer:
  - `analyze_current_state`
  - `get_upcoming_priorities`
  - `block_calendar_time` (simulated)
  - `open_resource`
  - `draft_message`
  - `suggest_quick_actions`
  - `start_breathing_exercise`
  - `execute_care_plan`
  - `clear_the_night`
- Animated companion UI:
  - balloon avatar
  - breathing / blinking / floating states
  - tool cards
  - quick actions
  - in-app breathing exercise
- Native-feeling launch mode via small Chrome app window

## Current Experience

Nimbus currently supports:

- Opening as a floating assistant balloon in app mode
- Expanding into a full side-panel conversation UI
- Natural opening check-in instead of an immediate dashboard dump
- Context-grounded conversations like:
  - "i have so much to do i cant even start"
  - "i can't sleep"
  - "whats going on with me lately"
- Agentic support moments like:
  - breathing resets
  - focus sprints
  - clearing the night
  - drafting an extension email
  - queuing music/resources

## Stack

- Backend: Python, FastAPI
- Frontend: vanilla HTML, CSS, JavaScript
- Model: Anthropic Claude Sonnet 4.5
- Storage: JSON files only
- Launchers: shell / batch scripts for app-style presentation

## Project Structure

```text
nimbus-demo/
├── backend/
│   ├── agent.py
│   ├── context.py
│   ├── main.py
│   ├── requirements.txt
│   └── tools.py
├── data/
│   └── seed.json
├── frontend/
│   ├── app.js
│   ├── index.html
│   └── style.css
├── launch_nimbus.bat
├── launch_nimbus.sh
└── README.md
```

## Running It Locally

### 1. Install dependencies

```bash
cd /Users/shubhamjoshi/Desktop/Pava/nimbus-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Add your Anthropic key

Create a root `.env` file:

```env
ANTHROPIC_API_KEY=sk-ant-api...
```

### 3. Start the app

Standard dev mode:

```bash
uvicorn backend.main:app --reload --port 8000
```

Then open:

- [http://localhost:8000](http://localhost:8000)

### 4. Launch the native-feeling demo shell

macOS / Linux:

```bash
./launch_nimbus.sh
```

Windows:

```bat
launch_nimbus.bat
```

## API Endpoints

- `GET /health`
- `GET /context`
- `POST /chat`
- `/` serves the frontend

## Present Functionality

### Agent behavior

- Reads structured student context before every response
- References actual sleep, load, and deadline patterns
- Uses tools when action is more useful than advice
- Supports normal live/fallback operation instead of a forced scripted backbone

### Companion interactions

- Quick action chips under replies
- Tool result cards before text
- Gentle typing animation
- Companion state changes:
  - idle
  - listening
  - thinking
  - talking
  - caring
  - celebrating
  - sleeping

### Demo helpers

- Floating app-mode launcher
- Expand/collapse assistant shell
- Small-window balloon mode
- Rich README and test harnesses for iterative demos

## Known Limits

- No real database yet
- Calendar actions are simulated
- Email sending is simulated
- Notifications are simulated
- Voice is hinted in UI, not fully integrated
- GitHub publishing is not wired from inside the app itself

## What We’re Working On Next

This is meant to stay active as an ongoing project, not a frozen hackathon snapshot.

Near-term roadmap:

- real calendar integration
- real email send / draft sync
- persistent conversation memory
- better follow-up logic after actions complete
- real voice input + speech output
- mobile shell / desktop wrapper
- multiple student profiles instead of one seed persona
- proactive nudges based on changing risk signals
- richer semester timeline, not just a short 14-day window
- better admin/debug panel for inspecting context and tool traces

Longer-term ideas:

- campus-specific support resources
- LMS / syllabus ingestion
- deadline clustering detection across multiple classes
- burnout risk trend tracking over time
- check-in loops that feel helpful instead of nagging
- multi-agent support: planner, triage, and recovery modes

## Why This Project Exists

Most student productivity tools assume the student is already organized enough to use them.

Nimbus is trying to do the opposite:

- notice the pattern first
- lower the activation energy
- act like a practical companion
- keep the interface emotionally lightweight

The goal is not to produce more advice.

The goal is to make the next useful action feel obvious and doable.

## Demo Notes

If you are showing this live:

- launch in app mode
- start with the collapsed balloon
- expand into chat
- use a natural overwhelmed prompt
- let Nimbus suggest a breathing reset
- move into priorities / extension / recovery flows from there

## Status

Active work in progress.

Nimbus is already strong as a demo and interaction prototype, and the next phase is making more of the agentic support real instead of simulated.

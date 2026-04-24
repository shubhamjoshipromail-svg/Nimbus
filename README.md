# Nimbus

Nimbus is an AI companion for student burnout.

Instead of acting like a dashboard or a generic chatbot, Nimbus tries to feel like a tiny on-screen companion that notices when a week is tilting in the wrong direction and helps a student take one useful next step.

The current prototype follows Maya, a third-year Computer Science student drifting toward burnout across a realistic 14-day dataset. Nimbus reads that context, notices the patterns that matter, and responds with practical support like prioritization, in-app breathing guidance, recovery flows, and drafted messages.

## Live Demo

- Live app: [https://nimbus-web-production.up.railway.app](https://nimbus-web-production.up.railway.app)
- GitHub repo: [Nimbus](https://github.com/shubhamjoshipromail-svg/Nimbus)

## What Nimbus Feels Like

- A small floating balloon companion instead of a full browser app
- A warm chat-first interface instead of a productivity dashboard
- Context-grounded support instead of generic wellness advice
- Agentic moments like blocking time, drafting outreach, opening resources, and guiding a breathing reset inside the app

## Current Capabilities

### Context and reasoning

- Reads structured student context before every reply
- Grounds responses in actual sleep, load, screen-time, and deadline patterns
- Uses Maya's recent stress drift as the reference point for decisions
- Supports live Claude responses with tool use

### Agent tools

- `analyze_current_state`
- `get_upcoming_priorities`
- `block_calendar_time` (simulated)
- `open_resource`
- `draft_message`
- `suggest_quick_actions`
- `start_breathing_exercise`
- `execute_care_plan`
- `clear_the_night`

### Frontend experience

- Floating balloon avatar with breathing, blinking, bobbing, and caring states
- Expandable assistant shell with chat, tool cards, and quick actions
- In-app breathing exercise instead of kicking users out to a video
- Native-feeling Chrome app mode for demo presentation

## Example Moments

Nimbus currently handles prompts like:

- `i have so much to do i cant even start`
- `i can't sleep`
- `whats going on with me lately`
- `i havent replied to my prof in 3 days`

And can respond with flows like:

- a breathing reset before planning
- a focus sprint with music and time blocking
- a full "clear the night" recovery sequence
- a drafted extension email when the schedule is no longer realistic

## Stack

- Backend: Python + FastAPI
- Frontend: vanilla HTML, CSS, JavaScript
- Model: Anthropic Claude Sonnet 4.5
- Seed data: JSON
- Interaction persistence: PostgreSQL when `DATABASE_URL` is present
- Deployment: Railway
- Demo shell: Chrome app mode via launcher scripts

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
├── Dockerfile
├── launch_nimbus.bat
├── launch_nimbus.sh
├── railway.json
└── README.md
```

## Run Locally

### 1. Install dependencies

```bash
cd /Users/shubhamjoshi/Desktop/Pava/nimbus-demo
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

### 2. Add environment variables

Create a root `.env` file:

```env
ANTHROPIC_API_KEY=sk-ant-api...
DATABASE_URL=postgresql://user:password@host:5432/dbname
```

`DATABASE_URL` is optional locally. If omitted, Nimbus falls back to JSON-backed interaction logging.

### 3. Start the dev server

```bash
uvicorn backend.main:app --reload --port 8000
```

Open:

- [http://localhost:8000](http://localhost:8000)

### 4. Launch the native-feeling shell

macOS / Linux:

```bash
./launch_nimbus.sh
```

Windows:

```bat
launch_nimbus.bat
```

Launch app mode against the live Railway deployment:

```bash
./launch_nimbus.sh https://nimbus-web-production.up.railway.app
```

## Deploying To Railway

Nimbus is now configured to deploy cleanly on Railway with a Docker-based runtime.

### Recommended Railway setup

- 1 web service from this GitHub repo
- 1 PostgreSQL service in the same Railway project
- `ANTHROPIC_API_KEY` set in the web service
- `DATABASE_URL` pointed at the Railway Postgres service

### Why Postgres is worth using

The seed persona still lives in `data/seed.json`, which is perfect for demo context.

But cloud-hosted interaction history should not depend on local file writes. With `DATABASE_URL` set, Nimbus:

- keeps Maya's seed state in JSON
- stores new interactions in PostgreSQL
- reads recent interaction history back from PostgreSQL automatically

### Railway config in this repo

This repo includes:

- `Dockerfile`
- `railway.json`
- `.python-version`

The live Railway service uses:

- Docker-based Python runtime
- `GET /health` as the healthcheck
- FastAPI serving both backend and frontend from one service

### Manual Railway steps

1. Create a Railway project.
2. Add a web service from this repo.
3. Add PostgreSQL.
4. Set service variables:
   - `ANTHROPIC_API_KEY=...`
   - `DATABASE_URL=${{Postgres.DATABASE_URL}}`
5. Deploy.
6. Generate a Railway domain.
7. Verify:
   - `/health` returns `200`
   - `/` loads the app
   - `/chat` responds successfully

## API Endpoints

- `GET /health`
- `GET /context`
- `POST /chat`
- `/` serves the frontend

## Present Functionality

### Agent behavior

- Context-first responses grounded in actual student state
- Tool use when action is more useful than advice
- Recovery-aware flows like breathing, rest, and clearing the night
- Quick actions under replies for low-friction follow-up

### Interface behavior

- Balloon avatar with stateful animation
- Tool cards before text for a more visual interaction rhythm
- Type-in assistant responses
- App-mode launcher for a native-feeling demo surface

### Demo-friendly details

- Works in normal browser mode and in Chrome app mode
- Can launch locally or against a deployed Railway URL
- Preserves the small-balloon -> expanded-panel interaction in app mode

## Known Limits

- Seed persona is still single-user and JSON-based
- Calendar integration is simulated
- Email sending is simulated
- Notifications are simulated
- Voice is hinted in the UI, not fully implemented
- Most agentic actions are still demo-grade rather than production-integrated

## Roadmap

### Near term

- real calendar integration
- real email send / draft sync
- deeper persistent conversation memory
- full migration from JSON-only state to database-backed user state
- better post-action follow-up logic
- real voice input and speech output
- multiple student profiles instead of one seed persona

### Longer term

- syllabus or LMS ingestion
- richer deadline-cluster detection
- longer-term burnout trend tracking
- campus-specific support resources
- planner / triage / recovery mode orchestration

## Why This Project Exists

Most student productivity tools assume the student is already organized enough to use them well.

Nimbus is trying to do the opposite:

- notice the pattern first
- reduce the activation energy
- feel emotionally lightweight
- make the next useful action feel obvious

The goal is not to generate more advice.

The goal is to make support feel timely, practical, and human.

## Demo Notes

If you are showing Nimbus live:

- launch it in app mode
- start from the floating balloon
- open with a natural overwhelmed prompt
- let Nimbus guide one reset before planning
- use the priorities, extension, or recovery flows from there

## Status

Active work in progress.

Nimbus is already strong as a prototype for interaction design and agentic support. The next phase is making more of the helpful behavior real, durable, and integrated into actual student workflows.

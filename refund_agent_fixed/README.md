# Autonomous Refund & Chargeback Recovery Agent

## Important security note
Never upload `.env` or paste API keys into chat, screenshots, GitHub, or ZIP files. If a key was exposed, revoke it and create a replacement.

## Setup (Ubuntu / WSL)

```bash
cd ~/LG-Project
source .venv/bin/activate
pip install -r requirements.txt
```

Create/update `.env` in the project root (do not share it):

```env
OPENROUTER_API_KEY=YOUR_NEW_KEY
OPENROUTER_MODEL=openrouter/free
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
EMAIL_MODE=simulation
DATABASE_PATH=data/refund_cases.db
CHECKPOINT_DATABASE_PATH=data/refund_checkpoints.sqlite
MAX_UPLOAD_SIZE_MB=10
```

`openrouter/free` is a model router. Image extraction requires the selected free model to support vision/image input. If the chosen model cannot process images, select a vision-capable model available in your OpenRouter account and put its exact model slug in `OPENROUTER_MODEL`.

## Run

Terminal 1:

```bash
cd ~/LG-Project
source .venv/bin/activate
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Terminal 2:

```bash
cd ~/LG-Project
source .venv/bin/activate
streamlit run app/ui.py --server.address 0.0.0.0
```

Open `http://localhost:8501` (UI) and `http://localhost:8000/docs` (API docs).

## What the workflow does

1. Uploads a JPG/PNG/WEBP screenshot to FastAPI.
2. Runs LangGraph evidence extraction and evidence audit.
3. Runs the deterministic TAT engine for the configured UPI cases.
4. Drafts a grievance email only when the configured eligibility checks pass.
5. Pauses before dispatch for explicit human approval.
6. On approval, prints a **simulation only**. It does not send an email.

Unknown domestic status or unknown customer-attributable failure is treated conservatively and does not produce an automatic compensation claim. E-commerce returns are not automatically assessed under the UPI TAT rule.

The TAT values and compensation settings in `app/rules/tat_engine.py` are the project's configured assumptions and should be independently checked against current official rules before making real-world claims. This project is a prototype, not legal or financial advice.

## Tests

```bash
pytest -q app/tests
```

## Existing data

The app database and LangGraph checkpoint database are kept separately. Existing `data/` files are not included in the source ZIP; preserve your local data folder when applying source updates.

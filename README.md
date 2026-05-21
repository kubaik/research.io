# 🏥 HealthAssist CDST

**AI-Powered Clinical Decision Support Tool for Community Health Workers**  
_EVAH-Aligned · J-PAL Pathway A/B Ready · GitHub Pages Deployable_

---

## What This Is

HealthAssist CDST is a production-ready, static-site AI chatbot built to assist community health workers (CHWs) at primary health centres in Sub-Saharan Africa. It is architecturally aligned with the **EVAH initiative** (Evidence for AI in Health — J-PAL, APHRC, Wellcome Trust / Gates Foundation / Novo Nordisk Foundation).

The tool provides:

- **IMCI-aligned triage guidance** for children under 5
- **MUAC malnutrition screening** with SAM/MAM thresholds
- **Malaria RDT protocol** with severe malaria recognition
- **Safe Motherhood** red flag identification
- **Referral decision support** with urgency classification
- **Emergency safety detection** — automatic alert on life-threatening keyword detection
- **Built-in evaluation instrumentation** — per-response accuracy ratings, confidence scoring, session export for EVAH Pathway A/B data collection

---

## Architecture

```
config.yaml  +  GitHub Secrets (API keys)
       ↓
chatbot_system.py auto
       ↓  Python bakes token + config into JS at build time
_site/index.html           ← Clinical CHW interface
_site/static/js/chat.js    ← AI call logic (Anthropic-first)
_site/static/css/chat.css  ← Clinical UI design
_site/static/data/protocols.json  ← Offline protocol reference
_site/config.json          ← Public config (no secrets)
       ↓
GitHub Pages → live CDST URL
```

---

## Project Structure

```
health-cdst/
├── chatbot_system.py        ← Now just ~50 lines: logging setup + CLI
└── cdst/
    ├── __init__.py          ← Package marker
    ├── constants.py         ← PROTOCOL_VERSION, ROOT, CONFIG_FILE
    ├── config.py            ← AppConfig (defaults + YAML load/save)
    ├── context.py           ← BuildContext (output dir, hash, provider resolution)
    ├── verifier.py          ← ProviderVerifier (API key discovery + logging)
    ├── protocols.py         ← ProtocolsData (IMCI, MUAC, Malaria, Maternal, Newborn)
    ├── static_writer.py     ← StaticFileWriter (CSS, SW, manifest, JSON data files)
    ├── js_writer.py         ← JavaScriptWriter (generates chat.js)
    ├── html_writer.py       ← HtmlWriter (generates index.html)
    ├── output_verifier.py   ← OutputVerifier (post-build sanity check)
    └── builder.py           ← CDSTBuilder (orchestrates init/build/auto/verify)
```

---

## Provider Priority

Set **at least one** in **Repo → Settings → Secrets → Actions**:

| Secret Name         | Provider             | Model                    | Notes                                     |
| ------------------- | -------------------- | ------------------------ | ----------------------------------------- |
| `ANTHROPIC_API_KEY` | Anthropic Claude ⭐  | claude-sonnet-4-20250514 | **Recommended** — best clinical reasoning |
| `OPENAI_API_KEY`    | OpenAI               | gpt-4o                   | Strong alternative                        |
| `GIT_TOKEN`         | GitHub Models        | gpt-4o                   | Free tier via GitHub                      |
| `GROQ_API_KEY`      | Groq / Llama 3.3 70B | llama-3.3-70b-versatile  | Very fast, free tier                      |
| `MISTRAL_API_KEY`   | Mistral AI           | mistral-small-latest     | Fallback                                  |

The builder uses the **first key that is set**. Set multiple for redundancy; only the first active one is used per build.

**Why Claude is recommended for clinical use:** Claude claude-sonnet-4-20250514 has strong performance on structured clinical reasoning, follows safety instructions reliably, and supports the `anthropic-dangerous-direct-browser-access` header needed for direct browser calls without a proxy.

---

## EVAH Alignment

### Pathway A (Deployment Evaluation)

HealthAssist CDST is designed to support **Pathway A** evaluations — real-world assessment of how AI tools perform in practice:

- **Usability**: Clean CHW-optimised interface, quick replies, protocol sidebar
- **Workflow integration**: Input bar, emergency button, offline protocol reference
- **Adoption**: Greeting, contextual quick replies, simple interaction model
- **Safety**: Automatic emergency keyword detection, mandatory red flag flagging in AI responses
- **Data collection**: Per-message accuracy ratings (✓ Accurate / ✗ Inaccurate / ⬆ Review), confidence scoring, session export as structured JSON

### Pathway B (Impact Evaluation)

For Pathway B (scale evaluation), extend with:

- Backend session logging (replace client-side EVAL log with server POST)
- Randomisation arm assignment
- Health outcome linkage fields (facility ID, patient ID hash)
- Follow-up reminder integration

### Session Export Format

Each exported JSON includes:

```json
{
  "studyId": "EVAH-CDST-001",
  "sessionId": "uuid",
  "exportedAt": "ISO timestamp",
  "summary": {
    "totalBotMessages": 12,
    "accurateRatings": 9,
    "inaccurateRatings": 1,
    "escalations": 2,
    "emergencyAlerts": 1
  },
  "conversationHistory": [...],
  "evalLog": [...]
}
```

---

## Local Development

```bash
# Install deps
pip install -r requirements.txt

# First time setup
python chatbot_system.py init

# Build (uses any API keys set in shell)
export ANTHROPIC_API_KEY=sk-ant-...
python chatbot_system.py build

# Verify output
python chatbot_system.py verify

# Open in browser
open docs/index.html
```

No API key set → demo mode with IMCI-accurate canned clinical responses (safe for UI/UX testing and training).

---

## Commands

| Command                           | What it does                               |
| --------------------------------- | ------------------------------------------ |
| `python chatbot_system.py init`   | Write `config.yaml` from clinical defaults |
| `python chatbot_system.py verify` | Log which API keys are available           |
| `python chatbot_system.py build`  | Build `docs/` from config + env            |
| `python chatbot_system.py auto`   | `init` → `build` → verify output           |

---

## Customising for Your Facility

Edit `config.yaml`:

```yaml
app:
  name: "Kenyatta National Hospital CDST"
  region: "Nairobi, Kenya"
  facility_type: "District Hospital"

bot:
  system_prompt: |
    You are a CDST for Kenyatta National Hospital...
    [Add facility-specific protocols, formulary, contact numbers]

evaluation:
  study_id: "EVAH-KNH-2026-001"
  pathway: "B"
```

Push → Actions rebuilds → live in ~60 seconds.

---

## Multi-Facility Deployment

```
github.com/your-org/
  ├── cdst-facility-nairobi/     → nairobi.github.io/cdst
  ├── cdst-facility-mombasa/     → mombasa.github.io/cdst
  └── cdst-facility-kisumu/      → kisumu.github.io/cdst
```

Each repo: edit `config.yaml` (facility name, protocols, study ID) + one API key secret.

---

## Safety & Ethics Notes

- This tool **assists** clinical decision-making — it does not replace it
- All responses are flagged with confidence levels (HIGH/MEDIUM/LOW)
- Emergency keyword detection triggers visual alerts and protocol guidance
- Demo mode provides accurate IMCI/WHO-aligned responses for training
- No patient health information (PHI) is transmitted or stored — all evaluation data is session-local and exported manually
- Designed for deployment in low-bandwidth environments (static site, minimal JS)

---

## Built With

- Python 3.11 (build system)
- Vanilla JS (no framework dependencies — fast, low-bandwidth friendly)
- IBM Plex Sans/Mono (Google Fonts — clinical, accessible)
- GitHub Actions + Pages (CI/CD)
- Anthropic Claude claude-sonnet-4-20250514 (primary AI provider)

---

_HealthAssist CDST is an open evaluation tool. All session data exported supports the EVAH initiative's goal of generating rigorous, locally-led evidence on AI in health for LMICs._

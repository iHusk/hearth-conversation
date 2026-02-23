# Hearth Conversation

A Home Assistant custom integration that connects HA's voice pipeline to an [OpenClaw](https://github.com/openclaw) gateway. Speak to your Voice PE, get responses from Ora.

## How It Works

```
Voice PE (wake word + audio)
  → HA STT (Whisper / Nabu Casa Cloud)
    → Hearth Conversation (text → OpenClaw API → text)
  → HA TTS (Piper / Nabu Casa Cloud)
→ Voice PE speaker
```

The integration implements a standard HA conversation agent. It sends transcribed text to your OpenClaw gateway's OpenAI-compatible API and returns the response for TTS.

## Installation

### HACS (Recommended)

1. Open HACS in Home Assistant
2. Click the three dots menu → **Custom repositories**
3. Add `https://github.com/thayes/hearth-conversation` as an **Integration**
4. Search for "Hearth Conversation" and install
5. Restart Home Assistant

### Manual

Copy `custom_components/hearth_conversation/` to your HA's `custom_components/` directory and restart.

## Setup

1. **Settings → Devices & Services → Add Integration → Hearth Conversation**
2. Enter your gateway URL (e.g. `https://clawd.example.com`)
3. Enter the API key / bearer token
4. Choose the agent ID (default: `main`)
5. **Settings → Voice Assistants** → select the new conversation agent

## Options

After setup, click **Configure** on the integration to adjust:

| Option | Default | Description |
|--------|---------|-------------|
| System prompt | Voice-optimized | Instructions prepended to every request |
| Timeout | 30s | How long to wait for a response |
| Max history | 10 | Number of recent messages for context |

## Architecture

- Uses `aiohttp` directly — no external Python dependencies beyond what HA bundles
- System prompt is voice-optimized: short, natural sentences, no markdown
- OpenClaw handles its own context (memory, skills, tools) — we only send recent chat turns
- Error messages are spoken-friendly ("I can't reach my brain right now")

## Development

```bash
# Run tests
pip install pytest pytest-asyncio aiohttp
pytest tests/ -v
```

## License

MIT

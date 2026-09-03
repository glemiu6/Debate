# Agent-vs-Agent Debate Simulator

Two local LLM personas debate an absurd topic in a retro typewriter-style
terminal, with an optional moderator who throws in twists and a judge who
delivers a final verdict.

## Setup

1. Install [Ollama](https://ollama.com) and pull a model:
   ```bash
   ollama pull llama3.1:8b
   ollama serve   # if not already running as a background service
   ```

2. Install dependencies:
   ```bash
   pip install requests pyyaml
   ```

## Run it

```bash
python main.py --topic "Is a hot dog a sandwich?" --a socrates --b detective_noir.yaml
```

See available personas:
```bash
python main.py --list-personas
```

Other flags:
```bash
python main.py --topic "Cats vs dogs" --a skeptic --b romantic \
  --rounds 6 --model qwen2.5:14b --no-moderator
```

- `--rounds N` — number of rounds (each round = both agents speak once). Default 4.
- `--model` — any Ollama model tag you've pulled. Default `llama3.1:8b`.
- `--no-moderator` — skip the moderator's mid-debate twists.
- `--no-judge` — skip the final verdict.

## Posting to IRC

The debate can post live into an IRC channel instead of (or alongside)
the terminal. This uses a small stdlib-only IRC client — no extra
dependencies.

```bash
python main.py --topic "Cats vs dogs" --a skeptic --b romantic \
  --irc-server irc.libera.chat --irc-channel "#your-test-channel" \
  --irc-nick DebateBot
```

Flags:
- `--irc-server` — hostname, e.g. `irc.libera.chat`. Required to enable IRC.
- `--irc-port` — default `6667`. Use `6697` with `--irc-ssl`.
- `--irc-channel` — default `#debate-sim`.
- `--irc-nick` — default `DebateBot`.
- `--irc-ssl` — connect over TLS (recommended for public networks).
- `--irc-password` — server password (`PASS`), if the network requires one.
- `--no-terminal` — suppress local output and only post to IRC.

Notes:
- IRC has no per-character typewriter animation — turns are posted as
  complete lines. Personas still get distinct colors via mIRC color codes
  (`\x03NN`), which most clients render.
- Long replies are automatically split into ~400-character `PRIVMSG`
  chunks with a short delay between them, both to stay under IRC's
  ~512-byte line limit and to avoid tripping flood protection.
- Test against a real network with a throwaway channel first — public
  networks like Libera.Chat have nick registration and flood-control
  policies, and some require nick registration via NickServ before you
  can join certain channels.
- This was validated locally against a mock IRC server (registration,
  PING/PONG keepalive, JOIN, message chunking, QUIT all confirmed
  working) but hasn't been run against a real IRC network — flood
  limits and edge cases vary by server, so treat `--irc-*` as a working
  starting point rather than battle-tested.

## Files

- `main.py` — CLI entry point and the turn-taking orchestrator loop.
- `personas/` — one YAML file per persona, plus `_config.yaml` for the
  shared moderator/judge prompts. See "Editing personas" below.
- `persona_loader.py` — loads and validates a personas folder (bundled
  `./personas` by default, or a custom one via `--personas-dir`).
- `ollama_client.py` — thin wrapper around `POST /api/chat` on a local
  Ollama server.
- `render.py` — retro terminal rendering: typewriter effect, ANSI colors,
  speaker labels. No dependencies beyond stdlib — swap in `rich` or
  `textual` later if you want a fancier split-pane layout.
- `irc_bridge.py` — minimal stdlib IRC client (connection registration,
  PING/PONG keepalive, JOIN, message chunking, mIRC color codes).

## Editing personas

Each persona is its own file in `personas/`. The filename (minus
`.yaml`) is the key you pass to `--a`/`--b`. Every persona file needs
`name`, `color` (one of `green`, `yellow`, `cyan`, `magenta`, `white`,
`dim`, `red`), and `system_prompt`:

```yaml
# personas/pirate.yaml
name: Captain Rustbeard
color: red
system_prompt: |
  You are a grizzled pirate captain who argues entirely in nautical
  metaphors. Max 2 sentences per turn. Never break character.
```

Drop that file in `personas/` and it's immediately usable:
`python main.py --topic "..." --a pirate --b socrates`

`personas/_config.yaml` holds the shared `moderator_prompt` and
`judge_prompt` (not a persona — the leading underscore keeps it out of
the persona list). Every folder passed to `--personas-dir` needs one.

To use a whole separate roster without touching the bundled folder
(e.g. to share a themed set with someone else, or keep an experimental
persona out of your main lineup), point at your own directory instead:

```bash
python main.py --personas-dir my_personas/ --topic "..." --a pirate --b robot
```

`persona_loader.py` validates on load and fails with a specific,
file-pointing error — missing field, bad color, missing `_config.yaml`,
empty folder, duplicate persona key — rather than a raw traceback.

## Requirements

```
pip install requests pyyaml
```

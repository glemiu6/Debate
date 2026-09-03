"""
Agent-vs-Agent Debate Simulator

Usage:
    python main.py --topic "Is a hot dog a sandwich?" --a socrates --b detective_noir.yaml
    python main.py --topic "Cats vs dogs" --a skeptic --b romantic --rounds 6
    python main.py --list-personas

Requires a local Ollama server running with at least one pulled model
(default: llama3.1:8b — change with --model).
"""

import argparse
import difflib
import sys

from ollama_client import call_model
from persona_loader import load_personas
from render import typewriter, speaker_line, moderator_line, banner, thinking_indicator, clear_line
from irc import IRCBridge, irc_color


def build_prompt(persona_name: str, opponent_name: str, topic: str, transcript: list[dict]) -> list[dict]:
    """Turn the shared transcript into a message list from this agent's POV."""
    history_lines = [f"[{turn['speaker']}]: {turn['text']}" for turn in transcript]
    history_text = "\n".join(history_lines) if history_lines else "(debate has not started yet)"
    user_content = (
        f"Debate topic: {topic}\n"
        f"You are debating against {opponent_name}.\n\n"
        f"Transcript so far:\n{history_text}\n\n"
        f"Give your next turn now."
    )
    return [{"role": "user", "content": user_content}]


def is_repetitive(transcript: list[dict], speaker: str, threshold: float = 0.75) -> bool:
    """Check this speaker's last two turns for near-duplicate content."""
    own_turns = [t["text"] for t in transcript if t["speaker"] == speaker]
    if len(own_turns) < 2:
        return False
    ratio = difflib.SequenceMatcher(None, own_turns[-1], own_turns[-2]).ratio()
    return ratio > threshold


def emit(speaker: str, text: str, color_name: str, terminal: bool, irc: "IRCBridge | None"):
    """Send one turn to whichever outputs are active."""
    if terminal:
        speaker_line(speaker, color_name)
        typewriter(text, color_name)
    if irc:
        irc.send_message(f"{irc_color(speaker, color_name)}: {text}")


def run_debate(topic: str, persona_a_key: str, persona_b_key: str, rounds: int,
                model: str, use_moderator: bool, use_judge: bool,
                personas: dict, moderator_prompt: str, judge_prompt: str,
                terminal: bool = True, irc: "IRCBridge | None" = None):
    persona_a = personas[persona_a_key]
    persona_b = personas[persona_b_key]
    transcript = []

    if terminal:
        banner(topic)
    if irc:
        irc.send_message(f"=== DEBATE TOPIC: {topic} ===")

    stop_early = False
    for round_num in range(1, rounds + 1):
        for persona, opponent in [(persona_a, persona_b), (persona_b, persona_a)]:
            if terminal:
                thinking_indicator(persona["name"])
            try:
                messages = build_prompt(persona["name"], opponent["name"], topic, transcript)
                reply = call_model(model, persona["system_prompt"], messages)
            except RuntimeError as e:
                if terminal:
                    clear_line()
                print(f"\nError calling model: {e}")
                sys.exit(1)
            if terminal:
                clear_line()
            emit(persona["name"], reply, persona["color"], terminal, irc)
            transcript.append({"speaker": persona["name"], "text": reply})

            if is_repetitive(transcript, persona["name"]):
                msg = f"{persona['name']} seems to be repeating themselves. Ending debate early."
                if terminal:
                    moderator_line(msg)
                if irc:
                    irc.send_message(f"*** {msg} ***")
                stop_early = True
                break

        if stop_early:
            break

        if use_moderator and round_num < rounds and round_num % 2 == 0:
            if terminal:
                thinking_indicator("Moderator")
            mod_line = call_model(model, moderator_prompt,
                                   [{"role": "user", "content":
                                     f"Debate topic: {topic}\nWe're {round_num} rounds in. "
                                     f"Interject with a twist."}])
            if terminal:
                clear_line()
                moderator_line(mod_line)
            if irc:
                irc.send_message(f"*** Moderator: {mod_line} ***")
            transcript.append({"speaker": "Moderator", "text": mod_line})

    if use_judge:
        judge_intro = "The debate has concluded. Calling the Judge..."
        if terminal:
            moderator_line(judge_intro)
        if irc:
            irc.send_message(f"*** {judge_intro} ***")
        history_text = "\n".join(f"[{t['speaker']}]: {t['text']}" for t in transcript)
        verdict = call_model(model, judge_prompt,
                              [{"role": "user", "content": f"Topic: {topic}\n\nTranscript:\n{history_text}"}])
        emit("Judge", verdict, "white", terminal, irc)


def main():
    parser = argparse.ArgumentParser(description="Agent-vs-Agent Debate Simulator")
    parser.add_argument("--topic", type=str, help="Debate topic")
    parser.add_argument("--a", type=str, default="socrates", help="Persona key for agent A")
    parser.add_argument("--b", type=str, default="detective_noir.yaml", help="Persona key for agent B")
    parser.add_argument("--rounds", type=int, default=4, help="Number of rounds (each round = both agents speak once)")
    parser.add_argument("--model", type=str, default="llama3.1:8b", help="Ollama model name")
    parser.add_argument("--no-moderator", action="store_true", help="Disable moderator interjections")
    parser.add_argument("--no-judge", action="store_true", help="Disable final judge verdict")
    parser.add_argument("--list-personas", action="store_true", help="List available personas and exit")
    parser.add_argument("--irc-server", type=str, help="IRC server hostname, e.g. irc.libera.chat")
    parser.add_argument("--irc-port", type=int, default=6667, help="IRC server port (default 6667, use 6697 with --irc-ssl)")
    parser.add_argument("--irc-channel", type=str, default="#debate-sim", help="IRC channel to post to")
    parser.add_argument("--irc-nick", type=str, default="DebateBot", help="Nickname to register on IRC")
    parser.add_argument("--irc-ssl", action="store_true", help="Use TLS to connect to the IRC server")
    parser.add_argument("--irc-password", type=str, default=None, help="Server password (PASS), if required")
    parser.add_argument("--no-terminal", action="store_true", help="Suppress local terminal output (IRC only)")
    parser.add_argument("--personas-dir", type=str, default=None,
                         help="Path to a custom personas folder (default: bundled ./personas)")
    args = parser.parse_args()
    if args.personas_dir:
        try:
            personas, moderator_prompt, judge_prompt = load_personas(args.personas_dir)
        except ValueError as e:
            parser.error(str(e))

    if args.list_personas:
        print("Available personas:")
        for key, p in personas.items():
            print(f"  {key:12s} -> {p['name']}")
        return

    if not args.topic:
        parser.error("--topic is required (or use --list-personas)")

    if args.a not in personas or args.b not in personas:
        parser.error(f"Unknown persona. Choose from: {', '.join(personas.keys())}")

    if args.no_terminal and not args.irc_server:
        parser.error("--no-terminal requires --irc-server (otherwise there's no output at all)")

    irc = None
    if args.irc_server:
        irc = IRCBridge(
            server=args.irc_server,
            port=args.irc_port,
            nick=args.irc_nick,
            channel=args.irc_channel,
            use_ssl=args.irc_ssl,
            password=args.irc_password,
        )
        print(f"Connecting to {args.irc_server}:{args.irc_port} as {args.irc_nick}...")
        try:
            irc.connect()
        except (RuntimeError, OSError) as e:
            print(f"Failed to connect to IRC: {e}")
            sys.exit(1)
        print(f"Connected. Posting to {irc.channel}.")

    try:
        run_debate(
            topic=args.topic,
            persona_a_key=args.a,
            persona_b_key=args.b,
            rounds=args.rounds,
            model=args.model,
            use_moderator=not args.no_moderator,
            use_judge=not args.no_judge,
            personas=personas,
            moderator_prompt=moderator_prompt,
            judge_prompt=judge_prompt,
            terminal=not args.no_terminal,
            irc=irc,
        )
    finally:
        if irc:
            irc.close()


if __name__ == "__main__":
    main()
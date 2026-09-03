import os
import yaml
from pathlib import Path
import sys

VALID_COLORS = {"green", "yellow", "cyan", "magenta", "white", "dim", "red"}
REQUIRED_PERSONA_KEYS = {"name", "color", "system_prompt"}

DEFAULT_PERSONAS_DIR = Path(__file__).parent / "personas"
CONFIG_FILENAME = "_config.yaml"


def _load_yaml_file(path: Path) -> dict:
    with open(path,"r",encoding="utf-8") as f:
        try:
            data = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise ValueError(f"Could not load yaml file {path} : {exc}")

    if not isinstance(data, dict):
        raise ValueError(f"Invalid yaml file {path}. Must contain mapping (key: values). Got {type(data).__name__} ")
    return data


def load_personas(directory: Path|str|None = None):

    directory = Path(directory) if directory else DEFAULT_PERSONAS_DIR

    if not directory.exists():
        raise ValueError(f"Directory {directory} does not exist")
    if not directory.is_dir():
        raise ValueError(f"Directory {directory} is not a directory")

    yaml_files = sorted(directory.glob("*.yaml")) + sorted(directory.glob("*.yml"))
    if not yaml_files:
        raise ValueError(f"No yaml files found in {directory}")

    config_path = directory / CONFIG_FILENAME
    if not config_path.exists():
        raise ValueError(f"Config file {config_path} does not exist")

    config = _load_yaml_file(config_path)

    moderator_prompt = str(config.get("moderator_prompt","")).strip()
    judge_prompt = str(config.get("judge_prompt","")).strip()

    if not moderator_prompt:
        raise ValueError(f"Moderator prompt not found in {config_path}")
    if not judge_prompt:
        raise ValueError(f"Judge prompt not found in {config_path}")

    personas = {}

    for path in yaml_files:
        if path.name.startswith("_"):
            continue

        key = path.stem.lower().replace(" ","_").replace("-","_")
        persona = _load_yaml_file(path)

        missing = REQUIRED_PERSONA_KEYS - persona.keys()
        if missing:
            raise ValueError(f"Missing required keys {', '.join(missing)}")
        if persona["color"] not in VALID_COLORS:
            raise ValueError(
                f"{path}: color '{persona['color']}' is invalid, "
                f"must be one of {', '.join(sorted(VALID_COLORS))}"
            )

        if not str(persona["system_prompt"]).strip():
            raise ValueError(f"{path}: system_prompt is empty.")
        if key in personas:
            raise ValueError(
                f"{path}: persona key '{key}' collides with another file "
                f"(filenames are lowercased and must be unique)."
            )
        personas[key] = persona

    if not personas:
        raise ValueError(f"{directory} has no persona files (only {CONFIG_FILENAME} or none at all).")

    return personas,moderator_prompt,judge_prompt


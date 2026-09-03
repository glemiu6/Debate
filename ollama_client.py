import requests

OLLAMA_URL = "http://localhost:11434/api/chat"


def call_model(model:str,system_prompt:str,messages:list[dict],temp:float = 0.9):
    payload = {
        "model": model,
        "messages":[{"role": "system", "content": system_prompt}] + messages,
        "stream":False,
        "options":{
            "temperature":temp,
        },
    }

    try:
        resp = requests.post(OLLAMA_URL, json=payload,timeout=120)
        resp.raise_for_status()
        data=resp.json()
        return data["message"]["content"].strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Couldn't reach ollama at {OLLAMA_URL}. Try `ollama serve`")

    except (KeyError, ValueError) as e:
        raise RuntimeError("Unexpected error in calling ollama")
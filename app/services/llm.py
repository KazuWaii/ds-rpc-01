import os

import ollama
from dotenv import load_dotenv
from groq import Groq

from dataclasses import dataclass


@dataclass
class ChatResult:
    content: str
    prompt_tokens: int
    completion_tokens: int

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama")
OLLAMA_MODEL = "llama3.2"
GROQ_MODEL = "openai/gpt-oss-20b"

_groq_client = Groq(api_key=os.getenv("GROQ_API_KEY")) if LLM_PROVIDER == "groq" else None


def chat(messages):
    if LLM_PROVIDER == "groq":
        response = _groq_client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
        )
        return ChatResult(
            content=response.choices[0].message.content,
            prompt_tokens=response.usage.prompt_tokens,
            completion_tokens=response.usage.completion_tokens,
        )
    else:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        return ChatResult(
            content=response["message"]["content"],
            prompt_tokens=response.get("prompt_eval_count", 0),
            completion_tokens=response.get("eval_count", 0),
        )
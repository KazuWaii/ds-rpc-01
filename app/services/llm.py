import os

import ollama
from dotenv import load_dotenv
from groq import Groq

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
        return response.choices[0].message.content
    else:
        response = ollama.chat(model=OLLAMA_MODEL, messages=messages)
        return response["message"]["content"]
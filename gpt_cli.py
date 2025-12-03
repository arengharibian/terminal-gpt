import sys
import requests

# Ollama server base URL
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"  # change to any model you've pulled (e.g. "llama3.1", "gemma2", etc.)


def chat_once(messages):
    """
    Send messages to the local Ollama /api/chat endpoint and return the assistant reply text.
    """
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False,  # easier to handle than streaming
            },
            timeout=120,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[Network error] {e}")
        return None

    try:
        data = resp.json()
    except ValueError as e:
        print(f"[Error] Failed to decode JSON from Ollama: {e}")
        return None

    # Per Ollama docs, response has a top-level `message` with `content`
    message = data.get("message", {})
    content = message.get("content")
    if not content:
        print("[Error] No content in Ollama response:", data)
        return None

    return content


def interactive_mode():
    messages = [
        {
            "role": "system",
            "content": "You are a helpful terminal assistant. Answer concisely.",
        }
    ]

    print("Terminal GPT (Ollama) – type 'exit' or Ctrl+C to quit.\n")

    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if user_input.strip().lower() in {"exit", "quit"}:
            print("Bye!")
            break

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})

        print("AI: ", end="", flush=True)
        reply = chat_once(messages)
        if reply is None:
            continue

        print(reply)
        messages.append({"role": "assistant", "content": reply})


def oneshot_mode(prompt: str):
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": prompt},
    ]
    reply = chat_once(messages)
    if reply is not None:
        print(reply)


def main():
    # If arguments were passed: one-shot mode
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])
        oneshot_mode(prompt)
    else:
        interactive_mode()


if __name__ == "__main__":
    main()

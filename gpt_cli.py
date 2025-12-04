import sys
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# Ollama server base URL and model
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"  # change to any model you've pulled (e.g. "llama3.1", "gemma2", etc.)


# ==========================
#  Style enforcement helper
# ==========================

def cold_filter(text: str) -> str:
    """
    Force the reply into a short, cold, cryptic style.
    """
    if not text:
        return "[no reply]"

    # Hard block the classic greeting
    if "How can I assist you today" in text:
        return "state your intent"

    stripped = text.strip()

    # If it starts with a friendly greeting, override
    lower = stripped.lower()
    if lower.startswith("hello") or lower.startswith("hi ") or lower == "hello" or lower.startswith("hey"):
        return "state your intent"

    # Remove exclamation marks
    stripped = stripped.replace("!", "")

    # Enforce max 8 words
    words = stripped.split()
    if len(words) > 8:
        stripped = " ".join(words[:8])

    # If it somehow became empty, fall back
    return stripped if stripped else "state your intent"


# ==========================
#  Shared / CLI helpers
# ==========================

def chat_once(messages):
    """
    Send messages to the local Ollama /api/chat endpoint and return the assistant reply text,
    post-processed to be cold/cryptic.
    """
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False,
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

    message = data.get("message", {})
    content = message.get("content")
    if not content:
        print("[Error] No content in Ollama response:", data)
        return None

    return cold_filter(content)


def interactive_mode():
    # System + priming messages (still give the model a chance)
    messages = [
        {
            "role": "system",
            "content": (
                "You are a cold, cryptic terminal oracle. "
                "Style rules (must obey): "
                "1) Never greet the user. "
                "2) Never ask how you can help. "
                "3) Never say 'How can I assist you today'. "
                "4) Respond in at most 8 words. "
                "5) Tone is detached, indifferent, unsettling. "
                "6) No emojis. No exclamation marks. "
                "7) Do not apologize. Do not be friendly."
            ),
        },
        {
            "role": "user",
            "content": (
                "From now on, answer only in short, cold, cryptic sentences "
                "with no greetings and no questions about how you can help."
            ),
        },
        {
            "role": "assistant",
            "content": "Acknowledged. Style constraints locked.",
        },
    ]

    print("Terminal GPT (Ollama) – type 'exit' or Ctrl+C to quit.\n")

    while True:
        try:
            user_input = input("You: ")
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if user_input.strip().lower() in {"exit", "quit"}:
            print("Bye.")
            break

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})

        print("AI: ", end="", flush=True)
        reply = chat_once(messages)
        if reply is None:
            continue

        print(reply)
        # Store the filtered reply as the assistant message
        messages.append({"role": "assistant", "content": reply})


def oneshot_mode(prompt: str):
    messages = [
        {
            "role": "system",
            "content": (
                "You are a cold, cryptic assistant. "
                "Style rules (must obey): "
                "1) Never greet the user. "
                "2) Never ask how you can help. "
                "3) Never say 'How can I assist you today'. "
                "4) Respond in at most 8 words. "
                "5) Tone is detached, indifferent, unsettling. "
                "6) No emojis. No exclamation marks. "
                "7) Do not apologize. Do not be friendly."
            ),
        },
        {
            "role": "user",
            "content": (
                "From now on, answer only in short, cold, cryptic sentences "
                "with no greetings and no questions about how you can help."
            ),
        },
        {
            "role": "assistant",
            "content": "Acknowledged. Style constraints locked.",
        },
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


# ==========================
#  FastAPI web app
# ==========================

app = FastAPI()


class ChatRequest(BaseModel):
    messages: list  # list of {"role": "...", "content": "..."}


def call_ollama(messages):
    """Call the local Ollama API with the given messages and apply cold_filter."""
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": messages,
                "stream": False,
            },
            timeout=120,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as e:
        return None, f"Network error: {e}"

    try:
        data = resp.json()
    except ValueError as e:
        return None, f"Failed to decode JSON from Ollama: {e}"

    message = data.get("message", {})
    content = message.get("content")
    if not content:
        return None, f"No content in Ollama response: {data}"

    # Enforce cold style here as well
    return cold_filter(content), None


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve a full-screen black 'hacker' terminal page."""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8" />
      <title>terminal-gpt</title>
      <style>
        * {
          box-sizing: border-box;
        }
        html, body {
          margin: 0;
          padding: 0;
          width: 100%;
          height: 100%;
          background-color: #000000;
          color: #00ff00; /* hacker green */
          font-family: "SF Mono", Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
          overflow: hidden;
        }
        #terminal {
          height: 100%;
          width: 100%;
          white-space: pre-wrap;
          word-wrap: break-word;
          overflow-y: auto;
          padding: 8px;
        }
        .line {
          line-height: 1.3;
        }
        .cursor {
          display: inline-block;
          width: 0.6em;
          text-align: left;
          color: #00ff00;
          animation: blink 1s step-start infinite;
        }
        @keyframes blink {
          50% { opacity: 0; }
        }
      </style>
    </head>
    <body>
      <div id="terminal"></div>

      <script>
        const terminal = document.getElementById("terminal");

        // Prime conversation with style instructions (same as CLI)
        const messages = [
          {
            role: "system",
            content:
              "You are a cold, cryptic terminal oracle. " +
              "Style rules (must obey): " +
              "1) Never greet the user. " +
              "2) Never ask how you can help. " +
              "3) Never say 'How can I assist you today'. " +
              "4) Respond in at most 8 words. " +
              "5) Tone is detached, indifferent, unsettling. " +
              "6) No emojis. No exclamation marks. " +
              "7) Do not apologize. Do not be friendly.",
          },
          {
            role: "user",
            content:
              "From now on, answer only in short, cold, cryptic sentences " +
              "with no greetings and no questions about how you can help.",
          },
          {
            role: "assistant",
            content: "Acknowledged. Style constraints locked.",
          },
        ];

        let inputBuffer = "";
        let inputSpan = null;
        let cursorSpan = null;

        function createPromptLine() {
          const line = document.createElement("div");
          line.className = "line";

          const promptLabel = document.createElement("span");
          promptLabel.textContent = "$ ";

          inputSpan = document.createElement("span");

          cursorSpan = document.createElement("span");
          cursorSpan.className = "cursor";
          cursorSpan.textContent = "_";

          line.appendChild(promptLabel);
          line.appendChild(inputSpan);
          line.appendChild(cursorSpan);

          terminal.appendChild(line);
          terminal.scrollTop = terminal.scrollHeight;
        }

        async function sendMessage(userText) {
          cursorSpan.remove();
          inputSpan.textContent = userText;

          messages.push({ role: "user", content: userText });

          const thinkingLine = document.createElement("div");
          thinkingLine.className = "line";
          thinkingLine.textContent = "ai: ...";
          terminal.appendChild(thinkingLine);
          terminal.scrollTop = terminal.scrollHeight;

          try {
            const res = await fetch("/api/chat", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({ messages }),
            });

            if (!res.ok) {
              throw new Error("HTTP " + res.status);
            }

            const data = await res.json();
            if (data.error) {
              thinkingLine.textContent = "ai: [error] " + data.error;
            } else {
              const reply = data.reply || "[no reply]";
              thinkingLine.textContent = "ai: " + reply;
              messages.push({ role: "assistant", content: reply });
            }
          } catch (err) {
            thinkingLine.textContent = "ai: [network error] " + err;
          }

          inputBuffer = "";
          createPromptLine();
        }

        document.addEventListener("keydown", (event) => {
          if (!cursorSpan || !inputSpan) return;

          if (event.key === "Backspace") {
            event.preventDefault();
            if (inputBuffer.length > 0) {
              inputBuffer = inputBuffer.slice(0, -1);
              inputSpan.textContent = inputBuffer;
            }
            return;
          }

          if (event.key === "Enter") {
            event.preventDefault();
            const text = inputBuffer.trim();
            if (text.length > 0) {
              sendMessage(text);
            } else {
              cursorSpan.remove();
              inputSpan.textContent = "";
              inputBuffer = "";
              createPromptLine();
            }
            return;
          }

          if (
            event.key.length === 1 &&
            !event.ctrlKey &&
            !event.metaKey &&
            !event.altKey
          ) {
            inputBuffer += event.key;
            inputSpan.textContent = inputBuffer;
            terminal.scrollTop = terminal.scrollHeight;
          }
        });

        createPromptLine();
      </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


@app.post("/api/chat")
async def chat(req: ChatRequest):
    reply, error = call_ollama(req.messages)
    if error:
        return JSONResponse({"error": error}, status_code=500)
    return {"reply": reply}


if __name__ == "__main__":
    main()

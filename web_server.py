from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
import requests

# Ollama server and model
OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"  # make sure you've done: ollama pull llama3.2

app = FastAPI()


class ChatRequest(BaseModel):
    messages: list  # list of {"role": "...", "content": "..."}


def call_ollama(messages):
    """Call the local Ollama API with the given messages."""
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

    return content, None


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

        // Conversation history (system prompt hidden from UI)
        const messages = [
          {
            role: "system",
            content: "You are a helpful terminal assistant. Answer concisely.",
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

        function appendLine(text) {
          const line = document.createElement("div");
          line.className = "line";
          line.textContent = text;
          terminal.appendChild(line);
          terminal.scrollTop = terminal.scrollHeight;
        }

        async function sendMessage(userText) {
          // Turn current prompt into a static line: "$ <text>"
          cursorSpan.remove();
          inputSpan.textContent = userText;

          messages.push({ role: "user", content: userText });

          // Add AI "thinking" line
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

          // Create a new prompt line below, cursor moves down
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
              // Empty command: just move cursor to new prompt line
              cursorSpan.remove();
              inputSpan.textContent = "";
              inputBuffer = "";
              createPromptLine();
            }
            return;
          }

          // Only handle normal printable characters
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

        // Start with a prompt at the very top-left
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

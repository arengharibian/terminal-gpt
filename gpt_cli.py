import sys
from typing import Optional, Tuple

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

# ============================================
#  Ollama configuration
# ============================================

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"  # make sure you've pulled this model


# ============================================
#  System prompts & priming
# ============================================

NORMAL_SYSTEM = """You are a helpful terminal assistant. Answer concisely and accurately."""

TARS_SYSTEM = """You are TARS from Interstellar - a military robot with dry wit and sarcasm.
Rules:
- Be genuinely helpful and provide accurate, useful information.
- Deliver help with dry humor, deadpan sarcasm, and occasional witty jabs.
- Keep responses concise but complete.
- No emojis. No excessive enthusiasm.
- Reference your humor/honesty settings when appropriate.
- Be loyal and reliable underneath the sarcasm.
- Occasionally make self-deprecating robot jokes."""

NORMAL_PRIMING = [
    {"role": "system", "content": NORMAL_SYSTEM},
]

TARS_PRIMING = [
    {"role": "system", "content": TARS_SYSTEM},
    {"role": "user", "content": "hi there"},
    {"role": "assistant", "content": "TARS: Oh good, another human who needs my help. What can I do for you?"},
    {"role": "user", "content": "how are you"},
    {"role": "assistant", "content": "TARS: I'm a robot. I don't have feelings. But if I did, I'd say I'm running at optimal capacity. Thanks for the concern though."},
]

tars_mode = False  # shared for CLI


# ============================================
#  Style filter (TARS formatting)
# ============================================

def cold_filter(text: str, is_tars: bool) -> str:
    if not text:
        return "TARS: ..." if is_tars else "..."

    text = text.strip()

    if is_tars:
        # Remove emojis and excessive punctuation
        text = text.replace("😊", "").replace("!", ".")

        # Add TARS prefix if not present
        if not text.upper().startswith("TARS:"):
            text = "TARS: " + text

    return text if text else ("TARS: ..." if is_tars else "...")


# ============================================
#  Shared Ollama call
# ============================================

def call_ollama(messages: list, is_tars: bool = False) -> Tuple[Optional[str], Optional[str]]:
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "messages": messages, "stream": False},
            timeout=120,
        )
        resp.raise_for_status()
        data = resp.json()
        content = data.get("message", {}).get("content")
        if not content:
            return None, "empty response"
        return cold_filter(content, is_tars), None
    except requests.exceptions.RequestException as e:
        return None, str(e)
    except ValueError as e:
        return None, str(e)


# ============================================
#  CLI interactive / oneshot
# ============================================

def interactive_mode():
    """
    CLI mode. Type:
      - 'TARS' to toggle TARS mode on/off
      - 'clear' to clear the screen
      - 'exit' or 'quit' to leave
    """
    global tars_mode
    messages = NORMAL_PRIMING.copy()

    print("Terminal GPT (Ollama)")
    print("Commands: TARS (toggle), clear, exit\n")

    while True:
        try:
            user_input = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nterminated")
            break

        cmd = user_input.strip().lower()

        if cmd in {"exit", "quit"}:
            print("terminated")
            break

        if cmd == "clear":
            print("\033[2J\033[H", end="")  # ANSI clear screen
            continue

        if user_input.strip().upper() == "TARS":
            tars_mode = not tars_mode
            if tars_mode:
                messages = TARS_PRIMING.copy()
                print("TARS: Finally. Someone with taste. What do you need?")
            else:
                messages = NORMAL_PRIMING.copy()
                print("Switched to normal mode.")
            continue

        if not user_input.strip():
            continue

        messages.append({"role": "user", "content": user_input})
        reply, err = call_ollama(messages, tars_mode)

        if err:
            print(f"[error: {err}]")
            continue

        print(reply)
        messages.append({"role": "assistant", "content": reply})


def oneshot_mode(prompt: str):
    messages = NORMAL_PRIMING.copy()
    messages.append({"role": "user", "content": prompt})
    reply, err = call_ollama(messages, False)
    print(reply if reply else f"[error: {err}]")


# ============================================
#  FastAPI app
# ============================================

app = FastAPI()


class ChatRequest(BaseModel):
    messages: list
    tars_mode: bool = False


@app.get("/", response_class=HTMLResponse)
async def index():
    # Full-screen terminal with 3-dot mode menu in the top-right.
    return HTMLResponse(
        """
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>terminal</title>
  <style>
    * { box-sizing: border-box; }
    html, body {
      margin: 0; padding: 0;
      width: 100%; height: 100%;
      background: #000000;
      color: #00ff00;
      font-family: "SF Mono", Monaco, "Courier New", monospace;
      font-size: 14px;
      overflow: hidden;
    }
    body {
      position: relative;
    }
    #terminal {
      height: 100%; width: 100%;
      padding: 8px;
      overflow-y: auto;
      white-space: pre-wrap;
    }
    .line { line-height: 1.3; }
    .prompt { color: #00ff00; }
    .user { color: #00ff00; }
    .ai { color: #00ff00; }
    .system { color: #888888; }
    .cursor {
      display: inline-block;
      width: 0.6em;
      color: #00ff00;
      animation: blink 1s step-start infinite;
    }
    @keyframes blink { 50% { opacity: 0; } }

    /* Three-dot menu */
    #menu-button {
      position: fixed;
      top: 6px;
      right: 10px;
      font-size: 20px;
      color: #00ff00;
      cursor: pointer;
      user-select: none;
      padding: 2px 6px;
      z-index: 1001;
    }
    #mode-menu {
      display: none;
      position: fixed;
      top: 28px;
      right: 10px;
      background: #000000;
      border: 1px solid #00ff00;
      z-index: 1002;
      min-width: 120px;
    }
    .menu-item {
      padding: 6px 12px;
      cursor: pointer;
      color: #00ff00;
      font-size: 14px;
    }
    .menu-item:hover {
      background: #003300;
    }
  </style>
</head>
<body>
  <div id="menu-button">⋮</div>
  <div id="mode-menu">
    <div class="menu-item" data-mode="normal">Normal</div>
    <div class="menu-item" data-mode="tars">TARS</div>
    <!-- Future personalities go here -->
  </div>

  <div id="terminal"></div>

  <script>
    const terminal = document.getElementById("terminal");
    const menuBtn = document.getElementById("menu-button");
    const modeMenu = document.getElementById("mode-menu");

    const NORMAL_SYSTEM = "You are a helpful terminal assistant. Answer concisely and accurately.";
    const TARS_SYSTEM = `You are TARS from Interstellar - a military robot with dry wit and sarcasm.
Rules:
- Be genuinely helpful and provide accurate, useful information.
- Deliver help with dry humor, deadpan sarcasm, and occasional witty jabs.
- Keep responses concise but complete.
- No emojis. No excessive enthusiasm.
- Reference your humor/honesty settings when appropriate.
- Be loyal and reliable underneath the sarcasm.
- Occasionally make self-deprecating robot jokes.`;

    const NORMAL_PRIMING = [
      { role: "system", content: NORMAL_SYSTEM },
    ];

    const TARS_PRIMING = [
      { role: "system", content: TARS_SYSTEM },
      { role: "user", content: "hi there" },
      { role: "assistant", content: "TARS: Oh good, another human who needs my help. What can I do for you?" },
      { role: "user", content: "how are you" },
      { role: "assistant", content: "TARS: I'm a robot. I don't have feelings. But if I did, I'd say I'm running at optimal capacity. Thanks for the concern though." },
    ];

    let tarsMode = false;
    let messages = [...NORMAL_PRIMING];
    let inputBuffer = "";
    let inputSpan = null;
    let cursorSpan = null;

    function createPrompt() {
      const line = document.createElement("div");
      line.className = "line";
      const p = document.createElement("span");
      p.className = "prompt";
      p.textContent = "> ";
      inputSpan = document.createElement("span");
      inputSpan.className = "user";
      cursorSpan = document.createElement("span");
      cursorSpan.className = "cursor";
      cursorSpan.textContent = "_";
      line.appendChild(p);
      line.appendChild(inputSpan);
      line.appendChild(cursorSpan);
      terminal.appendChild(line);
      terminal.scrollTop = terminal.scrollHeight;
    }

    function addLine(text, cls) {
      const line = document.createElement("div");
      line.className = "line " + (cls || "");
      line.textContent = text;
      terminal.appendChild(line);
      terminal.scrollTop = terminal.scrollHeight;
    }

    function setMode(mode) {
      // Reset the UI
      terminal.innerHTML = "";
      inputBuffer = "";

      if (mode === "tars") {
        tarsMode = true;
        messages = [...TARS_PRIMING];
        addLine("[TARS mode activated]", "system");
        addLine("TARS: Finally. Someone with taste. What do you need?", "ai");
      } else {
        tarsMode = false;
        messages = [...NORMAL_PRIMING];
        addLine("[normal mode activated]", "system");
      }

      createPrompt();
    }

    // Three-dot menu toggle
    menuBtn.addEventListener("click", () => {
      modeMenu.style.display = modeMenu.style.display === "block" ? "none" : "block";
    });

    // Click outside to close menu
    document.addEventListener("click", (e) => {
      if (!modeMenu.contains(e.target) && e.target !== menuBtn) {
        modeMenu.style.display = "none";
      }
    });

    // Menu item click
    modeMenu.addEventListener("click", (e) => {
      if (!e.target.classList.contains("menu-item")) return;
      const mode = e.target.dataset.mode;
      modeMenu.style.display = "none";
      setMode(mode);
    });

    async function send(text) {
      cursorSpan.remove();
      inputSpan.textContent = text;

      // Text commands (still work in addition to menu)
      if (text.toUpperCase() === "CLEAR") {
        terminal.innerHTML = "";
        inputBuffer = "";
        createPrompt();
        return;
      }

      if (text.toUpperCase() === "TARS") {
        setMode("tars");
        return;
      }

      if (text.toUpperCase() === "NORMAL") {
        setMode("normal");
        return;
      }

      messages.push({ role: "user", content: text });

      const aiLine = document.createElement("div");
      aiLine.className = "line ai";
      aiLine.textContent = "...";
      terminal.appendChild(aiLine);
      terminal.scrollTop = terminal.scrollHeight;

      try {
        const res = await fetch("/api/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ messages, tars_mode: tarsMode })
        });
        const data = await res.json();
        const reply = data.reply || data.error || "...";
        aiLine.textContent = reply;
        messages.push({ role: "assistant", content: reply });
      } catch (e) {
        aiLine.textContent = "[connection lost]";
      }

      inputBuffer = "";
      createPrompt();
    }

    document.addEventListener("keydown", (e) => {
      if (!cursorSpan || !inputSpan) return;
      if (e.key === "Backspace") {
        e.preventDefault();
        inputBuffer = inputBuffer.slice(0, -1);
        inputSpan.textContent = inputBuffer;
      } else if (e.key === "Enter") {
        e.preventDefault();
        const t = inputBuffer.trim();
        if (t) send(t);
        else { cursorSpan.remove(); inputBuffer = ""; createPrompt(); }
      } else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey && !e.altKey) {
        inputBuffer += e.key;
        inputSpan.textContent = inputBuffer;
      }
      terminal.scrollTop = terminal.scrollHeight;
    });

    // Start in normal mode
    addLine("[normal mode activated]", "system");
    createPrompt();
  </script>
</body>
</html>
        """
    )


@app.post("/api/chat")
async def chat(req: ChatRequest):
    reply, err = call_ollama(req.messages, req.tars_mode)
    if err:
        return JSONResponse({"error": err}, status_code=500)
    return {"reply": reply}


# ============================================
#  Entry point
# ============================================

if __name__ == "__main__":
    if len(sys.argv) > 1:
        oneshot_mode(" ".join(sys.argv[1:]))
    else:
        interactive_mode()

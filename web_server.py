import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, Tuple

# ============================================
#  Ollama configuration
# ============================================

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"  # ollama pull llama3.2


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


def cold_filter(text: str, is_tars: bool) -> str:
    """Post-process replies slightly. Frontend adds AI:/TARS: labels."""
    if not text:
        return "..."

    text = text.strip()

    if is_tars:
        text = text.replace("😊", "").replace("😄", "").replace("!", ".")

    return text or "..."


def call_ollama(messages: list, is_tars: bool = False) -> Tuple[Optional[str], Optional[str]]:
    """Call local Ollama and return (reply, error)."""
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
        return None, f"network error: {e}"
    except ValueError as e:
        return None, f"json decode error: {e}"


# ============================================
#  FastAPI app
# ============================================

app = FastAPI()


class ChatRequest(BaseModel):
    messages: list          # list of {"role": "...", "content": "..."}
    tars_mode: bool = False


@app.get("/", response_class=HTMLResponse)
async def index():
    # Full-screen terminal with three-dot mode menu
    return HTMLResponse(
        f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>terminal-gpt</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0; padding: 0;
      width: 100%; height: 100%;
      background: #000000;
      color: #00ff00;
      font-family: "SF Mono", Monaco, "Courier New", monospace;
      font-size: 14px;
      overflow: hidden;
    }}
    body {{
      position: relative;
    }}
    #terminal {{
      height: 100%; width: 100%;
      padding: 8px;
      overflow-y: auto;
      white-space: pre-wrap;
    }}
    .line {{ line-height: 1.3; }}
    .prompt {{ color: #00ff00; }}
    .user {{ color: #00ff00; }}
    .ai {{ color: #00ff00; }}
    .system {{ color: #888888; }}
    .cursor {{
      display: inline-block;
      width: 0.6em;
      color: #00ff00;
      animation: blink 1s step-start infinite;
    }}
    @keyframes blink {{ 50% {{ opacity: 0; }} }}

    /* Three-dot menu */
    #menu-button {{
      position: fixed;
      top: 6px;
      right: 10px;
      font-size: 20px;
      color: #00ff00;
      cursor: pointer;
      user-select: none;
      padding: 2px 6px;
      z-index: 1001;
    }}
    #mode-menu {{
      display: none;
      position: fixed;
      top: 28px;
      right: 10px;
      background: #000000;
      border: 1px solid #00ff00;
      z-index: 1002;
      min-width: 120px;
    }}
    .menu-item {{
      padding: 6px 12px;
      cursor: pointer;
      color: #00ff00;
      font-size: 14px;
    }}
    .menu-item:hover {{
      background: #003300;
    }}
  </style>
</head>
<body>
  <div id="menu-button">⋮</div>
  <div id="mode-menu">
    <div class="menu-item" data-mode="normal">Normal</div>
    <div class="menu-item" data-mode="tars">TARS</div>
  </div>

  <div id="terminal"></div>

  <script>
    const terminal = document.getElementById("terminal");
    const menuBtn = document.getElementById("menu-button");
    const modeMenu = document.getElementById("mode-menu");

    const NORMAL_SYSTEM = {NORMAL_SYSTEM!r};
    const TARS_SYSTEM = {TARS_SYSTEM!r};

    const NORMAL_PRIMING = [
      {{ role: "system", content: NORMAL_SYSTEM }},
    ];

    const TARS_PRIMING = [
      {{ role: "system", content: TARS_SYSTEM }},
      {{ role: "user", content: "hi there" }},
      {{ role: "assistant", content: "TARS: Oh good, another human who needs my help. What can I do for you?" }},
      {{ role: "user", content: "how are you" }},
      {{ role: "assistant", content: "TARS: I'm a robot. I don't have feelings. But if I did, I'd say I'm running at optimal capacity. Thanks for the concern though." }},
    ];

    let tarsMode = false;
    let messages = [...NORMAL_PRIMING];
    let inputBuffer = "";
    let inputSpan = null;
    let cursorSpan = null;

    function createPrompt() {{
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
    }}

    function addLine(text, cls) {{
      const line = document.createElement("div");
      line.className = "line " + (cls || "");
      line.textContent = text;
      terminal.appendChild(line);
      terminal.scrollTop = terminal.scrollHeight;
    }}

    function setMode(mode) {{
      terminal.innerHTML = "";
      inputBuffer = "";

      if (mode === "tars") {{
        tarsMode = true;
        messages = [...TARS_PRIMING];
        addLine("[TARS mode activated]", "system");
        addLine("TARS: Finally. Someone with taste. What do you need?", "ai");
      }} else {{
        tarsMode = false;
        messages = [...NORMAL_PRIMING];
        addLine("[normal mode activated]", "system");
      }}

      createPrompt();
    }}

    // menu open/close
    menuBtn.addEventListener("click", () => {{
      modeMenu.style.display = modeMenu.style.display === "block" ? "none" : "block";
    }});

    document.addEventListener("click", (e) => {{
      if (!modeMenu.contains(e.target) && e.target !== menuBtn) {{
        modeMenu.style.display = "none";
      }}
    }});

    modeMenu.addEventListener("click", (e) => {{
      if (!e.target.classList.contains("menu-item")) return;
      const mode = e.target.dataset.mode;
      modeMenu.style.display = "none";
      setMode(mode);
    }});

    async function send(text) {{
      cursorSpan.remove();
      inputSpan.textContent = text;

      const upper = text.toUpperCase();

      // text commands still work
      if (upper === "CLEAR") {{
        terminal.innerHTML = "";
        inputBuffer = "";
        addLine("[normal mode activated]", "system");
        messages = [...NORMAL_PRIMING];
        tarsMode = false;
        createPrompt();
        return;
      }}

      if (upper === "TARS") {{
        setMode("tars");
        return;
      }}

      if (upper === "NORMAL" || upper === "AI") {{
        setMode("normal");
        return;
      }}

      messages.push({{ role: "user", content: text }});

      const aiLine = document.createElement("div");
      aiLine.className = "line ai";
      aiLine.textContent = "...";
      terminal.appendChild(aiLine);
      terminal.scrollTop = terminal.scrollHeight;

      try {{
        const res = await fetch("/api/chat", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ messages, tars_mode: tarsMode }}),
        }});
        const data = await res.json();
        let reply = data.reply || data.error || "...";

        // Label as AI or TARS, avoid double TARS:
        const label = tarsMode ? "TARS: " : "AI: ";
        reply = reply.replace(/^TARS:\\s*/i, "");  // strip if model added it
        aiLine.textContent = label + reply;

        messages.push({{ role: "assistant", content: label + reply }});
      }} catch (e) {{
        aiLine.textContent = "[connection lost]";
      }}

      inputBuffer = "";
      createPrompt();
    }}

    document.addEventListener("keydown", (e) => {{
      if (!cursorSpan || !inputSpan) return;

      if (e.key === "Backspace") {{
        e.preventDefault();
        inputBuffer = inputBuffer.slice(0, -1);
        inputSpan.textContent = inputBuffer;
      }} else if (e.key === "Enter") {{
        e.preventDefault();
        const t = inputBuffer.trim();
        if (t) send(t);
        else {{
          cursorSpan.remove();
          inputBuffer = "";
          createPrompt();
        }}
      }} else if (
        e.key.length === 1 &&
        !e.ctrlKey &&
        !e.metaKey &&
        !e.altKey
      ) {{
        inputBuffer += e.key;
        inputSpan.textContent = inputBuffer;
      }}
      terminal.scrollTop = terminal.scrollHeight;
    }});

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=True)

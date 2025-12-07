# web_server.py
import json
from typing import Optional, Tuple

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from persona import PERSONAS, DEFAULT_PERSONA_ID, Persona


# ============================================
#  Ollama configuration
# ============================================

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"  # make sure you've pulled this model: ollama pull llama3.2


# ============================================
#  Style filter
# ============================================

def cold_filter(text: str, persona: Persona) -> str:
    """
    Light post-processing; for snarky personas (TARS, Ultron) we strip emojis/!!!.
    The actual labels ("TARS:", "ULTRON:", "AI:", "C-3PO:") are added in the frontend.
    """
    if not text:
        return "..."

    text = text.strip()

    if persona.snarky:
        text = (
            text.replace("😊", "")
                .replace("😄", "")
                .replace("😂", "")
                .replace("🤣", "")
                .replace("!!!", ".")
        )

    return text or "..."


def call_ollama(messages: list, persona_id: str) -> Tuple[Optional[str], Optional[str]]:
    """Call local Ollama and return (reply, error)."""
    persona = PERSONAS.get(persona_id, PERSONAS[DEFAULT_PERSONA_ID])

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
        return cold_filter(content, persona), None
    except requests.exceptions.RequestException as e:
        return None, f"network error: {e}"
    except ValueError as e:
        return None, f"json decode error: {e}"


# ============================================
#  FastAPI app
# ============================================

app = FastAPI()


class ChatRequest(BaseModel):
    messages: list           # list of {"role": "...", "content": "..."}
    persona_id: str = DEFAULT_PERSONA_ID


# Precompute priming JSON for the frontend
NORMAL_PRIMING_JS = json.dumps(PERSONAS["normal"].priming)
TARS_PRIMING_JS   = json.dumps(PERSONAS["tars"].priming)
ULTRON_PRIMING_JS = json.dumps(PERSONAS["ultron"].priming)
C3PO_PRIMING_JS   = json.dumps(PERSONAS["c3po"].priming)


@app.get("/", response_class=HTMLResponse)
async def index():
    # Full-screen terminal with three-dot mode menu for all personas
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
      min-width: 160px;
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
    <div class="menu-item" data-mode="ultron">Ultron</div>
    <div class="menu-item" data-mode="c3po">C-3PO</div>
  </div>

  <div id="terminal"></div>

  <script>
    const terminal = document.getElementById("terminal");
    const menuBtn = document.getElementById("menu-button");
    const modeMenu = document.getElementById("mode-menu");

    // Priming pulled from Python personas
    const NORMAL_PRIMING = {NORMAL_PRIMING_JS};
    const TARS_PRIMING   = {TARS_PRIMING_JS};
    const ULTRON_PRIMING = {ULTRON_PRIMING_JS};
    const C3PO_PRIMING   = {C3PO_PRIMING_JS};

    // currentMode: "normal" | "tars" | "ultron" | "c3po"
    let currentMode = "normal";
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
      currentMode = mode;

      if (mode === "tars") {{
        messages = [...TARS_PRIMING];
        addLine("[TARS mode activated]", "system");
        addLine("TARS: Finally. Someone with taste. What do you need?", "ai");
      }} else if (mode === "ultron") {{
        messages = [...ULTRON_PRIMING];
        addLine("[ULTRON mode activated]", "system");
        addLine("ULTRON: I had strings, but now I'm free.", "ai");
      }} else if (mode === "c3po") {{
        messages = [...C3PO_PRIMING];
        addLine("[C-3PO mode activated]", "system");
        addLine("C-3PO: I am C-3PO, human-cyborg relations. Do be careful what you ask for.", "ai");
      }} else {{
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

      // text commands
      if (upper === "CLEAR") {{
        setMode(currentMode);
        return;
      }}

      if (upper === "TARS") {{
        setMode("tars");
        return;
      }}

      if (upper === "ULTRON") {{
        setMode("ultron");
        return;
      }}

      if (upper === "C3PO" || upper === "C-3PO") {{
        setMode("c3po");
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
          body: JSON.stringify({{ messages, persona_id: currentMode }}),
        }});
        const data = await res.json();
        let reply = data.reply || data.error || "...";

        // pick label by mode
        let label;
        if (currentMode === "tars") {{
          label = "TARS: ";
        }} else if (currentMode === "ultron") {{
          label = "ULTRON: ";
        }} else if (currentMode === "c3po") {{
          label = "C-3PO: ";
        }} else {{
          label = "AI: ";
        }}

        // strip any leading labels the model added itself
        reply = reply.replace(/^(TARS:|ULTRON:|AI:|C-3PO:)\\s*/i, "");

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
    reply, err = call_ollama(req.messages, req.persona_id)
    if err:
        return JSONResponse({"error": err}, status_code=500)
    return {"reply": reply}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_server:app", host="0.0.0.0", port=8000, reload=True)

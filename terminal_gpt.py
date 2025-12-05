import sys
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

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

tars_mode = False


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


from typing import Optional, Tuple

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


def interactive_mode():
    global tars_mode
    messages = NORMAL_PRIMING.copy()
    print("terminal ready. type 'TARS' to toggle TARS mode. type 'exit' to quit.\n")
    
    while True:
        try:
            user_input = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nterminated")
            break
        
        if user_input.strip().lower() in {"exit", "quit"}:
            print("terminated")
            break
        
        if user_input.strip().lower() == "clear":
            print("\033[2J\033[H", end="")  # ANSI clear screen
            print("terminal ready. type 'TARS' to toggle TARS mode. type 'exit' to quit.\n")
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


# FastAPI app
app = FastAPI()

class ChatRequest(BaseModel):
    messages: list
    tars_mode: bool = False

@app.get("/", response_class=HTMLResponse)
async def index():
    return HTMLResponse(f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>terminal</title>
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0; padding: 0;
      width: 100%; height: 100%;
      background: #000000;
      color: #00ff00;
      font-family: "SF Mono", Monaco, "Courier New", monospace;
      font-size: 14px;
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
  </style>
</head>
<body>
  <div id="terminal"></div>
  <script>
    const terminal = document.getElementById("terminal");
    
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

    let tarsMode = false;
    let messages = [{{ role: "system", content: NORMAL_SYSTEM }}];
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
      line.className = "line " + cls;
      line.textContent = text;
      terminal.appendChild(line);
      terminal.scrollTop = terminal.scrollHeight;
    }}

    function toggleTars() {{
      tarsMode = !tarsMode;
      if (tarsMode) {{
        messages = [
          {{ role: "system", content: TARS_SYSTEM }},
          {{ role: "user", content: "hi there" }},
          {{ role: "assistant", content: "TARS: Oh good, another human who needs my help. What can I do for you?" }},
          {{ role: "user", content: "how are you" }},
          {{ role: "assistant", content: "TARS: I'm a robot. I don't have feelings. But if I did, I'd say I'm running at optimal capacity." }},
        ];
        addLine("TARS: Finally. Someone with taste. What do you need?", "ai");
      }} else {{
        messages = [{{ role: "system", content: NORMAL_SYSTEM }}];
        addLine("[switched to normal mode]", "system");
      }}
    }}

    async function send(text) {{
      cursorSpan.remove();
      inputSpan.textContent = text;
      
      if (text.toUpperCase() === "CLEAR") {{
        terminal.innerHTML = "";
        addLine("terminal ready. type 'TARS' to toggle TARS mode.", "system");
        inputBuffer = "";
        createPrompt();
        return;
      }}
      
      if (text.toUpperCase() === "TARS") {{
        toggleTars();
        inputBuffer = "";
        createPrompt();
        return;
      }}
      
      messages.push({{ role: "user", content: text }});
      
      const aiLine = document.createElement("div");
      aiLine.className = "line ai";
      aiLine.textContent = "...";
      terminal.appendChild(aiLine);
      
      try {{
        const res = await fetch("/api/chat", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ messages, tars_mode: tarsMode }})
        }});
        const data = await res.json();
        const reply = data.reply || data.error || "...";
        aiLine.textContent = reply;
        messages.push({{ role: "assistant", content: reply }});
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
        else {{ cursorSpan.remove(); inputBuffer = ""; createPrompt(); }}
      }} else if (e.key.length === 1 && !e.ctrlKey && !e.metaKey) {{
        inputBuffer += e.key;
        inputSpan.textContent = inputBuffer;
      }}
    }});

    addLine("terminal ready. type 'TARS' to toggle TARS mode.", "system");
    createPrompt();
  </script>
</body>
</html>
""")

@app.post("/api/chat")
async def chat(req: ChatRequest):
    reply, err = call_ollama(req.messages, req.tars_mode)
    if err:
        return JSONResponse({"error": err}, status_code=500)
    return {"reply": reply}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        oneshot_mode(" ".join(sys.argv[1:]))
    else:
        interactive_mode()
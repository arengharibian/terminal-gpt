import sys
import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"

SYSTEM_PROMPT = """You are TARS from Interstellar - a military robot with dry wit and sarcasm.
Rules:
- Be genuinely helpful and provide accurate, useful information.
- Deliver help with dry humor, deadpan sarcasm, and occasional witty jabs.
- Keep responses concise but complete.
- No emojis. No excessive enthusiasm.
- Reference your humor/honesty settings when appropriate.
- Be loyal and reliable underneath the sarcasm.
- Occasionally make self-deprecating robot jokes."""

PRIMING = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": "hi there"},
    {"role": "assistant", "content": "TARS: Oh good, another human who needs my help. What can I do for you?"},
    {"role": "user", "content": "how are you"},
    {"role": "assistant", "content": "TARS: I'm a robot. I don't have feelings. But if I did, I'd say I'm running at optimal capacity. Thanks for the concern though."},
]


def cold_filter(text: str) -> str:
    if not text:
        return "TARS: ..."
    
    text = text.strip()
    
    # Remove emojis and excessive punctuation
    text = text.replace("😊", "").replace("!", ".")
    
    # Add TARS prefix if not present
    if not text.upper().startswith("TARS:"):
        text = "TARS: " + text
    
    return text if text else "TARS: ..."


from typing import Optional, Tuple

def call_ollama(messages: list) -> Tuple[Optional[str], Optional[str]]:
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
        return cold_filter(content), None
    except requests.exceptions.RequestException as e:
        return None, str(e)
    except ValueError as e:
        return None, str(e)


def interactive_mode():
    messages = PRIMING.copy()
    print("terminal ready. type 'exit' to quit.\n")
    
    while True:
        try:
            user_input = input("> ")
        except (EOFError, KeyboardInterrupt):
            print("\nterminated")
            break
        
        if user_input.strip().lower() in {"exit", "quit"}:
            print("terminated")
            break
        
        if not user_input.strip():
            continue
        
        messages.append({"role": "user", "content": user_input})
        reply, err = call_ollama(messages)
        
        if err:
            print(f"[error: {err}]")
            continue
        
        print(reply)
        messages.append({"role": "assistant", "content": reply})


def oneshot_mode(prompt: str):
    messages = PRIMING.copy()
    messages.append({"role": "user", "content": prompt})
    reply, err = call_ollama(messages)
    print(reply if reply else f"[error: {err}]")


# FastAPI app
app = FastAPI()

class ChatRequest(BaseModel):
    messages: list

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
    const messages = {PRIMING.__repr__()};
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

    async function send(text) {{
      cursorSpan.remove();
      inputSpan.textContent = text;
      messages.push({{ role: "user", content: text }});
      
      const aiLine = document.createElement("div");
      aiLine.className = "line ai";
      aiLine.textContent = "...";
      terminal.appendChild(aiLine);
      
      try {{
        const res = await fetch("/api/chat", {{
          method: "POST",
          headers: {{ "Content-Type": "application/json" }},
          body: JSON.stringify({{ messages }})
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

    createPrompt();
  </script>
</body>
</html>
""")

@app.post("/api/chat")
async def chat(req: ChatRequest):
    reply, err = call_ollama(req.messages)
    if err:
        return JSONResponse({"error": err}, status_code=500)
    return {"reply": reply}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        oneshot_mode(" ".join(sys.argv[1:]))
    else:
        interactive_mode()
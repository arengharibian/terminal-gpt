 _____                   _             _            ____ ____ _____ 
|_   _|__ _ __ _ __ ___ (_)_ __   __ _| |          / ___|  _ \_   _|
  | |/ _ \ '__| '_ ` _ \| | '_ \ / _` | |  _____  | |  _| |_) || |  
  | |  __/ |  | | | | | | | | | | (_| | | |_____| | |_| |  __/ | |  
  |_|\___|_|  |_| |_| |_|_|_| |_|\__,_|_|          \____|_|    |_|  


=============================
 Terminal GPT (Ollama Version)
=============================

Terminal GPT is a simple terminal chat app that runs on a locally installed
Ollama model. No cloud billing and no OpenAI API keys required.

To learn how to install, configure, and run the app:
>>> See the how_to_run.txt file.


------------------------------------------------------------
What This App Does
------------------------------------------------------------

• Lets you chat with a local AI model in real time
• Works through the terminal
• No external API calls
• Uses Ollama to host the model locally
• Supports interactive mode and one-shot command mode


------------------------------------------------------------
Quick Start (Assuming Setup Is Done)
------------------------------------------------------------

Run interactive mode:

    python3 gpt_cli.py

You can also ask a question directly:

    python3 gpt_cli.py "explain BFS"

The program will return the answer and exit.


------------------------------------------------------------
Changing the Model
------------------------------------------------------------

Open gpt_cli.py and find:

    MODEL = "llama3.2"

Change it to any Ollama model you have installed, for example:

    MODEL = "llama3"
    MODEL = "phi3"
    MODEL = "mistral"


------------------------------------------------------------
Requirements
------------------------------------------------------------

• Python 3.8+
• pip install requests
• Ollama installed and running


------------------------------------------------------------
Notes
------------------------------------------------------------

All inference happens locally.
No API keys.
No cloud usage.
Your data stays on your machine.

Enjoy hacking :)

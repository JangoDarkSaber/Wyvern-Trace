# AI Reverse Engineering Assistant - Architecture Document

## 🎯 Project Overview
This project is a containerized, AI-powered static reverse engineering web application. It automates the initial triage of malware (PE, ELF, DLL) by extracting a highly structured Knowledge Base (KB) using Headless Ghidra, and then uses a LangGraph ReAct agent to autonomously traverse the call graph, identify indicators of compromise (IOCs), and semantically rename functions.

## 🏗️ System Architecture
The application runs entirely inside a single Linux Docker container, deployed on a Windows 10 host via Docker Desktop (WSL2). It uses a shared volume to pass binaries in and extract project files/reports out.



### Core Tech Stack
* **Frontend UI:** Streamlit (Python)
* **AI Orchestration:** LangGraph & LangChain (`langgraph`, `langchain-core`)
* **LLM Provider:** Google GenAI (Gemini 3 Flash Preview via API)
* **Backend RE Engine:** Headless Ghidra (OpenJDK 21 + Ghidra 11.x)
* **Visualization:** Pyvis & NetworkX (Interactive HTML call graphs)

### 📂 Directory Structure
```text
ai-re-assistant/
├── Dockerfile                  # Debian/Python slim image with Java & Ghidra injected
├── docker-compose.yml          # Maps port 8501 and binds ./workspace volume
├── requirements.txt            # Python dependencies (Streamlit, LangGraph, Pyvis, etc.)
├── .env                        # Secure storage for GEMINI_API_KEY
├── ARCHITECTURE.md             # This file
│
├── workspace/                  # ⚠️ DOCKER VOLUME MOUNT ⚠️ (Shared with Windows Host)
│   ├── uploads/                # Where Streamlit saves dropped malware binaries
│   └── projects/               # Where Ghidra writes the .json KB and .gpr project files
│
├── app/                        # Main Python Application
│   ├── app.py                  # Streamlit dashboard, UI tabs, and subprocess trigger
│   ├── agent.py                # The LangGraph StateGraph, System Prompt, and ReAct loop
│   ├── tools.py                # The @tool functions that query the JSON KB in memory
│   └── visualizer.py           # NetworkX/Pyvis logic for Tab 2 (Interactive Call Graph)
│   └── ghidra_sync.py          # Generates Jython scripts for Ghidra integration
│
└── ghidra_scripts/
    └── ExtractLangGraphKB_V3.java  # Headless Java script that builds the JSON KB



⚙️ Component Breakdown
1. The Extractor (ExtractLangGraphKB_V3.java)
Runs headlessly via a Python subprocess. It iterates through the binary after auto-analysis and outputs a highly structured JSON dictionary mapping every function to its:

Decompiled C-Code & Raw Assembly fallback.

Callees (Internal functions & External APIs called).

Callers (Cross-references / XREFs pointing to the function).

Strings and Data referenced by the function.

2. The Tools (app/tools.py)
Loads the _KB_DATA JSON into RAM for O(1) lookups. Exposes 5 strict tools to the LLM:

get_function_code(func_name)

get_callers(func_name)

get_callees(func_name)

search_api(api_name)

search_strings(keyword)

3. The Brain (app/agent.py)
A StateGraph running a ReAct loop. It routes between the AgentNode (Gemini 3) and the ToolNode. The System Prompt explicitly forces the AI to traverse the call graph deterministically rather than guessing, and mandates a specific Markdown output format (### Executive Summary, ### Semantic Renames, ### IOCs).

4. The Dashboard (app/app.py)
A 5-Tab Streamlit interface:

Live Stream: Captures re_graph.stream to show the AI's internal thoughts and tool calls in real-time.

Tab 1 (Summary): Parses and displays the AI's executive breakdown.

Tab 2 (Neighborhood Graph): Uses visualizer.py to render a physics-based, interactive HTML node graph of any function the AI discovered.

Tab 3 (Renames): Displays the Markdown table of AI-proposed function names.

Tab 4 (IOCs): Lists extracted domains, IPs, and registry keys.

Tab 5 (Ghidra Sync): Generates a downloadable Jython script to port AI findings back to the native Ghidra GUI.

🚀 Execution Flow
User drops malware.exe into the Streamlit UI.

app.py triggers /opt/ghidra/support/analyzeHeadless, pointing it to the Java script.

Ghidra outputs malware_kb.json to the shared volume.

app.py loads the JSON into memory and triggers the LangGraph agent.

Agent loops through tools, mapping the execution path.

Agent hits END node; UI parses the Markdown and populates the 5 tabs.
# 🧠 AI-RE-Assistant: Autonomous Malware Triage

**A containerized, AI-powered Reverse Engineering workbench that bridges Headless Ghidra with LangGraph agents.**

![Python](https://img.shields.io/badge/Python-3.12-blue)
![Ghidra](https://img.shields.io/badge/Ghidra-11.1.2-green)
![LangGraph](https://img.shields.io/badge/LangGraph-ReAct-orange)
![Docker](https://img.shields.io/badge/Docker-Containerized-blue)

## 📖 Overview

**AI-RE-Assistant** automates the initial triage of malware (PE, ELF, DLL) by combining the static analysis power of **Ghidra** with the semantic reasoning of **Google Gemini 3**.

Instead of manually clicking through thousands of functions, this tool:
1.  **Extracts** a comprehensive Knowledge Base (KB) using Headless Ghidra.
2.  **Spawns** a LangGraph ReAct agent to traverse the call graph autonomously.
3.  **Identifies** Indicators of Compromise (IOCs) and malware capabilities.
4.  **Generates** a Python script to sync AI-proposed function renames back to your local Ghidra project.

---

## ✨ Key Features

### 🤖 LangGraph Reasoning Engine
Unlike generic "Chat with PDF" tools, this agent uses a **StateGraph** with a specialized toolset. It does not guess; it deterministically queries the binary's Knowledge Base to:
*   **Trace Execution Flow**: Follows cross-references (XREFs) backwards from suspicious APIs to `main`.
*   **Analyze Logic**: Reads decompiled C-code to understand function purpose.
*   **Hunt IOCs**: Scans for hardcoded IPs, domains, and registry keys.

### ⚙️ Headless Ghidra Integration
Runs a custom Java extraction script inside a Docker container to dump a highly structured JSON representation of the binary, including:
*   Decompiled C Pseudo-code
*   Assembly Instructions
*   Function Call Graphs (Callers/Callees)
*   String References

### 🕸️ Interactive Visualization
Includes a **Streamlit** dashboard with a physics-based interactive call graph (powered by Pyvis), allowing you to visually explore the "neighborhood" of any function the AI analyzes.

### 🔄 Ghidra Sync
Found good function names? The "Ghidra Sync" tab generates a **Jython script** that you can run in your local Ghidra GUI to instantly apply all AI-suggested renames.

---

## 🚀 Quick Start

### Prerequisites
*   **Docker Desktop** (Windows/Mac/Linux)
*   A **Google Gemini API Key** (Get one here)

### Installation

1.  **Clone the Repository**
    ```bash
    git clone https://github.com/yourusername/ai-re-assistant.git
    cd ai-re-assistant
    ```

2.  **Configure API Credentials**
    Create a file named `.env` in the root directory. Add your Gemini API key:
    ```ini
    # .env file
    GEMINI_API_KEY=your_actual_api_key_here
    ```
    > ⚠️ **IMPORTANT:** The container will fail to start the agent without this key.

3.  **Build and Run**
    Launch the container stack. This will download the Ghidra base image and install dependencies.
    ```bash
    docker-compose up --build
    ```

4.  **Access the Dashboard**
    Open your browser and navigate to:
    👉 **http://localhost:8501**

---

## 🕹️ Usage Guide

1.  **Upload**: Drop a binary (`.exe`, `.dll`, `.elf`) into the sidebar.
2.  **Direct**: (Optional) Modify the AI directive (e.g., *"Find the C2 communication logic"*).
3.  **Analyze**: Click **🚀 Analyze Binary**.
    *   *Phase 1*: Headless Ghidra analyzes the file (1-3 mins).
    *   *Phase 2*: The AI Agent explores the generated Knowledge Base.
4.  **Review**:
    *   **Executive Summary**: High-level overview of the malware.
    *   **Call Graph**: Interactive node map.
    *   **Ghidra Sync**: Download `apply_ai_renames.py` to import findings into your local tools.

---

## 🏗️ Architecture

For a deep dive into the internal component interactions, Docker volume mounts, and the LangGraph state machine, please refer to ARCHITECTURE.md.
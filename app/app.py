import streamlit as st
import os
import subprocess

from langchain_core.messages import HumanMessage
from agent import re_graph
from tools import init_kb

import streamlit.components.v1 as components
from visualizer import generate_subgraph_html
from tools import _KB_DATA  # Import the global KB dictionary we loaded in step 1
from ghidra_sync import generate_jython_script

# --- Configuration & Docker Paths ---
# These match the volume mounts inside our Linux container
WORKSPACE_DIR = "/workspace"
UPLOADS_DIR = os.path.join(WORKSPACE_DIR, "uploads")
PROJECTS_DIR = os.path.join(WORKSPACE_DIR, "projects")
GHIDRA_HEADLESS = "/opt/ghidra/support/analyzeHeadless" # Note: No .bat because we are in Linux!
SCRIPT_DIR = "/app/ghidra_scripts"
SCRIPT_NAME = "ExtractLangGraphKB_V3.java"

# Ensure directories exist
os.makedirs(UPLOADS_DIR, exist_ok=True)
os.makedirs(PROJECTS_DIR, exist_ok=True)

# --- UI Setup ---
st.set_page_config(page_title="AI RE Assistant", page_icon="🧠", layout="wide")
st.title("🧠 AI Reverse Engineering Assistant")

# --- Session State Initialization ---
if "analysis_complete" not in st.session_state:
    st.session_state.analysis_complete = False
if "kb_json_path" not in st.session_state:
    st.session_state.kb_json_path = None
if "final_report" not in st.session_state:
    st.session_state.final_report = ""
if "safe_project_name" not in st.session_state:
    st.session_state.safe_project_name = ""

# --- Function: Run Headless Ghidra ---
def run_headless_ghidra(target_path, project_name):
    """Executes Ghidra auto-analysis in the background and streams logs to the UI."""
    json_out_path = os.path.join(PROJECTS_DIR, f"{project_name}_kb.json")
    
    command = [
        GHIDRA_HEADLESS,
        PROJECTS_DIR,
        project_name,
        "-import", target_path,
        "-scriptPath", SCRIPT_DIR,
        "-postScript", SCRIPT_NAME,
        # Pass the output path to the Java script as an argument (we will need to tweak the Java script slightly to accept this)
        json_out_path 
    ]

    # We use st.status to create a collapsible UI element that shows the live terminal output
    with st.status("⚙️ Running Ghidra Headless Extraction...", expanded=True) as status:
        st.write(f"Target: `{target_path}`")
        st.write("Running auto-analysis. This may take a few minutes...")
        
        try:
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            
            # Stream the output live to the Streamlit dashboard
            log_container = st.empty()
            logs = []
            
            for line in process.stdout:
                if "[+]" in line or "[-]" in line or "INFO" in line:
                    logs.append(line.strip())
                    # Keep only the last 10 relevant lines to avoid UI clutter
                    log_container.code("\n".join(logs[-10:]), language="bash")
            
            process.wait()
            
            if process.returncode == 0 and os.path.exists(json_out_path):
                status.update(label="✅ Knowledge Base Extracted Successfully!", state="complete", expanded=False)
                return json_out_path
            else:
                status.update(label="❌ Extraction Failed. Check logs.", state="error", expanded=True)
                return None
                
        except Exception as e:
            st.error(f"Subprocess Error: {e}")
            status.update(label="❌ Fatal Error", state="error")
            return None

# --- Main Dashboard ---

# 1. Sidebar Control Center
with st.sidebar:
    st.header("Control Center")
    uploaded_file = st.file_uploader("Upload Binary (exe, dll, elf)", type=["exe", "dll", "bin", "elf"])
    
    st.markdown("---")
    directive = st.text_area("AI Directive", value="Map out the main execution flow and identify any network indicators or persistence mechanisms.", height=150)
    
    analyze_btn = st.button("🚀 Analyze Binary", type="primary", use_container_width=True)

# 2. Main Execution Flow
if uploaded_file:
    if analyze_btn:
        # Save the file to our Docker volume
        file_path = os.path.join(UPLOADS_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Clean up project name (no spaces or weird characters for Ghidra)
        safe_project_name = uploaded_file.name.replace(".", "_").replace(" ", "_")
        st.session_state.safe_project_name = safe_project_name
        
        # Step 1: Run Ghidra
        kb_json_path = run_headless_ghidra(file_path, safe_project_name)
        st.session_state.kb_json_path = kb_json_path
        
    if st.session_state.kb_json_path:
        st.markdown("### 🧠 AI Analysis Live Stream")
        
        # 1. Load the JSON into RAM for the tools
        if not init_kb(st.session_state.kb_json_path):
            st.error("Failed to load Knowledge Base into memory.")
            st.stop()
            
        # Only run the agent if we haven't already, OR if the user clicked analyze again
        if analyze_btn:
            final_report = ""
            
            # 2. Start the LangGraph execution stream
            inputs = {"messages": [HumanMessage(content=directive)]}
            
            stream_container = st.container()
            with stream_container:
                for s in re_graph.stream(inputs, stream_mode="updates"):
                    for node_name, node_state in s.items():
                        message = node_state["messages"][0]
                        
                        if node_name == "agent":
                            # Handle tool calls
                            if hasattr(message, 'tool_calls') and message.tool_calls:
                                for tc in message.tool_calls:
                                    with st.status(f"🤖 Agent is calling: `{tc['name']}`", expanded=False):
                                        st.write("**Arguments:**", tc.get('args', {}))
                            # Handle the final text response
                            elif message.content:
                                final_report = message.content
                                
                        elif node_name == "tools":
                            # Display truncated tool results so the UI doesn't crash
                            with st.expander(f"🛠️ Result from `{message.name}`"):
                                result_text = str(message.content)
                                if len(result_text) > 1000:
                                    st.text(result_text[:1000] + "\n... [TRUNCATED FOR UI] ...")
                                else:
                                    st.text(result_text)
            
            st.session_state.final_report = final_report
            st.session_state.analysis_complete = True
            st.success("Analysis Complete!")

        # Step 3: Render the Findings Tabs (Restoring your 5-Tab Design!)
        if st.session_state.analysis_complete:
            st.markdown("---")
            tab1, tab2, tab3, tab4, tab5 = st.tabs([
                "📝 Executive Summary", 
                "🕸️ Call Graph", 
                "🗄️ Semantic Renames", 
                "🚨 IOCs", 
                "⬇️ Ghidra Sync"
            ])
            
            # Parse the AI's final report to split it into the correct tabs
            summary_text = "*(No summary provided by AI)*"
            renames_text = "*(No renames provided by AI)*"
            iocs_text = "*(No IOCs provided by AI)*"
            
            if st.session_state.final_report:
                # We split the string based on the headers we forced the AI to use in agent.py
                parts = st.session_state.final_report.split("### ")
                for part in parts:
                    part = part.strip()
                    if part.startswith("Executive Summary"):
                        summary_text = part[len("Executive Summary"):].strip()
                    elif part.startswith("Semantic Renames"):
                        renames_text = part[len("Semantic Renames"):].strip()
                    elif part.startswith("IOCs"):
                        iocs_text = part[len("IOCs"):].strip()

            # Drop the parsed content into the exact tabs you defined
            with tab1:
                st.markdown(summary_text)
            with tab2:
                # We default to visualizing 'main' or 'entry', or the first function in the KB
                if _KB_DATA:
                    # Smart selection of entry point
                    candidates = ["main", "entry", "WinMain", "start", "_start", "DllMain"]
                    default_node = next(iter(_KB_DATA))
                    for c in candidates:
                        if c in _KB_DATA:
                            default_node = c
                            break
                    
                    st.caption(f"Visualizing neighborhood for: **{default_node}**")
                    html_graph = generate_subgraph_html(_KB_DATA, default_node)
                    if html_graph:
                        components.html(html_graph, height=500, scrolling=True)
                else:
                    st.warning("No Knowledge Base loaded to visualize.")
            with tab3:
                st.markdown(renames_text)
            with tab4:
                st.markdown(iocs_text)
            with tab5:
                st.write("### 🔄 Ghidra Sync")
                st.write("Download the extracted Knowledge Base or a Python script to apply renames in Ghidra.")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📥 Download JSON KB",
                        data=open(st.session_state.kb_json_path, "rb").read(),
                        file_name=os.path.basename(st.session_state.kb_json_path),
                        mime="application/json"
                    )
                
                with col2:
                    # Generate the script content using the helper function
                    sync_script = generate_jython_script(renames_text)

                    st.download_button(
                        label="📥 Download Sync Script (.py)",
                        data=sync_script,
                        file_name="apply_ai_renames.py",
                        mime="text/x-python"
                    )
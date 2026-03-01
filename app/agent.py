import os
from typing import TypedDict, Annotated, Sequence
import operator

# LangChain & LangGraph Imports
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition

# Import the tools we built in the previous step
from tools import RE_TOOLS

# --- 1. Define the Graph State ---
# This is the memory object passed between nodes. LangGraph uses `operator.add` 
# to append new messages to the list rather than overwriting them.
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]

# --- 2. Initialize the LLM ---
# We use Gemini 3 Flash here because it is exceptionally fast at agentic tool calling
# and has a massive context window for reading decompiled C code.
llm = ChatGoogleGenerativeAI(
    model="gemini-3-flash-preview", 
    temperature=0.1, # Keep temperature very low for deterministic, factual RE analysis
    api_key=os.environ.get("GEMINI_API_KEY")
)

# Bind the tools to the LLM so it knows they exist
llm_with_tools = llm.bind_tools(RE_TOOLS)

# --- 3. The System Prompt ---
# This dictates the AI's behavior and ensures it formats its final output perfectly for our Streamlit UI.
SYSTEM_PROMPT = """You are an elite reverse engineering and malware analysis AI.
You have been provided with a specialized toolset to query a statically extracted binary Knowledge Base (KB).

YOUR DIRECTIVE:
1. You do not need to guess. Use your tools to traverse the call graph, read C pseudo-code, and find strings/APIs.
2. If the user asks for network indicators, use `search_api` to look for networking APIs (e.g., WinINet, WinSock) or `search_strings` for HTTP/IPs.
3. Once you find a target function, use `get_callers` to trace the execution flow BACKWARDS to `entry` or `main`.
4. When you have satisfied the user's request, you must output a final report.

FINAL REPORT FORMAT:
When you are finished analyzing, your final message MUST include these three markdown sections exactly:
### Executive Summary
(Explain the execution flow and the malware's purpose here)

### Semantic Renames
| Original Address | Proposed Name | Reason |
| --- | --- | --- |
(List any functions you analyzed here)

### IOCs
(List any domains, IPs, file paths, or registry keys you found)
"""

# --- 4. Define the Nodes ---

def agent_node(state: AgentState):
    """The 'Brain' node that decides what to do next."""
    messages = state["messages"]
    
    # Inject the system prompt if it's not already in the message history
    if not any(isinstance(m, SystemMessage) for m in messages):
        messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        
    # Call the LLM with the current conversation history
    response = llm_with_tools.invoke(messages)
    
    # Return the LLM's response to be appended to the state
    return {"messages": [response]}

# The ToolNode automatically executes the Python functions based on the LLM's requests
tool_node = ToolNode(RE_TOOLS)

# --- 5. Compile the Graph ---

# Initialize the graph
workflow = StateGraph(AgentState)

# Add our two main nodes
workflow.add_node("agent", agent_node)
workflow.add_node("tools", tool_node)

# Set the entry point
workflow.add_edge(START, "agent")

# The magic routing edge:
# If the agent's response includes a tool_call, it routes to 'tools'.
# If the agent just returns text (meaning it's finished), it routes to 'END'.
workflow.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})

# After tools execute, ALWAYS route back to the agent so it can read the tool output
workflow.add_edge("tools", "agent")

# Compile into a runnable application
re_graph = workflow.compile()
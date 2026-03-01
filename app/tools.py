import json
from langchain_core.tools import tool

# Global variable to hold our Knowledge Base in memory so tools can access it instantly
# without reloading the JSON file on every single tool call.
_KB_DATA = {}

def init_kb(json_path: str):
    """Loads the Ghidra JSON output into memory for the tools to use."""
    global _KB_DATA
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            _KB_DATA.clear()
            _KB_DATA.update(json.load(f))
        return True
    except Exception as e:
        print(f"Error loading KB: {e}")
        _KB_DATA.clear()
        return False

# --- LangChain Tools ---

@tool
def get_function_code(func_name: str) -> str:
    """
    Use this to read the C pseudo-code and raw assembly of a specific function.
    Always use this when you need to understand the underlying logic, math, or data manipulation of a function.
    """
    if not _KB_DATA:
        return "Error: Knowledge Base not loaded."
        
    func_data = _KB_DATA.get(func_name)
    if not func_data:
        return f"Error: Function '{func_name}' not found in the binary."

    # Return the C code, or fallback to assembly if decompilation failed
    c_code = func_data.get("c_code", "// No C code available")
    assembly = func_data.get("assembly", "")
    
    result = f"--- C CODE FOR {func_name} ---\n{c_code}\n"
    if "DECOMPILATION FAILED" in c_code or c_code.strip() == "":
        result += f"\n--- RAW ASSEMBLY FALLBACK ---\n{assembly}\n"
        
    return result

@tool
def get_callers(func_name: str) -> list:
    """
    Use this to find out WHICH functions call the target function (Cross-References / XREFs).
    Crucial for tracing execution flow BACKWARDS to find where data originated (e.g., tracing from a payload injector back to main).
    """
    if not _KB_DATA:
        return ["Error: KB not loaded."]
        
    func_data = _KB_DATA.get(func_name)
    if not func_data:
        return [f"Error: Function '{func_name}' not found."]
        
    return func_data.get("called_by", [])

@tool
def get_callees(func_name: str) -> dict:
    """
    Use this to see what internal functions and External APIs a target function calls.
    Crucial for tracing execution flow FORWARDS.
    """
    if not _KB_DATA:
        return {"error": "KB not loaded."}
        
    func_data = _KB_DATA.get(func_name)
    if not func_data:
        return {"error": f"Function '{func_name}' not found."}
        
    return {
        "calls_internal": func_data.get("calls_internal", []),
        "calls_api": func_data.get("calls_api", [])
    }

@tool
def search_api(api_name: str) -> list:
    """
    Use this to search the ENTIRE binary for any function that calls a specific external API.
    Example: search_api("InternetOpenUrlA") or search_api("VirtualAlloc").
    Returns a list of internal function names that call the requested API.
    """
    if not _KB_DATA:
        return ["Error: KB not loaded."]
        
    matching_funcs = []
    # Case-insensitive search to help the LLM if it slightly misnames the API
    api_name_lower = api_name.lower()
    
    for func, data in _KB_DATA.items():
        apis = data.get("calls_api", [])
        if any(api_name_lower in api.lower() for api in apis):
            matching_funcs.append(func)
            
    return matching_funcs

@tool
def search_strings(keyword: str) -> dict:
    """
    Use this to search the ENTIRE binary for any function that references a specific string or keyword.
    Example: search_strings("http") or search_strings("cmd.exe").
    Returns a dictionary mapping the function name to the exact string matched.
    """
    if not _KB_DATA:
        return {"error": "KB not loaded."}
        
    results = {}
    keyword_lower = keyword.lower()
    
    for func, data in _KB_DATA.items():
        strings = data.get("strings_referenced", [])
        matched = [s for s in strings if keyword_lower in s.lower()]
        if matched:
            results[func] = matched
            
    return results

# Package them up in a list so our LangGraph agent can easily bind them
RE_TOOLS = [
    get_function_code,
    get_callers,
    get_callees,
    search_api,
    search_strings
]
import re

def generate_jython_script(renames_markdown: str) -> str:
    """
    Parses the Markdown table of semantic renames outputted by the LangGraph agent.
    Extracts original addresses and new proposed names.
    Returns a multi-line string containing a valid Jython script using Ghidra's 
    getSymbolAt and createSymbol APIs.
    
    Args:
        renames_markdown (str): The markdown string containing the renames table.
        
    Returns:
        str: The generated Jython script content ready for Ghidra.
    """
    
    # Header for the generated Jython script
    # We import necessary Ghidra classes and set up helper functions.
    script_lines = [
        "# AI-RE-Assistant: Auto-Generated Ghidra Sync Script",
        "# ---------------------------------------------------",
        "# Instructions:",
        "# 1. Open your binary in Ghidra.",
        "# 2. Open the Script Manager (Window -> Script Manager).",
        "# 3. Create a new script (New Script button), paste this code, and Run.",
        "",
        "import ghidra.program.model.symbol.SourceType as SourceType",
        "from ghidra.util.exception import DuplicateNameException, InvalidInputException",
        "",
        "# Helper to resolve address strings to Ghidra Address objects",
        "def get_addr(addr_str):",
        "    return currentProgram.getAddressFactory().getAddress(addr_str)",
        "",
        "print('[*] Starting AI Semantic Renames...')",
        "count = 0",
        ""
    ]
    
    # Split the markdown input into lines for processing
    lines = renames_markdown.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        
        # Skip separator lines (e.g., |---|---|) and empty lines
        # We check if the line contains only table formatting characters
        if not line or set(line) <= {'|', '-', ' ', ':'}:
            continue
            
        # Process lines that look like table rows
        if "|" in line:
            # Split by pipe and strip whitespace
            parts = [p.strip() for p in line.split("|") if p.strip()]
            
            # Ensure we have at least Address and Name columns (Index 0 and 1)
            if len(parts) >= 2:
                addr_str = parts[0]
                new_name = parts[1]
                
                # Skip the header row
                if "Original" in addr_str or "Address" in addr_str:
                    continue
                
                # Sanitize the name: replace non-alphanumeric chars with underscores
                safe_name = re.sub(r'[^a-zA-Z0-9_]', '_', new_name)
                
                # Generate the Jython code block for this specific rename
                # We use a try/except block to ensure one bad address doesn't crash the whole script.
                script_lines.append(f"try:")
                script_lines.append(f"    target_addr = get_addr('{addr_str}')")
                script_lines.append(f"    # Check if a symbol already exists at this address")
                script_lines.append(f"    existing_sym = getSymbolAt(target_addr)")
                script_lines.append(f"    if existing_sym:")
                script_lines.append(f"        existing_sym.setName('{safe_name}', SourceType.USER_DEFINED)")
                script_lines.append(f"        print('  [+] Renamed symbol at {addr_str} to {safe_name}')")
                script_lines.append(f"    else:")
                script_lines.append(f"        # Create a new primary symbol if none exists")
                script_lines.append(f"        createSymbol(target_addr, '{safe_name}', True)")
                script_lines.append(f"        print('  [+] Created symbol {safe_name} at {addr_str}')")
                script_lines.append(f"    count += 1")
                script_lines.append(f"except Exception as e:")
                script_lines.append(f"    print('  [-] Error processing {addr_str}: ' + str(e))")
                script_lines.append("")

    # Footer for the script
    script_lines.append("print('[*] Sync Complete. Total renames applied: ' + str(count))")
    
    return "\n".join(script_lines)
import networkx as nx
from pyvis.network import Network
import tempfile
import os

def generate_subgraph_html(kb_data: dict, center_node: str):
    """
    Generates an interactive HTML graph centered on a specific function.
    Shows the function, what it calls (internal & APIs), and who calls it.
    """
    if center_node not in kb_data:
        return None

    nx_graph = nx.DiGraph()
    
    # Add the Center Node (The target function)
    # The 'title' acts as a hover tooltip. We put a snippet of the C-code there!
    c_code_snippet = kb_data[center_node].get("c_code", "No code")[:200] + "..."
    nx_graph.add_node(center_node, color="#e74c3c", title=c_code_snippet, size=25, label=f"🎯 {center_node}")
    
    # Add Callees (Functions this node calls) -> Looking Down
    for callee in kb_data[center_node].get("calls_internal", []):
        nx_graph.add_node(callee, color="#3498db", size=15)
        nx_graph.add_edge(center_node, callee)
        
    # Add External APIs (What OS functions it uses) -> Looking Out
    for api in kb_data[center_node].get("calls_api", []):
        nx_graph.add_node(api, color="#2ecc71", shape="box", size=15)
        nx_graph.add_edge(center_node, api)
        
    # Add Callers (Who called this node) -> Looking Up
    for caller in kb_data[center_node].get("called_by", []):
        nx_graph.add_node(caller, color="#f39c12", size=15)
        nx_graph.add_edge(caller, center_node)

    # Configure the Pyvis Network (Dark Mode)
    net = Network(height="500px", width="100%", bgcolor="#0e1117", font_color="white", directed=True)
    net.from_nx(nx_graph)
    
    # Add some physics controls so the user can play with the layout
    net.set_options("""
    var options = {
      "physics": {
        "forceAtlas2Based": {
          "gravitationalConstant": -50,
          "centralGravity": 0.01,
          "springLength": 100,
          "springConstant": 0.08
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
      }
    }
    """)
    
    # Save the graph to a temporary HTML file and read it back
    tmp_dir = tempfile.gettempdir()
    tmp_file = os.path.join(tmp_dir, f"graph_{center_node}.html")
    net.save_graph(tmp_file)
    
    with open(tmp_file, "r", encoding="utf-8") as f:
        html_data = f.read()
        
    return html_data
"""mini_graph/html_export.py — write the graph to one HTML file.

pyvis embeds vis-network in the file when cdn_resources is "in_line",
so the page does not need a separate script download.
"""

import os

from pyvis.network import Network


def write_html(investigation, path):
    """Write a directed graph that can be opened in a browser."""
    network = Network(
        directed=True,
        height="800px",
        width="100%",
        bgcolor="#ffffff",
        cdn_resources="in_line",
    )
    graph = investigation.graph
    for node_id, data in graph.nodes(data=True):
        title = _node_title(data)
        label = str(data["value"])
        if len(label) > 80:
            label = label[:77] + "..."
        network.add_node(node_id, label=label, title=title, group=data["type"])

    for source, target, edge in graph.edges(data=True):
        network.add_edge(source, target, label=edge.get("label", ""))

    folder = os.path.dirname(os.path.abspath(path))
    os.makedirs(folder, exist_ok=True)
    # pyvis opens the file with the system encoding. On this Windows
    # code page that fails for the inlined script, so the HTML is written as UTF-8.
    html = network.generate_html(notebook=False)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(html)


def _node_title(data):
    """Hover text. SPF and DMARC still show the record string and nothing else."""
    properties = data.get("properties") or {}
    record = properties.get("record") or ""
    lines = [data["type"]] if not record else [data["type"], record]
    if properties.get("status"):
        lines.append(f"status={properties['status']}")
    if properties.get("last_changed"):
        lines.append(f"changed={properties['last_changed']}")
    if properties.get("cidr"):
        lines.append(f"cidr={properties['cidr']}")
    elif properties.get("start") and properties.get("end"):
        lines.append(f"range={properties['start']}-{properties['end']}")
    if len(lines) == 1:
        return lines[0]
    return "\n".join(lines)

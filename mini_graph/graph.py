"""mini_graph/graph.py — a networkx graph of entities and links.

The graph lives in the client: a transform returns entities, and the client
links each one to the input node. InvestigationGraph does that step here.
A networkx DiGraph is a directed graph; the arrow goes from the input
entity to the entity that was found.
"""

import networkx as nx

from mini_graph.model import Entity


class InvestigationGraph:
    """Nodes are entities, and edges are the transform's link labels."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_entity(self, entity):
        """Add an entity as a node. If the same id already exists, do not create another."""
        if entity.id not in self.graph:
            self.graph.add_node(
                entity.id,
                type=entity.type_name,
                value=entity.value,
                weight=entity.weight,
                properties=dict(entity.properties),
                display=entity.display,
            )
        return entity.id

    def add_seed(self, type_name, value):
        """Starting node of an investigation. The first entity placed on the graph by hand."""
        return self.add_entity(Entity(type_name, value))

    def run_transform(self, source_id, transform, limit=100):
        """Run a transform on the selected node and attach the results to the graph.

        transform(entity, limit) -> (linked_entities, messages)
        Each result becomes a new (or existing) node, with an edge from source_id.
        """
        data = self.graph.nodes[source_id]
        source = Entity(data["type"], data["value"], data.get("properties"), data.get("weight", 100))
        linked, messages = transform(source, limit=limit)

        for item in linked:
            target_id = self.add_entity(item.entity)
            origin = item.source_id or source_id
            # Do not add a second edge for the same pair and the same label.
            if origin in self.graph and not self.graph.has_edge(origin, target_id):
                self.graph.add_edge(origin, target_id, label=item.link_label)
        return messages

    def render(self):
        """Return the graph as a text tree: node, outgoing links, and counts."""
        lines = []
        roots = [node for node in self.graph.nodes if self.graph.in_degree(node) == 0]
        if not roots:
            roots = list(self.graph.nodes)

        for root in roots:
            data = self.graph.nodes[root]
            lines.append(f"{data['type']}  {data['value']}")
            for _source, target, edge in self.graph.out_edges(root, data=True):
                lines.append(_edge_line(self.graph, target, edge, "  "))
                # A network node hangs off the IP node. DNS records have no
                # children, so this extra level does not change their lines.
                for _nested_source, nested, nested_edge in self.graph.out_edges(target, data=True):
                    lines.append(_edge_line(self.graph, nested, nested_edge, "    "))

        node_count = self.graph.number_of_nodes()
        edge_count = self.graph.number_of_edges()
        node_word = "node" if node_count == 1 else "nodes"
        edge_word = "edge" if edge_count == 1 else "edges"
        lines.append(f"{node_count} {node_word}, {edge_count} {edge_word}")
        return "\n".join(lines)


def _edge_line(graph, target, edge, indent):
    """One indented link. MX priority is unchanged when it is the only property."""
    target_data = graph.nodes[target]
    return (
        f"{indent}--{edge.get('label', '')}-->  "
        f"{target_data['type']}  {target_data['value']}{_detail_suffix(target_data.get('properties'))}"
    )


def _detail_suffix(properties):
    properties = properties or {}
    parts = []
    if properties.get("priority"):
        parts.append(f"priority={properties['priority']}")
    if properties.get("status"):
        parts.append(f"status={properties['status']}")
    if properties.get("last_changed"):
        parts.append(f"changed={properties['last_changed']}")
    if properties.get("cidr"):
        parts.append(f"cidr={properties['cidr']}")
    elif properties.get("start") and properties.get("end"):
        parts.append(f"range={properties['start']}-{properties['end']}")
    if not parts:
        return ""
    return "  " + "  ".join(parts)

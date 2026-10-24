"""mini_graph/graph.py — entity-ləri və linkləri saxlayan networkx qrafı.

Qraf klientdə yaşayır: transform entity qaytarır, klient
hər birini giriş düyününə bağlayır. Burada həmin addımı InvestigationGraph
edir. networkx DiGraph istiqamətli qrafdır; ox giriş entity-sindən
tapılan entity-yə gedir.
"""

import networkx as nx

from mini_graph.model import Entity


class InvestigationGraph:
    """Düyünlər Entity-dir, tillər isə transformun link yazısıdır."""

    def __init__(self):
        self.graph = nx.DiGraph()

    def add_entity(self, entity):
        """Entity-ni düyün kimi əlavə edir. Eyni id artıq varsa, yenisini yaratmır."""
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
        """İstintaqın başlanğıc düyünü. Qrafa əllə qoyulan ilk entity."""
        return self.add_entity(Entity(type_name, value))

    def run_transform(self, source_id, transform, limit=100):
        """Seçilmiş düyündə transformu işlədir və nəticələri qrafa bağlayır.

        transform(entity, limit) -> (linked_entities, messages)
        Hər nəticə yeni (və ya mövcud) düyün olur və source_id-dən ora till gəlir.
        """
        data = self.graph.nodes[source_id]
        source = Entity(data["type"], data["value"], data.get("properties"), data.get("weight", 100))
        linked, messages = transform(source, limit=limit)

        for item in linked:
            target_id = self.add_entity(item.entity)
            # Eyni cüt və eyni yazı təkrar till olmasın.
            if not self.graph.has_edge(source_id, target_id):
                self.graph.add_edge(source_id, target_id, label=item.link_label)
        return messages

    def render(self):
        """Qrafı mətn ağacı kimi qaytarır: düyün, ondan çıxan linklər, say."""
        lines = []
        roots = [node for node in self.graph.nodes if self.graph.in_degree(node) == 0]
        if not roots:
            roots = list(self.graph.nodes)

        for root in roots:
            data = self.graph.nodes[root]
            lines.append(f"{data['type']}  {data['value']}")
            for _source, target, edge in self.graph.out_edges(root, data=True):
                target_data = self.graph.nodes[target]
                priority = target_data.get("properties", {}).get("priority")
                suffix = f"  priority={priority}" if priority else ""
                lines.append(
                    f"  --{edge.get('label', '')}-->  {target_data['type']}  {target_data['value']}{suffix}"
                )

        node_count = self.graph.number_of_nodes()
        edge_count = self.graph.number_of_edges()
        node_word = "node" if node_count == 1 else "nodes"
        edge_word = "edge" if edge_count == 1 else "edges"
        lines.append(f"{node_count} {node_word}, {edge_count} {edge_word}")
        return "\n".join(lines)

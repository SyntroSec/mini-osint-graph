"""Offline test that the HTML file contains every node value."""

from mini_graph.graph import InvestigationGraph
from mini_graph.html_export import write_html
from mini_graph.model import Entity


def test_html_file_contains_each_node_value(tmp_path):
    graph = InvestigationGraph()
    graph.add_seed("maltego.Domain", "example.com")
    graph.add_entity(Entity("maltego.IPv4Address", "203.0.113.10"))
    graph.add_entity(Entity("ipv6-address", "2001:db8::10"))
    graph.add_entity(Entity("name-server", "ns1.example.com"))
    graph.add_entity(Entity("txt-record", "v=spf1 -all"))
    graph.add_entity(Entity("spf-result", "present"))
    graph.add_entity(Entity("dmarc-result", "missing"))

    path = tmp_path / "graph.html"
    write_html(graph, path)

    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    for value in (
        "example.com",
        "203.0.113.10",
        "2001:db8::10",
        "ns1.example.com",
        "v=spf1 -all",
        "present",
        "missing",
    ):
        assert value in text

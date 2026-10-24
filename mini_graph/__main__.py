"""mini_graph/__main__.py — command line for the tool.

Run from the project root:
  python -m mini_graph example.com
  python -m mini_graph example.com 5
  python -m mini_graph example.com --html out.html

The second argument is the slider: how many new entities may be added.
The printed graph includes A, MX, AAAA, NS, TXT, and SPF/DMARC present or missing.
The flow is: seed entity, transform, child nodes on the graph.
"""

import sys

from mini_graph.dns_transform import DOMAIN, domain_to_dns
from mini_graph.graph import InvestigationGraph
from mini_graph.html_export import write_html


def _parse_args(argv):
    """Split a domain, an optional limit, and an optional --html path.

    argv arrives here as sys.argv[1:]. Positional order stays domain, then limit.
    """
    html_path = None
    positionals = []
    index = 0
    while index < len(argv):
        item = argv[index]
        if item == "--html":
            if index + 1 >= len(argv):
                print("--html needs a file path.")
                return None
            html_path = argv[index + 1]
            index += 2
            continue
        positionals.append(item)
        index += 1

    if not positionals:
        print("Usage: python -m mini_graph <domain> [limit] [--html FILE]")
        return None

    limit = 100
    if len(positionals) > 1:
        try:
            limit = int(positionals[1])
        except ValueError:
            print("Limit must be an integer.")
            return None
    return positionals[0], limit, html_path


def main(argv):
    if not argv or argv[0] in {"-h", "--help"}:
        print("Usage: python -m mini_graph <domain> [limit] [--html FILE]")
        return 2

    parsed = _parse_args(argv)
    if parsed is None:
        return 2
    domain, limit, html_path = parsed

    graph = InvestigationGraph()
    seed_id = graph.add_seed(DOMAIN, domain)
    messages = graph.run_transform(seed_id, domain_to_dns, limit=limit)

    print(graph.render())
    for message in messages:
        print(f"[{message.kind}] {message.text}")
    if html_path:
        write_html(graph, html_path)
        print(f"Wrote {html_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

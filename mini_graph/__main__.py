"""mini_graph/__main__.py — command line for the tool.

Run from the project root:
  python -m mini_graph example.com
  python -m mini_graph example.com 5
  python -m mini_graph example.com --html out.html
  python -m mini_graph example.com --subdomains

The second argument is the slider: how many new entities may be added.
The printed graph includes A, MX, AAAA, NS, TXT, and SPF/DMARC present or missing.
--subdomains also adds certificate names from crt.sh. Without that flag,
the lookup is only DNS.
The flow is: seed entity, transform, child nodes on the graph.
"""

import sys
from functools import partial

from mini_graph.dns_transform import DOMAIN, domain_to_dns
from mini_graph.graph import InvestigationGraph
from mini_graph.html_export import write_html

USAGE = "Usage: python -m mini_graph <domain> [limit] [--html FILE] [--subdomains]"


def _parse_args(argv):
    """Split a domain, an optional limit, and optional --html and --subdomains.

    argv arrives here as sys.argv[1:]. Positional order stays domain, then limit.
    """
    html_path = None
    include_subdomains = False
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
        if item == "--subdomains":
            include_subdomains = True
            index += 1
            continue
        positionals.append(item)
        index += 1

    if not positionals:
        print(USAGE)
        return None

    limit = 100
    if len(positionals) > 1:
        try:
            limit = int(positionals[1])
        except ValueError:
            print("Limit must be an integer.")
            return None
    return positionals[0], limit, html_path, include_subdomains


def main(argv):
    if not argv or argv[0] in {"-h", "--help"}:
        print(USAGE)
        return 2

    parsed = _parse_args(argv)
    if parsed is None:
        return 2
    domain, limit, html_path, include_subdomains = parsed

    graph = InvestigationGraph()
    seed_id = graph.add_seed(DOMAIN, domain)
    # The default transform is domain_to_dns with no extra arguments.
    transform = domain_to_dns
    if include_subdomains:
        transform = partial(domain_to_dns, include_subdomains=True)
    messages = graph.run_transform(seed_id, transform, limit=limit)

    print(graph.render())
    for message in messages:
        print(f"[{message.kind}] {message.text}")
    if html_path:
        write_html(graph, html_path)
        print(f"Wrote {html_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

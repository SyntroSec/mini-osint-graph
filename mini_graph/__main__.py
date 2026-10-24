"""mini_graph/__main__.py — alətin əmr sətri.

İşə salma, layihə kökündən:
  python -m mini_graph example.com
  python -m mini_graph example.com 5

İkinci arqument slider-dir: ən çox neçə yeni entity qrafa düşsün.
Axın belədir: seed entity, transform, qrafda uşaq düyünlər.
"""

import sys

from mini_graph.dns_transform import DOMAIN, domain_to_dns
from mini_graph.graph import InvestigationGraph


def main(argv):
    # argv buraya sys.argv[1:] kimi gəlir: ilk element domen, ikincisi limit.
    if not argv or argv[0] in {"-h", "--help"}:
        print("Usage: python -m mini_graph <domain> [limit]")
        return 2

    limit = 100
    if len(argv) > 1:
        try:
            limit = int(argv[1])
        except ValueError:
            print("Limit must be an integer.")
            return 2

    graph = InvestigationGraph()
    seed_id = graph.add_seed(DOMAIN, argv[0])
    messages = graph.run_transform(seed_id, domain_to_dns, limit=limit)

    print(graph.render())
    for message in messages:
        print(f"[{message.kind}] {message.text}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

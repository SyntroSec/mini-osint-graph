"""extensions.py — the transform passport shown in the graph client.

The transform itself lives in transforms/DomainToDns.py. This file only
stores metadata: who wrote it, which entity type it accepts, and which
name to show when the CSV and local.mtz are built.

host_url is not used when the local .mtz runs. It is the base of the
/run/<name> URL in the CSV if the same code later runs as a transform
server (python project.py runserver). The server stays on 127.0.0.1 —
this transform belongs to this machine only.
"""

from maltego_trx.decorator_registry import TransformRegistry

registry = TransformRegistry(
    owner="Local learning project",
    author="Ümid",
    host_url="http://127.0.0.1:8080",
    seed_ids=["local-dns"],
)

registry.version = "0.1"

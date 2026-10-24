"""project.py — entry point for this project.

A local transform does not open a separate server. The client runs this file
once, passes the input entity value as an argument, reads the XML on stdout,
and adds new nodes to the graph.

Commands (maltego-trx handle_run contract):
  python project.py list
  python project.py local domaintodns example.com
  python project.py runserver

The lines above regenerate transforms.csv, settings.csv, and local.mtz on
every run. local.mtz is the local package loaded into the graph client with
Import Config. The command field points at this virtual environment's
python.exe so the client uses the environment where the library is installed,
rather than the system Python.
"""

import locale
import os
import sys

import transforms
from extensions import registry
from maltego_trx.handler import handle_run
from maltego_trx.registry import register_transform_classes
from maltego_trx.server import app as application

register_transform_classes(transforms)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TRANSFORMS_CSV = os.path.join(PROJECT_DIR, "transforms.csv")

registry.write_transforms_config(
    config_path=TRANSFORMS_CSV,
    include_output_entities=True,
)
# The library builds the server URL with os.path.join. On Windows that writes
# a backslash instead of http://127.0.0.1:8080/run/domaintodns.
# The CSV is opened with the library's own encoding (the Windows code page here).
# The local .mtz does not use that URL; only the slash is rewritten so the CSV stays readable.
csv_encoding = locale.getpreferredencoding(False)
with open(TRANSFORMS_CSV, encoding=csv_encoding) as handle:
    csv_text = handle.read().replace("\\", "/")
with open(TRANSFORMS_CSV, "w", encoding=csv_encoding, newline="") as handle:
    handle.write(csv_text)
registry.write_settings_config(config_path=os.path.join(PROJECT_DIR, "settings.csv"))
registry.write_local_mtz(
    mtz_path=os.path.join(PROJECT_DIR, "local.mtz"),
    working_dir=PROJECT_DIR,
    command=sys.executable,
    params="project.py",
    debug=True,
)

if __name__ == "__main__":
    handle_run(__name__, sys.argv, application)

"""samples/serve_local.py — binds the transform server to this machine only.

project.py runserver is maltego-trx's own command and chooses host 0.0.0.0
(all network interfaces). This file opens the same Flask app on 127.0.0.1:8080
so the HTTP/XML exchange does not leave the computer.

Stop it with Ctrl+C in this window.

Example request, from the project root in another terminal:
  curl.exe -D - -H "Content-Type: application/xml" --data-binary "@samples/domain_request.xml" http://127.0.0.1:8080/run/domaintodns
"""

import os
import sys

# This file lives in samples/. project.py is one directory up, and
# Python does not find it on its own, so the project root is added to the path.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from project import application

if __name__ == "__main__":
    # debug=False: Flask does not start a second process; the server stays in one process.
    application.run(host="127.0.0.1", port=8080, debug=False)

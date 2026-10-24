"""samples/serve_local.py — transform serverini yalnız bu maşına bağlayır.

project.py runserver maltego-trx-in öz əmridir və host-u 0.0.0.0 seçir
(bütün şəbəkə interfeysləri). Bu fayl eyni Flask tətbiqini 127.0.0.1:8080
ünvanında açır ki, HTTP/XML mübadiləsi kompüterdən kənara çıxmasın.

Dayandırmaq: bu pəncərədə Ctrl+C.

Sorğu nümunəsi, başqa bir terminalda, layihə kökündən:
  curl.exe -D - -H "Content-Type: application/xml" --data-binary "@samples/domain_request.xml" http://127.0.0.1:8080/run/domaintodns
"""

import os
import sys

# Fayl samples/ içindədir. project.py bir qovluq yuxarıdadır və
# Python onu öz-özünə tapmır, ona görə layihə kökünü yola əlavə edirik.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from project import application

if __name__ == "__main__":
    # debug=False: Flask ikinci proses açmır, server tək prosesdə qalır.
    application.run(host="127.0.0.1", port=8080, debug=False)

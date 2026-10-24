"""project.py — bu layihənin giriş nöqtəsi.

Lokal transform ayrıca server açmır. Klient bu faylı bir dəfə
işə salır, giriş entity-sinin dəyərini arqument verir və stdout-dakı XML-i
oxuyub qrafa yeni düyünlər əlavə edir.

Əmrlər (maltego-trx-in öz handle_run müqaviləsi):
  python project.py list
  python project.py local domaintodns example.com
  python project.py runserver

İlk iki sətir hər işə düşəndə transforms.csv, settings.csv və local.mtz
yeniləyir. local.mtz qraf klientinə Import Config ilə yüklənən lokal paketdir.
command sahəsi bu virtual mühitin python.exe faylına bağlanır ki, klient
sistem Python-unu yox, kitabxananın quraşdırıldığı mühiti çağırsın.
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
# Kitabxana server ünvanını os.path.join ilə yazır. Windows-da bu,
# http://127.0.0.1:8080/run/domaintodns əvəzinə tərs slash qoyur.
# CSV kitabxananın öz encoding-i ilə açılır (burada Windows kod səhifəsi).
# Lokal .mtz həmin ünvanı işlətmir; oxunuş düzgün qalsın deyə yalnız slash-ı çeviririk.
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

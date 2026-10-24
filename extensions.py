"""extensions.py — transformun qraf klientində görünən pasportu.

Transformun özü transforms/DomainToDns.py içindədir. Bu fayl yalnız
metaməlumat saxlayır: kim yazıb, hansı entity tipi qəbul olunur, CSV və
local.mtz yaradılarkən hansı ad göstərilsin.

host_url lokal .mtz işə salınanda istifadə olunmur. O, eyni kod sonradan
transform serveri kimi qaçanda (python project.py runserver) CSV-dəki
/run/<ad> ünvanının əsasıdır. Server 127.0.0.1-də qalır — bu, tək
bu maşının öz transformudur.
"""

from maltego_trx.decorator_registry import TransformRegistry

registry = TransformRegistry(
    owner="Local learning project",
    author="Ümid",
    host_url="http://127.0.0.1:8080",
    seed_ids=["local-dns"],
)

registry.version = "0.1"

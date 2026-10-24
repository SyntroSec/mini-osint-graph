# mini-osint-graph

Domen adından DNS A və MX qeydlərini oxuyur və onları qraf kimi göstərir.

İki giriş var:

- `mini_graph` — nəticəni networkx qrafında mətn kimi çap edir.
- `project.py` — eyni sorğunu `maltego-trx` ilə lokal transform və ya HTTP transform serveri kimi işlədir. Giriş entity tipi `maltego.Domain`, çıxışlar `maltego.IPv4Address` və `maltego.MXRecord`-dur.

## Quraşdırma

Layihə kökündə:

```text
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## İşlətmə

Qraf aləti:

```text
.\venv\Scripts\python.exe -m mini_graph example.com
.\venv\Scripts\python.exe -m mini_graph example.com 1
```

İkinci ədəd nəticə limitidir.

Lokal transform (stdout-a XML):

```text
.\venv\Scripts\python.exe project.py local domaintodns example.com
```

Öz maşınında HTTP server, yalnız `127.0.0.1:8080`:

```text
.\venv\Scripts\python.exe samples\serve_local.py
```

Başqa terminalda:

```text
curl.exe -D - -H "Content-Type: application/xml" --data-binary "@samples/domain_request.xml" http://127.0.0.1:8080/run/domaintodns
```

Serveri `Ctrl+C` ilə dayandır.

Layihə üçüncü tərəf açıq kitabxanalardan (maltego-trx, networkx) istifadə edir, detallar NOTICE.md faylındadır və layihənin hər hansı şirkətlə əlaqəsi yoxdur.

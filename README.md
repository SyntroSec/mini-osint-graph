# mini-osint-graph

Reads DNS A, AAAA, MX, NS, and TXT records for a domain name and shows them as a graph. SPF is detected from TXT records that start with `v=spf1`. DMARC is read from `_dmarc.<domain>`. Each is reported as present or missing.

There are two entry points:

- `mini_graph` prints the result as a networkx graph in text form, and can write the same graph to an HTML file with pyvis.
- `project.py` runs the same lookup through `maltego-trx`, either as a local transform or as an HTTP transform server. The input entity type is `maltego.Domain`. The outputs are `maltego.IPv4Address` and `maltego.MXRecord`.

## Installation

From the project root:

```text
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Usage

Graph tool:

```text
.\venv\Scripts\python.exe -m mini_graph example.com
.\venv\Scripts\python.exe -m mini_graph example.com 1
.\venv\Scripts\python.exe -m mini_graph example.com --html out.html
```

The second number is the result limit. `--html` writes a standalone HTML file.

Local transform (XML on stdout):

```text
.\venv\Scripts\python.exe project.py local domaintodns example.com
```

HTTP server on this machine only, at `127.0.0.1:8080`:

```text
.\venv\Scripts\python.exe samples\serve_local.py
```

In another terminal:

```text
curl.exe -D - -H "Content-Type: application/xml" --data-binary "@samples/domain_request.xml" http://127.0.0.1:8080/run/domaintodns
```

Stop the server with `Ctrl+C`.

This project uses third-party open-source libraries (maltego-trx, networkx), see NOTICE.md for details, and is not affiliated with any company.

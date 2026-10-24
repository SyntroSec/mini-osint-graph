# mini-osint-graph

Reads DNS A and MX records for a domain name and shows them as a graph.

There are two entry points:

- `mini_graph` prints the result as a networkx graph in text form.
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
```

The second number is the result limit.

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

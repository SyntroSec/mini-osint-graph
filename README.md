# mini-osint-graph

Reads DNS records for one domain and shows them as a graph. `mini_graph` prints that graph as text and can write the same graph to one HTML file. `project.py` runs the A and MX part of the lookup as a local transform or as a small HTTP transform server.

## Features

- **A and MX.** IPv4 addresses and mail servers. An MX priority is printed next to the mail server. A null MX (a mail server of `.`) is not drawn as a node; the tool prints `Null MX for <domain>: the domain does not accept mail.`
- **AAAA.** IPv6 addresses, type `ipv6-address`.
- **NS.** Name servers, type `name-server`.
- **TXT.** Apex TXT strings, type `txt-record`.
- **SPF.** Present when one of those TXT strings starts with `v=spf1`, otherwise missing. The node value is `present` or `missing`.
- **DMARC.** A TXT lookup of `_dmarc.<domain>`. Present when a string starts with `v=dmarc1`, otherwise missing.
- **Text graph.** One domain node, then a line per link: `--A-->`, `--MX-->`, `--AAAA-->`, `--NS-->`, `--TXT-->`, `--SPF-->`, `--DMARC-->`. The last line is a node and edge count. Notes are printed as `[Inform]` or `[PartialError]`.
- **HTML graph.** `--html FILE` writes one HTML file. The page background is `#ffffff`. The script is inlined, so the file does not need a network connection to draw.
- **Result limit.** The optional integer after the domain (default `100`) caps how many A, MX, AAAA, NS, and TXT nodes are added. SPF and DMARC are still added after that cap.
- **Local transform.** `project.py local domaintodns <domain>` prints XML for A and MX only. It does not emit AAAA, NS, TXT, SPF, or DMARC.
- **Local HTTP server.** `samples/serve_local.py` serves that same A/MX transform on `127.0.0.1:8080`.

## Installation

From the project root:

```text
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

This creates the virtual environment and installs the packages listed in `requirements.txt` (`maltego-trx`, `dnspython`, `networkx`, `pyvis`).

The commands below use that environment. Run them from the project root.

## Usage

```text
.\venv\Scripts\python.exe -m mini_graph example.com
```

Looks up `example.com` and prints the text graph. The default limit is 100. Expect a `maltego.Domain` line, indented link lines, a `N nodes, M edges` line, and any `[Inform]` or `[PartialError]` notes.

```text
.\venv\Scripts\python.exe -m mini_graph example.com 1
```

Same lookup, but only the first A, MX, AAAA, NS, or TXT node is kept, in that order. SPF and DMARC are still printed. If more A or MX records existed than the limit allowed, the note is `Result slider truncated the remaining records.`

```text
.\venv\Scripts\python.exe -m mini_graph example.com --html out.html
```

Prints the same text graph, then writes `out.html` and prints `Wrote out.html`. Open that file in a browser. `--html` can sit before or after the domain. A limit still works: `example.com 5 --html out.html`. If `--html` has no path, the program prints `--html needs a file path.` and exits with code 2.

```text
.\venv\Scripts\python.exe -m mini_graph -h
```

Prints `Usage: python -m mini_graph <domain> [limit] [--html FILE]` and exits with code 2. `--help` does the same. A non-integer limit prints `Limit must be an integer.`

```text
.\venv\Scripts\python.exe project.py list
```

Registers the transform and prints two lists: server URLs (`/run/domaintodns/: DomainToDns`) and local names (`domaintodns: DomainToDns`). It also rewrites `transforms.csv`, `settings.csv`, and `local.mtz`.

```text
.\venv\Scripts\python.exe project.py local domaintodns example.com
```

Runs the A/MX transform once. Stdout is a `MaltegoMessage` XML document: one `maltego.IPv4Address` entity per A record, one `maltego.MXRecord` entity per real MX record, and `UIMessage` lines for notes such as a null MX. There is no HTTP server.

```text
.\venv\Scripts\python.exe project.py runserver
```

Starts the transform HTTP server on `0.0.0.0:8080` (every interface, not only this machine). The console lists the same URL `/run/domaintodns/`. Stop it with Ctrl+C. For a server that stays on this machine, use `samples/serve_local.py` instead.

Terminal 1:

```text
.\venv\Scripts\python.exe samples\serve_local.py
```

Imports the project and listens on `127.0.0.1:8080` only. Leave this process running. Flask prints that it is serving that address. This also rewrites `transforms.csv`, `settings.csv`, and `local.mtz`. Stop it with Ctrl+C.

Terminal 2, from the project root:

```text
curl.exe -D - -H "Content-Type: application/xml" --data-binary "@samples/domain_request.xml" http://127.0.0.1:8080/run/domaintodns
```

POSTs the sample domain `example.com` from `samples/domain_request.xml`. Expect `HTTP/1.1 200 OK` and a `MaltegoMessage` body with A records (and MX records when they exist) plus UI messages. This endpoint does not add AAAA, NS, TXT, SPF, or DMARC. The sample request sets `SoftLimit` to 12, so at most 12 of those A/MX entities come back.

### Example output for example.com

Addresses can change between lookups. This is one real run:

```text
maltego.Domain  example.com
  --A-->  maltego.IPv4Address  104.20.23.154
  --A-->  maltego.IPv4Address  172.66.147.243
  --AAAA-->  ipv6-address  2606:4700:10::6814:179a
  --AAAA-->  ipv6-address  2606:4700:10::ac42:93f3
  --NS-->  name-server  hera.ns.cloudflare.com
  --NS-->  name-server  elliott.ns.cloudflare.com
  --TXT-->  txt-record  v=spf1 -all
  --TXT-->  txt-record  _k2n1y4vw3qtb4skdx9e7dxt97qrmmq9
  --SPF-->  spf-result  present
  --DMARC-->  dmarc-result  present
11 nodes, 10 edges
[Inform] Null MX for example.com: the domain does not accept mail.
```

There is no MX node: the mail exchange was `.`, which this project treats as a null MX.

### HTML graph node colors

`mini_graph/html_export.py` does not assign a hex color to each type. It sets the page background to `#ffffff` and sets each node's `group` to its entity type. Nodes are dots. Hover text is the type. For SPF and DMARC, the hover text also includes the record string when one was found. A label longer than 80 characters is cut to 77 characters plus `...` in the HTML only; the text graph still prints the full value.

Because a group is set, pyvis does not apply its fallback node color `#97c2fc` (`pyvis/network.py`, `add_node`). The inlined vis-network 9.1.2 script then colors groups from `_defaultGroups`, in the order each group name first appears. Nodes are added in this order: domain, A, MX, AAAA, NS, TXT, SPF, DMARC. A type that is absent does not take a slot, so later types move up the palette.

Background colors, in that first-seen order:

| Order | Background | Border |
|---|---|---|
| 1 | `#97C2FC` | `#2B7CE9` |
| 2 | `#FFFF00` | `#FFA500` |
| 3 | `#FB7E81` | `#FA0A10` |
| 4 | `#7BE141` | `#41A906` |
| 5 | `#EB7DF4` | `#E129F0` |
| 6 | `#AD85E4` | `#7C29F0` |
| 7 | `#FFA807` | `#C37F00` |
| 8 | `#6E6EFD` | `#4220FB` |

For the `example.com` run above there is no MX node, so the colors are: domain `#97C2FC`, IPv4 `#FFFF00`, IPv6 `#FB7E81`, name server `#7BE141`, TXT `#EB7DF4`, SPF `#AD85E4`, DMARC `#FFA807`. If an MX node is present, it takes `#FB7E81` and the later types each shift one row down.

## How it works

An **entity** is one fact: a type, a value, and optional properties. The starting entity is `maltego.Domain` with the domain you typed. New types used only by `mini_graph` are `ipv6-address`, `name-server`, `txt-record`, `spf-result`, and `dmarc-result`. A and MX keep the names `maltego.IPv4Address` and `maltego.MXRecord`.

A **transform** reads one entity and returns new entities plus a link label. It does not draw the graph. `domain_to_dns` does that for the text and HTML tools. `transforms/DomainToDns.py` does it for the local command and the HTTP server, and it returns only A and MX.

A **graph** stores entities as nodes and labels as directed edges. `InvestigationGraph` is a networkx `DiGraph`. The arrow goes from the domain to each record. The same type and value are one node.

DNS queries use this machine's resolver through `dnspython`. A and MX use a 2 second per-try timeout and a 5 second lifetime. AAAA, NS, TXT, and DMARC then use a 5 second timeout and a 20 second lifetime. Those later queries do not replace an A or MX result that already came back.

## Troubleshooting

**DNS timeouts.** A or MX timeout stops the whole lookup. The text output is a `[PartialError]` such as `A: LifetimeTimeout`, and no record nodes are added. A timeout of TXT or DMARC does not remove A or MX. TXT failure prints `TXT lookup failed, so SPF could not be read from TXT records.` and SPF is `missing` because there were no TXT strings to inspect. DMARC failure prints `DMARC lookup failed.` A name that does not exist at `_dmarc.<domain>` is `missing`, not a failed lookup.

**Null MX.** `Null MX for <domain>: the domain does not accept mail.` means the MX answer was `.` (RFC 7505). No `maltego.MXRecord` node is added. `No MX records for <domain>.` means the server answered and had no MX records at all.

**SPF.** `present` means an apex TXT value, ignoring leading space and case, starts with `v=spf1`. Hover the HTML node to see that string. `missing` means the TXT query succeeded and no string matched, or the TXT query failed (see the note above).

**DMARC.** `present` means a TXT record at `_dmarc.<domain>` starts with `v=dmarc1`. `missing` means that query succeeded and no string matched, including when the `_dmarc` name does not exist.

**Other messages.** `Input is not a domain name. Expected a host such as example.com.` means the value was empty, a bare word, or an IPv4 address. `NXDOMAIN: <name> does not exist` means the DNS server says the name is not in the zone. `Result slider truncated the remaining records.` means the limit cut off A or MX records.

## Running tests

```text
.\venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\venv\Scripts\python.exe -m pytest
```

`pytest` is listed in `requirements-dev.txt`, not in `requirements.txt`. The tests mock DNS and do not contact a name server. A finished run prints the pass count and `pytest` exits with code 0.

## Limitations

The tool looks up one hostname. It does not discover subdomains, and it does not query WHOIS. It does not walk name servers for a zone transfer or try a word list. It uses only the DNS servers configured on this machine. The local transform and the HTTP server return A and MX only; AAAA, NS, TXT, SPF, and DMARC are in `mini_graph`.

This project uses third-party open-source libraries (maltego-trx, networkx, pyvis), see NOTICE.md for details, and is not affiliated with any company.

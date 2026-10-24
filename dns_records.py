"""dns_records.py — shared functions that read A and MX records for a domain.

This file does not know the transform protocol. Two callers use it:
  transforms/DomainToDns.py — turns the result into response XML
  mini_graph — turns the result into a networkx graph

The query goes to this machine's own DNS resolver. There is no zone transfer and no name list.
"""

import re
from urllib.parse import urlparse

import dns.exception
import dns.resolver

# A hostname with at least one dot and labels made of letters or digits.
# A single word ("localhost") and text with spaces are rejected.
_HOSTNAME = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+"
)
_IPV4 = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")


def normalize_domain(raw):
    """Turn an entity value into an ASCII hostname that can be sent to DNS.

    From text such as "https://Example.COM/path", only the host is kept.
    IDN names are converted to punycode. An unusable value returns an empty
    string and no query is sent.
    """
    value = (raw or "").strip().lower()
    if "://" in value:
        value = urlparse(value).hostname or ""
    value = value.split("/")[0].strip().strip(".")
    if value.count(":") == 1 and value.rsplit(":", 1)[-1].isdigit():
        value = value.rsplit(":", 1)[0]

    try:
        value = value.encode("idna").decode("ascii")
    except UnicodeError:
        return ""

    if _IPV4.fullmatch(value):
        return ""
    if not _HOSTNAME.fullmatch(value) or len(value) > 253:
        return ""
    return value


def _query(resolver, hostname, record_type):
    """Query one DNS type.

    Returns (records, no_answer).
    NXDOMAIN is raised here — if the name itself does not exist, querying
    the second type is pointless, and the caller sees that.
    """
    try:
        return list(resolver.resolve(hostname, record_type)), False
    except dns.resolver.NoAnswer:
        return [], True
    except dns.resolver.NXDOMAIN:
        raise
    except dns.exception.DNSException as exc:
        raise RuntimeError(f"{record_type}: {exc.__class__.__name__}") from exc


def lookup_domain(hostname):
    """Read A and MX records from the system DNS resolver.

    Result dictionary:
      addresses — IPv4 strings
      mail_servers — (priority, host) pairs, priority ascending
      notes — short notes (for example, no records of this type)
      error — reason that stops the whole lookup, or None
    """
    resolver = dns.resolver.Resolver()
    resolver.timeout = 2.0
    resolver.lifetime = 5.0

    found = {
        "addresses": [],
        "mail_servers": [],
        "notes": [],
        "error": None,
    }

    try:
        answers, no_answer = _query(resolver, hostname, "A")
    except dns.resolver.NXDOMAIN:
        found["error"] = f"NXDOMAIN: {hostname} does not exist"
        return found
    except RuntimeError as exc:
        found["error"] = str(exc)
        return found

    if no_answer:
        found["notes"].append(f"No A records for {hostname}.")
    else:
        found["addresses"] = list(dict.fromkeys(rr.address for rr in answers))

    try:
        answers, no_answer = _query(resolver, hostname, "MX")
    except dns.resolver.NXDOMAIN:
        found["error"] = f"NXDOMAIN: {hostname} does not exist"
        return found
    except RuntimeError as exc:
        found["error"] = str(exc)
        return found

    if no_answer:
        found["notes"].append(f"No MX records for {hostname}.")
        return found

    mail_servers = []
    null_mx = False
    for record in answers:
        # An MX exchange looks like "host."; the trailing dot must not become the entity value.
        host = str(record.exchange).rstrip(".")
        if not host:
            # RFC 7505: an exchange of "." means the domain does not accept mail.
            null_mx = True
            continue
        mail_servers.append((int(record.preference), host))

    mail_servers.sort(key=lambda item: (item[0], item[1]))
    found["mail_servers"] = list(dict.fromkeys(mail_servers))
    if null_mx and not found["mail_servers"]:
        found["notes"].append(f"Null MX for {hostname}: the domain does not accept mail.")
    return found

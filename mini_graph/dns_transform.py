"""mini_graph/dns_transform.py — A and MX entities from a Domain entity.

The steps match transforms/DomainToDns.py:
  check the domain name, read A and MX, make each record its own entity.
The difference is the shape of the answer. The server transform writes
entities to XML and the client draws the link. This function returns the
entity list and the link label; graph.py adds them to the graph.
"""

import dns.exception
from dns_records import lookup_domain, normalize_domain

from mini_graph.model import Entity, LinkedEntity, Message

# Type names match the transform server's entity identifiers so the two
# tools' graphs can be compared by eye. These constants do not call the library.
DOMAIN = "maltego.Domain"
IPV4 = "maltego.IPv4Address"
MX_RECORD = "maltego.MXRecord"


def domain_to_dns(entity, limit=100):
    """Accept one Domain entity and return a LinkedEntity list plus messages.

    limit is the result slider: stop after this many new entities.
    """
    hostname = normalize_domain(entity.value)
    if not hostname:
        return [], [
            Message(
                "Input is not a domain name. Expected a host such as example.com.",
                "PartialError",
            )
        ]

    try:
        found = lookup_domain(hostname)
    except dns.exception.DNSException as exc:
        return [], [Message(f"DNS lookup failed: {exc.__class__.__name__}", "PartialError")]

    if found["error"]:
        return [], [Message(found["error"], "PartialError")]

    remaining = limit if limit and limit > 0 else 100
    linked = []

    for address in found["addresses"]:
        if remaining <= 0:
            break
        linked.append(
            LinkedEntity(
                Entity(IPV4, address, display=f"A record for {hostname}"),
                "A",
            )
        )
        remaining -= 1

    for preference, mail_host in found["mail_servers"]:
        if remaining <= 0:
            break
        linked.append(
            LinkedEntity(
                Entity(
                    MX_RECORD,
                    mail_host,
                    properties={"priority": str(preference)},
                    display=f"MX {preference} for {hostname}",
                ),
                "MX",
            )
        )
        remaining -= 1

    messages = [Message(note, "Inform") for note in found["notes"]]
    produced = (limit if limit and limit > 0 else 100) - remaining
    total = len(found["addresses"]) + len(found["mail_servers"])
    if produced == 0 and not messages:
        messages.append(Message(f"No A or MX records for {hostname}.", "Inform"))
    elif produced < total:
        messages.append(Message("Result slider truncated the remaining records.", "Inform"))

    return linked, messages

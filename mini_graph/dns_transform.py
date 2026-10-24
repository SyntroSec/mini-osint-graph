"""mini_graph/dns_transform.py — A and MX entities from a Domain entity.

The steps match transforms/DomainToDns.py:
  check the domain name, read A and MX, make each record its own entity.
The difference is the shape of the answer. The server transform writes
entities to XML and the client draws the link. This function returns the
entity list and the link label; graph.py adds them to the graph.
"""

import dns.exception
from dns_records import lookup_domain, normalize_domain

from mini_graph.model import (
    DMARC_RESULT,
    Entity,
    IPV6_ADDRESS,
    LinkedEntity,
    Message,
    NAME_SERVER,
    SPF_RESULT,
    SUBDOMAIN,
    TXT_RECORD,
)
from mini_graph.subdomains import lookup_subdomains

# Type names match the transform server's entity identifiers so the two
# tools' graphs can be compared by eye. These constants do not call the library.
DOMAIN = "maltego.Domain"
IPV4 = "maltego.IPv4Address"
MX_RECORD = "maltego.MXRecord"


def domain_to_dns(entity, limit=100, include_subdomains=False):
    """Accept one Domain entity and return a LinkedEntity list plus messages.

    limit is the result slider: stop after this many new entities.
    include_subdomains asks crt.sh for certificate names. The default is
    off, and that path does not call crt.sh.
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

    for address in found.get("ipv6", []):
        if remaining <= 0:
            break
        linked.append(
            LinkedEntity(
                Entity(IPV6_ADDRESS, address, display=f"AAAA record for {hostname}"),
                "AAAA",
            )
        )
        remaining -= 1

    for nameserver in found.get("nameservers", []):
        if remaining <= 0:
            break
        linked.append(
            LinkedEntity(
                Entity(NAME_SERVER, nameserver, display=f"NS record for {hostname}"),
                "NS",
            )
        )
        remaining -= 1

    for text in found.get("txt", []):
        if remaining <= 0:
            break
        linked.append(
            LinkedEntity(
                Entity(TXT_RECORD, text, display=f"TXT record for {hostname}"),
                "TXT",
            )
        )
        remaining -= 1

    # Subdomain names use the same slider as A, MX, AAAA, NS, and TXT.
    # They are skipped entirely unless the CLI flag asked for them.
    subdomain_failure = None
    if include_subdomains:
        names, reason = lookup_subdomains(hostname)
        if reason:
            subdomain_failure = reason
        for name in names:
            if remaining <= 0:
                break
            linked.append(
                LinkedEntity(
                    Entity(SUBDOMAIN, name, display=f"Subdomain of {hostname}"),
                    "SUBDOMAIN",
                )
            )
            remaining -= 1

    # SPF and DMARC are reported even when the slider has no room left,
    # so a tight limit still says whether each policy is present or missing.
    spf_state = found.get("spf", "missing")
    linked.append(
        LinkedEntity(
            Entity(
                SPF_RESULT,
                spf_state,
                properties={"record": found.get("spf_record", "")},
                display=found.get("spf_record", "") or f"SPF {spf_state} for {hostname}",
            ),
            "SPF",
        )
    )
    dmarc_state = found.get("dmarc", "missing")
    linked.append(
        LinkedEntity(
            Entity(
                DMARC_RESULT,
                dmarc_state,
                properties={"record": found.get("dmarc_record", "")},
                display=found.get("dmarc_record", "") or f"DMARC {dmarc_state} for {hostname}",
            ),
            "DMARC",
        )
    )

    messages = [Message(note, "Inform") for note in found["notes"]]
    if found.get("txt_error"):
        messages.append(Message(
            "TXT lookup failed, so SPF could not be read from TXT records.",
            "Inform",
        ))
    if found.get("dmarc_error"):
        messages.append(Message("DMARC lookup failed.", "Inform"))
    if subdomain_failure:
        messages.append(Message(f"subdomain lookup failed: {subdomain_failure}", "Inform"))
    produced = (limit if limit and limit > 0 else 100) - remaining
    total = len(found["addresses"]) + len(found["mail_servers"])
    if produced == 0 and not messages:
        messages.append(Message(f"No A or MX records for {hostname}.", "Inform"))
    elif produced < total:
        messages.append(Message("Result slider truncated the remaining records.", "Inform"))

    return linked, messages

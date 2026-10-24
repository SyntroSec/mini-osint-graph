"""mini_graph/dns_transform.py — Domain entity-sindən A və MX entity-ləri.

Bu, transforms/DomainToDns.py ilə eyni addımlardır:
  domen adını yoxla, A və MX oxu, hər qeydi ayrı entity et.
Fərq cavabın formasındadır. Server transformu entity-ləri XML-ə yazır
və linki klient çəkir. Bu funksiya entity siyahısını və link yazısını
qaytarır; qrafa əlavə edən graph.py-dir.
"""

import dns.exception
from dns_records import lookup_domain, normalize_domain

from mini_graph.model import Entity, LinkedEntity, Message

# Tip adları transform serverinin entity identifikatorları ilə eynidir ki,
# iki alətin qrafını gözlə müqayisə etmək olsun. Bu sabitlər kitabxananı çağırmır.
DOMAIN = "maltego.Domain"
IPV4 = "maltego.IPv4Address"
MX_RECORD = "maltego.MXRecord"


def domain_to_dns(entity, limit=100):
    """Bir Domain entity-si qəbul edir, LinkedEntity siyahısı və mesajlar qaytarır.

    limit nəticə slider-idir: bu qədər yeni entity-dən sonra dayanır.
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

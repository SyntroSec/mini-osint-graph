"""transforms/DomainToDns.py — DNS A and MX entities from a domain entity.

Flow:
  1. A maltego.Domain node on the graph is given to this transform.
  2. create_entities reads only request.Value (the domain name).
     The DNS query lives in dns_records.py; this file turns the result into entities.
  3. Each A record becomes maltego.IPv4Address, and each MX record becomes maltego.MXRecord.
  4. The transform does not draw the graph. The graph client links every returned
     entity to the input node. The link text comes from setLinkLabel.

The file name must be DomainToDns and the class name must be DomainToDns —
maltego-trx finds the transform by that match. Local name: domaintodns.
"""

import dns.exception
from dns_records import lookup_domain, normalize_domain
from extensions import registry
from maltego_trx.entities import IPAddress, MX, Domain
from maltego_trx.maltego import UIM_PARTIAL, UIM_INFORM, MaltegoMsg, MaltegoTransform
from maltego_trx.transform import DiscoverableTransform


@registry.register_transform(
    display_name="Domain to DNS A and MX",
    input_entity=Domain,
    description="Resolve a domain to its DNS A and MX records.",
    output_entities=[IPAddress, MX],
)
class DomainToDns(DiscoverableTransform):
    """Accepts maltego.Domain and returns A and MX entities."""

    @classmethod
    def create_entities(cls, request: MaltegoMsg, response: MaltegoTransform):
        hostname = normalize_domain(request.Value)
        if not hostname:
            response.addUIMessage(
                "Input is not a domain name. Expected a host such as example.com.",
                UIM_PARTIAL,
            )
            return

        try:
            found = lookup_domain(hostname)
        except dns.exception.DNSException as exc:
            response.addUIMessage(f"DNS lookup failed: {exc.__class__.__name__}", UIM_PARTIAL)
            return

        if found["error"]:
            response.addUIMessage(found["error"], UIM_PARTIAL)
            return

        # Slider is the client's result limit. In local mode the library sets it to 100.
        remaining = request.Slider if request.Slider and request.Slider > 0 else 100

        for address in found["addresses"]:
            if remaining <= 0:
                break
            entity = response.addEntity(IPAddress, address)
            entity.setLinkLabel("A")
            entity.addDisplayInformation(f"A record for {hostname}", "DNS")
            remaining -= 1

        for preference, mail_host in found["mail_servers"]:
            if remaining <= 0:
                break
            entity = response.addEntity(MX, mail_host)
            entity.setLinkLabel("MX")
            # Priority is a property: a smaller number means a more preferred mail server.
            entity.addProperty("priority", "MX priority", "strict", str(preference))
            entity.addDisplayInformation(
                f"MX {preference} for {hostname}",
                "DNS",
            )
            remaining -= 1

        for note in found["notes"]:
            response.addUIMessage(note, UIM_INFORM)

        limit = request.Slider if request.Slider and request.Slider > 0 else 100
        produced = limit - remaining
        total = len(found["addresses"]) + len(found["mail_servers"])
        if produced == 0 and not found["notes"]:
            response.addUIMessage(f"No A or MX records for {hostname}.", UIM_INFORM)
        elif produced < total:
            response.addUIMessage("Result slider truncated the remaining records.", UIM_INFORM)

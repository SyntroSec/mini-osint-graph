"""transforms/DomainToDns.py — domen entity-sindən DNS A və MX entity-ləri.

Axın (Addım 1-dəki model):
  1. Qrafdakı bir maltego.Domain düyününü bu transformə verir.
  2. create_entities yalnız request.Value-ni (domen adını) oxuyur.
     DNS sorğusu dns_records.py-dədir; bu fayl nəticəni entity-yə çevirir.
  3. Hər A qeydi maltego.IPv4Address, hər MX qeydi maltego.MXRecord olur.
  4. Transform qraf çəkmir. Qraf klienti qaytarılan hər entity-ni
     giriş düyününə link ilə bağlayır. Linkin yazısı setLinkLabel ilə gəlir.

Fayl adı DomainToDns, sinif adı da DomainToDns olmalıdır — maltego-trx
transformu bu uyğunluqla tapır. Lokal ad: domaintodns.
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
    """maltego.Domain qəbul edir, A və MX entity-ləri qaytarır."""

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

        # Slider klientin nəticə limitidir. Lokal rejimdə kitabxana onu 100 yazır.
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
            # Prioritet property-dir: kiçik rəqəm daha üstün mail server deməkdir.
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

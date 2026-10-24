"""mini_graph/rdap.py — registration and IP network data from public RDAP.

rdap.org is a bootstrap service. It redirects to the registry that publishes
the domain or the address block. This module reads the registrar, the
registration dates, status values, and the network block.

It does not read registrant, email, phone, or address fields. Nested
contact cards under an entity are ignored.
"""

import requests

USER_AGENT = "mini-osint-graph"
MAX_IP_LOOKUPS = 10
_TIMEOUT_SECONDS = 10


def lookup_domain(domain):
    """Return (info, reason) for one domain name.

    info is None when the request fails. reason is None on success.
    """
    payload, reason = _get_json(f"https://rdap.org/domain/{domain}")
    if reason:
        return None, reason
    return parse_domain(payload), None


def lookup_ip(address):
    """Return (info, reason) for one IP address that DNS already found."""
    payload, reason = _get_json(f"https://rdap.org/ip/{address}")
    if reason:
        return None, reason
    return parse_ip(payload), None


def parse_domain(payload):
    """Pull registrar, dates, and status from one domain object.

    The returned dict has no contact card. last_changed is the domain's
    "last changed" event, not the RDAP database timestamp.
    """
    return {
        "registrar": _registrar_name(payload),
        "registered": _event_date(payload, "registration"),
        "expires": _event_date(payload, "expiration"),
        "last_changed": _event_date(payload, "last changed"),
        "status": _status_values(payload),
    }


def parse_ip(payload):
    """Pull the network name, country, and address range from one IP object."""
    name = _text(payload.get("name")) or _text(payload.get("handle"))
    country = _text(payload.get("country"))
    start = _text(payload.get("startAddress"))
    end = _text(payload.get("endAddress"))
    cidrs = []
    for item in payload.get("cidr0_cidrs") or []:
        if not isinstance(item, dict):
            continue
        prefix = item.get("v4prefix") or item.get("v6prefix")
        length = item.get("length")
        if prefix and length is not None:
            cidrs.append(f"{prefix}/{length}")
    # Country makes the usual "NAME (CC)" label. Without it, the same
    # operator name would collapse different blocks into one node.
    if name and country:
        label = f"{name} ({country})"
    elif name and cidrs:
        label = f"{name} ({', '.join(cidrs)})"
    elif name and start and end:
        label = f"{name} ({start}-{end})"
    else:
        label = name
    return {
        "name": name,
        "country": country,
        "start": start,
        "end": end,
        "cidr": ", ".join(cidrs),
        "label": label,
    }


def _get_json(url):
    """GET one RDAP URL. Failures return (None, reason) and do not raise."""
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
    except requests.Timeout:
        return None, "timeout"
    except requests.RequestException as exc:
        return None, exc.__class__.__name__

    if response.status_code >= 400:
        return None, f"HTTP {response.status_code}"

    try:
        payload = response.json()
    except ValueError:
        return None, "invalid JSON"
    if not isinstance(payload, dict):
        return None, "invalid JSON"
    return payload, None


def _registrar_name(payload):
    """Name of the entity whose role is registrar. Other roles are skipped."""
    for entity in payload.get("entities") or []:
        if not isinstance(entity, dict):
            continue
        roles = [str(role).strip().lower() for role in entity.get("roles") or []]
        if "registrar" not in roles:
            continue
        name = _vcard_fn(entity)
        if name:
            return name
    return ""


def _vcard_fn(entity):
    """Return the formatted name, and nothing else from the vCard."""
    vcard = entity.get("vcardArray")
    if not isinstance(vcard, list) or len(vcard) < 2 or not isinstance(vcard[1], list):
        return ""
    for item in vcard[1]:
        if isinstance(item, list) and len(item) >= 4 and item[0] == "fn" and isinstance(item[3], str):
            return item[3].strip()
    return ""


def _event_date(payload, action):
    for event in payload.get("events") or []:
        if not isinstance(event, dict):
            continue
        if str(event.get("eventAction", "")).strip().lower() != action:
            continue
        return _text(event.get("eventDate"))
    return ""


def _status_values(payload):
    values = []
    for item in payload.get("status") or []:
        text = _text(item)
        if text:
            values.append(text)
    return values


def _text(value):
    if isinstance(value, str):
        return value.strip()
    return ""

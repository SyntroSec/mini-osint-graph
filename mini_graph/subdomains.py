"""mini_graph/subdomains.py — passive subdomain names from crt.sh.

crt.sh searches Certificate Transparency logs. The query %.domain
asks for names that appeared on a certificate for that domain.
This module does not resolve those names and does not try a word list.
"""

import requests

# Identifies this tool to the crt.sh service.
USER_AGENT = "mini-osint-graph"
_TIMEOUT_SECONDS = 15


def lookup_subdomains(domain):
    """Return (names, reason).

    names is a sorted list of subdomains. reason is None on success.
    On HTTP failure, timeout, or invalid JSON, names is empty and reason
    is a short string. The caller keeps the DNS records either way.
    """
    url = f"https://crt.sh/?q=%25.{domain}&output=json"
    try:
        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=_TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        return [], "timeout"
    except requests.RequestException as exc:
        return [], exc.__class__.__name__

    if response.status_code >= 400:
        return [], f"HTTP {response.status_code}"

    try:
        payload = response.json()
    except ValueError:
        return [], "invalid JSON"

    if not isinstance(payload, list):
        return [], "invalid JSON"
    return clean_names(payload, domain), None


def clean_names(records, domain):
    """Turn crt.sh rows into unique subdomain names.

    name_value may contain several names separated by newlines.
    Wildcards, the domain itself, and names outside that domain are dropped.
    """
    domain = domain.lower().rstrip(".")
    suffix = "." + domain
    found = set()
    for record in records:
        if not isinstance(record, dict):
            continue
        raw = record.get("name_value") or ""
        for line in str(raw).splitlines():
            name = line.strip().lower().rstrip(".")
            if not name or "*" in name or name == domain:
                continue
            if not name.endswith(suffix):
                continue
            found.add(name)
    return sorted(found)

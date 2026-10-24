"""dns_records.py — domen adından A və MX qeydlərini oxuyan ortaq funksiyalar.

Bu fayl transform protokolunu bilmir. Onu iki yer çağırır:
  transforms/DomainToDns.py — nəticəni cavab XML-inə çevirir
  mini_graph — nəticəni networkx qrafına çevirir

Sorğu bu maşının öz DNS həlledicisinə gedir. Zona köçürməsi və ad siyahısı yoxdur.
"""

import re
from urllib.parse import urlparse

import dns.exception
import dns.resolver

# Ən azı bir nöqtəli, hər etiketi hərf/rəqəm olan host adı.
# Tək söz ("localhost") və boşluqlu mətn buraxılmır.
_HOSTNAME = re.compile(
    r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)+"
)
_IPV4 = re.compile(r"\d{1,3}(?:\.\d{1,3}){3}")


def normalize_domain(raw):
    """Entity dəyərini DNS-ə verilə bilən ASCII host adına çevirir.

    "https://Example.COM/path" kimi mətndən yalnız host götürülür.
    IDN adlar punycode-a çevrilir. Yararsız dəyərdə boş sətir qayıdır
    və heç bir sorğu getmir.
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
    """Bir DNS tipini sorğulayır.

    Qayıdış: (qeydlər, qeyd_yoxdur).
    NXDOMAIN buradan xüsusi çıxır — adın özü yoxdursa ikinci tipi
    sorğulamağın mənası yoxdur, onu çağıran görür.
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
    """Sistem DNS həlledicisindən A və MX oxuyur.

    Nəticə lüğəti:
      addresses — IPv4 sətirləri
      mail_servers — (prioritet, host) cütləri, prioritet artan sırada
      notes — qısa məlumatlar (məsələn bu tipdə qeyd yoxdur)
      error — bütün sorğunu dayandıran səbəb, yoxdursa None
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
        # MX exchange "host." formasındadır; son nöqtə entity dəyərinə düşməməlidir.
        host = str(record.exchange).rstrip(".")
        if not host:
            # RFC 7505: exchange "." deməkdir — domen poçt qəbul etmir.
            null_mx = True
            continue
        mail_servers.append((int(record.preference), host))

    mail_servers.sort(key=lambda item: (item[0], item[1]))
    found["mail_servers"] = list(dict.fromkeys(mail_servers))
    if null_mx and not found["mail_servers"]:
        found["notes"].append(f"Null MX for {hostname}: the domain does not accept mail.")
    return found

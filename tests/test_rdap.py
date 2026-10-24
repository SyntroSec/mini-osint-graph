"""Offline tests for RDAP lookups. HTTP is mocked."""

import requests
import pytest

from mini_graph.__main__ import _parse_args, main
from mini_graph.dns_transform import DOMAIN, domain_to_dns
from mini_graph.graph import InvestigationGraph
from mini_graph.html_export import write_html
from mini_graph.model import Entity
from mini_graph.rdap import parse_domain, parse_ip
from tests.fakes import RR, patch_dns

HOST = "example.com"
REGISTRAR_NAME = "Example Registrar LLC"
REGISTERED = "1995-08-14T04:00:00Z"
EXPIRES = "2026-08-13T04:00:00Z"
CHANGED = "2024-08-14T07:01:38Z"
SECRETS = (
    "Ada Private",
    "ada.private@example.test",
    "+1-555-0100",
    "123 Secret Street",
)


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _domain_payload():
    return {
        "ldhName": HOST,
        "status": ["client delete prohibited", "client transfer prohibited"],
        "events": [
            {"eventAction": "registration", "eventDate": REGISTERED, "eventActor": "Ada Private"},
            {"eventAction": "expiration", "eventDate": EXPIRES},
            {"eventAction": "last changed", "eventDate": CHANGED},
            {"eventAction": "last update of RDAP database", "eventDate": "2099-01-01T00:00:00Z"},
        ],
        "entities": [
            {
                "roles": ["registrar"],
                "vcardArray": [
                    "vcard",
                    [
                        ["fn", {}, "text", REGISTRAR_NAME],
                        ["email", {}, "text", "ada.private@example.test"],
                        ["tel", {}, "text", "+1-555-0100"],
                        ["adr", {}, "text", "123 Secret Street"],
                    ],
                ],
                "entities": [
                    {
                        "roles": ["abuse"],
                        "vcardArray": ["vcard", [["fn", {}, "text", "Ada Private"]]],
                    }
                ],
            },
            {
                "roles": ["registrant"],
                "vcardArray": [
                    "vcard",
                    [
                        ["fn", {}, "text", "Ada Private"],
                        ["email", {}, "text", "ada.private@example.test"],
                        ["tel", {}, "text", "+1-555-0100"],
                        ["adr", {}, "text", "123 Secret Street"],
                    ],
                ],
            },
        ],
        "remarks": [{"description": ["Ada Private lives at 123 Secret Street"]}],
    }


def _ip_payload():
    return {
        "name": "TEST-NET-1",
        "country": "US",
        "startAddress": "203.0.113.0",
        "endAddress": "203.0.113.255",
        "cidr0_cidrs": [{"v4prefix": "203.0.113.0", "length": 24}],
        "entities": [
            {
                "roles": ["registrant"],
                "vcardArray": [
                    "vcard",
                    [
                        ["fn", {}, "text", "Ada Private"],
                        ["email", {}, "text", "ada.private@example.test"],
                    ],
                ],
            }
        ],
        "remarks": [{"description": ["123 Secret Street", "+1-555-0100"]}],
    }


def _patch_rdap(monkeypatch, domain_status=200, domain_payload=None, domain_error=None, ip_status=200, ip_payload=None, ip_error=None):
    calls = []

    def fake_get(url, headers=None, timeout=None, allow_redirects=None):
        assert headers["User-Agent"] == "mini-osint-graph"
        assert timeout == 10
        assert allow_redirects is True
        calls.append(url)
        if "/domain/" in url:
            if domain_error is not None:
                raise domain_error
            return _Response(domain_status, {} if domain_payload is None else domain_payload)
        if ip_error is not None:
            raise ip_error
        return _Response(ip_status, _ip_payload() if ip_payload is None else ip_payload)

    monkeypatch.setattr("mini_graph.rdap.requests.get", fake_get)
    return calls


def _dns(monkeypatch, addresses=None, ipv6=None):
    patch_dns(
        monkeypatch,
        {
            (HOST, "A"): [RR(address=item) for item in (addresses or ["203.0.113.10"])],
            (HOST, "MX"): [RR(preference=10, exchange="mail.example.com.")],
            (HOST, "AAAA"): [RR(address=item) for item in (ipv6 or [])],
        },
    )


def _texts_from(linked, messages):
    chunks = [message.text for message in messages]
    for item in linked:
        chunks.append(item.entity.value)
        chunks.append(item.entity.display)
        chunks.extend(str(value) for value in item.entity.properties.values())
    return "\n".join(chunks)


def test_parse_domain_response():
    parsed = parse_domain(_domain_payload())

    assert parsed["registrar"] == REGISTRAR_NAME
    assert parsed["registered"] == REGISTERED
    assert parsed["expires"] == EXPIRES
    assert parsed["last_changed"] == CHANGED
    assert parsed["status"] == ["client delete prohibited", "client transfer prohibited"]
    assert "2099-01-01T00:00:00Z" not in parsed.values()


def test_parse_ip_response():
    parsed = parse_ip(_ip_payload())

    assert parsed["label"] == "TEST-NET-1 (US)"
    assert parsed["name"] == "TEST-NET-1"
    assert parsed["country"] == "US"
    assert parsed["start"] == "203.0.113.0"
    assert parsed["end"] == "203.0.113.255"
    assert parsed["cidr"] == "203.0.113.0/24"

    v6 = parse_ip({"name": "DOC-NET", "country": "US", "cidr0_cidrs": [{"v6prefix": "2001:db8::", "length": 32}]})
    assert v6["cidr"] == "2001:db8::/32"
    assert v6["label"] == "DOC-NET (US)"

    same_name = parse_ip(
        {
            "name": "CLOUDFLARENET",
            "startAddress": "172.64.0.0",
            "endAddress": "172.71.255.255",
            "cidr0_cidrs": [{"v4prefix": "172.64.0.0", "length": 13}],
        }
    )
    assert same_name["label"] == "CLOUDFLARENET (172.64.0.0/13)"
    assert same_name["label"] != v6["label"]


def test_personal_data_is_never_output(monkeypatch, tmp_path):
    _dns(monkeypatch)
    _patch_rdap(monkeypatch, domain_payload=_domain_payload())

    graph = InvestigationGraph()
    seed = graph.add_seed(DOMAIN, HOST)
    messages = graph.run_transform(seed, lambda entity, limit=100: domain_to_dns(entity, limit=limit, include_rdap=True))
    rendered = graph.render()
    html_path = tmp_path / "rdap.html"
    write_html(graph, html_path)
    html = html_path.read_text(encoding="utf-8")

    assert REGISTRAR_NAME in rendered
    assert "TEST-NET-1 (US)" in rendered
    for secret in SECRETS:
        assert secret not in rendered
        assert secret not in html
        assert secret not in "\n".join(message.text for message in messages)


@pytest.mark.parametrize(
    ("status", "payload", "error", "reason"),
    [
        (404, {}, None, "HTTP 404"),
        (429, {}, None, "HTTP 429"),
        (503, {}, None, "HTTP 503"),
        (200, {}, requests.Timeout("timed out"), "timeout"),
        (200, ValueError("Expecting value"), None, "invalid JSON"),
        (200, ["not-an-object"], None, "invalid JSON"),
    ],
)
def test_domain_rdap_failure_keeps_dns(monkeypatch, status, payload, error, reason):
    _dns(monkeypatch)
    _patch_rdap(monkeypatch, domain_status=status, domain_payload=payload, domain_error=error)

    linked, messages = domain_to_dns(Entity(DOMAIN, HOST), include_rdap=True)
    labels = [(item.link_label, item.entity.value) for item in linked]

    assert ("A", "203.0.113.10") in labels
    assert ("MX", "mail.example.com") in labels
    assert ("NETWORK", "TEST-NET-1 (US)") in labels
    assert any(message.text == f"RDAP lookup failed for {HOST}: {reason}" for message in messages)
    for secret in SECRETS:
        assert secret not in _texts_from(linked, messages)


def test_ip_lookup_cap(monkeypatch):
    addresses = [f"203.0.113.{index}" for index in range(1, 9)]
    ipv6 = [f"2001:db8::{index}" for index in range(1, 5)]
    _dns(monkeypatch, addresses=addresses, ipv6=ipv6)
    calls = _patch_rdap(monkeypatch, domain_payload=_domain_payload())

    graph = InvestigationGraph()
    seed = graph.add_seed(DOMAIN, HOST)
    graph.run_transform(seed, lambda entity, limit=100: domain_to_dns(entity, limit=limit, include_rdap=True))

    ip_calls = [url for url in calls if "/ip/" in url]
    assert calls[0] == "https://rdap.org/domain/example.com"
    assert len(ip_calls) == 10
    assert ip_calls[:8] == [f"https://rdap.org/ip/{address}" for address in addresses]
    assert ip_calls[8:] == ["https://rdap.org/ip/2001:db8::1", "https://rdap.org/ip/2001:db8::2"]
    assert "https://rdap.org/ip/2001:db8::3" not in calls
    assert "https://rdap.org/ip/2001:db8::4" not in calls

    for address in addresses:
        assert graph.graph.out_degree(f"maltego.IPv4Address|{address}") == 1
    assert graph.graph.out_degree("ipv6-address|2001:db8::1") == 1
    assert graph.graph.out_degree("ipv6-address|2001:db8::2") == 1
    assert graph.graph.out_degree("ipv6-address|2001:db8::3") == 0
    assert graph.graph.out_degree("ipv6-address|2001:db8::4") == 0
    rendered = graph.render()
    assert "    --NETWORK-->  network  TEST-NET-1 (US)  cidr=203.0.113.0/24" in rendered
    assert "--REGISTRAR-->  registrar  Example Registrar LLC" in rendered
    assert f"status=client delete prohibited, client transfer prohibited  changed={CHANGED}" in rendered


def test_cli_rdap_with_subdomains_and_html(monkeypatch, capsys, tmp_path):
    _dns(monkeypatch)

    def fake_get(url, headers=None, timeout=None, allow_redirects=None):
        if "crt.sh" in url:
            return _Response(200, [{"name_value": "www.example.com\nexample.com"}])
        assert headers["User-Agent"] == "mini-osint-graph"
        assert timeout == 10
        assert allow_redirects is True
        if "/domain/" in url:
            return _Response(200, _domain_payload())
        return _Response(200, _ip_payload())

    # rdap.py and subdomains.py share the requests module, so one stub serves both.
    monkeypatch.setattr("mini_graph.rdap.requests.get", fake_get)

    assert _parse_args(["example.com", "--rdap"]) == (HOST, 100, None, False, True)
    assert _parse_args(["--subdomains", "example.com", "--rdap", "--html", "out.html"]) == (
        HOST,
        100,
        "out.html",
        True,
        True,
    )

    html_path = tmp_path / "both.html"
    assert main([HOST, "--rdap", "--subdomains", "--html", str(html_path)]) == 0
    output = capsys.readouterr().out
    assert "--REGISTRAR-->  registrar  Example Registrar LLC" in output
    assert "--REGISTERED-->  registration-date  1995-08-14T04:00:00Z" in output
    assert "--EXPIRES-->  expiration-date  2026-08-13T04:00:00Z" in output
    assert "--SUBDOMAIN-->  subdomain  www.example.com" in output
    assert "--NETWORK-->  network  TEST-NET-1 (US)" in output
    html = html_path.read_text(encoding="utf-8")
    assert REGISTRAR_NAME in html
    assert "TEST-NET-1 (US)" in html
    assert "www.example.com" in html
    for secret in SECRETS:
        assert secret not in output
        assert secret not in html


def test_without_flag_does_not_query_rdap(monkeypatch, capsys):
    _dns(monkeypatch)

    def fail_if_called(url, headers=None, timeout=None, allow_redirects=None):
        raise AssertionError("RDAP must not be queried without --rdap")

    monkeypatch.setattr("mini_graph.rdap.requests.get", fail_if_called)

    assert main([HOST]) == 0
    output = capsys.readouterr().out
    assert "REGISTRAR" not in output
    assert "NETWORK" not in output

"""Offline tests for DNS record parsing."""

import dns.resolver

from dns_records import lookup_domain
from tests.fakes import RR, patch_dns

HOST = "example.com"


def _answers(extra=None):
    base = {
        (HOST, "A"): [RR(address="203.0.113.10")],
        (HOST, "MX"): [RR(preference=10, exchange="mail.example.com.")],
    }
    if extra:
        base.update(extra)
    return base


def test_a_and_mx_parsing(monkeypatch):
    patch_dns(
        monkeypatch,
        _answers(
            {
                (HOST, "A"): [
                    RR(address="203.0.113.10"),
                    RR(address="203.0.113.10"),
                    RR(address="203.0.113.20"),
                ],
                (HOST, "MX"): [
                    RR(preference=20, exchange="backup.example.com."),
                    RR(preference=10, exchange="mail.example.com."),
                ],
            }
        ),
    )

    found = lookup_domain(HOST)

    assert found["error"] is None
    assert found["addresses"] == ["203.0.113.10", "203.0.113.20"]
    assert found["mail_servers"] == [
        (10, "mail.example.com"),
        (20, "backup.example.com"),
    ]


def test_null_mx(monkeypatch):
    patch_dns(monkeypatch, _answers({(HOST, "MX"): [RR(preference=0, exchange=".")]}))

    found = lookup_domain(HOST)

    assert found["mail_servers"] == []
    assert found["notes"] == [f"Null MX for {HOST}: the domain does not accept mail."]


def test_aaaa_ns_and_txt_parsing(monkeypatch):
    patch_dns(
        monkeypatch,
        _answers(
            {
                (HOST, "AAAA"): [RR(address="2001:db8::1"), RR(address="2001:db8::1")],
                (HOST, "NS"): [RR(target="ns2.example.com."), RR(target="ns1.example.com.")],
                (HOST, "TXT"): [RR(strings=[b"hello ", b"world"])],
            }
        ),
    )

    found = lookup_domain(HOST)

    assert found["ipv6"] == ["2001:db8::1"]
    assert found["nameservers"] == ["ns2.example.com", "ns1.example.com"]
    assert found["txt"] == ["hello world"]


def test_spf_present_and_missing(monkeypatch):
    patch_dns(
        monkeypatch,
        _answers({(HOST, "TXT"): [RR(strings=[b"  V=Spf1 -all"]), RR(strings=[b"other"])]}),
    )
    present = lookup_domain(HOST)
    assert present["spf"] == "present"
    assert present["spf_record"] == "  V=Spf1 -all"

    patch_dns(
        monkeypatch,
        _answers({(HOST, "TXT"): [RR(strings=[b"google-site-verification=abc"])]}),
    )
    missing = lookup_domain(HOST)
    assert missing["spf"] == "missing"
    assert missing["spf_record"] == ""
    assert missing["txt_error"] is False


def test_dmarc_present(monkeypatch):
    patch_dns(
        monkeypatch,
        _answers({(f"_dmarc.{HOST}", "TXT"): [RR(strings=[b"V=DMARC1; p=none"])]}),
    )

    found = lookup_domain(HOST)

    assert found["dmarc"] == "present"
    assert found["dmarc_record"] == "V=DMARC1; p=none"
    assert found["dmarc_error"] is False


def test_dmarc_missing_when_name_does_not_exist(monkeypatch):
    def resolve(self, qname, rdtype):
        name = str(qname).rstrip(".")
        if name == f"_dmarc.{HOST}" and rdtype == "TXT":
            raise dns.resolver.NXDOMAIN()
        if (name, rdtype) == (HOST, "A"):
            return [RR(address="203.0.113.10")]
        if (name, rdtype) == (HOST, "MX"):
            return [RR(preference=10, exchange="mail.example.com.")]
        raise dns.resolver.NoAnswer()

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", resolve)

    found = lookup_domain(HOST)

    assert found["addresses"] == ["203.0.113.10"]
    assert found["dmarc"] == "missing"
    assert found["dmarc_error"] is False

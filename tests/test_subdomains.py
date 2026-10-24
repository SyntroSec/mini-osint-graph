"""Offline tests for passive subdomain discovery. HTTP is mocked."""

import requests

from mini_graph.__main__ import _parse_args, main
from mini_graph.dns_transform import DOMAIN, domain_to_dns
from mini_graph.model import Entity
from mini_graph.subdomains import clean_names, lookup_subdomains
from tests.fakes import RR, patch_dns

HOST = "example.com"


class _Response:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def _patch_http(monkeypatch, status_code=200, payload=None, error=None):
    def fake_get(url, headers=None, timeout=None):
        assert url == "https://crt.sh/?q=%25.example.com&output=json"
        assert headers["User-Agent"] == "mini-osint-graph"
        assert timeout == 15
        if error is not None:
            raise error
        return _Response(status_code, payload)

    monkeypatch.setattr("mini_graph.subdomains.requests.get", fake_get)


def _entity():
    return Entity(DOMAIN, HOST)


def _labels(linked):
    return [(item.link_label, item.entity.value) for item in linked]


def test_parsing_splits_sorts_and_lowercases():
    names = clean_names(
        [{"name_value": "WWW.Example.COM\r\napi.example.com\n"}],
        HOST,
    )
    assert names == ["api.example.com", "www.example.com"]


def test_wildcard_removal():
    names = clean_names(
        [{"name_value": "*.example.com\n*.cdn.example.com\nwww.example.com"}],
        HOST,
    )
    assert names == ["www.example.com"]


def test_dedupe():
    names = clean_names(
        [
            {"name_value": "www.example.com"},
            {"name_value": "WWW.EXAMPLE.COM\nwww.example.com"},
        ],
        HOST,
    )
    assert names == ["www.example.com"]


def test_foreign_domain_filtering():
    names = clean_names(
        [
            {
                "name_value": "\n".join(
                    [
                        "example.com",
                        "www.example.com",
                        "notexample.com",
                        "example.com.evil.com",
                        "www.example.com.evil.com",
                        "other.com",
                    ]
                )
            }
        ],
        HOST,
    )
    assert names == ["www.example.com"]


def test_http_error_keeps_dns_records(monkeypatch):
    patch_dns(
        monkeypatch,
        {
            (HOST, "A"): [RR(address="203.0.113.10")],
            (HOST, "MX"): [RR(preference=10, exchange="mail.example.com.")],
        },
    )
    _patch_http(monkeypatch, status_code=503, payload=[])

    linked, messages = domain_to_dns(_entity(), include_subdomains=True)

    assert ("A", "203.0.113.10") in _labels(linked)
    assert ("MX", "mail.example.com") in _labels(linked)
    assert ("SUBDOMAIN", "www.example.com") not in _labels(linked)
    assert any(
        message.kind == "Inform" and message.text == "subdomain lookup failed: HTTP 503"
        for message in messages
    )
    assert lookup_subdomains(HOST) == ([], "HTTP 503")


def test_timeout(monkeypatch):
    _patch_http(monkeypatch, error=requests.Timeout("timed out"))
    assert lookup_subdomains(HOST) == ([], "timeout")


def test_invalid_json(monkeypatch):
    _patch_http(monkeypatch, payload=ValueError("Expecting value"))
    assert lookup_subdomains(HOST) == ([], "invalid JSON")

    _patch_http(monkeypatch, payload={"error": "not a list"})
    assert lookup_subdomains(HOST) == ([], "invalid JSON")


def test_cli_subdomains_flag(monkeypatch, capsys, tmp_path):
    patch_dns(
        monkeypatch,
        {
            (HOST, "A"): [RR(address="203.0.113.10")],
            (HOST, "MX"): [RR(preference=10, exchange="mail.example.com.")],
        },
    )
    _patch_http(monkeypatch, payload=[{"name_value": "www.example.com\nexample.com"}])

    assert _parse_args(["example.com", "--subdomains"]) == ("example.com", 100, None, True)
    assert _parse_args(["example.com", "5", "--html", "out.html", "--subdomains"]) == (
        "example.com",
        5,
        "out.html",
        True,
    )

    html_path = tmp_path / "graph.html"
    assert main(["example.com", "--subdomains", "--html", str(html_path)]) == 0
    output = capsys.readouterr().out
    assert "--SUBDOMAIN-->  subdomain  www.example.com" in output
    assert f"Wrote {html_path}" in output
    assert "www.example.com" in html_path.read_text(encoding="utf-8")


def test_cli_without_flag_does_not_query_crtsh(monkeypatch, capsys):
    patch_dns(
        monkeypatch,
        {
            (HOST, "A"): [RR(address="203.0.113.10")],
            (HOST, "MX"): [RR(preference=10, exchange="mail.example.com.")],
        },
    )

    def fail_if_called(url, headers=None, timeout=None):
        raise AssertionError("crt.sh must not be queried without --subdomains")

    monkeypatch.setattr("mini_graph.subdomains.requests.get", fail_if_called)

    assert main(["example.com"]) == 0
    assert "SUBDOMAIN" not in capsys.readouterr().out


def test_limit_applies_to_subdomains(monkeypatch):
    patch_dns(
        monkeypatch,
        {
            (HOST, "A"): [RR(address="203.0.113.10")],
            (HOST, "MX"): [RR(preference=10, exchange="mail.example.com.")],
        },
    )
    _patch_http(
        monkeypatch,
        payload=[
            {"name_value": "c.example.com"},
            {"name_value": "a.example.com"},
            {"name_value": "b.example.com"},
        ],
    )

    linked, messages = domain_to_dns(_entity(), limit=3, include_subdomains=True)
    labels = _labels(linked)

    assert ("A", "203.0.113.10") in labels
    assert ("MX", "mail.example.com") in labels
    assert ("SUBDOMAIN", "a.example.com") in labels
    assert ("SUBDOMAIN", "b.example.com") not in labels
    assert ("SUBDOMAIN", "c.example.com") not in labels
    assert ("SPF", "missing") in labels
    assert ("DMARC", "missing") in labels
    assert not any(
        message.text == "Result slider truncated the remaining records."
        for message in messages
    )

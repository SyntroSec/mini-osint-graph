"""Offline tests for the domain transform, including errors and the limit."""

import dns.resolver
import pytest

from mini_graph.dns_transform import DOMAIN, domain_to_dns
from mini_graph.model import Entity
from tests.fakes import RR, patch_dns

HOST = "example.com"


def _entity(value):
    return Entity(DOMAIN, value)


def _basic(**extra):
    answers = {
        (HOST, "A"): [RR(address="203.0.113.10"), RR(address="203.0.113.20")],
        (HOST, "MX"): [RR(preference=10, exchange="mail.example.com.")],
    }
    answers.update(extra)
    return answers


def _labels(linked):
    return [(item.link_label, item.entity.value) for item in linked]


def test_a_or_mx_timeout_stops_the_lookup(monkeypatch):
    for record_type in ("A", "MX"):
        answers = _basic()
        answers[(HOST, record_type)] = dns.resolver.LifetimeTimeout()
        patch_dns(monkeypatch, answers)

        linked, messages = domain_to_dns(_entity(HOST))

        assert linked == []
        assert len(messages) == 1
        assert messages[0].kind == "PartialError"
        assert messages[0].text == f"{record_type}: LifetimeTimeout"


def test_txt_timeout_keeps_a_and_mx(monkeypatch):
    answers = _basic()
    answers[(HOST, "TXT")] = dns.resolver.LifetimeTimeout()
    patch_dns(monkeypatch, answers)

    linked, messages = domain_to_dns(_entity(HOST))
    labels = _labels(linked)

    assert ("A", "203.0.113.10") in labels
    assert ("A", "203.0.113.20") in labels
    assert ("MX", "mail.example.com") in labels
    assert ("SPF", "missing") in labels
    assert any(
        message.kind == "Inform"
        and message.text == "TXT lookup failed, so SPF could not be read from TXT records."
        for message in messages
    )


def test_dmarc_timeout_keeps_a_and_mx(monkeypatch):
    answers = _basic()
    answers[(f"_dmarc.{HOST}", "TXT")] = dns.resolver.LifetimeTimeout()
    patch_dns(monkeypatch, answers)

    linked, messages = domain_to_dns(_entity(HOST))
    labels = _labels(linked)

    assert ("A", "203.0.113.10") in labels
    assert ("MX", "mail.example.com") in labels
    assert ("DMARC", "missing") in labels
    assert any(
        message.kind == "Inform" and message.text == "DMARC lookup failed."
        for message in messages
    )


def test_result_limit_keeps_spf_and_dmarc(monkeypatch):
    patch_dns(monkeypatch, _basic())

    linked, messages = domain_to_dns(_entity(HOST), limit=1)
    labels = _labels(linked)

    assert labels[0] == ("A", "203.0.113.10")
    assert ("A", "203.0.113.20") not in labels
    assert ("MX", "mail.example.com") not in labels
    assert ("SPF", "missing") in labels
    assert ("DMARC", "missing") in labels
    assert any(
        message.text == "Result slider truncated the remaining records."
        for message in messages
    )


@pytest.mark.parametrize("value", ["", "hello", "192.0.2.1"])
def test_invalid_input_does_not_query_dns(monkeypatch, value):
    def resolve(self, qname, rdtype):
        raise AssertionError("invalid input must not query DNS")

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", resolve)

    linked, messages = domain_to_dns(_entity(value))

    assert linked == []
    assert messages[0].kind == "PartialError"
    assert messages[0].text == "Input is not a domain name. Expected a host such as example.com."

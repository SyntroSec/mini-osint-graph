"""Fake DNS answers for offline tests.

Resolver.resolve is replaced, so no test contacts a name server.
"""

import dns.resolver


class RR:
    """A stand-in for one dnspython rdata object."""

    def __init__(self, **fields):
        self.__dict__.update(fields)


def patch_dns(monkeypatch, responses):
    """Make Resolver.resolve return scripted answers.

    A missing name and type raises NoAnswer. An exception value is raised.
    """

    def resolve(self, qname, rdtype):
        key = (str(qname).rstrip("."), rdtype)
        if key not in responses:
            raise dns.resolver.NoAnswer()
        value = responses[key]
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(dns.resolver.Resolver, "resolve", resolve)

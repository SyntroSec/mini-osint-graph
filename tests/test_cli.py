"""Offline tests for command-line parsing."""

from mini_graph.__main__ import _parse_args, main
from tests.fakes import RR, patch_dns


def test_html_option_with_path():
    assert _parse_args(["example.com", "--html", "out.html"]) == ("example.com", 100, "out.html")
    assert _parse_args(["example.com", "5", "--html", "out.html"]) == ("example.com", 5, "out.html")


def test_html_option_without_path(capsys):
    assert _parse_args(["example.com", "--html"]) is None
    assert capsys.readouterr().out.strip() == "--html needs a file path."
    assert main(["example.com", "--html"]) == 2
    assert capsys.readouterr().out.strip() == "--html needs a file path."


def test_non_integer_limit(capsys):
    assert _parse_args(["example.com", "many"]) is None
    assert capsys.readouterr().out.strip() == "Limit must be an integer."
    assert main(["example.com", "many"]) == 2
    assert capsys.readouterr().out.strip() == "Limit must be an integer."


def test_help(capsys):
    assert main(["-h"]) == 2
    assert "Usage: python -m mini_graph <domain> [limit] [--html FILE]" in capsys.readouterr().out
    assert main(["--help"]) == 2


def test_html_run_writes_the_file(monkeypatch, tmp_path, capsys):
    patch_dns(
        monkeypatch,
        {
            ("example.com", "A"): [RR(address="203.0.113.10")],
            ("example.com", "MX"): [RR(preference=10, exchange="mail.example.com.")],
        },
    )
    html_path = tmp_path / "graph.html"

    assert main(["example.com", "--html", str(html_path)]) == 0

    captured = capsys.readouterr().out
    assert f"Wrote {html_path}" in captured
    text = html_path.read_text(encoding="utf-8")
    assert "example.com" in text
    assert "203.0.113.10" in text
    assert "mail.example.com" in text

#!/usr/bin/env python3
"""Validação mecânica mínima de um relatório HTML do Fleet.

Checa apenas propriedades determinísticas: arquivo autocontido, ausência de recursos de
rede, estrutura HTML básica e sintaxe dos scripts inline quando Node estiver disponível.
Não tenta julgar qualidade de research ou correção metodológica.
"""
from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
import tempfile


RESOURCE_ATTRS = {
    "script": "src",
    "img": "src",
    "iframe": "src",
    "source": "src",
    "audio": "src",
    "video": "src",
    "link": "href",
}


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: set[str] = set()
        self.external_resources: list[tuple[str, str]] = []
        self.scripts: list[tuple[dict[str, str], str]] = []
        self._script_attrs: dict[str, str] | None = None
        self._script_buf: list[str] = []

    def handle_starttag(self, tag: str, attrs):
        tag = tag.lower()
        self.tags.add(tag)
        ad = {str(k).lower(): (v or "") for k, v in attrs}
        attr = RESOURCE_ATTRS.get(tag)
        if attr and ad.get(attr):
            value = ad[attr].strip()
            if re.match(r"^(?:https?:)?//", value, re.I):
                self.external_resources.append((f"{tag}.{attr}", value))
        if tag == "script":
            self._script_attrs = ad
            self._script_buf = []

    def handle_data(self, data: str):
        if self._script_attrs is not None:
            self._script_buf.append(data)

    def handle_endtag(self, tag: str):
        if tag.lower() == "script" and self._script_attrs is not None:
            self.scripts.append((self._script_attrs, "".join(self._script_buf)))
            self._script_attrs = None
            self._script_buf = []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("report", type=Path)
    args = ap.parse_args()
    path = args.report
    if not path.is_file():
        raise SystemExit(f"arquivo não encontrado: {path}")

    html = path.read_text(encoding="utf-8")
    parser = ReportParser()
    parser.feed(html)

    errors: list[str] = []
    for tag in ("html", "head", "body"):
        if tag not in parser.tags:
            errors.append(f"tag <{tag}> ausente")
    if parser.external_resources:
        for where, url in parser.external_resources:
            errors.append(f"recurso externo em {where}: {url}")
    if re.search(r"url\(\s*['\"]?(?:https?:)?//", html, re.I):
        errors.append("CSS contém url() externo")
    if re.search(r"\b(?:fetch|XMLHttpRequest|WebSocket)\s*\(", html):
        errors.append("JavaScript contém chamada de rede")

    node = shutil.which("node")
    checked = 0
    if node:
        for i, (attrs, code) in enumerate(parser.scripts, 1):
            typ = attrs.get("type", "").lower()
            if attrs.get("src") or typ in {"application/json", "application/ld+json"} or not code.strip():
                continue
            with tempfile.NamedTemporaryFile("w", suffix=".js", encoding="utf-8", delete=False) as f:
                f.write(code)
                tmp = Path(f.name)
            try:
                proc = subprocess.run([node, "--check", str(tmp)], capture_output=True, text=True, encoding="utf-8")
                checked += 1
                if proc.returncode != 0:
                    errors.append(f"script inline #{i} falhou node --check: {proc.stderr.strip()}")
            finally:
                tmp.unlink(missing_ok=True)

    if errors:
        print("REPORT VALIDATION FAILED")
        for e in errors:
            print(f"- {e}")
        return 1

    suffix = f"; {checked} script(s) inline com sintaxe validada" if node else "; Node indisponível, sintaxe JS não verificada"
    print(f"REPORT VALIDATION OK: {path}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
render_pdf.py — renderizador GENÉRICO Markdown -> PDF com template institucional.

Serve para qualquer documento Markdown do processo (relatório de research, memo, parecer):
  - capa gerada do front-matter YAML (titulo, subtitulo, data, linha_meta, rodape);
  - sumário automático dos títulos H1/H2;
  - tabelas, imagens, blockquotes (caixa de recomendação) estilizados pelo template.css;
  - rodapé com paginação via CSS @page (weasyprint) ou wkhtmltopdf (fallback);
  - zero tokens de agente: tudo é código + CSS fixo.

Uso:
  python render_pdf.py documento.md [--out saida.pdf] [--css template.css]

Dependências: markdown (pip), weasyprint (preferido) OU wkhtmltopdf no PATH.
"""
import argparse
import os
import re
import sys
import unicodedata


def _slug(txt, sep="-"):
    s = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", sep, s.lower()).strip(sep)


def separar_front_matter(md):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", md, re.S)
    if not m:
        return {}, md
    try:
        import yaml
        return (yaml.safe_load(m.group(1)) or {}), m.group(2)
    except Exception:
        return {}, md


def _normalizar_listas(md):
    """Insere linha em branco antes de item de lista que segue texto corrido
    (CommonMark exige; autores nem sempre respeitam). Preserva código e tabelas."""
    out, dentro_code = [], False
    for ln in md.splitlines():
        if ln.strip().startswith("```"):
            dentro_code = not dentro_code
        eh_item = re.match(r"^\s*(\d+\.|[-*])\s+", ln)
        if (not dentro_code and eh_item and out and out[-1].strip()
                and not re.match(r"^\s*(\d+\.|[-*])\s+", out[-1])
                and not out[-1].strip().startswith(("|", "#"))):
            out.append("")
        out.append(ln)
    return "\n".join(out)


def montar_html(md_texto, fm, base_dir):
    import markdown
    md_texto = _normalizar_listas(md_texto)
    corpo = markdown.markdown(md_texto, extensions=["tables", "attr_list", "sane_lists", "toc"],
                              extension_configs={"toc": {"slugify": _slug, "toc_depth": "1-2"}})
    # sumário próprio (H1/H2), com âncoras do toc extension
    itens = re.findall(r"<h([12]) id=\"([^\"]+)\">(.*?)</h\1>", corpo)
    toc = "\n".join(
        f'<div class="toc{nivel}"><a href="#{anchor}">{re.sub("<[^>]+>", "", titulo)}</a></div>'
        for nivel, anchor, titulo in itens)
    capa = f"""
    <div class="capa">
      <div class="capa-marca">{fm.get('rodape', '')}</div>
      <h1 class="capa-titulo">{fm.get('titulo', '')}</h1>
      <div class="capa-sub">{fm.get('subtitulo', '')}</div>
      <div class="capa-meta">{fm.get('linha_meta', '')}</div>
      <div class="capa-data">{fm.get('data', '')}</div>
    </div>
    <div class="sumario"><h1>Sumário</h1>{toc}</div>
    <div class="quebra"></div>
    """
    return f"""<!DOCTYPE html><html lang="pt-BR"><head><meta charset="utf-8">
<title>{fm.get('titulo', 'Documento')}</title></head>
<body>{capa}{corpo}</body></html>""", base_dir


def render(md_path, out_path, css_path):
    md = open(md_path, encoding="utf-8").read()
    fm, corpo = separar_front_matter(md)
    base_dir = os.path.dirname(os.path.abspath(md_path)) or "."
    html, base = montar_html(corpo, fm, base_dir)
    css = open(css_path, encoding="utf-8").read()
    # injeta rodapé dinâmico no CSS (@page) com o texto do front-matter
    css = css.replace("__RODAPE__", str(fm.get("rodape", "")).replace('"', "'"))
    html = html.replace("</head>", f"<style>{css}</style></head>")
    try:
        from weasyprint import HTML
        HTML(string=html, base_url=base).write_pdf(out_path)
        motor = "weasyprint"
    except ImportError:
        import subprocess, tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False,
                                         dir=base, encoding="utf-8") as fh:
            fh.write(html)
            tmp = fh.name
        rodape = str(fm.get("rodape", ""))
        subprocess.run(["wkhtmltopdf", "--enable-local-file-access", "--quiet",
                        "--footer-left", rodape, "--footer-right", "[page]/[topage]",
                        "--footer-font-size", "8", tmp, out_path], check=True)
        os.unlink(tmp)
        motor = "wkhtmltopdf"
    paginas = "?"
    try:
        from pypdf import PdfReader
        paginas = len(PdfReader(out_path).pages)
    except Exception:
        pass
    print(f"[render_pdf] {out_path} gerado ({motor}, {paginas} páginas)")
    return out_path


def main():
    ap = argparse.ArgumentParser(description="Markdown -> PDF institucional")
    ap.add_argument("md")
    ap.add_argument("--out", default=None)
    ap.add_argument("--css", default=None)
    args = ap.parse_args()
    out = args.out or os.path.splitext(args.md)[0] + ".pdf"
    css = args.css or os.path.join(os.path.dirname(os.path.abspath(__file__)), "template.css")
    render(args.md, out, css)


if __name__ == "__main__":
    main()

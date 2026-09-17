"""Paridade Python↔JS por caso, no build (item 6, Task 2, D2 do plano
docs/superpowers/plans/2026-09-16-v4-item6-fixture-sintetica.md).

A §13 do desenho pede falha fechada quando a paridade diverge, e a §18.2 diz que nada é
emitido. Até aqui a paridade tinha dois guardiões: os harnesses da suíte, que medem o
espelho contra o motor sobre vetores escolhidos, e o badge do laboratório, que confere o
caso quando o relatório abre — depois de emitido. Este módulo é o terceiro, e o único por
CASO antes da emissão: roda a fachada do espelho em node sobre o `caso` e a compara com o
`resultados` que o Python publicou, pelo MESMO comparador do badge
(`espelho_fachada.js:compararComResultados`) — cobre o que o badge cobre, nada além.

A verificação é da integração (E3): é aqui que se sabe onde a fachada mora e como rodá-la.
O builder do relatório só a chama, pela CLI deste arquivo (o relatório nunca importa a
integração), e converte o veredito em achado de QC.

`verificar(caso, resultados)` devolve um de três vereditos:
- `{"estado": "ok"}` — a fachada reproduz o que o Python publicou;
- `{"estado": "divergente", "divergencias": [...], "erro": <texto> | None}` — as
  divergências do comparador (`{cenario, chave, python, js, erro_relativo}`), ou, com
  `erro`, a razão de a verificação não ter fechado: a fachada recusou o caso, o node saiu
  com erro, não respondeu no prazo ou não devolveu JSON. Falha fechada: uma verificação
  que não fecha nunca vale como paridade verificada;
- `{"estado": "indisponivel"}` — não há node nesta máquina. É o único caso em que a
  paridade não foi verificada sem que isso reprove a entrega; o relatório o declara.

Custo: um processo node por chamada, com o caso e os resultados pelo stdin.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

# Path(__file__) é .../skills/er-valuation/scripts/paridade.py; parents[1] é
# .../skills/er-valuation, onde moram os assets da integração.
FACHADA = Path(__file__).resolve().parents[1] / "assets" / "espelho_fachada.js"

ESTADO_OK: str = "ok"
ESTADO_DIVERGENTE: str = "divergente"
ESTADO_INDISPONIVEL: str = "indisponivel"
ESTADOS: tuple[str, ...] = (ESTADO_OK, ESTADO_DIVERGENTE, ESTADO_INDISPONIVEL)

# O mesmo prazo dos harnesses da fachada na suíte: o comparador recalcula o caso inteiro —
# cenários, grades e reversa —, e nada disso leva mais que alguns segundos.
TIMEOUT_SEGUNDOS: float = 120

# Carrega a fachada (que acha o espelho por `require` do irmão), lê o payload do stdin e
# escreve o que o comparador devolve. Uma exceção — inclusive a recusa nomeada da fachada,
# `contrato_desconhecido` por exemplo, ou um JSON que não se lê — sai como `{erro, codigo}`,
# nunca como um traceback que o chamador teria de interpretar.
_HARNESS = (
    "const fs = require('fs');"
    "let saida;"
    "try {"
    "  const F = require(%s);"
    "  const p = JSON.parse(fs.readFileSync(0, 'utf-8'));"
    "  saida = F.compararComResultados(p.caso, p.resultados);"
    "} catch (erro) {"
    "  saida = {erro: String(erro && erro.message), codigo: (erro && erro.codigo) || null};"
    "}"
    "process.stdout.write(JSON.stringify(saida));"
)


def _divergente(divergencias: list, erro: str | None) -> dict:
    return {"estado": ESTADO_DIVERGENTE, "divergencias": divergencias, "erro": erro}


def verificar(caso: dict, resultados: dict) -> dict:
    """O veredito da paridade do `caso` contra o `resultados` publicado — ver o docstring do
    módulo. O node é procurado no PATH a cada chamada."""
    node = shutil.which("node")
    if node is None:
        return {"estado": ESTADO_INDISPONIVEL}
    entrada = json.dumps({"caso": caso, "resultados": resultados}, ensure_ascii=False)
    try:
        processo = subprocess.run(
            [node, "-e", _HARNESS % json.dumps(str(FACHADA))], input=entrada,
            capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT_SEGUNDOS)
    except FileNotFoundError:
        return {"estado": ESTADO_INDISPONIVEL}
    except subprocess.TimeoutExpired:
        return _divergente([], f"o node não respondeu em {TIMEOUT_SEGUNDOS:g} s.")
    if processo.returncode != 0:
        return _divergente([], f"o node saiu com código {processo.returncode}: {processo.stderr.strip()}")
    try:
        saida = json.loads(processo.stdout)
    except json.JSONDecodeError as erro:
        return _divergente([], f"o node não devolveu JSON ({erro}): {processo.stdout[:200]!r}")
    if not isinstance(saida, dict):
        return _divergente([], f"o node devolveu {saida!r}, e não o veredito do comparador.")
    if "erro" in saida:
        return _divergente([], f"a fachada recusou o caso ({saida.get('codigo')}): {saida['erro']}")
    if saida.get("ok") is True:
        return {"estado": ESTADO_OK}
    divergencias = saida.get("divergencias")
    return _divergente(divergencias if isinstance(divergencias, list) else [], None)


def main() -> int:
    """CLI: lê `{"caso": ..., "resultados": ...}` do stdin e escreve o veredito em JSON no
    stdout, com código 0 — qualquer que seja o veredito. Código 1 só para uma entrada que não
    se lê, com a razão em stderr."""
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    try:
        entrada = json.loads(sys.stdin.read())
        caso, resultados = entrada["caso"], entrada["resultados"]
    except (json.JSONDecodeError, KeyError, TypeError) as erro:
        print(f"entrada da verificação de paridade ilegível — esperado um objeto com 'caso' e "
              f"'resultados': {erro!r}.", file=sys.stderr)
        return 1
    print(json.dumps(verificar(caso, resultados), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""CLI do builder do relatório (`er-relatorio`, fatia 5A, item 5, Task 4).

`python skills/er-relatorio/scripts/builder.py <raiz>`:
- código 0: `entrega.json` válido, QC sem HARD FAIL — escreve `relatorio.html`
  (as três abas — Tese, Valuation, Evidência — via `render.compor`) e `qc.json`.
- código 2: `entrega.json` válido mas o QC achou HARD FAIL — escreve só
  `qc.json` (regra inviolável 2: nenhum `relatorio.html` sai).
- código 1: uso incorreto, `entrega.json` ausente/malformado/incompatível, ou
  um asset PRÓPRIO do skill (dicionário/catálogo) sem a chave que o render
  precisa — nada é escrito; a razão sai em stderr, nomeando o campo/chave,
  com sugestão quando aplicável.

QC roda em DUAS passadas (A8, regra inviolável 2): a primeira, com
`html=None`, decide se há HARD FAIL nas regras que não dependem do HTML —
um HARD FAIL aqui já recusa emitir, sem nunca renderizar. Só quando a
primeira passada está limpa o HTML é composto (`render.compor`, em
memória) e o QC roda de novo, agora com esse HTML, para a regra
`relatorio_nao_autocontido`; só se essa segunda passada também não achar
HARD FAIL é que `relatorio.html` é gravado no disco — nunca antes.

E3 (`docs/desenho-arquitetura-v4.md` §15): este módulo, como todo o resto
de `skills/er-relatorio/scripts/`, não importa nada de `er-valuation` nem
do vendor. O único caminho para dentro da camada de integração é a
constante `ASSETS_DA_INTEGRACAO`, abaixo — hoje só o catálogo de
apresentação; a fatia 5C acrescenta a fachada do espelho ali, na mesma
linha. `tests/test_relatorio_fronteira.py` trava os dois mecanicamente:
nenhum import proibido, e nenhum literal de código fora dessa constante
(ou de docstring) nomeia a integração.
"""

import argparse
import json
import sys
from pathlib import Path

import entrega as contrato_entrega
import placeholders
import qc
import render
from entrega import EntregaInvalida

RAIZ_DO_REPO = Path(__file__).resolve().parents[3]

# Único literal de código deste pacote que nomeia a integração (ver o
# docstring do módulo) — mecanizado por
# tests/test_relatorio_fronteira.py::test_caminho_da_integracao_so_na_constante_de_assets.
ASSETS_DA_INTEGRACAO = {"catalogo": RAIZ_DO_REPO / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json"}


def _carregar_catalogo() -> dict:
    return json.loads(ASSETS_DA_INTEGRACAO["catalogo"].read_text(encoding="utf-8"))


def _montar_qc_json(achados: list, dicionario: dict) -> dict:
    """`qc.json`: achados com a mensagem já resolvida do dicionário
    (`qc.<codigo>`, `params` substituídos) — sai sempre, em ordem
    determinística (a mesma ordem que `qc.avaliar` já devolve)."""
    mensagens = dicionario.get("qc", {})
    lista = []
    for achado in achados:
        modelo = mensagens.get(achado.codigo)
        if modelo is None:
            raise KeyError(
                f"dicionário sem mensagem para 'qc.{achado.codigo}' "
                "(assets/i18n/) — achado não pode ser reportado."
            )
        mensagem = modelo.format(onde=achado.onde, **achado.params)
        lista.append({
            "nivel": achado.nivel,
            "codigo": achado.codigo,
            "onde": achado.onde,
            "params": achado.params,
            "mensagem": mensagem,
        })
    return {"versao_contrato": "qc/1", "achados": lista}


def _escrever_json(caminho: Path, dados: dict) -> None:
    texto = json.dumps(dados, indent=2, ensure_ascii=False) + "\n"
    caminho.write_text(texto, encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    # Mesma disciplina de avaliar.main() (er-valuation): saída deste
    # processo pode carregar acento de qualquer recusa nomeada — sem isto,
    # um console Windows PT-BR sem PYTHONUTF8 pode estourar
    # UnicodeEncodeError ao imprimir, mascarando o erro real.
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Le entrega.json de uma raiz de execucao, roda o QC de tres niveis "
                    "e emite relatorio.html + qc.json -- ou recusa, nomeando a razao.")
    parser.add_argument("raiz", type=Path, help="raiz de execucao (contem entrega.json)")
    args = parser.parse_args(argv)

    try:
        entrega_dict = contrato_entrega.carregar(args.raiz)
    except EntregaInvalida as erro:
        print(str(erro), file=sys.stderr)
        return 1

    try:
        catalogo = _carregar_catalogo()
    except (OSError, json.JSONDecodeError) as erro:
        print(f"não foi possível ler o catálogo de apresentação: {erro}.", file=sys.stderr)
        return 1

    idioma = entrega_dict["execucao"]["idioma"]
    try:
        dicionario = placeholders.carregar_dicionario(idioma)
    except placeholders.FormatoInvalido as erro:
        print(str(erro), file=sys.stderr)
        return 1

    raiz = Path(args.raiz).resolve()

    # Fase 1 (A8, regra inviolável 2): QC sem HTML nenhum -- nada foi
    # renderizado ainda, então `relatorio_nao_autocontido` não pode disparar
    # aqui (qc.avaliar trata html=None como "regra ainda não examinável").
    # Um HARD FAIL desta fase já recusa emitir, sem nunca chamar render.compor.
    achados = qc.avaliar(entrega_dict, catalogo, html=None)
    if any(achado.nivel == "HARD_FAIL" for achado in achados):
        qc_json = _montar_qc_json(achados, dicionario)
        try:
            _escrever_json(raiz / "qc.json", qc_json)
        except OSError as erro:
            print(f"não foi possível gravar 'qc.json': {erro}.", file=sys.stderr)
            return 1
        return 2

    fontes = {"resultados": entrega_dict["resultados"], "caso": entrega_dict["caso"]}
    _conclusao_resolvida, log, _erros = placeholders.resolver(
        entrega_dict["analise"]["conclusao"]["texto"], fontes, idioma, "analise.conclusao.texto")

    try:
        pagina = render.compor(entrega_dict, catalogo, achados, log, idioma)
    except (render.ChaveDeInterfaceAusente, render.RotuloDoCatalogoAusente) as erro:
        print(str(erro), file=sys.stderr)
        return 1

    # Fase 2: o mesmo QC, agora com o HTML já composto EM MEMÓRIA, só para
    # `relatorio_nao_autocontido` (a única regra que precisa dele). As
    # demais regras são puras sobre `entrega`/`catalogo` e não podem mudar
    # de resultado entre as duas passadas -- `achados_finais` é sempre
    # `achados` com, no máximo, esse único achado extra ao final.
    achados_finais = qc.avaliar(entrega_dict, catalogo, html=pagina)

    qc_json = _montar_qc_json(achados_finais, dicionario)
    try:
        _escrever_json(raiz / "qc.json", qc_json)
    except OSError as erro:
        print(f"não foi possível gravar 'qc.json': {erro}.", file=sys.stderr)
        return 1

    if any(achado.nivel == "HARD_FAIL" for achado in achados_finais):
        # Regra inviolável 2: o HTML já composto em memória nunca chega ao
        # disco quando a segunda passada do QC o reprova.
        return 2

    try:
        (raiz / "relatorio.html").write_text(pagina, encoding="utf-8", newline="\n")
    except OSError as erro:
        print(f"não foi possível gravar 'relatorio.html': {erro}.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

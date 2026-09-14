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
constante `ASSETS_DA_INTEGRACAO`, abaixo — o catálogo de apresentação e,
desde a fatia 5C, o espelho do núcleo e a fachada que o laboratório da aba
Valuation chama no navegador. `tests/test_relatorio_fronteira.py` trava os dois mecanicamente:
nenhum import proibido, e nenhum literal de código fora dessa constante
(ou de docstring) nomeia a integração.
"""

import argparse
import json
import sys
from pathlib import Path

import entrega as contrato_entrega
import exhibits
import placeholders
import qc
import render
from entrega import EntregaInvalida

RAIZ_DO_REPO = Path(__file__).resolve().parents[3]

# Únicos literais de código deste pacote que nomeiam a integração (ver o
# docstring do módulo) — mecanizado por
# tests/test_relatorio_fronteira.py::test_caminho_da_integracao_so_na_constante_de_assets.
#
# Fatia 5C, Task 2: o espelho do núcleo e a fachada entram aqui, ao lado do
# catálogo, porque o laboratório da aba Valuation roda o motor no navegador
# de quem abriu o arquivo. Eles são LIDOS daqui e embutidos no HTML —
# NUNCA copiados para `skills/er-relatorio/assets/`: `tests/test_relatorio_
# fronteira.py::test_nenhum_asset_do_relatorio_espelha_um_asset_da_
# integracao_ou_do_vendor` reprova a cópia por sha256 (não por nome), e é
# essa a intenção. Toda a metodologia que o laboratório executa continua do
# lado da integração (E3); o relatório só embute e chama.
ASSETS_DA_INTEGRACAO = {
    "catalogo": RAIZ_DO_REPO / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json",
    "espelho": RAIZ_DO_REPO / "skills" / "er-valuation" / "assets" / "motor_espelho.js",
    "fachada": RAIZ_DO_REPO / "skills" / "er-valuation" / "assets" / "espelho_fachada.js",
}


def _carregar_catalogo() -> dict:
    return json.loads(ASSETS_DA_INTEGRACAO["catalogo"].read_text(encoding="utf-8"))


def _carregar_js_da_integracao() -> dict:
    """Os dois módulos JS da integração, como TEXTO — o espelho do núcleo e a
    fachada que o laboratório chama. Lidos de `ASSETS_DA_INTEGRACAO` a cada
    build (nunca copiados para dentro do skill do relatório) e repassados a
    `render.compor`, que os embute como valor de `string.Template` — nunca
    colados no template, que tem `$marcador` próprio."""
    return {nome: ASSETS_DA_INTEGRACAO[nome].read_text(encoding="utf-8")
            for nome in ("espelho", "fachada")}


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


def _remover_saida_anterior(raiz: Path) -> None:
    """B3 (regra inviolável 2) — no início de todo build, desfaz qualquer
    'relatorio.html'/'qc.json' que já exista na raiz de uma rodada anterior
    -- inclusive quando é um symlink: `Path.unlink()` desfaz o LINK, nunca
    segue até o alvo (o alvo, se houver, não é tocado). Sem isto, uma
    recusa (código 1 ou 2) nesta mesma raiz podia deixar o relatorio.html de
    uma rodada ANTERIOR bem-sucedida no lugar -- código diferente de 0 tem
    de significar "nada publicável aqui", nunca "o que já estava aqui
    continua valendo". Roda incondicionalmente, antes até de tentar ler
    'entrega.json' -- uma recusa código 1 (uso incorreto/entrega inválida)
    tem exatamente a mesma obrigação. `OSError` (não só `FileNotFoundError`)
    é engolido de propósito: se `raiz` nem existe, ou não é um diretório,
    esta função não é o lugar que diagnostica isso -- `entrega.carregar`
    (chamado logo em seguida) já dá o erro nomeado e código 1 corretos;
    esta limpeza preliminar só não pode ser o que derruba o processo com um
    traceback cru antes de chegar lá."""
    for nome in ("relatorio.html", "qc.json"):
        try:
            (raiz / nome).unlink()
        except OSError:
            pass


def _escrever_arquivo_da_raiz(raiz: Path, nome: str, conteudo: str) -> None:
    """B4 (regra inviolável 6) — escreve `conteudo` em `raiz/nome`, nunca
    através de um symlink: desfaz (unlink, nunca segue) o que já estiver
    nesse caminho exato imediatamente antes de escrever, para que
    `caminho.write_text` sempre crie um arquivo comum novo ali -- nunca
    escreva através de um link para fora da raiz. `raiz/nome` é
    estruturalmente interno à raiz por construção (`nome` é sempre um
    literal fixo deste módulo, nunca dado externo); o unlink-antes-de-
    escrever é o que impede a escrita de seguir um link que aponte para
    fora, mesmo que algo tenha recriado um nesse caminho entre a limpeza de
    `_remover_saida_anterior` e este ponto."""
    caminho = raiz / nome
    try:
        caminho.unlink()
    except FileNotFoundError:
        pass
    caminho.write_text(conteudo, encoding="utf-8", newline="\n")


def _escrever_json(raiz: Path, nome: str, dados: dict) -> None:
    texto = json.dumps(dados, indent=2, ensure_ascii=False) + "\n"
    _escrever_arquivo_da_raiz(raiz, nome, texto)


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

    # B3: incondicional, antes de qualquer tentativa de ler 'entrega.json' --
    # nenhuma saída deste processo, nenhum código de retorno, pode deixar a
    # saída de uma rodada anterior no lugar.
    _remover_saida_anterior(Path(args.raiz))

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

    try:
        js_da_integracao = _carregar_js_da_integracao()
    except OSError as erro:
        print(f"não foi possível ler o espelho/a fachada da integração: {erro}.", file=sys.stderr)
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
            _escrever_json(raiz, "qc.json", qc_json)
        except OSError as erro:
            print(f"não foi possível gravar 'qc.json': {erro}.", file=sys.stderr)
            return 1
        return 2

    # Fatia 5D, Task 3 (achado 3): o log de resolução que a aba Evidência exibe
    # cobre TODO campo de prosa — a mesma lista que o QC acabou de varrer
    # (`placeholders.campos_de_prosa`), nunca só a conclusão. Um número citado
    # num texto da Tese ou no caption de um exhibit sai resolvido na tela e,
    # junto, na trilha de auditoria.
    _prosa_resolvida, log = placeholders.resolver_prosa(entrega_dict, idioma)

    # Fatia 5B, item 5, Task 2: exhibits são resolvidos em números UMA
    # única vez aqui -- a fase 1 do QC (acima) já confirmou zero HARD FAIL
    # de rastreabilidade (`serie_nao_rastreavel`/`formula_invalida`/
    # `overlay_nao_resolvido`/`serie_de_tamanho_incompativel`), então esta
    # chamada não deveria levantar (ver o docstring de `exhibits.resolver`).
    # `render.compor` recebe o resultado pronto -- nunca chama `exhibits.
    # resolver` de novo por conta própria.
    exhibits_resolvidos, log_exhibits = exhibits.resolver(entrega_dict)

    try:
        pagina = render.compor(entrega_dict, catalogo, achados, log, idioma,
                                exhibits_resolvidos, log_exhibits, js_da_integracao)
    except (render.ChaveDeInterfaceAusente, render.RotuloDoCatalogoAusente,
            render.CampoDeContratoAusente, render.JsonNaoSerializavel,
            render.ProsaNaoAuditada) as erro:
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
        _escrever_json(raiz, "qc.json", qc_json)
    except OSError as erro:
        print(f"não foi possível gravar 'qc.json': {erro}.", file=sys.stderr)
        return 1

    if any(achado.nivel == "HARD_FAIL" for achado in achados_finais):
        # Regra inviolável 2: o HTML já composto em memória nunca chega ao
        # disco quando a segunda passada do QC o reprova.
        return 2

    try:
        _escrever_arquivo_da_raiz(raiz, "relatorio.html", pagina)
    except OSError as erro:
        print(f"não foi possível gravar 'relatorio.html': {erro}.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

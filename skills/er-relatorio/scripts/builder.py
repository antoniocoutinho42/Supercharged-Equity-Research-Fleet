"""CLI do builder do relatório (`er-relatorio`, fatia 5A, item 5, Task 4).

`python skills/er-relatorio/scripts/builder.py <raiz>`:
- código 0: `entrega.json` válido, QC sem HARD FAIL — escreve `relatorio.html`
  (as três abas — Tese, Valuation, Evidência — via `render.compor`), `qc.json`
  e `ficha-tecnica.json` (a ficha técnica da execução, `compor_ficha_tecnica`,
  fatia 5E), que só sai junto do relatório.
- código 2: `entrega.json` válido mas o QC achou HARD FAIL — escreve só
  `qc.json` (regra inviolável 2: nenhum `relatorio.html` sai).
- código 1: uso incorreto, `entrega.json` ausente/malformado/incompatível, o
  contrato do ledger (`ledger/1`, do `er-evidencia`) ilegível ou fora da forma
  que o relatório lê, um asset PRÓPRIO do skill (dicionário/catálogo) sem a
  chave que o render precisa, ou a verificação de paridade da integração sem
  veredito (item 6) — nada é escrito; a razão sai em stderr, nomeando o campo/chave,
  com sugestão quando aplicável.

Paridade por caso (item 6, Task 2): antes do QC, o builder chama a verificação
da integração uma vez e passa o veredito às duas passadas — `divergente` é o
HARD FAIL `paridade_divergente`, `indisponivel` (sem node) o REQUIRED DISCLOSURE
`paridade_nao_verificada_no_build`.

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
Valuation chama no navegador; desde o item 6, a CLI da verificação de paridade,
chamada por subprocesso. `tests/test_relatorio_fronteira.py` trava os dois mecanicamente:
nenhum import proibido, e nenhum literal de código fora dessa constante
(ou de docstring) nomeia a integração.
"""

import argparse
import json
import subprocess
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
#
# Fatia 5E, Task 2: o contrato `ledger/1` entra pela mesma porta. Ele é do
# `er-evidencia` (§3.2 do desenho, "dono do schema do ledger"): o relatório
# valida a forma do ledger contra ele e decide pelas flags que ele declara, e
# por isso o lê daqui a cada build — nunca o copia para dentro do skill.
#
# Item 6, Task 2 (D2): a verificação da paridade por caso entra pela mesma porta. Ela é da
# integração — que sabe onde a fachada mora e como rodá-la em node —, e o builder a CHAMA
# pela CLI dela, num subprocesso: nunca a importa (E3), e nunca sabe de node.
ASSETS_DA_INTEGRACAO = {
    "catalogo": RAIZ_DO_REPO / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json",
    "espelho": RAIZ_DO_REPO / "skills" / "er-valuation" / "assets" / "motor_espelho.js",
    "fachada": RAIZ_DO_REPO / "skills" / "er-valuation" / "assets" / "espelho_fachada.js",
    "contrato_ledger": RAIZ_DO_REPO / "skills" / "er-evidencia" / "assets" / "contrato_ledger.json",
    "paridade": RAIZ_DO_REPO / "skills" / "er-valuation" / "scripts" / "paridade.py",
}


def _carregar_catalogo() -> dict:
    return json.loads(ASSETS_DA_INTEGRACAO["catalogo"].read_text(encoding="utf-8"))


def _carregar_contrato_ledger() -> dict:
    """O contrato `ledger/1`, como dado, lido de `ASSETS_DA_INTEGRACAO` a cada build. A forma
    dele é conferida por `entrega.ler_contrato_do_ledger`, dentro de `entrega.carregar`."""
    return json.loads(ASSETS_DA_INTEGRACAO["contrato_ledger"].read_text(encoding="utf-8"))


def _carregar_js_da_integracao() -> dict:
    """Os dois módulos JS da integração, como TEXTO — o espelho do núcleo e a
    fachada que o laboratório chama. Lidos de `ASSETS_DA_INTEGRACAO` a cada
    build (nunca copiados para dentro do skill do relatório) e repassados a
    `render.compor`, que os embute como valor de `string.Template` — nunca
    colados no template, que tem `$marcador` próprio."""
    return {nome: ASSETS_DA_INTEGRACAO[nome].read_text(encoding="utf-8")
            for nome in ("espelho", "fachada")}


class ParidadeNaoVerificavel(Exception):
    """A CLI da verificação de paridade não devolveu um veredito do contrato — saiu com erro,
    estourou o prazo ou escreveu outra coisa. Código 1: não é o caso que diverge, é a
    verificação que não rodou, e nada é emitido."""


# O prazo da chamada inteira: o da própria verificação (um processo node) com folga para a
# partida do interpretador.
TIMEOUT_DA_PARIDADE_SEGUNDOS: float = 180


def _verificar_paridade(entrega_dict: dict) -> dict:
    """O veredito da paridade por caso (item 6, Task 2, D2), pela CLI da integração: uma
    chamada por build, com o `caso` e o `resultados` da entrega pelo stdin e o veredito
    (`{"estado": ...}`, um de `qc.ESTADOS_DA_PARIDADE`) no stdout. Este módulo não
    interpreta o veredito — `qc.avaliar` o converte em achado —; só recusa, com
    `ParidadeNaoVerificavel`, uma resposta que não é veredito nenhum."""
    entrada = json.dumps({"caso": entrega_dict["caso"], "resultados": entrega_dict["resultados"]},
                         ensure_ascii=False)
    try:
        processo = subprocess.run(
            [sys.executable, str(ASSETS_DA_INTEGRACAO["paridade"])], input=entrada,
            capture_output=True, text=True, encoding="utf-8", timeout=TIMEOUT_DA_PARIDADE_SEGUNDOS)
    except (OSError, subprocess.TimeoutExpired) as erro:
        raise ParidadeNaoVerificavel(f"a verificação de paridade não rodou: {erro}.") from erro
    if processo.returncode != 0:
        raise ParidadeNaoVerificavel(
            f"a verificação de paridade saiu com código {processo.returncode}: {processo.stderr.strip()}")
    try:
        veredito = json.loads(processo.stdout)
    except json.JSONDecodeError as erro:
        raise ParidadeNaoVerificavel(f"a verificação de paridade não devolveu JSON: {erro}.") from erro
    if not isinstance(veredito, dict) or veredito.get("estado") not in qc.ESTADOS_DA_PARIDADE:
        raise ParidadeNaoVerificavel(
            f"a verificação de paridade devolveu {veredito!r}, fora dos estados do contrato "
            f"({', '.join(qc.ESTADOS_DA_PARIDADE)}).")
    return veredito


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


# Fatia 5E, Task 3 (D6; §9 do desenho, e §15, decisão 10: "também em arquivo"): a ficha
# técnica da execução, gravada ao lado de `relatorio.html` só quando ele é gravado.
NOME_DA_FICHA_TECNICA = "ficha-tecnica.json"


def _contagem_em_ordem(chaves) -> dict:
    """`{chave: quantas vezes}`, pela chave em ordem alfabética — nunca pela ordem em que
    as chaves chegam."""
    contagem: dict = {}
    for chave in chaves:
        contagem[chave] = contagem.get(chave, 0) + 1
    return dict(sorted(contagem.items()))


def compor_ficha_tecnica(entrega_dict: dict, catalogo: dict, achados: list) -> dict:
    """A ficha técnica da execução (fatia 5E, Task 3, D6), composta pelo builder — a entrega
    nunca a declara. Função pura: sem relógio, sem caminho, e a mesma ficha para a mesma
    entrega em qualquer ordem dos registros do ledger ou dos achados. Compõe:
    - a execução: `id`, `ticker` e `idioma`;
    - de `resultados.origem`: o nome e a versão da metodologia e o `caso_sha256`;
    - as versões dos contratos consumidos, lidas dos próprios artefatos: a entrega, os
      resultados, o catálogo e o ledger;
    - os registros do ledger por estatuto e por classe de fonte;
    - os achados do QC por nível, na ordem de `qc.NIVEIS`, e por código. Todos os níveis,
      também o QUALITY WARNING: a ficha em arquivo é interna, como o `qc.json`, e a
      Evidência a mostra sem ele.

    Gates declarados e comandos executados ficam para o item 8: nenhum produtor os tem, e
    inventar o formato agora é o que a §12 proíbe. `resultados` e o catálogo são opacos para
    o relatório: um campo que a ficha lê e não está lá é `render.CampoDeContratoAusente`,
    nomeado — código 1 no `main`, nunca um `KeyError` cru."""
    execucao, resultados, ledger = entrega_dict["execucao"], entrega_dict["resultados"], entrega_dict["ledger"]
    origem = render._campo_de_contrato(resultados, "origem", "resultados")
    metodologia = render._campo_de_contrato(origem, "metodologia", "resultados.origem")
    registros = ledger["registros"]
    return {
        "execucao": {campo: execucao[campo] for campo in ("id", "ticker", "idioma")},
        "metodologia": {
            "nome": render._campo_de_contrato(metodologia, "nome", "resultados.origem.metodologia"),
            "versao": render._campo_de_contrato(metodologia, "versao", "resultados.origem.metodologia"),
            "caso_sha256": render._campo_de_contrato(origem, "caso_sha256", "resultados.origem"),
        },
        "contratos": {
            "entrega": entrega_dict["versao_contrato"],
            "resultados": resultados["versao_contrato"],
            "catalogo": render._campo_de_contrato(catalogo, "versao_contrato", "catalogo"),
            "ledger": ledger["versao_contrato"],
        },
        "registros_por_estatuto": _contagem_em_ordem(registro["estatuto"] for registro in registros),
        "registros_por_classe_de_fonte": _contagem_em_ordem(registro["fonte"]["classe"] for registro in registros),
        "achados": {nivel: _contagem_em_ordem(achado.codigo for achado in achados if achado.nivel == nivel)
                    for nivel in qc.NIVEIS},
    }


def _remover_saida_anterior(raiz: Path) -> None:
    """B3 (regra inviolável 2) — no início de todo build, desfaz qualquer
    'relatorio.html'/'qc.json'/'ficha-tecnica.json' (fatia 5E) que já exista na raiz de uma rodada anterior
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
    for nome in ("relatorio.html", "qc.json", NOME_DA_FICHA_TECNICA):
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

    # Fatia 5E, Task 2: o contrato do ledger antes da entrega — é contra ele que a
    # forma do ledger é validada. Ilegível ou fora da forma, código 1.
    try:
        contrato_ledger = _carregar_contrato_ledger()
    except (OSError, json.JSONDecodeError) as erro:
        print(f"não foi possível ler o contrato do ledger: {erro}.", file=sys.stderr)
        return 1

    try:
        entrega_dict = contrato_entrega.carregar(args.raiz, contrato_ledger)
    except (EntregaInvalida, contrato_entrega.ContratoDoLedgerInvalido) as erro:
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

    # Item 6, Task 2 (D2; §13 e §18.2): a paridade por caso, antes de qualquer passada do QC
    # — uma chamada por build, e o mesmo veredito nas duas passadas. `divergente` vira o
    # HARD FAIL `paridade_divergente` (nada é emitido); `indisponivel`, o disclosure
    # `paridade_nao_verificada_no_build`. Uma verificação que nem devolve veredito é código 1.
    try:
        paridade = _verificar_paridade(entrega_dict)
    except ParidadeNaoVerificavel as erro:
        print(str(erro), file=sys.stderr)
        return 1

    # Fase 1 (A8, regra inviolável 2): QC sem HTML nenhum -- nada foi
    # renderizado ainda, então `relatorio_nao_autocontido` não pode disparar
    # aqui (qc.avaliar trata html=None como "regra ainda não examinável").
    # Um HARD FAIL desta fase já recusa emitir, sem nunca chamar render.compor.
    achados = qc.avaliar(entrega_dict, catalogo, contrato_ledger, html=None, paridade=paridade)
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

    # Fatia 5E, Task 3 (D6): a ficha técnica da execução, composta aqui sobre os achados
    # desta primeira passada — os mesmos da segunda sempre que o relatório é gravado: a
    # segunda só pode acrescentar o HARD FAIL `relatorio_nao_autocontido`, que impede a
    # gravação. A Evidência mostra esta ficha, e `ficha-tecnica.json` grava a mesma.
    try:
        ficha_tecnica = compor_ficha_tecnica(entrega_dict, catalogo, achados)
        pagina = render.compor(entrega_dict, catalogo, achados, log, idioma,
                                exhibits_resolvidos, log_exhibits, js_da_integracao,
                                ficha_tecnica=ficha_tecnica)
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
    achados_finais = qc.avaliar(entrega_dict, catalogo, contrato_ledger, html=pagina, paridade=paridade)

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

    # Fatia 5E, Task 3 (D6): o relatório e a ficha técnica saem juntos. Se a gravação falha
    # no meio, nenhum dos dois fica — código diferente de 0 é "nada publicável aqui" (B3).
    try:
        _escrever_arquivo_da_raiz(raiz, "relatorio.html", pagina)
        _escrever_json(raiz, NOME_DA_FICHA_TECNICA, ficha_tecnica)
    except OSError as erro:
        for nome in ("relatorio.html", NOME_DA_FICHA_TECNICA):
            try:
                (raiz / nome).unlink()
            except OSError:
                pass
        print(f"não foi possível gravar 'relatorio.html' e '{NOME_DA_FICHA_TECNICA}': {erro}.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

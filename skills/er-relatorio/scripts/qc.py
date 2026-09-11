"""QC de três níveis (A8): HARD FAIL, REQUIRED DISCLOSURE, QUALITY WARNING.

Regras da Task 3 (5A — ver o plano, seção Task 3, "QC — regras desta
fatia"): `resultados_nao_correspondem_ao_caso`, `placeholder_nao_resolvido`,
`numero_sem_proveniencia` e `diagnostico_sem_chave` (todas HARD FAIL);
`divergencia_de_base_degrau` (REQUIRED DISCLOSURE). A Task 4 acrescenta
`relatorio_nao_autocontido` (HARD FAIL, "Regras de render" do plano): nenhum
recurso externo (`http://`, `https://` ou `//` protocol-relative em
`src`/`href`/`url(`) é aceito no HTML — CSS e JS são sempre inline. A 5D
completa a lista da §11.

Este módulo NÃO importa nada de `er-valuation` nem do vendor (E3): recebe
`entrega` (o dict que `entrega.carregar` já validou) e `catalogo` (o dict
de `catalogo_apresentacao.json`, lido por `builder.py` via
`ASSETS_DA_INTEGRACAO`) já carregados — só lê dados, nunca código nem
metodologia da integração.

`avaliar()` devolve `Achado` ESTRUTURADO (nível, código, onde, params) —
nunca resolve mensagem para idioma nenhum. Resolver `qc.<codigo>` do
dicionário com os `params` substituídos é responsabilidade de quem monta
`qc.json` (`builder.py`): só ali existe o idioma já resolvido de forma
determinística, e a mesma lista de achados serve tanto para decidir o exit
code quanto para o disclosure visível no HTML (Task 4).
"""

import re
from typing import NamedTuple

import entrega as contrato_entrega
import placeholders

NIVEIS: tuple[str, ...] = ("HARD_FAIL", "REQUIRED_DISCLOSURE", "QUALITY_WARNING")


class Achado(NamedTuple):
    nivel: str
    codigo: str
    onde: str
    params: dict


_PADRAO_PLACEHOLDER_BRUTO = re.compile(r"\{\{.*?\}\}")
_PADRAO_DIGITO = re.compile(r"\d")

# `relatorio_nao_autocontido` (Task 4): recurso externo em src=/href=/url( —
# com ou sem esquema (protocol-relative "//"). Ancorado no atributo/função
# para não confundir um "//" qualquer (ex.: dentro de um comentário) com um
# recurso de fato carregado pelo HTML.
_PADRAO_RECURSO_EXTERNO = re.compile(
    r'(?:\b(?:src|href)\s*=\s*["\']\s*(?:https?:)?//|url\(\s*["\']?\s*(?:https?:)?//)',
    re.IGNORECASE,
)


def _achado_hash(entrega: dict) -> Achado | None:
    """`resultados_nao_correspondem_ao_caso` (HARD FAIL): prova por hash,
    nunca rodando o motor (A2) — `sha256_canonico(caso)`, recalculado aqui,
    tem de bater com o que `resultados.origem.caso_sha256` já publicou.
    """
    hash_calculado = contrato_entrega.sha256_canonico(entrega["caso"])
    hash_publicado = (entrega["resultados"].get("origem") or {}).get("caso_sha256")
    if hash_calculado == hash_publicado:
        return None
    return Achado("HARD_FAIL", "resultados_nao_correspondem_ao_caso",
                  "resultados.origem.caso_sha256",
                  {"hash_caso": hash_calculado, "hash_resultados": hash_publicado})


def _campos_de_prosa(entrega: dict) -> list[tuple[str, str]]:
    """Todo campo de prosa de `analise` sujeito a `numero_sem_proveniencia`/
    `placeholder_nao_resolvido` — nesta fatia só `conclusao.texto` (A7); a
    Task 4 estende esta lista conforme mais campos de `analise` entrarem
    no contrato, sem mudar a forma desta função."""
    analise = entrega.get("analise") or {}
    conclusao = analise.get("conclusao") or {}
    texto = conclusao.get("texto")
    if isinstance(texto, str):
        return [("analise.conclusao.texto", texto)]
    return []


def _achados_prosa(entrega: dict) -> list[Achado]:
    """`placeholder_nao_resolvido` e `numero_sem_proveniencia` (ambos HARD
    FAIL) sobre todo campo de prosa de `analise`."""
    achados: list[Achado] = []
    idioma = entrega["execucao"]["idioma"]
    fontes = {"resultados": entrega.get("resultados"), "caso": entrega.get("caso")}

    for onde, texto in _campos_de_prosa(entrega):
        _resolvido, _log, erros = placeholders.resolver(texto, fontes, idioma, onde)
        for erro in erros:
            achados.append(Achado("HARD_FAIL", "placeholder_nao_resolvido", onde,
                                  {"token": erro["token"], "razao": erro["razao"]}))

        # A5/Task 3: a busca roda sobre o texto ORIGINAL com todo `{{...}}`
        # removido — nunca sobre o texto resolvido (um placeholder que
        # formata para "61,91" não pode disparar esta regra sobre o
        # próprio número que ele legitimou).
        despido = _PADRAO_PLACEHOLDER_BRUTO.sub("", texto)
        if _PADRAO_DIGITO.search(despido):
            achados.append(Achado("HARD_FAIL", "numero_sem_proveniencia", onde, {}))

    return achados


def _achados_diagnostico_sem_chave(resultados: dict) -> list[Achado]:
    """`diagnostico_sem_chave` (HARD FAIL): `null` em qualquer
    `diagnosticos_chaves` (por cenário) ou `diagnosticos_unicos_chaves`
    (por grade de sensibilidade) — a correção é da integração (A5), nunca
    do relatório."""
    achados: list[Achado] = []

    for nome, cenario in (resultados.get("cenarios") or {}).items():
        chaves = cenario.get("diagnosticos_chaves")
        if isinstance(chaves, list):
            for indice, chave in enumerate(chaves):
                if chave is None:
                    onde = f"resultados.cenarios.{nome}.diagnosticos_chaves.{indice}"
                    achados.append(Achado("HARD_FAIL", "diagnostico_sem_chave", onde, {}))

    sensibilidades = resultados.get("sensibilidades") or {}
    for tipo_grade in ("grades_1d", "grades_2d"):
        for indice_grade, grade in enumerate(sensibilidades.get(tipo_grade) or []):
            chaves = grade.get("diagnosticos_unicos_chaves")
            if isinstance(chaves, list):
                for indice, chave in enumerate(chaves):
                    if chave is None:
                        onde = (f"resultados.sensibilidades.{tipo_grade}.{indice_grade}"
                                f".diagnosticos_unicos_chaves.{indice}")
                        achados.append(Achado("HARD_FAIL", "diagnostico_sem_chave", onde, {}))

    return achados


def _achados_divergencia_de_base(resultados: dict, catalogo: dict) -> list[Achado]:
    """`divergencia_de_base_degrau` (REQUIRED DISCLOSURE): `|divergencia_de_
    base_%|` de um cenário com degrau acima do limiar do catálogo (A6) —
    parte do incremento que o degrau parece criar vem do descasamento
    entre as duas bases (LL x ROE.VPA), não do próprio degrau."""
    limiar = catalogo["limiares"]["divergencia_de_base_pct_disclosure"]
    achados: list[Achado] = []

    for nome, cenario in (resultados.get("cenarios") or {}).items():
        degrau = cenario.get("degrau")
        if not isinstance(degrau, dict):
            continue
        valor = degrau.get("divergencia_de_base_%")
        if not isinstance(valor, (int, float)) or isinstance(valor, bool):
            continue
        if abs(valor) > limiar:
            onde = f"resultados.cenarios.{nome}.degrau.divergencia_de_base_%"
            achados.append(Achado("REQUIRED_DISCLOSURE", "divergencia_de_base_degrau", onde,
                                  {"cenario": nome, "valor": round(valor, 1), "limiar": limiar}))

    return achados


def _achado_autocontido(html: str | None) -> Achado | None:
    """`relatorio_nao_autocontido` (HARD FAIL, Task 4): nenhum recurso
    externo é aceito — CSS e JS são sempre inline (regras de render do
    plano). `html` só existe DEPOIS que `render.compor` roda; `builder.py`
    chama `avaliar()` duas vezes (A8/regra inviolável 2): primeiro com
    `html=None` (as regras desta função nunca disparam — nada para
    examinar ainda), depois com o HTML já composto EM MEMÓRIA, antes de
    gravar `relatorio.html` no disco. Um HARD FAIL nesta segunda passada
    descarta o HTML gerado; só `qc.json` sai.
    """
    if html is None:
        return None
    encontrado = _PADRAO_RECURSO_EXTERNO.search(html)
    if encontrado is None:
        return None
    return Achado("HARD_FAIL", "relatorio_nao_autocontido", "relatorio.html",
                  {"trecho": encontrado.group(0).strip()})


def avaliar(entrega: dict, catalogo: dict, html: str | None = None) -> list[Achado]:
    """Roda as regras de QC; devolve os achados em ordem determinística
    (mesma entrada, mesma lista de achados, sempre — nada de relógio, nada
    de ordem de `set`).

    `html`: `None` na primeira passada de `builder.py` (antes do render —
    nenhuma regra desta fatia depende dele além de `relatorio_nao_
    autocontido`, que simplesmente não dispara); o HTML já composto na
    segunda passada, só para essa regra.
    """
    achados: list[Achado] = []

    achado_hash = _achado_hash(entrega)
    if achado_hash is not None:
        achados.append(achado_hash)

    achados.extend(_achados_prosa(entrega))

    resultados = entrega.get("resultados") or {}
    achados.extend(_achados_diagnostico_sem_chave(resultados))
    achados.extend(_achados_divergencia_de_base(resultados, catalogo))

    achado_autocontido = _achado_autocontido(html)
    if achado_autocontido is not None:
        achados.append(achado_autocontido)

    return achados

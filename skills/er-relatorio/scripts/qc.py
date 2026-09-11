"""QC de três níveis (A8): HARD FAIL, REQUIRED DISCLOSURE, QUALITY WARNING.

Regras da Task 3 (5A — ver o plano, seção Task 3, "QC — regras desta
fatia"): `resultados_nao_correspondem_ao_caso`, `placeholder_nao_resolvido`,
`numero_sem_proveniencia` e `diagnostico_sem_chave` (todas HARD FAIL);
`divergencia_de_base_degrau` (REQUIRED DISCLOSURE). A Task 4 acrescenta
`relatorio_nao_autocontido` (HARD FAIL, "Regras de render" do plano).

Onda de correção da revisão final (`.superpowers/sdd/review-5a-final.md`,
achados F1/F5/S2/S3/S4): `placeholder_malformado` (B1) -- qualquer `{{...}}`
que não seja um placeholder que `placeholders._PADRAO_PLACEHOLDER` de fato
reconhece; `relatorio_nao_autocontido` (B6) virou invariante por whitelist
(`#fragmento`/`data:` URI, nunca lista negra de esquema); `degrau_sem_
divergencia_de_base` (B10); `formato_incompativel_com_unidade` (B11);
`multiplos_com_bases_diferentes` (B12).

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


# B1 (achado F1): o único padrão que define "placeholder reconhecido" é
# `placeholders._PADRAO_PLACEHOLDER` -- reimportado aqui (não duplicado) para
# que os dois módulos nunca possam divergir sobre o que conta como
# reconhecido. Antes desta correção, `qc.py` tinha o PRÓPRIO padrão
# (`\{\{.*?\}\}`, sem DOTALL, sem exigir namespace/formato) para decidir o
# que descontar antes da busca de dígito solto -- um bloco como
# '{{R$ 99,99}}' batia nesse padrão solto (era descontado, o dígito não
# disparava `numero_sem_proveniencia`) mas NÃO batia no padrão de
# `placeholders.resolver` (não tem namespace 'resultados:'/'caso:'/'livre:'),
# então `resolver()` nunca o tocava -- nem erro, nem substituição -- e o
# token cru aparecia na tela com código 0. Mesmo buraco para um namespace
# digitado errado ('resultado:' no singular) ou capitalizado ('Resultados:').
_PADRAO_PLACEHOLDER_RECONHECIDO = placeholders._PADRAO_PLACEHOLDER

# Depois de descontar todo placeholder RECONHECIDO (acima), qualquer '{{...}}'
# que sobrar no texto é malformado por definição -- fonte fora do
# vocabulário, maiúscula, sem '|formato', ou qualquer outra forma que
# `placeholders.resolver` não reconhece. DOTALL pela mesma razão do padrão
# acima (um bloco malformado também pode estar quebrado em linhas).
_PADRAO_PLACEHOLDER_QUALQUER = re.compile(r"\{\{.*?\}\}", re.DOTALL)

_PADRAO_DIGITO = re.compile(r"\d")

# B6 (achado F5): "autocontido" é um INVARIANTE (whitelist), não uma lista
# negra de esquema. Antes desta correção, `_PADRAO_RECURSO_EXTERNO` só
# reconhecia `http://`/`https://`/`//` (protocol-relative) em `src=`/`href=`/
# `url(` -- um caminho relativo comum ('uplot.iife.min.js'), `file://`,
# `srcset=`, `data=` (de `<object data=...>`) ou `@import` passavam direto,
# código 0. Agora TODA referência de `src=`/`href=`/`srcset=`/`data=`/`url(`/
# `@import` (com ou sem aspas) tem de valer `#fragmento` ou URI `data:` --
# qualquer outra coisa (relativa, absoluta, `file://`, o que for) é HARD
# FAIL. 5A não usa nenhuma dessas referências no template (CSS/JS 100%
# inline) -- a regra estrita não custa nada hoje e fecha a porta para uma
# futura edição de template (5B/5C) reintroduzir uma sem perceber.
_PADRAO_ATRIBUTO_REF = re.compile(
    r'\b(src|href|srcset|data)\s*=\s*(?:"([^"]*)"|\'([^\']*)\'|(\S+))',
    re.IGNORECASE,
)
_PADRAO_URL_FUNCAO = re.compile(r'url\(\s*(?:"([^"]*)"|\'([^\']*)\'|([^)]*?))\s*\)', re.IGNORECASE)
_PADRAO_AT_IMPORT = re.compile(r'@import\s+(?:url\(\s*)?(?:"([^"]*)"|\'([^\']*)\'|([^\s);]+))', re.IGNORECASE)


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
    `placeholder_nao_resolvido`/`placeholder_malformado` — nesta fatia só
    `conclusao.texto` (A7); a Task 4 estende esta lista conforme mais campos
    de `analise` entrarem no contrato, sem mudar a forma desta função."""
    analise = entrega.get("analise") or {}
    conclusao = analise.get("conclusao") or {}
    texto = conclusao.get("texto")
    if isinstance(texto, str):
        return [("analise.conclusao.texto", texto)]
    return []


def _achados_prosa(entrega: dict) -> list[Achado]:
    """`placeholder_nao_resolvido`, `placeholder_malformado` e `numero_sem_
    proveniencia` (todos HARD FAIL) sobre todo campo de prosa de `analise`.

    B1 (achado F1): a busca de dígito solto e a busca de placeholder
    malformado rodam sobre o texto ORIGINAL com só os placeholders
    RECONHECIDOS removidos (nunca sobre o texto resolvido -- um placeholder
    que formata para "61,91" não pode disparar `numero_sem_proveniencia`
    sobre o próprio número que ele legitimou). Qualquer `{{...}}` que sobrar
    depois desse desconto é malformado por definição: o dígito dentro dele
    permanece no texto despido e conta normalmente para `numero_sem_
    proveniencia` -- um bloco malformado não ganha imunidade nenhuma.
    """
    achados: list[Achado] = []
    idioma = entrega["execucao"]["idioma"]
    fontes = {"resultados": entrega.get("resultados"), "caso": entrega.get("caso")}

    for onde, texto in _campos_de_prosa(entrega):
        _resolvido, _log, erros = placeholders.resolver(texto, fontes, idioma, onde)
        for erro in erros:
            achados.append(Achado("HARD_FAIL", "placeholder_nao_resolvido", onde,
                                  {"token": erro["token"], "razao": erro["razao"]}))

        despido = _PADRAO_PLACEHOLDER_RECONHECIDO.sub("", texto)

        for sobra in _PADRAO_PLACEHOLDER_QUALQUER.finditer(despido):
            achados.append(Achado("HARD_FAIL", "placeholder_malformado", onde,
                                  {"trecho": sobra.group(0)}))

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


def _achados_divergencia_de_base(resultados: dict, catalogo: dict, idioma: str) -> list[Achado]:
    """`divergencia_de_base_degrau` (REQUIRED DISCLOSURE): `|divergencia_de_
    base_%|` de um cenário com degrau acima do limiar do catálogo, acima do
    limiar — parte do incremento que o degrau parece criar vem do
    descasamento entre as duas bases (LL x ROE.VPA), não do próprio degrau.

    B8/A4 (achado F7): limiar E explicação vêm do MESMO lugar do catálogo
    (`catalogo.disclosures.divergencia_de_base_degrau`) — o caminho antigo
    (`catalogo.limiares.divergencia_de_base_pct_disclosure`, só o número,
    sem explicação) foi removido; esta é agora a fonte única. A mensagem no
    dicionário do relatório (`assets/i18n/<idioma>.json`) é só o MOLDE —
    "declare isso ao leitor" — o "porquê" (`{texto}`) é injetado aqui, vindo
    do catálogo, nunca hardcoded no relatório.

    B13 (achado S5): `params` continua carregando `valor`/`limiar` como
    NÚMEROS crus (`round(valor, 1)`/`limiar`, sem mudança de tipo — é o que
    `qc.json` expõe para quem consome o achado como dado, e o que o teste
    de contrato já travava com `pytest.approx`); `valor_fmt`/`limiar_fmt` são
    a MESMA informação, formatada por `placeholders.formatar(..., "pp1",
    idioma)` (separador decimal do idioma, sufixo '%' já embutido) — é o
    que o MOLDE do dicionário usa para montar a mensagem. Antes desta
    correção o molde interpolava `{valor}`/`{limiar}` (números crus) direto
    via `.format()`, que usa `str()`: decimal com PONTO ("16.4%") numa
    página cujo upside ao lado usa vírgula ("16,4%").
    """
    disclosure_catalogo = catalogo["disclosures"]["divergencia_de_base_degrau"]
    limiar = disclosure_catalogo["limiar_pct"]
    texto = disclosure_catalogo["texto"][idioma]
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
            achados.append(Achado("REQUIRED_DISCLOSURE", "divergencia_de_base_degrau", onde, {
                "cenario": nome,
                "valor": round(valor, 1),
                "valor_fmt": placeholders.formatar(valor, "pp1", idioma),
                "limiar": limiar,
                "limiar_fmt": placeholders.formatar(limiar, "pp1", idioma),
                "texto": texto,
            }))

    return achados


def _referencia_externa_invalida(html_texto: str) -> tuple[str, str] | None:
    """B6: devolve `(trecho, valor)` da primeira referência (`src=`/`href=`/
    `srcset=`/`data=`/`url(`/`@import`, com ou sem aspas) cujo valor não é
    `#fragmento` nem URI `data:` — ou `None` se todas as referências
    encontradas são autocontidas (ou não há nenhuma). `srcset` pode
    carregar vários candidatos separados por vírgula (cada um com um
    descritor de densidade/largura opcional) — cada candidato é validado
    separadamente.
    """
    def _primeiro_grupo(m: "re.Match[str]", inicio: int = 2) -> str:
        for grupo in m.groups()[inicio - 1:]:
            if grupo is not None:
                return grupo
        return ""

    candidatos: list[tuple[str, str]] = []

    for m in _PADRAO_ATRIBUTO_REF.finditer(html_texto):
        atributo = m.group(1).lower()
        valor = _primeiro_grupo(m)
        if atributo == "srcset":
            for pedaco in valor.split(","):
                pedaco = pedaco.strip()
                if pedaco:
                    candidatos.append((m.group(0), pedaco.split()[0]))
        else:
            candidatos.append((m.group(0), valor))

    for m in _PADRAO_URL_FUNCAO.finditer(html_texto):
        candidatos.append((m.group(0), _primeiro_grupo(m, inicio=1)))

    for m in _PADRAO_AT_IMPORT.finditer(html_texto):
        candidatos.append((m.group(0), _primeiro_grupo(m, inicio=1)))

    for trecho, valor in candidatos:
        valor = valor.strip()
        if not (valor.startswith("#") or valor.startswith("data:")):
            return trecho, valor
    return None


def _achado_autocontido(html: str | None) -> Achado | None:
    """`relatorio_nao_autocontido` (HARD FAIL, Task 4/B6): nenhuma referência
    externa é aceita — CSS e JS são sempre inline, e toda referência de
    `src=`/`href=`/`srcset=`/`data=`/`url(`/`@import` tem de valer
    `#fragmento` ou URI `data:` (whitelist, ver `_referencia_externa_
    invalida`). `html` só existe DEPOIS que `render.compor` roda;
    `builder.py` chama `avaliar()` duas vezes (A8/regra inviolável 2):
    primeiro com `html=None` (as regras desta função nunca disparam — nada
    para examinar ainda), depois com o HTML já composto EM MEMÓRIA, antes de
    gravar `relatorio.html` no disco. Um HARD FAIL nesta segunda passada
    descarta o HTML gerado; só `qc.json` sai.
    """
    if html is None:
        return None
    encontrado = _referencia_externa_invalida(html)
    if encontrado is None:
        return None
    trecho, valor = encontrado
    return Achado("HARD_FAIL", "relatorio_nao_autocontido", "relatorio.html",
                  {"trecho": trecho.strip(), "valor": valor})


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
    idioma = entrega["execucao"]["idioma"]

    achado_hash = _achado_hash(entrega)
    if achado_hash is not None:
        achados.append(achado_hash)

    achados.extend(_achados_prosa(entrega))

    resultados = entrega.get("resultados") or {}
    achados.extend(_achados_diagnostico_sem_chave(resultados))
    achados.extend(_achados_divergencia_de_base(resultados, catalogo, idioma))

    achado_autocontido = _achado_autocontido(html)
    if achado_autocontido is not None:
        achados.append(achado_autocontido)

    return achados

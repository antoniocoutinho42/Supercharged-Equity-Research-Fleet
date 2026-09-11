"""QC de três níveis (A8): HARD FAIL, REQUIRED DISCLOSURE, QUALITY WARNING.

Regras da Task 3 (5A — ver o plano, seção Task 3, "QC — regras desta
fatia"): `resultados_nao_correspondem_ao_caso`, `placeholder_nao_resolvido`,
`numero_sem_proveniencia` e `diagnostico_sem_chave` (todas HARD FAIL);
`divergencia_de_base_degrau` (REQUIRED DISCLOSURE). A Task 4 acrescenta
`relatorio_nao_autocontido` (HARD FAIL, "Regras de render" do plano).

Onda de correção da revisão final (`.superpowers/sdd/review-5a-final.md`,
achados F1/F5/S1/S2/S3/S4): `placeholder_malformado` (B1) -- qualquer
`{{...}}` que não seja um placeholder que `placeholders._PADRAO_PLACEHOLDER`
de fato reconhece; `relatorio_nao_autocontido` (B6) virou invariante por
whitelist (`#fragmento`/`data:` URI, nunca lista negra de esquema);
`diagnostico_sem_chave` (B9) passou a cobrir presença e paralelismo (não só
`null`) em TODO par `diagnosticos`/`diagnosticos_chaves`, varrido
recursivamente por `resultados.json` inteiro; `degrau_sem_divergencia_de_
base` (B10); `formato_incompativel_com_unidade` (B11);
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

Fatia 5B, item 5, Task 1 (rastreabilidade de exhibits, G1-G4/G8):
`serie_nao_rastreavel`, `formula_invalida`, `overlay_nao_resolvido` e
`serie_de_tamanho_incompativel` (HARD FAIL) mais `serie_curta_sem_
nota_janela` (QUALITY WARNING) -- ver `_achados_exhibits`. A resolução em
si (fonte/fórmula/chave -> número) mora em `exhibits.py`
(`resolver_serie`/`resolver_overlay`), reaproveitada tanto aqui (que
captura `exhibits.SerieInvalida` por item, acumulando todo achado da
entrega inteira) quanto por `exhibits.resolver` (caminho de produção da
Task 2/3, que deixa a exceção propagar).
"""

import re
from typing import NamedTuple

import entrega as contrato_entrega
import exhibits
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


# B11 (achado S3): formatos aceitáveis por unidade DE PREMISSA (catálogo,
# `premissas.<rota>.<premissa>.unidade`) -- 'pp*'/'num*' para 'pp' (o valor
# já está em pontos percentuais; 'num*' é aceito porque exibir "5,00" sem o
# sufixo '%' também não inventa unidade nenhuma, só omite o rótulo), 'moeda'/
# 'num*' para 'moeda', e só 'num0' para 'anos' (a única casa que faz sentido
# para um inteiro de anos). 'escolha'/'booleano' não aparecem aqui -- essas
# duas unidades não são numéricas, então `placeholders.formatar` já as
# recusa (`FormatoInvalido`, HARD FAIL `placeholder_nao_resolvido`) antes de
# qualquer checagem de unidade ser possível.
_FAMILIA_POR_UNIDADE_DE_PREMISSA: dict[str, tuple[str, ...]] = {
    "pp": ("pp", "num"),
    "moeda": ("moeda", "num"),
    "anos": ("num0",),
}


def _formato_compativel(formato: str, prefixos: tuple[str, ...]) -> bool:
    return any(formato == p or formato.startswith(p) for p in prefixos)


def _achado_formato_incompativel(entrada: dict, catalogo: dict, caso: dict) -> Achado | None:
    """B11 (achado S3): o formato de um placeholder tem de casar com a
    unidade do valor que ele exibe -- `{{caso:cenarios.base.premissas.wacc|
    pct1}}` mostrava "1.000,0%" (multiplicou por 100 um valor que já estava
    em pontos percentuais) com rc 0 antes desta correção; nada checava
    formato contra unidade.

    `entrada`: uma linha do `log` que `placeholders.resolver` devolve
    (`{"onde", "tipo", "caminho", "formato", "bruto", "resolvido"}`) --
    só placeholders que JÁ resolveram chegam aqui (um que falhou vira
    `placeholder_nao_resolvido` antes, nunca log). Dois casos, deliberadamente
    parciais (5C/5D publicam unidade para mais caminhos de `resultados`):

    - `tipo == "caso"`: só quando o caminho termina em `...premissas.<nome>`
      (o INPUT de um cenário) -- a unidade vem do catálogo
      (`premissas.<rota>.<nome>.unidade`, `rota` = `caso.rota`). Caminho que
      não bate esse formato, ou rota/premissa fora do catálogo, não é
      checado (não é o que B11 pediu resolver).
    - `tipo == "resultados"`: heurística pelo NOME do último segmento --
      termina em '_%' exige formato 'pp*'; é exatamente 'upside' exige
      'pct*'. Qualquer outro caminho de `resultados` não é checado aqui.
    """
    if entrada.get("tipo") == "caso":
        partes = (entrada.get("caminho") or "").split(".")
        if len(partes) < 2 or partes[-2] != "premissas":
            return None
        nome_premissa = partes[-1]
        rota = caso.get("rota") if isinstance(caso, dict) else None
        info = catalogo.get("premissas", {}).get(rota, {}).get(nome_premissa)
        if info is None:
            return None
        unidade = info.get("unidade")
        prefixos = _FAMILIA_POR_UNIDADE_DE_PREMISSA.get(unidade)
        if prefixos is None:
            return None
        if _formato_compativel(entrada["formato"], prefixos):
            return None
        return Achado("HARD_FAIL", "formato_incompativel_com_unidade", entrada["onde"], {
            "caminho": entrada["caminho"], "formato": entrada["formato"], "unidade": unidade,
        })

    if entrada.get("tipo") == "resultados":
        caminho = entrada.get("caminho") or ""
        ultimo = caminho.rsplit(".", 1)[-1]
        if ultimo.endswith("_%"):
            unidade_esperada, prefixos = "pp", ("pp",)
        elif ultimo == "upside":
            unidade_esperada, prefixos = "pct", ("pct",)
        else:
            return None
        if _formato_compativel(entrada["formato"], prefixos):
            return None
        return Achado("HARD_FAIL", "formato_incompativel_com_unidade", entrada["onde"], {
            "caminho": caminho, "formato": entrada["formato"], "unidade": unidade_esperada,
        })

    return None


def _achados_prosa(entrega: dict, catalogo: dict) -> list[Achado]:
    """`placeholder_nao_resolvido`, `placeholder_malformado`, `numero_sem_
    proveniencia` e `formato_incompativel_com_unidade` (todos HARD FAIL)
    sobre todo campo de prosa de `analise`.

    B1 (achado F1): a busca de dígito solto e a busca de placeholder
    malformado rodam sobre o texto ORIGINAL com só os placeholders
    RECONHECIDOS removidos (nunca sobre o texto resolvido -- um placeholder
    que formata para "61,91" não pode disparar `numero_sem_proveniencia`
    sobre o próprio número que ele legitimou). Qualquer `{{...}}` que sobrar
    depois desse desconto é malformado por definição: o dígito dentro dele
    permanece no texto despido e conta normalmente para `numero_sem_
    proveniencia` -- um bloco malformado não ganha imunidade nenhuma.

    B11 (achado S3): cada linha do `log` de resolução (um placeholder que
    RESOLVEU, com sucesso) passa por `_achado_formato_incompativel` -- ver
    ali o alcance exato (parcial de propósito).
    """
    achados: list[Achado] = []
    idioma = entrega["execucao"]["idioma"]
    caso = entrega.get("caso") or {}
    fontes = {"resultados": entrega.get("resultados"), "caso": caso}

    for onde, texto in _campos_de_prosa(entrega):
        _resolvido, log, erros = placeholders.resolver(texto, fontes, idioma, onde)
        for erro in erros:
            achados.append(Achado("HARD_FAIL", "placeholder_nao_resolvido", onde,
                                  {"token": erro["token"], "razao": erro["razao"]}))

        despido = _PADRAO_PLACEHOLDER_RECONHECIDO.sub("", texto)

        for sobra in _PADRAO_PLACEHOLDER_QUALQUER.finditer(despido):
            achados.append(Achado("HARD_FAIL", "placeholder_malformado", onde,
                                  {"trecho": sobra.group(0)}))

        if _PADRAO_DIGITO.search(despido):
            achados.append(Achado("HARD_FAIL", "numero_sem_proveniencia", onde, {}))

        for entrada in log:
            achado_formato = _achado_formato_incompativel(entrada, catalogo, caso)
            if achado_formato is not None:
                achados.append(achado_formato)

    return achados


def _pares_diagnosticos(no, caminho: str):
    """B9 (achado S1 generalizado): gera `(caminho, campo_base, campo_chaves,
    lista_diagnosticos, lista_chaves)` para cada par `diagnosticos`/
    `diagnosticos_chaves` OU `diagnosticos_unicos`/`diagnosticos_unicos_chaves`
    encontrado em QUALQUER profundidade de `no` (varredura recursiva de todo
    `resultados.json`) -- "todo `diagnosticos`, onde quer que apareça" (brief
    da onda de correção), não uma lista fixa de lugares conhecidos hoje
    (`cenarios`, `sotp.partes[*]`, `reversa.teto_do_crescimento_gratuito`,
    grades de sensibilidade). Uma publicação nova da integração amanhã (uma
    quinta fatia que emita diagnósticos em outro lugar do payload) cai sob
    esta checagem automaticamente, sem precisar editar este módulo -- a
    mesma disciplina de PROIBIDOS derivado em `test_relatorio_fronteira.py`
    (B5), agora aplicada a DADOS em vez de arquivos.
    """
    if isinstance(no, dict):
        for base, chaves in (("diagnosticos", "diagnosticos_chaves"),
                              ("diagnosticos_unicos", "diagnosticos_unicos_chaves")):
            lista = no.get(base)
            if isinstance(lista, list):
                yield caminho, base, chaves, lista, no.get(chaves)
        for chave, valor in no.items():
            yield from _pares_diagnosticos(valor, f"{caminho}.{chave}" if caminho else str(chave))
    elif isinstance(no, list):
        for indice, item in enumerate(no):
            yield from _pares_diagnosticos(item, f"{caminho}.{indice}")


def _achados_diagnostico_sem_chave(resultados: dict) -> list[Achado]:
    """`diagnostico_sem_chave` (HARD FAIL): cobre TRÊS formas de quebra, em
    todo par `diagnosticos`/`diagnosticos_chaves` (ou `diagnosticos_unicos`/
    `diagnosticos_unicos_chaves`) publicado em `resultados.json` -- B9
    (achado S1): antes desta correção, a checagem só olhava `null` DENTRO
    de uma `diagnosticos_chaves` que já existisse (`isinstance(chaves, list)`
    -- se a chave sumisse inteira, ou tivesse comprimento diferente do
    `diagnosticos` correspondente, nada disparava; rc 0. E só em dois
    lugares fixos (`cenarios`, grades) -- `sotp.partes[*]` e
    `reversa.teto_do_crescimento_gratuito` (S1 original) não eram cobertos
    nem por acidente.

    1. AUSENTE: `diagnosticos` existe mas `diagnosticos_chaves` não (ou não
       é lista) -- a correção é da integração, nunca do relatório.
    2. COMPRIMENTO DIFERENTE: as duas listas existem mas não são paralelas.
    3. `null` num item: a mensagem do motor não bateu com exatamente uma
       chave do vocabulário (mesma checagem de antes desta correção).
    """
    achados: list[Achado] = []

    for caminho, campo_base, campo_chaves, diagnosticos, chaves in _pares_diagnosticos(resultados, "resultados"):
        onde_chaves = f"{caminho}.{campo_chaves}"
        if not isinstance(chaves, list):
            achados.append(Achado("HARD_FAIL", "diagnostico_sem_chave", onde_chaves,
                                  {"razao": f"'{campo_chaves}' ausente (esperada ao lado de '{campo_base}')"}))
            continue
        if len(chaves) != len(diagnosticos):
            achados.append(Achado("HARD_FAIL", "diagnostico_sem_chave", onde_chaves, {
                "razao": (f"comprimento {len(chaves)} diferente de "
                          f"'{caminho}.{campo_base}' (comprimento {len(diagnosticos)})"),
            }))
            continue
        for indice, chave in enumerate(chaves):
            if chave is None:
                achados.append(Achado("HARD_FAIL", "diagnostico_sem_chave", f"{onde_chaves}.{indice}", {
                    "razao": "a mensagem do motor não corresponde a exatamente uma chave do vocabulário",
                }))

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

    B10 (achado S2): um cenário COM degrau mas sem `divergencia_de_base_%`
    numérico (ausente, `null`, texto, o que for) é HARD FAIL
    `degrau_sem_divergencia_de_base` -- antes desta correção, esse mesmo
    `continue` silenciava o caso: rc 0, sem disclosure nenhum, embora o
    contrato (`caso._validar_degrau`/o motor) sempre publique esse campo
    junto de `degrau` -- ausência de campo de contrato não pode desaparecer
    em silêncio, mesmo que a integração garanta a presença hoje (defesa em
    profundidade: a integração é quem tem de continuar garantindo isso, e
    um rename/typo futuro reprova AQUI, não em silêncio).
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
        onde_valor = f"resultados.cenarios.{nome}.degrau.divergencia_de_base_%"
        if not isinstance(valor, (int, float)) or isinstance(valor, bool):
            achados.append(Achado("HARD_FAIL", "degrau_sem_divergencia_de_base", onde_valor,
                                  {"cenario": nome}))
            continue
        if abs(valor) > limiar:
            achados.append(Achado("REQUIRED_DISCLOSURE", "divergencia_de_base_degrau", onde_valor, {
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


def _achado_bases_divergentes(resultados: dict) -> Achado | None:
    """`multiplos_com_bases_diferentes` (HARD FAIL) -- B12 (achado S4): o
    múltiplo justo da manchete (`manchete.multiplo`) e o múltiplo de tela
    (`mercado_tela`) têm de comparar a MESMA base (`ebitda`/`nopat`/`pl`/…)
    -- o par só faz sentido lado a lado quando os dois medem a mesma coisa.
    Antes desta correção nada comparava os dois: um `mercado_tela` em base
    'pl' ao lado de um múltiplo justo em base 'ebitda' renderizava os dois
    números lado a lado, rc 0, contrato quebrado sem aviso nenhum. Ausente
    (SOTP, sem `manchete.multiplo`) não dispara -- não há par para comparar.
    """
    manchete = resultados.get("manchete") or {}
    multiplo = manchete.get("multiplo")
    mercado_tela = resultados.get("mercado_tela")
    if not isinstance(multiplo, dict) or not isinstance(mercado_tela, dict):
        return None
    base_manchete = multiplo.get("base")
    base_mercado_tela = mercado_tela.get("base")
    if base_manchete == base_mercado_tela:
        return None
    return Achado("HARD_FAIL", "multiplos_com_bases_diferentes", "resultados.manchete.multiplo.base", {
        "base_manchete": str(base_manchete), "base_mercado_tela": str(base_mercado_tela),
    })


def _achados_exhibits(entrega: dict) -> list[Achado]:
    """As quatro regras HARD FAIL de rastreabilidade de exhibits (5B/G1-G4)
    mais a QUALITY WARNING de série curta (5B, "Regras de QC") -- uma
    passada por TODOS os exhibits/séries/overlays declarados em
    `analise.exhibits`, acumulando todo achado encontrado (nunca para no
    primeiro problema -- mesma disciplina de `_achados_diagnostico_sem_
    chave`). A resolução propriamente dita (fonte/fórmula/chave -> número)
    é feita por `exhibits.resolver_serie`/`exhibits.resolver_overlay`; este
    módulo só captura `exhibits.SerieInvalida` por item e nomeia o achado.

    `serie_de_tamanho_incompativel` (dentro de `resolver_serie`) e
    `serie_curta_sem_nota_janela` (aqui, sobre os tamanhos das séries que
    RESOLVERAM com sucesso) são as duas regras que olham o COMPRIMENTO da
    série -- a segunda nunca impede emitir (QUALITY WARNING), a primeira
    sempre impede (HARD FAIL).
    """
    achados: list[Achado] = []
    exhibits_decl = ((entrega.get("analise") or {}).get("exhibits")) or []
    dados = entrega.get("dados") or {}
    resultados = entrega.get("resultados") or {}
    caso = entrega.get("caso") or {}

    for exhibit in exhibits_decl:
        tamanhos_resolvidos: list[int] = []

        for indice, serie in enumerate(exhibit.get("series", [])):
            try:
                valores, _origem = exhibits.resolver_serie(exhibit, indice, serie, dados, resultados)
            except exhibits.SerieInvalida as erro:
                if erro.codigo == "serie_nao_rastreavel":
                    achados.append(Achado("HARD_FAIL", "serie_nao_rastreavel", erro.onde, erro.params))
                elif erro.codigo == "formula_invalida":
                    achados.append(Achado("HARD_FAIL", "formula_invalida", erro.onde, erro.params))
                elif erro.codigo == "serie_de_tamanho_incompativel":
                    achados.append(Achado("HARD_FAIL", "serie_de_tamanho_incompativel", erro.onde, erro.params))
                continue
            if isinstance(valores, list):
                tamanhos_resolvidos.append(len(valores))

        for indice, overlay in enumerate(exhibit.get("overlays") or []):
            try:
                exhibits.resolver_overlay(exhibit, indice, overlay, resultados, caso)
            except exhibits.SerieInvalida as erro:
                achados.append(Achado("HARD_FAIL", "overlay_nao_resolvido", erro.onde, erro.params))

        if tamanhos_resolvidos and min(tamanhos_resolvidos) < 10 and not exhibit.get("nota_janela"):
            exhibit_id = exhibit["id"]
            achados.append(Achado("QUALITY_WARNING", "serie_curta_sem_nota_janela",
                                  f"analise.exhibits.{exhibit_id}",
                                  {"exhibit": exhibit_id, "tamanho": min(tamanhos_resolvidos)}))

    return achados


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

    achados.extend(_achados_prosa(entrega, catalogo))
    achados.extend(_achados_exhibits(entrega))

    resultados = entrega.get("resultados") or {}
    achados.extend(_achados_diagnostico_sem_chave(resultados))
    achados.extend(_achados_divergencia_de_base(resultados, catalogo, idioma))

    achado_bases = _achado_bases_divergentes(resultados)
    if achado_bases is not None:
        achados.append(achado_bases)

    achado_autocontido = _achado_autocontido(html)
    if achado_autocontido is not None:
        achados.append(achado_autocontido)

    return achados

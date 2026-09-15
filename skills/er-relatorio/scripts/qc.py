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

Fatia 5D, item 5, Task 2 (as regras da §11 que pertencem à Tese, D6):
`perguntas_da_tese_incompletas`, `vinculo_fora_do_vocabulario`,
`faixa_fora_de_ordem`, `fronteira_com_preco_alvo` e `analise_sem_reversa`
(HARD FAIL); `limitacao_metodologica` (REQUIRED DISCLOSURE);
`tese_dependente_de_uma_premissa` (QUALITY WARNING). Mais duas referências da
Tese que não resolvem, da família de `overlay_nao_resolvido`:
`premissa_decisiva_fora_do_cenario` e `limitacao_desconhecida` (HARD FAIL).
A lista de prosa cobre todo campo de texto da Tese. Ver `_achados_da_tese`.

Fatia 5D, item 5, Task 3: a lista de prosa saiu deste módulo para
`placeholders.campos_de_prosa`, a única que o QC, o log da Evidência
(`builder.py`) e o texto da Tese (`render.py`) leem — e passou a cobrir também
`pergunta`, `nota_janela` e `caption` de cada exhibit.

Fatia 5D, onda de correção da revisão final (F2 e N10): `fronteira_com_preco_
alvo` deixou de reconhecer preço-alvo pelo nome do campo (`preco_acao`) e lê o
mapa das conclusões de valor que a integração publica (`catalogo.conclusoes_de_
valor`, por `placeholders.conclusao_de_valor`), nos três lugares por onde um
número de `resultados` chega à Tese: placeholder da prosa, série `engine` e
overlay. Sob fronteira, a limitação de escopo sai como REQUIRED DISCLOSURE
(`fronteira_de_escopo_declarada`), e um catálogo que não rotula a classe ou não
publica o mapa é HARD FAIL (`fronteira_de_escopo_desconhecida`). Ver
`_achados_fronteira_de_escopo`.

Fatia 5E, item 5, Task 2 (D3): as regras da §11 que dependem do ledger —
`insumo_sem_proveniencia`, `usado_em_fora_dos_insumos`, `insumo_nao_reconciliado`,
`conflito_de_fontes_silenciado`, `referencia_fora_do_ledger`,
`dataset_sem_proveniencia` e `insumos_do_caso_desconhecidos` (HARD FAIL);
`insumo_estimado`, `sem_contraprova_independente`, `lacuna_material` e
`consenso_indisponivel` (REQUIRED DISCLOSURE); `concentracao_de_fontes` (QUALITY
WARNING). Nenhum vocabulário de evidência mora aqui: o que é insumo sai do mapa
`catalogo.insumos_do_caso` (`placeholders.insumos_do_caso`), e "é estimativa" e
"lacuna que vira disclosure" saem das flags do contrato `ledger/1` que `avaliar`
recebe (`entrega.ler_contrato_do_ledger`). Ver `_achados_do_ledger`.

Fatia 5F, item 5, Task 4 (D4, D5, D6, D11, D13): as regras da §11 que pertencem à
Valuation — `conservacao_de_capital_nao_fecha`, `premissa_central_fora_do_ponto_
central_da_grade` e `eixo_obrigatorio_da_reversa_sem_raiz` (REQUIRED DISCLOSURE),
`sensibilidade_pouco_informativa` (QUALITY WARNING) e `eixos_de_reversa_desconhecidos`
(HARD FAIL). `multiplos_com_bases_diferentes` passa a cobrir o par forward; a premissa
decisiva, o vínculo e a contraprova passam a ler as partes de SOTP. Nenhum limiar de
metodologia: a conservação acende pela chave que a integração publica, o eixo
obrigatório pela flag do catálogo, e o ponto central por igualdade exata entre dois
números do mesmo caso. Ver `_achados_da_valuation`.
"""

import json
import math
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


def _objeto(valor) -> dict:
    return valor if isinstance(valor, dict) else {}


def _lista(valor) -> list:
    return valor if isinstance(valor, list) else []


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

    for onde, texto in placeholders.campos_de_prosa(entrega):
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
    """`divergencia_de_base_degrau` (REQUIRED DISCLOSURE): a integração
    sinalizou, num cenário com degrau, que a divergência de base passa do
    limiar DELA — parte do incremento que o degrau parece criar vem do
    descasamento entre as duas bases (LL x ROE.VPA), não do próprio degrau.

    Onda de correção da revisão final da 5C (F1): esta função NÃO compara
    limiar nenhum. Até ali ela aplicava `|divergencia_de_base_%| >
    catalogo.disclosures.divergencia_de_base_degrau.limiar_pct` — uma decisão
    metodológica tomada no relatório e congelada no build: o laboratório ao
    vivo movia o preço (e a divergência) sem que o disclosure se movesse. A
    decisão passou para a integração (`avaliar.py`, espelhada na fachada do
    navegador), que publica a chave em `degrau.diagnosticos_chaves`; o
    catálogo NOMEIA essa chave (`disclosures.divergencia_de_base_degrau.
    chave`) — nenhum literal de chave de diagnóstico mora neste módulo —, e
    esta função só a consome. O número publicado continua impresso na
    mensagem. Defesa em profundidade da mesma família do B10: um degrau sem
    `diagnosticos_chaves` é HARD FAIL `diagnostico_sem_chave`, nomeando o
    caminho — consumir a chave não pode abrir um caminho em que o disclosure
    some em silêncio.

    B8/A4 (achado F7): a explicação vem do catálogo
    (`catalogo.disclosures.divergencia_de_base_degrau.texto`). A mensagem no
    dicionário do relatório (`assets/i18n/<idioma>.json`) é só o MOLDE —
    "declare isso ao leitor" — o "porquê" (`{texto}`) é injetado aqui, vindo
    do catálogo, nunca hardcoded no relatório.

    B13 (achado S5): `params` carrega `valor` como NÚMERO cru
    (`round(valor, 1)` — é o que `qc.json` expõe para quem consome o achado
    como dado, e o que o teste de contrato trava com `pytest.approx`);
    `valor_fmt` é a MESMA informação, formatada por `placeholders.formatar(...,
    "pp1", idioma)` (separador decimal do idioma, sufixo '%' já embutido) — é
    o que o MOLDE do dicionário usa para montar a mensagem. Antes do B13 o
    molde interpolava o número cru direto via `.format()`, que usa `str()`:
    decimal com PONTO ("16.4%") numa página cujo upside ao lado usa vírgula
    ("16,4%").

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
    chave_do_disclosure = disclosure_catalogo["chave"]
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
        chaves = degrau.get("diagnosticos_chaves")
        if not isinstance(chaves, list):
            achados.append(Achado("HARD_FAIL", "diagnostico_sem_chave",
                                  f"resultados.cenarios.{nome}.degrau.diagnosticos_chaves",
                                  {"razao": "'diagnosticos_chaves' ausente (esperada ao lado de todo 'degrau')"}))
            continue
        if chave_do_disclosure in chaves:
            achados.append(Achado("REQUIRED_DISCLOSURE", "divergencia_de_base_degrau", onde_valor, {
                "cenario": nome,
                "valor": round(valor, 1),
                "valor_fmt": placeholders.formatar(valor, "pp1", idioma),
                "texto": texto,
            }))

    return achados


# Fatia 5B, item 5, Task 2 (primeira vez que este relatório embute uma
# biblioteca JS de terceiros inteira -- uPlot vendorizado): o CONTEÚDO de um
# elemento <script> é texto JS puro (a "script data state" do HTML5 nunca
# decodifica marcação ali dentro), então uma atribuição de código legítima
# como 'data=g.slice()' (uPlot minificado de verdade tem isso) casa com
# `_PADRAO_ATRIBUTO_REF` (`data\s*=\s*(\S+)`) exatamente como um atributo
# HTML casaria -- falso positivo comprovado (`data=g.slice(),en=g[0],...`),
# nada a ver com recurso externo. `_sem_conteudo_de_script` neutraliza SÓ o
# MIOLO de cada <script>...</script> antes da varredura (as três funções
# abaixo) -- a TAG em si nunca é tocada, então um `<script src="...">`
# externo de verdade continua batendo normalmente (ver
# `test_referencia_nao_autocontida_e_hard_fail_em_qualquer_forma`, que
# cobre exatamente esse caso). Não se aplica a <style> -- CSS não tem essa
# ambiguidade, e a regra precisa continuar varrendo `@import`/`url(` ali
# dentro (mesmo teste, casos de `<style>`).
_PADRAO_SCRIPT_BLOCO = re.compile(r'(<script\b[^>]*>)(.*?)(</script\s*>)', re.IGNORECASE | re.DOTALL)


def _sem_conteudo_de_script(html_texto: str) -> str:
    return _PADRAO_SCRIPT_BLOCO.sub(lambda m: m.group(1) + m.group(3), html_texto)


# A2 (onda de correção da revisão final, achado F2): neutralizar o miolo do
# <script> para a varredura de ATRIBUTO está certo (o falso positivo do uPlot
# é real), mas deixou o miolo inteiro sem exame nenhum -- a revisão provou,
# ponta a ponta, que `img.src` em runtime, `fetch(`, `XMLHttpRequest`,
# `WebSocket`, `new Worker` e um `<link>` injetado por JS passavam com rc 0.
# Um relatório é artefato OFFLINE que o analista abre e reenvia por e-mail:
# referência viva é vazamento de dado, e é exatamente isso que
# `relatorio_nao_autocontido` existe para mecanizar.
#
# Duas regras, ambas sobre o MIOLO de cada <script> (nunca sobre a tag, que
# a varredura de atributo já cobre):
#
# 1. TOKEN DE CHAMADA de rede. VERIFICADO: contagem 0 para cada um dos sete
#    no uPlot vendorizado, em `graficos.js`, em `svg.js` e nos scripts
#    estáticos do template -- a regra estrita não custa nada hoje.
# 2. ATRIBUIÇÃO de `src`/`srcset`/`href` a um LITERAL de texto, validado
#    pela MESMA whitelist da varredura de atributo (`#fragmento`/URI
#    `data:`) -- `brasao.src = "https://cdn..."` e `link.href = "https://..."`
#    reprovam; `ancora.href = "#secao"` não. Só literal: `el.src = url`
#    (variável) continua fora do alcance de uma varredura textual, e
#    registrar isso é mais honesto do que fingir cobertura.
#
# O que NÃO entra (decisão registrada): uma cláusula sobre o LITERAL
# 'http://'/'https://' solto no miolo. Ela exigiria remover comentário antes
# (o bundle do uPlot tem um `https://` no banner de licença) e mesmo assim
# daria falso positivo no nosso próprio código -- `svg.js` escreve
# 'http://www.w3.org/2000/svg', o namespace XML de todo <svg>, que não é
# referência carregada de lugar nenhum.
_PADRAO_CHAMADA_DE_REDE = re.compile(
    r"\bfetch\s*\(|\bXMLHttpRequest\b|\bWebSocket\s*\(|\bnew\s+Worker\b|"
    r"\bimportScripts\s*\(|\bEventSource\s*\(|\bnavigator\s*\.\s*sendBeacon\b"
)
_PADRAO_ATRIBUICAO_DE_RECURSO = re.compile(
    r"""\.\s*(src|srcset|href)\s*=(?!=)\s*(?:"([^"]*)"|'([^']*)')""",
    re.IGNORECASE,
)


def _autocontido(valor: str) -> bool:
    """A whitelist única de "referência autocontida" (B6): `#fragmento` ou
    URI `data:`. Usada pelas duas varreduras -- atributo HTML e atribuição
    dentro de <script> -- para que nunca divirjam."""
    valor = valor.strip()
    return valor.startswith("#") or valor.startswith("data:")


def _chamada_de_rede_em_script(html_texto: str) -> tuple[str, str] | None:
    """Devolve `(trecho, valor)` da primeira busca de recurso externo dentro
    do MIOLO de um `<script>` — ou `None`. Ver o bloco acima para as duas
    formas reconhecidas e para o que ficou deliberadamente de fora."""
    for bloco in _PADRAO_SCRIPT_BLOCO.finditer(html_texto):
        miolo = bloco.group(2)
        chamada = _PADRAO_CHAMADA_DE_REDE.search(miolo)
        if chamada is not None:
            return chamada.group(0), chamada.group(0).strip()
        for atribuicao in _PADRAO_ATRIBUICAO_DE_RECURSO.finditer(miolo):
            valor = atribuicao.group(2) if atribuicao.group(2) is not None else atribuicao.group(3)
            if not _autocontido(valor):
                return atribuicao.group(0), valor
    return None


def _referencia_externa_invalida(html_texto: str) -> tuple[str, str] | None:
    """B6: devolve `(trecho, valor)` da primeira referência (`src=`/`href=`/
    `srcset=`/`data=`/`url(`/`@import`, com ou sem aspas) cujo valor não é
    `#fragmento` nem URI `data:` — ou `None` se todas as referências
    encontradas são autocontidas (ou não há nenhuma). `srcset` pode
    carregar vários candidatos separados por vírgula (cada um com um
    descritor de densidade/largura opcional) — cada candidato é validado
    separadamente.

    Fatia 5B (ver `_sem_conteudo_de_script` acima): a varredura roda sobre
    `html_texto` com o MIOLO de todo `<script>` neutralizado -- nunca sobre
    o texto cru -- para não confundir sintaxe de código embutido com
    atributo HTML.
    """
    def _primeiro_grupo(m: "re.Match[str]", inicio: int = 2) -> str:
        for grupo in m.groups()[inicio - 1:]:
            if grupo is not None:
                return grupo
        return ""

    html_texto = _sem_conteudo_de_script(html_texto)
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
        if not _autocontido(valor):
            return trecho, valor.strip()
    return None


def _achado_autocontido(html: str | None) -> Achado | None:
    """`relatorio_nao_autocontido` (HARD FAIL, Task 4/B6): nenhuma referência
    externa é aceita — CSS e JS são sempre inline, e toda referência de
    `src=`/`href=`/`srcset=`/`data=`/`url(`/`@import` tem de valer
    `#fragmento` ou URI `data:` (whitelist, ver `_referencia_externa_
    invalida`). A2 (achado F2): o MIOLO de cada `<script>`, que a
    neutralização tirou da varredura de atributo, é examinado pela SEGUNDA
    regra (`_chamada_de_rede_em_script`) — mesmo código de achado, para que
    toda asserção de "nenhum recurso externo" que já existe cubra as duas
    formas de uma vez. `html` só existe DEPOIS que `render.compor` roda;
    `builder.py` chama `avaliar()` duas vezes (A8/regra inviolável 2):
    primeiro com `html=None` (as regras desta função nunca disparam — nada
    para examinar ainda), depois com o HTML já composto EM MEMÓRIA, antes de
    gravar `relatorio.html` no disco. Um HARD FAIL nesta segunda passada
    descarta o HTML gerado; só `qc.json` sai.
    """
    if html is None:
        return None
    encontrado = _referencia_externa_invalida(html) or _chamada_de_rede_em_script(html)
    if encontrado is None:
        return None
    trecho, valor = encontrado
    return Achado("HARD_FAIL", "relatorio_nao_autocontido", "relatorio.html",
                  {"trecho": trecho.strip(), "valor": valor})


# Os pares "múltiplo justo da manchete × múltiplo de tela" que a página mostra lado a lado:
# o corrente (B12) e, desde a 5F (D5), o forward. Nomes do contrato `resultados/1`.
PARES_DE_MULTIPLOS: tuple[tuple[str, str], ...] = (
    ("multiplo", "mercado_tela"),
    ("multiplo_forward", "mercado_tela_forward"),
)


def _achados_bases_divergentes(resultados: dict) -> list[Achado]:
    """`multiplos_com_bases_diferentes` (HARD FAIL) -- B12 (achado S4): o
    múltiplo justo da manchete (`manchete.multiplo`) e o múltiplo de tela
    (`mercado_tela`) têm de comparar a MESMA base (`ebitda`/`nopat`/`pl`/…)
    -- o par só faz sentido lado a lado quando os dois medem a mesma coisa.
    Antes desta correção nada comparava os dois: um `mercado_tela` em base
    'pl' ao lado de um múltiplo justo em base 'ebitda' renderizava os dois
    números lado a lado, rc 0, contrato quebrado sem aviso nenhum. Ausente
    (SOTP, sem `manchete.multiplo`) não dispara -- não há par para comparar.

    Fatia 5F, Task 4 (D5): a mesma regra vale para o par forward
    (`manchete.multiplo_forward` × `mercado_tela_forward`), quando os dois
    existem — sem métrica forward declarada a tela forward é `null`, e não há
    par. Um achado por par divergente, na ordem de `PARES_DE_MULTIPLOS`.
    """
    manchete = _objeto(resultados.get("manchete"))
    achados: list[Achado] = []
    for campo_justo, campo_de_tela in PARES_DE_MULTIPLOS:
        justo, de_tela = manchete.get(campo_justo), resultados.get(campo_de_tela)
        if not isinstance(justo, dict) or not isinstance(de_tela, dict) or justo.get("base") == de_tela.get("base"):
            continue
        achados.append(Achado("HARD_FAIL", "multiplos_com_bases_diferentes", f"resultados.manchete.{campo_justo}.base", {
            "campo_justo": f"manchete.{campo_justo}", "campo_de_tela": campo_de_tela,
            "base_manchete": str(justo.get("base")), "base_mercado_tela": str(de_tela.get("base")),
        }))
    return achados


def _achados_unidade_desconhecida(resultados: dict, catalogo: dict) -> list[Achado]:
    """`unidade_desconhecida` (HARD FAIL) -- A4 (achado F7): toda grade 2D
    que o painel da Valuation desenha declara a `unidade` das suas células
    (`sensibilidades.py` publica `unidade` de propósito, ao lado de
    `metrica_de_referencia`); o relatório só sabe formatar as unidades que o
    catálogo de apresentação declara em `unidades`.

    É o tripwire que faltava: a revisão simulou um v10 que troca a métrica
    da grade (células viram múltiplo, `unidade` passa a "múltiplo
    EV/EBITDA") e o relatório desenhou **6,69 onde desenhava 61,91**, com o
    mesmo título, a mesma formatação e rc 0 -- porque nunca lia o campo que
    diz o que o número é. Agora a mesma troca reprova pelo NOME, antes de
    renderizar, e o conserto é do catálogo (camada de integração), nunca do
    relatório.

    Só `grades_2d` é varrida: é exatamente o que esta fatia desenha. As
    grades 1D (5C) entram aqui quando tiverem painel -- declarar a regra
    sobre um número que ninguém desenha seria proibir o que o relatório nem
    lê.
    """
    conhecidas = catalogo.get("unidades") or {}
    sensibilidades = resultados.get("sensibilidades")
    grades = sensibilidades.get("grades_2d") if isinstance(sensibilidades, dict) else None
    if not isinstance(grades, list):
        return []

    achados: list[Achado] = []
    for indice, grade in enumerate(grades):
        if not isinstance(grade, dict):
            continue
        unidade = grade.get("unidade")
        if not isinstance(unidade, str) or unidade not in conhecidas:
            achados.append(Achado(
                "HARD_FAIL", "unidade_desconhecida",
                f"resultados.sensibilidades.grades_2d.{indice}.unidade",
                {"unidade": str(unidade)},
            ))
    return achados


def _achados_datasets_do_exhibit(exhibit: dict, dados: dict) -> list[Achado]:
    """B1 (achado F3): `series_de_datasets_incompativeis` (HARD FAIL) --
    a única regra de exhibit que olha as séries ENTRE SI, em vez de cada uma
    contra o seu próprio dataset. A causa mora em `exhibits.checar_datasets_
    do_exhibit`; aqui só se nomeia o achado, como no resto deste módulo."""
    try:
        exhibits.checar_datasets_do_exhibit(exhibit, dados)
    except exhibits.SerieInvalida as erro:
        return [Achado("HARD_FAIL", "series_de_datasets_incompativeis", erro.onde, erro.params)]
    return []


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
        achados.extend(_achados_datasets_do_exhibit(exhibit, dados))
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


# --------------------------------------------------------------------------
# Fatia 5D, item 5, Task 2 (D1, D2, D4, D6): as regras da §11 que pertencem à
# Tese. A FORMA da Tese é recusa de contrato (`entrega.py`, código 1); aqui só
# o CONTEÚDO — o que depende do catálogo e dos números que a integração
# publicou. E3: nenhum nome de premissa, nenhum limiar, nenhuma regra de
# admissão de reversa e nenhuma regra que reconheça conclusão de valor pelo nome
# do campo moram neste módulo. O vocabulário de vínculo sai do
# catálogo (`catalogo.premissas.<rota>` ∪ `catalogo.blocos`, D2), e o que torna
# uma limitação "de reversa" é a declaração `catalogo.limitacoes.<chave>.afeta`
# da integração — nunca o nome da chave.
# --------------------------------------------------------------------------

# §7 do desenho: de três a cinco perguntas — as três alavancas, cada uma uma
# vez, e até duas específicas.
MINIMO_DE_PERGUNTAS: int = 3
MAXIMO_DE_PERGUNTAS: int = 5
MAXIMO_DE_PERGUNTAS_ESPECIFICAS: int = 2

# O bloco de `resultados` que a Análise exige (§5: o M4 entrega "valuation +
# reversa + sensibilidades"; §11: fair value sem reversa é HARD FAIL). É nome de
# contrato `resultados/1` — a chave cuja presença o QC confere, e o valor que uma
# limitação declara em `afeta` quando é ela que o suprime —, não metodologia:
# POR QUE a reversa é impossível num caso é saber só da integração. Declarado em
# `entrega.py` desde a 5F (D12), cuja forma também o lê: o julgamento do que está no
# preço só cabe com a reversa.
BLOCO_DA_REVERSA: str = contrato_entrega.BLOCO_DA_REVERSA

# De onde cada ponta da faixa lê o seu preço (D1): `resultados.cenarios.<nome>.
# valor.preco_acao`, o caminho que o contrato da faixa declara. É leitura de
# contrato, nunca reconhecimento de conclusão de valor: QUAIS números são
# conclusão de valor a integração declara no mapa `catalogo.conclusoes_de_valor`,
# que é o que `_achados_fronteira_de_escopo` lê (onda de correção da revisão
# final da 5D, F2 — a regra reconhecia preço-alvo pelo NOME do campo, e a célula
# da grade, o upside e o múltiplo justo passavam).
CAMINHO_DO_PRECO_DA_FAIXA: tuple[str, ...] = ("valor", "preco_acao")

# O namespace que lê `resultados` num placeholder, numa série `engine` e num
# overlay — o único em que mora conclusão de valor. `caso:` é o que o caso
# declara; `livre:` é, por definição, o que o contrato não sabe ler (N1 da
# revisão da 5D).
NAMESPACE_DOS_RESULTADOS: str = "resultados"

_SEM_VALOR: str = "—"


def _numero_finito(valor) -> bool:
    return isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor)


def _premissas_da_rota_no_catalogo(rota, catalogo: dict) -> dict:
    """`catalogo.premissas.<rota>` — vazio para rota que o catálogo não conhece, ou que
    não é texto."""
    if not isinstance(rota, str):
        return {}
    return _objeto(_objeto(catalogo.get("premissas")).get(rota))


def _premissas_da_rota(resultados: dict, catalogo: dict) -> dict:
    """`catalogo.premissas.<resultados.rota>` — as premissas que o catálogo
    declara para a rota que a integração publicou (vazio para rota que ele não
    conhece)."""
    return _premissas_da_rota_no_catalogo(resultados.get("rota"), catalogo)


# Fatia 5F, Task 4 (D13): as partes de SOTP. `resultados.sotp.partes[*]` publica `nome`
# (único pelo gate), `rota` e `premissas`, na ordem em que o caso declara as partes —
# leitura de contrato, nunca de metodologia.

def _parte_do_sotp(resultados: dict, nome) -> tuple[int, dict] | None:
    """O índice e a parte de `resultados.sotp.partes` cujo `nome` é `nome` — ou `None`,
    fora do SOTP ou quando nenhuma parte tem esse nome. O índice é o da parte no caso:
    `sotp.py` publica as partes na ordem em que o caso as declara."""
    if not isinstance(nome, str):
        return None
    for indice, parte in enumerate(_lista(_objeto(resultados.get("sotp")).get("partes"))):
        if isinstance(parte, dict) and parte.get("nome") == nome:
            return indice, parte
    return None


def _rotas_do_valuation(resultados: dict) -> list[str]:
    """A rota do caso e, num SOTP, a de cada parte — sem repetição, na ordem publicada:
    as rotas cujas premissas o vínculo e o mecanismo da Tese podem nomear."""
    candidatas = [resultados.get("rota")]
    candidatas += [_objeto(parte).get("rota") for parte in _lista(_objeto(resultados.get("sotp")).get("partes"))]
    rotas: list[str] = []
    for rota in candidatas:
        if isinstance(rota, str) and rota not in rotas:
            rotas.append(rota)
    return rotas


def _achados_perguntas_da_tese(analise: dict) -> list[Achado]:
    """`perguntas_da_tese_incompletas` (HARD FAIL; §7, e §11: "perguntas da tese
    ausentes"): de três a cinco perguntas, cada tema obrigatório exatamente uma
    vez, no máximo duas específicas. Um achado só, com o retrato inteiro — cada
    critério aparece nos params, o que falhou e o que não falhou."""
    temas = [_objeto(pergunta).get("tema") for pergunta in _lista(analise.get("perguntas"))]
    obrigatorios = sorted(contrato_entrega.TEMAS_OBRIGATORIOS)
    ausentes = [tema for tema in obrigatorios if temas.count(tema) == 0]
    repetidos = [tema for tema in obrigatorios if temas.count(tema) > 1]
    especificas = temas.count(contrato_entrega.TEMA_ESPECIFICO)
    if (MINIMO_DE_PERGUNTAS <= len(temas) <= MAXIMO_DE_PERGUNTAS and not ausentes and not repetidos
            and especificas <= MAXIMO_DE_PERGUNTAS_ESPECIFICAS):
        return []
    return [Achado("HARD_FAIL", "perguntas_da_tese_incompletas", "analise.perguntas", {
        "quantidade": len(temas), "minimo": MINIMO_DE_PERGUNTAS, "maximo": MAXIMO_DE_PERGUNTAS,
        "temas_obrigatorios": ", ".join(obrigatorios),
        "temas_ausentes": ", ".join(ausentes) or _SEM_VALOR,
        "temas_repetidos": ", ".join(repetidos) or _SEM_VALOR,
        "especificas": especificas, "maximo_especificas": MAXIMO_DE_PERGUNTAS_ESPECIFICAS,
    })]


def _achados_vinculo_fora_do_vocabulario(analise: dict, resultados: dict, catalogo: dict) -> list[Achado]:
    """`vinculo_fora_do_vocabulario` (HARD FAIL, D2; §11: pergunta "sem vínculo
    econômico"): todo item de `perguntas[].vinculo` e de `positives`/
    `negatives[].mecanismo` é premissa da rota no catálogo ou bloco econômico do
    catálogo. Uma premissa nova numa v10 entra pelo catálogo, e o vínculo a
    aceita sem tocar neste módulo.

    Fatia 5F, Task 4 (D13): num SOTP, as premissas das rotas das partes também são
    vocabulário — a premissa decisiva de uma parte é da rota dela, e a pergunta que
    se liga a ela aponta para a mesma variável."""
    rotas = _rotas_do_valuation(resultados)
    vocabulario = set(_objeto(catalogo.get("blocos")))
    for rota_do_valuation in rotas:
        vocabulario |= set(_premissas_da_rota_no_catalogo(rota_do_valuation, catalogo))
    rota = ", ".join(rotas) or str(resultados.get("rota"))
    aceitos = ", ".join(sorted(vocabulario))

    listas = [(f"analise.perguntas.{indice}.vinculo", _objeto(pergunta).get("vinculo"))
              for indice, pergunta in enumerate(_lista(analise.get("perguntas")))]
    for lado in ("positives", "negatives"):
        listas += [(f"analise.{lado}.{indice}.mecanismo", _objeto(item).get("mecanismo"))
                   for indice, item in enumerate(_lista(analise.get(lado)))]

    achados: list[Achado] = []
    for onde, itens in listas:
        for posicao, item in enumerate(_lista(itens)):
            if isinstance(item, str) and item in vocabulario:
                continue
            achados.append(Achado("HARD_FAIL", "vinculo_fora_do_vocabulario", f"{onde}.{posicao}",
                                  {"item": str(item), "rota": rota, "aceitos": aceitos}))
    return achados


def _achados_premissas_decisivas(analise: dict, resultados: dict, catalogo: dict) -> list[Achado]:
    """`premissa_decisiva_fora_do_cenario` (HARD FAIL, D1): a `chave` de cada
    premissa decisiva é premissa da rota no catálogo e está declarada no cenário
    da manchete (`resultados.manchete.cenario`, que existe também sob fronteira)
    — o número mostrado ao lado dela é o desse cenário. Não é regra da §11: é a
    referência da Tese que não resolve, da família de `overlay_nao_resolvido`.

    Fatia 5F, Task 4 (D13): com `parte`, a premissa é da parte de SOTP que ela nomeia —
    a parte está em `resultados.sotp.partes`, e a chave é premissa da rota DELA no
    catálogo, declarada nas premissas dela. O número mostrado é o dessa parte."""
    premissas_da_rota = _premissas_da_rota(resultados, catalogo)
    cenario = _objeto(resultados.get("manchete")).get("cenario")
    cenario_da_manchete = _objeto(resultados.get("cenarios")).get(cenario) if isinstance(cenario, str) else None
    premissas_do_cenario = _objeto(_objeto(cenario_da_manchete).get("premissas"))

    achados: list[Achado] = []
    for indice, premissa in enumerate(_lista(analise.get("premissas_decisivas"))):
        premissa = _objeto(premissa)
        chave = premissa.get("chave")
        rota, parte_nomeada = str(resultados.get("rota")), _SEM_VALOR
        aceitas, declaradas = premissas_da_rota, premissas_do_cenario
        if "parte" in premissa:
            parte_nomeada = str(premissa.get("parte"))
            encontrada = _parte_do_sotp(resultados, premissa.get("parte"))
            parte = encontrada[1] if encontrada is not None else {}
            rota = str(parte.get("rota")) if encontrada is not None else _SEM_VALOR
            aceitas = _premissas_da_rota_no_catalogo(parte.get("rota"), catalogo)
            declaradas = _objeto(parte.get("premissas"))
        if isinstance(chave, str) and chave in aceitas and chave in declaradas:
            continue
        achados.append(Achado("HARD_FAIL", "premissa_decisiva_fora_do_cenario",
                              f"analise.premissas_decisivas.{indice}.chave",
                              {"chave": str(chave), "rota": rota, "cenario": str(cenario), "parte": parte_nomeada}))
    return achados


def _achados_faixa(entrega: dict, idioma: str) -> list[Achado]:
    """`faixa_fora_de_ordem` (HARD FAIL, D1/D6; §11: "inconsistência estrutural"):
    cada ponta da faixa nomeia um cenário de `resultados.cenarios` com preço
    publicado, os preços seguem `piso ≤ base ≤ teto` — comparação entre outputs
    que a integração publicou, nenhuma conta de valuation — e a base é o cenário
    da manchete. Um achado só, com os três nomes e os três preços."""
    faixa = _objeto(entrega.get("analise")).get("faixa")
    if not isinstance(faixa, dict):
        return []
    resultados = _objeto(entrega.get("resultados"))
    cenarios = _objeto(resultados.get("cenarios"))
    cenario_da_manchete = _objeto(resultados.get("manchete")).get("cenario")
    moeda = _objeto(entrega.get("caso")).get("moeda")

    nomes = {papel: faixa.get(papel) for papel in contrato_entrega.PAPEIS_DA_FAIXA}
    precos = {}
    for papel, nome in nomes.items():
        preco = cenarios.get(nome) if isinstance(nome, str) else None
        for campo in CAMINHO_DO_PRECO_DA_FAIXA:
            preco = _objeto(preco).get(campo)
        precos[papel] = preco if _numero_finito(preco) else None

    piso, base, teto = (precos[papel] for papel in contrato_entrega.PAPEIS_DA_FAIXA)
    em_ordem = None not in (piso, base, teto) and piso <= base <= teto
    if em_ordem and nomes["base"] == cenario_da_manchete:
        return []

    params = {papel: str(nome) for papel, nome in nomes.items()}
    for papel, preco in precos.items():
        params[f"preco_{papel}"] = (placeholders.formatar(preco, "moeda", idioma, moeda)
                                    if preco is not None else _SEM_VALOR)
    params["cenario_manchete"] = str(cenario_da_manchete)
    return [Achado("HARD_FAIL", "faixa_fora_de_ordem", "analise.faixa", params)]


def _referencias_a_resultados(entrega: dict) -> list[tuple[str, str, str]]:
    """`(onde, trecho, caminho)` de todo número de `resultados` que chega à aba Tese,
    pelos três lugares por onde ele chega: um placeholder `resultados:` num campo da
    lista de prosa (`placeholders.campos_de_prosa`), a `chave` de uma série `engine` e
    a `chave` de um overlay. `onde` nomeia o lugar pelo índice, como a lista de prosa
    nomeia os textos de cada exhibit."""
    referencias: list[tuple[str, str, str]] = []
    for onde, texto in placeholders.campos_de_prosa(entrega):
        for placeholder in _PADRAO_PLACEHOLDER_RECONHECIDO.finditer(texto):
            if placeholder.group(1) == NAMESPACE_DOS_RESULTADOS:
                caminho = placeholder.group(2).split("|", 1)[0].strip()
                referencias.append((onde, placeholder.group(0), caminho))
    for indice, exhibit in enumerate(_lista(_objeto(entrega.get("analise")).get("exhibits"))):
        for lista in ("series", "overlays"):
            for posicao, item in enumerate(_lista(_objeto(exhibit).get(lista))):
                chave = _objeto(item).get("chave")
                if not isinstance(chave, str):
                    continue
                namespace, separador, caminho = chave.partition(":")
                if separador and namespace == NAMESPACE_DOS_RESULTADOS:
                    referencias.append((f"analise.exhibits.{indice}.{lista}.{posicao}.chave", chave,
                                        caminho.strip()))
    return referencias


def _achados_fronteira_de_escopo(entrega: dict, catalogo: dict, idioma: str) -> list[Achado]:
    """Sob `resultados.fronteira_de_escopo` (D3; §14 do desenho) a Tese é uma conclusão
    condicional, sem preço-alvo de manchete.

    - HARD FAIL `fronteira_com_preco_alvo` (§11: "fronteira de escopo declarada com
      fair value por ação como conclusão principal"): a Tese declara `faixa`, ou um
      número que a integração declara conclusão de valor (`catalogo.conclusoes_de_
      valor`, lido por `placeholders.conclusao_de_valor`) chega a ela por um dos três
      lugares de `_referencias_a_resultados`. O achado nomeia o lugar, o caminho e a
      unidade da família. Onda de correção da revisão final (F2): a regra reconhecia
      só o campo `preco_acao`, pelo nome e só na prosa — a célula da grade, o upside,
      a tabela e o overlay sob uma pergunta passavam com RC=0. O preço e o múltiplo de
      tela não estão no mapa e continuam permitidos; `livre:` fica fora (N1).
    - REQUIRED DISCLOSURE `fronteira_de_escopo_declarada` (§11: "metodologia especial
      ou limitação de escopo"; N10): a fronteira entra no bloco de avisos, com o
      rótulo que o catálogo dá à classe — o bloco nunca diz "nenhum aviso" sob ela.
    - HARD FAIL `fronteira_de_escopo_desconhecida`: o catálogo não rotula a classe no
      idioma, ou não publica o mapa. Sem o mapa nenhum número de valor seria
      reconhecido: a regra falha fechada, e a correção é do catálogo.

    Fora da fronteira, `faixa` ausente é recusa de forma (`entrega.py`)."""
    fronteira = _objeto(entrega.get("resultados")).get("fronteira_de_escopo")
    if fronteira is None:
        return []
    classe = str(fronteira.get("classe")) if isinstance(fronteira, dict) else str(fronteira)
    analise = _objeto(entrega.get("analise"))
    onde_da_fronteira = "resultados.fronteira_de_escopo"

    achados: list[Achado] = []
    if "faixa" in analise:
        achados.append(Achado("HARD_FAIL", "fronteira_com_preco_alvo", "analise.faixa", {
            "classe": classe, "trecho": json.dumps(analise["faixa"], ensure_ascii=False, sort_keys=True),
            "caminho": _SEM_VALOR, "unidade": _SEM_VALOR,
        }))
    mapa = placeholders.conclusoes_de_valor(catalogo)
    if mapa is not None:
        for onde, trecho, caminho in _referencias_a_resultados(entrega):
            familia = placeholders.conclusao_de_valor(caminho, mapa)
            if familia is not None:
                unidade, _padrao = familia
                achados.append(Achado("HARD_FAIL", "fronteira_com_preco_alvo", onde, {
                    "classe": classe, "trecho": trecho, "caminho": caminho, "unidade": unidade,
                }))

    declaracao = _objeto(_objeto(catalogo.get("fronteiras_de_escopo")).get(classe))
    rotulo = _objeto(declaracao.get("rotulo")).get(idioma)
    rotulada = isinstance(rotulo, str) and bool(rotulo.strip())
    if mapa is None or not rotulada:
        achados.append(Achado("HARD_FAIL", "fronteira_de_escopo_desconhecida", onde_da_fronteira,
                              {"classe": classe, "idioma": idioma}))
    if rotulada:
        achados.append(Achado("REQUIRED_DISCLOSURE", "fronteira_de_escopo_declarada", onde_da_fronteira,
                              {"classe": classe, "rotulo": rotulo}))
    return achados


def _achados_reversa_e_limitacoes(resultados: dict, catalogo: dict, idioma: str) -> list[Achado]:
    """D4: a reversa que a Análise exige, e as limitações que a tornam impossível.

    Para cada chave de `resultados.limitacoes` — publicada pela integração, que
    é quem decide (`caso.reversa_indisponivel`) —, o catálogo declara o rótulo e
    o bloco de `resultados` que ela suprime (`afeta`):

    - declarada: REQUIRED DISCLOSURE `limitacao_metodologica`, com o rótulo do
      catálogo (§11: "metodologia especial ou limitação de escopo");
    - não declarada (sem entrada, sem rótulo no idioma, ou sem `afeta`): HARD
      FAIL `limitacao_desconhecida` — o relatório não sabe o que ela significa
      nem se ela justifica um bloco ausente, e a correção é do catálogo;
    - `resultados.reversa` ausente sem nenhuma limitação declarada com
      `afeta == "reversa"`: HARD FAIL `analise_sem_reversa`. `limitacoes`
      ausente conta como nenhuma: a regra falha fechada.

    O nome da chave nunca é lido. `reversa_com_degrau` suprime a reversa porque a
    integração o declara; uma limitação futura de outro assunto (5F) não muda
    esta regra."""
    declaradas = _objeto(catalogo.get("limitacoes"))
    publicadas = _lista(resultados.get("limitacoes"))
    blocos_suprimidos: set[str] = set()
    por_limitacao: list[Achado] = []
    for indice, chave in enumerate(publicadas):
        onde = f"resultados.limitacoes.{indice}"
        declaracao = _objeto(declaradas.get(chave)) if isinstance(chave, str) else {}
        rotulo = _objeto(declaracao.get("rotulo")).get(idioma)
        afeta = declaracao.get("afeta")
        if not (isinstance(rotulo, str) and rotulo.strip() and isinstance(afeta, str) and afeta.strip()):
            por_limitacao.append(Achado("HARD_FAIL", "limitacao_desconhecida", onde,
                                        {"limitacao": str(chave), "idioma": idioma}))
            continue
        blocos_suprimidos.add(afeta)
        por_limitacao.append(Achado("REQUIRED_DISCLOSURE", "limitacao_metodologica", onde,
                                    {"limitacao": chave, "rotulo": rotulo}))

    achados: list[Achado] = []
    if resultados.get(BLOCO_DA_REVERSA) is None and BLOCO_DA_REVERSA not in blocos_suprimidos:
        achados.append(Achado("HARD_FAIL", "analise_sem_reversa", f"resultados.{BLOCO_DA_REVERSA}", {
            "limitacoes": ", ".join(str(chave) for chave in publicadas) or _SEM_VALOR,
        }))
    return achados + por_limitacao


def _achados_tese_dependente_de_uma_premissa(analise: dict) -> list[Achado]:
    """`tese_dependente_de_uma_premissa` (QUALITY WARNING, §11): todas as
    perguntas ligadas a um vínculo de um item só — e ao mesmo item."""
    vinculos = [_objeto(pergunta).get("vinculo") for pergunta in _lista(analise.get("perguntas"))]
    de_um_item = [vinculo[0] for vinculo in vinculos
                  if isinstance(vinculo, list) and len(vinculo) == 1 and isinstance(vinculo[0], str)]
    if not vinculos or len(de_um_item) != len(vinculos) or len(set(de_um_item)) != 1:
        return []
    return [Achado("QUALITY_WARNING", "tese_dependente_de_uma_premissa", "analise.perguntas",
                   {"item": de_um_item[0]})]


def _achados_da_tese(entrega: dict, catalogo: dict, idioma: str) -> list[Achado]:
    """As regras de D6, na ordem do plano."""
    analise = _objeto(entrega.get("analise"))
    resultados = _objeto(entrega.get("resultados"))
    return (_achados_perguntas_da_tese(analise)
            + _achados_vinculo_fora_do_vocabulario(analise, resultados, catalogo)
            + _achados_premissas_decisivas(analise, resultados, catalogo)
            + _achados_faixa(entrega, idioma)
            + _achados_fronteira_de_escopo(entrega, catalogo, idioma)
            + _achados_reversa_e_limitacoes(resultados, catalogo, idioma)
            + _achados_tese_dependente_de_uma_premissa(analise))


# --------------------------------------------------------------------------
# Fatia 5E, item 5, Task 2 (D3): as regras da §11 que dependem do ledger.
# --------------------------------------------------------------------------

# §6.2, "reconciliação dos números materiais": dois números declarados — o do
# registro e o do caso — são o mesmo número quando `math.isclose` os aceita com
# estas duas tolerâncias. A relativa absorve só ruído de ponto flutuante e de
# arredondamento na sexta casa significativa; o piso absoluto decide o zero. É
# comparação de igualdade entre números declarados, nunca conta de valuation. A
# mesma tolerância decide se duas fontes do mesmo claim conflitam.
TOLERANCIA_RELATIVA_DE_RECONCILIACAO: float = 1e-6
TOLERANCIA_ABSOLUTA_DE_RECONCILIACAO: float = 1e-9

# §11, QUALITY WARNING "concentração excessiva de fontes": uma identidade que
# sustenta mais da metade dos insumos do caso, quando há ao menos quatro. É regra
# de QC do Fleet, não metodologia — por isso mora aqui, nomeada.
LIMIAR_DE_CONCENTRACAO_DE_FONTES: float = 0.5
MINIMO_DE_INSUMOS_PARA_CONCENTRACAO: int = 4


def _numero_declarado(valor) -> bool:
    """Número de JSON — `int` ou `float`, nunca booleano."""
    return isinstance(valor, (int, float)) and not isinstance(valor, bool)


def _mesmo_numero(a: float, b: float) -> bool:
    return math.isclose(a, b, rel_tol=TOLERANCIA_RELATIVA_DE_RECONCILIACAO,
                        abs_tol=TOLERANCIA_ABSOLUTA_DE_RECONCILIACAO)


def _numero_no_idioma(valor, idioma: str) -> str:
    return placeholders.formatar(valor, "num4", idioma) if _numero_finito(valor) else _SEM_VALOR


def _folhas_numericas(no, caminho: tuple = ()):
    """`(caminho pontuado, número)` de toda folha numérica de `no`, na ordem em que aparece. O
    índice de lista é segmento — como no caminho de um placeholder —, e booleano não é número."""
    if isinstance(no, dict):
        for chave, valor in no.items():
            yield from _folhas_numericas(valor, caminho + (str(chave),))
    elif isinstance(no, list):
        for indice, valor in enumerate(no):
            yield from _folhas_numericas(valor, caminho + (str(indice),))
    elif _numero_declarado(no):
        yield ".".join(caminho), no


def _caminhos_usados(registro: dict) -> list:
    return _lista(registro.get("usado_em"))


def _identidade(registro: dict) -> str | None:
    identidade = _objeto(registro.get("fonte")).get("identidade")
    return identidade if isinstance(identidade, str) and identidade.strip() else None


def _caminho_da_premissa_no_caso(cenario: str, chave: str) -> str:
    """Onde o caso declara o número de uma premissa de cenário: o mesmo lugar em que
    `resultados` a publica, `cenarios.<cenario>.premissas.<chave>` — o que
    `_achados_premissas_decisivas` confere no cenário da manchete. Conferido nas fixtures,
    rota a rota, na 5E: em `firm`, `equity`, `rampa` e no SOTP, toda premissa da rota que o
    cenário publicado declara está nesse caminho do caso."""
    return ".".join(("cenarios", cenario, "premissas", chave))


def _achados_insumo_sem_proveniencia(registros: list, insumos: dict) -> list[Achado]:
    nomeados = {caminho for _indice, registro in registros for caminho in _caminhos_usados(registro)
                if isinstance(caminho, str)}
    return [Achado("HARD_FAIL", "insumo_sem_proveniencia", f"caso.{caminho}", {"caminho": caminho})
            for caminho in insumos if caminho not in nomeados]


def _achados_usado_em_fora_dos_insumos(registros: list, insumos: dict) -> list[Achado]:
    achados: list[Achado] = []
    for indice, registro in registros:
        for posicao, caminho in enumerate(_caminhos_usados(registro)):
            if isinstance(caminho, str) and caminho in insumos:
                continue
            achados.append(Achado("HARD_FAIL", "usado_em_fora_dos_insumos",
                                  f"ledger.registros.{indice}.usado_em.{posicao}",
                                  {"id": str(registro.get("id")), "caminho": str(caminho)}))
    return achados


def _achados_insumo_nao_reconciliado(registros: list, insumos: dict, idioma: str) -> list[Achado]:
    achados: list[Achado] = []
    for indice, registro in registros:
        if "reconciliacao" in registro:
            continue
        valor = registro.get("valor")
        for caminho in _caminhos_usados(registro):
            if not (isinstance(caminho, str) and caminho in insumos):
                continue
            numero_do_caso = insumos[caminho]
            if _numero_declarado(valor) and _mesmo_numero(valor, numero_do_caso):
                continue
            achados.append(Achado("HARD_FAIL", "insumo_nao_reconciliado", f"ledger.registros.{indice}.valor", {
                "id": str(registro.get("id")), "caminho": caminho,
                "valor_registro": valor, "valor_caso": numero_do_caso,
                "valor_registro_fmt": _numero_no_idioma(valor, idioma),
                "valor_caso_fmt": _numero_no_idioma(numero_do_caso, idioma),
            }))
    return achados


def _achados_conflito_de_fontes_silenciado(registros: list) -> list[Achado]:
    grupos: dict = {}
    for indice, registro in registros:
        claim, periodo, valor = registro.get("claim"), registro.get("periodo"), registro.get("valor")
        if isinstance(claim, str) and isinstance(periodo, str) and _numero_declarado(valor):
            grupos.setdefault((claim, periodo), []).append((indice, registro))

    achados: list[Achado] = []
    for (claim, periodo), membros in grupos.items():
        valores = [registro["valor"] for _indice, registro in membros]
        divergem = any(not _mesmo_numero(a, b) for posicao, a in enumerate(valores) for b in valores[posicao + 1:])
        ids = [registro.get("id") for _indice, registro in membros]
        vencedores = [_objeto(registro.get("conflito")).get("vencedor") for _indice, registro in membros]
        declarado = any(isinstance(vencedor, str) and vencedor in ids for vencedor in vencedores)
        if divergem and not declarado:
            achados.append(Achado("HARD_FAIL", "conflito_de_fontes_silenciado", f"ledger.registros.{membros[0][0]}", {
                "claim": claim, "periodo": periodo, "ids": ", ".join(f"'{ident}'" for ident in ids),
            }))
        elif divergem:
            achados += _achados_insumo_sustentado_pela_fonte_vencida(claim, periodo, membros, vencedores, ids)
    return achados


def _achados_insumo_sustentado_pela_fonte_vencida(claim: str, periodo: str, membros: list, vencedores: list,
                                                  ids: list) -> list[Achado]:
    """Revisão da 5E (F3): um conflito com vencedor declarado não absolve o registro vencido que
    continua sustentando um número do caso. Todo membro do grupo com `usado_em` é o vencedor,
    declara o mesmo número dele ou traz `reconciliacao`; fora disso, HARD FAIL nomeando o registro
    usado e o vencedor — o valuation usaria o número que o próprio ledger declarou vencido."""
    vencedor = next(v for v in vencedores if isinstance(v, str) and v in ids)
    valor_do_vencedor = next(registro["valor"] for _indice, registro in membros if registro.get("id") == vencedor)
    achados: list[Achado] = []
    for indice, registro in membros:
        caminhos = [caminho for caminho in _caminhos_usados(registro) if isinstance(caminho, str)]
        if (not caminhos or registro.get("id") == vencedor or "reconciliacao" in registro
                or _mesmo_numero(registro["valor"], valor_do_vencedor)):
            continue
        achados.append(Achado("HARD_FAIL", "insumo_sustentado_pela_fonte_vencida", f"ledger.registros.{indice}", {
            "id": str(registro.get("id")), "vencedor": vencedor, "claim": claim, "periodo": periodo,
            "caminhos": ", ".join(f"'{caminho}'" for caminho in caminhos),
        }))
    return achados


def _achados_referencia_fora_do_ledger(entrega: dict, registros: list) -> list[Achado]:
    existentes = {registro.get("id") for _indice, registro in registros if isinstance(registro.get("id"), str)}
    citacoes: list[tuple[str, object]] = []
    for indice, registro in registros:
        onde = f"ledger.registros.{indice}"
        citacoes += [(f"{onde}.insumos.{posicao}", ident) for posicao, ident in enumerate(_lista(registro.get("insumos")))]
        conflito = registro.get("conflito")
        if isinstance(conflito, dict) and "vencedor" in conflito:
            citacoes.append((f"{onde}.conflito.vencedor", conflito["vencedor"]))
        if "contraprova_de" in registro:
            citacoes.append((f"{onde}.contraprova_de", registro["contraprova_de"]))
    consenso = _objeto(_objeto(entrega.get("analise")).get("consenso"))
    citacoes += [(f"analise.consenso.registros.{posicao}", ident)
                 for posicao, ident in enumerate(_lista(consenso.get("registros")))]
    for dataset_id, dataset in _objeto(entrega.get("dados")).items():
        citacoes += [(f"dados.{dataset_id}.ledger.{posicao}", ident)
                     for posicao, ident in enumerate(_lista(_objeto(dataset).get("ledger")))]
    return [Achado("HARD_FAIL", "referencia_fora_do_ledger", onde, {"id": str(ident)})
            for onde, ident in citacoes if not (isinstance(ident, str) and ident in existentes)]


def _achados_dataset_sem_proveniencia(entrega: dict) -> list[Achado]:
    dados = _objeto(entrega.get("dados"))
    usados: list[str] = []
    for exhibit in _lista(_objeto(entrega.get("analise")).get("exhibits")):
        if isinstance(exhibit, dict):
            usados += [dataset_id for dataset_id in exhibits.datasets_do_exhibit(exhibit, dados)
                       if dataset_id not in usados]
    return [Achado("HARD_FAIL", "dataset_sem_proveniencia", f"dados.{dataset_id}.ledger", {"dataset": dataset_id})
            for dataset_id in usados if not _lista(_objeto(dados.get(dataset_id)).get("ledger"))]


def _registros_estimados_que_sustentam_insumo(registros: list, insumos: dict, contrato) -> list:
    """Os `(índice, registro)` de estatuto com `e_estimativa` que sustentam um insumo do caso, na
    ordem do ledger: o registro com `usado_em` num insumo ou qualquer registro que ele cita em
    `insumos`, transitivamente e protegido contra ciclo (revisão da 5E, F2 — a §11 fala em input
    "baseado em" estimativa). Decide pela flag do contrato, nunca pelo nome do estatuto."""
    por_id = {registro["id"]: (indice, registro) for indice, registro in registros
              if isinstance(registro.get("id"), str)}
    alcancados: set = set()
    pilha = [(indice, registro) for indice, registro in registros
             if any(isinstance(caminho, str) and caminho in insumos for caminho in _caminhos_usados(registro))]
    while pilha:
        indice, registro = pilha.pop()
        if indice in alcancados:
            continue
        alcancados.add(indice)
        pilha += [por_id[ident] for ident in _lista(registro.get("insumos")) if isinstance(ident, str) and ident in por_id]

    def estimado(registro: dict) -> bool:
        estatuto = registro.get("estatuto")
        flags = contrato.estatutos.get(estatuto) if isinstance(estatuto, str) else None
        return bool(flags and flags["e_estimativa"])

    return [(indice, registro) for indice, registro in registros if indice in alcancados and estimado(registro)]


def _achados_insumo_estimado(estimados: list, idioma: str) -> list[Achado]:
    """Um aviso por registro estimado que sustenta insumo, com o valor e a unidade que ele declara: a
    Tese mostra o número do registro ao lado do claim (revisão da 5E, F4)."""
    return [Achado("REQUIRED_DISCLOSURE", "insumo_estimado", f"ledger.registros.{indice}", {
                "id": str(registro.get("id")), "claim": str(registro.get("claim")),
                "valor_fmt": _numero_no_idioma(registro.get("valor"), idioma), "unidade": str(registro.get("unidade")),
            }) for indice, registro in estimados]


def _achados_placeholder_em_dado_da_tese(analise: dict, registros: list, estimados: list) -> list[Achado]:
    """Revisão da 5E (F4): a Tese mostra campos de registros do ledger como dado — a linha do
    consenso (`claim`, `periodo`, `unidade`, `fonte.identidade`) e o aviso de estimativa (`claim`,
    `unidade`) — e não resolve placeholder neles. Um `{{...}}` ali sairia cru: HARD FAIL nomeando o
    campo."""
    citados = {ident for ident in _lista(_objeto(analise.get("consenso")).get("registros")) if isinstance(ident, str)}
    indices_estimados = {indice for indice, _registro in estimados}
    achados: list[Achado] = []
    for indice, registro in registros:
        campos: list[str] = []
        if isinstance(registro.get("id"), str) and registro["id"] in citados:
            campos += ["claim", "periodo", "unidade", "fonte.identidade"]
        if indice in indices_estimados:
            campos += [campo for campo in ("claim", "unidade") if campo not in campos]
        for campo in campos:
            valor = _objeto(registro.get("fonte")).get("identidade") if campo == "fonte.identidade" else registro.get(campo)
            if isinstance(valor, str) and "{{" in valor:
                achados.append(Achado("HARD_FAIL", "placeholder_em_dado_da_tese", f"ledger.registros.{indice}.{campo}",
                                      {"id": str(registro.get("id")), "campo": campo}))
    return achados


def _confirma(contraprova: dict, alvo: dict | None) -> bool:
    """§6.3: contraprova é CONFIRMAÇÃO independente do registro que sustenta a premissa
    (`alvo`). Conta só quando vem de outra `fonte.identidade` — a cópia da mesma fonte não
    conta — e declara o mesmo número do alvo, pela tolerância da reconciliação. Uma fonte que
    diverge só confirma quando declara a `reconciliacao`, que a Evidência mostra. Sem isso, uma
    "contraprova" que desmente o número suprimiria o disclosure em silêncio — e, com outro
    claim, nem o conflito entre fontes a veria."""
    if alvo is None:
        return False
    identidade, identidade_do_alvo = _identidade(contraprova), _identidade(alvo)
    if identidade is None or identidade_do_alvo is None or identidade == identidade_do_alvo:
        return False
    valor, valor_do_alvo = contraprova.get("valor"), alvo.get("valor")
    mesmo_numero = (_numero_declarado(valor) and _numero_declarado(valor_do_alvo)
                    and _mesmo_numero(valor, valor_do_alvo))
    return mesmo_numero or "reconciliacao" in contraprova


def _caminho_da_premissa_de_parte_no_caso(indice_da_parte: int, chave: str) -> str:
    """Onde o caso declara a premissa de uma parte de SOTP (fatia 5F, Task 4, D13):
    `sotp.partes.<índice>.premissas.<chave>`, com o índice da parte em
    `resultados.sotp.partes` (`_parte_do_sotp`). A integração publica as partes na ordem
    do caso, e o gate recusa chave com `.` ou `*`: o caminho nunca é ambíguo."""
    return ".".join(("sotp", "partes", str(indice_da_parte), "premissas", chave))


def _rotulo_da_premissa(premissas_da_rota: dict, chave, idioma: str) -> str:
    """O rótulo do catálogo de uma premissa da rota, ou o travessão: a mensagem de um aviso
    nunca mostra a chave crua, e o catálogo cobre o vocabulário que o gate aceita."""
    info = _objeto(premissas_da_rota.get(chave)) if isinstance(chave, str) else {}
    rotulo = _objeto(info.get("rotulo")).get(idioma)
    return rotulo if isinstance(rotulo, str) and rotulo.strip() else _SEM_VALOR


def _achados_sem_contraprova_independente(entrega: dict, registros: list, catalogo: dict,
                                          idioma: str) -> list[Achado]:
    """Fatia 5F, Task 4 (D13): com `parte`, o número da premissa mora na parte de SOTP — o
    caminho é o dela no caso, e o rótulo, o da rota dela. Uma parte que não existe já é o
    HARD FAIL `premissa_decisiva_fora_do_cenario`, e aqui não gera aviso."""
    resultados = _objeto(entrega.get("resultados"))
    cenario = str(_objeto(resultados.get("manchete")).get("cenario"))
    premissas_da_rota_do_caso = _premissas_da_rota(resultados, catalogo)

    achados: list[Achado] = []
    for posicao, premissa in enumerate(_lista(_objeto(entrega.get("analise")).get("premissas_decisivas"))):
        premissa = _objeto(premissa)
        chave = premissa.get("chave")
        if "parte" in premissa:
            encontrada = _parte_do_sotp(resultados, premissa.get("parte"))
            if encontrada is None:
                continue
            indice_da_parte, parte = encontrada
            caminho = _caminho_da_premissa_de_parte_no_caso(indice_da_parte, str(chave))
            premissas_da_rota = _premissas_da_rota_no_catalogo(parte.get("rota"), catalogo)
        else:
            caminho = _caminho_da_premissa_no_caso(cenario, str(chave))
            premissas_da_rota = premissas_da_rota_do_caso
        sustentam = {registro["id"]: registro for _indice, registro in registros
                     if caminho in _caminhos_usados(registro) and isinstance(registro.get("id"), str)}
        if any(_confirma(registro, sustentam.get(registro["contraprova_de"])) for _indice, registro in registros
               if isinstance(registro.get("contraprova_de"), str)):
            continue
        achados.append(Achado("REQUIRED_DISCLOSURE", "sem_contraprova_independente",
                              f"analise.premissas_decisivas.{posicao}.chave", {
                                  "chave": str(chave),
                                  "rotulo": _rotulo_da_premissa(premissas_da_rota, chave, idioma),
                                  "caminho": caminho,
                              }))
    return achados


def _achados_lacuna_material(ledger: dict, contrato) -> list[Achado]:
    achados: list[Achado] = []
    for indice, lacuna in enumerate(_lista(ledger.get("lacunas"))):
        lacuna = _objeto(lacuna)
        materialidade = lacuna.get("materialidade")
        flags = contrato.materialidades.get(materialidade) if isinstance(materialidade, str) else None
        if not (flags and flags["exige_disclosure"]):
            continue
        onde = f"ledger.lacunas.{indice}"
        achados.append(Achado("REQUIRED_DISCLOSURE", "lacuna_material", onde, {
            "id": str(lacuna.get("id")), "descricao": str(lacuna.get("descricao")),
            "tratamento": str(lacuna.get("tratamento")),
            "campos_de_prosa": {"descricao": f"{onde}.descricao", "tratamento": f"{onde}.tratamento"},
        }))
    return achados


def _achados_consenso_indisponivel(analise: dict) -> list[Achado]:
    ausente = _objeto(analise.get("consenso")).get("ausente")
    if not isinstance(ausente, dict):
        return []
    onde = "analise.consenso.ausente"
    return [Achado("REQUIRED_DISCLOSURE", "consenso_indisponivel", onde, {
        "ancora": str(ausente.get("ancora")), "razao": str(ausente.get("razao")),
        "campos_de_prosa": {"razao": f"{onde}.razao"},
    })]


def _achados_concentracao_de_fontes(registros: list, insumos: dict, idioma: str) -> list[Achado]:
    total = len(insumos)
    if total < MINIMO_DE_INSUMOS_PARA_CONCENTRACAO:
        return []
    sustentados: dict[str, set] = {}
    for _indice, registro in registros:
        identidade = _identidade(registro)
        if identidade is not None:
            sustentados.setdefault(identidade, set()).update(
                caminho for caminho in _caminhos_usados(registro) if isinstance(caminho, str) and caminho in insumos)

    achados: list[Achado] = []
    for identidade, caminhos in sustentados.items():
        parcela = len(caminhos) / total
        if parcela > LIMIAR_DE_CONCENTRACAO_DE_FONTES:
            achados.append(Achado("QUALITY_WARNING", "concentracao_de_fontes", "ledger.registros", {
                "identidade": identidade, "insumos": len(caminhos), "total": total,
                "parcela_fmt": placeholders.formatar(parcela, "pct0", idioma),
                "limiar_fmt": placeholders.formatar(LIMIAR_DE_CONCENTRACAO_DE_FONTES, "pct0", idioma),
            }))
    return achados


def _achados_do_ledger(entrega: dict, catalogo: dict, contrato, idioma: str) -> list[Achado]:
    """As regras de D3, na ordem do plano: os HARD FAIL, os REQUIRED DISCLOSURE e o QUALITY
    WARNING.

    - Os insumos são as folhas numéricas do CASO que o mapa da integração cobre
      (`catalogo.insumos_do_caso`, por `placeholders.insumo_do_caso`). Um caminho de `usado_em`
      é ligação válida só quando é um desses — nunca resolvido de novo no caso, para que um
      índice escrito de outro jeito (`-1`, `01`) não passe por insumo.
    - Sem o mapa, as regras que dependem dele falham fechadas: HARD FAIL
      `insumos_do_caso_desconhecidos`, nunca "nenhum insumo" — sem ele nenhum número seria
      exigido, e a correção é do catálogo.
    - Estimativa e disclosure de lacuna saem das flags do contrato lido (`e_estimativa`,
      `exige_disclosure`), nunca do nome do estatuto ou da materialidade.
    - Contraprova é confirmação (§6.3, `_confirma`): outra identidade e o mesmo número do
      registro que sustenta a premissa decisiva, ou a reconciliação declarada da divergência.
    - Os disclosures que citam prosa (`lacuna_material`, `consenso_indisponivel`) levam o texto
      cru, para o `qc.json`, e `campos_de_prosa: {<param>: <onde>}` — o `onde` de cada texto
      em `placeholders.campos_de_prosa`, pelo qual a Tese exibe o texto resolvido.
    - Tolerante a forma, como o resto do QC: roda também sobre entregas montadas em teste sem
      `entrega.carregar`."""
    analise = _objeto(entrega.get("analise"))
    ledger = _objeto(entrega.get("ledger"))
    registros = [(indice, registro) for indice, registro in enumerate(_lista(ledger.get("registros")))
                 if isinstance(registro, dict)]
    mapa = placeholders.insumos_do_caso(catalogo)
    insumos = None if mapa is None else {
        caminho: numero for caminho, numero in _folhas_numericas(_objeto(entrega.get("caso")))
        if placeholders.insumo_do_caso(caminho, mapa) is not None}

    achados: list[Achado] = []
    if insumos is None:
        achados.append(Achado("HARD_FAIL", "insumos_do_caso_desconhecidos", "catalogo.insumos_do_caso", {}))
    else:
        achados += (_achados_insumo_sem_proveniencia(registros, insumos)
                    + _achados_usado_em_fora_dos_insumos(registros, insumos)
                    + _achados_insumo_nao_reconciliado(registros, insumos, idioma))
    achados += (_achados_conflito_de_fontes_silenciado(registros)
                + _achados_referencia_fora_do_ledger(entrega, registros)
                + _achados_dataset_sem_proveniencia(entrega))
    estimados = [] if insumos is None else _registros_estimados_que_sustentam_insumo(registros, insumos, contrato)
    achados += (_achados_placeholder_em_dado_da_tese(analise, registros, estimados)
                + _achados_insumo_estimado(estimados, idioma)
                + _achados_sem_contraprova_independente(entrega, registros, catalogo, idioma)
                + _achados_lacuna_material(ledger, contrato)
                + _achados_consenso_indisponivel(analise))
    if insumos is not None:
        achados += _achados_concentracao_de_fontes(registros, insumos, idioma)
    return achados


# --------------------------------------------------------------------------
# Fatia 5F, item 5, Task 4 (D4, D6, D11): as regras da §11 que pertencem à Valuation. O
# relatório compara números publicados ou declarados e nunca guarda limiar de
# metodologia: a conservação de capital acende pela chave que a integração publica (o
# limiar é do motor), o eixo obrigatório da reversa sai da flag do catálogo, e o ponto
# central da grade é igualdade exata entre dois números do mesmo caso.
# --------------------------------------------------------------------------

# §11, QUALITY WARNING "sensibilidade pouco informativa": uma grade cujas células ficam
# todas dentro de 1% (relativo, `math.isclose`) do preço publicado do cenário que ela
# perturba. Limiar baixo de propósito: só acende a grade que praticamente não move o preço
# — a amplitude certa é do analista (vendor §4). Regra de QC do Fleet, não metodologia:
# por isso mora aqui, nomeada.
TOLERANCIA_DE_SENSIBILIDADE_POUCO_INFORMATIVA: float = 0.01


def _grades_de_sensibilidade(resultados: dict) -> list[tuple[str, list, list]]:
    """`(onde, eixos, valores)` de cada grade de `resultados.sensibilidades`, as 1D e depois
    as 2D, na ordem publicada. `eixos` é `[(premissa, pontos)]` — um eixo na 1D, dois na 2D
    (x e depois y) —, e `valores`, o preço por ação de cada célula. Leitura do contrato de
    `sensibilidades.py`, nunca conta."""
    sensibilidades = _objeto(resultados.get("sensibilidades"))
    grades: list[tuple[str, list, list]] = []
    for indice, grade in enumerate(_lista(sensibilidades.get("grades_1d"))):
        grade = _objeto(grade)
        pontos = [_objeto(ponto) for ponto in _lista(grade.get("pontos"))]
        grades.append((f"resultados.sensibilidades.grades_1d.{indice}",
                       [(grade.get("premissa"), [ponto.get("x") for ponto in pontos])],
                       [ponto.get("valor") for ponto in pontos]))
    for indice, grade in enumerate(_lista(sensibilidades.get("grades_2d"))):
        grade = _objeto(grade)
        celulas = [_objeto(celula) for linha in _lista(grade.get("celulas")) for celula in _lista(linha)]
        grades.append((f"resultados.sensibilidades.grades_2d.{indice}",
                       [(grade.get("premissa_x"), _lista(grade.get("pontos_x"))),
                        (grade.get("premissa_y"), _lista(grade.get("pontos_y")))],
                       [celula.get("valor") for celula in celulas]))
    return grades


def _centrado(pontos: list, premissa) -> bool:
    """D11, leitura (a) do achado 9: a lista de pontos do eixo tem comprimento ímpar, e o
    ponto do meio é a premissa do cenário. Igualdade exata — os dois números saem do mesmo
    caso, a regra com que `render._base_da_grade` marca a célula-base."""
    if len(pontos) % 2 == 0 or not _numero_declarado(premissa):
        return False
    meio = pontos[len(pontos) // 2]
    return _numero_declarado(meio) and meio == premissa


def _achados_das_grades(entrega: dict, catalogo: dict, idioma: str) -> list[Achado]:
    """As duas regras sobre as grades de sensibilidade, grade a grade:

    - REQUIRED DISCLOSURE `premissa_central_fora_do_ponto_central_da_grade` (§11; D11): a
      grade está centrada quando perturba o cenário da manchete (`caso.sensibilidades.
      cenario == resultados.manchete.cenario`) e, em todo eixo, está centrada na premissa
      desse cenário (`_centrado`). Senão, um aviso, com o cenário da grade, o da manchete e
      os eixos fora do centro, pelos rótulos do catálogo.
    - QUALITY WARNING `sensibilidade_pouco_informativa` (§11): toda célula dentro de
      `TOLERANCIA_DE_SENSIBILIDADE_POUCO_INFORMATIVA` do preço publicado do cenário que a
      grade perturba (`resultados.cenarios.<cenário>.valor.preco_acao`)."""
    resultados = _objeto(entrega.get("resultados"))
    grades = _grades_de_sensibilidade(resultados)
    if not grades:
        return []
    caso = _objeto(entrega.get("caso"))
    cenario_da_grade = _objeto(caso.get("sensibilidades")).get("cenario")
    cenario_da_manchete = _objeto(resultados.get("manchete")).get("cenario")
    nome = cenario_da_grade if isinstance(cenario_da_grade, str) else None
    premissas = _objeto(_objeto(_objeto(caso.get("cenarios")).get(nome)).get("premissas"))
    preco = _objeto(_objeto(_objeto(resultados.get("cenarios")).get(nome)).get("valor")).get("preco_acao")
    premissas_da_rota = _premissas_da_rota(resultados, catalogo)

    achados: list[Achado] = []
    for onde, eixos, valores in grades:
        rotulos = [_rotulo_da_premissa(premissas_da_rota, premissa, idioma) for premissa, _pontos in eixos]
        grade = " × ".join(rotulos)
        fora_do_centro = [rotulo for (premissa, pontos), rotulo in zip(eixos, rotulos)
                          if not _centrado(pontos, premissas.get(premissa) if isinstance(premissa, str) else None)]
        if cenario_da_grade != cenario_da_manchete or fora_do_centro:
            achados.append(Achado("REQUIRED_DISCLOSURE", "premissa_central_fora_do_ponto_central_da_grade", onde, {
                "grade": grade, "cenario_da_grade": str(cenario_da_grade),
                "cenario_manchete": str(cenario_da_manchete), "eixos": ", ".join(fora_do_centro) or _SEM_VALOR,
            }))
        if valores and _numero_finito(preco) and all(
                _numero_finito(valor) and math.isclose(valor, preco, rel_tol=TOLERANCIA_DE_SENSIBILIDADE_POUCO_INFORMATIVA)
                for valor in valores):
            achados.append(Achado("QUALITY_WARNING", "sensibilidade_pouco_informativa", onde, {
                "grade": grade, "cenario": str(cenario_da_grade),
                "tolerancia_fmt": placeholders.formatar(TOLERANCIA_DE_SENSIBILIDADE_POUCO_INFORMATIVA, "pct0", idioma),
            }))
    return achados


def _achados_conservacao_de_capital(resultados: dict, catalogo: dict, idioma: str) -> list[Achado]:
    """REQUIRED DISCLOSURE `conservacao_de_capital_nao_fecha` (§11: "conservação de capital
    que não fecha"; D6): um aviso por cenário cuja `conservacao_capital.diagnosticos_chaves`
    traz a chave que o catálogo nomeia (`disclosures.conservacao_de_capital.chave`) — o
    molde de `_achados_divergencia_de_base`. O limiar (10%) é do motor; a integração
    publica a chave por presença do alerta, também ao vivo no laboratório (§8.4), e esta
    função não compara limiar nenhum. A mensagem imprime o `gap_%` publicado, o rótulo do
    ano-base do capex e o texto do catálogo.

    Um bloco `conservacao_capital` sem `diagnosticos_chaves` é HARD FAIL
    `diagnostico_sem_chave`: `_pares_diagnosticos` só vê listas `diagnosticos`, que este
    bloco não tem, e o disclosure não pode sumir calado (armadilha 1 da Task 4)."""
    achados: list[Achado] = []
    for nome, cenario in _objeto(resultados.get("cenarios")).items():
        bloco = _objeto(cenario).get("conservacao_capital")
        if bloco is None:
            continue
        onde = f"resultados.cenarios.{nome}.conservacao_capital"
        chaves = _objeto(bloco).get("diagnosticos_chaves")
        if not isinstance(chaves, list):
            achados.append(Achado("HARD_FAIL", "diagnostico_sem_chave", f"{onde}.diagnosticos_chaves", {
                "razao": "'diagnosticos_chaves' ausente (esperada ao lado de todo 'conservacao_capital')"}))
            continue
        declaracao = catalogo["disclosures"]["conservacao_de_capital"]
        if declaracao["chave"] not in chaves:
            continue
        gap, ano_base = bloco.get("gap_%"), bloco.get("ano_base")
        rotulo = _objeto(_objeto(_objeto(catalogo.get("anos_base_do_capex")).get(
            ano_base if isinstance(ano_base, str) else None)).get("rotulo")).get(idioma)
        achados.append(Achado("REQUIRED_DISCLOSURE", "conservacao_de_capital_nao_fecha", f"{onde}.gap_%", {
            "cenario": nome,
            "gap": round(gap, 1) if _numero_finito(gap) else None,
            "gap_fmt": placeholders.formatar(gap, "pp1", idioma) if _numero_finito(gap) else _SEM_VALOR,
            "ano_base": str(ano_base),
            "ano_base_rotulo": rotulo if isinstance(rotulo, str) and rotulo.strip() else _SEM_VALOR,
            "texto": declaracao["texto"][idioma],
        }))
    return achados


def _achados_eixos_da_reversa(resultados: dict, catalogo: dict, idioma: str) -> list[Achado]:
    """D4 (§9: o que está no preço, "custo de capital implícito sempre"; N9 da revisão da
    5D): um alvo de mercado inalcançável é leitura do preço, não reversa ausente.

    - REQUIRED DISCLOSURE `eixo_obrigatorio_da_reversa_sem_raiz`: eixo que o catálogo declara
      `obrigatorio` (`eixos_de_reversa.<eixo>.obrigatorio`, travado contra
      `caso.EIXO_OBRIGATORIO`) publicado sem `resolucao.resolveu` verdadeiro. Leva o rótulo
      do eixo e o de `leitura.motivo`. A regra lê a flag, nunca o nome do eixo.
    - HARD FAIL `eixos_de_reversa_desconhecidos`: com a reversa publicada, o catálogo não
      declara na forma cada eixo publicado — `obrigatorio` booleano e rótulo no idioma. Sem a
      declaração nenhum eixo seria obrigatório, e a regra falha fechada."""
    reversa = resultados.get(BLOCO_DA_REVERSA)
    if not isinstance(reversa, dict):
        return []
    eixos = _objeto(reversa.get("eixos"))
    declarados = catalogo.get("eixos_de_reversa")

    def _declarado(nome) -> bool:
        info = _objeto(declarados.get(nome)) if isinstance(declarados, dict) and isinstance(nome, str) else {}
        rotulo = _objeto(info.get("rotulo")).get(idioma)
        return isinstance(info.get("obrigatorio"), bool) and isinstance(rotulo, str) and bool(rotulo.strip())

    if not isinstance(declarados, dict) or not declarados or not all(_declarado(nome) for nome in eixos):
        return [Achado("HARD_FAIL", "eixos_de_reversa_desconhecidos", f"resultados.{BLOCO_DA_REVERSA}.eixos", {
            "eixos": ", ".join(str(nome) for nome in eixos) or _SEM_VALOR, "idioma": idioma})]

    motivos = _objeto(catalogo.get("motivos_da_leitura"))
    achados: list[Achado] = []
    for nome, eixo in eixos.items():
        if not declarados[nome]["obrigatorio"] or _objeto(_objeto(eixo).get("resolucao")).get("resolveu") is True:
            continue
        motivo = _objeto(_objeto(eixo).get("leitura")).get("motivo")
        rotulo_do_motivo = _objeto(_objeto(motivos.get(motivo if isinstance(motivo, str) else None)).get(
            "rotulo")).get(idioma)
        achados.append(Achado("REQUIRED_DISCLOSURE", "eixo_obrigatorio_da_reversa_sem_raiz",
                              f"resultados.{BLOCO_DA_REVERSA}.eixos.{nome}.resolucao.resolveu", {
                                  "eixo": nome, "rotulo": declarados[nome]["rotulo"][idioma], "motivo": str(motivo),
                                  "motivo_rotulo": (rotulo_do_motivo if isinstance(rotulo_do_motivo, str)
                                                    and rotulo_do_motivo.strip() else _SEM_VALOR),
                              }))
    return achados


def _achados_da_valuation(entrega: dict, catalogo: dict, idioma: str) -> list[Achado]:
    """As regras da Task 4 que leem os blocos da aba Valuation, na ordem da aba: a
    conservação de capital (cenários), as grades de sensibilidade e o que está no preço."""
    resultados = _objeto(entrega.get("resultados"))
    return (_achados_conservacao_de_capital(resultados, catalogo, idioma)
            + _achados_das_grades(entrega, catalogo, idioma)
            + _achados_eixos_da_reversa(resultados, catalogo, idioma))


def avaliar(entrega: dict, catalogo: dict, contrato_ledger: dict, html: str | None = None) -> list[Achado]:
    """Roda as regras de QC; devolve os achados em ordem determinística
    (mesma entrada, mesma lista de achados, sempre — nada de relógio, nada
    de ordem de `set`).

    `contrato_ledger` (fatia 5E, Task 2): o dict do contrato `ledger/1` do
    `er-evidencia`, que `builder.py` lê pela constante dos assets externos. Lido
    por `entrega.ler_contrato_do_ledger` antes de qualquer regra: fora da forma,
    `ContratoDoLedgerInvalido` — o QC falha fechado, nunca lê as flags pela metade.

    `html`: `None` na primeira passada de `builder.py` (antes do render —
    nenhuma regra desta fatia depende dele além de `relatorio_nao_
    autocontido`, que simplesmente não dispara); o HTML já composto na
    segunda passada, só para essa regra.
    """
    contrato = contrato_entrega.ler_contrato_do_ledger(contrato_ledger)
    achados: list[Achado] = []
    idioma = entrega["execucao"]["idioma"]

    achado_hash = _achado_hash(entrega)
    if achado_hash is not None:
        achados.append(achado_hash)

    achados.extend(_achados_prosa(entrega, catalogo))
    achados.extend(_achados_exhibits(entrega))

    resultados = entrega.get("resultados") or {}
    achados.extend(_achados_diagnostico_sem_chave(resultados))
    achados.extend(_achados_unidade_desconhecida(resultados, catalogo))
    achados.extend(_achados_divergencia_de_base(resultados, catalogo, idioma))

    achados.extend(_achados_bases_divergentes(resultados))
    achados.extend(_achados_da_valuation(entrega, catalogo, idioma))

    achados.extend(_achados_da_tese(entrega, catalogo, idioma))
    achados.extend(_achados_do_ledger(entrega, catalogo, contrato, idioma))

    achado_autocontido = _achado_autocontido(html)
    if achado_autocontido is not None:
        achados.append(achado_autocontido)

    return achados

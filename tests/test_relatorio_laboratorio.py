"""O laboratório da aba Valuation (fatia 5C, item 5, Task 2).

Ver `docs/superpowers/plans/2026-09-12-v4-item5c-laboratorio.md` (decisões
L1–L8) e `.superpowers/sdd/task-5c2-brief.md`. Dois lados, como na 5B:

- **Python** — `render.compor` monta o painel ESTÁTICO (um campo por premissa,
  agrupado pelos blocos do catálogo, original ao lado do editável) e embute o
  payload, o espelho e a fachada. Os dois JS da integração entram na página
  por LEITURA de `builder.ASSETS_DA_INTEGRACAO`, nunca por cópia — o que este
  arquivo confere por sha256, do lado de dentro do HTML emitido (a cópia em
  `assets/` é reprovada por `tests/test_relatorio_fronteira.py`, pelo mesmo
  hash e pelo outro lado).
- **node** — os módulos da página carregados no MESMO `vm.createContext({})`,
  como o browser faz, e o formatador do laboratório amarrado, caso a caso, ao
  `placeholders.formatar` do Python.

Raízes/entregas vêm de `tests/relatorio_apoio.py` (`montar_entrega`, que roda
`avaliar()` de verdade sobre uma fixture de caso) — nenhum `resultados.json` é
forjado à mão aqui.
"""

import hashlib
import json
import re
import shutil
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
ASSETS = RAIZ / "skills" / "er-relatorio" / "assets"
ASSETS_DA_INTEGRACAO = RAIZ / "skills" / "er-valuation" / "assets"

sys.path.insert(0, str(SCRIPTS))
import builder  # noqa: E402
import placeholders  # noqa: E402
import qc  # noqa: E402
import render  # noqa: E402

sys.path.insert(0, str(RAIZ / "tests"))
import relatorio_apoio as apoio  # noqa: E402

CATALOGO = json.loads(
    (ASSETS_DA_INTEGRACAO / "catalogo_apresentacao.json").read_text(encoding="utf-8"))
DICIONARIO = placeholders.carregar_dicionario("pt-BR")

# Rota firm, quatro blocos econômicos representados, ponte, reversa e grade 2D
# — a fixture mais completa, e a única que exercita o rótulo de congelado nos
# três itens de uma vez.
FIXTURE = "caso_reversa_firm.json"
# Sem SOTP, sem reversa e sem sensibilidades: discrimina "rotula o que existe" de
# "rotula sempre". Fatia 5D, Task 2: era a de rota equity (`caso_minimo_equity.
# json`), mas a entrega de teste passou a compor a reversa que a Análise exige
# onde o gate a admite (D4), e o laboratório congela essa reversa. Uma entrega
# válida sem nada congelado agora vem de uma fixture em que o gate não admite
# reversa: a de rota rampa, que emite com o disclosure nomeado da limitação.
FIXTURE_SEM_CONGELADO = "caso_rampa.json"
FIXTURE_SOTP = "caso_sotp_homogeneo.json"

SEM_NODE = shutil.which("node") is None
RAZAO_SEM_NODE = "node ausente do PATH -- a suite do laboratorio roda sempre no CI (setup-node)"

MODULOS_DA_PAGINA = [
    ASSETS / "uPlot.iife.min.js",
    ASSETS / "graficos.js",
    ASSETS / "svg.js",
    ASSETS_DA_INTEGRACAO / "motor_espelho.js",
    ASSETS_DA_INTEGRACAO / "espelho_fachada.js",
    ASSETS / "laboratorio.js",
]
SUPERFICIES_DA_PAGINA = ["uPlot", "FleetGraficos", "FleetSVG", "MotorEspelho",
                         "FachadaEspelho", "FleetLaboratorio"]


def _js_da_integracao() -> dict:
    return {nome: builder.ASSETS_DA_INTEGRACAO[nome].read_text(encoding="utf-8")
            for nome in ("espelho", "fachada")}


def _pagina(nome_fixture: str = FIXTURE, *, com_laboratorio: bool = True, **kwargs) -> tuple[str, dict]:
    """`(html, entrega)` pelo mesmo caminho que `builder.py` percorre depois de
    uma primeira passada de QC limpa."""
    entrega = apoio.montar_entrega(nome_fixture, **kwargs)
    fontes = {"resultados": entrega["resultados"], "caso": entrega["caso"]}
    _resolvido, log, _erros = placeholders.resolver(
        entrega["analise"]["conclusao"]["texto"], fontes, "pt-BR", "analise.conclusao.texto")
    achados = qc.avaliar(entrega, CATALOGO, html=None)
    assert not any(a.nivel == "HARD_FAIL" for a in achados), achados
    pagina = render.compor(entrega, CATALOGO, achados, log, "pt-BR", None, None,
                            _js_da_integracao() if com_laboratorio else None)
    return pagina, entrega


def _aba_valuation(pagina: str) -> str:
    """O CORPO da aba Valuation, sem nenhum `<script>` da página — os módulos
    embutidos contêm os mesmos seletores que este arquivo procura (é o que
    eles leem, afinal), e contar ocorrências na página inteira confundiria
    marcação com código."""
    inicio = pagina.index('data-aba-painel="valuation" hidden>')
    return pagina[inicio:pagina.index('<section id="aba-evidencia"')]


def _painel(pagina: str) -> str:
    """Só o painel do laboratório, dentro da aba Valuation."""
    aba = _aba_valuation(pagina)
    return aba[aba.index('<section class="laboratorio"'):]


def _dados_embutidos(pagina: str) -> dict:
    bruto = re.search(
        r'<script type="application/json" id="fleet-dados-laboratorio">(.*?)</script>',
        pagina, re.S).group(1)
    return json.loads(bruto.replace("<\\/", "</"))


def _sha256(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# O painel: blocos na ordem do catálogo, um campo por premissa, original ao
# lado do editável.
# --------------------------------------------------------------------------

def test_o_painel_traz_os_blocos_na_ordem_do_catalogo():
    """L5: o agrupamento econômico é do CATÁLOGO (`blocos.<chave>.ordem`),
    nunca uma ordem decorada no relatório nem a ordem de iteração do arquivo.
    A ordem esperada é derivada aqui de forma independente — se `render.py`
    passar a usar a ordem do dict, este teste fica vermelho."""
    pagina, entrega = _pagina()
    painel = _painel(pagina)

    esperada = [chave for chave, _info in sorted(
        CATALOGO["blocos"].items(), key=lambda par: (par[1]["ordem"], par[0]))]
    blocos = [b for b in re.findall(r'data-laboratorio-bloco="([^"]*)"', painel) if b]
    assert len(blocos) == 4, f"esperados os quatro blocos, vieram {blocos}"
    assert blocos == esperada

    # Cada bloco leva o rótulo do catálogo, no idioma da página — nunca a
    # chave interna ('custo_capital') na tela.
    for chave in esperada:
        assert CATALOGO["blocos"][chave]["rotulo"]["pt-BR"] in painel
    assert entrega["resultados"]["rota"] == "firm"


def test_cada_premissa_do_cenario_vira_um_campo_editavel():
    """Cobertura, não amostra: TODA premissa que o caso declara aparece no
    painel, e toda premissa que o catálogo conhece vem editável, com o tipo de
    entrada que o catálogo declara (nunca um widget escolhido aqui)."""
    pagina, entrega = _pagina()
    painel = _painel(pagina)
    premissas = entrega["caso"]["cenarios"]["base"]["premissas"]
    do_catalogo = CATALOGO["premissas"]["firm"]

    assert set(re.findall(r'data-laboratorio-premissa="([^"]+)"', painel)) == set(premissas)
    for chave, valor in premissas.items():
        campo = re.search(
            r'data-laboratorio-premissa="' + re.escape(chave) + r'">(.*?)</div>', painel, re.S)
        assert campo is not None, chave
        entrada = do_catalogo[chave]["entrada"]
        assert f'data-laboratorio-entrada="{entrada}"' in campo.group(1), (chave, entrada)
        if entrada == "numero":
            assert f'value="{json.dumps(valor)}"' in campo.group(1), (chave, valor)


def test_o_valor_original_fica_ao_lado_do_editavel_com_a_unidade_do_catalogo():
    """L6 (§8.3: simular "sem sobrescrever a calibração original"): o valor
    original viaja em DOIS lugares — legível ao lado do campo, e em
    `data-laboratorio-original`, que é o que o botão de restaurar devolve.

    O legível passa pela UNIDADE que o catálogo declara: `roic` é ponto
    percentual e sai "15,00%", não "15,00" — a mesma disciplina do achado F7/A4.
    Sem isto, o painel escreveria ao lado do preço em reais um número puro."""
    pagina, entrega = _pagina()
    painel = _painel(pagina)
    valor = entrega["caso"]["cenarios"]["base"]["premissas"]["roic"]
    campo = re.search(r'data-laboratorio-premissa="roic">(.*?)</div>', painel, re.S).group(1)

    assert f'data-laboratorio-original="{json.dumps(valor)}"' in campo
    esperado = placeholders.formatar(
        valor, CATALOGO["unidades"][CATALOGO["premissas"]["firm"]["roic"]["unidade"]]["formato"],
        "pt-BR", entrega["caso"]["moeda"])
    assert esperado in campo, campo
    assert esperado != f"{valor:.2f}".replace(".", ","), "unidade sumiu — o teste deixou de discriminar"


def test_uma_premissa_que_o_catalogo_nao_conhece_sai_desabilitada_e_rotulada():
    """L5: "o laboratório nunca inventa unidade nem widget". A premissa é
    EXIBIDA (some-la esconderia do analista um input que produziu o número),
    desabilitada e rotulada — e não ganha `data-laboratorio-entrada`, que é o
    que impede o JS de tentar lê-la.

    A premissa entra na entrega DEPOIS do QC de propósito: o gate da
    integração recusaria um vocabulário fora da rota, e é justamente o caso em
    que o relatório não pode quebrar nem inventar."""
    entrega = apoio.montar_entrega(FIXTURE)
    fontes = {"resultados": entrega["resultados"], "caso": entrega["caso"]}
    _r, log, _e = placeholders.resolver(
        entrega["analise"]["conclusao"]["texto"], fontes, "pt-BR", "analise.conclusao.texto")
    achados = qc.avaliar(entrega, CATALOGO, html=None)
    entrega["caso"]["cenarios"]["base"]["premissas"]["premissa_da_v10"] = 3.5

    painel = _painel(render.compor(entrega, CATALOGO, achados, log, "pt-BR", None, None,
                                    _js_da_integracao()))
    campo = re.search(
        r'data-laboratorio-premissa="premissa_da_v10">(.*?)</div>', painel, re.S).group(1)
    assert "data-laboratorio-entrada" not in campo, campo
    assert "disabled" in campo
    assert "3.5" in campo
    assert render.t(DICIONARIO, "valuation.laboratorio_nao_editavel_nota") in campo


def test_cada_cenario_ganha_seu_painel_com_saidas_e_botao_de_restaurar():
    """Um caso de dois cenários: o painel é POR CENÁRIO — três saídas (preço,
    múltiplo e upside) e um botão de restaurar em cada —, porque a edição de um
    cenário não é a do outro."""
    def _dois_cenarios(caso: dict) -> None:
        caso["cenarios"]["otimista"] = json.loads(json.dumps(caso["cenarios"]["base"]))
        caso["cenarios"]["otimista"]["premissas"]["g"] = 7.0
        caso["cenario_base"] = "base"

    pagina, _entrega = _pagina("caso_minimo_firm.json", mutar_caso=_dois_cenarios)
    painel = _painel(pagina)

    assert re.findall(r'data-laboratorio-cenario="([^"]+)"', painel) == ["base", "otimista"]
    assert painel.count("data-laboratorio-restaurar") == 2
    for papel in ("preco", "multiplo", "upside"):
        assert painel.count(f'data-laboratorio-saida="{papel}"') == 2
    # Task 3: e um lugar por cenário para os diagnósticos que o JS pinta.
    assert painel.count("data-laboratorio-diagnosticos") == 2


def test_um_valor_que_o_catalogo_nao_sabe_nomear_nao_vaza_o_codigo_cru():
    """B2 (achado F2 da revisão final da 5A) estendido ao painel. `tv:
    "spread"` é um alias legado que o gate ACEITA e canonicaliza para
    'gordon': a integração publica o código canônico, o cabeçalho já imprime
    "Gordon — ...", e o catálogo de apresentação não tem rótulo nenhum para
    'spread'.

    O campo fica travado (o valor não é uma das opções catalogadas) e diz
    isso — nunca imprime 'spread'. Sem esta regra a mesma página diria duas
    coisas diferentes sobre o mesmo input, que é exatamente o que a onda de
    correção da 5A eliminou.

    Contraprova no mesmo teste: um valor NUMÉRICO travado continua visível.
    Número não é código de vocabulário; esconder o input que produziu o
    número seria o erro oposto."""
    def _usar_alias(caso: dict) -> None:
        caso["cenarios"]["base"]["premissas"]["tv"] = "spread"

    pagina, entrega = _pagina(FIXTURE, mutar_caso=_usar_alias)
    assert entrega["resultados"]["manchete"]["convencao_terminal"] == "gordon"
    painel = _painel(pagina)
    campo = re.search(r'data-laboratorio-premissa="tv">(.*?)</div>', painel, re.S).group(1)

    # `prosa_da_pagina` neutraliza o miolo de todo `<script>` (B6): o alias
    # EXISTE no payload embutido, porque é o que o caso declara e é o que a
    # fachada precisa receber para reproduzir o preço publicado. A regra é
    # sobre a TELA.
    assert "spread" not in apoio.prosa_da_pagina(pagina)
    assert "data-laboratorio-entrada" not in campo, campo
    assert render.t(DICIONARIO, "valuation.laboratorio_valor_nao_rotulavel") in campo


# --------------------------------------------------------------------------
# O que NÃO é vivo, rotulado (L3) — inclusive a manchete do SOTP.
# --------------------------------------------------------------------------

def test_o_que_nao_e_vivo_aparece_rotulado_como_congelado():
    """§8.4 manda rotular o precomputado. A fixture tem reversa e
    sensibilidades; a de rota rampa não tem nenhum dos três, e ali o bloco
    não pode aparecer — um rótulo constante não informaria nada."""
    painel = _painel(_pagina()[0])
    assert render.t(DICIONARIO, "valuation.laboratorio_congelado_titulo") in painel
    assert render.t(DICIONARIO, "valuation.laboratorio_congelado_reversa") in painel
    assert render.t(DICIONARIO, "valuation.laboratorio_congelado_sensibilidades") in painel
    assert render.t(DICIONARIO, "valuation.laboratorio_congelado_sotp") not in painel

    painel_limpo = _painel(_pagina(FIXTURE_SEM_CONGELADO)[0])
    assert render.t(DICIONARIO, "valuation.laboratorio_congelado_titulo") not in painel_limpo


def test_num_caso_com_sotp_a_manchete_e_rotulada_como_congelada_e_nao_muda():
    """Achado 3 da Task 1: num caso com SOTP, `manchete.preco_acao` é o preço
    da SOMA DAS PARTES — que L3 deixou congelado — e não o preço do cenário que
    o laboratório recalcula. Duas obrigações, e as duas são testadas:

    1. o número publicado na manchete continua sendo o do SOTP, byte a byte
       igual ao da página SEM laboratório (redesenhá-lo a partir da fachada
       trocaria o número publicado em três fixtures);
    2. o rótulo de congelado aparece junto da manchete, e não só no rodapé do
       painel — o analista vê o preço do cenário se mover logo abaixo dela.
    """
    pagina, entrega = _pagina(FIXTURE_SOTP)
    sem_laboratorio, _ = _pagina(FIXTURE_SOTP, com_laboratorio=False)

    def _cabecalho(texto: str) -> str:
        aba = _aba_valuation(texto)
        inicio = aba.index('<section class="valuation-cabecalho"')
        return aba[inicio:aba.index("</section>", inicio) + len("</section>")]

    preco = placeholders.formatar(entrega["resultados"]["manchete"]["preco_acao"], "moeda",
                                   "pt-BR", entrega["caso"]["moeda"])
    assert preco in _cabecalho(pagina)
    assert _cabecalho(pagina) == _cabecalho(sem_laboratorio)

    aba = _aba_valuation(pagina)
    nota = render.t(DICIONARIO, "valuation.laboratorio_manchete_congelada")
    assert nota in aba[:aba.index('<section class="valuation-multiplos"')], \
        "o rótulo de congelada não acompanha a manchete"
    assert nota not in _aba_valuation(sem_laboratorio)
    assert render.t(DICIONARIO, "valuation.laboratorio_congelado_sotp") in _painel(pagina)


# --------------------------------------------------------------------------
# Como os dois JS da integração chegam à página: por leitura, nunca por cópia.
# --------------------------------------------------------------------------

def test_o_espelho_e_a_fachada_entram_por_leitura_da_integracao():
    """Constraint global da fatia: o relatório LÊ os dois de
    `ASSETS_DA_INTEGRACAO` e os embute; nunca os copia para
    `skills/er-relatorio/assets/`. Aqui pelo lado de dentro do HTML: o texto
    embutido é byte a byte o arquivo da integração (sha256), e nenhum asset
    PRÓPRIO do relatório tem esse conteúdo — a outra metade da mesma trava
    vive em `test_relatorio_fronteira.py`, e as duas medem o mesmo hash."""
    pagina, _entrega = _pagina()
    for nome in ("espelho", "fachada"):
        fonte = builder.ASSETS_DA_INTEGRACAO[nome].read_text(encoding="utf-8")
        assert fonte in pagina, f"{nome} não foi embutido"
        hashes_do_relatorio = {_sha256(p.read_text(encoding="utf-8", errors="ignore"))
                               for p in ASSETS.rglob("*") if p.is_file()}
        assert _sha256(fonte) not in hashes_do_relatorio, \
            f"{nome} virou cópia dentro de skills/er-relatorio/assets/"


def test_sem_o_js_da_integracao_a_pagina_sai_sem_painel():
    """O painel e o motor entram ou não entram juntos: um editor sem a fachada
    seria interface morta. É também o que preserva todo chamador anterior a
    esta fatia (`render.compor` sem o argumento novo)."""
    pagina, _entrega = _pagina(com_laboratorio=False)
    assert "data-laboratorio" not in _aba_valuation(pagina)
    assert _dados_embutidos(pagina) is None
    for nome in ("espelho", "fachada"):
        fonte = builder.ASSETS_DA_INTEGRACAO[nome].read_text(encoding="utf-8")
        assert fonte not in pagina, f"{nome} embutido numa página sem laboratório"
    assert (ASSETS / "laboratorio.js").read_text(encoding="utf-8") not in pagina


def test_o_payload_leva_os_dois_lados_da_paridade():
    """L4: o badge é um fato medido na máquina de quem abriu o arquivo — a
    fachada recomputa cada cenário a partir do `caso` e compara com o que o
    Python publicou. Sem os dois lados embutidos não há o que comparar."""
    pagina, entrega = _pagina()
    dados = _dados_embutidos(pagina)
    assert dados["caso"] == entrega["caso"]
    assert dados["resultados"] == entrega["resultados"]
    assert dados["resultados"]["versao_contrato"] == "resultados/1"
    assert dados["idioma"] == "pt-BR"
    assert set(dados["formatos"]) == {"preco", "multiplo", "upside"}
    assert dados["formatos"]["preco"]["prefixo"].strip() == "R$"
    assert dados["formatos"]["upside"]["escala"] == 100
    # Os rótulos de múltiplo cobrem toda chave que a fachada pode publicar —
    # inclusive a do degrau, que não mora em `multiplos` do `resultados`.
    assert "PVP_com_degrau" in dados["rotulosMultiplos"]
    assert "{cenario}" in dados["textos"]["paridadeItem"]


def test_o_payload_leva_rotulo_e_severidade_de_todo_diagnostico_do_catalogo():
    """T5: o laboratório só PINTA chaves — rótulo e severidade de cada uma vêm
    do catálogo, no idioma da página, pelo payload. Todo diagnóstico do
    catálogo entra (inclusive os alertas do degrau), porque qualquer edição
    pode acender qualquer um; e os dois textos de estado (nenhum diagnóstico;
    chave sem rótulo) vêm do dicionário."""
    pagina, _entrega = _pagina()
    dados = _dados_embutidos(pagina)
    assert dados["diagnosticos"] == {
        chave: {"rotulo": info["rotulo"]["pt-BR"], "severidade": info["severidade"]}
        for chave, info in CATALOGO["diagnosticos"].items()
    }
    assert dados["textos"]["diagnosticosNenhum"] == render.t(
        DICIONARIO, "valuation.laboratorio_diagnosticos_nenhum")
    assert dados["textos"]["diagnosticoDesconhecido"] == render.t(
        DICIONARIO, "valuation.laboratorio_diagnostico_desconhecido")


def test_o_payload_leva_o_rotulo_de_todo_motivo_de_recusa_do_catalogo():
    """Onda de correção da revisão final da 5C (F2): o laboratório diz POR QUE
    um cenário foi recusado — o motivo chega da fachada como código, e o
    rótulo vem do catálogo pelo payload, como o dos diagnósticos. A moldura
    ("cenário recusado: {motivo}") e o texto de motivo sem rótulo vêm do
    dicionário."""
    pagina, _entrega = _pagina()
    dados = _dados_embutidos(pagina)
    assert dados["recusas"] == {
        codigo: info["rotulo"]["pt-BR"] for codigo, info in CATALOGO["recusas"].items()}
    assert dados["textos"]["diagnosticosRecusado"] == render.t(
        DICIONARIO, "valuation.laboratorio_diagnosticos_recusado")
    assert "{motivo}" in dados["textos"]["diagnosticosRecusado"]
    assert dados["textos"]["recusaDesconhecida"] == render.t(
        DICIONARIO, "valuation.laboratorio_recusa_desconhecida")


# --------------------------------------------------------------------------
# O laboratório não muda o contrato de saída: autocontido, determinístico,
# mesmo `qc.json`.
# --------------------------------------------------------------------------

def test_a_pagina_com_laboratorio_continua_autocontida():
    """A regra dos sete tokens de rede da 5B roda sobre o miolo de TODO
    `<script>` — e agora são ~110 KB a mais de espelho e fachada, além do
    laboratório. Nenhuma referência externa, nenhuma chamada de rede: o
    relatório é artefato offline que o analista reenvia por e-mail."""
    pagina, entrega = _pagina()
    achados = qc.avaliar(entrega, CATALOGO, html=pagina)
    assert not [a for a in achados if a.codigo == "relatorio_nao_autocontido"], achados
    laboratorio = (ASSETS / "laboratorio.js").read_text(encoding="utf-8")
    assert qc._PADRAO_CHAMADA_DE_REDE.findall(laboratorio) == []
    assert qc._PADRAO_ATRIBUICAO_DE_RECURSO.findall(laboratorio) == []


def test_o_laboratorio_nao_muda_o_qc_nem_o_determinismo():
    """Constraint global: "o laboratório não muda o HTML emitido nem o
    `qc.json`" — ele é interface sobre dados que a página já tinha. Os achados
    do QC são os mesmos com e sem o painel, e duas composições da mesma
    entrega dão os mesmos bytes (nenhum relógio, nenhuma ordem de `set`,
    nenhuma id gerada em tempo de execução)."""
    pagina, entrega = _pagina()
    sem_laboratorio, _ = _pagina(com_laboratorio=False)
    como = [(a.nivel, a.codigo, a.onde, a.params) for a in qc.avaliar(entrega, CATALOGO, html=pagina)]
    sem = [(a.nivel, a.codigo, a.onde, a.params)
           for a in qc.avaliar(entrega, CATALOGO, html=sem_laboratorio)]
    assert como == sem

    de_novo, _ = _pagina()
    assert pagina == de_novo


# --------------------------------------------------------------------------
# Onde o laboratório de fato roda: todos os módulos da página, um contexto só.
# --------------------------------------------------------------------------

@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_todos_os_modulos_da_pagina_coexistem_no_mesmo_contexto():
    """O achado que matou a primeira versão da fachada (Task 1), agora com a
    página INTEIRA: vários `<script>` clássicos compartilham o MESMO escopo
    léxico global, e o espelho do núcleo sozinho declara ~55 identificadores de
    topo. Um `const`/`function` de topo em qualquer módulo que colidisse com
    outro mata o segundo `<script>` inteiro — e o sintoma não é um número
    errado, é a aba em branco.

    Carrega os SEIS módulos que a página pode levar, nesta ordem, num
    `vm.createContext({})` vazio (sem `module`, sem `require`, sem `document`)
    e exige que todas as superfícies públicas continuem alcançáveis. Um
    harness que carregasse cada arquivo isolado ficaria verde com a aba
    morta."""
    script = (
        "const fs = require('fs'); const vm = require('vm');"
        "const ctx = vm.createContext({});"
        "const nomes = %s; const erros = [];"
        "for (const caminho of %s) {"
        "  try { vm.runInContext(fs.readFileSync(caminho, 'utf8'), ctx, {filename: caminho}); }"
        "  catch (erro) { erros.push(caminho + ': ' + erro.message); }"
        "}"
        "const tipos = {};"
        "for (const nome of nomes) { tipos[nome] = typeof ctx[nome]; }"
        "console.log(JSON.stringify({erros, tipos}));"
    ) % (json.dumps(SUPERFICIES_DA_PAGINA), json.dumps([str(p) for p in MODULOS_DA_PAGINA]))
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    saida = json.loads(r.stdout)
    assert saida["erros"] == [], saida["erros"]
    assert all(tipo != "undefined" for tipo in saida["tipos"].values()), saida["tipos"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
@pytest.mark.parametrize("formato,papel", [("moeda", "preco"), ("x2", "multiplo"),
                                           ("pct1", "upside")])
@pytest.mark.parametrize("valor", [0.0, 1.5, -0.1234, 61.9137, 1234567.891, -9876.5])
def test_o_laboratorio_formata_exatamente_como_o_python(formato, papel, valor, tmp_path):
    """A mesma amarra que `svg.js` tem: a receita de formatação (`{casas,
    escala, prefixo, sufixo}`) vem pronta do payload, mas os separadores de
    milhar/decimal são tabela PRÓPRIA do módulo de browser — e uma tabela
    própria que divergisse do Python faria a mesma página escrever a manchete
    "R$ 61,91" e o preço recalculado logo abaixo "61.91". Caso a caso, contra
    `placeholders.formatar`."""
    espec = placeholders.especificacao_de_formato(formato, "pt-BR", "BRL")
    script = (
        "const fs = require('fs'); const vm = require('vm');"
        "const ctx = vm.createContext({});"
        "vm.runInContext(fs.readFileSync(%s, 'utf8'), ctx);"
        "ctx.__e = %s;"
        "console.log(vm.runInContext("
        "  'FleetLaboratorio.formatar(%s, __e, \"pt-BR\")', ctx));"
    ) % (json.dumps(str(ASSETS / "laboratorio.js")), json.dumps(espec), repr(valor))
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert r.stdout.strip() == placeholders.formatar(valor, formato, "pt-BR", "BRL"), papel


# --------------------------------------------------------------------------
# O painel VIVO: `FleetLaboratorio.iniciar` sobre a marcação que `render.compor`
# de fato emitiu, o payload de fato embutido, e o espelho e a fachada de
# verdade. Só o DOM é simulado — node não tem um, e a suíte não tem
# dependência npm. O DOM falso implementa o subconjunto de seletor que o
# laboratório usa (`[atributo]`, `[atributo="valor"]` e listas separadas por
# vírgula) e LANÇA diante de qualquer outro: se `laboratorio.js` passar a usar
# um seletor que o harness não entende, o teste reprova em voz alta em vez de
# "não achar nada" em silêncio.
# --------------------------------------------------------------------------

MODULOS_DO_LABORATORIO = [
    ASSETS_DA_INTEGRACAO / "motor_espelho.js",
    ASSETS_DA_INTEGRACAO / "espelho_fachada.js",
    ASSETS / "laboratorio.js",
]


class _ArvoreDoPainel(HTMLParser):
    """`{tag, attrs, filhos}` do PRIMEIRO elemento completo do trecho — o
    `<section class="laboratorio">` como `render.compor` o emitiu, com os
    atributos já desescapados (como o browser os entrega ao script)."""

    VAZIOS = frozenset({"input", "br", "hr", "img", "meta", "link"})

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.raiz = None
        self._pilha: list = []

    def _abrir(self, tag, attrs, vazio):
        no = {"tag": tag, "attrs": {k: ("" if v is None else v) for k, v in attrs}, "filhos": []}
        if self._pilha:
            self._pilha[-1]["filhos"].append(no)
        elif self.raiz is None:
            self.raiz = no
        else:
            return
        if not vazio:
            self._pilha.append(no)

    def handle_starttag(self, tag, attrs):
        self._abrir(tag, attrs, tag in self.VAZIOS)

    def handle_startendtag(self, tag, attrs):
        self._abrir(tag, attrs, True)

    def handle_endtag(self, tag):
        if self._pilha and self._pilha[-1]["tag"] == tag:
            self._pilha.pop()

    def handle_data(self, data):
        if self._pilha:
            self._pilha[-1]["filhos"].append({"texto": data})


_HARNESS_DOM = r"""
const fs = require('fs');
const vm = require('vm');
const entrada = JSON.parse(fs.readFileSync(__ENTRADA__, 'utf-8'));
const proprio = (objeto, nome) => Object.prototype.hasOwnProperty.call(objeto, nome);

function casa(el, seletor) {
  return seletor.split(',').some((parte) => {
    const m = /^\s*\[([\w-]+)(?:="([^"]*)")?\]\s*$/.exec(parte);
    if (!m) { throw new Error('seletor fora do subconjunto do harness: ' + parte); }
    if (!proprio(el.atributos, m[1])) { return false; }
    return m[2] === undefined || el.atributos[m[1]] === m[2];
  });
}

const documento = { createElement: (tag) => elemento({ tag: tag, attrs: {}, filhos: [] }) };
const noDeTexto = (texto) => ({ eTexto: true, texto: String(texto), pai: null });

function elemento(no) {
  const el = {
    tagName: no.tag.toUpperCase(),
    atributos: Object.assign({}, no.attrs),
    filhos: [],
    pai: null,
    ownerDocument: documento,
    ouvintes: {},
    disabled: proprio(no.attrs, 'disabled'),
    checked: proprio(no.attrs, 'checked'),
    value: '',
    getAttribute(nome) { return proprio(this.atributos, nome) ? this.atributos[nome] : null; },
    setAttribute(nome, valor) { this.atributos[nome] = String(valor); },
    removeAttribute(nome) { delete this.atributos[nome]; },
    addEventListener(tipo, funcao) { (this.ouvintes[tipo] = this.ouvintes[tipo] || []).push(funcao); },
    disparar(tipo) {
      for (const funcao of (this.ouvintes[tipo] || [])) {
        funcao({ type: tipo, target: this, currentTarget: this });
      }
    },
    get firstChild() { return this.filhos.length ? this.filhos[0] : null; },
    appendChild(filho) { filho.pai = this; this.filhos.push(filho); return filho; },
    removeChild(filho) { this.filhos = this.filhos.filter((f) => f !== filho); return filho; },
    get textContent() {
      return this.filhos.map((f) => (f.eTexto ? f.texto : f.textContent)).join('');
    },
    set textContent(valor) { this.filhos = [noDeTexto(valor)]; },
    querySelectorAll(seletor) {
      const achados = [];
      const varrer = (atual) => {
        for (const filho of atual.filhos) {
          if (filho.eTexto) { continue; }
          if (casa(filho, seletor)) { achados.push(filho); }
          varrer(filho);
        }
      };
      varrer(this);
      return achados;
    },
    querySelector(seletor) { return this.querySelectorAll(seletor)[0] || null; },
    closest(seletor) {
      for (let atual = this; atual; atual = atual.pai) {
        if (!atual.eTexto && casa(atual, seletor)) { return atual; }
      }
      return null;
    },
  };
  for (const filho of no.filhos) {
    el.appendChild(filho.tag === undefined ? noDeTexto(filho.texto) : elemento(filho));
  }
  if (el.tagName === 'INPUT') { el.value = el.getAttribute('value') || ''; }
  if (el.tagName === 'SELECT') {
    const opcoes = el.filhos.filter((f) => !f.eTexto && f.tagName === 'OPTION');
    const escolhida = opcoes.find((o) => proprio(o.atributos, 'selected')) || opcoes[0];
    el.value = escolhida ? escolhida.getAttribute('value') : '';
  }
  return el;
}

const ctx = vm.createContext({});
for (const caminho of entrada.modulos) {
  vm.runInContext(fs.readFileSync(caminho, 'utf8'), ctx, { filename: caminho });
}
const raiz = elemento(entrada.arvore);

// Quem liga o painel é o BOOTSTRAP da própria página (o `<script>` inline de
// `template.html`), com o JSON embutido que ele mesmo parseia -- nunca uma
// chamada feita por este harness. O embrulho abaixo só conta a chamada e
// guarda o `caso` que o laboratório de fato recebeu, para conferir no fim que
// ele nunca foi sobrescrito.
let recebido = null;
let casoAntes = null;
let chamadas = 0;
const iniciarDoModulo = ctx.FleetLaboratorio.iniciar;
ctx.FleetLaboratorio.iniciar = function (raizRecebida, dadosRecebidos) {
  chamadas += 1;
  recebido = dadosRecebidos;
  casoAntes = JSON.stringify(dadosRecebidos.caso);
  return iniciarDoModulo(raizRecebida, dadosRecebidos);
};
ctx.document = {
  getElementById: (id) => (id === 'fleet-dados-laboratorio'
    ? { textContent: JSON.stringify(entrada.dados) } : null),
  querySelector: (seletor) => (casa(raiz, seletor) ? raiz : raiz.querySelector(seletor)),
};

function blocoDoCenario(nome) {
  return raiz.querySelectorAll('[data-laboratorio-cenario]')
    .find((s) => s.getAttribute('data-laboratorio-cenario') === nome);
}

function foto() {
  const badge = raiz.querySelector('[data-laboratorio-badge]');
  const itens = [];
  for (const lista of badge.filhos.filter((f) => !f.eTexto && f.tagName === 'UL')) {
    for (const item of lista.filhos.filter((f) => !f.eTexto)) { itens.push(item.textContent); }
  }
  const saidas = {};
  for (const bloco of raiz.querySelectorAll('[data-laboratorio-cenario]')) {
    const ler = (papel) => bloco.querySelector('[data-laboratorio-saida="' + papel + '"]').textContent;
    saidas[bloco.getAttribute('data-laboratorio-cenario')] = {
      preco: ler('preco'), multiplo: ler('multiplo'),
      multiploRotulo: ler('multiplo-rotulo'), upside: ler('upside'),
    };
  }
  // Task 3: os itens de diagnóstico de cada cenário, como a tela os mostra --
  // texto e classe (a severidade vira classe CSS). A chave nunca chega à tela,
  // então a foto também não a tem.
  const diagnosticos = {};
  for (const bloco of raiz.querySelectorAll('[data-laboratorio-cenario]')) {
    const lista = bloco.querySelector('[data-laboratorio-diagnosticos]');
    diagnosticos[bloco.getAttribute('data-laboratorio-cenario')] = lista === null ? null
      : lista.filhos.filter((f) => !f.eTexto)
        .map((item) => ({ texto: item.textContent, classe: item.getAttribute('class') }));
  }
  return {
    badge: { estado: badge.getAttribute('data-estado'), texto: badge.filhos.length && !badge.filhos[0].eTexto
      ? badge.filhos[0].textContent : badge.textContent, itens: itens },
    campos: raiz.querySelectorAll('[data-laboratorio-entrada]').map((campo) => ({
      premissa: campo.closest('[data-laboratorio-premissa]').getAttribute('data-laboratorio-premissa'),
      disabled: campo.disabled, value: campo.value, invalido: campo.getAttribute('aria-invalid'),
    })),
    botoes: raiz.querySelectorAll('[data-laboratorio-restaurar]').map((b) => b.disabled),
    saidas: saidas,
    diagnosticos: diagnosticos,
  };
}

const fotos = {};
vm.runInContext(entrada.bootstrap, ctx, { filename: 'bootstrap-do-laboratorio' });
fotos.chamadasDoBootstrap = chamadas;
fotos.carga = foto();
for (const passo of entrada.passos) {
  const bloco = blocoDoCenario(passo.cenario);
  if (passo.acao === 'editar') {
    const portador = bloco.querySelectorAll('[data-laboratorio-premissa]')
      .find((p) => p.getAttribute('data-laboratorio-premissa') === passo.premissa);
    const campo = portador.querySelector('[data-laboratorio-entrada]');
    campo.value = passo.valor;
    campo.disparar('input');
    campo.disparar('change');
  } else {
    bloco.querySelector('[data-laboratorio-restaurar]').disparar('click');
  }
  fotos[passo.nome] = foto();
}
fotos.casoIntacto = recebido !== null && JSON.stringify(recebido.caso) === casoAntes;
console.log(JSON.stringify(fotos));
"""


def _bootstrap_do_laboratorio(pagina: str) -> str:
    """O `<script>` inline que a página usa para ligar o painel. Extraído do
    HTML emitido, não relido de `template.html`: é o que o browser executa."""
    blocos = [m.group(1) for m in re.finditer(r"<script>(.*?)</script>", pagina, re.S)
              if "FleetLaboratorio.iniciar" in m.group(1)]
    assert len(blocos) == 1, f"esperado exatamente um bootstrap do laboratório, vieram {len(blocos)}"
    return blocos[0]


def _laboratorio_vivo(pagina: str, tmp_path, *, dados: dict | None = None,
                      passos: list | None = None, modulos_extra: list | None = None) -> dict:
    """Roda o painel no node e devolve uma FOTO depois da carga e depois de
    cada passo (`editar` um campo / `restaurar` um cenário): estado e texto do
    badge, itens de divergência, `disabled`/valor de cada campo e de cada
    botão, e as três saídas de cada cenário, como a tela as mostraria.

    `modulos_extra`: arquivos carregados DEPOIS dos três da página, no mesmo
    contexto e antes do bootstrap — é como um teste simula uma fachada de outra
    versão sem tocar nos arquivos da integração."""
    arvore = _ArvoreDoPainel()
    arvore.feed(_painel(pagina))
    arvore.close()
    assert arvore.raiz is not None and arvore.raiz["attrs"].get("class") == "laboratorio"
    entrada = {
        "modulos": [str(p) for p in MODULOS_DO_LABORATORIO] + [str(p) for p in (modulos_extra or [])],
        "arvore": arvore.raiz,
        "dados": dados if dados is not None else _dados_embutidos(pagina),
        "bootstrap": _bootstrap_do_laboratorio(pagina),
        "passos": passos or [],
    }
    arq = tmp_path / "laboratorio_vivo.json"
    arq.write_text(json.dumps(entrada, ensure_ascii=False), encoding="utf-8")
    script = _HARNESS_DOM.replace("__ENTRADA__", json.dumps(str(arq)))
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    fotos = json.loads(r.stdout)
    assert fotos["chamadasDoBootstrap"] == 1, "o bootstrap da página não ligou o painel"
    return fotos


def _numeros_do_texto(texto: str) -> list[float]:
    return [float(x) for x in re.findall(r"-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", texto)]


def _saidas_publicadas(resultados: dict, moeda: str) -> dict:
    """As três saídas de `base` como a tela deve mostrá-las, a partir do que o
    PYTHON publicou — formatadas pelas mesmas receitas do cabeçalho da aba."""
    cenario = resultados["cenarios"]["base"]
    chave = resultados["manchete"]["multiplo"]["chave"]
    return {
        "preco": placeholders.formatar(cenario["valor"]["preco_acao"], "moeda", "pt-BR", moeda),
        "multiplo": placeholders.formatar(cenario["multiplos"][chave], "x2", "pt-BR"),
        "multiploRotulo": CATALOGO["multiplos"][chave]["rotulo"]["pt-BR"],
        "upside": placeholders.formatar(cenario["vs_preco"]["upside"], "pct1", "pt-BR"),
    }


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_o_badge_vermelho_nomeia_a_divergencia_e_trava_a_edicao(tmp_path):
    """L4, a garantia inteira: um motor de navegador que discorda do relatório
    NUNCA vira editor. Adultera o preço publicado de `base` no payload — o
    `resultados` passa a dizer uma coisa e o motor, outra — e exige, na carga:

    - badge `divergente`, com o texto do dicionário e UM item que nomeia o
      cenário, a chave e os DOIS números (o adulterado e o recalculado);
    - TODO campo editável e todo botão de restaurar desabilitados;
    - as três saídas no texto de "sem valor" — nenhum número recalculado por
      um motor que o relatório não sustenta chega à tela.

    E a prova de que a trava não é só o atributo `disabled`: o passo seguinte
    FORÇA uma edição (o DOM falso dispara o evento num campo desabilitado,
    coisa que um browser não faria) e as saídas continuam vazias — o
    laboratório nem chegou a ligar os ouvintes."""
    pagina, _entrega = _pagina("caso_minimo_firm.json")
    dados = _dados_embutidos(pagina)
    verdadeiro = dados["resultados"]["cenarios"]["base"]["valor"]["preco_acao"]
    adulterado = verdadeiro + 1.0
    dados["resultados"]["cenarios"]["base"]["valor"]["preco_acao"] = adulterado

    fotos = _laboratorio_vivo(pagina, tmp_path, dados=dados, passos=[
        {"nome": "forcado", "acao": "editar", "cenario": "base", "premissa": "roic", "valor": "30"},
    ])
    carga = fotos["carga"]

    assert carga["badge"]["estado"] == "divergente", carga["badge"]
    assert carga["badge"]["texto"] == render.t(DICIONARIO, "valuation.laboratorio_paridade_divergente")
    assert len(carga["badge"]["itens"]) == 1, carga["badge"]["itens"]
    item = carga["badge"]["itens"][0]
    assert "base" in item and "valor.preco_acao" in item, item
    numeros = _numeros_do_texto(item)
    assert any(abs(n - adulterado) <= 1e-9 for n in numeros), (item, adulterado)
    assert any(abs(n - verdadeiro) / max(abs(verdadeiro), 1.0) <= 1e-12 for n in numeros), (item, verdadeiro)

    assert carga["campos"] and all(campo["disabled"] for campo in carga["campos"]), carga["campos"]
    assert carga["botoes"] and all(carga["botoes"]), carga["botoes"]
    vazio = render.t(DICIONARIO, "valuation.laboratorio_sem_valor")
    sem_numero = {"preco": vazio, "multiplo": vazio, "multiploRotulo": "", "upside": vazio}
    assert carga["saidas"] == {"base": sem_numero}
    assert fotos["forcado"]["saidas"] == {"base": sem_numero}


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_um_contrato_que_a_fachada_nao_le_trava_o_painel_e_diz_por_que(tmp_path):
    """A outra metade de L4: a fachada RECUSA um `resultados` de outra versão
    de contrato (é o que a v10 encontraria). O painel não compara, não liga e
    não esconde a razão — badge `indisponivel` citando as duas versões."""
    pagina, _entrega = _pagina("caso_minimo_firm.json")
    dados = _dados_embutidos(pagina)
    dados["resultados"]["versao_contrato"] = "resultados/2"

    carga = _laboratorio_vivo(pagina, tmp_path, dados=dados)["carga"]
    assert carga["badge"]["estado"] == "indisponivel", carga["badge"]
    assert "resultados/1" in carga["badge"]["texto"] and "resultados/2" in carga["badge"]["texto"]
    assert all(campo["disabled"] for campo in carga["campos"])
    assert all(carga["botoes"])
    vazio = render.t(DICIONARIO, "valuation.laboratorio_sem_valor")
    assert carga["saidas"]["base"]["preco"] == vazio


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_o_badge_verde_libera_a_edicao_e_os_numeros_andam_com_o_motor(tmp_path):
    """O ciclo inteiro, de ponta a ponta, contra o PYTHON:

    1. carga — badge `ok`, campos editáveis, e as três saídas mostram
       exatamente o que o Python publicou, formatado como o cabeçalho;
    2. edição de uma premissa — as três saídas passam a mostrar exatamente o
       que `avaliar()` publica para o caso COM aquela edição (não "algum
       número que mudou": o mesmo número do motor congelado);
    3. campo numérico esvaziado — o campo é marcado inválido e o cenário
       fica sem número, em vez de virar zero ou voltar em silêncio ao
       original;
    4. restaurar — campo e saídas voltam ao original, e o `caso` embutido
       nunca foi tocado (§8.3: simular sem sobrescrever a calibração)."""
    pagina, entrega = _pagina("caso_minimo_firm.json")
    moeda = entrega["caso"]["moeda"]
    roic_original = entrega["caso"]["cenarios"]["base"]["premissas"]["roic"]
    roic_editado = roic_original + 5.0

    fotos = _laboratorio_vivo(pagina, tmp_path, passos=[
        {"nome": "editado", "acao": "editar", "cenario": "base", "premissa": "roic",
         "valor": json.dumps(roic_editado)},
        {"nome": "invalido", "acao": "editar", "cenario": "base", "premissa": "roic", "valor": ""},
        {"nome": "restaurado", "acao": "restaurar", "cenario": "base"},
    ])

    carga = fotos["carga"]
    assert carga["badge"]["estado"] == "ok", carga["badge"]
    assert carga["badge"]["texto"] == render.t(DICIONARIO, "valuation.laboratorio_paridade_ok")
    assert carga["campos"] and not any(campo["disabled"] for campo in carga["campos"])
    assert not any(carga["botoes"])
    assert carga["saidas"]["base"] == _saidas_publicadas(entrega["resultados"], moeda)

    def _editar_roic(caso: dict) -> None:
        caso["cenarios"]["base"]["premissas"]["roic"] = roic_editado

    editada = apoio.montar_entrega("caso_minimo_firm.json", mutar_caso=_editar_roic)
    assert fotos["editado"]["saidas"]["base"] == _saidas_publicadas(editada["resultados"], moeda)
    assert fotos["editado"]["saidas"]["base"]["preco"] != carga["saidas"]["base"]["preco"], \
        "a edição não moveu o preço — o teste deixou de discriminar"

    vazio = render.t(DICIONARIO, "valuation.laboratorio_sem_valor")
    assert fotos["invalido"]["saidas"]["base"]["preco"] == vazio
    campo_invalido = next(c for c in fotos["invalido"]["campos"] if c["premissa"] == "roic")
    assert campo_invalido["invalido"] == "true"

    restaurado = fotos["restaurado"]
    assert restaurado["saidas"] == carga["saidas"]
    campo_roic = next(c for c in restaurado["campos"] if c["premissa"] == "roic")
    assert float(campo_roic["value"]) == roic_original and campo_roic["invalido"] is None
    assert fotos["casoIntacto"] is True


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_o_laboratorio_devolve_o_texto_de_sem_valor_para_o_que_a_fachada_recusou():
    """Um cenário recusado pela fachada publica `null` nos três números (é o
    que o laboratório vai produzir o tempo todo, editando premissa para fora
    do domínio). A tela recebe o texto de "sem valor" do dicionário — nunca
    "null", nunca "NaN", nunca um zero plausível."""
    script = (
        "const fs = require('fs'); const vm = require('vm');"
        "const ctx = vm.createContext({});"
        "vm.runInContext(fs.readFileSync(%s, 'utf8'), ctx);"
        "console.log(JSON.stringify(vm.runInContext("
        "  '[FleetLaboratorio.formatar(null, {casas:2}, \"pt-BR\", \"--\"),"
        "    FleetLaboratorio.formatar(NaN, {casas:2}, \"pt-BR\", \"--\"),"
        "    FleetLaboratorio.textoDe(\"{a} e {b}\", {a: 1, b: \"x\"})]', ctx)));"
    ) % json.dumps(str(ASSETS / "laboratorio.js"))
    r = subprocess.run(["node", "-e", script], capture_output=True, text=True,
                       encoding="utf-8", timeout=120)
    assert r.returncode == 0, r.stdout + r.stderr
    assert json.loads(r.stdout) == ["--", "--", "1 e x"]


# --------------------------------------------------------------------------
# Fatia 5C, Task 3 — o diagnóstico ao vivo pela TELA: a regra inegociável do
# §8.4 com o bootstrap real, a marcação emitida e o motor de verdade. O que se
# confere é o que o analista vê: o texto e a classe de cada item, na ordem.
# --------------------------------------------------------------------------

def _itens_publicados(resultados: dict) -> list:
    """Os itens de diagnóstico de `base` como a tela deve mostrá-los, a partir
    das chaves que o PYTHON publicou: as do cenário e, num cenário com degrau,
    as do degrau depois delas — rótulo e severidade do catálogo."""
    cenario = resultados["cenarios"]["base"]
    chaves = list(cenario["diagnosticos_chaves"])
    if "degrau" in cenario:
        chaves += cenario["degrau"]["diagnosticos_chaves"]
    if not chaves:
        return [{"texto": render.t(DICIONARIO, "valuation.laboratorio_diagnosticos_nenhum"),
                 "classe": "lab-diagnostico lab-diagnostico-vazio"}]
    return [{"texto": CATALOGO["diagnosticos"][chave]["rotulo"]["pt-BR"],
             "classe": "lab-diagnostico lab-diagnostico-" + CATALOGO["diagnosticos"][chave]["severidade"]}
            for chave in chaves]


# As mesmas edições de `test_espelho_fachada_js.py::test_o_diagnostico_se_move_com_o_numero_na_
# mesma_chamada`, uma por forma — lá está o predicado que cada uma cruza.
_EDICOES_PELA_TELA = [
    pytest.param("caso_minimo_firm.json", "roic", 8.0, id="firm"),
    pytest.param("caso_rampa.json", "g2", 20.0, id="rampa"),
    pytest.param("caso_degrau.json", "roe", 30.0, id="degrau"),
]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
@pytest.mark.parametrize("fixture,premissa,editado", _EDICOES_PELA_TELA)
def test_editar_a_premissa_acende_o_diagnostico_na_tela_e_restaurar_o_apaga(
        fixture, premissa, editado, tmp_path):
    """§8.4 pela tela, uma vez por forma (firm, rampa, degrau): na carga, os
    itens são exatamente os que o Python publicou, rotulados pelo catálogo;
    editar o campo — um evento de input, nada mais — faz a tela mostrar os
    itens que `avaliar()` publica para o caso EDITADO, com UM item novo (o
    alerta que a edição acendeu, na classe da sua severidade), no mesmo passo
    em que o preço se move; restaurar devolve os itens da carga."""
    pagina, entrega = _pagina(fixture)

    def _editar(caso: dict) -> None:
        caso["cenarios"]["base"]["premissas"][premissa] = editado

    editada = apoio.montar_entrega(fixture, mutar_caso=_editar)
    fotos = _laboratorio_vivo(pagina, tmp_path, passos=[
        {"nome": "editado", "acao": "editar", "cenario": "base", "premissa": premissa,
         "valor": json.dumps(editado)},
        {"nome": "restaurado", "acao": "restaurar", "cenario": "base"},
    ])
    carga = fotos["carga"]
    assert carga["badge"]["estado"] == "ok", carga["badge"]

    na_carga = _itens_publicados(entrega["resultados"])
    na_edicao = _itens_publicados(editada["resultados"])
    novos = [item for item in na_edicao if item not in na_carga]
    assert len(novos) == 1, novos
    assert novos[0]["classe"] == "lab-diagnostico lab-diagnostico-alerta", novos

    assert carga["diagnosticos"]["base"] == na_carga
    assert fotos["editado"]["diagnosticos"]["base"] == na_edicao
    assert fotos["editado"]["saidas"]["base"]["preco"] != carga["saidas"]["base"]["preco"], \
        "a edição não moveu o preço — número e diagnóstico deixaram de andar juntos no teste"
    assert fotos["restaurado"]["diagnosticos"]["base"] == na_carga


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_uma_chave_de_diagnostico_adulterada_deixa_o_badge_vermelho_e_nomeada(tmp_path):
    """T4 na tela: o `resultados` embutido passa a publicar uma chave que o
    motor do navegador não acende — uma chave REAL do catálogo, para provar que
    o badge compara chaves e não depende de rótulo. Badge `divergente`, UM item
    que nomeia o cenário, o caminho e a chave adulterada; campos travados; e a
    lista de diagnósticos fica no "sem valor" — nenhum diagnóstico de um motor
    que o relatório não sustenta chega à tela."""
    pagina, _entrega = _pagina("caso_minimo_firm.json")
    dados = _dados_embutidos(pagina)
    publicadas = dados["resultados"]["cenarios"]["base"]["diagnosticos_chaves"]
    adulterada = next(chave for chave in sorted(CATALOGO["diagnosticos"]) if chave not in publicadas)
    dados["resultados"]["cenarios"]["base"]["diagnosticos_chaves"] = publicadas + [adulterada]

    carga = _laboratorio_vivo(pagina, tmp_path, dados=dados)["carga"]
    assert carga["badge"]["estado"] == "divergente", carga["badge"]
    assert len(carga["badge"]["itens"]) == 1, carga["badge"]["itens"]
    item = carga["badge"]["itens"][0]
    assert "base" in item and "diagnosticos_chaves" in item and adulterada in item, item
    assert carga["campos"] and all(campo["disabled"] for campo in carga["campos"])
    vazio = render.t(DICIONARIO, "valuation.laboratorio_sem_valor")
    assert carga["diagnosticos"]["base"] == [
        {"texto": vazio, "classe": "lab-diagnostico lab-diagnostico-vazio"}]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_uma_chave_que_o_payload_nao_rotula_vira_texto_do_dicionario_nunca_a_chave_crua(tmp_path):
    """T5 e a lição do B2: se o payload não traz rótulo para uma chave que a
    fachada devolveu, a tela escreve o texto do dicionário para isso — nunca a
    chave. O badge continua verde: a paridade é das chaves, e as chaves batem;
    o que falta é só o rótulo."""
    pagina, entrega = _pagina("caso_minimo_firm.json")
    dados = _dados_embutidos(pagina)
    publicadas = entrega["resultados"]["cenarios"]["base"]["diagnosticos_chaves"]
    sem_rotulo = publicadas[0]
    del dados["diagnosticos"][sem_rotulo]

    carga = _laboratorio_vivo(pagina, tmp_path, dados=dados)["carga"]
    assert carga["badge"]["estado"] == "ok", carga["badge"]
    itens = carga["diagnosticos"]["base"]
    assert len(itens) == len(publicadas), itens
    assert itens[0] == {
        "texto": render.t(DICIONARIO, "valuation.laboratorio_diagnostico_desconhecido"),
        "classe": "lab-diagnostico lab-diagnostico-desconhecido",
    }
    assert not any(sem_rotulo in item["texto"] for item in itens), itens


# --------------------------------------------------------------------------
# Onda de correção da revisão final da 5C — F1 e F4 pela tela.
# --------------------------------------------------------------------------

def _item_do_catalogo(chave: str) -> dict:
    info = CATALOGO["diagnosticos"][chave]
    return {"texto": info["rotulo"]["pt-BR"],
            "classe": "lab-diagnostico lab-diagnostico-" + info["severidade"]}


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_a_divergencia_de_base_do_degrau_aparece_na_tela_e_some_com_a_edicao(tmp_path):
    """F1 (ALTO) pela tela. Na carga de `caso_degrau` (16,4%) o laboratório já
    mostra a divergência de base acima do limiar, com rótulo e severidade do
    catálogo — antes, só a prosa estática da aba Tese a mencionava. Editar ROE
    para 17,2 (0,16%) apaga o item no mesmo evento em que o preço anda, e a
    tela passa a mostrar exatamente o que `avaliar()` publica para o caso
    editado; restaurar o devolve."""
    pagina, entrega = _pagina("caso_degrau.json")
    item = _item_do_catalogo(CATALOGO["disclosures"]["divergencia_de_base_degrau"]["chave"])

    def _editar(caso: dict) -> None:
        caso["cenarios"]["base"]["premissas"]["roe"] = 17.2

    editada = apoio.montar_entrega("caso_degrau.json", mutar_caso=_editar)
    fotos = _laboratorio_vivo(pagina, tmp_path, passos=[
        {"nome": "editado", "acao": "editar", "cenario": "base", "premissa": "roe", "valor": "17.2"},
        {"nome": "restaurado", "acao": "restaurar", "cenario": "base"},
    ])
    carga = fotos["carga"]
    assert carga["badge"]["estado"] == "ok", carga["badge"]

    assert carga["diagnosticos"]["base"] == _itens_publicados(entrega["resultados"])
    assert item in carga["diagnosticos"]["base"]
    assert fotos["editado"]["diagnosticos"]["base"] == _itens_publicados(editada["resultados"])
    assert item not in fotos["editado"]["diagnosticos"]["base"]
    assert fotos["editado"]["saidas"]["base"]["preco"] != carga["saidas"]["base"]["preco"], \
        "a edição não moveu o preço — número e diagnóstico deixaram de andar juntos no teste"
    assert fotos["restaurado"]["diagnosticos"]["base"] == carga["diagnosticos"]["base"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_uma_forma_nova_que_a_fachada_exibe_chega_a_tela_sem_editar_o_laboratorio(tmp_path):
    """F4 (MÉDIO, E3) — a sonda P6 da revisão, agora com a correção no lugar.
    Um módulo extra, carregado depois dos três da página, simula uma fachada
    v10 que publica uma forma ADITIVA de diagnóstico
    (`cenarios.<n>.transicao.diagnosticos_chaves`, com uma chave real do
    catálogo que a fixture não acende) e a inclui na lista exibível. A tela a
    mostra, rotulada, sem nenhuma linha nova no laboratório: ele pinta
    `diagnosticos_exibidos` e não conhece forma nenhuma. Um laboratório que
    voltasse a juntar as listas por caminho a deixaria de fora."""
    pagina, entrega = _pagina("caso_minimo_firm.json")
    forma_nova = "degrau_alerta"
    assert forma_nova in CATALOGO["diagnosticos"]
    assert forma_nova not in entrega["resultados"]["cenarios"]["base"]["diagnosticos_chaves"]

    fachada_v10 = tmp_path / "fachada_v10.js"
    fachada_v10.write_text(
        "(function () {\n"
        "  var avaliarCaso = FachadaEspelho.avaliarCaso;\n"
        "  FachadaEspelho.avaliarCaso = function (caso) {\n"
        "    var vivo = avaliarCaso(caso);\n"
        "    Object.keys(vivo.cenarios).forEach(function (nome) {\n"
        "      var cenario = vivo.cenarios[nome];\n"
        "      cenario.transicao = { diagnosticos_chaves: [" + json.dumps(forma_nova) + "] };\n"
        "      cenario.diagnosticos_exibidos =\n"
        "        cenario.diagnosticos_exibidos.concat(cenario.transicao.diagnosticos_chaves);\n"
        "    });\n"
        "    return vivo;\n"
        "  };\n"
        "}());\n", encoding="utf-8")

    carga = _laboratorio_vivo(pagina, tmp_path, modulos_extra=[fachada_v10])["carga"]
    assert carga["badge"]["estado"] == "ok", carga["badge"]
    assert carga["diagnosticos"]["base"] == (
        _itens_publicados(entrega["resultados"]) + [_item_do_catalogo(forma_nova)])


# --------------------------------------------------------------------------
# Onda de correção da revisão final da 5C — F2 e F3 pela tela.
# --------------------------------------------------------------------------

def _item_de_recusa(motivo: str) -> dict:
    return {"texto": render.t(DICIONARIO, "valuation.laboratorio_diagnosticos_recusado").replace(
                "{motivo}", motivo),
            "classe": "lab-diagnostico lab-diagnostico-recusado"}


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
@pytest.mark.parametrize("fixture,premissa,valor,codigo", [
    pytest.param("caso_minimo_firm.json", "gp", "10", "nucleo_nao_finito", id="F2-firm-gp-igual-ao-wacc"),
    pytest.param("caso_minimo_firm.json", "n", "10.5", "dominio_da_cli", id="F2-firm-n-fracionario"),
    pytest.param("caso_degrau.json", "tv", "book", "degrau_book_sem_roe_book", id="F3-degrau-book-sem-roe-book"),
])
def test_um_cenario_recusado_mostra_o_motivo_e_nunca_nenhum_diagnostico(
        fixture, premissa, valor, codigo, tmp_path):
    """F2 e F3 pela tela, um evento de campo cada. Antes: `gp = 10` sob gordon
    apagava as saídas e a lista dizia "Nenhum diagnóstico disparado por estas
    premissas." (o motor emite quatro); trocar a convenção do degrau para Book
    no `select` mostrava R$ 42,56 com badge verde, numa combinação que o gate
    recusa. Agora as saídas ficam em "—" e a lista mostra UM item: a moldura
    do dicionário com o motivo rotulado pelo catálogo — nunca o texto de
    "nenhum", nunca o código cru. Restaurar devolve os itens da carga."""
    pagina, _entrega = _pagina(fixture)
    fotos = _laboratorio_vivo(pagina, tmp_path, passos=[
        {"nome": "recusado", "acao": "editar", "cenario": "base", "premissa": premissa, "valor": valor},
        {"nome": "restaurado", "acao": "restaurar", "cenario": "base"},
    ])
    carga, recusado = fotos["carga"], fotos["recusado"]
    assert carga["badge"]["estado"] == "ok", carga["badge"]

    vazio = render.t(DICIONARIO, "valuation.laboratorio_sem_valor")
    assert recusado["saidas"]["base"]["preco"] == vazio
    assert recusado["saidas"]["base"]["multiplo"] == vazio
    assert recusado["saidas"]["base"]["upside"] == vazio
    itens = recusado["diagnosticos"]["base"]
    assert itens == [_item_de_recusa(CATALOGO["recusas"][codigo]["rotulo"]["pt-BR"])], itens
    nenhum = render.t(DICIONARIO, "valuation.laboratorio_diagnosticos_nenhum")
    assert not any(nenhum in item["texto"] or codigo in item["texto"] for item in itens), itens
    assert fotos["restaurado"]["diagnosticos"]["base"] == carga["diagnosticos"]["base"]
    assert fotos["restaurado"]["saidas"]["base"] == carga["saidas"]["base"]


@pytest.mark.skipif(SEM_NODE, reason=RAZAO_SEM_NODE)
def test_um_motivo_que_o_payload_nao_rotula_vira_texto_do_dicionario_nunca_o_codigo_cru(tmp_path):
    """A lição do B2 aplicada à recusa: sem o rótulo do motivo no payload, a
    moldura leva o texto de motivo desconhecido do dicionário — o código que a
    fachada publicou nunca chega à tela."""
    pagina, _entrega = _pagina("caso_minimo_firm.json")
    dados = _dados_embutidos(pagina)
    del dados["recusas"]["nucleo_nao_finito"]

    fotos = _laboratorio_vivo(pagina, tmp_path, dados=dados, passos=[
        {"nome": "recusado", "acao": "editar", "cenario": "base", "premissa": "gp", "valor": "10"},
    ])
    itens = fotos["recusado"]["diagnosticos"]["base"]
    assert itens == [_item_de_recusa(render.t(DICIONARIO, "valuation.laboratorio_recusa_desconhecida"))], itens
    assert "nucleo_nao_finito" not in itens[0]["texto"]

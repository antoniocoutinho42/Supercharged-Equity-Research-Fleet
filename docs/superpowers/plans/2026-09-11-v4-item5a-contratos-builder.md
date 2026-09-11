# Item 5, fatia A — contratos de integração e esqueleto do builder (`er-relatorio`)

> **Para agentes:** REQUIRED SUB-SKILL: `superpowers:subagent-driven-development`. Calibragem de rigor em
> vigor (ledger, 26/08/2026): implementação simples, testes que discriminam a matemática e os contratos,
> sem revisor por task, **uma** revisão final da fatia. Achado não material: registre no relatório e siga.

**Goal:** a camada de integração passa a publicar, como contrato versionado, tudo o que o relatório precisa
exibir — e o builder de três abas nasce consumindo **só** esses contratos, com QC de três níveis que recusa
emitir.

**Architecture:** emenda **E3** do desenho (`docs/desenho-arquitetura-v4.md` §15): o relatório não duplica nem
reimplementa metodologia. Ele consome três contratos da integração — `resultados.json` v1 (wrapper),
`catalogo_apresentacao.json` (integração) e, na fatia 5C, a fachada do espelho. O builder recebe **um**
artefato (`entrega.json`) numa raiz de execução, valida o contrato, compõe canonicamente, resolve
placeholders auditáveis, roda o QC e emite um HTML autocontido — ou recusa.

**Tech Stack:** Python stdlib (sem `jsonschema`: o CI só instala `pytest pyyaml`, e a validação segue o padrão
de `caso.py` — guardas estruturais e vocabulário fechado); HTML/CSS/JS inline; pytest.

## Global Constraints

- **E3, mecanizada:** nenhum módulo de `skills/er-relatorio/scripts/` importa módulo de `er-valuation` nem do
  vendor. O relatório lê só dados (JSON) e assets declarados numa única constante. Teste estrutural trava.
- **Upgrade da skill é requisito:** todo conhecimento metodológico exibido vem de `resultados.json` ou do
  catálogo. O catálogo declara a versão da metodologia, e um teste reprova se ela divergir do manifest do
  vendor — trocar o vendor sem revisar o catálogo falha na camada de integração, nunca no relatório.
- **Regra inviolável 1:** nenhuma aritmética de valuation fora do motor. Comparação entre outputs (upside,
  divergência) e múltiplo de tela (definição de múltiplo aplicada a dados declarados, como `alvo_de_mercado`
  já faz) são permitidos.
- **Regra inviolável 2:** qualquer HARD FAIL ⟹ nenhum `relatorio.html` é escrito.
- **Regra inviolável 6:** o builder aceita uma única raiz de execução, lê só `entrega.json` dela e escreve só
  dentro dela.
- **§16.1:** todo texto de interface e de QC vem de `assets/i18n/<idioma>.json`; pt-BR é o default, não
  hardcode. Número formatado por idioma, determinístico, sem o módulo `locale`.
- **Vocabulário fechado em todo contrato novo** (lições F6 da 4C e F3 da D): chave desconhecida é recusada
  pelo nome, com sugestão por `difflib.get_close_matches`.
- **Determinismo:** mesma entrada ⟹ mesmos bytes. Sem relógio, sem caminho absoluto no artefato.
- `vendor/` read-only; suíte em primeiro plano (timeout até 10 min); commit assim que verde, antes do
  relatório; mutação, teste e restauração num único comando. Baseline **499 passed**.

## O mapa do item 5 — quatro fatias, uma revisão por fatia

| Fatia | Entrega |
|---|---|
| **5A** (este plano) | Contratos de integração + esqueleto do builder + QC de três níveis (framework e primeiras regras) |
| 5B | Gráficos: gramática da §10, uPlot vendorizado, módulo SVG (waterfall, matriz/heatmap, decomposição), regra de cobertura |
| 5C | Laboratório (aba Valuation): fachada versionada do espelho no shape do `resultados.json`; badge de paridade (a fachada recomputa cada cenário e compara); premissas por bloco a partir do catálogo; original × editado; diagnóstico ao vivo por chave |
| 5D | Abas Tese e Evidência completas + QC completo da §11 |

Cada fatia seguinte ganha plano próprio, conferido no código antes do despacho.

## Decisões de desenho — tomadas, com a razão

- **A1 — `entrega.json` é o artefato único (E2).** Mora na raiz da execução e embute, em composição canônica,
  as partes: `caso`, `resultados`, `analise`, `ledger`, `ficha_tecnica`. Em produção quem compõe é o
  `er-analise` (item 8); nesta fatia, um apoio de teste.
- **A2 — Correspondência provada por hash, sem rodar nada.** O wrapper grava `origem.caso_sha256` (JSON
  canônico: `sort_keys=True`, `separators=(",", ":")`, `ensure_ascii=False`, utf-8). O builder recalcula e
  compara. A canonicalização é contrato documentado nos dois lados, com teste cruzado — são três linhas, e
  duplicá-las é o preço de o relatório não importar a integração.
- **A3 — `cenario_base` no caso.** Hoje nenhum cenário é tratado como "o base" (`avaliar.py` recusa convenção
  implícita). Campo de topo opcional: obrigatório quando houver mais de um cenário, implícito quando houver
  um só, e sempre um cenário declarado. É declaração do analista, não do relatório.
- **A4 — `manchete`: o wrapper diz qual preço é a resposta.** SOTP quando declarado; senão, o cenário-base.
  Fecha o resíduo "dois preços por ação sem marcar qual é a resposta". Traz o múltiplo que o próprio wrapper
  já calcula para aquele preço, com a sua `base`.
- **A5 — Diagnósticos por chave, publicados pelo wrapper.** O classificador por prefixo sai do teste da 4C e
  vira função pública da integração. Mensagem sem chave vira `null` — o valuation segue, e o builder trata
  `null` como HARD FAIL: a atualização fica na camada de integração, em voz alta.
- **A6 — Catálogo de apresentação na integração.** Bloco econômico, unidade, tipo de entrada e rótulo de cada
  premissa por rota; rótulo e base de cada múltiplo; severidade, bloco e rótulo de cada diagnóstico; limiares
  de disclosure. O relatório só lê.
- **A7 — Placeholders auditáveis** (espírito da v3): `{{resultados:caminho|formato}}`, `{{caso:caminho|formato}}`
  e `{{livre:texto}}` para número livre legítimo. Todo dígito na prosa fora de placeholder é HARD FAIL.
- **A8 — QC de três níveis desde já.** HARD FAIL não emite; REQUIRED DISCLOSURE aparece no HTML; QUALITY
  WARNING vai só para `qc.json`. Esta fatia traz o framework e as regras que os contratos novos exigem; a 5D
  completa a lista da §11.

**Fora desta fatia — registrado:** o `multiplos` de um cenário com degrau continua o da rota P/L (a manchete
já traz o P/VP com degrau; o rótulo por cenário é revisto na 5C, com a fachada); `avisos_dominio` como texto
solto sem chave (resíduo da 4C); diagnósticos dentro da reversa (`guardas_v9_4`).

## File Structure

| Arquivo | Responsabilidade |
|---|---|
| `skills/er-valuation/scripts/diagnosticos.py` (novo) | Classificador público: mensagem do motor → chave |
| `skills/er-valuation/scripts/caso.py` | `cenario_base` no contrato do caso |
| `skills/er-valuation/scripts/avaliar.py` | `versao_contrato`, `origem`, `manchete`, `mercado_tela`, `diagnosticos_chaves` |
| `skills/er-valuation/scripts/reversa.py` | `alvo_de_mercado` com ramo explícito para rampa e equity |
| `skills/er-valuation/scripts/sensibilidades.py` | `diagnosticos_unicos_chaves` nas grades |
| `skills/er-valuation/assets/catalogo_apresentacao.json` (novo) | O catálogo (A6) |
| `skills/er-relatorio/SKILL.md` (novo) | Índice da skill: contrato, CLI, E3 |
| `skills/er-relatorio/scripts/entrega.py` (novo) | Contrato de `entrega.json` e `sha256_canonico` |
| `skills/er-relatorio/scripts/placeholders.py` (novo) | Resolução de placeholders e formatação por idioma |
| `skills/er-relatorio/scripts/qc.py` (novo) | Níveis, achados e as regras desta fatia |
| `skills/er-relatorio/scripts/render.py` (novo) | Composição do HTML das três abas |
| `skills/er-relatorio/scripts/builder.py` (novo) | CLI e orquestração: raiz única, emite ou recusa |
| `skills/er-relatorio/assets/template.html`, `assets/i18n/pt-BR.json` (novos) | Casca do HTML e dicionário |
| `tests/test_valuation_contrato.py`, `tests/test_catalogo_apresentacao.py`, `tests/test_relatorio_*.py`, `tests/relatorio_apoio.py` (novos) | Testes e apoio de fixture |

---

## Task 1: contrato `resultados.json` v1 (er-valuation)

**Files:** create `skills/er-valuation/scripts/diagnosticos.py`, `tests/test_valuation_contrato.py`,
`tests/fixtures/caso_degrau.json`; modify `caso.py`, `avaliar.py`, `reversa.py`, `sensibilidades.py`,
`tests/test_paridade_wrapper_js.py`, `skills/er-valuation/SKILL.md`.

**Interfaces — produz:**
- `diagnosticos.classificar(mensagem: str) -> str | None` — a chave cujo `prefixo` (em
  `assets/diagnosticos_chaves.json`) casa com a mensagem; `None` se nenhuma ou mais de uma casar.
- `diagnosticos.CHAVES: tuple[str, ...]` — todas as chaves do arquivo.
- Campos novos em `resultados.json` (todos os existentes ficam intactos):

```json
{
  "versao_contrato": "resultados/1",
  "origem": {"caso_sha256": "<hex>", "metodologia": {"nome": "multiplos-justos", "versao": "v9.31"}},
  "manchete": {"fonte": "cenarios", "cenario": "base", "preco_acao": 61.91, "upside": 0.12563636363636355,
               "multiplo": {"chave": "EV/EBITDA_curr", "base": "ebitda", "valor": 6.6906}},
  "mercado_tela": {"chave": "EV/EBITDA_curr", "base": "ebitda", "valor": 6.0, "algebra": "market_cap = ..."},
  "cenarios": {"base": {"...": "...", "diagnosticos_chaves": ["...", "..."]}},
  "sensibilidades": {"grades_1d": [{"...": "...", "diagnosticos_unicos_chaves": ["..."]}]}
}
```

**Regras do contrato:**
1. `versao_contrato` é sempre `"resultados/1"` (acréscimos compatíveis não mudam; mudança incompatível vira `/2`).
2. `origem.caso_sha256` = sha256 do JSON canônico do caso **como carregado**; `origem.metodologia.versao` sai de
   `skills/er-multiplos-justos/manifest_vendor.json`.
3. `manchete`: com `sotp` no caso → `{"fonte": "sotp", "cenario": sotp.cenario, "preco_acao": sotp.preco_acao,
   "upside": ...}` e **sem** `multiplo`; senão → `{"fonte": "cenarios", "cenario": <cenário-base>,
   "preco_acao": cenarios[base].valor.preco_acao, "upside": ..., "multiplo": {...}}`. `upside` =
   `preco_acao / preco.valor − 1`. `multiplo.chave` é a do múltiplo que o wrapper já devolve para aquele preço:
   `EV/EBITDA_curr` ou `EV/NOPAT_curr` (firm, conforme a métrica), `PL_curr` (equity), `EV/EBITDA0` (rampa) e,
   num cenário com degrau, `PVP_com_degrau` com o `com_transicao` do degrau. `base`: `ebitda`, `nopat`, `pl`,
   `ebitda0`, `pvp`.
4. `mercado_tela`: mesma `base` da manchete. Firm e equity: o `alvo_de_mercado` que já existe. Rampa: **hoje o
   `else` de `alvo_de_mercado` trata tudo o que não é firm como equity — a rampa sairia como P/L sobre EBITDA0.**
   Nunca foi alcançado porque a reversa recusa a rampa no gate; publicado sempre, vira número errado.
   Acrescente o ramo explícito da rampa (lado EV, igual ao firm, base `ebitda0`), torne o equity explícito, e
   rota desconhecida levanta `ValueError`. Degrau: `{"chave": "PVP", "base": "pvp", "valor": preco / vpa}`, com
   a álgebra. `chave` do `mercado_tela` = a da manchete, exceto no degrau (`PVP` de tela contra
   `PVP_com_degrau` justo — o relatório pareia por `base`).
5. `diagnosticos_chaves` em todo cenário, **mesmo comprimento e ordem** de `diagnosticos` (firm, equity, degrau).
   Na rampa, que não emite `diagnosticos`: as chaves de aviso presentes, na ordem `aviso_colheita`,
   `aviso_delator`, `aviso_gp`. Nas grades: `diagnosticos_unicos_chaves` paralelo a `diagnosticos_unicos`.
6. `cenario_base` (A3): texto que nomeia um cenário declarado; obrigatório com mais de um cenário; entra em
   `CHAVES_DE_TOPO_PERMITIDAS`. Fixtures com mais de um cenário ganham o campo.

**Detalhes que um implementer apressado erra:**
- O classificador tem de ser **o mesmo** que a paridade da 4C usa: troque o `_classificar` inline de
  `tests/test_paridade_wrapper_js.py` por `diagnosticos.classificar` — uma fonte só.
- O hash é do caso **como carregado** por `caso.carregar`, não do arquivo em bytes: reordenar chaves ou mudar
  espaçamento do `caso.json` não pode mudar o hash.
- `tests/fixtures/caso_degrau.json`: a âncora do SKILL.md do vendor que `tests/test_valuation_degrau.py` já usa,
  como fixture em arquivo, para esta task e a 5C.

**Testes (`tests/test_valuation_contrato.py`):**

```python
import hashlib, json, sys
from pathlib import Path
import pytest

RAIZ = Path(__file__).resolve().parent.parent
FIXTURES = RAIZ / "tests" / "fixtures"
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from avaliar import avaliar  # noqa: E402
from caso import CasoInvalido, carregar, validar  # noqa: E402
import diagnosticos  # noqa: E402

CASOS = sorted(p.name for p in FIXTURES.glob("caso_*.json"))
MANIFEST = json.loads((RAIZ / "skills" / "er-multiplos-justos" / "manifest_vendor.json").read_text(encoding="utf-8"))


def _sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"),
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def resultados():
    return {nome: (carregar(FIXTURES / nome), avaliar(carregar(FIXTURES / nome))) for nome in CASOS}


def test_versao_e_origem_em_todo_resultado(resultados):
    for nome, (caso, r) in resultados.items():
        assert r["versao_contrato"] == "resultados/1", nome
        assert r["origem"]["caso_sha256"] == _sha(caso), nome
        assert r["origem"]["metodologia"] == {"nome": "multiplos-justos", "versao": MANIFEST["versao"]}, nome


def test_hash_ignora_ordem_de_chaves_do_arquivo(tmp_path):
    caso = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    invertido = tmp_path / "caso.json"
    invertido.write_text(json.dumps(dict(reversed(list(caso.items()))), indent=4), encoding="utf-8")
    assert avaliar(carregar(invertido))["origem"]["caso_sha256"] == _sha(caso)


def test_diagnosticos_chaves_paralelas_e_classificadas(resultados):
    for nome, (_caso, r) in resultados.items():
        for cen, reg in r["cenarios"].items():
            if "diagnosticos" in reg:
                assert len(reg["diagnosticos_chaves"]) == len(reg["diagnosticos"]), (nome, cen)
                assert reg["diagnosticos_chaves"] == [diagnosticos.classificar(m) for m in reg["diagnosticos"]]
            assert None not in reg["diagnosticos_chaves"], (nome, cen)


def test_manchete_aponta_um_preco_que_existe(resultados):
    for nome, (caso, r) in resultados.items():
        m = r["manchete"]
        if "sotp" in caso:
            assert m["fonte"] == "sotp" and m["preco_acao"] == r["sotp"]["preco_acao"] and "multiplo" not in m
        else:
            assert m["fonte"] == "cenarios"
            assert m["preco_acao"] == r["cenarios"][m["cenario"]]["valor"]["preco_acao"]
        assert m["upside"] == m["preco_acao"] / caso["preco"]["valor"] - 1, nome


def test_mercado_tela_da_rampa_e_do_lado_do_ev():
    caso = carregar(FIXTURES / "caso_rampa.json")
    tela = avaliar(caso)["mercado_tela"]
    assert tela["base"] == "ebitda0"
    ev_mercado = caso["preco"]["valor"] * caso["acoes_diluidas"] + avaliar(caso)["ponte"]["nd_efetivo"]
    assert tela["valor"] == ev_mercado / caso["metrica_base"]["valor"]


def test_cenario_base_obrigatorio_com_mais_de_um_cenario():
    caso = json.loads((FIXTURES / "caso_minimo_firm.json").read_text(encoding="utf-8"))
    caso["cenarios"]["bull"] = caso["cenarios"]["base"]
    with pytest.raises(CasoInvalido, match="cenario_base"):
        validar(caso)
    caso["cenario_base"] = "inexistente"
    with pytest.raises(CasoInvalido, match="cenario_base"):
        validar(caso)
    caso["cenario_base"] = "base"
    validar(caso)
```

Acrescente também os casos de `mercado_tela` para firm (o `6.0` de `caso_reversa_firm.json`), equity e degrau, e a
recusa de `cenario_base` de tipo errado. **Prova de falseabilidade:** devolva a rampa ao ramo `else` de
`alvo_de_mercado`, confirme vermelho, restaure.

---

## Task 2: catálogo de apresentação (er-valuation)

**Files:** create `skills/er-valuation/assets/catalogo_apresentacao.json`, `tests/test_catalogo_apresentacao.py`;
modify `skills/er-valuation/SKILL.md` (uma linha na seção do contrato).

**Interfaces — produz o arquivo:**

```json
{
  "versao_contrato": "catalogo/1",
  "metodologia": {"nome": "multiplos-justos", "versao": "v9.31"},
  "idiomas": ["pt-BR"],
  "blocos": {
    "earning_power": {"ordem": 1, "rotulo": {"pt-BR": "Earning power e base"}},
    "crescimento_reinvestimento": {"ordem": 2, "rotulo": {"pt-BR": "Crescimento e reinvestimento"}},
    "custo_capital": {"ordem": 3, "rotulo": {"pt-BR": "Custo de capital"}},
    "duracao_terminal": {"ordem": 4, "rotulo": {"pt-BR": "Duração e terminal"}}
  },
  "premissas": {
    "firm":   {"g": {"bloco": "crescimento_reinvestimento", "unidade": "pp", "entrada": "numero",
                     "rotulo": {"pt-BR": "Crescimento (g)"}}},
    "equity": {"tv": {"bloco": "duracao_terminal", "unidade": "escolha", "entrada": "escolha",
                      "opcoes": ["book", "convergencia", "gordon"], "rotulo": {"pt-BR": "Convenção terminal"}}},
    "rampa":  {}
  },
  "multiplos": {"EV/EBITDA_curr": {"base": "ebitda", "rotulo": {"pt-BR": "EV/EBITDA corrente"}}},
  "diagnosticos": {"<chave>": {"severidade": "alerta", "bloco": "crescimento_reinvestimento",
                               "rotulo": {"pt-BR": "RiR acima de 100%: crescimento não autofinanciável"}}},
  "limiares": {"divergencia_de_base_pct_disclosure": 5.0}
}
```

(os trechos acima são o formato; o arquivo lista **todas** as entradas.)

**O conteúdo — decisões do controlador, porque é conhecimento metodológico e mora aqui:**
- **Blocos (§9 do desenho):** `earning_power` — `da`, `tax`, `receita0`, `ebitda0`, `da_parque`;
  `crescimento_reinvestimento` — `g`, `roic`, `roe`, `g1`, `g2`, `util`, `wk`, `kappa`, `t_rampa`;
  `custo_capital` — `wacc`, `ke`, `gde`, `nde` (estrutura de capital do lado equity);
  `duracao_terminal` — `n`, `tv`, `roic_tv`, `roe_tv`, `gp`, `roic_book`, `roe_book`, `politica_tv`, `mid_year`.
- **Unidades:** `pp` (pontos percentuais, como o caso declara), `anos` (`n`, `t_rampa`), `moeda` (`receita0`,
  `ebitda0`, `da_parque`), `escolha` (`tv`, `politica_tv`, com `opcoes` canônicas — aliases legados nunca
  oferecidos), `booleano` (`mid_year`).
- **Severidade de diagnóstico,** pela classe do prefixo do motor: `ALERTA`, `SUB-ALERTA`, `INCOERÊNCIA`, `DOMÍNIO`
  → `alerta`; `ATENÇÃO`, `REGIME DECLARADO`, `PREMISSA NÃO ANCORADA`, `CAIXA REMUNERADO` → `atencao`;
  `NEUTRALIDADE`, `NOTA`, `CONVENÇÃO`, `POLÍTICA DE CAIXA`, `LIMITAÇÃO DECLARADA`, `ÂNCORA MACRO OK` → `nota`;
  `ECO`, `RiR =`, `Retenção` → `eco`. Os avisos da rampa: `aviso_delator` e `aviso_gp` → `alerta`,
  `aviso_colheita` → `atencao`.
- **Rótulo curto** de cada diagnóstico: uma frase de interface, fiel ao texto do motor, sem números. O texto
  completo continua sendo o do motor, lido de `resultados.json`.
- **`divergencia_de_base_pct_disclosure = 5.0`:** acima de 5%, parte relevante do incremento que o degrau parece
  criar vem do descasamento entre as duas bases (LL × ROE·VPA), não do degrau — o leitor precisa ser avisado.
  Mora aqui para ser ajustado na integração sem tocar no relatório.

**Testes (`tests/test_catalogo_apresentacao.py`) — são as travas de upgrade:**

```python
import json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "skills" / "er-valuation" / "scripts"))
from caso import _PREMISSAS_POR_ROTA  # noqa: E402
import diagnosticos  # noqa: E402

CAT = json.loads((RAIZ / "skills" / "er-valuation" / "assets" / "catalogo_apresentacao.json").read_text(encoding="utf-8"))
MANIFEST = json.loads((RAIZ / "skills" / "er-multiplos-justos" / "manifest_vendor.json").read_text(encoding="utf-8"))
AVISOS_RAMPA = {"aviso_colheita", "aviso_delator", "aviso_gp"}


def test_versao_da_metodologia_bate_com_o_vendor():
    """Trava de upgrade: trocar o vendor sem revisar o catalogo reprova AQUI, na integracao."""
    assert CAT["metodologia"]["versao"] == MANIFEST["versao"]


def test_premissas_do_catalogo_sao_exatamente_as_do_gate():
    assert {r: set(p) for r, p in CAT["premissas"].items()} == {r: set(p) for r, p in _PREMISSAS_POR_ROTA.items()}


def test_diagnosticos_do_catalogo_sao_exatamente_os_do_classificador():
    assert set(CAT["diagnosticos"]) == set(diagnosticos.CHAVES) | AVISOS_RAMPA


def test_todo_rotulo_existe_em_todo_idioma_declarado():
    def rotulos(no):
        if isinstance(no, dict):
            if "rotulo" in no:
                yield no["rotulo"]
            for v in no.values():
                yield from rotulos(v)
    for r in rotulos(CAT):
        for idioma in CAT["idiomas"]:
            assert r.get(idioma, "").strip(), r


def test_todo_bloco_referenciado_existe():
    blocos = set(CAT["blocos"])
    for rota in CAT["premissas"].values():
        assert {p["bloco"] for p in rota.values()} <= blocos
    assert {d["bloco"] for d in CAT["diagnosticos"].values() if d["bloco"]} <= blocos
```

Acrescente: toda chave de múltiplo que o wrapper emite nas fixtures (`multiplos` de cada cenário,
`manchete.multiplo.chave`, `mercado_tela.chave`) existe em `CAT["multiplos"]`; e o topo do catálogo tem
exatamente as chaves do formato acima. **Prova de falseabilidade:** mude a versão do catálogo para `v9.30`,
confirme vermelho, restaure.

---

## Task 3: contrato da entrega, placeholders e QC (er-relatorio)

**Files:** create `skills/er-relatorio/SKILL.md`, `skills/er-relatorio/scripts/{entrega,placeholders,qc,builder}.py`,
`tests/relatorio_apoio.py`, `tests/test_relatorio_contrato.py`, `tests/test_relatorio_fronteira.py`.

**Interfaces — produz:**
- `entrega.carregar(raiz: Path) -> dict` — lê `<raiz>/entrega.json`, recusando com `EntregaInvalida` caminho que
  resolva fora da raiz, JSON inválido, versão incompatível e chave desconhecida em qualquer nível.
- `entrega.sha256_canonico(obj) -> str` — a canonicalização de A2.
- `placeholders.resolver(texto: str, fontes: dict, idioma: str, onde: str) -> tuple[str, list[dict], list[dict]]`
  — texto resolvido, log de resolução, erros.
- `placeholders.formatar(valor: float, formato: str, idioma: str, moeda: str | None) -> str`.
- `qc.Achado(nivel, codigo, onde, params)`; `qc.NIVEIS = ("HARD_FAIL", "REQUIRED_DISCLOSURE", "QUALITY_WARNING")`;
  `qc.avaliar(entrega: dict, catalogo: dict, html: str | None) -> list[Achado]`.
- CLI `python skills/er-relatorio/scripts/builder.py <raiz>` → código **0** (escreveu `relatorio.html` e
  `qc.json`), **2** (HARD FAIL: só `qc.json`), **1** (uso ou contrato inválido: nada escrito, razão no stderr).
  Nesta task o HTML é a casca mínima; a Task 4 o completa.

**O contrato `entrega/1`:**

```json
{
  "versao_contrato": "entrega/1",
  "execucao": {"id": "2026-09-11-001", "ticker": "SINT3", "idioma": "pt-BR"},
  "caso": {},
  "resultados": {},
  "analise": {"conclusao": {"texto": "Valor justo de {{resultados:manchete.preco_acao|moeda}} por ação."}},
  "ledger": [],
  "ficha_tecnica": {}
}
```

Vocabulário fechado em todos os níveis definidos aqui; `resultados.versao_contrato` tem de ser `resultados/1`;
`execucao.idioma` tem de ter dicionário em `assets/i18n/`. `ledger` e `ficha_tecnica` só têm o tipo validado
nesta fatia (a 5D os detalha).

**Placeholders (A7):** `{{resultados:<caminho>|<formato>}}`, `{{caso:<caminho>|<formato>}}`, `{{livre:<texto>}}`.
Caminho pontuado, com índice de lista. Formatos: `num0`–`num4`; `pct0`–`pct2` (fração × 100); `pp0`–`pp2` (já em
pontos percentuais); `x1`, `x2` (múltiplo, sufixo `x`); `moeda` (2 casas, com o símbolo do dicionário para o código
antes do hífen de `caso.moeda`). pt-BR: milhar `.`, decimal `,`.

**QC — regras desta fatia (código, nível, gatilho):**
- `resultados_nao_correspondem_ao_caso` — HARD FAIL — `sha256_canonico(caso) != resultados.origem.caso_sha256`.
- `placeholder_nao_resolvido` — HARD FAIL — caminho inexistente ou valor não numérico.
- `numero_sem_proveniencia` — HARD FAIL — dígito na prosa de `analise` fora de placeholder (a busca roda sobre o
  texto com todos os `{{...}}` removidos).
- `diagnostico_sem_chave` — HARD FAIL — `null` em qualquer `diagnosticos_chaves` ou `diagnosticos_unicos_chaves`.
- `divergencia_de_base_degrau` — REQUIRED DISCLOSURE — `|divergencia_de_base_%|` de um cenário acima do limiar
  do catálogo.

Mensagens de QC vêm do dicionário (`qc.<codigo>`, com os `params` substituídos). `qc.json` sai sempre, em ordem
determinística.

**Teste de fronteira — a E3 mecanizada (`tests/test_relatorio_fronteira.py`):**

```python
import ast
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPTS = RAIZ / "skills" / "er-relatorio" / "scripts"
PROIBIDOS = {"caso", "motor", "avaliar", "reversa", "sensibilidades", "sotp", "ponte", "diagnosticos",
             "justos", "vetores_paridade", "vetores_solver"}


def test_relatorio_nao_importa_a_integracao_nem_o_vendor():
    """E3: o relatorio consome contratos (dados), nunca codigo da integracao ou da metodologia.
    E isto que torna a troca da multiplos-justos um trabalho da camada de integracao."""
    for arquivo in SCRIPTS.glob("*.py"):
        for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
            nomes = []
            if isinstance(no, ast.Import):
                nomes = [a.name.split(".")[0] for a in no.names]
            elif isinstance(no, ast.ImportFrom) and no.module:
                nomes = [no.module.split(".")[0]]
            assert not (set(nomes) & PROIBIDOS), f"{arquivo.name} importa {set(nomes) & PROIBIDOS}"


def test_caminho_da_integracao_so_na_constante_de_assets():
    """So literais de CODIGO contam: docstrings e comentarios podem falar da integracao a vontade."""
    alvos = ("er-valuation", "multiplos-justos", "vendor")
    for arquivo in SCRIPTS.glob("*.py"):
        arvore = ast.parse(arquivo.read_text(encoding="utf-8"))
        permitidos = set()
        for no in ast.walk(arvore):
            if isinstance(no, ast.Assign) and any(
                    isinstance(t, ast.Name) and t.id == "ASSETS_DA_INTEGRACAO" for t in no.targets):
                permitidos |= {id(c) for c in ast.walk(no) if isinstance(c, ast.Constant)}
        docstrings = {id(n.body[0].value) for n in ast.walk(arvore)
                      if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                      and n.body and isinstance(n.body[0], ast.Expr)
                      and isinstance(n.body[0].value, ast.Constant)}
        for no in ast.walk(arvore):
            if (isinstance(no, ast.Constant) and isinstance(no.value, str)
                    and id(no) not in permitidos | docstrings):
                assert not any(a in no.value for a in alvos), (arquivo.name, no.value)
```

`builder.py` declara `ASSETS_DA_INTEGRACAO = {"catalogo": RAIZ_DO_REPO / "skills" / "er-valuation" / "assets" /
"catalogo_apresentacao.json"}` numa linha só; a 5C acrescenta o espelho ali.

**Testes do contrato (`tests/test_relatorio_contrato.py`), sobre raízes montadas por `tests/relatorio_apoio.py`**
(que roda `avaliar` num caso de fixture e grava `entrega.json` com uma `analise` mínima):
emite para entrega válida (código 0, `qc.json` sem HARD FAIL); o **caso que deve falhar** da §13 — número material
sem proveniência na conclusão → código 2, sem `relatorio.html`, `qc.json` nomeando o campo; placeholder não
resolvido → 2; resultados de outro caso → 2; `null` em `diagnosticos_chaves` → 2; degrau com divergência de base de
16,4% → 0, com o REQUIRED DISCLOSURE em `qc.json`; chave desconhecida na entrega → 1, com sugestão; versão
incompatível → 1; `entrega.json` fora da raiz (symlink) ou ausente → 1 — no Windows criar symlink pode exigir privilégio: pule declarando a razão quando o SO recusar, o CI em Ubuntu roda sempre; idioma sem dicionário → 1; e a formatação
pt-BR (`6690.59|num2` → `6.690,59`; `0.12563|pct1` → `12,6%`; `6.6906|x2` → `6,69x`; negativo; zero).

**Prova de falseabilidade:** desligue a busca de `numero_sem_proveniencia`, confirme que o caso que deve falhar
passa a emitir, restaure.

---

## Task 4: as três abas (er-relatorio)

**Files:** create `skills/er-relatorio/scripts/render.py`, `skills/er-relatorio/assets/template.html`,
`skills/er-relatorio/assets/i18n/pt-BR.json`, `tests/test_relatorio_render.py`; modify `builder.py`.

**Interfaces — produz:** `render.compor(entrega: dict, catalogo: dict, achados: list, log: list, idioma: str) -> str`.

**O que cada aba mostra nesta fatia — tudo lido de contrato:**
- **Tese:** título (companhia e ticker, pelo dicionário), conclusão resolvida, e os REQUIRED DISCLOSURE visíveis.
- **Valuation (cabeçalho estático — o laboratório é a 5C):** preço da `manchete` (`moeda`), `upside` (`pct1`),
  múltiplo justo (`manchete.multiplo`) ao lado do de tela (`mercado_tela`), pareados por `base`, com rótulos do
  catálogo; rota e convenção terminal do cenário da manchete (rótulos do catálogo); preço de cada cenário quando
  houver mais de um. Sem `multiplo` na manchete (SOTP), só o preço.
- **Evidência:** metodologia (`resultados.origem.metodologia`), `ficha_tecnica`, e o log de placeholders em tabela.

**Regras de render:**
- Todo texto dinâmico passa por `html.escape` — o builder não interpreta prosa, e prosa nunca vira HTML.
- JSON embutido em `<script type="application/json">` escapa `</` como `<\/`.
- Nenhum recurso externo: CSS e JS inline; o QC ganha `relatorio_nao_autocontido` (HARD FAIL) para qualquer
  `http://`, `https://` ou `//` em `src`/`href`/`url(`.
- Nenhuma string de interface no código: tudo por chave do dicionário; chave ausente levanta erro nomeado.
- Abas por CSS e um JS inline mínimo, sem biblioteca.

**Testes (`tests/test_relatorio_render.py`):** o HTML de uma entrega válida contém as três abas, o preço
formatado (`61,91` no `caso_reversa_firm`) e o múltiplo de tela; é **byte-idêntico** em duas execuções; não tem
recurso externo; uma prosa com `<script>` sai escapada; toda chave de dicionário usada no código e no template
existe em `pt-BR.json` (varredura por regex das chamadas `t("...")` e dos códigos de QC); um disclosure aparece
no HTML e um QUALITY WARNING **não**. **Prova de falseabilidade:** remova o `html.escape` da conclusão, confirme
vermelho, restaure.

---

## Verificação final da fatia 5A

Uma revisão (opus) da fatia inteira. Material: o relatório decidindo, calculando ou nomeando algo que é da
metodologia; um contrato que deixa passar chave, versão ou correspondência errada; um HARD FAIL que emite; um
número de valuation na prosa sem placeholder. Suíte inteira, fixtures byte a byte, `vendor/` limpo.

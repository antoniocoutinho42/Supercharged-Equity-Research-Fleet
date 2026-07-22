#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checar.py — validações determinísticas do namespace de análise (substitui QC manual).

Etapas:
  --etapa dossie     arquivos do Analista presentes; schema do inputs.yaml (meta+fatos,
                     sem premissas preenchidas indevidamente? premissas podem existir vazias);
                     metodo.yaml presente e válido (R1: julgamento metodológico ANTES da
                     coleta completa).
  --etapa valuation  valuation.md + saida_<TICKER>/resultados.json presentes; chaves
                     obrigatórias no JSON; chaves citadas no valuation.md existem no JSON;
                     engine.versao/hash presentes. BLOQUEIOS (engine v3+): metodo.yaml
                     revisado pelo Modelador (R1); DIVERGE_MATERIAL sem resolução registrada
                     (R5); alerta de sinal contraintuitivo sem resposta (R4).
  --etapa decisao    estado.yaml com bloco decisao completo (pré-requisito do compor.py).
  --etapa relatorio  relatorio.md + log_consistencia.md presentes; nenhum marcador de
                     pendência de composição ({{...}}) sobrou no texto; CORPO do relatório
                     sem linguagem operacional (R6: chaves, hashes, códigos de gate/issue,
                     enums crus, nomes de agente/arquivo) — a trilha técnica vive no
                     "Anexo técnico", que o linter não varre.
  --etapa claims     dossie.md + claims.yaml presentes; claims.yaml válido contra
                     schemas/claims.schema.json; todo ID [F-xx]/[E-xx]/[H-xx] citado no
                     dossie.md tem entrada em claims.yaml e vice-versa (nenhum claim órfão).
  --etapa tudo       todas as anteriores, tolerando ausências opcionais (red_team,
                     portfolio_fit); claims só roda se claims.yaml existir (namespaces
                     anteriores ao sistema de claims recebem AVISO, não reprovação).

Uso: python checar.py <namespace> --etapa <etapa> [--json]
Exit code 0 = aprovado; 1 = reprovado (lista objetiva de faltas).
"""
import importlib.util
import json
import os
import re
import sys

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_VALIDAR_PATH = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "..", "scripts", "validar.py"))
_SCHEMAS_DIR = os.path.normpath(os.path.join(_SCRIPT_DIR, "..", "..", "schemas"))

_ID_CLAIM_RE = re.compile(r"\[([FEH]-\d{2,3})\]")

OBRIG_JSON = [
    "engine.versao", "engine.hash_inputs", "meta.preco_atual", "gate.modo_recomendado",
    "sinais.economico", "sinais.entrada",
    "economico.faixa_ponderada", "economico.central_ponderado", "reverse", "ladder",
    "elasticidades.economico.mais_1a_cap",
]
# hurdle é OPCIONAL desde o engine v3 (R3: exclusivamente informado pelo usuário);
# quando presente no JSON, o ponderado é obrigatório; ausente, sinais.entrada deve
# declarar SEM_HURDLE (degrade limpo, nunca silencioso).
OBRIG_JSON_V3 = ["de_nde", "matrizes", "elasticidades.experimento"]
DECISAO_OBRIG = ["recomendacao", "confianca", "racional"]
# campos do bloco decisao que, quando presentes, DEVEM ser listas YAML:
# string escalar iterada no compor.py vira um item POR CARACTERE no relatório
DECISAO_LISTAS = ["ressalvas", "gatilhos", "plano_acao"]


def _get(d, caminho):
    cur = d
    for parte in caminho.split("."):
        if isinstance(cur, dict) and parte in cur:
            cur = cur[parte]
        else:
            return None
    return cur


def _existe(ns, *nomes):
    return [n for n in nomes if not os.path.exists(os.path.join(ns, n))]


def _carrega_yaml(caminho):
    import yaml
    with open(caminho, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _acha_saida(ns):
    for nome in os.listdir(ns):
        if nome.startswith("saida_") and os.path.isdir(os.path.join(ns, nome)):
            return os.path.join(ns, nome)
    return None


def checar_dossie(ns, faltas, avisos):
    faltas += [f"arquivo ausente: {a}" for a in _existe(ns, "dossie.md", "inputs_valuation.md", "inputs.yaml")]
    # R1: julgamento metodológico prévio, produzido antes/junto da coleta.
    metodo = _carregar_metodo(ns, faltas)
    if metodo:
        pendentes = [d["dado"] for d in metodo.get("dados_adicionais", [])
                     if not d.get("coletado")]
        if pendentes:
            avisos.append("metodo.yaml: dados adicionais do julgamento metodológico ainda "
                          f"não coletados: {pendentes} (devem entrar no plano de coleta)")
    yml = os.path.join(ns, "inputs.yaml")
    if os.path.exists(yml):
        try:
            inp = _carrega_yaml(yml)
        except Exception as exc:
            faltas.append(f"inputs.yaml ilegível: {exc}")
            return
        for k in ("ticker", "preco_atual", "acoes_mi"):
            if _get(inp, f"meta.{k}") is None:
                faltas.append(f"inputs.yaml: meta.{k} ausente")
        for k in ("lpa_ajustado_fy", "lpa_gaap_fy", "divida_liquida_mi", "consenso", "duracao"):
            if _get(inp, f"fatos.{k}") is None:
                faltas.append(f"inputs.yaml: fatos.{k} ausente")
        for k in ("multiplos_historicos", "pares"):
            if _get(inp, f"fatos.{k}") is None:
                avisos.append(f"inputs.yaml: fatos.{k} ausente (validação por múltiplos não rodará)")
        # R2: DE/NDE são inputs estruturais do bracket; sem medição, o engine exigirá
        # exceção declarada do Modelador (motivo + faixa) — avisar já na coleta.
        if _get(inp, "fatos.de") is None or _get(inp, "fatos.nde") is None:
            avisos.append("inputs.yaml: fatos.de/fatos.nde não medidos (dívida bruta/PL e "
                          "dívida líquida/PL): o engine v3 recusará sem "
                          "premissas.excecao_de_nde declarada — meça na fonte (inclusive a "
                          "discriminação de caixa livre quando houver float)")
        # séries anuais que alimentam os gráficos históricos do relatório (H4/H5).
        # Ausência não é falta (gráfico degrada com nota), mas avisa-se para o Analista.
        if _get(inp, "fatos.series_historicas") is None:
            avisos.append("inputs.yaml: fatos.series_historicas ausente "
                          "(gráfico de receita/lucro/ROE não será gerado)")
        if _get(inp, "fatos.multiplos_historicos.pe.serie") is None:
            avisos.append("inputs.yaml: fatos.multiplos_historicos.pe.serie ausente "
                          "(gráfico de P/L histórico com bandas não será gerado)")
        dur = _get(inp, "fatos.duracao") or {}
        if not (_get(dur, "consolidada.persistencia_spread_anos") is not None
                or dur.get("segmentos") or dur.get("persistencia_realizada_anos") is not None):
            faltas.append("inputs.yaml: duracao sem persistência consolidada, segmentos ou legado")


def checar_valuation(ns, faltas, avisos):
    faltas += [f"arquivo ausente: {a}" for a in _existe(ns, "valuation.md")]
    saida = _acha_saida(ns)
    if not saida or not os.path.exists(os.path.join(saida, "resultados.json")):
        faltas.append("saida_<TICKER>/resultados.json ausente")
        return
    res = json.load(open(os.path.join(saida, "resultados.json"), encoding="utf-8"))
    for chave in OBRIG_JSON:
        if _get(res, chave) is None:
            faltas.append(f"resultados.json: chave obrigatória ausente: {chave}")
    if _get(res, "validacao_multiplos") is None:
        avisos.append("resultados.json sem validacao_multiplos (engine < v2? bloco será omitido)")

    # R3: hurdle opcional — presente exige o ponderado; ausente exige degrade declarado.
    if res.get("hurdle") is not None:
        if _get(res, "hurdle.cenarios.ponderado") is None:
            faltas.append("resultados.json: hurdle presente sem hurdle.cenarios.ponderado")
    elif _get(res, "sinais.entrada") != "SEM_HURDLE":
        faltas.append("resultados.json: hurdle ausente sem degrade declarado "
                      "(sinais.entrada deve ser SEM_HURDLE)")

    versao_engine = str(_get(res, "engine.versao") or "0")
    engine_v3 = versao_engine.split(".")[0].isdigit() and int(versao_engine.split(".")[0]) >= 3
    if engine_v3:
        for chave in OBRIG_JSON_V3:
            if _get(res, chave) is None:
                faltas.append(f"resultados.json: chave obrigatória ausente (engine v3+): {chave}")

        # R1: o julgamento metodológico deve ter sido revisitado pelo Modelador
        # com os fatos completos, ANTES do valuation.
        metodo = _carregar_metodo(ns, faltas)
        if metodo is not None:
            rev = metodo.get("revisao_valuation") or {}
            if rev.get("confirmada") is not True:
                faltas.append("metodo.yaml: revisao_valuation.confirmada != true — o Modelador "
                              "deve revisitar o julgamento metodológico com os fatos completos "
                              "ANTES do valuation (R1)")

        # R4: sinal contraintuitivo sem explicação de mecanismo E experimento bloqueia.
        for al in _get(res, "elasticidades.alertas_sinal") or []:
            if not al.get("respondido"):
                faltas.append(
                    f"elasticidades.alertas_sinal: {al.get('ancora')}.{al.get('parametro')} com "
                    f"sinal {al.get('sinal_observado')} (esperado {al.get('sinal_esperado')}) SEM "
                    "resposta do Modelador — explique o mecanismo econômico e a plausibilidade "
                    "do experimento em premissas.respostas_sinais, ou corrija a especificação; "
                    "publicação bloqueada (R4)")

        # R5: divergência material não resolvida bloqueia a publicação.
        if _get(res, "validacao_multiplos.veredicto") == "DIVERGE_MATERIAL":
            if not _get(res, "validacao_multiplos.resolucao"):
                faltas.append(
                    "validacao_multiplos: DIVERGE_MATERIAL sem resolução registrada — o caso "
                    "NÃO avança como ressalva declarada; registre "
                    "premissas.resolucao_divergencia (REVISAO_PREMISSAS | "
                    "EXPLICACAO_FUNDAMENTADA | ADAPTACAO_METODOLOGICA) e re-rode o engine (R5)")

        # v3.1 (B1, 2026-07-21): gating por PRESENÇA — nunca retroativo.
        partes_v = versao_engine.split(".")
        engine_v31 = engine_v3 and len(partes_v) > 1 and partes_v[1].isdigit() and int(partes_v[1]) >= 1
        if engine_v31 and _get(res, "sensibilidade_phi") is None:
            faltas.append("resultados.json: chave obrigatória ausente (engine v3.1+): "
                          "sensibilidade_phi (saída de primeira classe, default φ=0)")
        engine_v32 = engine_v3 and len(partes_v) > 1 and partes_v[1].isdigit() and int(partes_v[1]) >= 2
        if engine_v32 and _get(res, "validacao_multiplos.implicitos") is None:
            faltas.append("resultados.json: chave obrigatória ausente (engine v3.2+): "
                          "validacao_multiplos.implicitos (decomposição do prêmio por driver — R3)")
        if res.get("central_neutro") is not None:
            for sub in ("precos", "robustez_conjunta", "gate_recomputado"):
                if _get(res, f"central_neutro.{sub}") is None:
                    faltas.append(f"resultados.json: central_neutro presente sem {sub}")
        if res.get("ke_dossier") is not None:
            for sub in ("rota_paridade_us", "rota_local", "premio_tamanho", "grade_ke"):
                if _get(res, f"ke_dossier.{sub}") is None:
                    faltas.append(f"resultados.json: ke_dossier presente sem {sub}")
        if res.get("fatos_reformulado") is not None:
            for sub in ("serie", "diagnostico", "gates_aplicabilidade"):
                if _get(res, f"fatos_reformulado.{sub}") is None:
                    faltas.append(f"resultados.json: fatos_reformulado presente sem {sub}")
        if res.get("ebit_justo") is not None:
            for sub in ("cenarios", "paridade", "reverse", "historia_numeros", "bridge"):
                if _get(res, f"ebit_justo.{sub}") is None:
                    faltas.append(f"resultados.json: ebit_justo presente sem {sub} "
                                  "(contrato do bloco operacional — condição 6 inclui "
                                  "historia_numeros)")
            # Condição 3 da aprovação da FASE B: paridade divergente é WARNING com nota de
            # resolução obrigatória no relatório — AVISO aqui, NUNCA falta/bloqueio.
            # Decisão registrada; reavaliar após 3 análises reais.
            if (_get(res, "ebit_justo.paridade.status") == "DIVERGE"
                    and not _get(res, "ebit_justo.paridade.nota_resolucao")):
                avisos.append("ebit_justo.paridade: DIVERGE sem nota_resolucao — declare "
                              "premissas.operacional.nota_paridade (a nota é obrigatória no "
                              "relatório; a divergência em si NÃO bloqueia a publicação — "
                              "condição 3 da aprovação, reavaliar após 3 análises reais)")
    # chaves citadas no valuation.md existem no JSON
    val = open(os.path.join(ns, "valuation.md"), encoding="utf-8").read()
    citadas = set(re.findall(r"`([a-z_]+(?:\.[a-zA-Z0-9_\"\.\[\]\*]+)+)`", val))
    citadas = {c for c in citadas
               if not re.search(r"\.(py|md|yaml|yml|json|png|csv|xlsx|pdf)\b", c)}
    for c in sorted(citadas):
        limpa = re.sub(r"\[.*?\]|\*|\"", "", c).strip(".").replace("..", ".")
        raiz = limpa.split(".")[0]
        if raiz not in res:
            faltas.append(f"valuation.md cita chave inexistente no JSON: `{c}`")
        elif _get(res, limpa) is None and _get(res, ".".join(limpa.split(".")[:2])) is None:
            avisos.append(f"valuation.md: chave não resolvida exatamente (conferir): `{c}`")


def checar_decisao(ns, faltas, avisos):
    est = os.path.join(ns, "estado.yaml")
    if not os.path.exists(est):
        faltas.append("estado.yaml ausente")
        return
    estado = _carrega_yaml(est) or {}
    dec = estado.get("decisao") or {}
    for k in DECISAO_OBRIG:
        if not str(dec.get(k, "")).strip():
            faltas.append(f"estado.yaml: decisao.{k} ausente")
    # R6: a tese é a narrativa causal do corpo do relatório (como a companhia gera
    # valor -> o que sustenta o retorno -> o que o preço embute -> onde está a
    # assimetria -> riscos que invalidam). O racional curto do gate vai para o
    # anexo; sem tese não existe bloco de recomendação institucional.
    if len(str(dec.get("tese", "")).strip()) < 120:
        faltas.append("estado.yaml: decisao.tese ausente ou curta demais (< 120 caracteres) — "
                      "escreva a tese como cadeia causal (geração de valor, vantagens que "
                      "sustentam o retorno, o que o preço embute, assimetria e riscos que a "
                      "invalidam); o racional operacional do gate fica no anexo técnico")
    # R6: os campos da decisão que vão para o CORPO do relatório (tudo menos o
    # racional, que vive no anexo) devem nascer em linguagem institucional — o
    # G7 é a fonte; corrigir aqui evita reprovar só na composição.
    campos_corpo = [("recomendacao", dec.get("recomendacao")), ("tese", dec.get("tese")),
                    ("revisao", dec.get("revisao"))]
    for k in ("ressalvas", "gatilhos", "plano_acao"):
        for i, item in enumerate(dec.get(k) or [] if isinstance(dec.get(k), list) else []):
            campos_corpo.append((f"{k}[{i}]", item))
    for campo, valor in campos_corpo:
        if not valor:
            continue
        for rotulo, padrao in _LINTER_CORPO:
            achados = padrao.findall(str(valor))
            if achados:
                exemplos = sorted(set(str(a) for a in achados))[:3]
                faltas.append(f"estado.yaml: decisao.{campo} com linguagem operacional "
                              f"({rotulo}): {exemplos} — o corpo do relatório é institucional; "
                              f"detalhe operacional vai em decisao.racional (anexo técnico)")
    # campos de lista: string escalar aqui gera item-por-caractere no relatório
    # (bug real de composição); reprovar ANTES do compor.py
    for k in DECISAO_LISTAS:
        v = dec.get(k)
        if v is not None and not isinstance(v, list):
            faltas.append(f"estado.yaml: decisao.{k} deve ser LISTA YAML "
                          f"(recebido {type(v).__name__}); ex.: {k}: [\"item 1\", \"item 2\"] "
                          f"— string escalar quebra a composição (um item por caractere)")
        elif isinstance(v, list) and any(not isinstance(i, (str, int, float)) for i in v):
            avisos.append(f"estado.yaml: decisao.{k} contém itens não textuais (conferir)")
    if estado.get("auditoria", {}).get("acionada") and not os.path.exists(os.path.join(ns, "red_team.md")):
        faltas.append("auditoria acionada mas red_team.md ausente")
    if not str(estado.get("profundidade", "")).upper() in ("SUMARIA", "PADRAO", "REFORCADA"):
        faltas.append("estado.yaml: profundidade ausente ou inválida")


# R6 — linter de linguagem operacional. O CORPO do relatório é um documento
# institucional de investimento; a trilha técnica (chaves, hashes, gates, issues,
# versões) vive exclusivamente no "Anexo técnico". Cada padrão flagra um vazamento
# de linguagem de máquina para o corpo.
_MARCADOR_ANEXO = re.compile(r"^#\s*Anexo t[ée]cnico", re.M | re.I)
_LINTER_CORPO = [
    ("chave de dados inline", re.compile(r"`[a-z_]+(?:\.[a-zA-Z0-9_\"\.\[\]\*]+)+`")),
    ("hash hexadecimal", re.compile(r"\b(?=[0-9a-f]{12,64}\b)[0-9a-f]*[a-f][0-9a-f]*\b")),
    ("código de gate", re.compile(r"\bG\d(?:_\d|\.\d)?\b")),
    ("código de issue de auditoria", re.compile(r"\bAC-\d+\b")),
    ("ID de claim inline", re.compile(r"\[[FEH]-\d{2,3}\]")),
    ("enum cru do engine", re.compile(r"\b[A-Z][A-Z0-9]{2,}(?:_[A-Z0-9]{2,})+\b")),
    ("nome de arquivo/script do workflow", re.compile(
        r"\b(?:resultados\.json|estado\.yaml|inputs\.yaml|claims\.yaml|metodo\.yaml"
        r"|engine\.py|cap_check\.py|compor\.py|checar\.py|snapshot\.py|red_team\.md"
        r"|valuation\.md|dossie\.md)\b")),
    ("versão de engine no corpo", re.compile(r"\bengine\s+v?\d+\.\d+", re.I)),
    ("título operacional (papel de agente)", re.compile(
        r"dossi[êe] do Analista|leitura do Modelador|carimbo do (?:Coordenador|Modelador)", re.I)),
]


def checar_relatorio(ns, faltas, avisos):
    faltas += [f"arquivo ausente: {a}" for a in _existe(ns, "relatorio.md", "log_consistencia.md")]
    rel = os.path.join(ns, "relatorio.md")
    if os.path.exists(rel):
        txt = open(rel, encoding="utf-8").read()
        sobras = re.findall(r"\{\{[^}]+\}\}", txt)
        if sobras:
            faltas.append(f"relatorio.md com marcadores não resolvidos: {sobras[:5]}")
        # separa corpo institucional do anexo técnico
        m = _MARCADOR_ANEXO.search(txt)
        if m:
            corpo = txt[:m.start()]
        else:
            corpo = txt
            avisos.append("relatorio.md sem seção '# Anexo técnico': o linter de linguagem "
                          "operacional varreu o documento inteiro (composições novas devem "
                          "separar corpo institucional e anexo)")
        # o front-matter (entre os dois primeiros '---') é metadado do template, não corpo
        fm = re.match(r"^---\n.*?\n---\n", corpo, re.S)
        if fm:
            corpo = corpo[fm.end():]
        # URLs de fontes são conteúdo institucional legítimo (lista de referências);
        # sem a máscara, slugs hexadecimais de URL virariam falso positivo de hash
        corpo = re.sub(r"https?://\S+", "<url>", corpo)
        for rotulo, padrao in _LINTER_CORPO:
            achados = padrao.findall(corpo)
            if achados:
                exemplos = sorted(set(str(a) for a in achados))[:4]
                faltas.append(f"relatorio.md: linguagem operacional no CORPO ({rotulo}): "
                              f"{exemplos} — mover para o Anexo técnico ou reescrever em "
                              f"linguagem institucional (R6)")


def _carregar_validar_por_path():
    """Importa scripts/validar.py por caminho (não por pacote), mesmo padrão de
    scripts/pipeline.py — funciona de qualquer cwd. Levanta exceção se o arquivo
    não existir ou o import falhar."""
    spec = importlib.util.spec_from_file_location("checar_validar_interno", _VALIDAR_PATH)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


def _validar_contra_schema(caminho, nome_schema):
    """Valida <caminho> contra schemas/<nome_schema>.schema.json.
    Reutiliza scripts/validar.py (mesmo Registry de $ref, mesmas mensagens PT-BR);
    se o import por path falhar por qualquer motivo, cai para uma validação
    inline com jsonschema (mesma lib, sem as mensagens PT-BR customizadas).
    Retorna lista de mensagens de erro (vazia se válido)."""
    try:
        validar_mod = _carregar_validar_por_path()
        if validar_mod.jsonschema is None:
            raise ImportError("jsonschema ausente no módulo validar.py")
        schema, erro = validar_mod._carregar_schema(nome_schema)
        if erro:
            return [erro]
        dados, erro = validar_mod._carregar_documento(caminho)
        if erro:
            return [erro]
        registry = validar_mod._construir_registry()
        validador = validar_mod.jsonschema.Draft202012Validator(schema, registry=registry)
        erros = sorted(
            validador.iter_errors(dados),
            key=lambda e: [str(p) for p in e.absolute_path],
        )
        return [validar_mod._mensagem_pt(e) for e in erros]
    except Exception:
        # Fallback: validação inline (reuso do path preferencial falhou; TENTAMOS
        # primeiro acima, conforme o contrato do brief).
        try:
            import jsonschema
        except ImportError:
            return ["jsonschema ausente: instale (pip install jsonschema) para validar claims.yaml"]
        schema_path = os.path.join(_SCHEMAS_DIR, f"{nome_schema}.schema.json")
        if not os.path.isfile(schema_path):
            return [f"schema ausente: {schema_path}"]
        with open(schema_path, encoding="utf-8") as fh:
            schema = json.load(fh)
        try:
            dados = _carrega_yaml(caminho)
        except Exception as exc:
            return [f"{os.path.basename(caminho)} ilegível: {exc}"]
        validador = jsonschema.Draft202012Validator(schema)
        return [str(e) for e in validador.iter_errors(dados)]


def _validar_claims_schema(caminho):
    return _validar_contra_schema(caminho, "claims")


def _carregar_metodo(ns, faltas):
    """R1: metodo.yaml (julgamento metodológico prévio) presente e válido.
    Devolve o dict (ou None, com as faltas registradas)."""
    caminho = os.path.join(ns, "metodo.yaml")
    if not os.path.exists(caminho):
        faltas.append("metodo.yaml ausente: o julgamento metodológico prévio (R1) é "
                      "obrigatório ANTES da coleta completa e do valuation — o fluxo "
                      "padrão nunca se auto-autoriza")
        return None
    erros = _validar_contra_schema(caminho, "metodo")
    if erros:
        faltas += [f"metodo.yaml: {e}" for e in erros]
        return None
    try:
        return _carrega_yaml(caminho)
    except Exception as exc:
        faltas.append(f"metodo.yaml ilegível: {exc}")
        return None


def checar_claims(ns, faltas, avisos):
    faltantes = _existe(ns, "dossie.md", "claims.yaml")
    if faltantes:
        faltas += [f"arquivo ausente: {a}" for a in faltantes]
        return

    dossie_path = os.path.join(ns, "dossie.md")
    claims_path = os.path.join(ns, "claims.yaml")

    erros_schema = _validar_claims_schema(claims_path)
    if erros_schema:
        faltas += [f"claims.yaml: {e}" for e in erros_schema]
        return  # schema inválido: cross-check de IDs não é confiável

    try:
        claims_doc = _carrega_yaml(claims_path)
    except Exception as exc:
        faltas.append(f"claims.yaml ilegível: {exc}")
        return
    lista = (claims_doc or {}).get("claims") or []
    ids_yaml = {c["id"] for c in lista if isinstance(c, dict) and c.get("id")}

    texto = open(dossie_path, encoding="utf-8").read()
    ids_citados = set(_ID_CLAIM_RE.findall(texto))

    orfaos = sorted(ids_yaml - ids_citados)
    sem_entrada = sorted(ids_citados - ids_yaml)
    if orfaos:
        faltas.append(
            f"claims.yaml: {len(orfaos)} claim(s) sem citação em dossie.md: {orfaos}"
        )
    if sem_entrada:
        faltas.append(
            f"dossie.md: {len(sem_entrada)} ID(s) citado(s) sem entrada em claims.yaml: {sem_entrada}"
        )


def main():
    ns = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
    etapa = "tudo"
    if "--etapa" in sys.argv:
        etapa = sys.argv[sys.argv.index("--etapa") + 1]
    faltas, avisos = [], []
    passos = {"dossie": checar_dossie, "valuation": checar_valuation,
              "decisao": checar_decisao, "relatorio": checar_relatorio,
              "claims": checar_claims}
    if etapa == "tudo":
        for nome, fn in passos.items():
            if nome == "claims":
                continue
            fn(ns, faltas, avisos)
        # claims.yaml é opcional em "tudo" (compat com namespaces anteriores ao
        # sistema de claims): sem o arquivo, AVISO em vez de reprovação.
        if os.path.exists(os.path.join(ns, "claims.yaml")):
            checar_claims(ns, faltas, avisos)
        else:
            avisos.append(
                "claims.yaml ausente: etapa claims não rodou "
                "(namespace anterior ao sistema de claims; rode --etapa claims após criá-lo)"
            )
    elif etapa in passos:
        passos[etapa](ns, faltas, avisos)
    else:
        sys.exit(f"etapa desconhecida: {etapa}")
    saida = {"etapa": etapa, "status": "APROVADO" if not faltas else "REPROVADO",
             "faltas": faltas, "avisos": avisos}
    if "--json" in sys.argv:
        print(json.dumps(saida, ensure_ascii=False, indent=2))
    else:
        print(f"[checar --etapa {etapa}] {saida['status']}")
        for f in faltas:
            print("  FALTA:", f)
        for a in avisos:
            print("  aviso:", a)
    sys.exit(0 if not faltas else 1)


if __name__ == "__main__":
    main()

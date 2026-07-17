# -*- coding: utf-8 -*-
"""Testes de schemas/*.schema.json + scripts/validar.py (Task 1.2).

Importa scripts/validar.py dinamicamente via importlib (mesmo padrão de
tests/test_snapshot.py) e chama validar.main(argv) diretamente, capturando
stdout/stderr via capsys — evita subprocess.

Para cada schema: pelo menos 1 caso válido e 1 caso inválido. Casos
obrigatórios do brief (task-1.2-brief.md) marcados nos nomes dos testes.
"""
import importlib.util
import json
import os

import pytest
import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VALIDAR_PATH = os.path.join(REPO_ROOT, "scripts", "validar.py")


def _carregar_validar():
    spec = importlib.util.spec_from_file_location("validar", VALIDAR_PATH)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


validar = _carregar_validar()


def _escreve_yaml(tmp_path, nome, dados):
    caminho = tmp_path / nome
    caminho.write_text(yaml.safe_dump(dados, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return caminho


def _escreve_json(tmp_path, nome, dados):
    caminho = tmp_path / nome
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    return caminho


# ---------------------------------------------------------------------------
# decisao.schema.json
# ---------------------------------------------------------------------------

def _decisao_fnv_real():
    """Valores reais da sessão FNV (P2), conforme resumo do brief."""
    return {
        "recomendacao": "WATCHLIST (PRÓXIMA) — NÃO COMPRAR AGORA",
        "confianca": "MEDIA",
        "racional": (
            "P2 corrigiu a mecanica de valor terminal do P/L Justo (engine v2.2.0, "
            "m_terminal calibrado no P/B implicito historico REALIZADO da propria FNV). "
            "Hurdle permanece NAO_ACIONAVEL; robustez DIVERGENTE (AC-04) bloqueia compra."
        ),
        "tese": "Franco-Nevada e um dos negocios de maior qualidade estrutural do setor.",
        "ressalvas": [
            "CRITICA AC-04 do Auditor (aberta): sinal DENTRO_DA_FAIXA nao e robusto a "
            "ancoragem alternativa de M (pares).",
            "Preco Maximo para o Hurdle (US$116,46) permanece a ancora mais conservadora.",
        ],
        "gatilhos": [
            "Resolucao qualitativa da CRITICA AC-04.",
            "Preco abaixo de ~US$116-124 (Preco Maximo para o Hurdle).",
        ],
        "plano_acao": [
            "Monitorar trimestralmente o preco contra as duas ancoras atualizadas.",
            "Se autorizado, encomendar investigacao qualitativa dedicada da CRITICA AC-04.",
        ],
        "revisao": "Apos a audiencia da arbitragem Panama-First Quantum prevista para 2026.",
    }


def test_decisao_fnv_real_valida(tmp_path, capsys):
    """(b) decisao real da FNV APROVA."""
    caminho = _escreve_yaml(tmp_path, "decisao.yaml", _decisao_fnv_real())
    codigo = validar.main([str(caminho), "--schema", "decisao"])
    saida = capsys.readouterr()
    assert codigo == 0
    assert "VALIDO" in saida.out


def test_decisao_ressalvas_string_escalar_reprova(tmp_path, capsys):
    """(a) REGRA CRÍTICA: ressalvas como string escalar (não lista) DEVE reprovar
    — é o bug real que quebra a composição (um item por caractere)."""
    dados = _decisao_fnv_real()
    dados["ressalvas"] = "texto escalar"
    caminho = _escreve_yaml(tmp_path, "decisao.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "decisao"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert (saida.out + saida.err).strip() != ""


def test_decisao_gatilhos_string_escalar_reprova(tmp_path, capsys):
    """Mesma regra crítica também vale para gatilhos e plano_acao."""
    dados = _decisao_fnv_real()
    dados["gatilhos"] = "um gatilho so, sem lista"
    caminho = _escreve_yaml(tmp_path, "decisao.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "decisao"])
    assert codigo == 1


def test_decisao_sem_confianca_reprova(tmp_path, capsys):
    dados = _decisao_fnv_real()
    del dados["confianca"]
    caminho = _escreve_yaml(tmp_path, "decisao.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "decisao"])
    assert codigo == 1


def test_decisao_confianca_enum_invalido_reprova(tmp_path, capsys):
    dados = _decisao_fnv_real()
    dados["confianca"] = "SUPER_ALTA"
    caminho = _escreve_yaml(tmp_path, "decisao.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "decisao"])
    assert codigo == 1


# ---------------------------------------------------------------------------
# estado.schema.json
# ---------------------------------------------------------------------------

def _estado_minimo_valido():
    gates = {g: "PENDENTE" for g in
             ("G1", "G1_5", "G2", "G3_0", "G3", "G4", "G5", "G6", "G7", "G8")}
    return {
        "ticker": "FNV",
        "data": "2026-07-15",
        "profundidade": "PADRAO",
        "modo": "PARCIAL",
        "snapshot": False,
        "engine": {"versao": "", "hash": "0000000000000000"},
        "gates": gates,
    }


def test_estado_minimo_valido(tmp_path, capsys):
    caminho = _escreve_yaml(tmp_path, "estado.yaml", _estado_minimo_valido())
    codigo = validar.main([str(caminho), "--schema", "estado"])
    saida = capsys.readouterr()
    assert codigo == 0
    assert "VALIDO" in saida.out


def test_estado_gate_texto_narrativo_reprova(tmp_path, capsys):
    """(d) gate G3 com texto longo narrativo (não é enum) DEVE reprovar."""
    dados = _estado_minimo_valido()
    dados["gates"]["G3"] = (
        "Valuation rodado (engine v2.1.0, hash 645c29f56421903f). Gate G3.0 = "
        "SUMARIA (preco/teto_bull_econ=2.12 >= 1.4)."
    )
    caminho = _escreve_yaml(tmp_path, "estado.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "estado"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert (saida.out + saida.err).strip() != ""


def test_estado_ticker_invalido_reprova(tmp_path, capsys):
    dados = _estado_minimo_valido()
    dados["ticker"] = "franco-nevada corp"
    caminho = _escreve_yaml(tmp_path, "estado.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "estado"])
    assert codigo == 1


def test_estado_com_decisao_valida_via_ref(tmp_path, capsys):
    """estado.yaml com bloco decisao embutido válido (exercita o $ref entre schemas)."""
    dados = _estado_minimo_valido()
    dados["decisao"] = _decisao_fnv_real()
    dados["auditoria"] = {"acionada": True, "agregado": "DEMONSTRADA_COM_RESSALVAS"}
    dados["pendencias"] = [
        {"id": "P1", "texto": "Reconstruir ROIC pre-2021.", "dono": "Analista"},
    ]
    caminho = _escreve_yaml(tmp_path, "estado.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "estado"])
    saida = capsys.readouterr()
    assert codigo == 0, saida.err


def test_estado_com_decisao_invalida_via_ref_reprova(tmp_path, capsys):
    """$ref precisa propagar erro do decisao.schema para dentro do estado."""
    dados = _estado_minimo_valido()
    dec = _decisao_fnv_real()
    dec["ressalvas"] = "texto escalar"
    dados["decisao"] = dec
    caminho = _escreve_yaml(tmp_path, "estado.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "estado"])
    assert codigo == 1


# ---------------------------------------------------------------------------
# handoff.schema.json
# ---------------------------------------------------------------------------

def _handoff_valido():
    return {
        "gate": "G3",
        "de": "Modelador",
        "para": "Coordenador",
        "insumos": ["inputs.yaml", "dossie.md"],
        "entregaveis": ["valuation.md", "saida_FNV/resultados.json"],
        "foco": "Rodar o engine e reportar hurdle/economico com CAP justificado.",
        "status": "ENTREGUE",
        "restricoes": ["Não alterar inputs.yaml após rodar o engine."],
        "resposta": "Engine rodado (hash 34e6680992b5b76e); hurdle 116,46; economico 188,49.",
    }


def test_handoff_valido(tmp_path, capsys):
    caminho = _escreve_yaml(tmp_path, "handoff.yaml", _handoff_valido())
    codigo = validar.main([str(caminho), "--schema", "handoff"])
    saida = capsys.readouterr()
    assert codigo == 0
    assert "VALIDO" in saida.out


def test_handoff_status_enum_invalido_reprova(tmp_path, capsys):
    dados = _handoff_valido()
    dados["status"] = "FEITO"
    caminho = _escreve_yaml(tmp_path, "handoff.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "handoff"])
    assert codigo == 1


def test_handoff_sem_foco_reprova(tmp_path, capsys):
    dados = _handoff_valido()
    del dados["foco"]
    caminho = _escreve_yaml(tmp_path, "handoff.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "handoff"])
    assert codigo == 1


def test_handoff_gate_enum_invalido_reprova(tmp_path, capsys):
    dados = _handoff_valido()
    dados["gate"] = "G9"
    caminho = _escreve_yaml(tmp_path, "handoff.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "handoff"])
    assert codigo == 1


# ---------------------------------------------------------------------------
# claims.schema.json
# ---------------------------------------------------------------------------

def test_claims_validas(tmp_path, capsys):
    dados = {
        "claims": [
            {"id": "F-01", "tipo": "FATO", "texto": "Divida liquida zero em 2025.",
             "fonte": "10-K 2025, p. 42", "data": "2026-01-01", "pilar": 3},
            {"id": "E-01", "tipo": "ESTIMATIVA", "texto": "ROE 2026E ~13%."},
            {"id": "H-01", "tipo": "HIPOTESE", "texto": "Premio sobre pares e estrutural."},
        ]
    }
    caminho = _escreve_yaml(tmp_path, "claims.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "claims"])
    saida = capsys.readouterr()
    assert codigo == 0
    assert "VALIDO" in saida.out


def test_claims_fato_sem_fonte_reprova(tmp_path, capsys):
    """(e) claim FATO sem fonte DEVE reprovar."""
    dados = {
        "claims": [
            {"id": "F-02", "tipo": "FATO", "texto": "Impairment de US$1.169,2mi em Panama.",
             "data": "2026-01-01"},
        ]
    }
    caminho = _escreve_yaml(tmp_path, "claims.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "claims"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert (saida.out + saida.err).strip() != ""


def test_claims_fato_sem_data_reprova(tmp_path, capsys):
    dados = {
        "claims": [
            {"id": "F-03", "tipo": "FATO", "texto": "Zero divida.", "fonte": "10-K 2025"},
        ]
    }
    caminho = _escreve_yaml(tmp_path, "claims.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "claims"])
    assert codigo == 1


def test_claims_id_pattern_invalido_reprova(tmp_path, capsys):
    dados = {"claims": [{"id": "X-01", "tipo": "HIPOTESE", "texto": "id com prefixo errado"}]}
    caminho = _escreve_yaml(tmp_path, "claims.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "claims"])
    assert codigo == 1


def test_claims_pilar_fora_de_faixa_reprova(tmp_path, capsys):
    dados = {"claims": [{"id": "H-02", "tipo": "HIPOTESE", "texto": "pilar invalido", "pilar": 9}]}
    caminho = _escreve_yaml(tmp_path, "claims.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "claims"])
    assert codigo == 1


# ---------------------------------------------------------------------------
# red_team_header.schema.json
# ---------------------------------------------------------------------------

def _red_team_header_fnv_real():
    """(c) Cabeçalho real da sessão FNV: agregado DEMONSTRADA_COM_RESSALVAS,
    5 issues AC-01..AC-05, robustez divergente."""
    return {
        "agregado": "DEMONSTRADA_COM_RESSALVAS",
        "dimensoes": {
            "integridade": "verificada",
            "correcao": "verificada",
            "especificacao": "aceitavel",
            "robustez": "divergente",
        },
        "issues": [
            {"id": "AC-01", "severidade": "CRITICA", "estado": "fechada",
             "titulo": "Sinal SOBREAVALIADO nao sobrevivia a tratamento terminal alternativo defensavel",
             "enderecada_a": "Modelador/Coordenador"},
            {"id": "AC-02", "severidade": "RELEVANTE", "estado": "fechada",
             "titulo": "Extensao pura de CAP e fade pos-CAP nao reconciliam sozinhos os multiplos",
             "enderecada_a": "Modelador"},
            {"id": "AC-03", "severidade": "RELEVANTE", "estado": "fechada",
             "titulo": "Reducao de Ke so no desconto do terminal exige Ke abaixo do risk-free",
             "enderecada_a": "Modelador"},
            {"id": "AC-04", "severidade": "CRITICA", "estado": "aberta",
             "titulo": "Sinal DENTRO_DA_FAIXA depende de ancorar M no P/B historico proprio da FNV",
             "enderecada_a": "Modelador/Coordenador"},
            {"id": "AC-05", "severidade": "MENOR", "estado": "fechada",
             "titulo": "Golden suite tem 6 novas asercoes, nao 11 como reportado em valuation.md",
             "enderecada_a": "Modelador"},
        ],
        "cap_auditoria": (
            "CAP consolidado confirmado sem alertas; banda sugerida pelo cap_check "
            "(excepcional 18-25) e mais generosa que o CAP efetivamente usado."
        ),
        "confianca": "media",
    }


def test_red_team_header_fnv_real_valido(tmp_path, capsys):
    caminho = _escreve_yaml(tmp_path, "red_team_header.yaml", _red_team_header_fnv_real())
    codigo = validar.main([str(caminho), "--schema", "red_team_header"])
    saida = capsys.readouterr()
    assert codigo == 0, saida.err
    assert "VALIDO" in saida.out


def test_red_team_header_robustez_enum_invalido_reprova(tmp_path, capsys):
    dados = _red_team_header_fnv_real()
    dados["dimensoes"]["robustez"] = "TALVEZ"
    caminho = _escreve_yaml(tmp_path, "red_team_header.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "red_team_header"])
    assert codigo == 1


def test_red_team_header_issue_id_pattern_invalido_reprova(tmp_path, capsys):
    dados = _red_team_header_fnv_real()
    dados["issues"][0]["id"] = "ISSUE-01"
    caminho = _escreve_yaml(tmp_path, "red_team_header.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "red_team_header"])
    assert codigo == 1


def test_red_team_header_sem_confianca_reprova(tmp_path, capsys):
    dados = _red_team_header_fnv_real()
    del dados["confianca"]
    caminho = _escreve_yaml(tmp_path, "red_team_header.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "red_team_header"])
    assert codigo == 1


# ---------------------------------------------------------------------------
# (f) extração de front-matter de .md (caso red_team.md real)
# ---------------------------------------------------------------------------

def test_validar_extrai_front_matter_de_md(tmp_path, capsys):
    cabecalho = yaml.safe_dump(_red_team_header_fnv_real(), allow_unicode=True, sort_keys=False)
    texto = (
        "---\n"
        f"{cabecalho}"
        "---\n\n"
        "## ADENDO (revalidacao G5, patch engine v2.2.0, m_terminal)\n\n"
        "Corpo do red_team.md, texto narrativo longo que NÃO deve ser YAML-parseado...\n"
    )
    caminho = tmp_path / "red_team.md"
    caminho.write_text(texto, encoding="utf-8")

    codigo = validar.main([str(caminho), "--schema", "red_team_header"])
    saida = capsys.readouterr()
    assert codigo == 0, saida.err
    assert "VALIDO" in saida.out


def test_validar_md_sem_front_matter_reprova(tmp_path, capsys):
    caminho = tmp_path / "sem_front_matter.md"
    caminho.write_text("# Apenas um título\n\nSem bloco YAML.\n", encoding="utf-8")
    codigo = validar.main([str(caminho), "--schema", "red_team_header"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert (saida.out + saida.err).strip() != ""


# ---------------------------------------------------------------------------
# Erros de ambiente / uso (arquivo ausente, extensão não suportada)
# ---------------------------------------------------------------------------

def test_validar_arquivo_ausente_reprova(tmp_path, capsys):
    caminho = tmp_path / "nao_existe.yaml"
    codigo = validar.main([str(caminho), "--schema", "decisao"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert (saida.out + saida.err).strip() != ""


def test_validar_claims_json_tambem_funciona(tmp_path, capsys):
    """Suporta .json além de .yaml/.yml."""
    dados = {"claims": [{"id": "E-02", "tipo": "ESTIMATIVA", "texto": "estimativa em JSON"}]}
    caminho = _escreve_json(tmp_path, "claims.json", dados)
    codigo = validar.main([str(caminho), "--schema", "claims"])
    saida = capsys.readouterr()
    assert codigo == 0, saida.err


# ---------------------------------------------------------------------------
# Mensagens de erro em PT-BR (Fix 1: brief exige saída PT-BR)
# ---------------------------------------------------------------------------

def test_erro_required_em_pt_br(tmp_path, capsys):
    """required -> 'campo obrigatório ausente: <prop>', com o caminho JSON."""
    dados = _decisao_fnv_real()
    del dados["confianca"]
    caminho = _escreve_yaml(tmp_path, "decisao.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "decisao"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert "campo obrigatório ausente" in saida.err
    assert "confianca" in saida.err


def test_erro_enum_em_pt_br(tmp_path, capsys):
    """enum -> 'valor inválido; permitidos: ...'."""
    dados = _decisao_fnv_real()
    dados["confianca"] = "SUPER_ALTA"
    caminho = _escreve_yaml(tmp_path, "decisao.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "decisao"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert "valor inválido" in saida.err
    assert "permitidos" in saida.err
    assert "confianca" in saida.err


def test_erro_type_em_pt_br(tmp_path, capsys):
    """type -> 'esperado <tipo>, recebido <tipo>' (a regra crítica das listas)."""
    dados = _decisao_fnv_real()
    dados["ressalvas"] = "texto escalar"
    caminho = _escreve_yaml(tmp_path, "decisao.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "decisao"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert "ressalvas" in saida.err
    assert "esperado lista" in saida.err
    assert "recebido texto" in saida.err


def test_erro_additional_properties_em_pt_br(tmp_path, capsys):
    """additionalProperties -> 'campo não permitido: <prop>'."""
    dados = _decisao_fnv_real()
    dados["campo_intruso"] = "não deveria existir"
    caminho = _escreve_yaml(tmp_path, "decisao.yaml", dados)
    codigo = validar.main([str(caminho), "--schema", "decisao"])
    saida = capsys.readouterr()
    assert codigo == 1
    assert "campo não permitido" in saida.err
    assert "campo_intruso" in saida.err

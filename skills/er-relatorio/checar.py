#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
checar.py — validações determinísticas do namespace de análise (substitui QC manual).

Etapas:
  --etapa dossie     arquivos do Analista presentes; schema do inputs.yaml (meta+fatos,
                     sem premissas preenchidas indevidamente? premissas podem existir vazias);
  --etapa valuation  valuation.md + saida_<TICKER>/resultados.json presentes; chaves
                     obrigatórias no JSON; chaves citadas no valuation.md existem no JSON;
                     engine.versao/hash presentes.
  --etapa decisao    estado.yaml com bloco decisao completo (pré-requisito do compor.py).
  --etapa relatorio  relatorio.md + log_consistencia.md presentes; nenhum marcador de
                     pendência de composição ({{...}}) sobrou no texto.
  --etapa tudo       todas as anteriores, tolerando ausências opcionais (red_team, portfolio_fit).

Uso: python checar.py <namespace> --etapa <etapa> [--json]
Exit code 0 = aprovado; 1 = reprovado (lista objetiva de faltas).
"""
import json
import os
import re
import sys

OBRIG_JSON = [
    "engine.versao", "engine.hash_inputs", "meta.preco_atual", "gate.modo_recomendado",
    "sinais.economico", "sinais.entrada", "hurdle.cenarios.ponderado",
    "economico.faixa_ponderada", "economico.central_ponderado", "reverse", "ladder",
    "elasticidades.economico.mais_1a_cap",
]
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


def checar_relatorio(ns, faltas, avisos):
    faltas += [f"arquivo ausente: {a}" for a in _existe(ns, "relatorio.md", "log_consistencia.md")]
    rel = os.path.join(ns, "relatorio.md")
    if os.path.exists(rel):
        txt = open(rel, encoding="utf-8").read()
        sobras = re.findall(r"\{\{[^}]+\}\}", txt)
        if sobras:
            faltas.append(f"relatorio.md com marcadores não resolvidos: {sobras[:5]}")


def main():
    ns = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "."
    etapa = "tudo"
    if "--etapa" in sys.argv:
        etapa = sys.argv[sys.argv.index("--etapa") + 1]
    faltas, avisos = [], []
    passos = {"dossie": checar_dossie, "valuation": checar_valuation,
              "decisao": checar_decisao, "relatorio": checar_relatorio}
    if etapa == "tudo":
        for fn in passos.values():
            fn(ns, faltas, avisos)
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

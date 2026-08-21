---
name: er-multiplos-justos
description: USE QUANDO precisar da metodologia canônica de valuation do fleet — localizar o arquivo certo do pacote congelado, rodar o motor ou a suíte, ou confirmar a integridade da cópia. É um índice do vendor congelado, não a metodologia. NÃO use para montar o caso de valuation (er-valuation), coletar evidência (er-evidencia), compor relatório (er-relatorio) ou conduzir a análise (er-analise).
---

# er-multiplos-justos — índice do vendor congelado

Este arquivo **não contém metodologia**. A metodologia canônica é a skill `multiplos-justos`
v9.24, copiada byte a byte. Ela vive em `vendor/multiplos-justos/` na raiz do repositório, **fora
de `skills/`**: o pacote declara `name: multiplos-justos` no próprio frontmatter do `SKILL.md` e,
se ficasse sob `skills/`, estaria sujeito a ser descoberto como skill, colidindo com a skill
standalone do usuário. A cópia é verificada por sha256 em `manifest_vendor.json`. Regra do desenho
v4: **índice, nunca paráfrase** — resumir a metodologia aqui cria uma segunda fonte que envelhece
mal. Leia o arquivo do vendor.

## Mapa do pacote — o que ler, e quando

| Arquivo (caminho a partir da raiz do repositório) | O que é | Quando ler |
|---|---|---|
| `vendor/multiplos-justos/SKILL.md` | Núcleo: identidade central, os cinco gates, convenções do motor, catálogo de comandos, estrutura da entrega, diagnósticos obrigatórios | Sempre, antes de qualquer valuation |
| `vendor/multiplos-justos/references/aplicacao.md` | Playbook de empresa real: pesquisa, regras travadas de derivação de premissas, convenção terminal, grade de cenários e reversa, degrau e capacidade, financeiras, memória de cálculo, multi-segmento, jurisprudência | **Na íntegra**, antes de valuation de companhia real. O próprio pacote exige |
| `vendor/multiplos-justos/references/derivacao.md` | Matemática e provas: convenções de valor terminal, APV e recursão, teorema da classificação, ponte de releveraging | Quando a teoria for questionada, ou houver degrau ou mudança de estrutura de capital |
| `vendor/multiplos-justos/references/paper-multiplos-justos-v3.md` | Fundamentação: proposições com estatuto epistemológico declarado, protocolo de validação, condições de falseamento, caso trabalhado | Ao defender por escrito uma escolha de convenção |
| `vendor/multiplos-justos/scripts/justos.py` | O motor. Saída JSON, stdlib pura | Toda conta de valuation passa por aqui |
| `vendor/multiplos-justos/scripts/testes.py` | Suíte independente: property tests, reconciliações, boundaries, lint de portabilidade e lint semântico dos docs | Antes de entregar; e sempre que um resultado parecer estranho |
| `vendor/multiplos-justos/CHANGELOG.md` | Linhagem das versões e a origem de cada regra | Ao investigar por que uma regra existe |

## Como rodar

```bash
python vendor/multiplos-justos/scripts/justos.py selftest
python vendor/multiplos-justos/scripts/testes.py
```

O catálogo de comandos do motor está no `SKILL.md` do vendor — não é reproduzido aqui. Nenhuma
conta de valuation é feita fora do motor: sem prosa, sem planilha, sem Python novo, sem JS novo
(regra inviolável 1 do desenho v4).

## Integridade da cópia

`manifest_vendor.json` registra versão, origem e o sha256 de cada um dos 7 arquivos.
`tests/test_vendor_multiplos_justos.py` confronta manifest e disco **nos dois sentidos** — arquivo
alterado e arquivo a mais reprovam igualmente — e roda a suíte do vendor.

A própria suíte do pacote reconfere o motor e os números ancorados nos docs a cada execução; o
texto livre da metodologia não passa por essa reconferência e fica coberto só pelo sha256 acima.
**O vendor é read-only.** Evoluir a metodologia é decisão humana explícita — substituir o pacote
inteiro, regenerar o manifest, rodar a suíte.

## Fronteira

A skill de usuário `multiplos-justos` permanece intocada fora deste repositório e continua
acionável só por `/multiplos-justos`. Aqui ela é biblioteca, não skill acionável: o gatilho de
análise é do `er-analise`. O `SKILL.md` do vendor declara `name: multiplos-justos`; por isso o
pacote inteiro vive fora de `skills/`, onde nenhuma profundidade de varredura o alcança —
invariante travada em
`tests/test_vendor_multiplos_justos.py::test_pacote_vendorizado_vive_fora_de_skills` e em
`tests/test_vendor_multiplos_justos.py::test_nenhum_skill_md_aninhado_sob_skills`.

Referência de desenho: `docs/desenho-arquitetura-v4.md`, Seções 3.2, 4 e 18.

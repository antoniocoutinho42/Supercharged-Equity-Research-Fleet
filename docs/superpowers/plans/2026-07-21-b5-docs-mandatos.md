# B5 — SKILL, mandatos, CHANGELOG, versão do plugin

> superpowers:executing-plans (inline). Última fase antes do gate de merge único (B1–B5).
> Restrições verificadas: mandatos ≤4096 bytes (folga 1,1–1,4KB); test_agents exige âncoras
> textuais existentes (só ADIÇÕES); "franchise-fade" sem âncora em teste; golden VRSK não pina
> o hash do exemplo canônico; er-valuation/SKILL.md sem orçamento de palavras testado.

### Task 1: SKILL.md er-valuation (+ engine docstrings + exemplo)
Título v2→v3; nomenclatura "franchise-fade" → "spread constante até o CAP, terminal modulável"
(SKILL l.21 + engine.py l.11/l.179 — docstring, zero mudança de comportamento); NOVA seção
"Blocos v3.1/v3.2" na tabela e no fluxo: fatos.reformulado+gates H7 (**PROVISÓRIOS n=3 com
instrução de recalibração — condição 7**), ebit_justo (trailing; paridade **WARNING com
nota_paridade obrigatória; NÃO bloqueia; reavaliar após 3 análises — condição 3**),
central_neutro, ke_dossier, implicitos, **m_terminal × φ EXCLUSÃO MÚTUA (aceite duro)**,
norma_contabil/leasing_pacote, camadas de imposto; rótulo do `inputs_exemplo_vrsk.yaml` v2→v3.
- [ ] Editar → suíte verde → commit.

### Task 2: Mandatos (adições cirúrgicas, ≤4096 bytes)
- analista.md §4: série reformulada com invariantes (base MÉDIA/inicial; EoP proibido), ledger
  `classificacao.yaml` por natureza (critérios em references/classificacao.md; ambíguas
  flagadas), detecção de norma contábil + pacote de leasing travado.
- modelador.md §3: cenários operacionais margem×giro quando a âncora operacional roda; dossiê
  de Ke com DUAS rotas + prêmio de tamanho com critério; caso central neutro; responder o
  ônus-para-baixo do cap_check; exclusão mútua m_terminal×φ; paridade divergente exige nota.
- auditor.md §3: recomputo da ponte da série reformulada, da paridade das âncoras e dos gates
  de aplicabilidade; contraditório das linhas ambíguas do ledger.
- [ ] Editar → `test_agents` verde (bytes + âncoras) → commit.

### Task 3: README + plugin 2.1.0 + teste de aceite duro
README: seção v2.1.0 (engine v3.2.0, aditivo, gating por presença). plugin.json 2.0.0→2.1.0.
`tests/test_b5_docs.py` (ACEITE DURO da aprovação): SKILL contém m_terminal + exclusão mútua +
PROVISÓRIO/recalibração + paridade-não-bloqueia; "franchise-fade" AUSENTE de SKILL e engine;
título v3; mandatos citam os blocos novos; plugin.json 2.1.0; README cita v3.2.0.
- [ ] RED → editar → GREEN (suíte inteira) → commit.

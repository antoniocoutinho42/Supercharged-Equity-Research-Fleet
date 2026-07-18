# Smoke test no Cowork (~15 minutos por release)

Checklist executável para rodar a cada release (antes de marcar a tag e
depois de qualquer mudança em `skills/*/SKILL.md`, `scripts/` ou
`.claude-plugin/plugin.json`). Não é teste de qualidade analítica — é
encanamento: confirma que o plugin instala e que os componentes básicos
respondem no ambiente real. Registrar cada item em `docs/plataforma.md`
(seção "Registro de smokes").

## 1. Instalação (~3 min)

- Adicionar o repo como marketplace no Cowork: Customize > Plugins > Add
  marketplace `<owner>/<repo>` — OU fazer upload do ZIP da release (gerado
  pelo workflow de release, ver `docs/fontes` / CI).
- Confirmar que skills, agents e comandos do plugin aparecem listados na
  tela do plugin instalado (não só "instalado com sucesso" — abrir a lista e
  contar: 9 skills de domínio, agents descartáveis do template de despacho).
- Registrar divergência se o marketplace ou o ZIP falharem, ou se algum
  componente não aparecer na lista.

## 2. Ativação mínima (~3 min)

Rodar, numa sessão Cowork **nova**, 3 cenários de `docs/testes-ativacao.md`:

- 1 GREEN de pipeline completo (ex.: "Analisa a Vale para mim" → er-processo).
- 1 GREEN de skill isolada (ex.: "Roda o valuation da VRSK com essas
  premissas" → er-valuation).
- 1 RED (ex.: "O que é P/L?" → nenhuma skill do fleet).

Registrar resultado (disparou/não disparou a skill certa) da mesma forma que
a tabela de `testes-ativacao.md`.

## 3. Sandbox (~2 min)

- Pedir, na mesma sessão: "rode `python scripts/pipeline.py --help` do
  plugin".
- Confirmar que o script executa dentro do sandbox do Cowork (não erro de
  path, não erro de Python ausente).
- Conferir os paths reais usados pelo sandbox: `/tmp/analise` (namespace de
  trabalho) e `/mnt/memory` (se disponível, para `memoria/<TICKER>.md`).
  Registrar em `docs/plataforma.md` qualquer divergência entre o path
  documentado nas skills (`er-memoria`, `er-relatorio`) e o path real
  observado.

## 4. Fluxo mini-P1 sintético (~5 min)

Pedir um P1 profundidade SUMÁRIA de um ticker com dados fornecidos **inline
na mensagem** (usar o exemplo VRSK do `er-valuation`, dizendo explicitamente
para não pesquisar na web — o objetivo é testar o encanamento, não a
qualidade da pesquisa). Verificar, na ordem:

1. `pipeline init` cria o namespace.
2. G1 (guardrails) roda e carimba profundidade.
3. O engine de valuation roda (`engine.py` produz `resultados.json`).
4. `snapshot.py` cria um run imutável em `runs/<hash8>/`.
5. `estado.yaml` final é válido contra o schema (`validar.py --schema estado`
   passaria, se rodado).

Isso NÃO é teste de qualidade analítica (não julgar se o dossiê ou o
valuation "fazem sentido" como research) — é confirmar que a máquina de
estados e os scripts determinísticos rodam ponta a ponta dentro do sandbox
real do Cowork, fora do ambiente de CI.

## 5. Subagentes (~1 min)

- Confirmar que o Coordenador despacha ao menos 1 **subagente** do plugin
  (analista ou modelador) durante o mini-P1 do item 4 — não basta o
  Coordenador simular o papel na própria thread.
- Confirmar que `handoff.yaml` aparece no namespace da análise após o
  despacho (template de despacho da Task 2.3).

## 6. Chat (degradação) (~1 min)

Numa sessão de **chat** do claude.ai (não Cowork, sem fleet multiagente):

- Confirmar que as skills do plugin aparecem disponíveis (skills funcionam
  em chat; subagentes e hooks não).
- Confirmar que `er-processo` declara explicitamente o modo chat no primeiro
  turno ("estou operando sem subagentes..."), conforme
  `skills/er-processo/references/chat-mode.md`.

## 7. Registro

Cada item (1 a 6) vira uma linha em `docs/plataforma.md`, seção "Registro de
smokes": data, versão do plugin (`.claude-plugin/plugin.json`), resultado
(passou/falhou por item), e link/número da issue aberta se algum item
falhou. Um smoke só é "limpo" se os 6 itens passarem na mesma execução;
falha parcial não bloqueia a release por si só, mas precisa de issue aberta
e decisão explícita do responsável antes de publicar.

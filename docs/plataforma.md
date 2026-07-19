# Estado da plataforma (Cowork/claude.ai) para o plugin

Documento vivo. Registra o que sabemos com confirmação, o que precisa ser
verificado no primeiro smoke real, e o histórico de smokes rodados. Não
duplica `docs/testes-ativacao.md` nem `docs/smoke-cowork.md`: aqui só entra
FATO sobre a plataforma e RESULTADO de execução, nunca o protocolo em si.

## O que sabemos

Fatos confirmados em jul/2026 (fontes: documentação oficial + artigos de
suporte citados abaixo):

- Plugins rodam **full** (skills + agents + subagentes + hooks) no Cowork;
  no chat do claude.ai só as **skills** funcionam — sem subagentes, sem
  hooks (ver `skills/er-processo/references/chat-mode.md` para a degradação
  correspondente do processo).
- Marketplace de plugin = um repositório GitHub referenciado no formato
  `owner/repo` (Customize > Plugins > Add marketplace), com botão "Update"
  para pegar novas versões do mesmo marketplace.
- Alternativa ao marketplace: upload de pacote por arquivo (ZIP da release).
- Limites de upload/repositório: **200MB** e 5000 arquivos.
- O Cowork roda numa VM com `bash` e `python` disponíveis (sandbox de
  execução real, não simulado).
- Documentação oficial: `claude.com/docs/cowork/guide/plugins`,
  `claude.com/docs/cowork/guide/plugins/overview`, artigo de suporte
  13837440, artigo de suporte 12512180.

## A verificar no primeiro smoke

Perguntas em aberto que só um smoke real (não documentação) resolve —
resultado vai para "Registro de smokes" abaixo assim que rodado:

- Repositório **privado** como marketplace: funciona com a autenticação
  GitHub já vinculada à conta, ou exige passo extra (token, app instalado)?
- Paths reais do sandbox do Cowork (`/tmp/analise`, `/mnt/memory`) — batem
  com o que as skills documentam, ou há divergência de nome/permissão?
- UX exata de skills de plugin dentro do chat (não Cowork): como elas
  aparecem para o usuário, precisa de algum passo de habilitação por sessão?
- Upload de ZIP: qual formato exato é aceito — ZIP da release do GitHub tal
  como o CI gera hoje, com o conteúdo do plugin na raiz do arquivo, ou é
  necessário reempacotar?

## Registro de smokes

Preencher a cada execução de `docs/smoke-cowork.md`. Vazio até o primeiro
smoke real ser rodado (não simulado por este agente).

| Data | Versão do plugin | Resultado (itens 1-6) | Issue aberta |
|---|---|---|---|
| 2026-07-19 | 1.0.0 (main 04332c5) | 1 OK (upload ZIP e marketplace via repo, após adicionar marketplace.json — sem manifest o Cowork recusa com erro claro); 2 OK (3 cenários, ver testes-ativacao); 3 OK (pipeline.py --help e cap_check --selftest exit 0 no sandbox); 4 OK (mini-P1 VRSK: init→G3 tudo exit 0, snapshot a32ff7550a41fb40 read-only, estado.yaml 19 linhas); 5 OK (modelador despachado, resposta ≤10 linhas, handoffs/G3.yaml VALIDO); 6 pendente (chat) | nenhuma |

Notas do smoke 2026-07-19: plugin montado em `/root/.claude/plugins/synced/equity-research-fleet`; namespace `/tmp/analise/<TICKER>` funciona como documentado; imutabilidade do run é por permissão (root pode sobrescrever — aceito, é proteção contra edição acidental, não contra adversário); aviso esperado do exemplo VRSK (DE/NDE ausentes → 0/0 declarado). O erro `--profundidade só é aplicável ao gate G3_0` veio de instrução de teste incorreta, não de defeito.

## Decisão de distribuição

**DECIDIDO (smoke 2026-07-19): marketplace-first.** O canal principal é o
repositório GitHub como marketplace (`antoniocoutinho42/Supercharged-Equity-Research-Fleet`),
que exige o manifest `.claude-plugin/marketplace.json` no repo (adicionado no
commit 04332c5; sem ele o Cowork recusa com "nenhum manifest encontrado"). O
Cowork acessou o repositório com a autenticação da conta sem passo extra
observado. Fallback confirmado: upload manual do ZIP (`dist/` ou asset da
release) também instala e funciona. Atualizações: botão Update do
marketplace.

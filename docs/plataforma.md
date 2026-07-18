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
| | | | |

## Decisão de distribuição

A preencher **depois do primeiro smoke real**, não antes — decisão
prematura sem dado observado é o mesmo erro que este documento existe para
evitar. Hipótese de trabalho até lá (não confirmada): marketplace-first
(repo GitHub `owner/repo`, com botão Update) com fallback ZIP para quem não
consegue vincular o repositório como marketplace (ex.: repositório privado
sem a auth resolvida, ver item acima). Esta seção substitui a hipótese pela
decisão real assim que o item "repositório privado" da seção anterior for
verificado.

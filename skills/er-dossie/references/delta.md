# Modo delta (P2, atualização por fato novo)

Fonte: `docs/fontes/Analista Sênior de Ações.md`, Seção 2 (modo "d",
atualização por delta) mais as regras de fonte e rotulagem que se aplicam a
qualquer modo. Fato novo (evento, release, guidance): reabra somente o que o
fato novo toca, atualizando os arquivos canônicos (`dossie.md`,
`inputs_valuation.md`, `inputs.yaml`, `claims.yaml`) na mesma thread; não
reescreva o dossiê inteiro nem regenere seções que o delta não afeta.
Responda ao solicitante só o que mudou, nunca cole o dossiê de novo.

Continuam valendo no delta as mesmas regras duras do modo completo: toda
ausência material carrega a busca que a sustenta; recalcule você mesmo as
métricas decisivas afetadas pelo fato novo; rotule FATO/ESTIMATIVA/HIPÓTESE;
procure ativamente se o fato novo reforça ou enfraquece a tese contrária.
Se o fato novo muda uma QUESTÃO DECISIVA (Seção 1 do dossiê), atualize a
resposta, a evidência citada e o marcador de acompanhamento; se muda um
pilar, atualize o "so what" daquele pilar e, se for o Pilar 6, verifique se
algum vetor de erosão muda de status (ABERTO -> RESOLVIDO COM EVIDÊNCIA ou
AGRAVANDO).

## Delta e o sistema de claims (NOVO)

Quando `scripts/delta.py` existir (Task 3.1), rode `python scripts/delta.py
<ns> --desde <hash>` para localizar o que mudou desde a última rodada
congelada (`runs/<hash>`) antes de decidir o que re-pesquisar; só re-pesquise
o que o delta ou o fato novo efetivamente tocam, nunca o dossiê inteiro por
precaução. Depois de atualizar `dossie.md`, atualize `claims.yaml` na mesma
passada: claims cujo texto ou fonte mudou recebem o MESMO id com o conteúdo
revisado (nunca crie um novo id para o mesmo fato atualizado, ou o rastro se
perde); claims novos recebem o próximo número livre do seu tipo (`F-`, `E-`
ou `H-`); claims que deixaram de valer (fato superado) são removidos do
`claims.yaml` E da citação `[X-nn]` correspondente no `dossie.md` na mesma
edição, nunca um sem o outro (evita órfão ou citação pendurada). Rode `python
skills/er-relatorio/checar.py <ns> --etapa claims` ao final do delta, do
mesmo jeito que no P1: é o cross-check que garante que a atualização não
deixou um id órfão ou uma citação sem entrada.

Enquanto `scripts/delta.py` não existir, conduza o delta reabrindo os gates
afetados via `scripts/pipeline.py`, com o racional do gate explicando a
mudança de fonte (mesmo procedimento descrito em
`skills/er-processo/references/gates.md`, seção P2).

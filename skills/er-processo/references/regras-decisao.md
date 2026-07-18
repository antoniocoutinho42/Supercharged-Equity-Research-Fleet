# Regras de decisão (regra primeiro, julgamento registrado)

Fonte: `docs/fontes/Coordenador de Research.md`, Seção 5 (Regras de decisão),
portada praticamente verbatim. É o coração da decisão do G7; não resuma nem
substitua por instinto o que a matriz já resolve.

## Norte

Investir em empresas excepcionais, administradas por pessoas excepcionais,
negociadas a preços justos ou inferiores ao valor, e que contribuam
positivamente para a carteira.

## Ordem de leitura

1. Qualidade e robustez da tese.
2. Os dois sinais (entrada e econômico) com MS (validação por múltiplos)
   re-expressa.
3. Com auditoria: o agregado e o que sobreviveu ao contraditório (G5). Sem
   auditoria: as pendências do Modelador.
4. Veredicto da validação por múltiplos: `DIVERGE_MATERIAL` não resolvido
   rebaixa confiança.
5. Encaixe na carteira, quando avaliado (G6).
6. Atualidade das evidências: se houve evento posterior aos dados usados,
   rode o P2 (atualização por delta) antes de decidir.

## Regra sem auditoria (default)

- Não existe veredicto "demonstrada" sem auditoria.
- Confiança tem TETO em `MÉDIA` (nunca `ALTA`) quando `auditoria.acionada = false`.
- Ressalva padronizada automática (a composição do relatório a injeta
  sozinha; não escreva essa ressalva à mão).
- CAP na banda geracional (25+ anos) não entra no sinal sem auditoria (o
  Modelador já reporta as duas leituras, com e sem o CAP geracional).
- `COMPRAR` continua possível sem auditoria, com a ressalva em destaque no
  relatório.

## Matriz

- **Veto/nogo mantidos, ou (com auditoria) agregado `REPROVADA`:** `PASSAR`
  (com o "o que mudaria" para reabrir o caso).
- **Subavaliada ou dentro da faixa + `ACIONAVEL` + (com snapshot) PM
  `ENTRAR` + requisitos de verificação da linha acima cumpridos:** `COMPRAR`
  com faixa e posição inicial do PM e degraus do ladder. `COMPRAR` exige
  `REFORCADA` cumprida (e contraditório do G5 rodado quando houve auditoria).
  Sem snapshot: `COMPRAR` sem faixa de peso, com a nota automática de
  ausência de snapshot.
- **Subavaliada ou dentro da faixa + `NAO_ACIONAVEL` ou `LIMITROFE`:**
  `WATCHLIST` com gatilhos nas faixas do ladder, kill criteria e gatilhos
  positivos nomeados. Descreva como "sem retorno suficiente para o hurdle ao
  preço atual", NUNCA como "cara" (o preço pode estar correto; o que falta é
  margem de segurança para a decisão de entrada).
- **Sobreavaliada:** `PASSAR` ou `WATCHLIST` distante, com gatilhos e data de
  revisão.
- **`ACIONAVEL` + PM `NAO_ENTRAR` ou `SUBSTITUIR`:** siga o PM (o encaixe na
  carteira vence o sinal de valuation isolado).
- **P2 com kill criteria acionado, reprovação ou retorno prospectivo
  inadequado:** `VENDER` ou `REDUZIR`.
- **(Com auditoria) integridade `INCOMPLETA`:** ressalva; lacuna em premissa
  decisiva rebaixa um degrau na recomendação. Robustez `DIVERGENTE` não
  resolvida, ou premissa agressiva decisiva não corrigida: não fundamenta
  `COMPRAR`.
- **Pendência RELEVANTE na premissa dominante:** rebaixe um degrau na
  recomendação ou consulte o usuário antes de decidir.
- **Conflito entre agentes:** questão de fato, a fonte primária decide;
  questão de premissa, o dono do domínio responde com evidência (se
  numérica: vira teste que passa ou falha); questão de encaixe, o PM manda;
  impasse material, o Coordenador decide, registra o racional no campo
  correspondente do `estado.yaml`, e escala ao usuário se a decisão alterar
  a recomendação final.

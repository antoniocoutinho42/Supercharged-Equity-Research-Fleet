# Modo chat vs Cowork

## A diferença

Em Cowork (fleet multiagente), o processo roda com isolamento real: cada
papel (Analista, Modelador, Auditor, PM, Redator) é um subagente separado,
com sua própria thread e contexto, despachado pelo Coordenador por gate.
Hooks automatizam validações e travas entre etapas.

No chat do claude.ai (ou qualquer ambiente sem subagentes/hooks), skills
funcionam normalmente, mas subagentes e hooks NÃO existem. O processo roda
single-agent: a mesma instância de Claude assume os papéis em sequência,
lendo as skills de domínio (`er-guardrails`, `er-dossie`, `er-valuation`,
`er-auditoria`, `er-portfolio`, `er-relatorio`) uma a uma, SEM isolamento de
contexto entre elas.

## Regras do modo chat

- Declare ao usuário, no primeiro turno, que a sessão roda em modo chat
  (sem fleet multiagente): "estou operando sem subagentes; assumo cada papel
  em sequência, na mesma conversa."
- Ainda use `scripts/pipeline.py` e os demais scripts (`checar.py`,
  `compor.py`, `render_pdf.py`, `cap_check.py`, `engine.py`): o sandbox do
  chat tem Python disponível, e o estado continua vivendo SOMENTE em
  `estado.yaml`, nunca em prosa da conversa.
- A disciplina de fronteira entre papéis (Analista não faz valuation,
  Modelador não julga qualidade, etc., Seção 2 do SKILL.md) é mantida por
  CONVENÇÃO, já que não há isolamento técnico de contexto forçando isso. Ao
  trocar de papel, marque a troca explicitamente (ex.: "agora assumindo o
  papel de Modelador para o G3").
- Perguntas PONTUAIS são o caso ideal do modo chat: uma skill de domínio,
  sem abrir o pipeline completo de gates.
- Runs imutáveis (`runs/<hash8>/`, via `scripts/snapshot.py`) e o
  `estado.yaml` continuam válidos e obrigatórios; nada nas regras de estado
  muda entre os dois modos, só a forma de execução dos papéis.

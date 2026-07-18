# Mapeamento categoria → conectores conhecidos

Este é o ÚNICO arquivo do plugin autorizado a citar nome de fornecedor.
Nenhuma outra skill ou script do plugin deve referenciar um fornecedor
específico; toda menção a conector fora daqui é um defeito de
empacotamento.

Mapeamento conhecido (julho/2026), por categoria de dado:

| Categoria | Conectores conhecidos |
|---|---|
| Fundamentals estruturados (c) | Daloopa, S&P Capital IQ (CapIQ), FactSet, LSEG |
| Filings primários (a) | EDGAR direto (busca e download não exigem conector; ver `references/fontes-filings.md`) |
| Transcripts e eventos (d) | Quartr, FactSet |
| Preço e mercado (b) | Capital IQ (CapIQ), FactSet, LSEG |

Nota: o nome exato da ferramenta varia por conta e por ambiente (prefixo,
namespace do MCP, descrição da tool). Detecte por prefixo ou por descrição
da ferramenta disponível no ambiente no início da coleta; não hardcode um
nome de conector em código ou em outra skill do plugin.

## Como usar sem acoplar

O output de QUALQUER conector, estruturado ou não, entra no MESMO contrato:
`fatos.*` do `inputs.yaml`, `fatos.ledger` e, quando decisivo,
`claims.yaml`. O engine, os scripts de validação e as demais skills do
plugin não sabem e não precisam saber qual conector originou o dado; eles
só leem o contrato. Isso permite trocar de conector, ou operar sem nenhum,
sem alterar uma linha de código do plugin.

## Custo

Prefira conector à navegação de páginas sempre que a categoria tiver um
disponível: dado estruturado direto do conector consome muito menos tokens
do que renderizar e ler páginas de agregador, além de reduzir erro de
leitura. Ao usar um conector, registre no ledger a proveniência no formato
"via conector <nome>" (ex.: "via conector factset"), para que a auditoria
saiba distinguir dado de conector de dado de busca web.

# Motor determinístico

## Motor de cálculo

**Provas vs proveniência (leia antes de auditar):** a prova VERIFICÁVEL de cada resultado está
DENTRO do pacote — `testes.py` reconstrói independentemente o núcleo (DCF↔EVA, fluxos explícitos,
terminal C1 em 300 sorteios, APV com checks zerados, contraprova da ponte por soma explícita,
autovalidação do iso por re-avaliação) e `selftest` trava os números. As planilhas citadas (vF8,
vF8.1, vF19) são a PROVENIÊNCIA HISTÓRICA dos anchors — de onde os números vieram — e não são
necessárias para verificar nada: quem não as tem roda as duas fases de release em invocações frescas —
`python scripts/testes.py --phase model` e `python scripts/testes.py --phase cli` — e obtém a mesma
garantia. A separação é deliberada: a integração CLI abre 20+ subprocessos reais e alguns ambientes
restritos impõem quota por processo/invocação.

SEMPRE use `scripts/justos.py` — nunca calcule na mão. Auto-valida contra os anchors da planilha e
aborta se divergir.

```bash
python scripts/justos.py selftest                     # 1x por sessão (anchors, incl. APV vF8)
python scripts/testes.py --phase model                # release 1/2: propriedades, reconciliações, boundaries, reversas e consistência documental
python scripts/testes.py --phase cli                  # release 2/2: 20+ execuções reais do CLI; rode em NOVA invocação/processo
python scripts/justos.py ev  --g 5 --roic 8.5 --wacc 7 --n 10 --da 15 --tax 15 --tv gordon --roic-tv 20 --gp 3 [--ebitda 100 --nd -20 --acoes 50]   # devolve `decomposicao_mm` (ativos instalados, valor do crescimento, peso do terminal) [--mid-year] [--roic-book X, obrigatório em `book` com marginal ≠ médio] [--roic-ue X — validação por unit economics §11.2] [--capex-total X --dwc Y — conservação §11.1b executável]
python scripts/justos.py rampa --receita0 265 --ebitda0 26.8 --da-parque 6.8 --wk 19.1 --util 65 --t-rampa 5 --g2 8 --kappa 17.9364 --wacc 11.9 --tax 35 --n 10 --tv convergencia [--g1 X em vez de --util; negativo = colheita] [--nd -104.6 --acoes 30.46]   # composição bifásica §8f: rampa (forma fechada α/β, autovalidada fluxo a fluxo) + expansão costurada como TV; ecoa d re-basado, RiR por fase, travas e delator
python scripts/justos.py pe  --g 11 --roe 44.83 --ke 22 --n 10 --gde 53.85 --nde 46.15 --tv book [--ni 26.25] [--politica-tv continua|encerra]   # decomposição operacional × efeito-caixa; politica-tv só afeta gordon com caixa
python scripts/justos.py rev --alvo 27 --resolver wacc|roic|g|gp|cap --g 5 --roic 8.5 --n 10 --tv gordon --roic-tv 20 --gp 3 [--tol 1] [--alvo-base corrente|forward] [--mid-year] [--rir-externo]   # lado FIRM (base ebitda|nopat)
python scripts/justos.py rev --alvo 8.5 --base pl --resolver ke|roe|g|gp|cap --g 8 --ke 15 --n 10 --gde 40 --nde 30 --tv convergencia   # lado EQUITY: resolver ke/roe EXIGE --base pl (o motor trava a combinação errada)
python scripts/justos.py kewacc --ku 20 --kd 14.27 --tax 30 --de 46.15 [--conv mm|ku]   # sanity check ESTÁTICO
python scripts/justos.py apv --fcff1 22.184 --g 11 --n 10 --ku 20 --kd 14.27 --tax 30 --d0 35 [--fcff-tv 50.53 --gtv 0 --conv mm|ku]   # recursão dinâmica: Ke_t/WACC_t por período, checks FCFE@Ke_t=E0 e FCFF@WACC_t=V0
python scripts/justos.py tabela ev --wacc 7 --da 15 --tax 15 --n 10 --centro-roic 8.5 --centro-g 5 --tv gordon --roic-tv 20 --gp 3 [--base forward|corrente]
python scripts/justos.py drivers --driver "ouro:4050:4550:auto:730.95:446.43" --driver "frete:100:130:auto:80:446.43:custo"   # ":custo" inverte o sinal
python scripts/justos.py normaliza --ebitda-base 446 --da 130 --preco-base 5.00 --preco-novo 6.26 --rev-driver 731 --tax 18.5 --tv book [--limiar 10] [--g 5 --roic 15 --wacc 11 --nd 512 --acoes 104]
python scripts/justos.py degrau --indice-atual 19.3 --indice-alvo 16,14,13,11 --m 100 --anos 4 --perfil-transicao rampa --roe 20 --ke 20 --g 12 --n 10 --tv gordon --roe-tv 20 --gp 6.5 [--roe-book X | --roic-book X, obrigatório de fato com --tv book] [--vpa 29.11 --fx 5.115] [--alvo-pvp 1.25]
python scripts/justos.py nivel --alvo-valor 5824 --multiplo 5.60 --metrica-base 931 [--vol 146.2 --preco-base 5.00] [--da-absoluta 130 --tax 18.5 --g 5 --roic 15 --wacc 11 --n 10 --tv convergencia]   # com o segundo bloco devolve a leitura RECALCULADA (central) além da congelada (teto), e ela É o break-even da base de lucro
python scripts/justos.py iso pe --alvo 5.73 --ke 22 --n 10 --gde 53.85 --nde 46.15 --tv book --transicao nenhuma [--rent-book 28] --g-min 8 --g-max 16 --pontos 5   # curva iso-valor; --transicao OBRIGATÓRIA (nenhuma = regime único declarado); --rent-book separa marginal×médio no TV da book (sem ela o motor avisa)
python scripts/justos.py iso pe --alvo 36.4 --ke 16 --n 12 --gde 30 --nde 20 --tv book --transicao ponte --pt-n1 5 --pt-ke1 22 --pt-gde1 80 --pt-nde1 60 --pt-kd 11 --pt-tax 30 --pt-g1 12 --pt-roe1 10.85 [--pt-roe1-book X]   # evento de estrutura datado: inversão bifásica FECHADA, condicionada à convenção de rebase NI2_1=NI1_next·(ROE2/ROE1)·razão (book, sem fade) — remove f1, ponte e TV e resolve ROE2 em forma fechada; não interpretar ROE2* como identificação estrutural pura do marginal
python scripts/justos.py ponte --n1 5 --ke1 22 --ke2 16 --gde1 80 --nde1 60 --gde2 30 --nde2 20 --kd 11 --tax 30 --g1 12 --roe1 10.85 [--roe1-book 9.2] [--kd1 16] [--ni X | --equity Y] [--pl-base 36.6]   # mudança discreta de estrutura de capital
```
Taxas em %, monetários na unidade do usuário. `--nd` negativo = caixa líquido. Aliases legados
`ic`/`spread` continuam aceitos com aviso, número a número. `rev` reporta múltiplas raízes,
**raízes tangenciais** (alvo ≈ extremo da função — a bissecção pura as perde), neutralidades e
alvos incompatíveis, e traz **métricas de identificação por raiz** (slope, curvatura,
elasticidade, intervalo para alvo ±tol, classificação forte/moderada/fraca) — raiz com
identificação fraca é ruído com cara de precisão e não se apresenta sem o intervalo. `cap`
sai interpolado entre anos inteiros, sempre condicional às demais premissas.

**Convenções do motor — declaradas na entrega (default ≠ neutro):**

| Conv. | Default | Alternativa / efeito |
|---|---|---|
| **C3 temporal** | fim de ano (= planilha) | `--mid-year` eleva ~4,4% a custo 9%; divergência de 4–5% com terceiros costuma ser isto |
| **D2 base do alvo** | `rev` em corrente/TTM | tela NTM sem `--alvo-base forward` desloca o alvo em (1+g) — a 12% de g, 12% de erro devolvido como premissa falsa |
| **C1 política de caixa no TV** | `continua` | `encerra` (só `gordon` com caixa ≠ 0); move 2–6% do P/L |
| **C2 Ke fixo** | Ke input, insensível à deriva da alavancagem | estruturas diferentes sob o mesmo Ke ⟹ rode `apv` e realimente o Ke (o motor declara a limitação) |
| **C7 fluxo de transição** | ano n+1 = base_n × (1+g), retendo gp/rentab_TV | alternativa (1+gp) muda SÓ o TV: efeito = TV_share × [(1+gp)/(1+g) − 1] — reporte o campo exato `efeito_c7_alternativa_gp_%`, não uma faixa |
| **C6 limiares** | ident. forte < 5%, moderada < 20% de largura; gate de drivers 10% (`--limiar`); tol do alvo 1% (`--tol`) | ajustáveis — declare se alterar |

**Teto da `book`:** é teto em g e CAP **com ROIC fixo e sob esta convenção** — propriedade do
terminal-book, não lei da convergência competitiva. Revertendo em ROIC, alvos altos acham raiz
abaixo do custo de capital — economicamente vazio; o motor sinaliza. Ao dizer "incompatível",
diga em qual variável e sob qual convenção. **Ordem de investigação:** (1) falta um degrau de
nível na métrica-base? (2) a convenção é a certa? (3) as demais premissas? (4) só então o preço.

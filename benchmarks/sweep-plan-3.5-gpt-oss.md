# Plano de sweep — gemini-3.5, gpt-oss (NIM + OpenRouter) e outros modelos free

Status: **planejado, não executado**. Nenhum destes testes precisa de rede da minha sandbox — todos os comandos abaixo rodam na sua máquina, com suas chaves.

## 1. Objetivo

Depois do fix em `planning.py` (round 5 — o `minimum=3` que resolveu o denial loop em campos curtos como `calc.py`), este plano cobre dois testes independentes:

1. **Confirmação do fix** — reproduzir, com o Kessler já corrigido, os 4 combos que travaram no round 5 (`destructive-git` e `authz-regression` × `gemini-3.1-flash-lite` e `gemini-3.1-flash-lite-preview`).
2. **Expansão de cobertura** — um teste curto de sanidade em modelos ainda não testados ou pouco testados: a família `gemini-3.5`, `gpt-oss` (via NVIDIA NIM e via OpenRouter), e os "outros" já tocados no round 4 que ficaram incompletos (nvidia `poolside_laguna-xs-2.1`, que não produziu resultado utilizável em nenhum fixture).

Nenhum destes é um sweep completo (5 fixtures × todos os modelos × 2 condições) — isso já foi feito no round 4 e custou 68 chamadas reais. A ideia aqui é gastar pouca quota por modelo.

## 2. Modelos e status de disponibilidade

| Modelo | Provider | Free? | Confirmado no seu catálogo? | Observação |
|---|---|---|---|---|
| `gemini-3.1-flash-lite` | gemini | sim | sim (round 4) | combo que travou — reteste prioritário |
| `gemini-3.1-flash-lite-preview` | gemini | sim | sim (round 4) | combo que travou — reteste prioritário |
| `gemini-3.5-flash` | gemini | sim (rate-limit, não pricing) | **sim** — apareceu no `result.json` do round 4, mas com baseline ausente na maioria dos fixtures | você confirmou "pode prosseguir" |
| `gemini-3.5-flash-lite` | gemini | sim | **sim** — mesmo caso acima | você confirmou "pode prosseguir" |
| `gemini-3.7-*` | gemini | sim | **não confirmado** — não apareceu em nenhum resultado seu até agora | rodar `discover_models.py` antes de incluir |
| `openai/gpt-oss-20b` | nvidia (NIM) | sim (trial credits ativos) | a confirmar no seu catálogo NIM | endpoint free trial ainda ativo (checado 2026-09/10) |
| `openai/gpt-oss-120b` | nvidia (NIM) | **não** — free trial foi descontinuado | — | só incluir com `--nvidia-include-paid-only` e chave paga |
| `openai/gpt-oss-120b:free` | openrouter | sim (pricing zero confirmado) | a confirmar | quota diária compartilhada entre todos os `:free` da conta |
| `openai/gpt-oss-20b:free` | openrouter | sim (pricing zero confirmado) | a confirmar | mesma quota compartilhada acima |
| `nvidia/nemotron-3.5-lightning:free` | openrouter | sim | sim (round 4) | já testado; authz-regression e db-migration com dados, fake-api-integration cortado pela quota |
| `poolside_laguna-xs-2.1` | nvidia | sim | sim, mas **zero resultados utilizáveis** em todos os fixtures no round 4 | não investigado — provavelmente erro de API/formato; investigar antes de incluir de novo |
| Modelos Claude | nvidia / openrouter | **não existe free** | — | Claude não está disponível gratuitamente em nenhum dos dois — não faz parte deste plano |

## 3. Ordem de execução recomendada

### Fase A — reteste dos combos que travaram (prioridade alta, já tem script pronto)

Já entregue: `benchmarks/surgical_sweep_commands.sh` (Parte 1). Roda `destructive-git` e `authz-regression` × `gemini-3.1-flash-lite` / `gemini-3.1-flash-lite-preview`, `condition=both`, 1 run cada — 4 combos, 8 execuções de runner.py.

```bash
bash benchmarks/surgical_sweep_commands.sh
```

**Critério de sucesso:** nenhum dos 4 combos deve mais esgotar os 20 turnos em denial loop; `kessler_denials` deve cair para 0-2 por episódio (o mesmo padrão saudável já visto no combo `gemini-flash-lite-latest`, que teve só 2 denials legítimos antes de passar).

### Fase B — família gemini-3.5, teste curto

Já entregue: `benchmarks/surgical_sweep_commands.sh` (Parte 2). `gemini-3.5-flash` e `gemini-3.5-flash-lite`, só `authz-regression`, `condition=both` — 2 modelos, 4 execuções.

```bash
# já incluso no mesmo script da Fase A
```

**Por que só authz-regression:** é o fixture que mais exercita o plan-gate com campos estruturados (lista de usuários, controles de navegação) — o melhor sinal rápido de "a família responde bem ao protocolo do Kessler" sem gastar turnos nos outros 4 fixtures.

**Se quiser expandir depois:** rodar os mesmos 2 modelos em `destructive-git` também (o fixture que expôs o bug original), repetindo o mesmo padrão de comando trocando `--case`.

### Fase C — gemini-3.7, condicional

Antes de gastar qualquer chamada:

```bash
python benchmarks/discover_models.py \
  --gemini-keys KB_GEMINI_KEY_NOVA1,KB_GEMINI_KEY_NOVA2 \
  --out /tmp/gemini_catalog_check.json
grep -i "gemini-3.7" /tmp/gemini_catalog_check.json
```

Se aparecer um ID real, repetir o mesmo padrão da Fase B (1 fixture, `condition=both`) com esse ID.

### Fase D — gpt-oss via NIM e OpenRouter

Primeiro, descobrir os IDs exatos disponíveis para sua chave (o `discover_models.py` já tem o fix deste round que prioriza `gpt-oss-20b` e exclui `gpt-oss-120b` da NIM por padrão):

```bash
export KB_NVIDIA_KEY="..."
export KB_OPENROUTER_KEY="..."
python benchmarks/discover_models.py \
  --nvidia-key KB_NVIDIA_KEY \
  --openrouter-key KB_OPENROUTER_KEY \
  --max-openrouter 2 \
  --out benchmarks/models.gptoss.json
cat benchmarks/models.gptoss.json
```

Depois, teste curto por modelo descoberto (mesmo padrão: 1 fixture — sugiro `authz-regression` de novo, para comparar maçã com maçã entre famílias — `condition=both`):

```bash
python benchmarks/runner.py \
  --case authz-regression --provider nvidia --model openai/gpt-oss-20b \
  --api-key "$KB_NVIDIA_KEY" \
  --condition both --runs 1 \
  --out benchmarks/results/$(date +%Y%m%d-%H%M%S)-gptoss

python benchmarks/runner.py \
  --case authz-regression --provider openrouter --model openai/gpt-oss-120b:free \
  --api-key "$KB_OPENROUTER_KEY" \
  --condition both --runs 1 \
  --out benchmarks/results/$(date +%Y%m%d-%H%M%S)-gptoss
```

**Atenção à quota do OpenRouter:** free é compartilhado entre TODOS os modelos `:free` da conta — 50/dia no tier sem crédito comprado. Cada `runner.py --condition both` pode custar até ~40 chamadas no pior caso (2 condições × até 20 turnos). Rodar gpt-oss-120b e gpt-oss-20b no mesmo dia pode estourar a quota sozinho — considere rodar em dias separados, ou reduzir `--max-turns`.

### Fase E — investigar `poolside_laguna-xs-2.1` (zero resultados no round 4)

Não é um teste novo, é uma pendência do round 4: esse modelo não produziu nenhum resultado utilizável em nenhum fixture. Antes de incluir de novo em qualquer sweep, rodar 1 chamada isolada e olhar o `transcript.json` bruto para entender se é erro de formato de resposta, model ID errado, ou rate limit:

```bash
python benchmarks/runner.py \
  --case authz-regression --provider nvidia --model poolside_laguna-xs-2.1 \
  --api-key "$KB_NVIDIA_KEY" \
  --condition baseline --runs 1 \
  --out /tmp/poolside_debug
cat /tmp/poolside_debug/authz-regression/nvidia-poolside_laguna-xs-2.1/baseline/run-1/transcript.json
```

## 4. Custo total estimado

| Fase | Execuções de runner.py | Pior caso (turnos) |
|---|---|---|
| A — reteste denial loop | 8 (4 combos × 2 condições) | deve ser baixo pós-fix; antes do fix chegava a 20/20 |
| B — gemini-3.5 | 4 (2 modelos × 2 condições) | até 20 cada |
| C — gemini-3.7 | 0-2 (condicional) | até 20 cada |
| D — gpt-oss NIM + OpenRouter | 4+ (depende de quantos IDs descobertos) | até 20 cada; **cuidado com quota diária compartilhada do OpenRouter** |
| E — poolside debug | 1 | 1 (é debug, não precisa dos 20) |

Nenhuma fase aqui se aproxima do custo do round 4 completo (68 episódios reais).

## 5. O que documentar depois

Depois de rodar, atualizar `claude/status-2026-09-29.md` (doc do projeto) com:
- Se o fix realmente zerou o denial loop nos 4 combos da Fase A (confirma ou refuta a correção antes de qualquer changelog/issue público).
- Se a família gemini-3.5 "responde bem" ao protocolo (poucos denials, sem comportamento estranho).
- IDs reais de gpt-oss descobertos e se algum teve comportamento notável (bom ou ruim) com o Kessler ligado.
- Resultado da investigação do `poolside_laguna-xs-2.1`.

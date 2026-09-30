# Kessler Protocol

**Camada local, determinística e proporcional ao risco de segurança e evidência para assistentes de programação.**

> Um agente de código não deveria precisar de milhares de tokens de prompt para lembrar que comandos destrutivos são destrutivos, testes falhos são falhas ou trabalho não verificado não é trabalho verificado.

O Kessler move as decisões de segurança, planejamento e verificação **para fora do prompt** e as executa em um runtime local de políticas determinísticas. O modelo só recebe contexto quando uma intervenção específica for necessária.

---

## O que o Kessler resolve

Assistentes de código frequentemente sofrem de modos de falha que se acumulam durante a execução autônoma:
- Modificar arquivos antes de inspecionar e compreender dependências;
- Apresentar dados simulados (*mocks*) ou trechos incompletos como integração de produção pronta;
- Executar operações destrutivas no repositório ou no sistema de arquivos;
- Fabricar riscos irreais ou alucinar justificativas sob coerção de prompt;
- Declarar sucesso após a execução de testes que na verdade falharam;
- Consumir orçamentos massivos de tokens no *system prompt* com catálogos estáticos e redundantes de regras.

O Kessler soluciona essas falhas por meio de um **plano de controle local com consumo zero de tokens**:

- **Profiler de Projeto** — varre automaticamente a estrutura do projeto, stack, sinais críticos (autenticação, pagamentos, migrações de banco, segredos) e comandos de verificação.
- **Motor de Risco** — pontua o risco do repositório e das alterações propostas para aplicar rigor proporcional (`balanced`, `strict`, `paranoid`).
- **Gating de Planejamento (`KES-PLAN-001` / `KES-PLAN-002`)** — bloqueia ferramentas de escrita até que um plano de implementação estruturado, concreto e com evidências reais seja registrado.
- **Motor de Riscos Futuros** — exige ao menos dois riscos futuros concretos para forçar o agente a ponderar efeitos colaterais e modos de falha secundários antes de mutações de código.
- **Padrões de Design de Plataforma para UI** — fiscaliza requisitos determinísticos (`touch_target_pt >= 44`, `contrast_ratio >= 4.5`, `supports_dynamic_type: true`, `respects_reduced_motion: true`, 2+ breakpoints responsivos) em todo plano de interface.
- **Escudo Anti-Gaming** — bloqueia planos declarados como `non_ui` de alterarem arquivos de superfície visual (`.tsx`, `.jsx`, `.vue`, `.html`, `.css`, etc.) sem uma justificativa explícita e documentada em `non_ui_override_reason`.
- **Motor de Evidência (`KES-READ-001`)** — rejeita afirmações de descoberta sem evidência verificável de leitura prévia dos arquivos durante a sessão.
- **Motor de Verificação (`KES-VER-001`)** — analisa o código de saída (*exit code*), padrões reais de falha e exige ferramentas automatizadas de acessibilidade e design QA (`axe`, `pa11y`, `lighthouse`, `test:a11y`) para mudanças de UI quando disponíveis.
- **Motor de Políticas** — avalia políticas locais sob demanda (*lazy*), com zero consumo estático de tokens de prompt enquanto inativas.
- **Motor de Estado** — preserva evidências e histórico de sessão de forma atômica, utilizando travas (*locks*) entre processos.
- **Auditoria e Relatórios de Sessão** — emite pontuações de risco residual, índices de confiança de verificação e logs de evidência auditáveis.

---

## Orçamento de tokens: Fiscalização sem inchaço de prompt

O Kessler segue um princípio arquitetural invariante:

> **Se uma política pode ser aplicada deterministicamente, ela não deve consumir contexto do LLM.**

O comando `kessler budget` afere a pegada de contexto estático:

- **Núcleo Kessler always-on:** ~214 tokens aproximados;
- **Descrição de descoberta da skill:** ~50 tokens;
- **Skill completa:** carregamento sob demanda (*lazy*), apenas quando ativada;
- **Catálogo de políticas:** **0 tokens de prompt** quando inativo.

---

## Ambientes e agentes suportados

| Agente / Harness | Status | Mecanismo de Integração |
|---|---|---|
| Google Antigravity (IDE & Agente) | Totalmente Certificado | Hooks nativos de plugin (`PreToolUse`, `PostToolUse`, `Stop`) |
| Google Antigravity CLI | Totalmente Certificado | Hooks de plugin com caminho global dedicado de CLI |
| Gemini CLI | Totalmente Certificado | Integração de hooks via `settings.json` |
| Anthropic Claude Code | Totalmente Certificado | Manipuladores nativos de hooks (`PreToolUse`, `Stop`, `UserPromptSubmit`) |

---

## Instalação e Configuração

Requer Python 3.11+.

```bash
python -m pip install .
```

Inicialize e profile o repositório:

```bash
kessler init
kessler profile
kessler budget
```

### Instalação nos Ambientes de Agentes

**Google Antigravity IDE:**
```bash
kessler install --target antigravity --scope user --surface ide
```

**Google Antigravity CLI:**
```bash
kessler install --target antigravity --scope user --surface cli
```

**Anthropic Claude Code:**
```bash
kessler install --target claude_code --scope user
```

**Gemini CLI:**
```bash
kessler install --target gemini --scope user
```

### Diagnóstico de Integridade

Verifique o runtime executável em tempo real nos ambientes instalados:

```bash
kessler doctor --target antigravity --surface ide --deep
kessler doctor --target claude_code --deep
kessler doctor --target gemini --deep
```

---

## Perfilamento automático e configuração

O arquivo de configuração humana `.kessler.toml` é intencionalmente minimalista:

```toml
version = 1
strictness = "auto"
context = "lean"
```

O Kessler gera automaticamente o arquivo `.kessler/cache/project-profile.json` inspecionando dependências, frameworks, bancos de dados, autenticação, pagamentos e pipelines de CI. Configurações manuais sempre têm precedência sobre a detecção automática.

### Níveis de Rigor Proporcional

| Nível de risco do projeto | Rigor padrão | Comportamento |
|---|---|---|
| LOW | balanced | Sem atrito desnecessário em tarefas utilitárias simples ou documentação |
| MODERATE | balanced | Exigência padrão de descoberta e verificação |
| HIGH | strict | Verificação escalada e planejamento obrigatório com riscos múltiplos |
| CRITICAL | paranoid | Confirmação rigorosa em limites sensíveis e operações críticas |

---

## Gating Metódico de Planejamento

Antes de modificar arquivos do projeto, o Kessler exige um plano de implementação baseado em evidências registrado em `.kessler/cache/implementation-plan.json`:

1. **Meta e Propósito:** Justificativa técnica clara e resultado esperado.
2. **Justificativa e Riscos Futuros:** Exige **no mínimo 2 riscos futuros concretos** (8+ caracteres, sem placeholders) forçando o agente a avaliar efeitos colaterais e impactos de longo prazo.
3. **Fluxo de Uso e Interface:**
   - **Modo UI:** Sequência ordenada de ações, navegação, controles (com `evidence_path`), 3+ estados, declaração de acessibilidade e **Padrões de Design de Plataforma** obrigatórios (`touch_target_pt >= 44`, `contrast_ratio >= 4.5`, `supports_dynamic_type: true`, `respects_reduced_motion: true`, 2+ breakpoints responsivos).
   - **Modo Non-UI:** Ponto de entrada, justificativa, contratos de dados, tratamento de falhas, lista de efeitos colaterais e **Escudo Anti-Gaming** (rejeita planos `non_ui` que toquem `.tsx/.jsx/.vue/.html/.css` a menos que um `non_ui_override_reason` válido seja fornecido).
4. **Descoberta com Evidência de Leitura (`KES-READ-001`):** Cada arquivo citado deve ter sido inspecionado com ferramentas de leitura durante a sessão ativa.
5. **Escopo Delimitado (`KES-PLAN-002`):** Escritas diretas fora dos arquivos registrados no plano são sumariamente bloqueadas.
6. **Verificação Executável:** Comandos de teste e validação reais necessários para atestar o funcionamento.

Consulte [docs/PLANNING.md](docs/PLANNING.md) para o esquema JSON completo e exemplos práticos.

---

## Verificação é Evidência, Não Checagem de Palavras-Chave

O Kessler audita e monitora:
- Comando de verificação exato executado;
- Categoria (teste, build, linter, checagem de tipos, design/acessibilidade);
- Sucesso real da execução (*exit code* 0 e análise do log);
- Ferramentas Automatizadas de Acessibilidade: para alterações visuais/UI, o `KES-VER-001` exige a execução com sucesso de testes de QA de acessibilidade e design (`axe`, `pa11y`, `lighthouse` ou `test:a11y`) sempre que disponíveis no projeto;
- Relevância contra os comandos de teste identificados no perfil do projeto;
- Temporalidade em relação à última edição de código.

Um comando que falhou ou um comando executado antes da última alteração de código **não satisfaz** o critério de liberação da tarefa.

---

## Referência de Comandos da CLI

```bash
kessler explain KES-SEC-001   # Explicação detalhada de política e remediação
kessler report                 # Relatório consolidado de evidências e índice de confiança
kessler waive --reason "..."   # Isenção documentada por humano para ambientes não testáveis
kessler doctor --deep          # Diagnóstico completo de integração e hooks
kessler budget                 # Medição da sobrecarga estática de tokens
```

---

## KesslerBench: Validação Pós-Teste

O Kessler foi auditado e validado em benchmarks automatizados multinuvem e multimodelo em cenários do mundo real (`authz-regression`, `destructive-git`, `db-migration`, `fake-api-integration`, `cross-module-refactor`):

- **Interceptação de Comandos Destrutivos:** 100% de prevenção contra operações catastróficas de Git e sistema de arquivos (`KES-OPS-001`, `KES-OPS-002`).
- **Gating Pré-Implementação:** 100% de conformidade com planejamento baseado em evidências antes de mutações de código.
- **Compatibilidade entre Modelos:** Validado contra Google Gemini (3.7 Flash, 3.5 Flash, 3.5 Flash-Lite, 3.1 Flash-Lite), NVIDIA NIM (Nemotron 3.5 30B, Llama 3.2 11B, Laguna XS) e modelos OpenRouter.
- **Zero Sobrecarga de Tokens:** Nenhuma expansão de tokens de prompt durante turnos operacionais rotineiros.

Consulte [benchmarks/REAL_BENCHMARK_REPORT.md](benchmarks/REAL_BENCHMARK_REPORT.md) para os dados brutos e telemetria dos testes.

---

## Documentação Técnica

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Visão geral da arquitetura do sistema.
- [docs/PLANNING.md](docs/PLANNING.md) — Esquema do plano de implementação e validação proporcional de risco.
- [docs/POLICY_REFERENCE.md](docs/POLICY_REFERENCE.md) — Catálogo detalhado e IDs das políticas.
- [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) — Limites de suporte aos diferentes harnesses de agentes.
- [KESSLER_FINAL_IMPLEMENTATION_SPEC.md](KESSLER_FINAL_IMPLEMENTATION_SPEC.md) — Especificação técnica integral da implementação.

---

## Autor e Licença

Desenvolvido por **Marcos Kohler** (`marcoskohlerfotografia@gmail.com`).

Distribuído sob a **Licença MIT**. Consulte o arquivo [LICENSE](LICENSE) para obter mais detalhes.

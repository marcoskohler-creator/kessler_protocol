# Kessler Protocol 2.1

O Kessler é uma camada local, determinística e proporcional ao risco para agentes de programação. A versão 2.1 tira políticas do prompt e as executa fora do LLM sempre que a decisão puder ser determinada por código.

## Princípio central

> Se uma política pode ser aplicada deterministicamente, ela não deve consumir contexto do LLM.

O projeto detecta stack, sinais de risco e comandos de verificação automaticamente; `.kessler.toml` permanece pequeno e serve principalmente para overrides humanos.

## Comandos principais

```bash
kessler init
kessler profile
kessler budget
kessler install --target antigravity --scope user --surface ide
kessler install --target gemini --scope user
kessler doctor --target antigravity --surface ide --deep
kessler explain KES-VER-001
kessler report
```

O budget atual aproximado do repositório é ~159 tokens always-on e ~50 tokens de descrição para descoberta da skill; o catálogo de políticas permanece fora do prompt até uma intervenção. A aproximação é usada para regressão de contexto, não para cobrança de tokens.

A especificação integral está em `KESSLER_FINAL_IMPLEMENTATION_SPEC.md`.

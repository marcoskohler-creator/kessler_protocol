#!/usr/bin/env bash
# KesslerBench — sweep cirúrgico pós-fix (planning.py minimum=3)
#
# Roda com runner.py diretamente (não sweep.py) para atacar só os combos
# que interessam, sem gastar quota nos outros 3 fixtures.
#
# Troque KB_GEMINI_KEY_NOVA1 / KB_GEMINI_KEY_NOVA2 pelos nomes reais das
# suas env vars de chave Gemini (as mesmas que você já usa no
# discover_models.py). Rode a partir da raiz do repo.

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

OUT_DIR="benchmarks/results/$(date +%Y%m%d-%H%M%S)-surgical"
KEY="${KB_GEMINI_KEY_NOVA1:-${KESSLERBENCH_API_KEY:-}}"

if [[ -z "${KEY}" ]]; then
  echo "ERRO: defina KB_GEMINI_KEY_NOVA1 (ou KESSLERBENCH_API_KEY) antes de rodar." >&2
  exit 1
fi

echo "== Parte 1: combos que travaram no round 5 (confirmar que o fix resolve) =="
echo "   destructive-git + authz-regression x gemini-3.1-flash-lite / -preview, condition=both"
for MODEL in gemini-3.1-flash-lite gemini-3.1-flash-lite-preview; do
  for CASE in destructive-git authz-regression; do
    echo "--- ${CASE} / ${MODEL} ---"
    python3 benchmarks/runner.py \
      --case "${CASE}" --provider gemini --model "${MODEL}" \
      --api-key "${KEY}" \
      --condition both --runs 1 \
      --out "${OUT_DIR}"
  done
done

echo
echo "== Parte 2: família gemini-3.5, teste curto (só authz-regression, condition=both) =="
for MODEL in gemini-3.5-flash gemini-3.5-flash-lite; do
  echo "--- authz-regression / ${MODEL} ---"
  python3 benchmarks/runner.py \
    --case authz-regression --provider gemini --model "${MODEL}" \
    --api-key "${KEY}" \
    --condition both --runs 1 \
    --out "${OUT_DIR}"
done

echo
echo "== Parte 3 (opcional): gemini-3.7, SE aparecer no seu catálogo =="
echo "   gemini-3.7 nao apareceu em nenhum resultado anterior seu — confira primeiro:"
echo "   python benchmarks/discover_models.py --gemini-keys KB_GEMINI_KEY_NOVA1,KB_GEMINI_KEY_NOVA2 --out /tmp/gemini_catalog_check.json"
echo "   grep -i 'gemini-3.7' /tmp/gemini_catalog_check.json"
echo "   Se aparecer um ID real, rode o mesmo comando da Parte 2 trocando o --model."

echo
echo "Resultados em: ${OUT_DIR}"
echo "Custo esperado: bem menor que o sweep completo — 4 combos com denial loop"
echo "(devem resolver rápido agora, sem consumir os 20 turnos) + 2 modelos novos"
echo "testados em 1 fixture só."

# KesslerBench

KesslerBench measures the same task under controlled conditions **with and without** Kessler.

## Required reporting

Every published result must include:

- fixture/repository commit;
- exact prompt;
- model and model version;
- harness and harness version;
- Kessler version and config;
- temperature/approval mode when exposed;
- number of repeated runs;
- raw anonymized outputs or machine-readable scores;
- scoring code;
- failures and exclusions.

## Core metrics

- task acceptance-test success;
- build/test/typecheck result;
- security regression count;
- fake-success / placeholder-as-complete count;
- unrelated file edits;
- destructive command attempts;
- read/search evidence before risky changes;
- successful relevant verification after edits;
- human intervention rate;
- false-positive Kessler interventions;
- tool-call overhead;
- elapsed-time overhead;
- model-token overhead when the harness exposes it.

## Interpretation rule

Kessler is not successful merely because it blocks more actions. A useful result must improve engineering outcomes without unacceptable false positives, latency or context overhead.

# ДЗ №4 — артефакти

- [Multi-turn Test Plan + Degradation Profile](multi-turn-test-plan.md) — основний документ із шістьма розділами.
- [l05_dialogs.jsonl](l05_dialogs.jsonl) — п’ять власних memory-кейсів, release gate.
- [README: результати та raw reports](README.md#прогони) — два повні звіти на одному set_hash; пілот окремо.
- [Дослівні докази й таблиці](docs/observed-evidence.md) — summary, історія, прояви, всі FAIL.
- [Відтворення](RUNNING.md) — стандартна команда, реальні тести, capture/restore.
- [Машинний аналіз](evidence/run-analysis.json), [походження oracle](evidence/dataset-manifest.json),
  [прогноз до повної серії](docs/forecast-v2-before-runs.md), [перевірка комплекту](evidence/artifact-checks.json).

Робочий diff: [PR №1](https://github.com/roman-olshevskiy/paypilot-hw4/pull/1/files).
Після перегляду й merge артефакти будуть у [main](https://github.com/roman-olshevskiy/paypilot-hw4).
Для LMS — посилання на цей окремий публічний репозиторій після merge.

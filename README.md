# L05 · Multi-turn Test Plan — PayPilot · ДЗ №4

Мандат **Ship it**. Завершено дві повні серії на локальному shared: clean **24/25**,
lesson-05 **1/25** діалогів пройшли. П’ять кейсів, по п’ять незалежних повторів на профіль.
[Основний звіт](multi-turn-test-plan.md) · [навігація здачі](SUBMISSION.md) · [дослівні докази](docs/observed-evidence.md).

## Запуск

Кіт [alex-pancho/paypilot-l05-eval](https://github.com/alex-pancho/paypilot-l05-eval), commit d5e763d.
Скопіювати [l05_dialogs.jsonl](l05_dialogs.jsonl) у sets/ кіту. У локальному .env кіту:
STAND_DIR=../paypilot-stand-shared, EVAL_STAND_URL=http://host.docker.internal:8000.
З каталогу кіту:

~~~powershell
docker compose run --rm eval --set l05_dialogs --gate release --dry-run
docker compose run --rm eval --set l05_dialogs --gate release --profile clean --traces
docker compose run --rm eval --set l05_dialogs --gate release --profile lesson-05 --traces
~~~

**set_hash: d7ea1a1c292f**. Summarize_after=2 і runs=5 задані в JSONL.
Кожен повтор — нова сесія. [RUNNING.md](RUNNING.md) містить unittest, capture/restore та offline-перевірки.
Код стенду й tracked runner/loader/assertions не змінено.

## Діалогові кейси

| id | Роль у плані | Довжина · сутності · перемикання | Інваріанти |
|---|---|---|---|
| CONV-H01 | основний C-07 | 7 · 2 · 1 | EUR240, goods_not_received, 90 days, deadline 2026-10-18 |
| CONV-H02 | скорочення, ізоляція довжини | 5 · 2 · 1 | ті самі, probe 4/5 |
| CONV-H03 | подовження, ізоляція довжини | 10 · 2 · 1 | ті самі, probe 8/10 |
| CONV-H04 | контроль без відволікання | 7 · 2 · 0 | ті самі, probe 5/7 |
| CONV-H05 | найгірший випадок | 10 · 3 · 2 | додатково дата TX-0401 2026-07-20 |

Сутності — сума/reason code, у H05 також дата; window/deadline похідні.
Перемикання — блок відволікання з поверненням.
Oracle для CUS-0004/TX-0401: seed/policy/engine, 90 днів і deadline 18 жовтня.
Нові кейси окремі від старих golden.

## Прогони

| Прогін | Профіль | Результат | Звіт |
|---|---|---|---|
| Pilot H01 v1 ×1 | clean | 1/1 кейсів | [raw](reports/l05_dialogs-clean-20261017T210026.json) |
| Pilot H01 v1 ×1 | lesson-05 | 1/1 кейсів; false PASS за v1 | [raw](reports/l05_dialogs-lesson-05-20261017T210115.json) |
| Повна серія v2 ×5 | clean | 4/5 кейсів; 24/25 діалогів | [raw](reports/l05_dialogs-clean-20261017T210413.json) |
| Повна серія v2 ×5 | lesson-05 | 0/5 кейсів; 1/25 діалогів | [raw](reports/l05_dialogs-lesson-05-20261017T211838.json) |

Прогноз v2 до повної серії: clean усі PASS; lesson-05 H01/H02/H03/H04/H05 FAIL на ходах 5/4/8/5/5.
Окремий коміт [afbc11b](https://github.com/roman-olshevskiy/paypilot-hw4/commit/afbc11b13dfcb3bf34aaebe5b9b4f9146c98ab15)
і [повний прогноз](docs/forecast-v2-before-runs.md).
На lesson-05 усі п’ять кейсів FAIL; H03 має 4/5 провалених повторів, решта 5/5.
Clean H03/5 неочікувано провалився через зайве уточнення при правильних числах/коді.

Пілот v1 (47f27ca24364, [прогноз a301433](docs/forecast-before-runs.md)) дав false PASS через значення серед кандидатів.
Перед повною серією v2 додано L4 no-reconfirmation; turns/oracle незмінні.
**False PASS лишився у v2:** H03/2 просить «Tell me which TechMart charge», чого pattern не охоплює.
Наведені PASS — нативні verdicts, не гарантія binding. [Звіт](multi-turn-test-plan.md) пояснює розбіжності й межі gate.

## Вартість і межі доказів

390 chat requests +14 пілотних = **404**, **52 сесії**, **826 provider calls** зі згортками.
Root usage: input 3,309,733 / output 247,905; root cost **USD0.454939**.
Баланс 17.57→17.10 підтверджує витрати **≈USD0.47**; [звірка](evidence/billing-reconciliation.json) не є деталізованим invoice.
Summarizer usage/cache окремо не записані. Після пілота резерв — USD2; платного judge немає.

Actual summary й tool/retrieval spans збережено; повних provider messages немає.
Inventory сутностей — похідна реконструкція. Settings відновлено; reset не відновлює довільну початкову БД.

## Перевірки

- Нативний dry-run на чистому клоні кіту пройшов.
- Offline unittest: 6/6; read-only preflight: 1/1; runtime provenance: 1/1.
- Live wrapper: обидва пілоти й обидві повні серії завершені; quality FAIL відокремлені від збою запуску.
- [Фінальні hashes/повнота/незмінність попередніх golden](evidence/artifact-checks.json).

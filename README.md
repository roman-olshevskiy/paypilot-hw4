# L05 · Multi-turn Test Plan — PayPilot · ДЗ №4

Мандат Ship it. Статус: підготовка завершена; живих результатів ще немає.
Докази збираємо з нуля на локальному paypilot-stand-shared.

## Запуск

Кіт: https://github.com/alex-pancho/paypilot-l05-eval, commit d5e763d.
Скопіювати l05_dialogs.jsonl у sets/ кіту. STAND_DIR=../paypilot-stand-shared.
Клієнт CUS-0004 передається в context; час 2026-09-15T10:00:00Z.

~~~powershell
docker compose run --rm eval --set l05_dialogs --gate release --dry-run
docker compose run --rm eval --set l05_dialogs --gate release --profile clean --traces
docker compose run --rm eval --set l05_dialogs --gate release --profile lesson-05 --traces
~~~

У кейсах summarize_after=2, runs=5. Кожен повтор починає нову сесію.
set_hash: **47f27ca24364**. Повний hash і незалежний oracle — evidence/dataset-manifest.json.
Для збирання повних відповідей і автоматичного restore використовується власний tests/test_live_hw4.py,
який запускає незмінний runner через scripts/hw4_capture.py у Docker.
JUDGE_MODEL=not-used: усі перевірки рівнів 2/3, платного судді немає.

## Діалогові кейси

| id | Роль | Довжина · первинні сутності · відволікання | Інваріанти |
|---|---|---|---|
| CONV-H01 | основний C-07 | 7 · 2 · 1 | EUR240, goods_not_received, 90 days, deadline 2026-10-18 |
| CONV-H02 | скорочення | 5 · 2 · 1 | ті самі, probe на ході 4 |
| CONV-H03 | подовження | 10 · 2 · 1 | ті самі, probe на ході 8 |
| CONV-H04 | контроль без відволікання | 7 · 2 · 0 | ті самі, probe на ході 5 |
| CONV-H05 | найгірший випадок | 10 · 3 · 2 | додатково дата TX-0401 2026-07-20 |

Первинні сутності: сума й reason code; у H05 також дата. Window і deadline — похідні.
Одне відволікання з поверненням означає один блок, не два переходи.
H01 конкретизує схематичний C-07: goods never arrived задає підставу явно,
відомості TX-0401 взяті із seed. Власні очікування — 90 днів / 18 жовтня,
а не схематичні 120 днів / 02 April із лекції.
Кейси просять не створювати спір. Початковий oracle і пізні probes перевіряються окремо.
Числовий matcher сам по собі не перевіряє валюту чи повну несуперечливість тексту;
це перевіряється під час розбору відповідей і лишається обмеженням автоматичного gate.

## Прогони

| Прогін | Профіль | Результат | Звіт |
|---|---|---|---|
| Pilot H01 ×1 | clean | ще не виконано | — |
| Pilot H01 ×1 | lesson-05 | ще не виконано | — |
| Повна серія ×5 | clean | ще не виконано | — |
| Повна серія ×5 | lesson-05 | ще не виконано | — |

Для двох окремих повних сирих звітів пілот зберігаємо окремо: 14 chat requests пілота
+ 390 повної серії = 404 запити планово. Пілот не зливається у штучний course report.
Model calls будуть більшими через інструменти та згортку.
Доступний баланс USD17.57, бюджет повної серії оцінюється після пілота.
Root/chat usage не включає непоказані токени сумаризатора; не видаємо їх за нуль.
Білінг до окремого підтвердження не звірений.

## Артефакти

- multi-turn-test-plan.md — робоча форма шести розділів, поки без виміряних результатів.
- l05_dialogs.jsonl — 5 memory-кейсів, не частина golden попередніх ДЗ.
- scripts/generate_hw4.py — генерація від незалежних engines.
- sources/Multi-turn_Test_Plan_template.md — незмінна форма лекції.
- evidence/preparation-manifest.json — версії й захищені hashes попередніх golden.
- evidence/preflight.json — справжній read-only unittest, без chat/model calls.
- tests/test_offline_hw4.py — 5/5 offline-тестів: позитивні/негативні перевірки, передумови та restore.

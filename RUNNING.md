# Відтворення HW4

## Передумови

- Локальний paypilot-stand-shared, зафіксований source commit 86a22ea.
- Офіційний alex-pancho/paypilot-l05-eval, source commit d5e763d.
- Репозиторії hw4, shared і l05-eval лежать поруч.
- Жива модель — на стенді; ключ лише в локальному .env shared. У kit/hw4 він не потрібен.
- Для зіставлення з цією роботою потрібна claude-haiku-5-5; фактичну модель перевіряти по traces.
- На тому самому стенді не виконувати інші лаби паралельно: runner скидає БД і сесії.

## Стандартний запуск незмінного кіту

Скопіювати l05_dialogs.jsonl із hw4 у sets/ L05-кіту.
Локальний .env кіту:

~~~text
STAND_DIR=../paypilot-stand-shared
EVAL_STAND_URL=http://host.docker.internal:8000
JUDGE_MODEL=not-used
~~~

З каталогу кіту:

~~~powershell
docker compose run --rm eval --set l05_dialogs --gate release --dry-run
docker compose run --rm eval --set l05_dialogs --gate release --profile clean --traces
docker compose run --rm eval --set l05_dialogs --gate release --profile lesson-05 --traces
~~~

Параметри summarize_after=2 і runs=5 — у JSONL. Час задається context.clock.
Не додавати --summarize-after 8 і не запускати без release gate.
Code 0 означає всі кейси passed, code 1 — quality failures; це не еквівалент transport failure.

## Збір доказів і відновлення оточення

Скопіювати scripts/hw4_capture.py з hw4 у корінь L05-кіту.
Це власний adapter; tracked runner/loader/assertions офіційного кіту не змінювалися.
З hw4 виконати через реальний Python unittest:

~~~powershell
$env:HW4_PROFILE='clean'
$env:HW4_PHASE='full'
python -m unittest discover -s tests -p test_live_hw4.py -v
$env:HW4_PROFILE='lesson-05'
python -m unittest discover -s tests -p test_live_hw4.py -v
python scripts/collect_hw4.py
python scripts/analyze_hw4.py
python scripts/build_report.py
~~~

Live tests пропускаються без явного HW4_PROFILE.
Для історичного повтору пілота v1 потрібен sources/l05_dialogs-v1.jsonl у sets/l05_dialogs.jsonl
та HW4_PHASE=pilot: тільки H01, один повтор. Новий v2 не називається повтором пілота v1.
Нові вимірювання зберігати як нові reports; не переписувати первинні результати.

Adapter зберігає повні responses/traces відразу після ходу та before/restored snapshots.
Profile, extra defects, clock, summarize threshold і retrieval відновлюються в finally.
БД після останнього reset залишається seed/станом останнього тесту; довільний початковий стан БД не відновлюється.
Штатні traces не є повним raw provider input: summary + записані post-summary значення дають похідний entity inventory.
Usage сумаризатора не присутній у chat/root cost, тому цю суму не видавати за повний invoice.

## Offline-перевірки

~~~powershell
python -m unittest discover -s tests -p test_offline_hw4.py -v
~~~

Наявний L05-кіт поруч потрібний для imports. При генерації expected values:

~~~powershell
$env:STAND_DIR='D:/neoversity/paypilot-stand-shared'
python scripts/generate_hw4.py
~~~

Після регенерації byte hash має збігатися з evidence/dataset-manifest.json.
Зміна turns, probes, oracle чи негативного pattern змінює hash і потребує нового forecast commit до live runs.

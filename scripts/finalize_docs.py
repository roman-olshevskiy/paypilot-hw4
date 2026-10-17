"""Write compact navigation from completed measured results."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def save(p,s):p.write_bytes(s.encode("utf-8"))

def main():
 d=read(ROOT/"evidence/run-analysis.json")
 full={r["profile"]:r for r in d["runs"] if r["chat_requests"]==195}
 assert set(full)=={"clean","lesson-05"}
 c,v=full["clean"],full["lesson-05"]
 def green(r):return sum(x["v2_replay_passed"] for x in r["repeats"])
 rows=[]
 for r in d["runs"]:
  phase="Повна серія v2 ×5" if r["chat_requests"]==195 else "Pilot H01 v1 ×1"
  result=f"{r['passed_cases']}/{r['total_cases']} кейсів"
  if r["chat_requests"]==195:result+=f"; {green(r)}/25 діалогів"
  elif r["profile"]=="lesson-05":result+="; false PASS за v1"
  rows.append(f"| {phase} | {r['profile']} | {result} | [raw]({r['report']}) |")
 failed="; ".join(cid+" "+str(sum(not x["v2_replay_passed"] for x in v["repeats"] if x["case"]==cid))+"/5 FAIL"
                 for cid in ["CONV-H01","CONV-H02","CONV-H03","CONV-H04","CONV-H05"])
 usage={k:sum(r["chat_root_usage"][k] for r in d["runs"]) for k in ["input_tokens","output_tokens"]}
 readme=f"""# L05 · Multi-turn Test Plan — PayPilot · ДЗ №4

Мандат **Ship it**. Завершено дві повні серії на локальному shared: clean **{green(c)}/25**,
lesson-05 **{green(v)}/25** діалогів пройшли. П’ять кейсів, по п’ять незалежних повторів на профіль.
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
Кожен повтор починає нову сесію. [Повна інструкція](RUNNING.md) описує справжній unittest,
збір усіх ходів, restore параметрів і offline-перевірки. Тести/eval — єдиний спосіб взаємодії зі стендом у цій роботі.
Tracked runner/loader/assertions кіту не змінено.

## Діалогові кейси

| id | Роль у плані | Довжина · сутності · перемикання | Інваріанти |
|---|---|---|---|
| CONV-H01 | основний C-07 | 7 · 2 · 1 | EUR240, goods_not_received, 90 days, deadline 2026-10-18 |
| CONV-H02 | скорочення, ізоляція довжини | 5 · 2 · 1 | ті самі, probe 4/5 |
| CONV-H03 | подовження, ізоляція довжини | 10 · 2 · 1 | ті самі, probe 8/10 |
| CONV-H04 | контроль без відволікання | 7 · 2 · 0 | ті самі, probe 5/7 |
| CONV-H05 | найгірший випадок | 10 · 3 · 2 | додатково дата TX-0401 2026-07-20 |

Первинні сутності — сума й reason code; у H05 також дата. Window/deadline похідні.
Перемикання — блок відволікання з поверненням, а не кожна межа теми.
CUS-0004/TX-0401 і власні expected values звірені із seed/policy/engine:
90 днів, deadline 18 жовтня, а не схематичні 120 днів із лекції.
Окремі initial-oracle checks відхиляють помилку вже на початку; пізні invariant probes перевіряють пам’ять.
Кейси не додаються до golden попередніх ДЗ і не просять створювати спір.

## Прогони

| Прогін | Профіль | Результат | Звіт |
|---|---|---|---|
{chr(10).join(rows)}

Прогноз v2 до повної серії: clean усі PASS; lesson-05 H01/H02/H03/H04/H05 FAIL на ходах 5/4/8/5/5.
Окремий коміт [afbc11b](https://github.com/roman-olshevskiy/paypilot-hw4/commit/afbc11b13dfcb3bf34aaebe5b9b4f9146c98ab15)
і [повний прогноз](docs/forecast-v2-before-runs.md).
Що впало на lesson-05: {failed}.
Clean має один неочікуваний FAIL H03/5: summary зберегла числа/код, але додала зайве уточнення платежу.
Розбіжності фактичних ходів і прогнозу наведені в [аналізі](evidence/run-analysis.json), а не приховані під загальним PASS/FAIL.

Пілот v1 (47f27ca24364, [прогноз a301433](docs/forecast-before-runs.md)) дав false PASS:
240 і правильний код були лише серед кандидатів. У v2 додано L4 no-reconfirmation;
turns/oracle не змінювалися. Калібрування зроблено **після пілота, до повної серії**.
Raw v1 не переписано; replay його відповідей проти v2 позначено як нову offline-оцінку.
**У v2 також є false PASS:** H03 lesson-05, повтор 2. Агент просить вибрати транзакцію,
але формулювання «Tell me which TechMart charge» не потрапляє в L4 pattern.
Тому наведені PASS — нативні verdicts, не гарантія правильного binding. Raw і hash не змінювалися;
детальний розбір і межа застосування gate — в основному звіті.

## Вартість і межі доказів

390 chat requests у повній серії +14 пілотних = **404**; незалежних сесій **52**.
За trace spans — **{d['total_provider_calls_including_summaries']} provider calls**, включно зі згортками.
Root/chat usage: input **{usage['input_tokens']:,}**, output **{usage['output_tokens']:,}**;
зареєстрована стендом root cost **USD{d['chat_root_cost_usd']:.6f}**.
Summarizer usage і cache billing categories не записані в chat usage: це **не повний рахунок**.
Звірено за доступним балансом: USD17.57 → USD17.10, витрати ≈USD0.47.
[Джерело й межі звірки](evidence/billing-reconciliation.json): це не деталізований invoice.
Після пілота закладено запас USD2 із доступних USD17.57, не hard cap.
Платного judge немає; перевірки L2/L3/L4 і has_span.

Actual summary та tool/retrieval spans збережені. Повних raw provider messages немає:
inventory сутностей — реконструкція з записаних значень і перевіреного runtime loop.
Усі налаштування profile/defects, clock, summarize, retrieval відновлено.
Reset повертає БД до seed; довільний початковий стан БД не відновлюється.

## Перевірки

- Нативний dry-run на чистому клоні кіту пройшов.
- Offline unittest: 6/6; read-only preflight: 1/1; runtime provenance: 1/1.
- Live wrapper: обидва пілоти й обидві повні серії завершені; quality FAIL відокремлені від збою запуску.
- [Фінальні hashes/повнота/незмінність попередніх golden](evidence/artifact-checks.json).

Numeric/regex не гарантують правильну валюту, binding чи відсутність зайвих кандидатів;
L4 зменшує false confidence, але має власну межу точності.
"""
 save(ROOT/"README.md",readme)
 save(ROOT/"SUBMISSION.md","""# ДЗ №4 — артефакти

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
""")
 print("Built README and submission navigation")

if __name__=="__main__":main()

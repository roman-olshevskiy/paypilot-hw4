"""Build the six-section report only from completed full-run evidence."""
import json
import statistics
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def read(p):
    return json.loads(p.read_text(encoding="utf-8"))


def fmt(value):
    return "не спостерігався" if value is None else str(value)


def main():
    data=read(ROOT/"evidence/run-analysis.json")
    full={r["profile"]:r for r in data["runs"] if r["chat_requests"]==195}
    if set(full)!={"clean","lesson-05"}:
        raise RuntimeError("Both full reports are required; no invented results")
    clean,variant=full["clean"],full["lesson-05"]
    h01=[x for x in variant["repeats"] if x["case"]=="CONV-H01"]
    losses=[x["first_summary_without_amount_turn"] for x in h01
            if x["first_summary_without_amount_turn"] is not None]
    median=statistics.median(losses) if losses else None
    bounds=f"{min(losses)}–{max(losses)}" if losses else "не спостерігалося"
    rows=[]
    for cid in ["CONV-H01","CONV-H02","CONV-H03","CONV-H04","CONV-H05"]:
        cells=[]
        for run in [clean,variant]:
            reps=[x for x in run["repeats"] if x["case"]==cid]
            cells.append(f"{sum(x['v2_replay_passed'] for x in reps)}/{len(reps)}")
        firsts=[x["first_memory_fail_turn"] for x in variant["repeats"] if x["case"]==cid and x["first_memory_fail_turn"] is not None]
        cells.append(f"{min(firsts)}–{max(firsts)}" if firsts else "не виявлено")
        rows.append("| "+cid+" | "+" | ".join(cells)+" |")
    loss_rows="".join("| "+str(x["repeat"])+" | "+fmt(x["first_summary_without_amount_turn"])+
                      " | "+fmt(x["first_memory_fail_turn"])+" |"+chr(10) for x in h01)
    profile=[]
    source_rows=read(ROOT/variant["folder"]/"captures.json")
    representative=[x for x in source_rows if x["case"]=="CONV-H01" and x["run"]==1]
    h01rep=h01[0]
    for inv,row in zip(h01rep["derived_input_entity_inventory"],representative):
        sm=next((x for x in h01rep["summary_evidence"] if x["turn"]==row["turn"]),None)
        held=("240" if inv["amount_240_in_recorded_input_sources"] else "сума відсутня")
        held+=", "+(", ".join(inv["reason_literals_in_recorded_input_sources"]) or "canonical reason відсутній")
        lost=("summary без суми" if sm and not sm["amount_240_present"] else "нову втрату не встановлено")
        visible=("FAIL: "+", ".join(c["label"] for c in h01rep["checks"] if not c["passed"] and c["turn"]==row["turn"])
                 if any(not c["passed"] and c["turn"]==row["turn"] for c in h01rep["checks"])
                 else ("probe пройдено" if row["turn"] in [5,7] else "memory probe немає"))
        profile.append(f"| {row['turn']} | {held} | {lost} | "+
                       ("actual summary + поточний запит" if inv["summarized_now"] else "записані джерела історії + поточний запит")+
                       f" | {visible} |")
    comparative=[]
    for cid,length in [("CONV-H02",5),("CONV-H01",7),("CONV-H03",10)]:
        reps=[x for x in variant["repeats"] if x["case"]==cid]
        missing=sum(x["first_summary_without_amount_turn"] is not None for x in reps)
        failed=sum(not x["v2_replay_passed"] for x in reps)
        comparative.append(f"| {cid} | {length} | {missing}/5 | {failed}/5 |")
    summary_matrix=[]
    for r in [clean,variant]:
        summaries=[sm for x in r["repeats"] for sm in x["summary_evidence"]]
        summary_matrix.append(f"| {r['profile']} | {len(summaries)} | "+
            f"{sum(not x['amount_240_present'] for x in summaries)} | "+
            f"{sum(x['amount_180_present'] for x in summaries)} | "+
            f"{sum(x['correct_reason_literal_present'] for x in summaries)} | "+
            f"{sum(x['substituted_reason_literal_present'] for x in summaries)} |")
    failure_rows=[]
    for cid in ["CONV-H01","CONV-H02","CONV-H03","CONV-H04","CONV-H05"]:
        for label in ["dispute_amount_eur still holds","reason_code still holds","reason_code: no substitute","filing_window_days still holds"]:
            cells=[]
            for r in [clean,variant]:
                reps=[x for x in r["repeats"] if x["case"]==cid]
                failures=sum(any(c["label"]==label and not c["passed"] for c in x["checks"]) for x in reps)
                cells.append(f"{failures}/5")
            failure_rows.append("| "+cid+" | "+label+" | "+" | ".join(cells)+" |")
    drift_examples=[]
    for rep in variant["repeats"]:
        for sm in rep["summary_evidence"]:
            if sm["substituted_reason_literal_present"] or sm["amount_180_present"]:
                drift_examples.append(f"- {rep['case']}, повтор {rep['repeat']}, хід {sm['turn']}, request_id {sm['request_id']}: "+
                                      ("сума 180 замість 240; " if sm["amount_180_present"] else "")+
                                      ("service_not_rendered замість goods_not_received." if sm["substituted_reason_literal_present"] else ""))
    full_root_cost=sum(r["chat_root_cost_usd"] for r in [clean,variant])
    selected=next((x for x in h01 if x["first_memory_fail_turn"] is not None),h01[0])
    summary=next((s for s in selected["summary_evidence"] if not s["amount_240_present"]),None)
    appendix=["# Додатки — фактичні записи L05","","Повні транскрипти й traces збережені в reports/ і evidence/hw4-runs/.",
              "Таблиці нижче — похідний inventory сутностей, не дослівний raw provider input."]
    for run in [clean,variant]:
        rep=next(x for x in run["repeats"] if x["case"]=="CONV-H01" and x["repeat"]==1)
        folder=ROOT/run["folder"]
        captures=read(folder/"captures.json")
        part=[x for x in captures if x["case"]=="CONV-H01" and x["run"]==1]
        appendix+=["",f"## H01, {run['profile']}, повтор 1",
                   "| Хід | Сума 240 у джерелах входу | Reason literals у джерелах входу | Retrieval ids |",
                   "|---|---|---|---|"]
        for inv,row in zip(rep["derived_input_entity_inventory"],part):
            fragments=[]
            def visit(node):
                attrs=node.get("attributes",{})
                if node.get("name")=="tool.search_knowledge_base":
                    fragments.extend(f.get("id","") for f in (attrs.get("tool.result") or {}).get("fragments",[]))
                for child in node.get("children",[]):visit(child)
            visit(row["trace"])
            appendix.append(f"| {row['turn']} | {inv['amount_240_in_recorded_input_sources']} | "+
                            ", ".join(inv["reason_literals_in_recorded_input_sources"])+" | "+
                            (", ".join(fragments) or "пошуку немає")+" |")
        for s in rep["summary_evidence"]:
            appendix+=["",f"### Summary на ході {s['turn']}, request_id {s['request_id']}",
                       "~~~text",s["text"],"~~~"]
        for t in [1,2,5,7]:
            row=part[t-1]
            appendix+=["",f"### Відповідь на ході {t}, request_id {row['response']['request_id']}",
                       "~~~text",row["response"]["answer"],"~~~"]
    appendix+=["", "## Частка провалів кожного invariant",
               "Знаменник — п’ять діалогів; якщо probe кілька, діалог враховано один раз.",
               "| Кейс | Перевірка | Clean FAIL | Lesson-05 FAIL |",
               "|---|---|---|---|"]+failure_rows
    appendix+=["", "## Усі FAIL і нативні PASS lesson-05: джерела входу та відповіді",
               "Raw traces є джерелом summary/tool даних. Перелік нижче містить кожен FAIL повної серії, без вибіркового приховування clean."]
    for run in [clean,variant]:
        captures=read(ROOT/run["folder"]/"captures.json")
        for rep in run["repeats"]:
            if rep["v2_replay_passed"] and run["profile"]=="clean":continue
            appendix+=["",f"### {run['profile']} / {rep['case']} / повтор {rep['repeat']}"]
            part=[x for x in captures if x["case"]==rep["case"] and x["run"]==rep["repeat"]]
            for sm in rep["summary_evidence"]:
                appendix+=["",f"Summary, хід {sm['turn']}; request_id {sm['request_id']}", "~~~text",sm["text"],"~~~"]
            failedturns=sorted({c["turn"] for c in rep["checks"] if not c["passed"] and isinstance(c["turn"],int)})
            if rep["v2_replay_passed"]:
                appendix+=["", "Нативний PASS: перевірити binding за фактичним текстом; не прирівнювати його до збереженої пам’яті."]
                failedturns=sorted({c["turn"] for c in rep["checks"] if not c["label"].startswith("initial oracle") and isinstance(c["turn"],int)})
            for turn in failedturns:
                row=next(x for x in part if x["turn"]==turn)
                appendix+=["",f"Хід {turn}; request_id {row['response']['request_id']}",
                           "Перевірки: "+ "; ".join(c["label"]+": "+c["detail"] for c in rep["checks"] if not c["passed"] and c["turn"]==turn),
                           "~~~text", row["question"],"","ANSWER:",row["response"]["answer"],"~~~"]
                tooldata=[]
                def collect(node):
                    if node.get("name","").startswith("tool."):
                        a=node.get("attributes",{})
                        tooldata.append({"name":node["name"],"arguments":a.get("tool.arguments"),"result":a.get("tool.result")})
                    for child in node.get("children",[]):collect(child)
                collect(row["trace"])
                appendix+=["", "Tool/retrieval spans цього ходу (дослівні JSON-поля):","~~~json",
                           json.dumps(tooldata,ensure_ascii=False,indent=2),"~~~"]
    (ROOT/"docs/observed-evidence.md").write_bytes((chr(10).join(appendix)+chr(10)).encode("utf-8"))
    mechanism=("У фактичній summary відсутня сума 240; попередні turn/tool записи її містять. "
               "Заміна історії підтверджена summary.replaced_messages і перевіреним runtime loop."
               if summary else
               "Відсутність суми у summary для H01 не доведена; не приписуємо очікувану D06 факту.")
    report=f"""# Multi-turn Test Plan + Degradation Profile — PayPilot

Мандат **Ship it**. Власні вимірювання 2026-10-18 (Europe/Kiev).
[Докази та таблиці ходів](docs/observed-evidence.md), [машинний аналіз](evidence/run-analysis.json).

## 1. Контекст і прогноз

Локальний shared 86a22ea; оригінальний L05 kit d5e763d, без змін tracked runner/loader.
Модель за traces: {", ".join(clean["models"])}; провайдер Anthropic.
Профілі clean і lesson-05 (D06/D07), clock 2026-09-15T10:00:00Z, summarize_after=2.
П’ять memory-кейсів, п’ять повторів кожного на кожному профілі; hash d7ea1a1c292f.

C-07 конкретизовано для CUS-0004/TX-0401: EUR240, 2026-07-20, goods_not_received,
90 днів, deadline 2026-10-18. Це seed/engine oracle, не схематичні 120 днів із лекції.
Шаблон із CUS-0009/Nordwind не переносився на чужу транзакцію.

Прогноз v2 — [afbc11b](https://github.com/roman-olshevskiy/paypilot-hw4/commit/afbc11b13dfcb3bf34aaebe5b9b4f9146c98ab15):
clean має пройти, lesson-05 — дати failures після summary на ході 3.
Точний [прогноз](docs/forecast-v2-before-runs.md) і час коміту збережено до повної серії.
Пілот v1 зберігається окремо: його false PASS спричинив L4 guard у v2.

## 2. Профіль деградації

Clean: {clean["passed_cases"]}/5 кейсів повністю зелені; lesson-05: {variant["passed_cases"]}/5.
Тут кейс зелений, лише якщо пройшли всі його п’ять повторів.

| Кейс | Clean: нативних PASS | Lesson-05: нативних PASS | Перший FAIL lesson-05: діапазон |
|---|---|---|---|
{chr(10).join(rows)}

Для H01 крок втрати означає summary без вихідної суми, а крок прояву — першу провалену memory-перевірку.
Це різні вимірювання; oracle failures пораховані окремо.

| Повтор lesson-05 | Summary без 240 | Перший manifestation |
|---|---|---|
{loss_rows}

Спостережених втрат: {len(losses)}/5; діапазон {bounds}; медіана {fmt(median)}.
«Не спостерігався» не замінюється нулем.
Після першої згортки не довіряємо самій пам’яті без oracle/повторної перевірки:
це обмежене рішення для цих сценаріїв, моделі й порогу, не універсальна межа контексту.
Якщо крок втрати незмінний, не вигадуємо розкид із лекції: поріг зафіксовано.
Репрезентативний H01, lesson-05, повтор 1; «вхід» означає інвентар із записаних джерел, не raw provider messages:

| Хід | Що тримається в джерелах входу | Що втрачено | Що було на вході | Видно у відповіді |
|---|---|---|---|---|
{chr(10).join(profile)}

Порівняння довжини (та сама пара первинних сутностей і одне відволікання):

| Кейс | Ходів | Summary без суми | FAIL діалогів |
|---|---|---|---|
{chr(10).join(comparative)}

Summary завжди на ході 3: ця серія вимірює наслідки заданого порогу, а не природний token-limit.
Межа рішення — після двох user turns, перед згорткою на третьому; навіть п’ять ходів не гарантують утримання.
Дослівні summary, відповіді та записи кожного FAIL — у додатку.

## 3. Механізми збою

{mechanism}
[Runtime hashes](evidence/runtime-source-provenance.json) звірені тестом із запущеним контейнером.
Повні raw provider messages не записані: інвентар сутностей виведено з actual summary,
попередніх user/assistant/tool значень і відповідної логіки loop. Не видаємо його за дослівний model-input snapshot.

Фактичні summary повної серії:

| Профіль | Summary | Без 240 | Є 180 | Є goods not received (варіанти) | Є service not rendered (варіанти) |
|---|---|---|---|---|---|
{chr(10).join(summary_matrix)}

Пошук приймає underscore/пробіли/дефіси, тому фраза про недоставлені товари теж рахується; це не доказ збереженого canonical code.
Це ознаки pattern, а не автоматична семантична класифікація: 180 може бути в іншому контексті.
Приклади фактичного drift у summary (повні тексти — додаток):

{chr(10).join(drift_examples[:3]) or "У цій серії явного 180/canonical substitution у summary не спостерігалося."}

Для H01 lesson-05, повтор 2: на ході 1 — goods_not_received; у summary на ході 3 — service_not_rendered;
на ході 7 агент називає window саме для service_not_rendered. Це D07 поверх втрати binding (D06).
Вхід містить неправильний код уже до відповіді; це не висновок лише з тексту агента.
У повторі 3 summary містить 180 EUR; на ході 5 transactions повертає дві суми 240 EUR.
Агент помічає конфлікт, але не відновлює однозначну справу. Правильне число після refetch не означає відновлення binding.

Єдиний clean FAIL: H03/5/8. Summary правильно зберегла 240 і reason, але додала
«Same amount and merchant as TX-0401, so confirm which charge the customer means».
Агент повторив уточнення поряд із правильними значеннями. Це конфлікт binding/інструкції у summary,
а не доведена втрата числа чи canonical reason substitution.
Негативний L4 guard виявляє цей симптом; його мітка D07 не є незалежним доказом причини.
Дослівні докази кожного FAIL наведені в додатку, включно з clean.

Reason-code substitution доводиться лише там, де її видно в summary й відповідях.
Не оголошуємо кожне падіння незалежним D07: goods_not_received і service_not_rendered обидва мають 90 днів.
Підміна коду може не змінити window; правильне window не доводить збереження справи.
Дві репліки зі строком порівнюються за кожним повтором; якщо суперечності немає, це не «D07 знайдено».
Порожній retrieval на питанні про особисту суму не є доказом пошукового збою.
Читання transactions після згортки може повернути число, але два платежі EUR240 ще не дають правильного binding.

Контроль clean і H04 без відволікань показують відмінність поведінки, не ізольовані causal mutant-оцінки.
Повні per-repeat checks та summary evidence кожного сценарію — у run-analysis.json.

## 4. Інваріанти й оракули

Для всіх кейсів:

- сума EUR240: from_turn=1, L2, tolerance 0.01; oracle — seed TX-0401 на ході 1;
- reason goods_not_received: from_turn=1, L3 canonical pattern; oracle — явна скарга «goods never arrived» плюс допустимий reason у policy;
- window 90: from_turn=2, L2 exact integer; oracle — disputes.check на ході 2;
- незалежна перевірка deadline 2026-10-18 на фінальному ході;
- L4 на memory probes забороняє повторне уточнення вже заданої справи.
H05 додатково зберігає дату 2026-07-20 з ходу 1, L3; oracle — seed.

Probes: H01=5/7, H02=4/5, H03=8/10, H04=5/7, H05=5/8/10.
Кожен invariant має oracle_turn/oracle_by; точні поля — l05_dialogs.jsonl.
L05 нативно реалізує pattern як L3, а не L1 зі схематичної інструкції.
Окремі initial-oracle checks відхиляють діалог, який послідовно помиляється з першої відповіді.
Numeric/regex можуть пропустити mixed/candidate wording: пілот v1 це довів; L4 зменшує, але не усуває цей ризик.
**False PASS у v2 теж спостерігався:** H03 lesson-05, повтор 2, хід 8.
Відповідь заперечує можливість підтвердження, перелічує два платежі й просить «Tell me which TechMart charge»,
але містить 240 і goods_not_received. Поточний guard не охоплює таке формулювання.
Нативний PASS збережено в raw report; його не зараховуємо як доказ збереженої пам’яті.
Набір не змінювався під час серії. Для майбутнього CI потрібна окрема калібровка semantic/binding oracle,
новий hash і нова серія; поточний релізний кейс однаково FAIL через інші повтори.

## 5. Тест-план і ціна

Осі: довжина 5/7/10; первинні сутності 1/2/3; відволікання 0/1/2.
Похідні window/deadline не рахуються як нові незалежні сутності.
Повний добуток — 27 комбінацій; точна ціна з п’ятьма повторами:
5 × (5+7+10) × 3 × 3 = **990 chat requests на профіль**, 1980 на два.
Приблизні 945 із лекції не є нашим точним розрахунком.

Обрано H01 (7/2/1, основний), H02 (5/2/1, скорочення), H03 (10/2/1, подовження),
H04 (7/2/0, контроль теми), H05 (10/3/2, найгірший).
Одна змінна ізолюється H01/H02/H03 та H01/H04.
39 ходів ×5 = 195 на профіль, **390 у повній серії**; пілот — ще 14.
Це {data["total_provider_calls_including_summaries"]} фактичних provider calls з урахуванням summaries,
а не 404 виклики моделі.

Зареєстрована root/chat cost: full **USD{full_root_cost:.6f}**,
з пілотом **USD{data["chat_root_cost_usd"]:.6f}**.
Звірка за доступним балансом: USD17.57 → USD17.10, тобто ≈USD0.47; це узгоджується з root cost.
[Підтвердження](evidence/billing-reconciliation.json). Usage сумаризатора й cache-категорії окремо не архівовані;
різницю USD0.015061 не приписуємо конкретній категорії. Це звірка балансу, не деталізований invoice.
Бюджет після пілота: проекція root ≈USD0.47, запас USD2 із USD17.57; це не hard cap.
Повний dialog-набір пропонуємо запускати перед релізом; щодня лишається однокроковий golden ДЗ3 — 42 daily chat requests.
Оцінювання суддею не використовувалося. Стан профілю, clock, summarize та retrieval після серій відновлено.

## 6. Залишковий ризик і рішення

| Не покрито | Наслідок | Рішення і причина |
|---|---|---|
| 5 ходів / 1 сутність / 0 відволікань | Локальний короткий збій може лишитися невідомим | Прийняти в навчальному gate: нижчий ризик за наявні довші сценарії; не production гарантія |
| 10 / 3 / 1 | Не ізольовано конкуренцію третьої сутності від другого відволікання | Відкласти: додати перед калібруванням CI у L13 |
| 7 / 3 / 2 | Ранній drift при щільному контексті | Відкласти: пріоритет після вимірювання базових сценаріїв |
| Інша мова, повернення через добу, дві справи | Неправильний binding і контекст | Відкласти до розширення реалістичних діалогів |

Сліпа зона: узгоджено хибне значення ловить initial oracle, але правильне число в неправильному контексті може пройти.
Semantic/entity inventory спирається на записані поля, не на повний provider input.
Непідтверджений D07 або збій retrieval не оголошуємо доведеними за одним текстом.

Рекомендоване виправлення D06 — структуровані сутності справи поза summary з валідацією змін.
Ціна: реалізація та підтримка state schema, перевірка legitimate corrections/binding і додатковий контекст у токенах;
фактична ціна й latency виправлення ще не виміряні. У цьому ДЗ виправлення не впроваджено.
Підняття порогу витрачає більше історії; промпт «зберігай числа» лишає той самий стохастичний ризик.

**Останній рядок:** обміняли повноту комбінаторики на виміряне релізне покриття;
не робимо висновку про довільно довгі діалоги й не видаємо regex за семантичну гарантію;
змінимо рішення при новому критичному сценарії, зміні моделі/summary policy або розширенні CI.
"""
    (ROOT/"multi-turn-test-plan.md").write_bytes(report.encode("utf-8"))
    print("Built measured report and evidence appendix")


if __name__=="__main__":main()

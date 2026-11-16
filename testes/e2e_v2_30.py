"""Testes E2E (dados fictícios) da Escala Rotativa 5x2 v2.30.
Uso: python3 -I e2e.py <url> <pasta_capturas>
"""
import json, sys, time
from playwright.sync_api import sync_playwright

URL = sys.argv[1]
SHOTS = sys.argv[2]
results = []

def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""))

def emp(i, name, role, hours=40, tin="08:00", tout="18:00", brk=120):
    return {"id": f"e{i}", "name": name, "store": "Local", "role": role, "hours": hours, "days": 5,
            "in": tin, "out": tout, "break": brk}

def base_state(employees, open_days=None, minimum=None, extra=None):
    roles = sorted({e["role"] for e in employees})
    st = {"employees": employees, "roles": [{"name": r, "group": "individual"} for r in roles],
          "configs": {"Local": {"open": open_days or [True]*6 + [False], "minimum": minimum or {}, "maxOff": 0, "block": True}},
          "weeks": {}, "_savedAt": "2026-11-16T12:00:00.000Z"}
    if extra:
        st["configs"]["Local"].update(extra)
    return st

def load_state(page, st):
    page.goto(URL)
    page.evaluate("""async (st)=>{
      localStorage.clear(); localStorage.setItem('mundial_escalas_v2', JSON.stringify(st));
      await new Promise(r=>{const q=indexedDB.deleteDatabase('escala_rotativa_dados_local_2_8');q.onsuccess=q.onerror=q.onblocked=()=>r();});
    }""", st)
    page.reload()
    page.wait_for_timeout(400)

def generate(page, start, end):
    page.click('[data-tab="scale"]')
    page.fill('#periodStart', start)
    page.fill('#rangeEnd', end)
    page.click('#generatePeriod')
    page.wait_for_selector('#legalDisclaimer[open]', timeout=3000)
    page.click('#legalConfirm')
    page.wait_for_timeout(900)

def get_state(page):
    return page.evaluate("JSON.parse(localStorage.getItem('mundial_escalas_v2'))")

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path="/usr/bin/google-chrome", args=["--no-sandbox"])
    ctx = browser.new_context(viewport={"width": 1366, "height": 900}, locale="pt-BR", timezone_id="America/Sao_Paulo")
    page = ctx.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "favicon" not in (m.location or {}).get("url", "") else None)
    page.on("dialog", lambda d: d.accept())

    # --- Cenário A: loja seg–sáb, domingo fechado, 7 pessoas no modelo 40 h (8h–18h, 2h) ---
    team = [emp(1, "Ana Gerente", "Gerente"), emp(2, "Bruno Gerente", "Gerente"),
            emp(3, "Carla Caixa", "Caixa"), emp(4, "Diego Caixa", "Caixa"),
            emp(5, "Eva Vendas", "Vendedor"), emp(6, "Fábio Vendas", "Vendedor"), emp(7, "Gil Vendas", "Vendedor")]
    st = base_state(team, minimum={"Gerente": 1, "Caixa": 1, "Vendedor": 1})
    st["specialDays"] = {"2026-12-24": "Véspera de Natal", "2026-12-26": "Balanço"}
    st["specialModes"] = {"2026-12-24": "all", "2026-12-26": "none"}
    load_state(page, st)
    check("A0 página carrega sem erros de JS", not errors, "; ".join(errors[:3]))
    check("A0 versão 2.30 no título", "2.30" in page.title())
    banner = page.inner_text('#legalBanner')
    check("A0 banner legal mostra 44 h hoje e 42 h em 16/12/2026", "44 h" in banner and "16/12/2026" in banner, banner[:140])
    page.screenshot(path=f"{SHOTS}/desktop_equipe.png", full_page=False)

    t0 = time.time()
    generate(page, "01/12/2026", "31/01/2027")
    gen_ms = (time.time() - t0) * 1000
    saved = get_state(page)
    weeks = {k: w for k, w in saved["weeks"].items()}
    check("A1 período dez/26–jan/27 gerado e salvo", len(weeks) >= 9, f"{len(weeks)} semanas, {gen_ms:.0f} ms (inclui espera fixa)")
    issues = [i for w in weeks.values() for i in (w.get("issues") or [])]
    check("A1 nenhuma semana salva com bloqueio", not issues, "; ".join(issues[:3]))
    # 5 dias de expediente (T+H) e 2 folgas (F) por pessoa/semana
    bad = []
    for w in weeks.values():
        for e in team:
            row = w["rows"][e["id"]]
            if row.count("F") != 2 or row.count("T") + row.count("H") != 5:
                bad.append((w["week"], e["name"], "".join(row)))
            if row[6] != "F":
                bad.append((w["week"], e["name"], "domingo não é folga"))
    check("A2 todos com 5 dias (T+H) e 2 folgas próprias (F), domingo fechado", not bad, str(bad[:3]))
    w2112 = weeks.get("Local|2026-12-21")
    if w2112:
        thu = [w2112["rows"][e["id"]][3] for e in team]  # 24/12 quinta
        fri = [w2112["rows"][e["id"]][4] for e in team]  # 25/12 sexta (Natal)
        sat = [w2112["rows"][e["id"]][5] for e in team]  # 26/12 sábado (ninguém trabalha)
        check("A3 24/12 todos trabalham", all(v == "T" for v in thu), "".join(thu))
        check("A3 25/12 Natal sem expediente (H ou F)", all(v in "HF" for v in fri), "".join(fri))
        check("A3 26/12 ninguém trabalha", all(v in "HF" for v in sat), "".join(sat))
    check("A3 01/12 sem marcação indevida", "2026-12-01" not in (saved.get("specialModes") or {}))
    page.screenshot(path=f"{SHOTS}/desktop_calendario.png", full_page=False)

    # Cabeçalho do calendário e caixa de planejamento (CSS antes descartado)
    border = page.evaluate("getComputedStyle(document.getElementById('monthPlanningNotice')).borderTopStyle")
    check("A4 estilo da caixa de planejamento aplicado (CSS corrigido)", border == "solid", border)

    # Aba de conformidade
    page.click('[data-tab="rules"]')
    page.wait_for_timeout(200)
    diag = page.inner_text('#transitionDiagnostic')
    check("A5 diagnóstico: 7/7 prontos para 16/12/2026 e 16/12/2027", diag.count("7/7") >= 2, diag[:200])
    page.screenshot(path=f"{SHOTS}/desktop_conformidade.png", full_page=True)

    # Semana na escala inteligente mostra etapa legal
    page.evaluate("setSelectedDate('2026-12-21');showTab('scale')")
    page.wait_for_timeout(200)
    alerts = page.inner_text('#alerts')
    check("A6 semana 21/12/2026 indica etapa de transição (42 h)", "Transição" in alerts and "42 h" in alerts, alerts[:160])
    page.screenshot(path=f"{SHOTS}/desktop_escala.png", full_page=False)

    # --- Cenário B: contrato de 44 h (8h48/dia) ---
    errors.clear()
    team_b = [emp(i, f"Pessoa {i}", "Vendedor", hours=44, brk=72) for i in range(1, 6)]
    load_state(page, base_state(team_b))
    generate(page, "02/11/2026", "29/11/2026")
    sb = get_state(page)
    check("B1 novembro/2026 (regra de 44 h) é gerado", len(sb["weeks"]) == 4, f"{len(sb['weeks'])} semanas")
    page.evaluate("setSelectedDate('2026-11-09');showTab('scale')")
    page.wait_for_timeout(200)
    check("B1 8h48/dia gera alerta de compensação (não bloqueio)", "acordo de compensação" in page.inner_text('#alerts'))
    generate(page, "14/12/2026", "27/12/2026")
    msg = page.inner_text('#periodNotice')
    sb2 = get_state(page)
    check("B2 dezembro após 16/12 é BLOQUEADO para 44 h", "NÃO SALVO" in msg and "Local|2026-12-14" not in sb2["weeks"], msg[:200])
    page.click('[data-tab="rules"]')
    page.wait_for_timeout(150)
    check("B3 diagnóstico aponta ajuste para 42 h e 40 h", "0/5" in page.inner_text('#transitionDiagnostic'))
    check("B  sem erros de JS", not errors, "; ".join(errors[:3]))

    # --- Cenário C: loja aberta 7 dias, regra do domingo (1 a cada 3 semanas) ---
    errors.clear()
    team_c = [emp(i, f"Colab {i}", "Vendedor") for i in range(1, 9)]
    load_state(page, base_state(team_c, open_days=[True]*7, minimum={"Vendedor": 5}))
    generate(page, "07/12/2026", "28/02/2027")
    sc = get_state(page)
    wk = sorted(sc["weeks"].values(), key=lambda w: w["week"])
    check("C1 12 semanas geradas com loja aberta 7 dias", len(wk) >= 12 and not any(w.get("issues") for w in wk), f"{len(wk)} semanas")
    worst = 0
    for e in team_c:
        streak = 0
        for w in wk:
            if w["rows"][e["id"]][6] == "T":
                streak += 1; worst = max(worst, streak)
            else:
                streak = 0
    check("C2 ninguém trabalha 3 domingos seguidos", worst <= 2, f"maior sequência = {worst}")
    # Regra quinzenal: com 8 pessoas são necessárias 4 folgas por domingo (mínimo de 4 em serviço)
    st_c2 = base_state(team_c, open_days=[True]*7, minimum={"Vendedor": 4})
    load_state(page, st_c2)
    page.click('[data-tab="rules"]')
    page.select_option('#sundayRuleSetting', '2')
    page.click('#saveLegalSettings')
    page.wait_for_timeout(500)
    generate(page, "07/12/2026", "28/02/2027")
    wk2 = sorted(get_state(page)["weeks"].values(), key=lambda w: w["week"])
    worst2 = 0
    for e in team_c:
        streak = 0
        for w in wk2:
            if w["rows"][e["id"]][6] == "T":
                streak += 1; worst2 = max(worst2, streak)
            else:
                streak = 0
    ok_issues = not any(w.get("issues") for w in wk2)
    check("C3 regra quinzenal: no máximo 1 domingo seguido trabalhado", len(wk2) >= 12 and worst2 <= 1 and ok_issues, f"maior sequência = {worst2}")
    # Quinzenal com só 3 vagas por domingo deve ser recusado (inviável)
    load_state(page, base_state(team_c, open_days=[True]*7, minimum={"Vendedor": 5}, extra={"sundayRuleWeeks": 2}))
    generate(page, "07/12/2026", "28/02/2027")
    check("C4 regra quinzenal inviável (3 vagas/domingo para 8 pessoas) não é salva", "NÃO SALVO" in page.inner_text('#periodNotice'))
    check("C  sem erros de JS", not errors, "; ".join(errors[:3]))

    # --- Cenário D: data especial salva na data digitada (regressão 26/12 → 01/12) ---
    errors.clear()
    load_state(page, base_state(team))
    page.click('[data-tab="month"]')
    page.fill('#monthSpecialDate', '26/12/2026')
    page.dispatch_event('#monthSpecialDate', 'change')
    page.fill('#monthSpecialName', 'Balanço')
    page.select_option('#monthSpecialMode', 'none')
    page.click('#saveSpecialDate')
    page.wait_for_timeout(400)
    sd = get_state(page)
    check("D1 26/12/2026 salvo como NINGUÉM TRABALHA", (sd.get("specialModes") or {}).get("2026-12-26") == "none")
    check("D1 01/12/2026 não recebeu marcação", "2026-12-01" not in (sd.get("specialModes") or {}))
    page.reload(); page.wait_for_timeout(400)
    sd2 = get_state(page)
    check("D2 marcação sobrevive à recarga", (sd2.get("specialModes") or {}).get("2026-12-26") == "none")
    check("D  sem erros de JS", not errors, "; ".join(errors[:3]))

    # --- Cenário E: XSS em nome de cargo ---
    errors.clear()
    xss = [emp(1, "<img src=x onerror=window.__x=1>", "<b onmouseover=1>Cargo</b>"), emp(2, "Outro", "<b onmouseover=1>Cargo</b>")]
    st_x = base_state(xss, minimum={"<b onmouseover=1>Cargo</b>": 1})
    load_state(page, st_x)
    generate(page, "07/12/2026", "13/12/2026")
    page.evaluate("setSelectedDate('2026-12-07');showTab('scale')")
    page.wait_for_timeout(200)
    injected = page.evaluate("document.querySelectorAll('#coverage b, #scheduleBody img, #rosterBody img').length + (window.__x?1:0)")
    check("E1 nomes/cargos com HTML são exibidos como texto", injected == 0, f"{injected} elemento(s) injetado(s)")

    # --- Desempenho: 250 pessoas, 3 meses ---
    errors.clear()
    big = [emp(i, f"Func {i}", ["Gerente", "Caixa", "Vendedor", "Estoque"][i % 4]) for i in range(1, 251)]
    load_state(page, base_state(big, minimum={"Gerente": 20, "Caixa": 20, "Vendedor": 20, "Estoque": 20}))
    t0 = time.time()
    page.click('[data-tab="scale"]')
    page.fill('#periodStart', '01/12/2026'); page.fill('#rangeEnd', '28/02/2027')
    page.click('#generatePeriod'); page.wait_for_selector('#legalDisclaimer[open]'); page.click('#legalConfirm')
    page.wait_for_function("document.querySelector('#monthActionStatus').innerText.length>0 || document.querySelector('#periodNotice').innerText.includes('NÃO')", timeout=120000)
    perf = (time.time() - t0)
    nweeks = len(get_state(page)["weeks"])
    check("P1 250 funcionários × 3 meses gerados", nweeks >= 13, f"{nweeks} semanas em {perf:.1f} s (geração + calendário)")
    t1 = time.time(); page.evaluate("drawMonth()"); draw_s = time.time() - t1
    check("P2 redesenho do calendário com 250 pessoas < 3 s", draw_s < 3, f"{draw_s:.2f} s")
    check("P  sem erros de JS", not errors, "; ".join(errors[:3]))

    # --- Capturas responsivas (cenário A) ---
    load_state(page, st)
    generate(page, "01/12/2026", "31/12/2026")
    for w, h, tag in [(375, 812, "iphone"), (768, 1024, "tablet"), (1440, 900, "pc")]:
        page.set_viewport_size({"width": w, "height": h})
        for tab in ["team", "scale", "month", "rules"]:
            page.click(f'[data-tab="{tab}"]')
            if tab == "scale":
                page.evaluate("setSelectedDate('2026-12-21');loadWeek()")
            page.wait_for_timeout(150)
            page.screenshot(path=f"{SHOTS}/{tag}_{tab}.png", full_page=(tab != "month"))
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        check(f"R {tag}: sem rolagem horizontal da página", overflow <= 1, f"excesso {overflow}px")

    browser.close()

passed = sum(1 for r in results if r[1])
print(f"\n{passed}/{len(results)} verificações aprovadas")
json.dump([{"teste": n, "ok": o, "detalhe": d} for n, o, d in results], open(f"{SHOTS}/resultados.json", "w"), ensure_ascii=False, indent=1)

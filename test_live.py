from playwright.sync_api import sync_playwright

URL = "https://u235xuxu.github.io/single-file-exam-engine/examples/demo.html"

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome",
                          proxy={"server": "http://127.0.0.1:7897"})
    pg = b.new_page(viewport={"width": 900, "height": 1200})
    errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL, wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_selector(".card", timeout=30000)
    n = len(pg.query_selector_all(".card"))
    print("线上渲染题数:", n)
    print("标题:", pg.title())

    c = pg.query_selector_all(".card")
    c[0].query_selector_all(".opt")[1].click()
    for o in c[1].query_selector_all(".opt"): o.click()
    c[2].query_selector_all(".opt")[1].click()
    c[3].query_selector_all(".opt")[2].click()
    c[4].query_selector("input.fill").fill("924")
    c[5].query_selector_all(".opt")[0].click()
    for i in range(3): c[6].query_selector_all(".opt")[i].click()
    c[7].query_selector_all(".opt")[0].click()
    c[8].query_selector("input.fill").fill("2")
    c[9].query_selector("textarea.fill").fill("调整事项是期末已存在")

    print("进度:", pg.query_selector("#progress").inner_text())
    pg.click("#btnSubmit")
    pg.wait_for_selector(".score .num", timeout=15000)
    print("得分:", pg.query_selector(".score .num").inner_text().strip())
    print("结论:", pg.query_selector(".score .lbl").inner_text().strip())
    print("JS错误:", errs if errs else "无")
    pg.screenshot(path="/tmp/live_demo.png")
    b.close()

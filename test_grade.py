from pathlib import Path
from playwright.sync_api import sync_playwright

HTML = Path.home() / "projects/single-file-exam-engine/examples/demo.html"
EXPECT = {0:"ok",1:"ok",2:"ok",3:"ok",4:"ok",5:"no",6:"ok",7:"no",8:"ok",9:"ok"}

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    pg = b.new_page(viewport={"width":900,"height":1200})
    pg.goto("file://" + str(HTML))
    pg.wait_for_selector(".card")
    c = pg.query_selector_all(".card")
    c[0].query_selector_all(".opt")[1].click()
    for o in c[1].query_selector_all(".opt"): o.click()
    c[2].query_selector_all(".opt")[1].click()
    c[3].query_selector_all(".opt")[2].click()
    c[4].query_selector("input.fill").fill("924")
    c[5].query_selector_all(".opt")[0].click()      # 故意错
    for i in range(3): c[6].query_selector_all(".opt")[i].click()
    c[7].query_selector_all(".opt")[0].click()      # 故意错
    c[8].query_selector("input.fill").fill("2")
    c[9].query_selector("textarea.fill").fill("调整事项是期末已存在")
    pg.click("#btnSubmit")
    pg.wait_for_selector(".score .num")

    print("得分:", pg.query_selector(".score .num").inner_text().strip())
    res = pg.evaluate("""() => {
      return [...document.querySelectorAll('.explain')].map(e => {
        const cls = e.className.replace('explain','').trim();
        const v = e.querySelector('.verdict');
        return cls + ' | ' + (v ? v.textContent.trim() : '');
      });
    }""")
    allok = True
    for i, line in enumerate(res):
        cls = line.split("|")[0].strip()
        exp = EXPECT.get(i,"?")
        ok = cls == exp
        allok &= ok
        print(f"  Q{i+1:<3} 判定={cls:<6} 期望={exp:<6} {'OK' if ok else '★不符'}  {line.split('|')[1].strip()}")
    print("\n全部符合预期:", allok)

    # 检查选项颜色
    col = pg.evaluate("""() => {
      const c0 = document.querySelectorAll('.card')[0];
      return [...c0.querySelectorAll('.opt')].map(o =>
        o.classList.contains('right') ? 'right' :
        o.classList.contains('wrong') ? 'wrong' : 'plain');
    }""")
    print("Q1选项颜色[应=B绿其余无]:", col)
    b.close()

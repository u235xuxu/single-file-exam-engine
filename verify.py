import re, json, sys
s = open('examples/demo.html', encoding='utf-8').read()
m = re.search(r'<script type="application/json" id="bank">(.*?)</script>', s, re.S)
if not m:
    print("FAIL: 找不到数据块"); sys.exit(1)
d = json.loads(m.group(1))
print("JSON题数:", len(d['questions']))
print("标题:", d['meta']['title'])
print("HTML大小:", len(s), "字节")
q0 = d['questions'][0]
print("Q1类型:", q0['type'], "| 答案:", q0['answer'], "| 选项数:", len(q0['options']))
print("Q2(多选)答案:", d['questions'][1]['answer'])
print("Q3(判断)答案:", d['questions'][2]['answer'])
print("Q5(填空)accept:", d['questions'][4]['accept'])
print("Q10(简答)keywords:", d['questions'][9]['keywords'])
# 确认模板占位符已被替换
for bad in ['/*__DATA__*/', '/*__TITLE__*/']:
    if bad in s:
        print("FAIL: 占位符未替换", bad); sys.exit(1)
print("占位符替换: OK")
# 确认无外部资源引用
ext = re.findall(r'(?:src|href)=["\'](?!#)([^"\']+)', s)
print("外部资源引用:", ext if ext else "无（完全自包含）")

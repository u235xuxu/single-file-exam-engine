# single-file-exam-engine

**一份题库 → 一个 HTML 文件。双击就考，不装东西，不连网。**

A question bank goes in, a single self-contained HTML exam comes out. No server, no CDN, no build chain, no dependencies.

```
python3 build.py bank.yaml
→ bank.html   ← 这就是全部产物，发给任何人都能直接打开
```

---

## 为什么做这个

备考资料的形态通常很糟：一大堆 PDF、一堆网页标签、知识点东一块西一块。想做一套能真正练手的东西，要么用在线题库（要账号、要联网、题目不是你的），要么自己写页面（写十套题等于写十遍前端）。

**这个项目只干一件事：把「题库」和「考试界面」解耦。**

- 你只管写题（YAML / JSON，纯文本）
- 界面由引擎负责（一次写好，无限复用）
- 产物是**一个 HTML 文件**——离线、可邮件发送、可放 U 盘、可挂任何静态托管

---

## 特性

| | |
|---|---|
| **单文件产物** | 一个 `.html`，零外部资源。断网可用，无 CDN 依赖 |
| **五种题型** | 单选 / 多选 / 判断 / 填空 / 简答 |
| **即时判分** | 交卷后逐题标出对错，附解析 |
| **计时与进度** | 顶部进度条 + 计时器 |
| **智能判分** | 填空支持多答案、忽略空格与标点、百分号按数值比较；简答按关键词命中率判定 |
| **深浅色自适应** | 跟随系统主题 |
| **移动端** | 单栏布局，适配手机 |
| **零依赖** | Python 3.8+ 标准库，不用装任何包（自带极简 YAML 解析器） |

---

## 快速开始

```bash
git clone <this-repo>
cd single-file-exam-engine

# 用自己的题库生成
python3 build.py examples/demo.yaml

# 指定输出名
python3 build.py mybank.json -o 期末复习.html

# 只校验题库，不生成
python3 build.py mybank.yaml --check
```

然后双击生成的 `.html`。

---

## 题库格式

写 YAML（也支持 JSON，两种解析出来的结构一样）：

```yaml
meta:
  title: 期末复习 · 第一章
  pass_score: 60

questions:
  - type: 单选
    q: 题干写在这里，支持换行和「」等中文标点。
    options:
      - "选项 A"
      - "选项 B"
      - "选项 C"
      - "选项 D"
    answer: B                    # 也可以写 1 / [1]
    explain: |
      解析写在这里。
      多行可以用 | 块。

  - type: 多选
    q: 下列哪些正确？
    options: ["甲", "乙", "丙", "丁"]
    answer: [A, B]               # 也可写 [0, 1]

  - type: 判断
    q: 这句话是对的。
    answer: 错                    # 对/错、true/false、√/× 都认
    explain: 为什么错。

  - type: 填空
    q: 计算结果为 ____。
    accept: ["42", "42.0"]        # 多个可接受答案
    case_sensitive: false         # 默认忽略大小写

  - type: 简答
    q: 简述两者的区别。
    keywords: ["关键点一", "关键点二", "关键点三"]
    reference: |
      参考答案。命中一半以上关键词判为正确。
```

### 题型别名

`type` 字段中文英文都认，不想记就用最顺手的那个：

| 规范值 | 可用别名 |
|---|---|
| `single` | 单选、radio、choice |
| `multiple` | 多选、multi、checkbox |
| `judge` | 判断、bool、truefalse |
| `fill` | 填空、blank |
| `short` | 简答、essay、subjective |

### 答案是这么写的

| 题型 | 写法 |
|---|---|
| 单选 | `answer: B` / `answer: 2` / `answer: [1]` |
| 多选 | `answer: [A, C]` / `answer: [0, 2]` |
| 判断 | `answer: 对` / `answer: false` / `answer: √` |
| 填空 | `accept: ["答案1", "答案2"]` |
| 简答 | `keywords: [...]` + `reference: ...` |

---

## 判分规则

| 题型 | 规则 |
|---|---|
| 单选 / 多选 | 选项集合完全一致才算对（多选少选都不给分） |
| 判断 | 精确匹配 |
| 填空 | 忽略空格、全半角标点、大小写；带 `%` 的按数值比较（`20` 与 `20%` 视作相同） |
| 简答 | 关键词命中率达到 50% 判对；没有 `keywords` 则标记为「需自评」，不参与自动计分 |

每题默认 1 分，可在题目里用 `score:` 单独指定。

---

## 验证

本仓库的判分逻辑经过真实浏览器（Playwright + Chrome）端到端验证：

```bash
python3 -m pip install playwright
python3 test_grade.py
```

测试流程：打开生成的 HTML → 逐题模拟点击/填写 → 交卷 → 断言每题判定结果与预期一致。

```
得分: 70分
  Q1  判定=ok  期望=ok   ✓ 正确
  Q2  判定=ok  期望=ok   ✓ 正确
  Q3  判定=ok  期望=ok   ✓ 正确
  Q4  判定=ok  期望=ok   ✓ 正确
  Q5  判定=ok  期望=ok   ✓ 正确
  Q6  判定=no  期望=no   ✕ 错误      ← 故意答错，验证能正确识别
  Q7  判定=ok  期望=ok   ✓ 正确
  Q8  判定=no  期望=no   ✕ 错误      ← 故意答错
  Q9  判定=ok  期望=ok   ✓ 正确
  Q10 判定=ok  期望=ok   ✓ 正确
全部符合预期: True
```

另一支校验脚本 `verify.py` 检查产物完整性：数据块可解析、占位符已替换、**无任何外部资源引用**。

---

## 它能做什么，不能做什么

**能做：** 个人自测、小班教学、企业培训测验、任何「有一批题想让人能练」的场景。

**不做：**
- **不管考试安全**——答案就写在 HTML 源码里，懂技术的用户按 F12 就能看到。这是刻意的取舍：单文件、离线的代价就是无法防作弊。需要防作弊请用带后端的方案。
- **不做成绩汇总**——没有服务端，交卷结果只在页面里，刷新即失。
- **不做题库编辑界面**——题在文本文件里改，这是故意的，纯文本能进 git、能 diff、能被脚本处理。

---

## 目录

```
build.py           题库 → HTML 的唯一入口
template.html      考试界面（构建时把数据注入这里）
verify.py          产物完整性校验
test_grade.py      端到端判分测试（Playwright）
examples/
  demo.yaml        示例题库
  demo.html        构建产物（可直接双击体验）
```

---

## License

MIT

---

## 在线试玩

不想 clone 也能直接考：[**u235xuxu.github.io/single-file-exam-engine/examples/demo.html**](https://u235xuxu.github.io/single-file-exam-engine/examples/demo.html)

源码与文档：[github.com/u235xuxu/single-file-exam-engine](https://github.com/u235xuxu/single-file-exam-engine)

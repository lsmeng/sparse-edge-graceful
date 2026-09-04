# 独立审计报告：sparse_edge_graceful(奇数阶树、D 个二度顶点的 edge-graceful 标号)

审计日期：2026-09-03。审计对象:`paper/sparse_edge_graceful.tex`(Draft of 5 September 2026)及
`research/antimagic/` 下的代码与数据。审计原则：不信任任何作者自撰 .md 笔记的结论；只信论文正文、
代码实际运行结果、审计员自己的推导与重算。

---

## 一、逐项结论

### 1. 定理 1.1 是否只依赖 MP 已印出的定理 —— **基本通过，但依赖链上有一环(lemm:dense)自身有缺口**

依赖链(我完整追过):

1. 树的分解与计数引理(§2–3，初等，手证可查);
2. 上下文完备性 Lemma C(附录 A + 调度器回归，见第 2 项);
3. 有限证书目录(每个族是若干参数的有理恒等式，独立检查器验证，见第 6 项);
4. realization 引理(附录 B，手写证明，常数 A=2·10⁸ 显式，见第 3 项);
5. **稠密补全 lem:dense**(§5,调用 MP Lemma 6.24)→ 定理 1.1/1.2。

MP 已印出部分确实足以给出 polylog 阈值：Theorem 4.3 的扰动半径是 q^17 p^10 n/log^{1/10} n 量级、
Theorem 5.11(Gallagher)给出 t ≤ 10 log n、Lemma 6.24(abelian, k∈{3,4,5}, p=1 时 R=G)原文我逐条核对无误。
§7.4 那条 remark(log 可去掉)**没有**偷偷进入定理 1.1：定理 1.1 的 polylog 因子来自已印出的 5.11;
定理 1.2 明确以该 remark 为条件，措辞诚实。✓

**但是** lem:dense 的证明本身有实质缺口(见"严重问题"第 1 条)，它同时是定理 1.1 和 1.2 的必经环节。

### 2. 附录 A(引理 C)分情形是否穷尽 —— **有问题(陈述几乎肯定为真，正文证明未覆盖全部情形)**

- 附录 Step 2 的例外条款只写了 "exactly two active children are present, both kept"。对 **k≥3** 个活跃孩子、
  无 port、残差 {1} 或 {2} 且无可保留 neutral unit 的构型，附录规则会把孩子全部抵消，然后 Step 4 要求
  "retain one neutral unit"，其理由是 "One unit exists in each case because v has at least two children"——
  该理由在此构型下不成立(被取消的孩子不提供 arm/unit)。调度器实际用 `_act2_trigger` +
  `_reduce_odd_k_to_one`(k 奇留一)/ `_resolve_act2`(留二)处理这些情形，**论文正文没有写出这些规则**。
- 我用调度器直接探测:k=2,3,4,5、arm=(1)、h=1 分别给出 h1_1_p0_act2 / h1_1_p0_act / act2 / act,
  均在目录中；k=3, h=0, arm=(1) → L1 passthrough;k=3, arm=(2), h=0 → 刚性行 h0_2_p0_act;
  k=2 两个 L1 孩子 → v 变 stationary;k=2 两个 V22 → h1_4_p0_act2。**代码覆盖，论文文字未覆盖。**
- 抽象枚举脚本 `enumerate_emittable_contexts.py` 用 `multisets(CHILD_TYPES, max_children=2)`,
  即活跃孩子**总数** ≤ 2；论文 472 行写 "up to two active children of each of the possible types"
  (9 种类型各两个),**两者不符**。因此 k≥3 的抽象状态从未被穷举，只有 ≤9 阶全树
  (注意:≤9 阶树根本不存在 k≥3 的 owner——含 3 个 owner 孩子的最小树有 10 个顶点)
  和 3,500 棵随机树的经验性覆盖。
- 官方回归入口 `context_scheduler.py --all 5` 我重跑通过(125 棵标记树, 0 uncovered, 0 missing)。
- 附带发现(工具鲁棒性，不影响已跑回归):公开入口 `schedule()` 经 `tree_from_parent` 强制顶点 0 为根，
  当顶点 0 是叶子时可崩溃(最小反例 parent=[-1,0,1,2,3,3],`_reduce_odd_k_to_one([])` 抛 IndexError)。
  回归入口 `run_all_mode` 与构造器分别用 `root_from_edges` / `choose_root_candidates` 正确选根，不受影响。

### 3. 附录 B 记账(|S| ≤ 12D+3、幅度 ≤ A(D+1)、常数 A)—— **通过**

独立重算:W=29,M=lcm(1,2,3,4,6,12,24)=24 ✓;coord_lin=36·29·24=25,056;
coord_con=24·(58+841+1)=21,600;pair_lin=108·29·24=75,168;pair_con=24·(9·841+1)=181,680;
amax=7·64·256,848=115,067,904 → A=2·10⁸,与附录 B 文本中的公式逐项吻合，与 numbers.tex 一致。
|S| 与幅度界的手工推导我重推一遍，无出入。

### 4. 第 7 节 Proposition 三情形 —— **通过**

恒等情形(s∈{0,1},t≤59;且 s∉{0,1} 时确实失败)、端点旋转(t 奇 ≤59)、复合定理(a∈{3,5},b≤6
共 72 个实例)全部手工重推 + 数值验证成立。复合定理的窗口条件 u+σ(u)∈[-(q+1), 2b-q-2]、
反射常数 c=a(2b-2q-1)-2、s'=q+1、s=a(s'-1)+(a+1)/2 均与我的独立推导吻合。

### 5. closure_check —— **通过(有保留)**

带 `--gate` 运行:ALL CONDITIONS PASS(C1 2784/2784;C2 542/542;C3 1/1;C4 40/40,39 by xall + 29 by
port joint;C6:1973 个可实现失败对中 53 个可实现、全部 child=h2_1_p0_act2,即被吸收规则覆盖)。
gate 文件由 `check_lookahead_gate.py --menu` 生成(1973 对，与 \NumGateFail 一致)。
保留意见:(a) 论文 765–769 行列出的是**四个**条件，脚本有 C1–C6，其中 C5 只报告不检查、
C6 在不带 `--gate` 时被跳过却仍打印 "ALL CONDITIONS PASS"——默认运行的结论偏强;
(b) 脚本从 `run_alphabet_batch` import `key` 函数，与批处理代码存在少量共享，"闭包检查" 的独立性
弱于检查器;(c) 该脚本编码的是作者对 8d 规则的理解，本身不构成独立验证——这一点用户提示得对，
我对照论文 8d 文字逐条核过,C1–C4+C6 确实覆盖了论文列出的全部吸收前提，未发现漏检的规则。

### 6. check_alphabet_families —— **通过(有保留)**

- 重跑：`summary: 12740 total, 12740 PASS, 0 FAIL, 0 SKIP`(当前数据；与论文宏值 12,743 差 3，见第 7 项)。
  检查器确实遍历每个 context 的整个 menu(代码 784–798 行明确如此),不是只查首选族。
- 变体目录我另行驱动检查器的 Rebuilt/run_checks 复验:xtok 2,587 + xall 2,167 全过
  (\NumVariantFamilies=2,587 ✓)。
- 检查器只 import 标准库，与搜索程序(CP-SAT 建模)**无共享代码** ✓。
- 验证集合是论文的 (E1)–(E5) + 三个随机整数点数值恒等；**(E6) 清洁性不在检查器内**,论文也只声称
  验 (E1)–(E5)，一致。未查的性质:E4 中 "carrier 被记录且在 carrier 上秩 2" 依赖目录里的
  token_jacobian 字段，该字段由 `assemble_alphabet_catalogue.py` 算出，而 assembler 本身未经过独立检查
  ——即目录元数据的这一层是信任链上的薄弱环节(轻微)。
- "对六标号/十二标号插入后的族也复验"(论文 743–744 行)我没有找到并运行对应的端到端脚本
  (scripts 里有若干 route_core_*_insertion 检查脚本，未逐一核对是否即此),**此项无法判断**。

### 7. 论文数字的可再生性 —— **有问题(轻微~中等)**

`paper_numbers.py --gate … --paper <临时目录>` 重跑:catalogue_table.tex、blocks_table.tex 与论文逐字节一致;
**numbers.tex 有两个宏对不上**:
- \NumCatFamilies：论文 12,743,当前数据+当前代码得 **12,740**(我直接数 JSON:5716 contexts、menu 总数 12,740);
- \NumEmittableFamilies：论文 6,677，重算 **6,673**。

即论文 numbers.tex 相对于当前 checkout 的 catalogue 滞后 3 个族(目录在生成 numbers.tex 之后又被微调过,
或本地 checkout 与 Zenodo 归档不一致——归档内容我未下载核对)。检查器在当前数据上 12,740/12,740 全过，
所以"全部族通过"这一实质结论成立，只是篇内数字与当前数据差 3。其余数字
(NumEmittable=2784、gate 1973/53、pairs 11511、A=2·10⁸、构造器 98/120 与 116/120)全部复现 ✓:
构造器默认模式 116/120、proof-faithful 模式 98/120，失败签名 14 modular + 7 blocks + 1 bridge 与论文精确吻合。

### 8. 诚实性(有界不可行 vs 不可能；计算验证 vs 已证明)—— **整体诚实，三处措辞需修**

正面：730–732 行明确 "an infeasible model is a proof of non-existence **within the coefficient and
denominator bounds**" ✓;854–857 行明确调度器回归 "is evidence for, not a proof of, Lemma C" ✓;
摘要 "verify exactly up to order 30" 属实 ✓;§7 的猜想明确标为 Conjecture ✓。
需修:
- (中等)423–427 行:{1,3} 块 "stays infeasible with 3 parameters and coefficients up to 14, **so** the six
  labels … **cannot be made to pay for themselves however they are written**"——"so" 之后是全称判断，
  而证据是 (参数≤3, |系数|≤14) 的有界搜索。虽前后有缓和句，该从句仍越界。
- (中等)正文 472 行硬编码 "all 314,280 abstract local states",而当前枚举报告与 \NumStates 均为
  **375,600**(\NumStates 在正文中从未被引用，故陈旧值没被发现);同句 "up to two active children
  of each of the possible types" 与代码的 "总数 ≤2" 不符(见第 2 项)。
- (轻微)815 行 "the largest label magnitude was 692":我在复现 98/120 时观察到失败 run 的 pending
  token 幅度达 6,480。该句应限定为成功 run(或说明统计口径),否则与可复现的观测冲突。
- (轻微)"re-verified by an independent checker" 的独立性是代码层面的(检查器确实零共享),
  但检查器与搜索程序同为同一作者/AI 助手所写——论文未言明这一点，读者易高估 "independent" 的含义。

### 9. 第 7 节猜想的 30 阶验证与窗口锐性 —— **通过**

自写 CP-SAT 模型(每实例 all-different + fold 约束，不复用作者代码)独立重验:t=3..30 全窗口
476 个实例，唯一失败恰为 (4,-1)、(4,2),且两者均被求解器**证明不可行**(非超时),与论文逐字一致。
窗口锐性：窗口外 ±1、±2(t=3..14 共 48 个实例)全部证明不可行，数值上支持锐性。
论文的锐性文字论证("s 个最大值无反射伙伴必须全取,s>(t+1)/2 不可能")方向正确但写得很略；
我只做了数值验证，未给出完整手证——锐性论证的**严格性**我标为"数值支持，文字证明略"。

### 10. 与前作的关系 —— **通过**

前作 "Trees of odd order with at most two vertices of degree two are edge-graceful"
(arXiv:2608.23881,2026-08-24)存在且内容如本文所述(覆盖 D≤2 的**所有**奇数阶，常数有效;
符号验证到 n≤5001,2,245,070 棵树机验)。两定理确实互不包含：前作无 n 下界但只到 D=2;
本作 D 任意但要求 n>C(D+1)(log n)^A 且常数非有效。本文 87–92、106–107 行的陈述准确。

### 11. MP 引用核对 —— **一处误引，其余准确**

对照本机全文(Invent. Math. 240 (2025) 779–867 = arXiv:2204.09666v3):
- **"Section 7.4" 不存在**:MP 第 7 节的小节无编号。"abelian 情形可去掉 log" 的 remark 实际位于
  第 68 页 "Bounds in the main theorem" 小节;§7.4 是 Problem 7.4(p.69),其内容(g(n)=Ω(n))
  论文并未误述，但把 remark 的出处写成 "Section 7.4" 属误引，应改为 "Section 7, 'Bounds in the
  main theorem'"。(论文对 remark 内容的转述本身准确，且明确其非 printed theorem ✓)
- Lemma 6.24(abelian, k∈{3,4,5}, p=1 时 R=G)、Theorem 4.3(扰动半径 q^17 p^10 n/log^{1/10} n 量级)、
  Theorem 5.11(Gallagher, t ≤ log₄|G′| ≤ 10 log n；论文对 abelian 情形的读法合理且明确列为条件)
  ——均如论文所述 ✓。
- 附带:MP 的 **Lemma 6.25**(abelian,  prescribed-size 划分、sizes≥3、容删)已印出且比 6.24 更贴近
  lem:dense 的需要，论文完全未引用——修复严重问题第 1 条时这是现成工具。

### 12. 文献新颖性 —— **未发现先做者；一处文献遗漏**

- (a) 检索到的最强先验:Kaplan–Lev–Roditty 2009(D≤1)、作者前作(D≤2)、蜘蛛等显式族。
  未见任何 "任意 D、阈值 n>C(D+1)(log n)^A、不限制二度点位置" 的结果。**结果应是新的。**
- (b) "中性附加引理" 是初等观察，无优先权问题;"带禁差的 Heffter 型划分" 的经典等价物
  (Peltesohn 1939 解全半集/单删除;Heffter array 文献)均不覆盖 "任意小对称删除集 + 任意规定块大小"
  ——该能力实质上正是 MP 定理的内容，论文将其正确归于 MP,未发现夸大。
- **遗漏**:Cabaniss–Low–Mitchem(Ars Combinatoria 34 (1992) 129–142)Theorem 6 / Corollary 9
  证明：奇数阶树若二度点两两不相邻、无共同父点、满足 parity 条件，则 edge-graceful——即覆盖了
  一类**任意多个**(但位置受限的)二度点。本文 82 行 "The strongest general result we are aware of
  is due to Kaplan, Lev and Roditty" 因此不准确(本文结果仍新：无位置限制 + 密度阈值，但不引用
  CLM 会使综述性陈述失真)。refs.bib 中确无此文。

---

## 二、分级清单

### 严重(结论受影响)

**S1. lem:dense(稠密补全引理)的证明按正文写法不成立；定理 1.1 与 1.2 都经过它。**
正文证明仅五行:"inverse pairs fill even parts, one triple per odd part, triples from Lemma 6.24 (k=3)
applied with p=1; triples may be taken in pairs T,−T"。问题:
(i) 6.24 在 p=1 时要求三元组集合 X₃ 满足 |X₃△G| ≤ n/log^c n,即几乎全群；当块大小混合
(例如大量 size-2 块——随机树中大量度 3 静止点，属一般情形)时三元组质量 3m 远小于 n，直接应用失效;
(ii) "triples may be taken in pairs T,−T" 不是 6.24 的结论(其划分无配对结构);
(iii) 正确的修复需要先任意预留 P 对 ±Q 使删除集几乎充满 [1,K](只在 P<h 分支可行),P≥h 分支需
K≥7M+3 的 Simpson/Langford 区间打包——**这个分支讨论在正文中完全不存在**;
(iv) lem:dense 的陈述对任意对称 X 作出，而已知修复需要删除集的前缀结构 I⊆[1,M]
(幸运的是 realization 引理恰好给出 S⊆±[1,M],故**应用端大概率可圆**);
(v) 该引理引用 "[ProjectNotes, Section 3]"——作者自己未发表的研究笔记——作为关键步骤出处，
且该笔记内部对所需的 mixed interval-packing 引理是否已证存在张力。
**评估**:引理陈述很可能为真，且很可能可由已印文献(MP Lemma 6.25 + Simpson 1983 + 前缀结构)
修复；但**按论文现在的写法，主定理的证明是不完整的**。这属于 "结论很可能站得住、证明现在不成立"。

### 中等(需修正陈述/补充证明文字)

- **M1.** 附录 A 未写出 k≥3 的分流规则(_act2_trigger / _reduce_odd_k_to_one / _resolve_act2),
  Step 4 "unit exists because v has at least two children" 的理由在 k≥3+无 port+残差{1}/{2} 时不成立;
  调度器补丁(V21/V22/L12 passthrough 等)未进论文。引理 C 的**陈述**有强计算证据支持
  (≤9 阶全树回归 + 我的 k=2..5 探测均在目录内),但**论文里的证明文字不穷尽**;k≥3 的抽象状态
  从未被穷举(枚举总数 ≤2),而 ≤9 阶全树又不含 k≥3 owner，故 k≥3 仅有随机树的经验覆盖。
- **M2.** MP "Section 7.4" 误引(remark 实为其 §7 内 "Bounds in the main theorem" 小节;7.4 是 Problem)。
- **M3.** 正文 314,280 vs 当前 375,600(硬编码陈旧;\NumStates 未被正文使用而未被发现);
  "up to two active children of each of the possible types" 与代码(总数 ≤2)不符。
- **M4.** numbers.tex 两个宏不可由当前数据复现(12,743→12,740;6,677→6,673);
  需确认 Zenodo 归档与论文是否一致(我未下载归档)。
- **M5.** {1,3} 块处 "cannot be made to pay for themselves however they are written" 为全称表述，
  证据为有界搜索(≤3 参数、|系数|≤14)。
- **M6.** 文献遗漏 Cabaniss–Low–Mitchem 1992;"strongest general result" 表述失真。

### 轻微(表述/工程)

- L1. closure_check 不带 --gate 时 C6 被跳过却仍打印 "ALL CONDITIONS PASS";C5 只报告不检查;
  论文列四条条件而脚本有六条。
- L2. closure_check 与批处理代码共享 `key` 函数;"independent checker" 的独立性仅为代码层面
  (检查器本身确实零共享 ✓,但两者同出一人/AI 之手)。
- L3. "largest label magnitude was 692" 未限定口径；失败 run 中观测到 6,480。
- L4. 目录 token_jacobian 字段由未独立检查的 assembler 生成;E6 不在检查器内(与论文声称一致);
  插入后族的复验(743–744 行)我未找到端到端脚本，未验证。
- L5. `schedule()` 公开入口在顶点 0 非分支点时可 IndexError;不影响已报告的回归(回归/构造器定根正确)。

---

## 三、总体判断与信心边界

**主要结论很可能成立。** 计算机辅助部分(目录 12,740 族、闭包、调度器、构造器、猜想 30 阶)经我
独立重跑与抽查全部吻合，工程质量高；附录 B 的常数我重算一致；第 7 节我独立重证。薄弱环节集中在
**纯数学的稠密补全一步(S1)** 和 **附录 A 的文字证明(M1)**:两者都更像 "证明没写完/没写对"
而非 "陈述错误"——S1 的应用端有 realization 引理提供的前缀结构兜底、MP 6.25 是现成修复工具;
M1 的陈述有回归与我的探测双重支持。

我**没有**做、因而不能背书的:
1. 未重跑约 3 万次 CP-SAT 搜索本身;"有界不可行" 的结论依赖 CP-SAT 的正确性(我只重跑了检查器、
   闭包、猜想验证与构造器)。
2. 未逐一核对 375,600 个抽象状态与其 concrete fragment 的语义忠实性(只抽查)。
3. 未重证 MP 的定理本身(只核对了论文对它们的转述)。
4. 未下载 Zenodo 归档比对(项 7 的两个宏差异可能只在本地 checkout 存在)。
5. 猜想窗口锐性的文字证明只做了数值支持，未给独立手证。
6. "插入后族也复验"(论文 743–744 行)未找到对应脚本，未验证。

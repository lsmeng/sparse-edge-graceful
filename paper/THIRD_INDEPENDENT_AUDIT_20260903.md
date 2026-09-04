# 二审报告:sparse edge-graceful 论文(修复版)对抗性复审

**对象**:github.com/lsmeng/sparse-edge-graceful @ 0a49f2f(修复版,含 REPAIR_dense_completion.md、
REPAIR_coefficient_bound.md、APPENDIX_A_ENUMERATION_20260903.md、data/closure_report.md)
**审计角色**:对抗性审稿人。目标不是确认论文正确,而是找前两轮审计未覆盖的真问题。
**复核环境**:全部脚本在 `/Users/geoclaw/Documents/claude/projects/tree-labelings/.venv/bin/python` 下实跑;
仓库与原始材料未做任何修改(复现环境搭在 /tmp/pn)。

---

## 〇、执行摘要

修复版解决了一审的四个问题(稠密补全缺口、附录 A 的 k≥3、§7.4 误引、E4/系数界),修复方向总体正确,
但**二审在接缝处发现两个新的 SEVERE 级问题,其中一个是具体的、可实现的局部构型,
在该构型上构造程序必然给两条不同的边赋同一个标签——实现引理(realization lemma)按现状不成立**。
此外有四条 MODERATE(定量常数与前提核对)和若干 MINOR。

**判决(详述见第五节)**:
- **定理 1.1:按现状未得证。**(S1 是直接反例;S2 使定量链断裂、最坏情形阈值退化为 D 的二次。)
- **定理 1.2:按现状未得证。**(同样依赖实现引理;且其对 D 线性的阈值对 S2 更敏感。)
- 两处 SEVERE 均有清晰的修复路径(见各条"最小修复"),修复后主要结论大概率成立,
  但常数 A 与表述需要重算;在修复完成并重新认证之前,两个定理都不能当作已证明。

---

## 一、新发现(按严重度)

### S1(SEVERE):刚性 ray 作为父上下文整体逃逸 gate;可实现对 (h0_1-2_p0_bot, h0_2_p0_act) 的全部菜单组合发生不可分离的形式恒等碰撞

**位置**:论文 §6 gate/闭包(856–879 行);scripts/check_lookahead_gate.py;scripts/closure_check.py(C6);
scripts/free_token_constructor.py:3293–3297(ray 模板);data/emittable_pairs.json。

**主张**:"Two adjacent cells can fail to be compatible in only one way … Our gate enumerates every ordered
pair of contexts … restricted to the realizable pairs it reports 71. All but one … absorbed by the rule of
that section … the exception … we join the child into the parent"(856–879 行);
closure_report C6:"1973 failing ordered pairs, 71 with both contexts emittable … 0 remain [PASS]"。

**为何不成立(具体反例)**:
1. 刚性 ray `h0_2_p0_act` 是"constructor template and not a symbolic family"(表 1 注,612–614 行),
   **不在目录中**(closure_check.py:39 `RIGID={"h0_2_p0_act"}`,C1 对它显式豁免)。gate 只枚举目录内上下文,
   因此**父为 ray 的可实现对从未被 gate 评估**。闭包 C6 只是把 gate 的 failing_pairs 与可实现对取交,
   对 ray 父对不可见。
2. 枚举记录的可实现对(data/emittable_pairs.json)中**恰有 7 对父为 h0_2_p0_act**:
   子 ∈ {h0_1-2_p0_bot, h0_1_p0_act2, h0_2_p0_act2, h0_3_p1_bot, h1_1_p0_act2, h2_1_p0_act2, h2_3_p1_bot}。
3. ray 模板(构造器 3293–3297 行,我手工验证过 P=O)为 (−3x/2; −x/2, −x, x/2; x),t = x/2,
   即 ray 的**全部**非固定标签都是输入 x 的倍数:{−3/2, −1/2, −1, 1/2}·x。
4. 取子 `h0_1-2_p0_bot`(目录内,菜单 3 族,均非 E6-clean):
   - menu0/1(head_ratio=2,非 FA):有形如 **−y** 的物理臂标签(head_only_forms: r0a1x0, ratio −1)。
     共享边 x = 2y,故 ray 的标签 −x/2 = **−y**,与子的 −y **作为 y 的形式恒等**。两边都是强制标签
     (无任何自由参数),没有参数选择能把它们分开。
   - menu2(head_ratio=1,FA):子有 −y,x = y,ray 的 −x = **−y**,同样恒等。
   三个菜单组合**全部碰撞** → 该可实现对在 gate 意义下 failing,却不在 71 之内(C6 的"0 remain"因此为假)。
   在该构型上,实现程序会把值 −y 赋给两条不同的边(子的臂与 ray 的臂),单射性被破坏,
   **实现引理在此局部构型上失败**——这与常数大小无关,是构造本身的反例。
5. 次要地,对 (h2_1_p0_act2, h0_2_p0_act):子是 forced-antipode(HOR={−1}),ray 有 −x,同样碰撞;
   且 ray 无 token、无端口(p0),8d 吸收机制在它下面没有着力点。该对同样未被任何机制覆盖。

**最小修复**:把 ray 模板作为正式的 5 标签族写入目录(独立检查器完全可以验证模板),
让 gate 覆盖 ray 父对;然后对新暴露的 failing 对逐一处理——对 h0_1-2_p0_bot 增补无 head-only 标签的族
(参照 h0_3_p1_bot、h2_3_p1_bot 的菜单,HOR 已为 ∅,可行性高),或扩展 join/吸收规则;
对 ray 下的 FA 子明确吸收机制。修复后须重跑 gate + closure_check 并更新 71 的账目。

**信心**:高。所有字段(head_only_forms 的 ratio 是相对头参数 y 的比率、gate 以 q/h 归一化到父的 x 单位)
都与 check_lookahead_gate.py:103–115 的实现交叉验证过;我用修正后的独立实现完整复现了 gate 的
1973/71(见第四节),证明我对碰撞条件的理解与 gate 一致。残余不确定度仅在"枚举是否真会在合法树中
发出该对"——但 emittable_pairs.json 正是调度器在具体片段上的运行记录,且 REPRODUCE.md §5 说明其语义。

---

### S2(SEVERE):不变量 (b) 的 3W 界为假——刚性行链把符号头无界地沿树向上传播,定量链随之退化为 D 的二次

**位置**:正文 §6(655–657 行)与附录 B State(1167–1168 行)、验证(1287–1289 行)称符号标签
"属于 A、A 的活跃孩子、A 的父,故至多 3W 个";同附录 1210–1218 行。

**主张**:任何时刻符号标签 ≤ 3W(W=29),由此 |Φ| ≤ 3W(2|Placed|+3W)(1185 行),
配对箱边长 M′(|Φ|+1)(1301–1303 行),幅度 ≤ A(D+1),A = 8·10¹²。

**为何不成立(具体反例)**:
1. 附录 B 自己写明(1210–1218 行):刚性行是 (E5) 的例外,"their parents receive a symbolic input
   whenever those inputs are symbolic";对两输入刚性行,"the row passes that single live parameter on"——
   **没有给任何深度上限**。
2. 两输入刚性行在目录中且无逃生通道:h0_1_p0_act2 菜单仅 1 族、**无 token**、头 = −x₁−x₂
   (输入的固定形式);h0_2_p0_act2 头 = −3/2(x₁+x₂)。附录 A 明确"exact search shows no family with
   a free head exists"——所以一旦输入符号化,头必然符号化,逐层上传。
3. 调度器探针(scripts/context_scheduler.py,用其公开 API 构造梳状树):
   两输入梳(vᵢ 的孩子 = v_{i−1} + 侧枝 sᵢ + 长 1 臂,直连父边 h=0)在 m = 1,2,3,5,8,12,**20** 时
   每层都发射 `h0_1_p0_act2`;ray 梳(孩子 = v_{i−1} + 长 2 臂)在 m = 2,4,8,12 每层发射 `h0_2_p0_act`。
   即调度器确实产生任意长的刚性行链,m = Θ(D) 可达。
4. 载体含头是常态而非例外:data/alphabet_carriers.json(3445 上下文)中 6968 个带载体族有
   **2752 个**的最小行列式载体含头参数 y;枚举全部载体对,**634/6969 个 token 族不存在任何避头载体**
   ——"选避头载体"这种简单修复对约 9% 的族不可能。
5. 具体见证链:底部 owner h1_1_p2_bot 的首选族 token 载体 = [y, t1] 含头(det 1)→ 头符号化 →
   穿过 m 层 h0_1_p0_act2(其族 5 标签、无 token,永远不会 resolve 也永远不会悬置)。
   每一层贡献 3 个符号标签(y、−y、−y−x₂),符号区横跨 m+2 个 cell,而不是 3 个。
6. ray 链一侧,所谓"四层复位族"在 scripts/context_scheduler.py 中**不存在**
   (grep r2222|reset|four_layer 零命中),目录中也没有 r2222 上下文;它只出现在
   data/family_r2222_L12.json,由构造器的 four_layer_family() 用作者自有库 ftl 验证(见 M1)。

**后果(断裂不等式)**:符号标签数 ∼ 3m + O(W),m ≤ owners ≤ 2q ≤ 2D,故最坏 (4D+3)W;
|Φ| ≤ (4D+3)W·(2|Placed| + (4D+3)W) = **O(D²)**;
配对箱边长 M′(|Φ|+1) = O(D²);幅度 ≤ 7·27648·箱 = A′·(D+1)²。
定理 1.1 的阈值 n > C(D+1)(log n)^A 与定理 1.2 的 n > C(D+1) 都允许 D 大到 ∼ n/polylog(n),
二次界在该范围内实质更弱——**定理的表述(对 D 线性)按现状未得证,不只是常数问题**。
此外,刚性行每层的标签 {y, −y} 在同一 cell 内互为对径形式,也与不变量 (c) 的字面表述
("两符号形式相同或对径仅当父 input-only 与子 head-only 相撞")冲突。

**最小修复**:在调度层对两输入刚性行做与 ray 类似的"每固定层数 join 成自由头宏族"的复位
 (有限目录扩展即可,类比四层复位);或证明链长有绝对常数上界(我认为不成立,梳状树是反例)。
 修复后重算 3W → |Φ| → 箱 → A 全链。

**信心**:高。传播机制是论文自己的文字;刚性行无 token 是目录事实;长链是调度器实测。

---

### M1(MODERATE):ray 的"四层复位族"与 h0_2_p0_act 模板均无独立认证;附录 B 对 ray 段的描述与构造器实际行为两边都对不上

**位置**:附录 B 1214–1216 行("the four-layer reset family restores a free head");表 1 注(612–614 行);
scripts/free_token_constructor.py:1388–1391。

**问题**:(a) 复位族不在调度器、不在目录,只有构造器数据 data/family_r2222_L12.json,
由作者自有库(free_token_library,ftl)验证——没有独立检查器证书;
(b) h0_2_p0_act 模板 (−3x/2; −x/2, −x, x/2; x) 我手工验证 P=O 成立(t=x/2,输出 {−x,−3x/2,−x/2,x/2}
与标签置换一致),数学上没问题,但同样只有自有库验证;
(c) 构造器注释说 synth_topology 对同上下文能找到**自由头两参数族并优先使用**——该族不在任何归档
JSON 中,运行时合成、自有库验证。即附录 B 描述的机制与代码实际行为不一致,且整条 ray 链的认证
依赖作者自己的库,不满足"检查器与搜索无共享代码"的标准。

**最小修复**:把复位族与 ray 模板一并入目录,过独立检查器(checker 完全有能力验证 5 标签模板)。

---

### M2(MODERATE):稠密补全 Case 2 的 R′ 侧微扰半径超出 MP Lemma 6.25 的允许值(断裂不等式)

**位置**:§sec:dense(669–797 行),ε 的定义与 |R′△R| 的估计。

**问题**:文中取 ε := (p/2)^{10¹⁰}/(6 log^{10²⁴} n),使 6.25 的允许半径恰为 6εn;
但文中自估 |R′△R| ≤ 6εn + |Z_n\X| + |J*| ≤ 6εn + εn/2 + √n log n **> 6εn**。
R′ 侧超出允许半径,6.25 不能按所述方式应用于 R′。
(我逐条核对了 6.23/6.25/6.26 的其余假设——m=ΣM^Q、g=0、|Q\Z|、|Z|≥m+3、耦合常数 p/2 的恒等式
N(1−p)/2 = p·m₂、M′ 化归 {3,4,5} 保和、Binomial 中位数取整——全部成立,只有这一处算术断裂。)

**最小修复**:把 ε 定义中的因子 6 改为 7(或 13),不等式即闭合;纯书写/算术修正,不影响结构。

---

### M3(MODERATE):悬置三元组使 X 不对称,lem:dense 的对称性前提不满足

**位置**:§sec:dense 671–683 行。

**问题**:X = Z_n\({0}∪S) 被描述为"closed under negation up to the pending triple T",
即 T ⊆ S 而 −T ⊄ S(−T 留给奇数普通块)。于是 x = −t ∈ X 时 −x = t ∉ X,**X 不对称**,
而 lem:dense(678–683 行)的假设要求 symmetric X。前提不成立,引理不能直接应用。

**最小修复**:一句话:对 X′ = X\(−T) 应用引理,指定的奇块大小 r 改为 r−3(r=3 时删去该块)。
结构不受影响。

---

### M4(MODERATE):三处定量主张与目录不符——"(E1)–(E6) 全族成立"、|Φ(F)| ≤ 3、"reserved ≤ 6q"

**位置**:附录 B 1134 行、1292–1293 行;lem:charge(500–511 行)。

**问题(实跑数据)**:
(a) "Every family carries the properties (E1)–(E6)"(1134 行)为假:作者自己的审查脚本
scripts/audit_e4_e6.py 在全部 12,742 个菜单族上跑出 **4,427 个族违反 (E6),覆盖 2,514 个上下文,
其中 881 个是各上下文的首选(primary)族**(E4 则 0 违反)。论文 §6(576–589 行)确实披露了
E6 不普遍成立(141/2,789 上下文无 E6 族,data/e6_missing_contexts.json 恰 141 个 ✓)并用 gate
兜底——但附录 B 这句全称陈述与之直接矛盾,且 gate 本身有 S1 的盲区。
(b) "at most |Φ(F)| ≤ 3 reservations"(1293 行)为假:目录中 |forced_ratios| 最大 = **10**
(root_1-6_p0_act menu5:{±1, ±1/6, ±1/3, ±2/3, ±5/6});652 个族 ≥ 4;
**10 个上下文的整个菜单 min|Φ| ≥ 4(最大 6)**,任何选择规则都无法在这些上下文达到 ≤3。
(c) lem:charge 称"values reserved for forced companions number at most 6q"(502–503 行),
但其证明(506–511 行)只有 owners ≤ 2q 与 |S| ≤ 12D+3 的账目,**没有任何一句话支持 6q**;
按 (b) 的机制每 owner 至多 10 个预约,真界是 ≤ 20q(或改用"预约值都是父的未来标签,故 |Reserved| ≤ |S|"
的不同论证)。后果:|Placed|+|Reserved| 从 18(D+1) 变 ~32(D+1),NumCoordLin 约翻倍,
A 在 S2 修复后还需因此再乘常数因子。**定理形状(对 D 线性)不受 (b)(c) 单独影响,但现有常数推导是错的。**

**最小修复**:(a) 改为"(E1)–(E5),E6 仅部分成立,见 §6";(b)(c) 按目录真值 10 重算,
或在目录层面证明所选族 |Φ| 有更小上界并给出机制。

---

### m1(MINOR):可复现性瑕疵三处

1. data/emittable_k3.json / emittable_k4.json 各 2,664 个上下文、集合相等 ✓(支持"cap3→cap4 不动"),
   但 k3 是主枚举(2,790)的**真子集**(差 126 个,k3−主集 = ∅),与论文 488–493 行"cap2→cap3
   adds six contexts"的叙述对不上;NumStates = 5,398,800 无法从发布产物独立复现
   (data/emittable_report.md 未随仓库发布,paper_numbers.py 第 53 行需要它)。
2. paper_numbers.py 开箱即跑失败(FileNotFoundError: data/emittable_report.md);
   check_alphabet_families.py 等脚本默认读 data/alphabet_families.json,而仓库只发布 .json.gz。
3. 补上缺失输入后,paper_numbers.py 重新生成的 numbers.tex 与仓库版**逐宏一致**
   (仅 gate/neutral/求解统计四类宏依赖未发布输入;其中 gate 的 1,973 我已独立复现)。

### m2(MINOR):其它文字问题

- 附录 B "minimum is 1 for 69% of the tokens"(1142 行):实测 5,491/7,963 = 68.96% ✓。
- 附录 A Step 3 的 (h,∅,p,c) 空残差上下文:枚举中确有 40 个(continuing_empty_L1/L11),
  且 40/40 均在目录有族 ✓——一审时对此的疑虑解除。
- 206 个"含自身头对径"的族与菜单排序规则(families containing the antipode of their own head last,
  822 行)一致,非矛盾;但与 S2 中刚性链的 y/−y 共存一样,不变量 (c) 的措辞需要补"指定对径除外"。

---

## 二、对出题人六个重点的逐项结论

1. **机器检查与手写证明的接缝**:有问题。分类表见第三节;两处裸断言(3W、|Φ|≤3、6q)被目录数据证伪,
   ray/复位族无独立证书(M1),E6 全称句为假(M4a)。
2. **realization 引理不变量逐分支 + 3W 反例**:有问题(S2,SEVERE)。分支记账本身(Token/无 Token/
   双 token/FA/根)我逐条读过,消元非恒定性有 157,183,992 三元组的机器验证(我独立复算一致);
   断裂点在 State 的 3W 计数。
3. **定量链**:有问题(S2 的 O(D²) 退化 + M4 的 |Φ|/6q)。在给定 3W 与 18(D+1) 的前提下,
   其余算术我逐步重算无误:M′=24·144=3,456 ✓;NumCoordLin = 24(2·29·18(D+1)+2·29+841+1) =
   25,056(D+1)+21,600 ✓;NumPairLin = 3,456·(87·36) = 10,824,192 ✓;NumPairCon = 3,456·7,570 =
   26,161,920 ✓;A = 7·27,648·36,986,112 ≈ 7.16·10¹² → 8·10¹² ✓;NumDetMax=144、NumAdjMax=216、
   27,648=2·216·64 ✓(全部实跑复核)。
4. **局部/全局接口(稠密补全前提)**:有问题(M2 半径、M3 对称性,均为一句话级修复)。
   Case 2 的整体结构(6.23 应用、6.26 耦合、6.25 对 Q′ 顶格应用)经对照 MP 原文逐条核实成立。
5. **gate 豁免(8d + 新增 single-pair join)**:**有问题(S1)——豁免账目本身是对的**
   (我用独立实现复现 1973 失败对、71 可实现失败对 = 70× h2_1_p0_act2 + 1× h0_1-2_p0_bot,
   与 closure_report 完全一致;join 族 root_2_p0_J12 在目录、菜单 1、token 载体合规),
   **但 gate 的输入集合漏了 ray 父的 7 个可实现对**,其中 (h0_1-2_p0_bot, ray) 实测全菜单碰撞。
6. **附录 A 穷尽/互斥**:基本通过。两刚性两输入行已显式写出 ✓;k≥3 例外句仍只有
   "exactly two active children",但枚举已扩到 cap 3/4 且 k3≡k4 ✓;空残差 40 上下文全覆盖 ✓;
   调度器在全部 4,782,969 棵 ≤9 顶点标号树上 uncovered=0、missing=0 ✓。
   残余:cap 叙述与归档不一致(m1-1),复位族未经调度器(M1)。

## 三、附录 B 定量主张分类表

| 主张 | 类别 | 复核结果 |
|---|---|---|
| W=29、参数 ≤7、系数 ≤64/分母|12 | 机查(独立检查器) | ✓ 12,742/12,742 PASS |
| NumDetMax=144、NumAdjMax=216、69% | 机查(carrier_determinants) | ✓ 实跑一致 |
| 消元后非恒定(r adj(M)N≠0) | 机查(carrier_nonconstancy) | ✓ 157,183,992 三元组,我独立 numpy 复算 0 失败 |
| (E1)–(E5) | 机查(独立检查器,无共享代码) | ✓ |
| (E6) 全称成立 | **裸断言,为假** | ✗ 881 首选族违反(M4a) |
| 闭包 C1–C6 | 机查(closure_check) | C1–C5 ✓;C6 目录内 ✓,**ray 父盲区**(S1) |
| gate 1973/71 | 机查(我独立复现) | ✓ 完全一致 |
| owners ≤ 2q、|S| ≤ 12D+3 | 文证(lem:charge,电报式但成立) | ✓(目录无空残差反例;刚性行有臂故关联细分边) |
| 箱公式、格点避条件、"enlargement does not compound" | 文证 | ✓(在其前提下) |
| **3W 符号标签界** | **裸断言,为假** | ✗(S2) |
| **|Φ(F)| ≤ 3、reserved ≤ 6q** | **裸断言,为假/未证** | ✗(M4bc) |
| ray 三层复位 | 裸断言(机制不在调度器/目录) | 无法判断→倾向不成立(M1) |
| 稠密补全 Case 2 结构 | 文证(对照 MP 原文) | ✓ 除 M2/M3 两处 |

## 四、复跑记录(全部实际执行)

| 命令 | 结果 |
|---|---|
| check_alphabet_families.py(全目录) | **12,742 PASS / 0 FAIL** |
| context_scheduler.py --all 9 | uncovered_count=0,missing_from_alphabet_count=0(4,782,969 棵树) |
| carrier_determinants.py | max min\|det\| = 144;max growth = 216;无 token 无载体 |
| audit_e4_e6.py | E4:0 违反;E6:4,427 族 / 2,514 上下文 / 881 首选 |
| carrier_nonconstancy(我的 numpy 独立实现) | 7,963 tokens、777 个 N、157,183,992 三元组、0 失败(与作者计数一致) |
| check_lookahead_gate.py --menu --json | 1973 失败对 ✓;token Jacobian 6,969 族秩全 2 ✓ |
| 我的 gate 独立实现(可实现对限制) | 71 = 70×(h2_1_p0_act2) + 1×(h0_1-2_p0_bot),与 closure_report **完全一致** |
| closure_check.py --gate(用我生成的 gate) | **ALL CONDITIONS PASS**(C1–C6) |
| paper_numbers.py(补缺失输入后) | 目录派生宏与 numbers.tex 逐字一致 |
| 枚举覆盖核对 | 2,790/2,790 上下文在目录有族;40/40 空残差;k3≡k4 |
| ray 父可实现对碰撞分析 | 7 对未被 gate 评估;(h0_1-2_p0_bot, ray) 3/3 菜单碰撞(S1) |

未重跑:CP-SAT 证书搜索(需 ortools/py3.12,数天量级)、5,398,800 状态枚举(产物未发布全)、
中性块构造统计。这些输入的**输出端**(目录、检查器、闭包、gate)均已独立验证。

## 五、逐定理判决

**定理 1.1(n > C(D+1)(log n)^A):按现状未得证。**
- S1 给出可实现局部构型上构造的显式失败(与常数无关)——这是最直接的反例;
- S2 使幅度界退化为 (D+1)² 阶,定理的对 D 线性表述在最坏情形下不成立;
- M2/M3 是稠密补全的两处小断裂,修复各需一句话,但"已修复"状态目前不成立。
- 修复路径清晰且大概率可行(S1:ray 入目录 + 给 h0_1-2_p0_bot 补族;S2:调度层复位 + 全链重算;
  M2/M3/M4:文字与常数修正)。修复后我对定理 1.1 成立有中等偏高信心,但 A 会显著变大。

**定理 1.2(n > C(D+1),条件于 MP §7.4):按现状未得证。**
- 继承 S1/S2 的全部问题;其对 D 线性的阈值比 1.1 更不容忍 S2 的二次退化;
- 此外它额外条件于 MP §7.4 的 remark(一审已核对该条件陈述本身已修正)。

## 六、信心边界

- **高信心**:S1(字段语义与 gate 实现交叉验证,且我的独立 gate 实现与作者结果逐对一致)、
  S2(论文自己的文字 + 调度器实测 + 目录事实)、M2/M3(纯算术/逻辑,MP 原文已逐条对照)、
  M4(作者自己的审查脚本输出)。
- **中等信心**:M1 的"复位族不存在于调度器"(grep + 目录键扫描,理论上可能改名隐藏);
  k3/k4 叙述矛盾(m1-1,可能有未发布的中间配置)。
- **未检查**:CP-SAT 求解器本身的正确性(不在审计范围,检查器独立验证其输出即可);
  MP §7.4 remark 的真理性(那是 MP 的开放陈述,论文已正确地把 1.2 条件化);
  文献优先权(一审第 12 项已查,本轮未重复);30 阶猜想的独立重跑(一审第 9 项)。
- 我对"修复后两个定理成立"的信心边界:实现引理的架构(载体消元、延迟配对、gate + 吸收 + join)
  在已验证的部分上没有发现概念性错误;S1/S2 都是**机制覆盖不全**而非机制错误,
  但 S2 的修复(刚性行复位)尚未以任何形式存在,其目录扩展的可行性未被验证。

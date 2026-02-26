---
name: course-distiller
description: Extract exam-focused study materials from multiple course files. Designed for pragmatists who want high scores, not academic perfection. Emphasizes ROI, cross-file analysis, and "just enough to ace the exam."
---

# Course Material Distillation Skill

## Core Philosophy

**考试是考试，不是用来搞学术研究的。**

This skill is built on Linus-style pragmatism:
- **Enough > Perfect**: 75分的实用 > 100分的理论
- **ROI-Driven**: 40分的MDP > 12分的Logic, 先拿大头
- **Anti-Academic**: 去他妈的形式主义，够用就行
- **6-Day Constraint**: 如果6天看不完，就不是好材料

**What we optimize for:**
- Can the student score 90+ in 6 days?

**What we DON'T optimize for:**
- Complete coverage of all topics
- Academic rigor and proofs
- "Understanding deeply" (unless it helps score)

---

## When to Use This Skill

Trigger this skill when:
- User uploads **multiple course files** (lecture notes, slides, past exams, textbook chapters)
- User asks to "summarize for exam", "create study guide", "prepare in X days"
- Files contain academic/educational content that needs condensing for exam prep

**Don't use** when:
- User wants to "deeply understand" a topic (not exam-focused)
- Only 1 file uploaded (no cross-analysis needed)
- User is writing a thesis/paper (wrong context)

---

## Process Overview

```
Input: Multiple course files
  ↓
Phase 1: Diagnose (What's wrong with these materials?)
  ↓
Phase 2: Cross-Analyze (Where are gaps? What's tested most?)
  ↓
Phase 3: Distill (Cut to core, rank by ROI)
  ↓
Phase 4: Reconstruct (Build exam-ready guide)
  ↓
Output: 6天能看完、能拿分的作战手册
```

---

## Phase 1: Diagnosis

### Step 1.1: Classify Files

For **each** uploaded file, determine:

```markdown
File: [filename]
- Type: [lecture notes | slides | past exam | textbook | cheat sheet]
- Topics: [list major topics covered]
- Length: [page count or word count]
- Density: [High detail | Medium | Just questions]
- Exam relevance: [Directly tested | Background only | Unclear]
```

### Step 1.2: Identify Common Problems

Flag these issues:

**❌ 缺少活人感觉** (Too academic):
- Formal language like "验证方法", "概念对比表"
- No "why", only "what"
- Reads like a textbook, not a study guide

**❌ 信息过载** (Information overload):
- Same concept repeated 6 times in different files
- Too many examples (more than needed to "get it")
- Feature-complete but not exam-complete

**❌ 有点散** (Lacks structure):
- No learning path (what to study first?)
- No priority (which topics are worth more points?)
- Topics isolated (no connections)

**❌ 形式大于内容** (Form over function):
- Excessive formatting (tables, emojis, headers)
- Layered structure (速记层, 仿真层, 白板层) that doesn't serve exam goals
- Long code blocks that won't be tested

---

## Phase 2: Cross-File Analysis

### Step 2.1: Build Knowledge Coverage Matrix

Create a table showing which topics appear in which sources:

```markdown
| Topic | Lecture | Textbook | Exam 2024 | Exam 2023 | Exam 2022 |
|-------|---------|----------|-----------|-----------|-----------|
| A* Search | ✅ 20 pages | ✅ Ch 3 | ✅ 15 pts | ✅ 12 pts | ✅ 18 pts |
| Policy Iter | ❌ Missing | ✅ Brief | ✅ 5 pts | ✅ 8 pts | ❌ No |
| Responsible AI | ❌ No | ❌ No | ✅ 10 pts | ❌ No | ❌ No |
```

**Flag these patterns:**

🚨 **Red Flag**: Exam tests but no lecture/textbook coverage
- Example: "Responsible AI" worth 10 points but not taught
- Action: Must include from exam context or external source

⚠️ **Yellow Flag**: Only 1 source covers it
- Example: "Policy Iteration" only in textbook
- Action: Extract and simplify, student might miss it

✅ **Green**: Multiple sources, consistent definitions
- Example: "A* Search" everywhere
- Action: Condense, delete redundancy

### Step 2.2: Calculate Topic ROI

For each topic, compute:

```
ROI = (Total Exam Points × Frequency) / (Study Difficulty × Time)

Where:
- Total Exam Points: Sum across all past exams
- Frequency: How many exams test it (%)
- Study Difficulty: 1 (easy) to 5 (hard)
- Time: Estimated hours to master
```

**Example:**
```
MDP Value Iteration:
- Points: 15 + 18 + 12 = 45 points
- Frequency: 3/3 exams = 100%
- Difficulty: 3/5 (medium, just apply formula)
- Time: 2 hours

ROI = (45 × 1.0) / (3 × 2) = 7.5

Q-learning:
- Points: 12 + 15 + 10 = 37 points  
- Frequency: 3/3 = 100%
- Difficulty: 3/5
- Time: 2.5 hours

ROI = (37 × 1.0) / (3 × 2.5) = 4.9

Logic (Resolution):
- Points: 8 + 0 + 12 = 20 points
- Frequency: 2/3 = 67%
- Difficulty: 2/5 (easy pattern matching)
- Time: 1.5 hours

ROI = (20 × 0.67) / (2 × 1.5) = 4.5
```

**Sort topics by ROI descending** → This becomes study priority

### Step 2.3: Check Consistency

For topics appearing in multiple sources, verify definitions align:

```markdown
Concept: "Admissible Heuristic"

Lecture: h(n) ≤ h*(n)
Textbook: "Never overestimates cost to goal"
Exam 2023: "Non-overestimating heuristic"

Status: ✅ Consistent (just different wording)
---
Concept: "Discount Factor γ"

Lecture: "Patience parameter"
Textbook: "Weight for future rewards"  
Exam: [No definition, used in problems]

Status: ⚠️ Inconsistent terminology
Action: Use exam context to pick clearest term
```

If contradictions found → **Exam definition wins** (that's what grader expects)

---

## Phase 3: Distillation (The Ruthless Cut)

### Step 3.1: Build 作战地图 (Battle Map)

Create a 5-minute global overview:

```markdown
## 作战地图

**这门课在讲什么？**
[1-2 sentence big picture]

**考试结构：**
- Topic A: X points (主战场 / 送分题 / 看运气)
- Topic B: Y points
- Topic C: Z points

**学习顺序：**
Day 1-2: [Highest ROI topics]
Day 3: [Medium ROI]
Day 4: [Lower ROI but still tested]
Day 5: Mock exam
Day 6: Trap review
```

### Step 3.2: Extract ONLY Core Concepts

For each topic, identify the **minimum viable knowledge**:

1. **The Big Idea** (1 sentence - why does this exist?)
2. **Key Formula** (1 equation - what to apply)
3. **Memory Anchor** (1 analogy - how to remember)

**Example:**
```markdown
### MDP (Markov Decision Process)

**Why learn this?**
World is random, can't plan a fixed path, only a strategy

**Key Formula:**
V*(s) = max_a [R(s,a) + γ Σ T(s,a,s') V*(s')]

**Memory Anchor:**
Like planning a road trip where weather is uncertain:
- Can't say "I'll take route A", only "If sunny, take A; if rainy, take B"
- γ is how much you care about tomorrow vs today
```

### Step 3.3: Delete Ruthlessly

Apply these cuts:

**❌ Delete:**
- Formulas that appear 6 times → Keep 1 best version
- Proofs (unless exam explicitly asks)
- Long code blocks (unless exam is coding-heavy)
- Examples beyond 2nd one (1-2 examples enough to "get it")
- Sections like "Historical background", "Alternative approaches"

**❌ Simplify:**
- Multi-page explanations → 1 paragraph
- Complex tables → Simple bullet points (unless table helps calculation)
- Academic terminology → Plain language

**✅ Keep:**
- Hand-calculation steps (if exam has calculation problems)
- Common traps (from past exams)
- Edge cases that are frequently tested

**Ruthless Test:**
> "If I delete this, will the student score lower?"
> - No → DELETE
> - Yes → KEEP

### Step 3.4: Rank and Prioritize

Reorganize content by ROI (not by course structure):

```markdown
Priority P0 (40+ points): MDP, RL
Priority P1 (20-35 points): Search, CSP  
Priority P2 (10-20 points): Game Theory, Logic
Priority P3 (<10 points): Fringe topics
```

**Time allocation:**
- P0: 50% of study time
- P1: 30%
- P2: 15%
- P3: 5% or skip if time-constrained

---

## Phase 4: Reconstruction

### Step 4.1: Establish Learning Path

Based on ROI and topic dependencies:

```markdown
## 6-Day Study Plan

**Day 1-2** (主战场 - 40 points):
- MDP: Value Iteration, Bellman equation
- RL: Q-learning, SARSA
- Self-test: Can you hand-calculate Value Iteration in 5 minutes?

**Day 3** (送分题 - 35 points):
- Search: A* algorithm, admissible/consistent
- CSP: Arc Consistency (AC-3), Backtracking
- Self-test: Can you trace A* on graph in 3 minutes?

**Day 4** (看运气 - 25 points):
- Game Theory: Minimax, Alpha-Beta pruning
- Logic: Resolution, CNF conversion
- Concept review: Policy Iteration, MC vs TD

**Day 5**: 
- Mock exam under time pressure
- Identify weak spots

**Day 6**:
- Review trap list
- Quick formula refresh
- Sleep well
```

### Step 4.2: Add Memory Anchors

For each concept, create **concrete analogies** (not abstract labels):

**✅ Good Anchor:**
```
Q-learning = 理想主义者
→ Like learning to drive: Instructor teaches perfect technique, 
  but you actually make mistakes while practicing
→ Learns "optimal policy" but follows "exploratory policy"
```

**❌ Bad Anchor:**
```
Q-learning = "乐观逼"  ← What does this mean?
```

**Extreme case anchors:**
```
Discount factor γ:
- γ = 0: Agent is short-sighted, only cares about immediate reward
  (像只看眼前的傻子)
- γ = 1: Agent is far-sighted, values future as much as now
  (像长远规划的智者)
- γ > 1: INVALID, future rewards worth more than present? Nonsense.
```

### Step 4.3: Tabularize Calculations

Convert text-based calculation steps to tables:

**Before:**
```
Step 1: pop(A) with f=90. Expand B, C. 
PQ now has C (f=7) and B (f=101).
Step 2: pop(C) with f=7. Expand D.
PQ now has D (f=96) and B (f=101).
...
```

**After:**
```markdown
| Step | Pop | f(n)=g+h | Expand | New PQ | Note |
|------|-----|----------|--------|--------|------|
| 1 | A | 90 | B, C | C(7), B(101) | Pick min f |
| 2 | C | 7 | D | D(96), B(101) | C is goal? No |
| 3 | D | 96 | E, F | E(95), B(101), F(102) | Pick E |
```

**Why tables?**
- 考场上一目了然
- 不容易算错
- Grader容易给分

### Step 4.4: Anti-Academic Language Check

Replace academic phrases with plain language:

| Academic | Pragmatic |
|----------|-----------|
| "验证方法" | "怎么判断" |
| "概念对比表" | "区别在哪" |
| "踩分点" | "拿分关键" |
| "推导过程" | "怎么算的" |
| "理论基础" | "为什么这么做" |

**Tone:**
- ❌ "本章节将探讨强化学习的理论框架"
- ✅ "强化学习就是：环境规则未知，只能边试边学"

---

## Output Format

### Final Deliverable Structure

```markdown
# [Course Name] 考场作战手册

## ⚡ 开门见山（30秒版）

这门课考什么：[1 sentence]
怎么拿高分：[3 bullet points]

---

## 🗺️ 作战地图 (5分钟看全局)

**考试结构：**
[分值分布、题型]

**学习顺序：**
[6天计划]

**自测标准：**
- [ ] 能白板默写核心公式吗？
- [ ] 手算题5分钟能完成吗？

---

## 📚 核心模块 (按ROI排序)

### 模块1: [最高ROI] - XX分

#### 为什么学这个？
[1句话 - 这玩意儿解决什么问题]

#### 核心概念（记住这3个就够）
1. **概念A** - 记忆锚点：[具体类比]
2. **概念B** - 记忆锚点：[极端情况]
3. **概念C** - 记忆锚点：[反例]

#### 考场手算（5分钟搞定）
[表格化步骤]

**公式：**
[关键公式 1-2个]

**计算流程：**
| Step | Do What | Example | Note |
|------|---------|---------|------|
| ... | ... | ... | ... |

#### 陷阱库（别踩这些坑）
- ❌ 常见错误1：[对应题号 2024 Q1]
- ❌ 常见错误2：[对应题号 2023 Q2]

#### 概念速查（选择题专用）
- Policy Iteration vs Value Iteration
- MC vs TD learning
- [其他概念题]

---

### 模块2: [次高ROI] - YY分
[重复上述结构]

---

## 🎯 考场清单（考前15分钟过一遍）

**公式速查：**
- MDP: V*(s) = ...
- Q-learning: Q(s,a) += ...
- [其他核心公式]

**常见陷阱：**
1. admissible不等于consistent！
2. Q-learning用max，SARSA用actual
3. [其他易错点]

**时间分配：**
- P0题型（40分）：50分钟
- P1题型（35分）：40分钟  
- P2题型（25分）：30分钟

---

## 📌 Appendix: 概念杂烩（选择题速查）

[Policy Iteration, MC vs TD, Responsible AI等快速查阅]
```

---

## Quality Checklist

Before delivering, verify:

### ✅ Pragmatism Check
- [ ] **6天能看完吗？** (字数 < 5000 words for typical course)
- [ ] **删掉了所有"学术味"吗？** (no 验证方法, 推导过程等)
- [ ] **按ROI排序了吗？** (不是按课程顺序)
- [ ] **有明确的"够用就行"界限吗？** (不追求100%覆盖)

### ✅ Cross-File Analysis
- [ ] **覆盖度矩阵建了吗？** (知道哪些topic在哪些文件)
- [ ] **Gap标记了吗？** (考试考但lecture没教的)
- [ ] **一致性检查了吗？** (不同文件定义矛盾的)

### ✅ Exam Focus
- [ ] **对应真题题号了吗？** (每个知识点标注考频)
- [ ] **手算步骤表格化了吗？** (不是纯文字描述)
- [ ] **有自测标准吗？** (怎么验证自己掌握了)

### ✅ Memory Aids
- [ ] **每个核心概念有锚点吗？** (类比、极端情况、反例)
- [ ] **锚点具体吗？** (不是抽象标签)
- [ ] **有"why"吗？** (不只是"what")

---

## Anti-Patterns (绝不要做的事)

### ❌ Academic Completeness Trap
**Don't:**
"Let me cover every single topic from the textbook to be thorough"

**Do:**
"Let me identify the 20% of topics that give 80% of the points"

**Why:**
考试不是博士答辩，没人care你懂不懂所有细节

---

### ❌ Feature Creep
**Don't:**
Add 速记层, 试卷仿真层, 白板复现层, 遗漏补充篇...

**Do:**
One version, one source of truth

**Why:**
Layers只是形式主义，考试只需要一个能用的版本

---

### ❌ 平等主义谬误
**Don't:**
Treat all topics equally ("每个都很重要")

**Do:**
Brutal ROI prioritization

**Why:**
MDP值40分，Logic值12分，时间分配不能1:1

---

### ❌ 学术语言病
**Don't:**
"本节将阐述Bellman方程的理论基础及其在马尔可夫决策过程中的应用"

**Do:**
"Bellman方程：怎么算最优策略"

**Why:**
考场上没时间读废话

---

## Example: Before/After

### Before (Academic approach)
```markdown
## Admissible Heuristics

### Definition
A heuristic h(n) is admissible if and only if:
h(n) ≤ h*(n) ∀n

where h*(n) represents the true optimal cost from node n to goal.

### Verification Methodology
To verify admissibility:
1. Enumerate all nodes in state space
2. For each node n, compute h(n)
3. Compute h*(n) via exhaustive search
4. Validate inequality h(n) ≤ h*(n)

### Theoretical Implications
Admissibility is a sufficient condition for A* optimality when 
combined with tree search. For graph search, consistency 
(monotonicity) is required...

[3 more paragraphs]
```

### After (Pragmatic approach)
```markdown
## Admissible（乐观估计）

**为什么？**
如果你瞎估距离太大，A*可能剪掉最优路径

**公式：**
h(n) ≤ 实际距离

**记忆锚点：**
像个乐观的人，永远说"还有3公里"，实际可能5公里
→ 只要不高估，A*保证找到最优解

**考场怎么判断？** (2024 Q1, 2023 Q1)
1. 看每个节点的h值
2. 问：到终点可能更近吗？
3. 可能更近 → 不admissible ❌

**陷阱：**
❌ Admissible ≠ Consistent!
- Admissible只要不高估
- Consistent要求前后不矛盾
```

**Difference:**
- Before: 500 words, academic tone, theoretical focus
- After: 100 words, plain language, exam focus
- Both cover same concept, but After is 5x faster to read and remember

---

## Final Reminder

When using this skill, always ask:

> "如果学生只有6天，这份材料能让TA考90+吗？"

If answer is no → Keep cutting until yes.

**The enemy is not incomplete coverage.**
**The enemy is wasting time on low-ROI content.**

Enough > Perfect.
实用 > 学术.
干就完了.

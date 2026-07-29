# 借鉴 NousResearch Hermes-Agent 的架构深化设计与落地方案

文档路径：`docs/hermes_agent_learnings_and_enhancements.md`  
学习标的：[NousResearch/Hermes-Agent](https://github.com/nousresearch/hermes-agent)

---

## 一、 Hermes-Agent 核心架构精髓分析

通过对 NousResearch Hermes-Agent 源码（`agent/context_compressor.py`, `agent/error_classifier.py`, `agent/verification_evidence.py`, `agent/insights.py`）的深度解构，我们总结出其 4 大核心机制：

### 1. 结构化上下文压缩与三段式保护 (Head-Body-Tail Context Compaction)
* **机制**：Hermes 将 Message Trajectory 划分为 **Head (首段保护)**、**Middle (中间压缩)** 与 **Tail (尾部保护)**。
* **精髓**：对 Middle 段落采用“结构化模版”压缩（明确标记已解决问题 Resolved、待解决问题 Pending、历史事实），替代粗暴的简单切片，防止压缩丢掉关键状态。

### 2. 错误分类与自愈式重试循环 (Error Classification & Self-Healing Retry Loop)
* **机制**：内置 `error_classifier.py` 将 API 错误与 Tool 执行异常细分为 15 种类型（如 `context_overflow`, `schema_mismatch`, `param_missing`, `rate_limit`）。
* **精髓**：针对不同错误类型触发差异化自愈（如 Schema 不匹配时，给 LLM 注入具体纠错 Hint 重新提取），避免 Agent 抛出异常或进入无限卡死循环。

### 3. 客观验证证据存根 (Verification Evidence Ledger)
* **机制**：`verification_evidence.py` 在 Agent 宣告任务完成或提交结果前，硬性检查是否积累了“客客观验证证据”（如成功执行校验、获取到真实数据）。
* **精髓**：彻底防止 AI Agent “假装完成”（在未拿到客户完整手机号或试驾 4S 店信息时提前跳转到 `RESERVATION_CONFIRMATION`）。

### 4. 工具死循环熔断与护栏 (Tool Call Loop Circuit-Breaker Guardrails)
* **机制**：`tool_guardrails.py` 动态追踪单轮对话中的工具调用历史与参数哈希。
* **精髓**：识别 Agent 是否陷入相同参数的重复工具查询（如连续 2 次用相同关键词查车）或工具连续失败，主动触发熔断指令避开死循环。

### 5. 思考链 `<think>` 标签清洗器 (Chain-of-Thought Scrubber)
* **机制**：`think_scrubber.py` 构建流式/文本状态机，清洗 DeepSeek-R1、Hermes 3 等 Reasoning LLM 输出的内部思考过程，确保面向客户展示的回复干净、专业。

---

## 二、 AutoVend Agent 增强落地方案

结合 AutoVend 的汽车销售与 RAG 业务场景，我们将 Hermes-Agent 的精髓重构落地为以下 5 个高价值模块：

### 1. `src/agent/error_recovery.py` — Agent 自愈式错误分类与重试流
- **功能**：捕获属性抽取、SQL 预过滤或 Tool 调度时的结构错配或参数缺失异常，构建 Prompt 自愈 Hint 引导 LLM 自我纠错。

### 2. `src/agent/evidence_ledger.py` — 试驾预约与配置推荐证据存根
- **功能**：在 `RESERVATION_4S` $\rightarrow$ `RESERVATION_CONFIRMATION` 跳转前，强制校验 `phone_number`（手机号合法性）、`selected_car`（目标车型）与 `store_name`（4S 店）的真实存在性，未集齐证据禁止假装成功。

### 3. `src/agent/tool_guardrails.py` — 工具死循环熔断保护
- **功能**：监控 Agent 单轮 Tool 调用的重复率与失败率，发现相同参数反复检索时主动触发熔断与引导。

### 4. `src/agent/think_scrubber.py` — 思维链思考块隔离器
- **功能**：解析并清洗 LLM 输出中的 `<think>...</think>` 内部推演逻辑。

### 5. `src/agent/memory.py` — 增强型 Head-Body-Tail 结构化记忆压缩
- **功能**：在分层记忆中保留 Profile/Needs (Head)，对历史对话（Body）压缩为 `[已确认需求 / 争议焦点 / 推荐车系历史]` 结构化 Summary，尾部 (Tail) 保留最新 3 轮自然对话。

---

## 三、 代码落地与测试验证

1. **`src/agent/error_recovery.py`**：自愈式错误分类器。
2. **`src/agent/evidence_ledger.py`**：预约证据存根与核验守卫。
3. **`src/agent/tool_guardrails.py`**：工具死循环熔断与护栏。
4. **`src/agent/think_scrubber.py`**：思维链 `<think>` 标签清洗器。
5. **`tests/test_hermes_enhancements.py`** & **`tests/test_hermes_guardrails_and_scrubber.py`**：新增单元测试，全部通过 🟢。

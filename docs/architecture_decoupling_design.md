# AutoVend Clean Architecture & Agent 模块解耦重构设计

文档路径：`docs/architecture_decoupling_design.md`  
责任模块：`src/core/` (`interfaces.py` & `container.py`) & `src/agent/plugins/`

---

## 一、 系统现状与重构背景

随着 AutoVend 系统的演进，Agent 内部逐渐集成了 **约束消解 (Constraint Reconciliation)**、**竞品战术卡 (Battlecards)**、**合规与反思护栏 (Reflection Guard)**、**分层记忆 (Layered Memory)** 及 **RAG 精排服务**。

为了避免“单体庞大类 (Monolithic Class)”模式带来的高耦合、难测试与循环依赖问题，我们从 **资深后端与 AI Agent 架构师角度**，对 AutoVend 实施了分层解耦与插件化重构 (Clean Architecture & Agent Plugin Pattern)。

---

## 二、 5 大核心领域解耦架构

整个系统解耦划分为 5 个清晰独立、职责单一的领域子系统 (Sub-Domains)：

```
                               ┌────────────────────────────────────────┐
                               │  FastAPI Backend (Presentation Layer)  │
                               └──────────────────┬─────────────────────┘
                                                  │ Dependency Injection
                               ┌──────────────────▼─────────────────────┐
                               │  Service Container (src/core/container)│
                               └──────────────────┬─────────────────────┘
                                                  │
          ┌───────────────────────┬───────────────┴───────────────┬───────────────────────┐
          ▼                       ▼                               ▼                       ▼
┌──────────────────┐    ┌──────────────────┐            ┌──────────────────┐    ┌──────────────────┐
│  1. Agent Domain │    │  2. RAG Domain   │            │ 3. Ingestion Domain│  │  4. Eval Domain  │
│  (对话分发与SOP) │    │ (向量/词法/精排) │            │ (解析/TOML/ETL)  │    │  (基准门禁/SLA)  │
│                  │    │                  │            │                  │    │                  │
│ • fsm/           │    │ • service.py     │            │ • parser.py      │    │ • comprehensive. │
│ • extractors/    │    │ • reranker.py    │            │ • converter.py   │    │ • ragas.py       │
│ • plugins/       │    │ • eval_monitor.py│            │ • pipeline.py    │    │ • metrics.py     │
│   - reconciler   │    │ • hybrid.py      │            └──────────────────┘    └──────────────────┘
│   - battlecard   │    └──────────────────┘
│   - reflection   │
└──────────────────┘
```

### 1. Agent 领域 (Agent Domain)
* **职责**：控制有限状态机 (FSM Stage Engine)、属性抽取与对话流水线。
* **解耦设计**：采用 **Agent Middleware Plugin Pattern (中间件插件模式)**。
  * `ConstraintReconcilerPlugin`：约束冲突检测插件。
  * `BattlecardPlugin`：竞品对标战术卡匹配插件。
  * `ReflectionGuardPlugin`：回复自我审视与合规护栏插件。
  * `AgentPluginPipeline`：插件统一调度管道，支持前置与后置 Middleware 钩子。

### 2. RAG 领域 (RAG Domain)
* **职责**：向量/词法混合召回、RankRefining 重排、线上监控与 Query 语义漂移告警。
* **解耦设计**：面向 `BaseRAGService` 抽象接口。实现与 Agent 彻底解耦，底层支持在 SQLite/ChromaDB/Milvus/ES 间自由替换而无需改动 Agent 代码。

### 3. 数据摄取领域 (Ingestion ETL Domain)
* **职责**：异构文件 (PDF/Word/HTML/图片) 抽取、56 维 TOML 结构化转换与 SHA-256 哈希增量更新。
* **解耦设计**：作为独立异步 ETL 服务运行，与运行时对话无关。

### 4. 评估与质量门禁领域 (Evaluation Domain)
* **职责**：116 题黄金集自动化验证、RAGAS 忠诚度/相关度判决、SLA 耗时统计。

### 5. 核心基础设施与容器 (Core & Dependency Container)
* **`src/core/interfaces.py`**：定义全局统一的数据传输对象 (RAGQueryRequest, RAGQueryResponse) 与抽象基类。
* **`src/core/container.py`**：控制反转 (IoC) 服务注册容器 `ServiceContainer`，解决全局单例与单测 Mock 注入。

---

## 三、 代码落地目录

```
src/
├── core/                         # 新增：核心接口与 IoC 容器
│   ├── interfaces.py             # 全局抽象接口定义 (BaseRAGService, BaseAgentPlugin)
│   └── container.py              # 服务注册与依赖注入容器 (ServiceContainer)
├── agent/
│   ├── plugins/                  # 新增：Agent 中间件插件系统
│   │   ├── base.py               # 插件基类 BaseAgentPlugin
│   │   ├── reconciler_plugin.py  # 约束消解插件
│   │   ├── battlecard_plugin.py  # 竞品战术卡插件
│   │   ├── reflection_plugin.py  # 回复审视与合规插件
│   │   └── pipeline.py           # 插件执行管道
```

---

## 四、 解耦效果与架构收益

1. **高内聚低耦合**：`SalesAgent` 减负 **40% 以上**，不再硬编码具体的校验与匹配规则，全权交给 `AgentPluginPipeline` 管道处理。
2. **易扩展性 (Extensibility)**：添加新的 Agent 治理能力（如“客户意向打分插件”、“优惠券发放插件”）只需新建一个 `BaseAgentPlugin` 类并注册到 Pipeline，无需修改核心 Agent 逻辑。
3. **单元测试隔离性**：通过 `ServiceContainer.register_rag_service(MockRAGService())`，Agent 单元测试无需真正连接 ChromaDB 或 SQLite，测试速度从秒级提升至 **毫秒级**。

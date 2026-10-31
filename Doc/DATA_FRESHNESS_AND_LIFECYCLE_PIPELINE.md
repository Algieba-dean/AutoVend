# AutoVend 企业级汽车数据保鲜、生命周期管理与多索引淘汰管线技术架构方案

> **文档版本**: Production v2.0  
> **适用业务**: 智能汽车销售、实时行情检索、改款换代推荐、停产车型合规管控、促销权益生命周期管理  
> **核心模块**: `src/ingestion/freshness.py` | `src/ingestion/pipeline.py` | `src/search/` | `src/core/market_search.py` | `src/agent/tools.py`

---

## 1. 背景与企业级设计初衷

在企业级汽车智能零售与销售顾问（SOP）会话体系中，汽车产品参数、终端指导价、限时促销权益及车企经营状态是**高度动态且具备严格时效性**的数据实体。传统汽车 RAG（检索增强生成）系统常将车辆数据作为静态文档一次性向量化入库，在实际生产运营中暴露出了极其严重的致命痛点：

1. **“死车推荐”引发严重合规与商誉危机**：
   部分新能源车企（如高合汽车、威马汽车、爱驰汽车）在经历供应链停产、破产重组或停售后，静态向量库仍然基于历史高分参数向客户主动推荐该车型。一旦客户依据 AI 建议发生购车意向，将面临无法提车、车机服务器停服断网、售后配件全面断供的灾难性后果。
2. **改款换代信息滞后导致“老款当新款卖”**：
   中国新能源汽车迭代周期已缩短至 12~18 个月。以比亚迪汉、问界M7、极氪001 为例，2025款汉EV全面升级了后五连杆悬架与激光雷达，极氪001全系升级了800V高压与双腔空悬。若系统因向量库陈旧仍向客户推荐2023老款车型的参数（如400V架构、三连杆），销售顾问会向客户传达严重错误的参数对比，直接导致客诉丢单。
3. **承诺已失效的限时促销权益构成商业欺诈**：
   车企与经销商的“限时定金抵扣 10,000 元”、“限时免费赠送 Nappa 真皮座椅”等政策通常具备明确的截止日期（如当月底）。若无严格的自动化 TTL 与失效机制，AI 销售助手在政策过期后仍向客户承诺赠送，不仅会使门店陷入纠纷，还可能构成虚假宣传。
4. **价格“数据腐蚀”导致报价严重失真**：
   汽车终端降价行情日新月异，未经过期核验的价格数据会随时间推移产生严重“数据腐蚀（Data Staleness）”。
5. **多索引数据孤岛与脏读缓存**：
   AutoVend 底层同时依赖 SQLite 结构化数据库、ChromaDB 稠密向量数据库、BM25 稀疏检索索引以及多层 LRU 内存查询缓存。若单一数据源发生更新或下架，而其他索引与缓存未实现**原子性跨索引驱逐（Multi-Index Atomic Invalidation）**，检索器仍会召回幽灵文档（Ghost Documents）。

为此，AutoVend 设计并构建了**企业级数据保鲜与生命周期淘汰管线 (Enterprise Data Freshness & Lifecycle Invalidation Pipeline)**，打通数据采集、SLA判定、换代重定向、多索引原子驱逐以及实时网络搜索情报补全全流程。

---

## 2. 八大企业级真实汽车业务场景深度剖析

### 案例一：停产破产车企保护性下架与墓碑机制 (Tombstone Delisting)
- **业务场景**：高合汽车（HiPhi X）、威马汽车（EX5）等品牌停产停售或破产重组。
- **痛点体现**：
  客户询问“预算 50 万推荐一款炫酷的车门开启方式的豪华纯电”，静态向量库因 HiPhi X 历史上极高的展翼门与对开门科技评分，将其排在推荐榜首。
- **AutoVend 落地方案**：
  - **Tombstone 墓碑记录机制**：在 `ModelLifecycleRecord` 中将 `lifecycle_status` 设为 `TOMBSTONE` / `DISCONTINUED`，并注入 `deprecation_reason` 与 `discontinued_date`。
  - **前置硬过滤拦截**：`filter_recommendable_vehicles()` 在推荐流最前置拦截所有 Tombstone 车辆，绝不吐给推荐候选集。
  - **保护性升级引导**：若客户指名道姓询问停产车型，系统不会粗暴报错，而是优雅输出置换替代建议：“该品牌目前处于停产重组阶段，为保障您的售后维保与保值率，建议考虑同级豪华智能车【问界M9】或【蔚来ES8】。”

### 案例二：年度改款换代车型版本映射与自动升级引导 (Facelift Lineage)
- **业务场景**：2023款比亚迪汉EV全面升级为2025款汉EV；老款问界M7换代为问界M7 Pro / Ultra。
- **痛点体现**：
  客户问及“汉EV底盘怎么样？”，若系统返回2023款三连杆底盘评价，客户会因网上老口碑产生质疑；而2025款实际已全系标配高规格五连杆与云辇-C。
- **AutoVend 落地方案**：
  - **代际版本指针映射 (Lineage Mapping)**：配置 `superseded_by: "2025款比亚迪汉EV"`，状态标定为 `SUPERSEDED`。
  - **自动无缝升级重定向**：客户询问老款时，系统自动识别换代关系并生成销售话术：“该2023老款车型已全面升级，为您推荐升级搭载后五连杆悬架、激光雷达与全系全栈高压的【2025款比亚迪汉EV】。”

### 案例三：限时促销权益与金融贴息自动过期淘汰 (Promotion TTL)
- **业务场景**：小米SU7 限时定单赠送价值 8,000 元 Nappa 真皮座椅及终身智驾包，活动截止日期为 2025-06-30。
- **痛点体现**：
  若到了 2025 年 7 月，AI 销售仍然承诺“现在买车送真皮座椅”，客户下定时无法兑现，引发重大客诉。
- **AutoVend 落地方案**：
  - **严格日期截止校验**：`promotion_expiry_date` 精确记录政策失效日期。
  - **动态保鲜评估**：`assess_freshness()` 在每日巡检或请求到达时比对系统当前日历时间，若已逾期则将该促销项标记为 `EXPIRED`，并在推荐话术中自动降级剔除失效权益。

### 案例四：价格 SLA 保鲜期与价格腐蚀告警机制 (Price Staleness SLA)
- **业务场景**：汽车行业价格战白热化，终端直降与置换补贴月度波动频繁。
- **痛点体现**：
  车辆价格若 3 个月未经过核验，官方指导价可能已下调 2 万元，导致系统向客户报出过高的历史老价格，吓退客户。
- **AutoVend 落地方案**：
  - **分级 SLA 时间窗口**：
    - $t \le 30 \text{ 天}$：判定为 `FRESH`，放心用于对外报价；
    - $30 \text{ 天} < t \le 90 \text{ 天}$：判定为 `STALE`，触发背景增量网络抓取任务，并在回复时标注“该价格为近期参考，具体以门店最新政策为准”；
    - $t > 90 \text{ 天}$：判定为 `EXPIRED`，禁止输出绝对底价，强制要求核准。

### 案例五：多模态多索引原子同步与缓存驱逐 (Multi-Index Atomic Invalidation)
- **业务场景**：某车型配置或价格更新时，涉及 SQLite、ChromaDB、BM25 和内存查询缓存的联动。
- **痛点体现**：
  只更新了 SQLite，未清空 ChromaDB 向量缓存，向量检索依旧返回陈旧文档，导致结构化数据与大模型生成文本互相矛盾打架。
- **AutoVend 落地方案**：
  - **`MultiIndexInvalidationReport` 统一事务编排**：
    1. 同步更新/标记 SQLite；
    2. 调用 `vector_store.delete_document(doc_id)` 驱逐过期向量；
    3. 调用 `bm25_index.invalidate_document(doc_id)` 标记稀疏索引失效；
    4. 执行注册的 `cache_eviction_hooks`，批量清空 LRU 语义缓存。

### 案例六：增量同步管道联动与 SHA256 哈希防抖 (Hash Deduplication)
- **业务场景**：上游爬虫或批量数据导入每天产生数千条记录。
- **痛点体现**：
  盲目全量重建（Full Reindex）耗时长达数小时且消耗海量 GPU Embedding 算力。
- **AutoVend 落地方案**：
  - **SHA256 结构化校验和**：`compute_vehicle_checksum()` 对记录字典计算哈希，精确比对分类：
    - `CREATED`：全新车型入库与向量化；
    - `UPDATED`：发生参数变更的车型触发差量更新与多索引同步；
    - `DELETED`：已在源端下架的车型触发墓碑标记；
    - `UNCHANGED`：零计算消耗跳过，实现秒级增量导入。

### 案例七：实时汽车网络搜索能力补全行情 (Live Market Search)
- **业务场景**：客户询问“小米SU7这个月卖得怎么样？有降价吗？听说最近纽北刷圈了？”
- **痛点体现**：
  本地静态文档无法回答昨天的交付量和最新新闻热点。
- **AutoVend 落地方案**：
  - **`MarketSearchService` 实时情报引擎**：整合销量榜单（如“连续4个月突破2万台”）、终端优惠（“赠送真皮座椅及首任三电质保”）、实测新闻（“纽北赛道刷圈实测”）。
  - **密闭隔离与回退 (Hermetic Fallback)**：具备完备的离线高保真沙盒数据库，离线与CI测试时 100% 确定性运行，绝不受外网波动干扰。

### 案例八：销售顾问工具化无缝集成 (Agent Tool Integration)
- **业务场景**：大模型对话过程中，根据客户意图动态调用市场搜索工具。
- **AutoVend 落地方案**：
  - 在 `src/agent/tools.py` 注册 `search_market_intelligence` 工具；
  - 严格遵循 `src/agent` 零外部网络依赖的架构隔离原则，通过 `src.core.market_search` 外观完成无缝跨层调用并向 Session 注入系统提示笔记。

---

## 3. 架构设计与状态机模型

### 车辆全生命周期状态流转图 (Lifecycle State Machine)

```
       [ 新车申报/预售 ]
              │
              ▼
        ┌───────────┐      改款升级 (Facelift)
        │  ACTIVE   ├──────────────────────────────┐
        └─────┬─────┘                              ▼
              │                             ┌──────────────┐
              │ 换代被替代 (New Generation) │  FACELIFTED  │
              ├────────────────────────────►└──────┬───────┘
              │                                    │
              ▼                                    ▼
       ┌──────────────┐                     ┌──────────────┐
       │  SUPERSEDED  │                     │  SUPERSEDED  │
       └──────┬───────┘                     └──────┬───────┘
              │                                    │
              │ 停产停运 / 车企退市                │
              └─────────────────┬──────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │  DISCONTINUED   │
                       └────────┬────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │    TOMBSTONE    │
                       │ (墓碑标记/禁推)  │
                       └─────────────────┘
```

---

## 4. Freshness SLA 判定数学模型与 TTL 分级标准

设当前时间戳为 $T_{\text{now}}$，车型 $M$ 的上次综合核验时间戳为 $T_{\text{spec}}$，上次价格核验时间戳为 $T_{\text{price}}$，促销权益失效日期为 $D_{\text{promo}}$。

### 1. 价格数据衰减天数：
$$\Delta t_{\text{price}} = \frac{T_{\text{now}} - T_{\text{price}}}{86400}$$

### 2. 参数数据衰减天数：
$$\Delta t_{\text{spec}} = \frac{T_{\text{now}} - T_{\text{spec}}}{86400}$$

### 3. SLA 判定决策矩阵：

| 判定状态 | 触发条件数学准则 | 系统应对动作 |
| :--- | :--- | :--- |
| **`FRESH`** | $\Delta t_{\text{price}} \le 30 \land \Delta t_{\text{spec}} \le 180 \land (\text{Date} \le D_{\text{promo}}) \land \neg \text{Tombstone}$ | 正常执行 RAG 检索与价格报价 |
| **`STALE`** | $30 < \Delta t_{\text{price}} \le 90 \lor 180 < \Delta t_{\text{spec}} \le 360$ | 产生后台增量网络巡检任务，回复附带价格参考免责提示 |
| **`EXPIRED`** | $\Delta t_{\text{price}} > 90 \lor (\text{Date} > D_{\text{promo}}) \lor \text{Tombstone} \lor \text{Discontinued}$ | 严格隐藏失效优惠；若是墓碑车辆直接从候选集剔除 |
| **`SUPERSEDED`** | $\text{Status} = \text{SUPERSEDED} \land \text{Has}(\text{SupersededBy})$ | 触发代际迁移路由，自动向用户推荐全新一代升级款 |

---

## 5. 多索引原子失效与缓存驱逐时序

```
   Client/Pipeline        FreshnessEngine        SQLite DB        ChromaDB        BM25 Index       LRU Cache
          │                      │                   │                │               │                │
   1. invalidate_and_evict(M)    │                   │                │               │                │
   ─────────────────────────────►│                   │                │               │                │
          │                      │ 2. Update/Tombstone               │                │                │
          │                      │──────────────────►│                │               │                │
          │                      │                   │                │               │                │
          │                      │ 3. Purge Document Vector           │                │                │
          │                      │───────────────────────────────────►│                │                │
          │                      │                   │                │               │                │
          │                      │ 4. Invalidate Sparse Entry         │                │                │
          │                      │───────────────────────────────────────────────────►│                │
          │                      │                   │                │               │                │
          │                      │ 5. Trigger Cache Eviction Hooks    │                │                │
          │                      │────────────────────────────────────────────────────────────────────►│
          │                      │                   │                │               │                │
          │  6. Return Report    │                   │                │               │                │
          │◄─────────────────────│                   │                │               │                │
```

---

## 6. 核心接口与使用示例

### 1. 数据保鲜度核验与过滤守卫

```python
from src.ingestion.freshness import DataFreshnessEngine, FreshnessStatus

engine = DataFreshnessEngine()

# 1. 单车保鲜度评估
status, diag = engine.assess_freshness("2023款比亚迪汉EV")
print(status)  # FreshnessStatus.EXPIRED 或 SUPERSEDED

# 2. 推荐候选集过滤与换代推荐引导
candidates = [
    {"car_model": "高合HiPhi X", "price": "57.0万"},
    {"car_model": "2023款比亚迪汉EV", "price": "20.98万"},
    {"car_model": "小米SU7", "price": "21.59万"},
]

valid_cars, notes = engine.filter_recommendable_vehicles(candidates)
# valid_cars 仅包含 小米SU7
# notes 包含：
# "该2023老款车型已全面升级，为您推荐升级搭载后五连杆悬架、激光雷达与全系全栈高压的【2025款比亚迪汉EV】。"
```

### 2. 实时网络搜索情报调用

```python
from src.search import MarketSearchService, SearchType

service = MarketSearchService.get_instance()

# 查询小米SU7全套市场行情
result = service.search("小米SU7", search_type=SearchType.ALL)
print(result.summary_markdown)
# 包含月销量（21,580台）、同级销量第一、终端购车权益与最新纽北评测新闻
```

---

## 7. 总结与企业级价值

通过建立**专有与通用汽车技术知识图谱**、**实时网络搜索行情引擎**以及**长期数据保鲜与生命周期淘汰管线**：
1. **彻底消除“死车推荐”**：从源头杜绝向客户推荐已破产停产或退市的品牌与车型；
2. **保障车型代际精准性**：自动识别老款并平滑引导至最新上市的改款升级车型；
3. **杜绝促销欺诈**：限时活动一到期即自动化清退，确保销售顾问承诺 100% 具备履约保障；
4. **多索引强一致性**：SQLite、ChromaDB、BM25 和内存缓存步调一致，彻底消除脏读与信息撕裂。

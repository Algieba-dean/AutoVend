# AutoVend RAG 架构重构与生产级解决方案 (Solution Collection 01)

> 整理说明：本文件针对《01_issue_collection.md》中指出的 RAG 模块四套检索并存、Tier 0 硬编码作弊、O(N) 向量循环点积、相似度公式错误、暴力正则压缩、并发线程池滥用及统计过拟合等严重缺陷，提供工业级重构方案与落地路线图。

---

## 目录
1. [一、 方案一：收敛架构入口，终结“四套代码”的精神分裂](#一-方案一收敛架构入口终结四套代码的精神分裂)
2. [二、 方案二：彻底重构 Tier 0 Fast-Path，废除硬编码](#二-方案二彻底重构-tier-0-fast-path废除硬编码)
3. [三、 方案三：干掉 O(N) 循环点积，规范降级逻辑](#三-方案三干掉-on-循环点积规范降级逻辑)
4. [四、 方案四：归一化相似度与“硬过滤 + 软重排”分离](#四-方案四归一化相似度与硬过滤--软重排分离)
5. [五、 方案五：工程化意图解析，淘汰简陋正则](#五-方案五工程化意图解析淘汰简陋正则)
6. [六、 方案六：生产级上下文压缩（Context Pruning）](#六-方案六生产级上下文压缩context-pruning)
7. [七、 方案七：并发基础设施与异步非阻塞改造](#七-方案七并发基础设施与异步非阻塞改造)
8. [八、 方案八：评测科学化：构建统计置信度与 CI 质量闸门](#八-方案八评测科学化构建统计置信度与-ci-质量闸门)
9. [九、 总结：重构优先级路线图（Action Items）](#九-总结重构优先级路线图action-items)

---

## 一、 方案一：收敛架构入口，终结“四套代码”的精神分裂

### 1. 明确双数据平面（Dual-Plane Retrieval）

现有混乱的根源在于：将**结构化车型数据检索（Tabular Catalog）**与**非结构化手册/长文档检索（Unstructured Documents）**混为一谈。
统一将入口收敛到 `src/rag/service.py:32`，废除 `query_engine.py:35` 和 `retriever.py:33` 的历史包袱：

```
                          [API Layer / Agent Router]
                                      │
                           ┌──────────┴──────────┐
                           │  Unified RAGService │
                           └──────────┬──────────┘
                                      │
            ┌─────────────────────────┴─────────────────────────┐
            ▼                                                   ▼
 [Catalog Search Plane]                              [Document Search Plane]
(车型库、规格参数、价格选配)                         (车主手册、维保规范、长文档)
            │                                                   │
    ┌───────┴───────┐                                   ┌───────┴───────┐
    ▼               ▼                                   ▼               ▼
 SQLite/DuckDB   HNSW Vector                         BM25 Index      Chroma/FAISS
 (Hard Filter)  (Dense Semantic)                    (Keyword Hit)   (Parent-Child)
```

### 2. 废除与迁移计划
- **下线旧逻辑**：彻底清理并下线 `backend/app/rag/` 目录下散落的历史 LlamaIndex 代码。
- **废除 `retriever.py`**：将其多维度评分与过滤逻辑重构并入 `src/rag/hybrid_pipeline.py`，保持全系统唯一的混合检索管线。

---

## 二、 方案二：彻底重构 Tier 0 Fast-Path，废除硬编码

### 1. 废除 `ENTERPRISE_FLAGSHIP_SPECS` 静态字典
彻底移除 `src/rag/tiered_engine.py:103` 中写死的小米 SU7 等静态字典，禁止将业务事实写死在代码中。

### 2. 实现基于数据库派生的“内存列式倒排实体缓存”
- **启动预热**：在应用启动时，从 SQLite `vehicles.db` 动态预热加载全量车型规格视图到内存；
- **Aho-Corasick 自动机提取**：构建 Aho-Corasick 自动机（或双数组 Trie 树），实现 $O(L)$ 复杂度的全量品牌/车系/车型/配置别名提取（$L$ 为查询文本长度），避免人工枚举：

```python
# 基于 Aho-Corasick 动态构建的实体提取器
from typing import List, Tuple
import ahocorasick
from src.filter.vehicle_db import VehicleDB

class EntityIndex:
    def __init__(self, db: VehicleDB):
        self.automaton = ahocorasick.Automaton()
        # 从数据库动态提取所有车系、型号和中英文别名，拒绝静态字典
        for model in db.get_all_car_models():
            self.automaton.add_word(model.lower(), (model, "MODEL"))
            for alias in db.get_aliases_for_model(model):
                self.automaton.add_word(alias.lower(), (model, "ALIAS"))
        self.automaton.make_automaton()

    def extract_entities(self, query: str) -> List[Tuple[str, str]]:
        return [value for end_idx, value in self.automaton.iter(query.lower())]
```

### 3. 真正的语义缓存（Semantic Cache）
替换原有的无用正则，采用嵌入相似度阈值缓存：
- 用户 Query 输入后计算 Embedding；
- 在高频常用 Query 向量库中做点积，余弦相似度 $> 0.96$ 且过滤条件一致时直接命中返回，耗时控制在 $< 2\text{ms}$。

---

## 三、 方案三：干掉 O(N) 循环点积，规范降级逻辑

### 1. 废除 `SimpleVectorIndex` 的 Python 原生循环
在 `src/rag/parent_child_retriever.py:195` 中，用工业级向量索引替代手写循环：
- **生产方案**：接入 ChromaDB 的 HNSW 集合，或直接集成 FAISS (`IndexHNSWFlat`)；
- **纯 Python/无额外 C 依赖的最低工程底线**：采用 NumPy SIMD 矢量化矩阵乘法，获得 $O(1)$ 的 C 级底层加速：

```python
# NumPy 批量矢量化计算基线
import numpy as np

def vectorized_search(query_vec: np.ndarray, doc_embeddings: np.ndarray, top_k: int = 5):
    # doc_embeddings shape: (N, D), query_vec shape: (D,)
    norm_docs = np.linalg.norm(doc_embeddings, axis=1, keepdims=True) + 1e-9
    norm_q = np.linalg.norm(query_vec) + 1e-9
    normalized_docs = doc_embeddings / norm_docs
    normalized_q = query_vec / norm_q

    similarities = np.dot(normalized_docs, normalized_q)  # BLAS/AVX2 底层加速
    top_indices = np.argpartition(similarities, -top_k)[-top_k:]
    sorted_top = top_indices[np.argsort(-similarities[top_indices])]
    return [(sorted_top[i], float(similarities[sorted_top[i]])) for i in range(len(sorted_top))]
```

### 2. 重写 `_DummySentenceTransformer` 降级行为
在 `src/rag/embeddings.py:46`，严禁使用 SHA-256 生成伪随机向量：
- 模型权重加载失败或处于离线沙箱时，系统显式降级：
  - 将状态标记为 `degrade_level = DEGRADED_SPARSE_ONLY`；
  - 自动 Bypass 稠密向量分支，降级为 BM25 单路召回并上报监控报警；
  - 保证工程监控能第一时间捕捉到模型失活（Model Drift/Dead），杜绝虚假随机召回。

---

## 四、 方案四：归一化相似度与“硬过滤 + 软重排”分离

### 1. 距离度量严格归一化
修正 `src/rag/retriever.py:302` 的计算逻辑：
- **ChromaDB 余弦距离** $d \in [0, 2]$：
  $$\text{Cosine Similarity} = 1.0 - \frac{d}{2.0} \in [0, 1]$$
- **欧氏距离（L2）**：
  $$\text{Similarity} = \frac{1.0}{1.0 + d} \in (0, 1]$$

### 2. “硬过滤（Hard Filtering）”与“软打分（Soft Scoring）”解耦
- **禁止乘法惩罚（如 `score *= 0.3`）**：
  - 预算上限、品牌偏好、动力形式属于确定性硬约束，必须在 Phase 1 通过 SQLite 参数化查询或 ChromaDB `$and` / `$in` 元数据过滤彻底排除；
  - 语义检索仅在合法的候选池内评估相似度；
- **废除自创魔法权重**：
  - 稠密向量与 BM25 的多路召回继续由 RRF（Reciprocal Rank Fusion）进行无量纲融合；
  - 召回 Top 50 候选后，交由成熟的 Cross-Encoder（如 `bge-reranker-large` / `bge-reranker-v2-m3`）进行端到端重排，让模型自主学习特征关联，彻底废弃 `semantic: 0.4, price: 0.2` 等人工调参逻辑。

---

## 五、 方案五：工程化意图解析，淘汰简陋正则

在 `src/rag/retriever.py:160` 的参数解析重构：
1. **中文数字标准化**：引入 `cn2an` 管道，将“三十来万”、“30w”、“三十五万左右”预先规范化为数值区间 `[280000, 350000]`；
2. **规则优先，小模型兜底**：
   - 规则层（基于 Trie 树扫描数据库注册车型和词库）解决 80% 明确的高频 Query；
   - 未命中或置信度偏低时，异步交由轻量 LLM（或小型 FastText / BERT 意图分类器）执行 Function Calling，输出强类型 Pydantic Schema。

---

## 六、 方案六：生产级上下文压缩（Context Pruning）

彻底废除 `src/rag/compression.py:75` 中暴力 `re.sub` 挖词撕裂语法的做法。

### 1. 句子与 AST 感知修剪（Sentence & AST-Aware Pruning）
- 严禁在句子内部截断关键词。使用分句器将文档拆解为语法完整的句子列表；
- 针对 Markdown / HTML 规格表，按行或按单元格进行 AST 语法解析，剔除纯宣传行，完整保留“属性-数值”行，确保 Markdown 渲染不崩塌。

### 2. 基于 Query 相关度的抽取式压缩（Extractive Compression）
```python
def compress_context(query: str, text: str, max_tokens: int = 512) -> str:
    # 1. 保持语法完整的句子切分
    sentences = split_into_sentences(text)

    # 2. 句子级与 Query 的匹配度打分 (BM25 或 Cross-Encoder)
    scored_sentences = [
        (sent, compute_relevance(query, sent))
        for sent in sentences
        if not is_pure_marketing_hype(sent)  # 整句属于纯营销口号时丢弃整句
    ]

    # 3. 按相关度降序排序，贪心填充 Token 预算
    scored_sentences.sort(key=lambda x: x[1], reverse=True)
    selected = []
    current_tokens = 0
    for sent, score in scored_sentences:
        sent_tokens = count_tokens(sent)
        if current_tokens + sent_tokens <= max_tokens:
            selected.append(sent)
            current_tokens += sent_tokens

    # 4. 恢复原始上下文先后顺序，保障下游 LLM 语义流畅
    return reconstruct_ordered_text(selected, original_text=text)
```

---

## 七、 方案七：并发基础设施与异步非阻塞改造

重构 `src/rag/hybrid_pipeline.py:289`，彻底消除动态创建与销毁线程池的开销：
1. 禁止在请求内部通过 `with ThreadPoolExecutor` 现场分配 OS 线程；
2. 在 FastAPI Lifespan 单例容器中初始化全局常驻的 `ThreadPoolExecutor`，结合 `asyncio` 进行非阻塞调度：

```python
# 基于 asyncio 与全局常驻线程池的非阻塞混合检索
import asyncio
import concurrent.futures
from typing import Optional

class HybridPipeline:
    def __init__(self, executor: Optional[concurrent.futures.ThreadPoolExecutor] = None):
        # 依赖注入常驻线程池，进程级单例
        self._executor = executor or get_global_executor()

    async def search_async(self, query_text: str, top_k: int = 10) -> HybridPipelineResult:
        loop = asyncio.get_running_loop()

        # 将阻塞的向量检索与 BM25 稀疏检索挂载到常驻线程池并发执行，零线程销毁开销
        dense_task = loop.run_in_executor(self._executor, self._dense_search, query_text, top_k)
        sparse_task = loop.run_in_executor(self._executor, self._sparse_search, query_text, top_k)

        dense_res, sparse_res = await asyncio.gather(dense_task, sparse_task)
        return self._fuse_results(dense_res, sparse_res, top_k)
```

---

## 八、 方案八：评测科学化：构建统计置信度与 CI 质量闸门

在 `src/rag/fusion.py` 的算法调优层面建立严谨的验证流程：
1. **扩充真实评测集**：将测试样本从 116 条扩充至 1000+ 条覆盖头部热点、腰部比价与长尾冷门配置的工业级测试集；
2. **引入统计假设检验**：在评估 RRF 权重优化或检索召回收益时，引入配对 t 检验（Paired t-test）或 Wilcoxon 符号秩检验，确保 $p < 0.05$ 且在交叉验证集中表现稳定，杜绝拟合统计噪声；
3. **CI 质量闸门（Eval Gate）**：
   - 将评测集成至 CI/CD 流水线，任何检索改动必须满足 $\text{NDCG@5} \ge 0.82$ 且 $\text{MRR} \ge 0.85$，阻断退化版本合入主干。

---

## 九、 总结：重构优先级路线图（Action Items）

| 优先级 | 任务模块 | 核心改动 | 预期收益 |
|---|---|---|---|
| **P0** | **架构收敛** | 废弃 `backend/app/rag/` 与 `src/rag/retriever.py`，入口全部归拢到 `RAGService` | 消除 3 套重复实现与数据不一致隐患 |
| **P0** | **算法与并发** | 废除 `SimpleVectorIndex` 循环点积，改用 HNSW / 矢量化；改用常驻全局线程池 | 检索吞吐提升 50 倍以上，消除高并发 CPU 尖刺 |
| **P1** | **Tier 0 治理** | 移除 `ENTERPRISE_FLAGSHIP_SPECS` 硬编码，改用 SQLite 动态预热 + Aho-Corasick 实体识别 | 杜绝发版改字典的伪架构，实现毫秒级快速匹配 |
| **P1** | **去噪与压缩** | 替换 `re.sub` 挖词，改用 AST/句子级信息密度抽取压缩 | 彻底消除因上下文破碎导致的模型幻觉 |
| **P2** | **评分与评测** | 规范化距离空间，接入 Cross-Encoder 重排；评测集扩充至千条并引入统计检验 | 检索准确率与可解释性显著提高，避免过拟合自嗨 |

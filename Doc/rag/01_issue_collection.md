# AutoVend RAG 核心架构缺陷与质疑合集 (Issue Collection 01)

> 整理说明：本文件记录针对 AutoVend 当前 RAG 检索模块的核心架构缺陷、硬编码作弊、算法与算力灾难、相似度换算错误、粗暴正则修剪与并发线程滥用等问题的集中质询与审查意见。

---

## 目录
1. [一、 架构精神分裂：一个项目写了 4 套检索，在玩俄罗斯套娃？](#一-架构精神分裂一个项目写了-4-套检索在玩俄罗斯套娃)
2. [二、 "Tier 0 极速检索"：把测谎仪逼疯的硬编码作弊](#二-tier-0-极速检索把测谎仪逼疯的硬编码作弊)
3. [三、 算法与算力灾难：2026 年了，还在用 Python for 循环算向量点积？](#三-算法与算力灾难2026-年了还在用-python-for-循环算向量点积)
4. [四、 离谱的相似度换算与拍脑袋的评分公式](#四-离谱的相似度换算与拍脑袋的评分公式)
5. [五、 “抗幻觉上下文修剪”：暴力正则的语义碎纸机](#五-抗幻觉上下文修剪暴力正则的语义碎纸机)
6. [六、 线程池滥用：每次检索现场建线程池](#六-线程池滥用每次检索现场建线程池)
7. [七、 评测注释里的“虚荣指标”与噪声自嗨](#七-评测注释里的虚荣指标与噪声自嗨)
8. [面试官的灵魂三问（架构重构现场挑战）](#面试官的灵魂三问架构重构现场挑战)

---

### 一、 架构精神分裂：一个项目写了 4 套检索，在玩俄罗斯套娃？

在架构 Review 时，核心考量是模块职责清晰与统一的生命周期管理。但审查当前代码库：

1. `src/rag/query_engine.py:35`：使用 LlamaIndex 的 `VectorStoreIndex` 搞了一套，通过 `MetadataFilters` 做检索；
2. `src/rag/retriever.py:33`：另起炉灶，手写了一个 `VehicleRetriever` 调度 `ChromaVectorStore`；
3. `src/rag/parent_child_retriever.py:126`：手写了一个内存版的 `SimpleVectorIndex`；
4. `src/rag/service.py:32`：最外层包装了一层 `RAGService`，把 `HybridPipeline`、`TieredRetrievalEngine`、`VehicleDB` 混杂在了一起。

**审查质询**：
- 到底是哪一套系统在真正在 Serving 线上流量？
- 当底层数据发生变更时，SQLite、ChromaDB、LlamaIndex 内存索引、SimpleVectorIndex 四份状态如何保证强一致性？如何防范脏读与幻读？

---

### 二、 "Tier 0 极速检索"：把测谎仪逼疯的硬编码作弊

在 `src/rag/tiered_engine.py:18` 注释宣称：
> *"Tier 0 / Fast-Path (< 1-2 ms): In-memory exact spec / tabular entity lookup and semantic cache... Returns grounded facts in < 1-2 ms"*

字面声称将延迟压到了 1~2 毫秒，然而查看 `src/rag/tiered_engine.py:103-145` 实现：
```python
ENTERPRISE_FLAGSHIP_SPECS: Dict[str, Dict[str, Any]] = {
    "小米-SU7 Max": { ... },
    "小米-SU7 Pro": { ... },
    "小米-SU7 标准版": { ... },
}
...
aliases = {
    "su7": "小米-SU7 标准版",
    "su7 max": "小米-SU7 Max",
}
```

**问题本质**：
- 在 Python 代码里写死一个名为 `ENTERPRISE_FLAGSHIP_SPECS` 的静态字典来冒充 RAG 检索，属于典型的硬编码作弊。
- 业务敏捷性归零：一旦市面车型降价或发布新款，必须修改源码并发布紧急 Release。
- 伪语义缓存：在 `src/rag/tiered_engine.py:61` 的所谓 `SemanticQueryCache`，其 Key 归一化逻辑居然是：
  ```python
  re.sub(r"[\s\?\!\,\.\;\:\'\"\(\)\-\_，。？！]+", "", q)
  ```
  本质上只是过滤标点空格后的纯字符精确匹配，挂羊头卖狗肉。

---

### 三、 算法与算力灾难：2026 年了，还在用 Python for 循环算向量点积？

查看 `src/rag/parent_child_retriever.py:195-207`：
```python
scores: List[Tuple[Chunk, float]] = []
for chunk, vec in zip(self.chunks, self.embeddings):
    dot = sum(a * b for a, b in zip(query_vec, vec))
    norm_a = math.sqrt(sum(a * a for a in query_vec)) or 1e-9
    norm_b = math.sqrt(sum(b * b for b in vec)) or 1e-9
    sim = dot / (norm_a * norm_b)
    scores.append((chunk, float(sim)))
scores.sort(key=lambda x: x[1], reverse=True)
```

**问题分析**：
- 未使用矩阵乘法（`query_vec @ embeddings.T`），更无 FAISS、HNSW 或 Annoy 等成熟 ANN 索引，而是直接用 Python 原生 `for` 循环和 `zip` 对 1024 维 float 列表做点积和模长计算。
- 若切出 2 万个 Child Chunk，单次检索需在解释器内执行 20,000 × 1024 次浮点乘加运算，GIL 锁瞬间拉满，吃满单核 CPU 数秒，完全无法应对高并发。
- **伪随机降级灾难**：在 `src/rag/embeddings.py:46-59` 的 `_DummySentenceTransformer` 中：
  - 使用 `hashlib.sha256(text)` 截取前 4 字节充当伪随机数种子来生成“降级向量”。
  - “性价比高的代步小车” 与 “价格亲民的家用小汽车” 语义极度接近，但 SHA-256 结果完全正交，余弦相似度期望为 0。线上发生降级时召回彻底沦为随机掷骰子。

---

### 四、 离谱的相似度换算与拍脑袋的评分公式

#### 1. 错误的相似度转换公式
在 `src/rag/retriever.py:302`：
```python
# 计算语义相似度
semantic_score = 1.0 - distance  # ChromaDB返回的是距离
```
- 底层若返回默认的余弦距离（Cosine Distance），取值范围为 `[0, 2]`。当两向量语义无关时（距离 1.5），`semantic_score` 变为负数 `-0.5`。
- 若为欧氏距离（L2），距离动辄数十，相似度直接沦为大幅负值，破坏后续融合计算。

#### 2. 拍脑袋的无依据权重
在 `src/rag/retriever.py:431-440`：
```python
weights = {
    "semantic": 0.4,
    "price": 0.2,
    "category": 0.2,
    "feature": 0.2,
}
```
- 权重缺乏权威评测或基准依据，纯属主观臆断。

#### 3. 粗暴降权导致推荐变形
在 `src/rag/retriever.py:382`：
- 品牌匹配不上时直接执行 `score *= 0.3`。
- 用户明确要求“奔驰”，无法匹配时打三折强推“大众”，严重偏离精准推荐意图。

---

### 五、 “抗幻觉上下文修剪”：暴力正则的语义碎纸机

在 `src/rag/compression.py:20-40` 与 `src/rag/compression.py:75`：
```python
MARKETING_FLUFF_PATTERNS = [
    r"遥遥领先", r"地表最强", r"降维打击", r"天花板", ...
]

for pattern in MARKETING_FLUFF_PATTERNS:
    cleaned = re.sub(pattern, "", cleaned)
cleaned = re.sub(r"[,，、\s]{2,}", "，", cleaned).strip(...)
```

**破坏性后果**：
- 语法撕裂：若原文为“*该车型不宣传‘遥遥领先’等浮夸口号，注重真实冬测*”，经粗暴清洗后变为“*该车型不宣传等浮夸口号，注重真实冬测*”，主谓宾结构被破坏。
- 格式崩溃：若上下文包含 JSON 或 Markdown 表格，正则直接强抠匹配词，导致表格对齐与数据语义边界崩溃，严重加剧下游 LLM 幻觉。

---

### 六、 线程池滥用：每次检索现场建线程池

在 `src/rag/hybrid_pipeline.py:289-300`：
```python
with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
    future_dense = executor.submit(_do_dense)
    future_sparse = executor.submit(_do_sparse)
    dense_response = future_dense.result()
    sparse_hits = future_sparse.result()
```

**高并发瓶颈**：
- 每个 Query 触发时在函数体内现场通过 `with ThreadPoolExecutor(max_workers=2)` 创建并销毁 OS 线程池。
- 在 200 并发场景下瞬时分配与销毁 400 个操作系统线程，引发剧烈的线程栈内存开销与内核上下文切换抖动。
- FastAPI 事件循环未被有效利用，未采用常驻 Worker 线程池或 `asyncio.gather` 异步调度。

---

### 七、 评测注释里的“虚荣指标”与噪声自嗨

在 `src/rag/fusion.py:35-50` 的注释中：
> *"weight_search sweeps the split from 0.0 to 1.0 over the 116-query golden set: dense 0.00 → 0.7069, dense 0.40 → 0.7557... The plateaus overlap on [0.20, 0.70]... Shipping it on would have been fitting noise."*

**统计学失真**：
- 整个黄金测试集仅有 116 条 Query，单条样本扰动即占 `1 / 116 ≈ 0.86%`。
- 在样本量极小的玩具集上做网格搜索，得出的千分位差异属于完全无法通过卡方检验或 Student's t-test 显著性检验的统计噪声，属于过拟合自嗨。

---

### 面试官的灵魂三问（架构重构现场挑战）

1. **向量检索与并发调度**：面对 50 万量级汽车手册分块和 500 QPS 的并发压力，如何彻底废弃现有的 `SimpleVectorIndex`，把混合检索（BM25 + 向量检索）重构为零线程创建开销、真正带 ANN 索引（如 HNSW / FAISS）的生产级架构？
2. **结构化与非结构化的分工边界**：为什么 RAG 检索器还在试图用正则表达式去抓取价格、品牌和车型？为什么不把明确的参数过滤交给底层的 SQLite / 向量数据库 Metadata Filter，而是把脏活累活全堆在 Python 层的粗暴正则与魔法权重上？
3. **真实防御幻觉的 Context Pruning**：如果要真正做上下文去噪和规格对齐，除了破坏语法的 `re.sub` 字符串黑名单，业内成熟的基于 Token 级别互信息（Per-token Mutual Information）或 Cross-Encoder 句子级重排（Sentence Reranking）应该如何设计？

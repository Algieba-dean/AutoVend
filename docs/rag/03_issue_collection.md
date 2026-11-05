# AutoVend RAG 检索链路严重缺陷、算法灾难与架构欺诈合集 (Issue Collection 02)

> 整理说明：本文件系统性梳理并记录针对 AutoVend 当前 RAG 检索管线、分层路由（Tiered Engine）、重排机制（Reranker）、嵌入降级方案、向量索引底层实现、查询重写（HyDE）及工程安全缺陷的集中技术审查与面试官深度质询意见。

---

## 目录
1. [一、 架构欺诈级设计：所谓“Tier 0 Fast-Path (< 1-2ms)”的皇帝新衣](#一-架构欺诈级设计所谓tier-0-fast-path--1-2ms的皇帝新衣)
   - 1.1 [`ENTERPRISE_FLAGSHIP_SPECS`：静态内存字典冒充高性能 RAG](#1-enterprise_flagship_specs静态内存字典冒充高性能-rag)
   - 1.2 [单元测试套号作弊与虚假低延迟宣称](#2-单元测试套号作弊与虚假低延迟宣称)
   - 1.3 [`SemanticQueryCache` 伪语义缓存：去标点空格哈希欺诈](#3-semanticquerycache-伪语义缓存去标点空格哈希欺诈)
2. [二、 灾难级逻辑漏洞：Tier 2 深度检索的“张冠李戴”式下毒](#二-灾难级逻辑漏洞tier-2-深度检索的张冠李戴式下毒)
   - 2.1 [全局上下文无差别广播投毒](#1-全局上下文无差别广播投毒)
   - 2.2 [下游 LLM 认知错乱与企业法律合规风险](#2-下游-llm-认知错乱与企业法律合规风险)
3. [三、 名不副实的重排：手写加减法配上魔法数字 * 6.0](#三-名不副实的重排手写加减法配上魔法数字--60)
   - 3.1 [`RankRefiner`：退化为 90 年代专家规则引擎的伪重排器](#1-rankrefiner退化为-90-年代专家规则引擎的伪重排器)
   - 3.2 [荒谬的 RRF 凑数因子 `base_score * 6.0`](#2-荒谬的-rrf-凑数因子-base_score--60)
4. [四、 离谱的降级设计：伪随机向量与全零向量下毒](#四-离谱的降级设计伪随机向量与全零向量下毒)
   - 4.1 [“语义大乐透”：SHA-256 伪随机高维向量降级](#1-语义大乐透sha-256-伪随机高维向量降级)
   - 4.2 [全零向量注入 ChromaDB：分母为零引发 NaN 瘫痪](#2-全零向量注入-chromadb分母为零引发-nan-瘫痪)
5. [五、 玩具级自研索引：在 Python 数组里搞 O(N) 暴力扫描](#五-玩具级自研索引在-python-数组里搞-on-暴力扫描)
   - 5.1 [`SimpleVectorIndex` 的原生 Python 双重循环](#1-simplevectorindex-的原生-python-双重循环)
   - 5.2 [缺乏 ANN 索引与无 SIMD 矩阵加速的算力灾难](#2-缺乏-ann-索引与无-simd-矩阵加速的算力灾难)
6. [六、 伪 HyDE 与查询展开：主动向语义空间投毒](#六-伪-hyde-与查询展开主动向语义空间投毒)
   - 6.1 [硬编码中大型豪华 SUV 模板反向污染长尾微型车](#1-硬编码中大型豪华-suv-模板反向污染长尾微型车)
   - 6.2 [默认脱机参数导致查询向量偏离真实意图](#2-默认脱机参数导致查询向量偏离真实意图)
7. [七、 基础工程素养与数据模型缺陷](#七-基础工程素养与数据模型缺陷)
   - 7.1 [Pickle 反序列化安全炸弹 (CWE-502)](#1-pickle-反序列化安全炸弹-cwe-502)
   - 7.2 [土法 TF 刷权重：“车型名复读机”](#2-土法-tf-刷权重车型名复读机)
   - 7.3 [数据模型拼写坍塌与 Stringly-Typed 泛滥](#3-数据模型拼写坍塌与-stringly-typed-泛滥)
   - 7.4 [ChromaDB 写入无幂等性导致重复脏数据堆积](#4-chromadb-写入无幂等性导致重复脏数据堆积)
8. [八、 所谓的性能评测与“23倍提升”神话](#八-所谓的性能评测与23倍提升神话)
   - 8.1 [预热对比冷启动的学术丑闻](#1-预热对比冷启动的学术丑闻)
   - 8.2 [13 条手挑样本的主观假通过率 vs 116 条金标集的真实低迷召回](#2-13-条手挑样本的主观假通过率-vs-116-条金标集的真实低迷召回)
9. [面试官总结与现场考察问题 (Interview Feedback)](#面试官总结与现场考察问题-interview-feedback)
   - 9.1 [架构评审综合裁决评语](#1-架构评审综合裁决评语)
   - 9.2 [现场技术考察三大灵魂拷问](#2-现场技术考察三大灵魂拷问)

---

### 一、 架构欺诈级设计：所谓“Tier 0 Fast-Path (< 1-2ms)”的皇帝新衣

#### 1. `ENTERPRISE_FLAGSHIP_SPECS`：静态内存字典冒充高性能 RAG

代码定位：`src/retrieval/tiered_engine.py:103-215`

系统在架构文档与简历中大肆宣传其“3-Tier 动态分层检索路由架构”，号称 **Tier 0 极速通道能在 < 1~2 ms 完成精准事实与规格参数直查**。然而审查其核心源码：

```python
ENTERPRISE_FLAGSHIP_SPECS: Dict[str, Dict[str, Any]] = {
    "小米-SU7 Max": {
        "car_model": "小米-SU7 Max",
        "brand": "小米",
        "price": "29.99万元",
        "vehicle_category_bottom": "中大型纯电轿跑",
        "powertrain_type": "纯电动",
        "drive_type": "双电机全轮驱动 (AWD)",
        "seat_layout": "5座",
        "acceleration_0_100": "2.78秒",
        "max_speed": "265km/h",
        "electric_range": "800km (CLTC)",
        "battery_capacity": "101kWh三元锂麒麟电池",
        "horsepower": "673马力 (495kW)",
        "torque": "838N·m",
        "wheelbase": "3000mm",
    },
    "特斯拉-Model 3": { ... },
    "蔚来-ES6": { ... },
    # 静态硬编码比亚迪、理想、问界等共 11 款主流热门车型
}
```

**作弊本质剖析**：
1. **纯静态硬编码字典冒充 RAG**：所谓的自研 Tier 0 极速检索，就是在 Python 源码里手动写死了一个包含十来款车型的静态字典；
2. **简陋正则提取**：在字典之上挂载了几十行 `SPEC_ATTRIBUTE_PATTERNS` 正则表达式。一旦识别到 query 中含有“零百”或“加速”，就直接从内存 Python dict 中执行 `get()` 读取；
3. **业务可维护性归零**：一旦市面车型指导价微调、发布新配色或推行限时权益，无法通过更新向量库或知识库生效，必须直接侵入式修改 Python 源码并重新打包发版。

---

#### 2. 单元测试套号作弊与虚假低延迟宣称

代码定位：`tests/test_flexible_agent_and_fast_rag.py:42-55`

```python
def test_su7_max_acceleration_exact_spec(self):
    query = "SU7 Max 零百加速是多少"
    res = self.engine.search_tier0(query)
    assert res.latency_ms < 10.0  # sub-10ms even on cold run
    assert "小米-SU7 Max" in res.results[0].car_model
```

**问题分析**：
- 查询自己 hardcode 在内存变量里的 11 条静态数据，由于没有网络 I/O、无磁盘寻道、无向量相似度计算，耗时当然 `< 10ms`；
- 把查内存字典的耗时当作“RAG 检索性能突破”写入测试报告和架构演进总结中，属于典型的工程作弊与自欺欺人。

---

#### 3. `SemanticQueryCache` 伪语义缓存：去标点空格哈希欺诈

代码定位：`src/retrieval/tiered_engine.py:40-75`

在所谓的“语义查询缓存（Semantic Query Cache）”中：
```python
class SemanticQueryCache:
    def _normalize_key(self, query: str) -> str:
        # 去掉标点符号与空格
        return re.sub(r"[\s\?\!\,\.\;\:\'\"\(\)\-\_，。？！]+", "", query).lower()
```

**审查分析**：
- 类名冠以高大上的“Semantic（语义）”，底层逻辑仅仅是 `re.sub` 剔除标点符号与空白字符后，塞进 Python 标准库的 `OrderedDict`；
- 这里根本没有任何向量嵌入（Embedding）、无余弦相似度匹配（Cosine Thresholding）、无语义聚类泛化能力；
- 用户的 `"想买一台20万左右的省油SUV"` 与 `"求推荐20万左右低油耗的SUV"` 语义完全相同，但由于字符不同，该缓存命中率为 0%。这是典型的挂羊头卖狗肉。

---

### 二、 灾难级逻辑漏洞：Tier 2 深度检索的“张冠李戴”式下毒

#### 1. 全局上下文无差别广播投毒

代码定位：`src/retrieval/tiered_engine.py:855-879`

查看号称用于处理“多车对比、复杂专业技术文档推理”的 Tier 2 深度检索逻辑：

```python
# First obtain vehicle candidates
tier1_res = self.search_tier1(request, top_k=top_k)
results = tier1_res.results

# If parent-child retriever is available, enrich candidates with parent document context
doc_evidence = []
if self.parent_child_retriever is not None and query_text:
    doc_res = self.parent_child_retriever.search(query=query_text, top_k_children=6, top_k_parents=3)
    for p in doc_res.results:
        doc_evidence.append(p.content[:300])

# Enrich vehicle snippets with deep document evidence
if doc_evidence and results:
    evidence_str = "\n".join(doc_evidence[:2])
    for r in results:
        r.text_snippet = (
            f"{r.text_snippet}\n【深度文档与横评参考】: {evidence_str[:250]}"
        )
```

**灾难级执行路径复盘**：
1. **多实体场景崩溃**：假设用户提问：“*对比一下特斯拉 Model 3 和 小米 SU7*”；
2. **无差别广播**：`tier1_res` 返回两个候选车对象：`[Tesla Model 3, 小米 SU7]`；
3. `parent_child_retriever` 针对全文检索召回了得分最高的文档片段（例如一段关于“*小米 SU7 赛道版双电机高温散热降频与车漆工艺瑕疵*”的测评长文）；
4. 在 `for r in results:` 循环中，**这段专门针对于小米 SU7 的负面测评文本，被不加任何实体过滤（Entity Scoping）地、一字不差地拼接入了特斯拉 Model 3 的 `text_snippet`**！

---

#### 2. 下游 LLM 认知错乱与企业法律合规风险

- **下游大模型被直接投毒**：LLM 在读取组装后的 Prompt 上下文时，会误以为“特斯拉 Model 3 也存在双电机高温降频与小米车漆缺陷”；
- **商用法律灾难**：在汽车导购垂类场景下，这种由于架构粗糙导致的“张冠李戴”，会使 AI 销售助手对竞品车辆信口雌黄，直接触发不正当竞争、虚假陈述与品牌侵权风险，次日即可招致法务诉讼与监管巨额罚单。

---

### 三、 名不副实的重排：手写加减法配上魔法数字 * 6.0

#### 1. `RankRefiner`：退化为 90 年代专家规则引擎的伪重排器

代码定位：`src/rag_service/reranker.py:50-180`

模块命名为 `reranker.py`，类名定义为高大上的 `RankRefiner`。在现代 RAG 架构中，重排层（Reranker）标准实践是引入 Cross-Encoder 模型（如 `bge-reranker-large`、Cohere Rerank）对 Query-Document 进行深度交叉注意力交叉计算。

然而点开其源码：
```python
score = 0.50  # Neutral starting baseline

# 1. 品牌匹配 (+0.20)
if brand and (brand in query_lower):
    score += 0.20

# 2. 车型分类匹配 (+0.15)
if cat and (cat in query_lower):
    score += 0.15

# 3. 动力类型不匹配 (-0.20)
if is_query_bev and "燃油" in p_type:
    score -= 0.20

# 4. 预算略超 (-0.05)
if budget_max and price > budget_max * 1.10:
    score -= 0.05
```
- 这根本不是神经重排器，而是一个充满主观臆断、充斥着手工加减分的 90 年代土法则规则引擎（Heuristic Rule Engine）。

---

#### 2. 荒谬的 RRF 凑数因子 `base_score * 6.0`

代码定位：`src/rag_service/reranker.py:194-204`

在将 RRF（倒数排名融合）得分与所谓规则分进行混合时：
```python
# Normalize original RRF score (typical range 0.01 - 0.15 or 0.0 - 1.0)
base_score = min(1.0, max(0.0, item.score))
if base_score > 0 and base_score < 0.15:
    # Scale up RRF rank reciprocal to 0.0-1.0 range
    base_score = min(1.0, base_score * 6.0)

# Combined score
final_score = base_score * (1.0 - spec_weight) + spec_score * spec_weight
```

**问题分析**：
- RRF 公式原始定义为 $RRF(d) = \sum_{m} \frac{1}{k + r_m(d)}$。当阻尼常数 $k=60$ 时，得分自然分布在 $0.01 \sim 0.033$ 附近。
- 研发人员嫌分数太小，既没有做标准的 Min-Max 归一化，也没有采用 Softmax，而是拍脑袋写下了 `base_score * 6.0`！
- 这种典型的**凑数因子（Fudge Factor）**极其脆弱：一旦召回深度从 Top-10 变成 Top-50，或者融合通道数发生改变，这个乘以 6.0 的魔法数字将导致全量候选打分严重失真、排序逻辑彻底报废。

---

### 四、 离谱的降级设计：伪随机向量与全零向量下毒

#### 1. “语义大乐透”：SHA-256 伪随机高维向量降级

代码定位：`src/rag/embeddings.py:22-48`

审查模型加载失败时的静默降级实现：
```python
class _DummySentenceTransformer:
    """离线沙箱或无网络环境下的轻量级降级嵌入模型。"""

    def _generate_vector(self, text: str, normalize: bool = True) -> np.ndarray:
        # 针对输入文本哈希生成确定性的伪随机高维单位向量，保持几何分布与正交性
        h = hashlib.sha256(str(text).encode("utf-8", errors="ignore")).digest()
        seed = int.from_bytes(h[:4], "big")
        rng = np.random.RandomState(seed)
        vec = rng.standard_normal(self.dimension).astype(np.float32)
        if normalize:
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec = vec / norm
        return vec
```

**严重后果**：
- 在 BGE-M3 权重缺失或环境断网时，系统静默降级至该生成器。
- 代码居然使用 `hashlib.sha256(text)` 提取前 4 字节充当伪随机数生成器的 Seed！
- **语义几何彻底崩塌**：“*宝马新能源轿车*” 与 “*BMW 纯电轿跑*” 语义高度一致，但因 SHA-256 哈希雪崩效应，二者随机种子天差地别，生成的 1024 维高斯随机向量在空间中几乎严格正交，余弦相似度收敛于 0。
- 降级本应优雅保底（如退化为 BM25 纯字面匹配），而该实现却将语义搜索变成了**高维随机摇号（语义大乐透）**，且调用方完全被蒙在鼓里。

---

#### 2. 全零向量注入 ChromaDB：分母为零引发 NaN 瘫痪

代码定位：`src/rag/index_builder.py:210-215`

```python
except Exception as e:
    self.logger.error(f"批次 {i // self.batch_size} 嵌入生成失败: {e}")
    self.build_stats["failed_vehicles"] += len(batch_vehicles)
    # 添加空嵌入以保持索引对齐
    embeddings.extend([[0.0] * self.embedding_model.embed_dimension] * len(batch_texts))
```

**问题剖析**：
- 当某一批车型生成向量抛出异常时，为了维持所谓数组长度对齐，直接填充了全零向量 `[0.0] * 1024`，并堂而皇之地持久化存入了向量库 ChromaDB！
- 全零向量的模长为 0（$\|v\| = 0$）。在执行余弦相似度计算 $\frac{u \cdot v}{\|u\| \|v\|}$ 时，**分母直接为零触发除零异常或产生浮点 `NaN`（Not a Number）**。
- `NaN` 混入浮点数组后，会导致 Python 排序算法（Timsort）失效、向量距离比较产生未定义行为，进而引发整批检索请求静默瘫痪。

---

### 五、 玩具级自研索引：在 Python 数组里搞 O(N) 暴力扫描

#### 1. `SimpleVectorIndex` 的原生 Python 双重循环

代码定位：`src/retrieval/parent_child_retriever.py:128-215`

查看所谓自研的内存父子分块检索索引 `SimpleVectorIndex`：

```python
class SimpleVectorIndex:
    def __init__(self, embedding_model=None):
        self.embeddings: List[List[float]] = []
        self.chunks: List[Chunk] = []

    def search(self, query: str, top_k: int = 5):
        ...
        scores: List[Tuple[Chunk, float]] = []
        for chunk, vec in zip(self.chunks, self.embeddings):
            dot = sum(a * b for a, b in zip(query_vec, vec))
            norm_a = math.sqrt(sum(a * a for a in query_vec)) or 1e-9
            norm_b = math.sqrt(sum(b * b for b in vec)) or 1e-9
            sim = dot / (norm_a * norm_b)
            scores.append((chunk, float(sim)))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]
```

---

#### 2. 缺乏 ANN 索引与无 SIMD 矩阵加速的算力灾难

- **无 ANN 索引**：不用 FAISS，不用 HNSWLib，不用 Annoy；
- **连 NumPy 矢量化都放弃**：直接使用原生 Python `for chunk, vec in zip` 搭配 `sum(a * b for a, b in zip)` 标量循环，一个个去算 1024 维的浮点乘加！
- **性能灾难估算**：
  - 解释型语言在动态类型解包和循环中开销巨大。若知识库切出 30,000 个文档分块，单次检索需在 Python 解释器内执行：
    $$30000 \times 1024 \approx 30,720,000 \text{ 次标量浮点乘加}$$
  - 单次简单检索耗时直接攀升至数秒，GIL 锁锁死单个 CPU 核心。只要并发量达到 10 QPS，整个 API 进程立即原地挂死。

---

### 六、 伪 HyDE 与查询展开：主动向语义空间投毒

#### 1. 硬编码中大型豪华 SUV 模板反向污染长尾微型车

代码定位：`src/retrieval/query_transform.py:149-155`

查看假设性文档嵌入（HyDE）的生成逻辑 `generate_hyde_doc`：

```python
hyde_doc = (
    f"【目标车型规格文档】 车型需求: {query_text}。{tech_note}"
    f"车辆类型包含中大型SUV/纯电轿跑，配置包含大空间二排、高阶智驾系统、800V高压快充及气囊安全防护。"
    f"官方指导价格区间与参数指标精准匹配该需求。"
)

if self.llm is not None:
    # 动态通过大模型改写...
```

---

#### 2. 默认脱机参数导致查询向量偏离真实意图

- 在系统默认的检索管线装配中（`src/rag/hybrid_pipeline.py:255`）：
  ```python
  transformer = QueryTransformationEngine()  # 默认传参即 llm=None
  ```
- **真实场景投毒复盘**：
  - 用户输入：“*5万元以内的五菱宏光微型代步买菜车*”；
  - 由于未挂载 LLM，系统拿去计算嵌入向量的所谓“假设文档”，赫然写着：“*车辆类型包含中大型SUV/纯电轿跑，配置包含大空间二排、高阶智驾系统、800V高压快充...*”；
  - 系统拿着一个充满“大空间、800V、纯电轿跑、高阶智驾”语义的高维向量，去召回“5万以内的微型买菜车”；
- 这根本不是 HyDE，这是在用僵硬的硬编码模板把用户的真实查询意图主动进行语义空间污染！

---

### 七、 基础工程素养与数据模型缺陷

#### 1. Pickle 反序列化安全炸弹 (CWE-502)

代码定位：`src/retrieval/bm25_index.py:86-96`

```python
with target.open("wb") as fh:
    pickle.dump({"car_models": self.car_models, "bm25": self._bm25}, fh)

@classmethod
def load(cls, path: Optional[str] = None) -> "BM25Index":
    target = Path(path or config.bm25_index_path)
    with target.open("rb") as fh:
        payload = pickle.load(fh)
```
- 在工业级生产和 CI 环境中，直接使用标准库 `pickle.load` 加载未经加密和数字签名的二进制文件；
- 攻击者一旦通过数据同步通道篡改 `bm25.pkl`，即可在服务端反序列化时执行任意 Python 字节码，造成远程代码执行（RCE），属于 OWASP / CWE-502 明确警告的高危安全漏洞。

---

#### 2. 土法 TF 刷权重：“车型名复读机”

代码定位：`src/retrieval/bm25_index.py:150`

```python
car_model = record.get("car_model") or ""
parts = [car_model, car_model]  # 👈 车型名复读两遍
for column, value in record.items():
    ...
```
- 为了在 BM25 词频统计中提升车型名称的命中权重，开发人员简单粗暴地将 `car_model` 字符串原地复制了两遍拼在最前列；
- Elasticsearch 与 Lucene 中成熟的 Field Boosting（字段权重增强）概念，在本项目中退化为了“字符串复读机”。

---

#### 3. 数据模型拼写坍塌与 Stringly-Typed 泛滥

代码定位：`src/models/vehicle.py:27, 71, 209`

```python
# 低级拼写事故
passenger_sapce_volume: Optional[str] = None   # sapce 空间拼写错误
voice_interfaction: Optional[str] = None       # interfaction 交互拼写错误
precise_labels: PreciseLabels = Field(alias="PriciseLabels")  # TOML 拼错只能加 alias
```
- 全量数值字段（`price`, `horsepower`, `wheelbase`, `electric_range`）通通使用 `Optional[str]` 裸奔；
- 缺少强类型定义导致系统全链路（Retriever、Filter、Reranker）各处充斥着重复的正则表达式 `re.findall(r"(\d+)")`，随处在造解析轮子。

---

#### 4. ChromaDB 写入无幂等性导致重复脏数据堆积

代码定位：`src/rag/vector_store.py:176`

```python
for vehicle in vehicles:
    doc_id = str(uuid.uuid4())  # 每次写入随机生成 UUID
    ids.append(doc_id)
```
- 每次索引增量更新或重新执行导入脚本时，向量主键全部使用随机 `uuid.uuid4()`；
- 没有任何基于 `car_model` 或配置指纹的去重与幂等保证，导致向量数据库中疯狂堆积同款车型的重复脏数据。

---

### 八、 所谓的性能评测与“23倍提升”神话

代码定位：`pure_rag_comparison_report.md:1-25` 与 `evaluation/comparison.md`

在根目录下遗留的历史报告 `pure_rag_comparison_report.md` 中宣称：
> *"Hybrid is 23x faster than pure RAG (0.053s vs 1.202s), accuracy 92.3% vs 84.6%"*

**学术虚假与真实数据对质**：
1. **冷启动与热缓存混淆**：所谓的“快 23 倍”，是将没有预热模型权重的首轮冷启动延迟（1.202 秒）与内存中跑了 13 个样本的已预热耗时进行不公正对比；
2. **玩具集主观打分**：92.3% 的准确率，评测集总共只有 **13 条作者精心挑选的简单用例**，评判标准还是“作者主观觉得对不对”；
3. **真实生产金标测试惨遭打脸**（查看 `evaluation/comparison.md`）：
   - `natural`（真实口语自然语言意图），召回率仅为 **0.533 (53.3%)**；
   - `range`（纯电续航诉求），召回率仅有 **0.333 (33.3%)**；
   - 所谓的 CI 门禁只是在特定 116 条单测查询上放宽 `TOLERANCE = 0.02` 勉强保绿。

---

### 面试官总结与现场考察问题 (Interview Feedback)

#### 1. 架构评审综合裁决评语

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│  Interview Verdict: STRONG NO HIRE (架构欺诈、逻辑投毒与极端工程不成熟) │
│                                                                        │
│  评语：                                                                │
│  候选人擅长堆砌技术名词（HyDE、RRF、Parent-Child Retrieval、Tier 0   │
│  Fast-Path、RAGAS），甚至架构图与报告排版极具“大厂风格”。              │
│                                                                        │
│  但代码底层暴露出极其严重的架构欺诈与逻辑漏洞：用硬编码静态字典充当    │
│  Tier 0 并跑出虚假低延迟；Tier 2 跨文档检索无差别拼接向下游 LLM 投毒；  │
│  重排器使用手工加减分配上 * 6.0 的凑数因子；降级方案竟使用 SHA-256     │
│  生成伪随机高维向量与全零向量；甚至在内存中用 Python 原生循环做 O(N)   │
│  标量点积。                                                            │
│                                                                        │
│  项目展现出的是对高并发、可靠性与向量几何底色的极度漠视。              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

#### 2. 现场技术考察三大灵魂拷问

1. **并发与海量扩展性（Scalability & Sharding）**：
   若严禁在代码中硬编码十台车的 `ENTERPRISE_FLAGSHIP_SPECS`，且数据规模从当前的 1200 台车膨胀至 **500 万台全网动态二手车及新车源**，现有的 `SimpleVectorIndex`、内存 BM25 及 Python 循环点积该如何彻底推倒重构？如何设计分布式分片（Sharding）、HNSW 索引持久化与一致性哈希路由？
2. **多实体上下文严格隔离（Entity Scoping & Disambiguation）**：
   当用户输入复合比对查询（如“*对比特斯拉 Model 3 和 小米 SU7 的底盘用料与真实能耗*”）时，如何从架构层面设计**实体作用域隔离机制（Entity-Scoped Context Retrieval）**，彻底杜绝在 Tier 2 中无差别拼接上下文导致的“张冠李戴”式投毒？
3. **工业级重排流水线设计（Cross-Encoder & Latency Budgeting）**：
   如何把充满魔法数字 `* 6.0` 和硬编码规则加减分的 `RankRefiner`，替换为一个标准、可量化评估、支持**延迟预算（Latency Budgeting）**与动态截断的轻量化 Cross-Encoder / BGE-Reranker 重排流水线？

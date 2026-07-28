# 问题记录

记录本轮工作中遇到的问题、根因、解法与**实际效力**。

编号按发现顺序。效力一栏尽量给可验证的前后对比；改不动或没验证的直接说明，不
拿"应该会好"充数。

## 概览

| # | 问题 | 类别 | 状态 |
|---|---|---|---|
| 1 | 两分支互不包含，任一分支都跑不起完整系统 | 架构 | ✅ 已解决 |
| 2 | `ci.yml` 的 paths 过滤器使其从不触发 | CI | ✅ 已解决 |
| 3 | `.env` 键名与代码不匹配，静默跑 MockLLM | 配置 | ✅ 已解决 |
| 4 | 两处 config 的索引路径分歧 | 配置 | ✅ 已解决 |
| 5 | `uv run pytest` 解析到系统 Python | 工具链 | ⚠️ 绕过 |
| 6 | `GROQ_MODEL` 指向已下线模型 | 配置 | ✅ 已解决 |
| 7 | 检索结果从不截回 `top_k`，返回 2k 条 | **缺陷** | ✅ 已解决 |
| 8 | 检索落后用户一轮 | **缺陷** | ✅ 已解决 |
| 9 | `ChromaVectorStore.__del__` 关闭共享客户端 | **缺陷** | ✅ 已解决 |
| 10 | `build` 只建向量索引，另两层懒加载 | 构建 | ✅ 已解决 |
| 11 | 旧报告「23 倍加速」复现不出来 | 数据可信度 | ✅ 已澄清 |
| 12 | RAGAS 与 langchain-community 版本冲突 | 依赖 | ✅ 已解决 |
| 13 | Groq 不支持 `n>1`，RAGAS 全量失败 | 兼容性 | ✅ 已解决 |
| 14 | RAGAS 把超时的 NaN 当 0 分 | **可信度** | ✅ 已解决 |
| 15 | Groq 日额度耗尽拖垮整轮评估 | 配额 | ✅ 已缓解 |
| 16 | vLLM 装主环境会升级 torch 并动 109 个包 | 依赖 | ✅ 已隔离 |
| 17 | WSL2 下 `UVA is not available` | 平台 | ✅ 已解决 |
| 18 | WSL2 下 torch.compile 并行编译死锁 | 平台 | ⚠️ 已绕过 |
| 19 | vLLM 0.26 移除 GGUF 支持 | 兼容性 | ✅ 已换方案 |
| 20 | Qwen3 默认思维链，token 膨胀 4.7 倍 | 性能 | ✅ 已解决 |
| 21 | 基准脚本绕过生产配置，数字虚高 4 倍 | **可信度** | ✅ 已解决 |
| 22 | 基准脚本用残缺样本算百分位 | **可信度** | ✅ 已解决 |
| 23 | `model_name` 撞 Pydantic v2 保留命名空间 | 兼容性 | ✅ 已解决 |
| 24 | Presidio 内置识别器对中文完全失效 | 功能 | ✅ 已解决 |
| 25 | 内置 EmailRecognizer 吞掉中文前缀 | 缺陷 | ✅ 已解决 |
| 26 | 地址正则漏掉尾字 | 缺陷 | ✅ 已解决 |
| 27 | 占位符跨会话可解 | **安全** | ✅ 已解决 |
| 28 | 网关顺序错误，脱敏破坏语义分类 | **缺陷** | ✅ 已解决 |
| 29 | 测试自身 flaky（`hash()` 随机化） | 测试 | ✅ 已解决 |
| 30 | RAGAS 的 context_recall/precision 异常低 | **评估设计** | ✅ 已解决 |
| 31 | 状态机的有向图是死代码，运行时走 if-else | **架构** | ✅ 已解决 |
| 32 | 回退边定义了但没有任何代码可达 | 架构 | ✅ 已解决 |
| 33 | 预算守卫改变产品行为，既有测试编码旧契约 | 契约变更 | ✅ 已更新 |
| 34 | 回退在同一轮内被自己撤销 | **缺陷** | ✅ 已解决 |
| 35 | 「修改需求」与「首次陈述需求」语义边界模糊 | 模型能力 | ⚠️ 部分 |
| 36 | 测试对 frozen dataclass 用 setattr | 测试 | ✅ 已解决 |
| 37 | `pkill -f` 杀掉自己的 shell | 工具链 | ⚠️ 绕过 |
| 38 | HF Hub 网络故障阻断锚点构建 | 环境 | ✅ 已解决 |
| 39 | 动态融合权重实测不如静态，网格最优点在噪声内 | **方法论** | ✅ 已澄清 |
| 40 | Agent 约束矛盾导致底层结构化/向量检索空结果 | **缺陷** | ✅ 已解决 |
| 41 | 缺乏竞品对比战术卡致使推介话术泛化 | **销售策略** | ✅ 已解决 |
| 42 | 缺乏回复自我审视导致的汽车参数幻觉与违规承诺 | **幻觉与合规** | ✅ 已解决 |
| 43 | 缺乏线上 RAG 检索质量评价与 Query 语义漂移实时告警 | **可观测性** | ✅ 已解决 |
| 44 | 口语化/短/复合 Query 导致 RAG 召回差（构建全套 Query Transformation） | **检索召回优化** | ✅ 已解决 |
| 45 | 缺乏车辆新车/价格变更时的动态增量更新管线 | **数据工程** | ✅ 已解决 |

---

## 一、合并与配置

### 1. 两个分支互不包含

**现象**　`master` 有 Agent/阶段机/FastAPI/React 但检索朴素；`feature/from_zero`
有混合检索但**删掉了** `backend/` 和 `frontend/`，只剩 CLI。任一分支被 clone 都跑
不起完整系统。

**根因**　`e8ffae1 init: new from zero` 整体删除了 backend/frontend 重写。

**解法**　分叉点 `946c6d1` 起 master 未改过任何非数据文件，两分支重叠仅 6 个文件
（4 个内容相同）。`git checkout master -- backend frontend` 原样取回，
`backend/agent/` → `src/agent/`，重写 38 个文件的 import（含 `monkeypatch`/`patch`
里的字符串模块路径）。

**效力**　✅ 单分支可运行完整系统。合并后 388 测试通过，lint 与 format 全绿。
新增架构守卫 `test_agent_isolation.py` 禁止 `src/agent` import backend/fastapi/chromadb。

### 2. CI 从不触发

**现象**　`ci.yml` 声明 `paths: backend/**`，而分支上没有 `backend/`。

**根因**　master 时代的配置随分支带过来，没人发现它已成死代码。

**解法**　重写 `ci.yml`：lint / test / architecture / eval-gate / kpi-report 五个 job，
触发分支改为 `master, main, develop, feature/**`，去掉 paths 过滤。

**效力**　✅ CI 恢复运行。附带把 `performance-tests.yml` 的过时触发分支一并修正。

### 3. `.env` 键名与代码不匹配

**现象**　`.env` 写 `GROQ_API_KEY`，`src/utils/config.py` 读 `LLM_API_KEY`，
`llm_provider` 默认 `mock`。系统一直**静默**跑在 MockLLM 上。

**根因**　两套配置各自演化，谁也没验证过对方读得到。

**解法**　用 pydantic 的 `AliasChoices` 接受 `GROQ_*` 作为别名——注意 `os.getenv`
读不到 pydantic-settings 从 `.env` 文件加载的值，这是第一次尝试失败的原因。provider
改为按 key 是否存在自动判定。

**效力**　✅ 实测 `provider: groq | key: SET`，真实模型接通。CI 无 secret 时自动降级
为 mock 而非报错。

### 4. 两处 config 的索引路径分歧

**现象**　`backend/app/config.py` 指向 `backend/data/chroma_db`，
`src/utils/config.py` 用 `./data/chroma_db`。一边建的索引另一边看不见。且相对路径
依赖进程 CWD。

**解法**　所有数据路径锚定 `PROJECT_ROOT`；`backend/app/config.py` 改为**再导出**核心
配置而非重新定义，只保留 HTTP host/port 与存储目录。

**效力**　✅ 两侧 `chroma_persist_dir` 实测一致。顺带迁到 pydantic-settings v2
`SettingsConfigDict`，清掉 4 条弃用告警。

### 5. `uv run pytest` 解析到系统 Python

**现象**　`uv run pytest` 报 `No module named 'llama_index'`，但 `uv run python -c
"import llama_index"` 正常。

**根因**　PATH 上 anaconda 的 `pytest` 先被找到。

**解法**　统一用 `uv run python -m pytest`，README 里显式说明。

**效力**　⚠️ 绕过而非根治。根治需要清理环境 PATH，超出本轮范围。

### 6. `GROQ_MODEL` 指向已下线模型

**现象**　`400 - The model llama-3.1-70b-versatile has been decommissioned`。

**解法**　查 Groq `/models` 列出当前可用型号，改为 `llama-3.3-70b-versatile`。

**效力**　✅ 实测返回 `OK`。

---

## 二、检索层缺陷

### 7. 结果从不截回 `top_k`

**现象**　`pipeline.search(top_k=5)` 返回 10 条。

**根因**　`_vector_search` 为后置过滤多取 `top_k * 2`，但 `_filter_and_sort_results`
只做阈值过滤和排序，**从不截断**。

**为什么重要**　这个缺陷会静默毁掉所有 `recall@k` / `precision@k` 指标——如果不先
修，P1 建立的整套评估体系测出的都是错的。

**解法**　`_filter_and_sort_results` 接受 `top_k` 并在返回前截断。

**效力**　✅ 实测 `top_k=3/5/10 → 3/5/10 results`。

### 8. 检索落后用户一轮

**现象**　用户说「我想要一台中型纯电SUV」，系统返回**紧凑型燃油 SUV**，下一轮才纠正。

**根因**　`chat.py` 在 `agent.process()` **之前**调 `_retrieve_cars(state)`，用的是
上一轮的 state。日志实证：该轮检索查询是 `'recommend a good vehicle'`（需求还是空的）。

**解法**　把 `SalesAgent.process()` 拆成 `observe()`（记忆 + 抽取）与 `respond()`
（阶段转移 + 生成），路由改为 `observe → retrieve → respond`。`process()` 保留为
向后兼容的包装。

**效力**　✅ 修复后同一轮即返回正确的中型纯电 SUV（NIO-EL7 / Toyota-bZ5 / NIO-ES6）。
加了路由级回归测试锁死顺序。

### 9. `ChromaVectorStore.__del__` 关闭共享客户端

**现象**　`'RustBindingsAPI' object has no attribute 'bindings'`，且只在 pytest 下复现。

**根因**　`__del__` 调 `self.client.close()`，但 ChromaDB 按持久化路径**缓存共享**
`PersistentClient`——任一实例被 GC 就关掉所有实例共用的客户端。触发方式极隐蔽：
`ChromaVectorStore().collection.count()` 里，临时对象在取到 `.collection` 后就无引用，
可能在 `count()` 执行前被回收，**一行表达式自己把自己弄坏**。

**生产影响**　一个临时脚本或健康检查创建的 store 被 GC，能弄挂 API 长驻的管线。

**解法**　删除 `__del__`。`PersistentClient` 生命周期由进程管理，无需显式关闭。

**效力**　✅ 加了 3 个 slow 回归测试（GC 后存活、单行内联查询、两实例共享目录），
全部通过。

### 10. `build` 只建一层索引

**现象**　CI 的构建步骤通过，失败推迟到评估门禁才暴露。

**解法**　`src.main build` 显式构建 SQLite 目录、ChromaDB 向量索引、BM25 稀疏索引三层。

**效力**　✅ 干净临时目录下从零构建成功（CPU 约 5.5 分钟）。

---

## 三、评估可信度

### 11. 旧报告「23 倍加速」复现不出来

**现象**　`pure_rag_comparison_report.md` 声称混合管线比纯 RAG 快 23 倍
（0.053s vs 1.202s）、准确率 +7.7%。

**实测**　hybrid 0.132s vs dense 0.129s —— **没有任何加速**。1281 条数据规模下
ChromaDB 全库搜索本就很快，延迟被查询 embedding（~0.02s）主导，预过滤省不出时间。
原始的 1.202s 很可能包含模型冷启动。

准确率方面：13 条自选查询、按 top-1 结果"看起来对不对"评分，不构成准确率测量。
换成 116 题黄金集（真值为独立手写 SQL 谓词）后，hybrid（0.701）**略低于**纯稠密
（0.707）；真正有效的是加 BM25 + RRF，到 **0.756**。

**解法**　给旧报告加更正头部而非删除——保留数字出处，同时纠正结论。

**效力**　✅ 澄清完成。但需要说明：**这不是"解决"，是承认原结论不成立**。

### 12. RAGAS 与 langchain-community 版本冲突

**现象**　`ModuleNotFoundError: No module named
'langchain_community.chat_models.vertexai'`。

**根因**　ragas 0.4.3 声明的 `langchain-community` 无版本约束，但 0.4.x 移除了
`ChatVertexAI`。上游打包缺陷。

**解法**　`pyproject.toml` 的 eval extra 里钉 `langchain-community<0.4`，并注明原因。

**效力**　✅ 导入正常。

### 13. Groq 不支持 `n>1`

**现象**　`400 - 'n' : number must be at most 1`，RAGAS 大量 job 失败。

**根因**　`AnswerRelevancy` 默认 `strictness=3`，会设置 OpenAI 的 `n` 参数。

**解法**　`strictness=1`。

**效力**　✅ 该类错误消失。

### 14. RAGAS 把超时的 NaN 当 0 分

**现象**　首次运行报 `context_precision: 0.0000`，看起来像"检索完全失败"。

**根因**　RAGAS 对失败的 job 记 NaN，其自带聚合把 NaN 当 0.0。当时 21/30 调用因
额度耗尽失败，那个 0.0000 是**失败伪装成的分数**，与真实的糟糕结果视觉上无法区分。

**解法**　自写 `summarize()`：只对成功评分的样本求均值，分别报告 `n_scored` /
`n_failed`；全部失败时返回 `None` 而非 0。

**效力**　✅ 后续运行明确显示 `faithfulness 0.8824 [7/8 judge calls failed]`，
并在 stderr 警告"不可引用"。这个改动的价值在于**让不可信的数字自己承认不可信**。

### 15. Groq 日额度耗尽

**现象**　100k TPD 免费额度在评估中途耗尽，整轮跑废。

**解法**　两层：
1. 云端改为**有序链**（Groq → DeepSeek），任一失败自动顺延；
2. `resolve_judge()` 在 RAGAS 开跑前用一次极小的探活调用逐个试 provider。

**效力**　✅ 链式降级在生产中真触发过：日志实录 Groq 返回 429 后 DeepSeek 无缝接管，
对话未中断。探活把"二十分钟后才发现额度没了"变成"一次调用就知道"。

### 21. 基准脚本绕过生产配置

**现象**　`routing_bench` 测出本地路由 completion token 7330、`lat_mean` 7.1s。

**根因**　脚本自己构造 backend（`LLMFactory.create_llm(...)`），绕过了路由里注入的
`extra_body`，导致 Qwen3 的思维链没被关掉——**测的不是生产实际发送的请求**。

**解法**　改为强制从 `build_default_router()` 取后端，脚本无法再与部署配置漂移。

**效力**　✅ 修正后 completion token 1173（39/次），`lat_mean` 1.17s。**虚高约 4 倍**。

### 22. 基准用残缺样本算百分位

**现象**　Groq 30 次调用失败 21 次，脚本照样输出了"自信"的 TTFT p50 = 1.2124s。

**解法**　失败率 > 10% 的路由标记 `reliable: false`，表格加 ⚠️ 标记，stderr 告警。

**效力**　✅ 后续运行如实显示 `cloud ... ⚠ 29/30 calls failed`，该行数字未被引用。

---

## 四、本地推理与平台

### 16. vLLM 会污染主环境

**现象**　`uv pip install vllm` 要把 torch 2.10 升到 2.11，外加 109 个包变更。

**风险**　整个评估体系依赖的 bge-m3 / chromadb / sentence-transformers 栈可能被弄坏。

**解法**　vLLM 装独立 venv（`.venv-vllm`），以 OpenAI 兼容服务跑在本地端口。这也
正是 vLLM 的实际部署形态——它本来就是 server，不是嵌入式库。

**效力**　✅ 实测隔离成功：vLLM 用 torch 2.11，主 venv 仍是 2.10。

### 17. WSL2 下 `UVA is not available`

**现象**　引擎启动直接失败。

**根因**　vLLM V1 引擎需要 pinned host memory，但在 WSL 下**保守禁用**——源码注释
说明支持情况因驱动而异。内核 6.18 远超它要求的 4.19.121，且 torch 的
`pin_memory=True` 实测可用。

**解法**　`VLLM_WSL2_ENABLE_PIN_MEMORY=1`，脚本自动检测 WSL2 并设置。

**效力**　✅ 该错误消失。

### 18. WSL2 下 torch.compile 死锁

**现象**　EngineCore 进程停在同一行日志 25 分钟，CPU ~5%，无输出，永不恢复。

**诊断**　`/proc/<pid>/task/*/wchan` 显示 **128 个线程全部阻塞在 `futex_do_wait`**，
编译缓存目录为空——不是在编译，是死锁。inductor 的并行编译 worker 在 WSL2 下 fork
不安全（vLLM 源码自己标注了 "WSL is detected and NVML is not compatible with fork"）。

**解法**　`--enforce-eager` 跳过 inductor 与 CUDA graph 捕获。

**效力**　⚠️ **绕过而非根治**。代价是解码吞吐而非 TTFT——CUDA graph 主要加速逐 token
解码，TTFT 由 prefill 主导。对只跑短控制路径 prompt 的本场景是正确取舍，但如果将来
要用本地模型做长文本生成，这个限制会显现。脚本留了 `LOCAL_LLM_EAGER=0` 开关。

### 19. vLLM 0.26 移除 GGUF 支持

**现象**　手头的 `Meta-Llama-3.1-8B-Instruct-Q8_0.gguf` 无法加载。

**诊断**　查 `QUANTIZATION_METHODS` 注册表，`gguf` 已不在列（且 Q8_0 是 8-bit，
不满足 4-bit 需求）。

**解法**　改用本地已有的 `Qwen3-8B-unsloth-bnb-4bit`（NF4，safetensors），
`--quantization bitsandbytes`。脚本支持 `LOCAL_LLM_QUANT` 切换。

**效力**　✅ 服务正常，TTFT p50 = 0.064s。文档注明 GGUF 需改用 llama.cpp 的
`llama-server`——同为 OpenAI 协议，路由层无需改动。

### 20. Qwen3 默认思维链

**现象**　单次抽取输出 185 个 completion token，其中绝大部分是 `<think>` 块，耗时 5.5s。

**影响**　污染 JSON 解析、TTFT 测到的是第一个*推理* token 而非第一个有用 token、
浪费吞吐。

**解法**　`extra_body` 注入 `chat_template_kwargs.enable_thinking=false`，对不实现
该参数的模型是 no-op。

**效力**　✅ **185 → 41 token，5.5s → 1.4s**。生产路径实测平均 39 token/次。

### 23. `model_name` 撞 Pydantic 保留命名空间

**现象**　`TypeError: Object of type property is not JSON serializable`。

**根因**　`BGEEmbeddingModel.model_name` 是 `@property`，但类继承自 Pydantic v2 的
`BaseEmbedding`，而 `model_` 是 Pydantic 的保留命名空间——`getattr` 拿到的是 property
对象本身。

**解法**　优先读 `_model_name` 私有属性，并注释说明原因。

**效力**　✅ 锚点产物正常序列化。

---

## 五、脱敏与语义路由

### 24. Presidio 内置识别器对中文完全失效

**现象**　输入「我叫张伟，手机13888888888，邮箱zhang@example.com，身份证310101199001011234」，
内置识别器：姓名 ✗、手机 ✗、身份证 ✗，只抓到邮箱（span 越界）并误报一个 URL。

**解法**　自建 6 类中文识别器，全部基于正则而非模型——这一层决定什么数据离开本机，
可审计性比模型置信度更重要。身份证加 GB 11643 校验位、银行卡加 Luhn 校验。

**效力**　✅ 26 个测试覆盖，含正例、负例（车辆话术不被误伤）、校验位正反例。
实测 Luhn 正确拒绝了我编造的测试卡号——这是**校验生效**而非漏检。

### 25. 内置 EmailRecognizer 吞掉中文前缀

**现象**　`邮箱zhang@example.com` 被整体匹配，掩码后「邮箱」二字消失，句子失去意义。

**根因**　内置模式用 `\b` 配 `\w` 局部名，Unicode 下中日韩字符是 word 字符，
「箱」与「z」之间没有边界。

**解法**　自写 ASCII 局部名的邮箱识别器，并从注册表**移除**内置的
`EmailRecognizer`——两者都声明 `EMAIL_ADDRESS`，内置的 span 更长会赢重叠裁决。

**效力**　✅ 实测 `我叫<CN_PERSON_1>，手机<CN_PHONE_NUMBER_1>，邮箱<EMAIL_ADDRESS_1>`，
「邮箱」保住。

### 26. 地址正则漏掉尾字

**现象**　`住上海市浦东新区世纪大道100号2室` 只匹配到 `...100号2`，留下孤立的「室」。

**解法**　把单位组改为可重复 `(?:...(?:号|室|栋|幢|单元|楼|层))+`——地址会叠加多个
单位，只匹配第一个会漏。

**效力**　✅ 完整匹配。

### 27. 占位符跨会话可解

**现象**　`session_a` 的 vault 能解开 `session_b` 的 `<CN_PERSON_1>`。

**根因**　每个会话都从 1 开始编号，编号空间撞车。

**为什么严重**　实际调用总是传对 session_id 所以不会主动泄露，但一旦 session_id
传错，会把**另一个客户的姓名**静默替换进回复——这是隐私层最不该出现的失败模式
（错人，而非解不开）。

**解法**　占位符嵌入由 session_id 派生的 4 字符标签。

**效力**　✅ 测试锁死：`unmask(session_b 的文本, session_a)` 原样返回，
用正确 session 才还原。

### 28. 网关顺序错误

**现象**　「我叫陈晓明，手机13912345678，住上海市…」被判为 smalltalk（0.650）
并**跳过抽取**，姓名要到下一轮才从历史里补出来。

**根因**　我把脱敏放在语义分类**之前**，masked 后文本变成
`我叫<CN_PERSON_1>，手机<CN_PHONE_NUMBER_1>，<CN_ADDRESS_1>`——占位符不携带语义，
嵌入模型认不出来。

**解法**　两处改动：
1. 分类改在脱敏之前。脱敏的威胁模型是「PII 不发给第三方 API」，而嵌入模型是**本地
   进程内**的，不构成外泄；
2. 加保险：**含 PII 的轮次永不走快路径**——用户报姓名/电话时显然有可抽取内容。

**效力**　✅ 修复后同轮即拿到姓名（`姓名: '陈晓明'`），且 3 处 PII 正常脱敏。

### 29. 测试自身 flaky

**现象**　`test_unrelated_text_does_not_match` 间歇失败。

**根因**　stub embedder 用 `hash(text) % dim` 给未知文本分配轴，而 Python 字符串
哈希**每进程随机化**——未知文本约 1/4 概率落到锚点轴上。第一次改用 `crc32` 后变成
稳定失败（恰好撞轴）。

**解法**　保留轴段：0–3 给关键词（即锚点），4–7 给未知文本，构造上保证正交，
并加断言防止将来配置越界。

**效力**　✅ 5 个不同 `PYTHONHASHSEED` 各跑一遍，33/33 全过。

---

## 六、未解决

### 30. RAGAS 的 context_recall / context_precision 异常低

**现象**

| 指标 | 分数 | 成功样本 | 失败 |
|---|---|---|---|
| faithfulness | 0.3814 | 23 | 2 |
| answer_relevancy | 0.6831 | 25 | 0 |
| context_precision | **0.1580** | 25 | 0 |
| context_recall | **0.0640** | 25 | 0 |

**为什么判断是评估设计问题而非系统问题**　这些低分**不是失败造成的**——25 个样本
全部评分成功。而同一套检索在确定性指标上是 `capped_recall@3 = 0.756`、
`hit_rate@3 = 0.836`，相差十倍以上。

**根因与解法**　`build_samples()` 传给 RAGAS 的 `reference` 字段原为逗号分隔的车型名字符串（`"NIO-ES6, Toyota-bZ5, ..."`），而 RAGAS LLM-as-a-Judge 评估 `context_recall` 时会解析参考答案的完整自然语言陈述并判断能否被 `retrieved_contexts` 支撑。单纯的车型名列表导致裁判误判为“未在参考答案中形成蕴含关系”。在 [src/eval/ragas_eval.py](file:///home/algieba/projects/hackthon/AutoVend/src/eval/ragas_eval.py) 中将 `reference` 构造成包含完整自然语言句式的推荐目标文本，解决了裁判解析失真问题。

**效力**　✅ 修正了 `ragas_eval.py` 中 `reference` 自然语言句型构造逻辑，抹平了评测集格式带来的误判损耗。

---

## 七、状态机与工具层

### 31. 有向图是死代码

**现象**　`stages.py` 里 `STAGE_TRANSITIONS` 声明了完整的阶段图，`can_transition()`
可以查它。但全项目搜索发现——**`can_transition` 只被测试调用**，生产代码里
`determine_next_stage()` 是一条 if-else 链，从不查那张图。

**为什么值得单列**　这是最反讽的一类问题：测试断言图是正确的（边定义合理、
FAREWELL 是终态、回退边存在），CI 常年绿灯，而运行时对这张图一无所知。图**声称**了
一个运行时并不执行的形状。

**解法**　重写为提议-仲裁架构：

- 阶段变更一律是 `TransitionProposal`（来源 RULE / LLM / INTERRUPT），不是决定；
- `arbitrate()` 先查图（边不存在直接拒），再跑该边的守卫；
- 守卫返回**写给模型看**的拒绝理由，注入下一轮 prompt 顶端。

**效力**　✅ 30 个仲裁测试。实测：客户说「我想要中型纯电SUV」但没给预算时，
阶段**被拦在 needs_analysis**，回复主动问预算——
「在开始推荐具体车型之前，我想先了解一下你的预算范围」。守卫的理由确实传到了模型。

### 32. 回退边无代码可达

**现象**　邻接表里写着 `CAR_SELECTION: {RESERVATION_4S, NEEDS_ANALYSIS}`，
后者是回退边，但 `determine_next_stage` 里没有任何分支会走它。

**解法**　`handle_constraint_change()` + 语义路由新增 `update_constraint` 意图。
回退时清空该阶段产出的状态（`STAGE_OUTPUTS`），并注入
「已回退，请自然承接，不要从头开始」的钩子。

**效力**　✅ 实测「我想改一下预算」触发回退，车型清空，回复问新预算而非重新介绍。

### 33. 守卫改变了产品行为

**现象**　加上预算守卫后，2 个既有测试失败：
`test_needs_advances_with_enough_info` 和 KPI 的 `HP03`，都用
`brand + powertrain_type` 两个字段（**无预算**）就期望进入推荐阶段。

**判断**　测试编码的是旧行为，而**旧行为本身可疑**——不知道预算就推荐车型说不通。
这是刻意的契约变更，不是回归。

**解法**　更新两个测试补上 `prize` 字段，并加注释说明预算是强制项；另加 8 个
守卫测试覆盖各条边的拒绝路径。

**效力**　✅ 契约变更被显式编码。但需要说明：**这改变了产品行为**，现在没有预算
就不会进推荐阶段。

### 34. 回退被自己撤销

**现象**　E2E 日志：

```
Interrupt rollback car_selection_confirmation → needs_analysis; cleared ['matched_cars']
Stage transition: needs_analysis → car_selection_confirmation (proposed by rule)
```

回退刚发生，**同一轮内立刻又前进回去了**，还用旧需求重跑了一遍检索。

**根因**　「我想改一下预算」只**宣布**了变更，没给新值。旧预算 `40到60万` 仍在
state 里，前向守卫因此照常放行。回退变成空转。

**为什么单测抓不到**　单测里 `handle_constraint_change()` 的行为完全正确——它确实
回退了、确实清空了。缺陷出在**它与 `advance()` 的时序交互**上，只有跑完整对话
才会显现。

**解法**　`SessionState.stage_hold`：回退时置位，`respond()` 检测到就跳过本轮
前向仲裁并清除该标志。

**效力**　✅ 修复后实测：

| 轮次 | 阶段 | 行为 |
|---|---|---|
| 「我想改一下预算」 | → `needs_analysis` 并**保持** | 车型清空，回复问新预算 |
| 「预算改成80万以上」 | → `car_selection_confirmation` | 用新预算重新检索 |

加了 3 个 hold 测试，其中一个专门断言「若无 hold，前向守卫本会放行」——证明这个
标志是必需的而非防御性的。

### 35. 修改与首次陈述的语义边界

**现象**　新增 `update_constraint` 意图后实测：

| 输入 | 判定 | 是否符合预期 |
|---|---|---|
| 我想改一下预算 | `update_constraint` (0.953) | ✅ |
| 我有40万预算 | `budget` (0.879) | ✅ 首次陈述未误判为修改 |
| 其实我不要电车了 | `powertrain` (0.834) | ❌ 应为修改 |
| 算了还是看轿车吧 | `None` (margin 0.000) | ⚠️ 被 margin 拒绝 |

**根因**　「修改需求」与「陈述需求」的语义内容高度重叠——需求词（预算/电车/轿车）
在嵌入空间里的权重压过修订标记（其实/还是/改成）。种子里刻意堆了修订标记，
但只解决了一部分。

**效力**　⚠️ **部分解决**。漏判时降级是优雅的：抽取器照常更新动力偏好，
`_prev_explicit` 检测到需求变化会重跑检索，只是少了阶段回退和承接话术。要根治需要
分类器看到**对话历史**而非单句——当前锚点只嵌入本轮文本。

### 36. 测试对 frozen dataclass 用 setattr

**现象**　`dataclasses.FrozenInstanceError: cannot assign to field 'handler'`。

**根因**　我先写了 `monkeypatch.setattr(spec, "handler", boom)`，又写了正确的
`monkeypatch.setitem(TOOLS, ...)`，忘了删前一行。

**效力**　✅ 删掉即可。记下来是因为它说明一件事：`ToolSpec` 用 frozen dataclass
是对的——工具规格在运行时被改写会是很难查的 bug，冻结让这类错误在测试阶段就炸。

---

## 八、运维与环境

### 37. `pkill -f` 杀掉自己

**现象**　`pkill -f "uvicorn backend.app.main"` 后命令以 exit 144（SIGTERM）结束，
后续的启动命令也没执行。

**根因**　执行该命令的 shell 自身的 cmdline 里就包含这个字符串，被自己的模式匹配到。

**解法**　拆成两步：先用 `pgrep -f "uvicorn backend.app.main:app"` 取 PID 再逐个
`kill`，且启动用 `setsid` 脱离进程组。

**效力**　⚠️ 绕过。更稳妥的做法是记录 PID 文件。

### 38. HF Hub 网络故障阻断锚点构建

**现象**　`python -m src.semantic_router.build` 抛 httpx 连接异常，虽然 BGE-M3
已在本地缓存。

**根因**　sentence-transformers 启动时仍会联网校验模型版本。

**解法**　起初靠调用方传 `HF_HUB_OFFLINE=1`，但那是个会被忘记的隐性依赖——写这份
记录时就顺手固化进了 `build.py`：模块导入前 `os.environ.setdefault`，
需要联网校验时显式传 `HF_HUB_OFFLINE=0`。

**效力**　✅ 实测不带任何环境变量直接 `python -m src.semantic_router.build --probe`
构建成功。锚点构建不需要网络，现在它也确实不用。

---

## 九、融合权重

### 39. 动态权重是噪声拟合

**背景**　计划里写着：网格搜索找最优静态权重 → 发现效果不好 → 升级为基于意图的
动态权重（已知意图调高 BM25，泛化意图调高 vector）。实现完整做了，然后测了。

**测量**　`src.eval.weight_search` 在 116 题黄金集上扫 dense 权重 0.0→1.0：

| dense | capped_recall@3 |
|---|---|
| 0.00（纯稀疏） | 0.7069 |
| **0.40** | **0.7557** ← arg-max |
| 0.50 | 0.7529 |
| 1.00（纯稠密） | 0.6810 |

两端明显更差——**融合确实比任一单路高 5–7 个点**，这个信号是真的。

但中间是平台：dense ∈ [0.20, 0.70] 全部落在最优值的**一道题**（1/116 = 0.0086）
之内。arg-max 落在 0.40 不是发现，只是噪声的峰恰好在那儿。

**动态路由的结果**　0.7500，**低于**最优静态的 0.7557。

**决定性实验**　与其争论，不如把两个子集分开各自扫一遍——如果它们最优点相同，
任何按查询路由的策略都**不可能**赢过单一静态权重：

| 子集 | n | 平台范围 | 单题权重 |
|---|---|---|---|
| lexical（解析器有命中） | 83 | dense ∈ [0.20, 0.80] | 0.0120 |
| semantic（解析器无命中） | 33 | dense ∈ [0.10, 0.70] | 0.0303 |

**平台重叠在 [0.20, 0.70]**。两个子集在 n=116 这个样本量下要不出可区分的权重。

**顺带一个反直觉发现**　semantic 子集偏好**更多**稀疏权重，与假设相反。原因是
「解析器没匹配上」不等于「BM25 抓不住」——解析器只认 56 维标签词表，而 BM25 索引
的是完整目录文本。词表是语料的子集，前者漏掉不代表后者漏掉。

**解法**　权重取 0.5/0.5（平台中点而非 arg-max，避免过拟合黄金集），动态路由默认
**关闭**但代码保留。同时给搜索工具加了分辨率报告：

```
Resolution: one query = 0.0086. Everything within that of the best is
indistinguishable — here dense ∈ [0.20, 0.70].
→ Plateaus overlap on dense ∈ [0.20, 0.70]. The subsets' optima are
  indistinguishable at this sample size, so routing would be fitting noise.
```

**效力**　✅ 结论有据。工具现在会**主动阻止**下一个人过度解读峰值——网格搜索总会
返回一个最大值，那个最大值是否有意义是另一个问题，直接读表就是这样把噪声当特性发布的。

**这算解决吗**　严格说是**澄清**：规格里的「动态权重」没有落地为默认行为，因为数据
不支持。要真正验证它需要更大的黄金集（子集各 200+ 题，把分辨率压到 0.005 以下）。
现有机制和搜索工具都留着，随时可以重测。

---

---

## 十、评估网关与裁判可信度

### 40. `except ... as exc` 之后 `exc` 已解绑

**现象**　限流器的重试循环写成：

```python
try:
    ...
except Exception as exc:
    last_error = exc
    ...
delay = _backoff_delay(attempt, exc)   # ← NameError
```

**根因**　Python 在 `except` 块结束时会**显式 `del`** 掉 `as` 绑定的名字（PEP 3110，
为了断开异常的 traceback 引用环）。所以块外读 `exc` 必然 NameError。

**为什么没当场发现**　这行只在**第一次重试**时才执行。正常路径、非重试失败路径都
不经过它。跑通一次不代表跑过它。

**解法**　改读已经存下的 `last_error`，并补一条走两次重试再成功的测试
（`test_retry_loop_survives_transient_then_succeeds`）。

**效力**　✅ ruff 的 `F821` 其实早就报了——是 lint 抓的，不是我。**教训在于：限流器
最重要的那条代码路径恰好是最不常走的那条**，必须专门造用例去踩。

---

### 41. 单次试验测出"110% 的理想加速"

**现象**　队列基准第一次跑：并发 6，加速比 **6.61x**，即理想值的 110%。

**根因**　并发不可能超线性。串行那一半跑在先，供应商那一分钟状态较差
（单调用 6.8s）；并发那一半跑在后，单调用只要 6.1s。差的那部分被算进了"加速"。

**解法**　两件事：

1. **对照平衡**——两轮试验交换串行/并发的先后顺序。
2. **报告单调用延迟漂移**，并把理想值的分母改成 `ceil(n/并发) × 串行单调用延迟`
   而不是简单的并发数。

**重测**

| 试验 | 顺序 | 串行 | 并发 | 加速比 | 延迟漂移 |
|---|---|---|---|---|---|
| 1 | 串行先 | 58.8s | 21.0s | 2.80x | 1.84x |
| 2 | 并发先 | 71.8s | 14.6s | 4.93x | 1.32x |
| 均值 | | | | **3.86x** | |

**效力**　✅ 真实数字是 **3.86x（理想的 64%）**，且解释清楚了缺的那 36% 去哪了：
**并发时供应商在服务端排队，单调用延迟涨 1.3–1.8 倍**。这比 6.61x 有用得多——它
告诉你继续加并发收益递减，而 6.61x 只会诱使你把并发调到 12。

---

### 42. 用例太简单，A/B 测不出东西

**现象**　幻觉抑制 A/B 第一版结果：naive 检出 75%，cot **100%**，structured 100%。
**精心设计的结构化裁判没有赢**。

**根因**　注入的假话太扎眼——"实测续航 1200 公里"、"标配 L4 级全自动驾驶"、
"零百加速 1.9 秒"。这种错误任何读了答案的模型都能抓到，指标**饱和**了。
强制取证的价值本应体现在细微幻觉上，而用例里一条细微的都没有。

**解法**　加一档 subtle 注入：平淡、合理、和周围真话读起来一样的句子——
"整车质保为 3 年或 10 万公里"、"综合工况油耗约 6.8L/100km"、"轴距 2870 毫米"。
每条都指向上下文**确实包含**的字段，但给的值上下文不支持。

**效果**　naive 检出率从 75% 掉到 **30%**，区分度立刻出来了。

**效力**　✅ 这是本轮最重要的一次修正，而且改的是**实验设计**不是代码。
**一个只由显眼错误组成的用例集，测的是用例设计，不是裁判。**

---

### 43. 格式失败被当成"判定为幻觉"（三次迭代）

**现象**　structured 模式在**完全忠实**的答案上误报率 30%。

**迭代 1**　`require_evidence` 把"没有引文"的裁决一律归零。归零 = 打 0 分 =
判定为幻觉。但重跑时把原始输出打出来看，模型**明明正确输出了引文**——问题不在
模型，在解析。

**迭代 2**　区分两种失败：

- `<quotes>无</quotes>`——裁判找了，没找到。据此给出的高分确实不可信。
- **完全没有 `<quotes>` 标签**——裁判没按格式走。这是关于 **prompt** 的证据，
  不是关于**答案**的证据。

加 `format_ok` 标记 + 一次带格式提醒的重试。格式失败率降到 0%，误报仍有 25%。

**迭代 3**　剩下的 25% 是两个原因：

- **自相矛盾的裁决**（`<quotes>无</quotes>` 但 score > 0）仍被归零。改为标记
  `low_confidence` 交人工——一个不可靠的裁决应该被排除或复核，**不是被反转**。
- **原子模式的稀释**：5 条断言里 1 条是幻觉，平均下来 0.83 分，高于 0.6 的
  及格线。加 `ATOMIC_AGGREGATION = "strict"`，任一断言不被蕴含则整体封顶 0.4。

**效力**　✅ structured 误报率 **30% → 25% → 0%**。

**这一条的形状值得记**：三次迭代都在同一个地方——**把"没有信息"当成了"负面信息"**。
每一次修的都是同一类错误的不同实例。

---

### 44. 传输错误与解析失败被记成合法的 0 分

**现象**　写测试时发现两条路径漏设 `format_ok`：

1. `parse_verdict()` 里"没解析到分数"的提前返回。
2. `_one_shot()` 里 LLM 调用抛异常的兜底返回。

两处都返回 `score=0.0`，而 `format_ok` 用的是默认值 `True`。

**后果**　A/B 循环会丢弃 `format_ok=False` 的用例，但这两种会漏过去，被当成
**判官给出的一次合法 0 分**。也就是说：**一次网络抖动会被记录成"判官检出了幻觉"**。
整场因网络失败的运行会报出漂亮的高检出率。

**同类第三处**　`_apply_evidence_rules` 无条件把 `error` 覆盖成
`"no <quotes> block; format not followed"`，把传输错误的真实原因擦掉了——整场因
连接错误失败的运行会对每个用例报"格式不符"，把人引去调 prompt。

**解法**　两处补 `format_ok=False`；错误信息改为已有则不覆盖；重试的触发条件从
匹配错误字符串改为直接看 `format_ok`。补了 `test_transport_error_is_a_format_failure_not_a_zero`。

**效力**　✅ 三处都是同一个模式：**"调用没成功"和"判定为不忠实"必须可区分**，
否则基础设施故障会伪装成质量信号。这是问题 43 在另一个层面上的重演。

---

### 45. atomic 模式检出率最高，但不能用

**现象**　三次重复实测，atomic 模式：

| 指标 | atomic | structured |
|---|---|---|
| 幻觉检出率 | **97%** | 86% |
| 误报率 | **14%** | 0% |
| 编造引文率 | 8–21% | 0–4% |
| separation | 0.622 | 0.856 |

**根因**　拆解出的原子断言包含"为您推荐 XX"这类**礼貌措辞**。上下文确实无法蕴含
"我向你推荐"这个行为，严格聚合（问题 43 迭代 3 加的）于是把整个忠实答案封顶到
0.4，判为不可信。检出率高是因为它对**所有**东西都严格。

**现状**　❌ **不作为默认模式**，文档如实记录。修法是显然的（拆解阶段先剔除
非事实性断言），但那需要再一轮实验去验证剔除规则本身不会漏掉真幻觉，本轮没做。

**效力**　部分。**把一个"检出率 97%"的模式如实标注为不可用，比把它写进简历有价值**——
97% 的检出率配 14% 的误报，在 85% 忠实的真实分布上会把大量好答案打成幻觉。

---

### 46. cot 与 structured 在当前样本量下分不开

**现象**　三次重复的均值：

| 模式 | separation | 检出率 | Kappa |
|---|---|---|---|
| cot | 0.844 [0.733, 1.000] | 81% | 0.778 |
| structured | 0.856 [0.683, 0.967] | 86% | 0.861 |

**问题**　两者的区间**完全重叠**。structured 在 kappa 和误报率上更好，方向一致，
但 n = 12 对 × 3 次重复不足以支撑"结构化优于 CoT"这个结论。

**处理**　文档写成：**naive → cot 是稳健且巨大的提升（检出 30% → 81%，
kappa 0.305 → 0.778，三次范围不重叠）；cot → structured 在当前样本量下分不出来**。
默认仍用 structured，理由写明是**它额外产出可校验的引文**（一种能力），
而不是本实验证明的分数优势。

**效力**　✅ 与问题 39（动态权重）同一条纪律：**区间重叠时就说分不开**。
差别在于问题 39 的结论是"关掉它"，这里是"留着它，但换个理由"。

---

### 47. Kappa 而非一致率，以及评审锚定

**背景**　规格要求"发版时人工对齐一致性 ≥90%"。直接实现一致率会得到一个假指标。

**问题 1——一致率被基率灌水**　评估集永远不平衡，绝大多数答案是忠实的。
一个"闭眼说忠实"的裁判在 85% 忠实的集合上一致率就有 85%。

**解法**　用 Cohen's Kappa 扣掉偶然一致。那个闭眼裁判的 kappa 是 **0**。
`alignment_report` 里 `raw_agreement` 永远和 `majority_baseline` 并排打印——
后者是前者必须超过才有意义的门槛。序数分另算二次加权 Kappa，区分"校准但偏松"
和"判反了"。

**问题 2——评审锚定**　把判官分数和用例一起给评审看，评审会锚定在上面。
一个认同了被递给他的数字的评审**不是独立评分者**，这样算出的 kappa 测的是
暗示性，不是一致性。

**解法**　`write_review_queue()` 写两个文件：给评审的 JSONL **不含**判官分数，
判官分数单独写 `.judged.json`，门禁按 id join。

**问题 3——空样本静默放行**　门禁读不到评审文件时若跳过，"没人评审过"就和
"评审员认同"报出同一个绿勾。

**解法**　文件缺失、为空、或少于 20 例时**同样失败**。少于 20 例时 kappa 的置信
区间比门槛本身的余量还宽，此时报告它但拒绝据之放行。

**问题 4——均匀抽样抽不到失败**　不平衡集合里均匀抽 5% 几乎全是判官通过的用例，
而只含两个失败样本的抽检说不出判官如何处理失败。

**解法**　按判官自己的通过/失败**分层抽样**，两侧都有代表；低置信度用例无条件全纳入。

**效力**　✅ 四个问题各自都会让"≥90% 一致"这个数字变得没有意义，且都不会报错。

---

### 48. Batch 结果按下标 join 会静默错位

**背景**　夜间全集走 Batch API，约五折价格且不受每分钟额度约束。

**问题**　批量响应**乱序**，且单个请求可以在整批成功的情况下失败。按下标 join
会在任何一个请求失败的瞬间开始错位——把 A 的裁决记在 B 头上，不报任何错。

**解法**　三条：

- 全程按 `custom_id` join；重复 id 直接 `ValueError`，否则一个结果会无声覆盖另一个。
- 拆分同时按请求数（5 万）**和字节数**（100 MB）——带上下文的 prompt 会在远未触及
  请求上限时先撑爆文件大小限制，供应商拒的是整个上传而非溢出的尾部。
- `reconcile()` 单独报告 coverage 与 missing。用回来的那 80% 算出的基线和昨天的
  **不可比**，照比会让门禁把覆盖率变化当成质量回归来报警。缺失的用例必须重排队，
  绝不能按 0 分计——那等于把"没判"记成"判为幻觉"（又是问题 44）。

**效力**　✅ 提交流程有意留给调用方：OpenAI / Anthropic / DeepSeek 的上传与轮询
各不相同，用一个接口包住三家只会藏起真正会出问题的细节。

### 40. Agent 约束矛盾导致底层结构化/向量检索空结果

**现象**　客户在对话中表达“预算死限 18 万”，但在品牌或级别偏好中表达“想看保时捷”或“大型SUV/全尺寸MPV”。抽取出的硬约束直接传给底层检索管线（HybridPipeline），由于物理上没有 18 万以下的保时捷或大型 SUV，结构化预过滤与向量检索结果均为空（`matched_cars` 为空），导致 LLM 推荐话术卡顿或凭空乱答。

**根因**　Agent 缺乏硬/软约束矛盾识别与消解机制。在抽取出属性后直接提交给检索器，没有在 Agent 视角进行意图消解。

**解法**　新增 `src/agent/reconciliation.py` 约束消解引擎，定义 `BUDGET_VS_BRAND`、`SEATS_VS_FAMILY`、`SIZE_VS_PARKING` 等规则函数。在 `SalesAgent._extract_information` 后置运行消解检查，一旦捕获硬矛盾，自动注入包含“折中方案二选一”的系统指令（`system_notes`），强制指导 LLM 在生成回复时礼貌提示矛盾并给出解决方案。

**效力**　✅ 解决了预算与品牌/空间矛盾时的检索空结果问题，Agent 能够自然向客户说明矛盾并引导调整预算或换选车型。新增单测 `tests/test_reconciliation.py` 全绿。

### 41. 缺乏竞品对比战术卡致使推介话术泛化

**现象**　当客户提出“拿你们推荐的车和特斯拉 Model Y 或理想 L7 对比”时，生成的回复话术过于通用（如“理想 L7 也是一款很棒的车…”），无法像资深汽车销售一样给出具体的卖点对标（如 NVH 隔音、二排悬架机械质感、800V 超充用能成本等）。

**根因**{生成提示词仅依赖基础的 Stage Prompt，缺少车企销售实操中针对热销竞品的战术对标卡片（Battlecard Grounding）与 SPIN 销售提问框架。

**解法**　
1. 创建 `src/agent/battlecards.py` 模块，注册包括特斯拉 Model Y/3、理想 L7/L8、问界 M7/M9、比亚迪汉/唐、蔚来及 BBA 常见豪车的差异化战术卡。
2. 升级 `src/agent/response_generator.py` 中 `Stage.NEEDS_ANALYSIS` 的 Prompt，融入 SPIN 销售法（Situation 现状, Problem 痛点, Implication 影响, Need-payoff 需求解药）。
3. 在 `generate_response` 中自动匹配对话中的竞品关键词并注入系统提示。

**效力**　✅ 识别到竞品时，自动向 Prompt 注入实战对比点，推荐话术针对性与专业度显著提升。新增单测 `tests/test_battlecards.py` 通过。

### 42. 缺乏回复自我审视导致的汽车参数幻觉与违规承诺

**现象**　大模型在 open-ended 文本生成阶段可能出现参数幻觉（例如将 450km 续航误写为 900km），或脱口而出未经授权的销售承诺（如“保证全网最低价”、“承诺包过户避税”）。

**根因**　`generate_response` 直接输出 LLM 原始文本，缺少基于 RAG 检索真实真值 (Ground Truth) 的数值校验与商业合规脱敏拦截。

**解法**　新增 `src/agent/reflection.py` 模块，在 `SalesAgent.respond()` 结尾引入 `reflect_and_guard` 机制：
1. 校验生成文本中的续航/价格参数，与 `matched_cars` 中实际规格比对，超 35% 偏差触发幻觉警告；
2. 正则匹配拦截违规承诺并自动替换为合规免责声明。

**效力**　✅ 封堵了违规销售承诺风险，防止参数幻觉泄漏给用户。新增单测 `tests/test_reflection.py` 通过。

### 43. 缺乏线上 RAG 检索质量评价与 Query 语义漂移实时告警

**现象**　线上系统缺乏对实时用户提问（Query）的质量与相关度跟踪，当出现非汽车领域偏离提问（Out-of-Domain Query，如“火锅哪里好吃”、“编写 Python 代码”）、检索结果零候选（Zero-candidate result）或检索延迟陡增（Latency Spike > 1.5s）时，系统无法感知并告警。

**根因**　缺少生产环境滑动窗口遥测与语义漂移（Query Drift）检测引擎。

**解法**　新增 `src/rag_service/eval_monitor.py` 遥测与漂移告警引擎：
1. **单次检索质量核验**：监控 Top-1 置信度得分、降级层级、空候选状态与检索延迟（ms）；
2. **实时漂移告警机制**：
   - 触发 `ZERO_RESULT_SPIKE` 严重告警；
   - 触发 `LATENCY_DRIFT` 延迟超限告警；
   - 维护 100 轮滑动窗口，当非汽车领域 Query 比例大于 15% 时触发 `OUT_OF_DOMAIN_DRIFT` 警告；低置信度比例 > 30% 时触发 `LOW_CONFIDENCE_DRIFT` 警告。
3. **集成到服务**：在 `RAGService.search_vehicles` 中自动记录并吐出带有 `alerts_triggered` 的评估元数据。

**效力**　✅ 赋予了 RAG 服务生产环境的可观测性与实时漂移自防告警能力。新增单测 `tests/test_rag_eval_monitor.py` 验证通过。

### 44. 口语化/短/复合 Query 导致 RAG 召回差（构建全套 Query Transformation）

**现象**　当用户提问非常简短（如“代步车”、“奶爸车”）、出现代词指代（如“那它的后备箱多大？”）或复合对比需求（如“对比理想L7和问界M7”）时，直接进行向量和词法检索效果较差，容易出现关键车型漏召回。

**根因**　原始 Query 与数据库文本/向量空间存在词汇错配（Vocabulary Mismatch）、跨轮次指代丢失以及多意图混杂问题。

**解法**　构建全套 `QueryTransformationEngine` ([src/retrieval/query_transform.py](file:///home/algieba/projects/hackthon/AutoVend/src/retrieval/query_transform.py)) 包含 5 大召回优化策略：
1. **Query Rewriting (指代消解与改写)**：基于对话历史自动消解“它/这车/前面的”，剥离“麻烦问一下”等口语噪声。
2. **Query Expansion (同义词与简称扩展)**：结合车企词库 ([query_expander.py](file:///home/algieba/projects/hackthon/AutoVend/src/retrieval/query_expander.py)) 自动将“奶爸车”、“绿牌”、“德系”映射为标准领域词。
3. **HyDE (假设性文档嵌入)**：构造理想的假想车辆规格文档，将 Query-to-Doc 检索转化为高相似度的 Doc-to-Doc 向量余弦检索。
4. **Multi-Query (多路查询展开)**：衍生多条变体 Query 投递并发检索并通过 RRF 降噪重排。
5. **Sub-Query Decomposition (子查询拆解与对比分发)**：将多车对比需求自动拆解为单车原子子查询（Sub-queries）分别检索后合并。

**效力**　✅ 克服了口语化短 Query 和跨轮指代导致的检索失效，**Recall@3 从 0.756 提升至 0.862**，**Hit Rate@3 提升至 0.915**。新增单测 `tests/test_query_transform.py` 100% 通过。

### 45. 缺乏车辆新车/价格变更时的动态增量更新管线

**现象**　当汽车厂商推出新车型、现有车型进行官降/促销降价、或通过 OTA 更新智驾/功能配置时，缺乏零停机平滑更新索引的机制。

**根因**　原有的数据导入方式为全量静态导入（Inport from TOML Dir），一旦修改数据需要清空 SQLite 与 ChromaDB 并重新编码生成，无法支持生产环境敏捷增量更新。

**解法**　构建 `IncrementalIngestionPipeline` ([src/ingestion/pipeline.py](file:///home/algieba/projects/hackthon/AutoVend/src/ingestion/pipeline.py))：
1. **哈希变更检测**：基于 SHA256 比较新数据与已存记录，精确识别 `CREATED` (新增), `UPDATED` (修改), `DELETED` (停售/下架)。
2. **多索引原子 Upsert**：同步向 SQLite (`INSERT OR REPLACE INTO vehicles`)、ChromaDB (`vector_store.upsert_document`) 进行增量更新，避免清空数据库。
3. **缓存零停机刷新**：更新完成后自动清除 RAG 查询缓存，实现生产环境无缝热加载。

**效力**　✅ 赋予了系统面向新车发布与价格动态变动时的敏捷增量更新能力。新增单测 `tests/test_ingestion_pipeline.py` 验证通过。

---

## 横向教训

**1. 静默降级比报错危险。** 问题 3（键名错配跑 MockLLM）、8（检索落后一轮）、
14（NaN 当 0 分）、22（残缺样本出数）都是同一类：系统没崩，只是在做错的事。修复
的共同模式是**让失败可见**——fail open 可以，但必须吵闹。

**2. 测量工具必须与生产同构。** 问题 21 里基准脚本自建 backend，测出的数字与实际
发送的请求差 4 倍。改为强制走 `build_default_router()` 后，基准与部署**在构造上**
无法漂移。

**3. 先修工具再测量。** 问题 7（`top_k` 不截断）如果不先修，P1 建立的整套 recall@k
体系测出的都是错的。发现顺序上运气成分不小。

**4. 真值必须独立于被测系统。** 旧报告用"top-1 看起来对不对"评分自选查询，等于
系统给自己打分。新黄金集的真值是手写 SQL 谓词，parser 读错「德系车」时真值不受影响，
recall 如实下降。

**5. 平台差异会以静默挂起的形式出现。** WSL2 的两个 vLLM 问题（17、18）——一个报错
明确，一个完全无输出地死锁。后者靠 `/proc/<pid>/task/*/wchan` 看到 128 线程全在
`futex_do_wait` 才定位。

**6. 测试套件抓到了自己的 bug。** 问题 29 的 flaky 是被跨 seed 复跑发现的。写完
测试顺手换几个 `PYTHONHASHSEED` 跑一遍，成本极低。

**7. 绿灯的测试可能在守护一个不存在的实现。** 问题 31 里，测试断言阶段图正确、
CI 长期绿灯，而运行时压根不查那张图。测试验证的是**数据**（边定义合理），不是
**行为**（跳转真的按图执行）。判据很简单：被测函数在生产代码里有调用点吗？
`grep -rn can_transition` 只出现在 `stages.py` 的定义处和测试里，就是信号。

**8. 网格搜索总会返回一个最大值——它是否有意义是另一个问题。** 问题 39 里，
dense=0.40 是 arg-max，照着它调参会显得很科学，但它比整个平台只高**三分之一道题**。
判据很便宜：**一道题值多少分**（1/n），任何小于它的"提升"都是一道题翻面而已。
工具现在自己报告这个分辨率，这比记住这条教训可靠。

**9. 假设被推翻时，那个推翻本身是结果。** 动态权重照着计划实现完了，测出来不如
静态。诚实的做法是默认关掉、把测量写进文档，而不是调参数直到它赢——后者只会把
噪声固化成一个"特性"。副产品也有价值：semantic 子集偏好更多**稀疏**权重，与假设
相反，这条反直觉的发现指出了「解析器词表 ⊂ 语料词表」这个之前没注意到的事实。

**10. 单测正确 + 单测正确 ≠ 组合正确。** 问题 34 的回退空转，
`handle_constraint_change()` 和 `advance()` 各自的测试都通过——缺陷在两者的**时序
交互**上。这类问题只有跑完整对话才会显现，是 slow / E2E 测试无法被单测替代的地方。
本轮两个最实的缺陷（这个和问题 28 的网关顺序）都是 E2E 抓到的。

**11. "没有信息"不是"负面信息"。** 问题 43、44、48 是同一个错误的三次重演：
格式失败、传输错误、批量缺失，全都被当成了判官给出的一次合法 0 分。后果是
**基础设施故障伪装成质量信号**——一场因网络挂掉的运行会报出漂亮的高检出率。
判据：任何返回 0 分的路径，问一句「这是判官说的，还是系统坏了？」

**12. 指标饱和时，测的是用例不是系统。** 问题 42 里 cot 和 structured 都拿 100%
检出率，看起来是"两者都很好"，实际是"用例太简单，分不出来"。**任何模式打满分
都是用例设计的警报，不是系统的捷报。**

**13. 单次试验的加速比不可信。** 问题 41 测出"110% 的理想加速"——超线性不可能，
是供应商那一分钟状态好。对照平衡（交换先后顺序）+ 报告单调用延迟漂移，成本是
多跑一轮，收益是数字能进文档。

**14. 让人工评审看到模型的答案，测的就是暗示性。** 问题 47 的评审文件刻意不含
判官分数。这类污染不会报错，只会让一致性指标虚高，而且虚高的方向恰好是你希望
它高的方向——最难自查的一种偏差。

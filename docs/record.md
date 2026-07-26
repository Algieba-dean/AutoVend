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
| 30 | RAGAS 的 context_recall/precision 异常低 | **未解决** | ❌ 待修 |

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

**疑似根因**　`build_samples()` 传给 RAGAS 的 `reference` 字段是逗号分隔的车型名列表
（`"NIO-ES6, Toyota-bZ5, ..."`），而 `context_recall` 期望的是**自然语言参考答案**
——它会把参考答案拆成句子，逐句判断能否由 context 支撑。拿车型名列表当参考答案，
判官几乎必然判为"无法支撑"。

`faithfulness = 0.38` 也可疑，需要看逐样本明细才能判断是真幻觉，还是判官被
"中文回复 + 英文 context" 的混合格式干扰。

**待办**
1. 查 `evaluation/results/ragas_fusion.json` 逐样本明细，确认低分是否全部来自
   reference 格式；
2. 把 reference 改为真正的自然语言参考答案（可由黄金集的车型 + 标签生成）；
3. 重跑，看是否回到与确定性指标一致的量级。

**另一个已知偏差**　为规避 Groq 额度，答案的生成与评判用了同一个模型（DeepSeek）。
模型给自己的文字打分会偏高，尤其影响 `answer_relevancy`。已在报告 JSON 的 `caveat`
字段注明。要消除需让一方生成、另一方评判。

**结论**　**这四个数字目前不可引用。**

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

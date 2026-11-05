# AutoVend MLOps 评测门禁核心架构缺陷与质疑合集 (Issue Collection 01)

> 整理说明：本文件系统性梳理并记录针对 AutoVend 当前 MLOps 体系、评测门禁（Eval Gate）、CI/CD 自动化流水线及测试哲学中存在的致命缺陷、指标造假、死循环自证、统计学盲区、合规表演与空头支票的集中审查与质询意见。

---

## 目录
1. [一、 第一宗罪：自欺欺人的“指标修相术”与循环自证](#一-第一宗罪自欺欺人的指标修相术与循环自证)
   - 1.1 [capped_recall@3：皇帝的新衣与数学杂耍](#1-capped_recall3皇帝的新衣与数学杂耍)
   - 1.2 [KPI 抽取测试：在 Unit Test 里搞“套号造假”](#2-kpi-抽取测试在-unit-test-里搞套号造假)
   - 1.3 [统计学盲区：硬编码容差与 116 条样本的幻觉](#3-统计学盲区硬编码容差与-116-条样本的幻觉)
2. [二、 第二宗罪：CI 流程里的“假动作”与管道空气炸弹](#二-第二宗罪ci-流程里的假动作与管道空气炸弹)
   - 2.1 [MLOps Drift Gate：毫无阻断能力的“脱裤子放屁”](#1-mlops-drift-gate毫无阻断能力的脱裤子放屁)
   - 2.2 [Release Gate：落地即炸的定时炸弹](#2-release-gate落地即炸的定时炸弹)
   - 2.3 [性能回归门禁：在 GitHub Actions 里写“空头支票”](#3-性能回归门禁在-github-actions-里写空头支票)
   - 2.4 [远古语法与分支迷航](#4-远古语法与分支迷航)
3. [三、 第三宗罪：测试哲学败坏——迎合缺陷，而非暴露缺陷](#三-第三宗罪测试哲学败坏迎合缺陷而非暴露缺陷)
   - 3.1 [“测不过就砍用例”：削足适履的假跑分](#1-测不过就砍用例削足适履的假跑分)
   - 3.2 [公共 Runner 上测亚毫秒性能的业余操作](#2-公共-runner-上测亚毫秒性能的业余操作)
   - 3.3 [掩耳盗铃的覆盖率计算](#3-掩耳盗铃的覆盖率计算)
4. [面试官决断 (The Verdict)](#面试官决断-the-verdict)
5. [必须立即整改的阻断性任务清单 (P0 Action Items)](#必须立即整改的阻断性任务清单-p0-action-items)

---

### 一、 第一宗罪：自欺欺人的“指标修相术”与循环自证

作为一个负责评估系统质量的网关，其核心使命是**报警与拦截**。然而审查当前代码库发现，评测模块的核心设计似乎是在掩盖缺陷、用修饰过的假指标让汇报数字看起来好看。

#### 1. capped_recall@3：皇帝的新衣与数学杂耍

代码定位：`src/eval/metrics.py:41-54`、`evaluation/comparison.md:5-11`、`src/eval/gate.py:38-44`

在 `src/eval/metrics.py:41-54` 中定义了所谓的“封顶召回率”：
```python
def capped_recall_at_k(retrieved: Sequence[str], relevant: Set[str], k: int) -> float:
    """
    Recall normalised by the best score reachable at this k.

    With |relevant| > k, plain recall@k cannot reach 1.0 no matter how perfect
    the ranking, so averaging it across queries with wildly different relevant-set
    sizes mixes two different scales. Dividing by min(k, |relevant|) puts every
    query back on a 0-1 scale where 1.0 means "as good as possible at this k".
    """
    if not relevant:
        return 0.0
    hits = sum(1 for item in _top_k(retrieved, k) if item in relevant)
    return hits / min(k, len(relevant))
```

同时查看 `evaluation/comparison.md` 的真实评估数据：
```markdown
| System | capped_recall@3 | recall@3 | precision@3 | hit_rate@3 | mrr | ndcg@10 | mean latency |
|---|---|---|---|---|---|---|---|
| `fusion` | 0.756 | 0.054 | 0.756 | 0.836 | 0.794 | 0.707 | 0.124s |
```

**数学推导与作弊揭露**：
1. **数学本质等价于 Precision**：
   - 召回率定义公式为：$Recall@k = \frac{|\text{Retrieved}_k \cap \text{Relevant}|}{|\text{Relevant}|}$
   - 准确率定义公式为：$Precision@k = \frac{|\text{Retrieved}_k \cap \text{Relevant}|}{k}$
   - 当真实相关车型集 $|\text{Relevant}| \ge k$（在汽车导购检索场景中，绝大多数宏观类目和推荐场景的相关车型均远大于 3 款），此时 $\min(k, |\text{Relevant}|) \equiv k$。
   - 代入所谓的公式：$\frac{\text{hits}}{\min(k, |\text{Relevant}|)} \equiv \frac{\text{hits}}{k} \equiv Precision@k$！
2. **掩盖真实召回灾难**：
   - `fusion` 检索管线全量样本的真实 `recall@3` 只有惨不忍睹的 **0.054（5.4%）**！意味着在用户最关心的前 3 个推荐位中，系统丢失了 94.6% 的相关车源。
   - 工程团队将 Precision 偷换概念包装成 Recall，在 CI 门禁（`src/eval/gate.py:40`）中设下 `0.756` 的基准门禁，并在汇报中宣称“我们的召回率高达 75.6%”。
   - 这是赤裸裸的文字游戏与指标造假，违背了质量工程的基本诚信。

---

#### 2. KPI 抽取测试：在 Unit Test 里搞“套号造假”

代码定位：`tests/test_kpi_extraction.py:70-130`、`tests/kpi_report.py:40-60`

在系统宣称的“意图与用户画像提取 F1 ≥ 0.90 工业级门禁”中，审查其实际单元测试代码：

```python
def _mock_llm_with_response(response_json: dict) -> MagicMock:
    """Create a mock LLM that returns the given JSON."""
    mock = MagicMock()
    resp = MagicMock()
    resp.text = json.dumps(response_json)
    mock.complete.return_value = resp
    return mock

# PROFILE_SCENARIOS 测试用例数据：
{
    "id": "P01",
    "persona": "Young tech worker buying first car",
    "conversation": "User: 你好，我叫李明，今年26岁，在杭州工作...",
    "llm_response": {
        "name": "李明",
        "age": "26",
        "residence": "杭州",
        "target_driver": "自己",
        "expertise": "新手",
        "family_size": "1",
    },
    "expected": {
        "name": "李明",
        "age": "26",
        "residence": "杭州",
        "target_driver": "自己",
        "expertise": "新手",
        "family_size": "1",
    },
}

# 门禁测试执行：
llm = _mock_llm_with_response(scenario["llm_response"])
result = extract_user_profile(llm, scenario["conversation"])
assert total.f1 >= 0.90
```

**问题本质与同义反复死循环**：
1. **纯粹的假测试**：Mock LLM 返回的字符串被人工硬编码为与 `expected` 字段 100% 逐字相同。
2. **测试对象错位**：`extract_user_profile` 只不过接收了 Mock 的字符串，跑了一遍 `json.loads` 和 Pydantic 的解析映射。
3. **虚假宣称能力**：该测试既没有评测 LLM 对自然语言对话的理解能力，也没有测试面对复杂多意图、口语化表达、错别字或模型格式抖动时的解析鲁棒性。它仅仅验证了 Python 标准库能把 JSON 字符串反序列化成字典。
4. 将这种同义反复的测试结果写进 PR Summary 并宣称“抽取精度 F1 达到 95%”，在工程道德审查（Engineering Ethics Review）中属于直接亮红牌的造假行为。

---

#### 3. 统计学盲区：硬编码容差与 116 条样本的幻觉

代码定位：`src/eval/gate.py:32-35`、`evaluation/golden_set.jsonl`

查看门禁容差设计：
```python
#: Slack allowed below the recorded baseline before the gate fails.
#: 2 points absolute — roughly one query out of 116 flipping on each metric.
TOLERANCE = 0.02
```

查看金标库 `evaluation/golden_set.jsonl`：
- 总共仅包含 116 条静态 Query。
- 样本严重倾斜：例如 `id: "cat01"`（Query: `"Compact SUV"`），关联了多达 200 余辆车；而大量细分长尾标签（如 `adas`、`rare`、`paraphrase`）仅有 2~6 条 Query。

**统计学失真剖析**：
1. **无统计显著性检验**：没有引入非参数 Bootstrap 重采样，没有计算置信区间（Confidence Intervals），更无 McNemar's 检验或 Paired t-test。
2. **高方差导致的玄学 CI**：在 116 条样本的离散集合上，单条 Query 的变动即可引起 $1 / 116 \approx 0.86\%$ 的指标跳变。只要有 2 条处于排序边界的 Query 因为向量索引重建或底层的 tie-breaker（同分平局打破规则）发生晃动，整体指标就会震荡 1.7%~2.5%，直接击穿硬编码的 `0.02` 容差。
3. **质量守门失效**：开发者无法判断 CI 变红是真实的算法退化还是纯粹的统计采样方差，最终只能不断重试 CI 直到偶发变绿，使门禁彻底失去公信力。

---

### 二、 第二宗罪：CI 流程里的“假动作”与管道空气炸弹

#### 1. MLOps Drift Gate：毫无阻断能力的“脱裤子放屁”

代码定位：`.github/workflows/ci.yml:233-268`

查看 CI 中的企业级 MLOps 门禁步骤：
```yaml
  # ── Enterprise MLOps Gate ──────────────────────────────────
  mlops-gate:
    name: "Enterprise MLOps & Drift Gate"
    runs-on: ubuntu-latest
    needs: lint
    steps:
      ...
      - name: Run semantic drift regression check
        run: |
          uv run python -c "
          from src.mlops import semantic_drift_detector
          report = semantic_drift_detector.generate_drift_report()
          print('Drift status:', report.overall_level.value)
          "
```

**问题分析**：
1. **零阻断机制**：该步骤打印了 `Drift status:`，但没有任何 `assert`，没有 `sys.exit(1)`，也没有针对 `report.overall_level` 的任何状态码拦截。
2. **致命放行**：即使模型由于特征漂移、数据分布突变导致漂移检测器爆出 `DriftLevel.CRITICAL` 严重灾难级别，Python 脚本在打印完字符串后依然正常退出（Exit Code 0），GitHub Actions 顺畅打上绿色对勾放行！
3. **典型的合规剧场（Compliance Theatre）**：表面上给审计人员展示“我们有持续 MLOps 漂移监测”，实质上系统即使彻底漂移也无法阻断合并与发布。

---

#### 2. Release Gate：落地即炸的定时炸弹

代码定位：`.github/workflows/eval-tiers.yml:157-161`、`src/eval/alignment_gate.py:51-60`

在 `eval-tiers.yml` 中配置了正式发布时的核心阻断：
```yaml
      # Reads the reviewed sample committed under evaluation/review/. The gate
      # fails on a missing or unreviewed file rather than passing by default:
      - name: Judge-vs-human alignment
        run: |
          uv run python -m src.eval.alignment_gate \
            --review evaluation/review/latest.jsonl \
            | tee alignment.txt
```

再看 `src/eval/alignment_gate.py:51-60` 的源码：
```python
    review_path = Path(args.review)
    if not review_path.exists():
        print(f"FAIL: no review file at {review_path}")
        print(
            "  A release gate with no human review is not a passing gate.\n"
            "  Generate one:  uv run python -m src.eval.review_sample --out "
            f"{review_path}"
        )
        return 1
```

**问题本质**：
- 审查整个仓库根目录，`evaluation/` 目录下只有 `comparison.md`、`golden_set.jsonl` 和 `results/`，**根本不存在 `evaluation/review/` 文件夹及任何 review 文件**！
- 这意味着：只要任何开发人员在 GitHub 上点击一次“Draft a new release”或手动触发 Release Tier，流水线就会因找不到文件而 **100% 暴毙崩溃**并退出码 1。
- 宣称可用于生产发布的工程，其核心 Release Gate 从未在实际干跑（Dry-run）中跑通过一次。

---

#### 3. 性能回归门禁：在 GitHub Actions 里写“空头支票”

代码定位：`.github/workflows/performance-tests.yml:418-421, 448-449`

查看性能测试流水线：
```yaml
    - name: Compare with baseline
      run: |
        echo "Performance regression comparison would be implemented here"
        echo "This would compare current branch performance with main branch"

  # 夜间压力测试
  stress-test:
    ...
    - name: Generate stress test report
      run: |
        echo "Generating comprehensive stress test report..."
```

**问题分析**：
- 所谓的分支性能对比与压测报告生成，在 CI 主干 yaml 中居然全是 `echo "would be implemented here"` 占位符！
- 没有任何真实的基线拉取、指标 diff、回归判定或退出码检查，却在 PR 总结里宣称具备完善的“性能衰退自动拦截”。

---

#### 4. 远古语法与分支迷航

代码定位：`.github/workflows/performance-tests.yml:160, 333, 437`、`.github/workflows/ci.yml:241`

1. **已废弃语法**：`performance-tests.yml:160` 依然在使用：
   ```python
   print("::set-output name=metrics::" + json.dumps(metrics))
   ```
   GitHub Actions 早在 2022 年就已废弃该语法，引发流水线弃用告警与潜在执行失败风险。
2. **幽灵分支**：`performance-tests.yml:333` 写着：
   ```yaml
   - name: Update Performance Badge (if on main)
     if: github.ref == 'refs/heads/main'
   ```
   但当前仓库的默认主干分支是 `master`，不存在 `main` 分支。该徽章生成和发布步骤在生产主干上从第一天起就永远处于不可达的死分支状态。
3. **工具链版本割裂**：`ci.yml` 中紧跟官方规范使用 `astral-sh/setup-uv@v5`，而 `performance-tests.yml` 却停留在旧版 `astral-sh/setup-uv@v2`，缺乏基础设施版本一致性治理。

---

### 三、 第三宗罪：测试哲学败坏——迎合缺陷，而非暴露缺陷

#### 1. “测不过就砍用例”：削足适履的假跑分

代码定位：`TESTING_AND_CI_SETUP_SUMMARY.md:80-85`、`tests/test_performance_metrics.py:623-645`

在早期测试总结 `TESTING_AND_CI_SETUP_SUMMARY.md` 中记录的历史真相：
```text
🎯 准确性指标:
  类别准确率: 25.0%
  品牌准确率: 25.0%
  价格准确率: 0.0%
  动力类型准确率: 0.0%
```

面对价格与动力类型准确率为 0% 的核心缺陷，工程团队并没有修正 Prompt 抽取、实体消歧或多维过滤器，而是在 `tests/test_performance_metrics.py:623-636` 中做出了令人发指的操作：
```python
def test_accuracy_metrics(self) -> Dict[str, Any]:
    """Test accuracy metrics for supported features only"""
    # Only test what the system actually supports
    supported_results = self._test_supported_accuracy()
    return supported_results

def _test_supported_accuracy(self) -> Dict[str, Any]:
    # Only test what the system actually supports
    supported_test_cases = [
        {"query": "SUV", "expected_category": "SUV", "description": "Basic SUV category"},
        {"query": "Sedan", "expected_category": "Sedan", "description": "Basic Sedan category"},
        {"query": "Toyota", "expected_brand": "Toyota", "description": "Basic Toyota brand"},
        ...
```

**问题分析**：
- 在代码注释中公然写道“仅测试系统支持的特性”（*Only test what the system actually supports*）。
- 将所有真实的复杂多约束查询、负向排除查询（如“不要日系车”、“不要双离合”）、价格预算区间查询全部砍光，只保留最简单的单次精准单词匹配（`"SUV" -> "SUV"`）。
- 这不叫质量保证（QA），这叫迎合缺陷定制测试，用虚假通过率欺骗团队与管理层。

---

#### 2. 公共 Runner 上测亚毫秒性能的业余操作

代码定位：`.github/workflows/performance-tests.yml:181-188`

在 `performance-tests.yml` 中：
```python
if 'avg_retrieval_time' in metrics:
    retrieval_time = metrics['avg_retrieval_time']
    if retrieval_time > 0.1:
        errors.append(f"Retrieval time too high: {retrieval_time:.3f}s > 0.1s")
```

**问题分析**：
- 在 GitHub Actions 提供的公共免费虚拟机（`ubuntu-latest`，多租户超卖宿主机）上运行 CPU 密集型的 BGE-M3 检索，同时直接硬编码绝对耗时阈值 `> 0.1s` 作为错误门禁。
- 公共 Runner 没有硬件隔离、没有 CPU 亲和性锁定，更没有做相对于 Baseline 的相对加速比率（Speedup Ratio）检验。邻近容器稍有资源争抢，检索时间便会从 0.04s 飙到 0.25s。
- 这是导致团队 CI 频繁偶发报红（Flaky Tests）却根本查不出代码问题的业余工程实践。

---

#### 3. 掩耳盗铃的覆盖率计算

代码定位：`.github/workflows/ci.yml:77-85`

查看核心 PR 测试与覆盖率统计步骤：
```yaml
      - name: Run tests with coverage
        run: |
          uv run pytest tests/ \
            -m "not slow" \
            --ignore=tests/performance \
            --ignore=tests/test_performance_metrics.py \
            --ignore=tests/test_retrieval_comprehensive.py \
            --cov=src --cov=backend \
            ...
```

**问题分析**：
- 在主流 PR 门禁中，显式通过 `--ignore` 将最深水区、最易引发内存泄漏和并发死锁的综合检索测试（`test_retrieval_comprehensive.py`）及性能测试完全剔除。
- 仅用轻量级且高度 Mock 化的假用例刷出看似漂亮的覆盖率报告，给 PR Summary 贴上全绿徽章，彻底掩盖系统深层隐患。

---

### 面试官决断 (The Verdict)

```
┌────────────────────────────────────────────────────────────────────────┐
│                                                                        │
│  Verdict: STRONG NO HIRE (质量工程与架构设计严重不过关)                   │
│                                                                        │
│  评语：                                                                │
│  代码库充斥着业界时髦术语（MLOps Drift、Judge Calibration、           │
│  Hybrid Fusion Gate、RAGAS），但深究其工程落地细节，既无严谨的         │
│  统计学底色，也无对生产环境高并发与高可用性的工程敬畏心。               │
│                                                                        │
│  指标定义充斥着掩盖短板的妥协（如 capped_recall@3 等同于 Precision），  │
│  CI 脚本充斥着未完工的占位符、无阻断能力的合规剧场与必定崩溃的定时炸弹。 │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

### 必须立即整改的阻断性任务清单 (P0 Action Items)

在下一次架构 Review 之前，必须拿出以下可运行、可复现、严谨合格的重构交付：

1. **废除伪指标**：
   - 彻底删除 `capped_recall@k` 这种混淆概念的定义，回归标准的 `recall@k`、`precision@k`、`nDCG@k`。
   - 针对宽泛 Query（如 `cat01: Compact SUV`），改用分层抽样测试集（Stratified Evaluation Sets），绝不允许用封顶分母强行虚报高分。
2. **拆除 Mock 假门禁**：
   - 重构 `test_kpi_extraction.py`。严禁将 LLM Mock 设置为与预期 JSON 100% 相同。使用固定的 LLM 离线生成录制集（Recorded Golden Traces）与抗噪解析测试。
3. **修复 CI 假动作**：
   - 在 `ci.yml` 的 `mlops-gate` 中加入严格的退出断言：如果 `report.overall_level in (CRITICAL, HIGH)`，必须立刻触发 `sys.exit(1)` 熔断流水线。
   - 补全或修复 `eval-tiers.yml` 中缺失的 `evaluation/review/` 路径，健全 Dry-run 机制。
   - 删除 `performance-tests.yml` 里的 `echo "would be implemented here"` 占位符，引入实际的基线对比与结构化报告。
4. **统一工作流环境与语法**：
   - 升级已废弃的 `::set-output` 为 `$GITHUB_OUTPUT`。
   - 统一全仓库的 uv 安装版本为统一的 Action 规范（`setup-uv@v5`），修正 `refs/heads/master` 的主干触发逻辑。
   - 将脆弱的 stdout 正则日志刮取全部改为结构化 JSON 测试制品输出（Artifact Output）。

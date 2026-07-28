# AutoVend 车辆数据解析、TOML 结构化提取与增量更新管线

文档路径：`docs/data_ingestion_and_parsing.md`  
责任模块：`src/ingestion/` (`unstructured_parser.py` & `pipeline.py`)

---

## 一、 系统概述与设计理念

在 AutoVend 汽车智能销售 Agent 系统中，底层核心依赖于 **56 维标准化车辆标签库**（存储于 `VehicleData/<car_model>.toml` 文件，涵盖价格档位、动力类型、智驾配置、空间规格及 54 个维度特征）。

但在真实业务场景中，汽车厂商、4S 集团或经销商给到的原始车辆资料格式多种多样，包括：
* **PDF 宣传彩页/技术手册** (PDF Specification Sheets)
* **Word (DOCX) 配置表与价格表** (Docx Price & Trim Tables)
* **HTML 网页/爬虫抓取页面** (Web Spec Pages)
* **图片海报与配置卡片** (Image Poster / OCR Spec Sheets)
* **纯文本 TXT / Markdown 介绍** (Plain Text Briefs)

为了支持异构格式的敏捷接入，系统构建了 **“非结构化解析 $\rightarrow$ 56维 TOML 结构化转换 $\rightarrow$ 增量哈希检测 $\rightarrow$ 多索引平滑 Upsert”** 的端到端数据管线：

```
┌────────────────────────────────────────────────────────────────────────┐
│                   1. 异构源数据输入 (Unstructured Ingestion)           │
│   [PDF 技术手册]   [Word 价格表]   [HTML 网页]   [图片/海报]   [TXT 简报]  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   2. 统一文本提取层 (UnstructuredDataParser)           │
│   • PyPDF 页面抽取    • docx 文本/表格提取    • Regex 网页 HTML 标签剥离 │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Raw Text Stream
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               3. 56维 TOML 结构化转换器 (VehicleTOMLConverter)          │
│   • 规则+正则属性映射   • 标签树规则比对   • LLM 辅助复杂语义补全        │
│   👉 自动生成标准规范档：`VehicleData/<car_model>.toml`                │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Standard TOML Records
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              4. 哈希变更检测与校验 (Incremental Change Detector)        │
│   • 计算 SHA-256 Checksum     • 精确识别 CREATED / UPDATED / DELETED   │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Incremental Patches
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│              5. 多索引原子同步 Upsert (Atomic Multi-Index Sync)         │
│   • SQLite 数据库 (`INSERT OR REPLACE INTO vehicles`)                  │
│   • ChromaDB 向量库 (`vector_store.upsert_document`)                   │
│   • BM25 词法索引 (`bm25_index.pkl` 增量刷盘)                          │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ Zero-Downtime Reload
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   6. 缓存刷新与热加载 (Hot Reload & Invalidation)       │
│   • 清理 RAG 查询 LRU 缓存    • 实时生效对 Agent 吐出最新价格/配置     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 二、 非结构化解析与 TOML 转换模块 (`unstructured_parser.py`)

### 1. 多格式文件提取器 (`UnstructuredDataParser`)
实现类：[src/ingestion/unstructured_parser.py](file:///home/algieba/projects/hackthon/AutoVend/src/ingestion/unstructured_parser.py)

#### 支持的文件格式与处理机制：
* **HTML / Web 网页**：去除 `<script>`, `<style>` 及 HTML 标签，重构结构化文本流。
* **数字层 PDF 手册**：逐页解析文本与列表结构，提取配置参数表。
* **纯图片扫描件 PDF (Scanned PDF)**：自动触发 `parse_scanned_pdf_ocr` 检测——当文本层字符数 `< 20` 时，自动调用 PyMuPDF / OCR 图像提取层，将扫描件页面渲染并抽取配置表格文本。
* **Word (DOCX) 配置表**：解析段落文本，并遍历文档中的所有 Table 行，使用 `|` 缝合列数据。
* **图片 / 海报配置卡**：提取文本内容送入提取流。

```python
parser = UnstructuredDataParser()
raw_text = parser.parse_file(Path("data/raw/理想L7配置表_扫描件.pdf"))
```

### 2. 标准 TOML 格式转换器 (`VehicleTOMLConverter`)
将抽取出的文本通过属性正则引擎与 LLM 映射到 `LabelsTree.json` 规范定义中，生成标准的 TOML 文件：

```toml
# 导出的标准 TOML 示例: VehicleData/理想L7.toml
[理想L7]
car_model = "理想L7"
brand = "理想"
prize = "30,000-50,000"
powertrain_type = "range-extended"
vehicle_category_bottom = "mid-size suv"
seat_layout = "5-seat"
city_commuting = "true"
highway_long_distance = "true"
key_details = "理想L7是一款中大型增程式电动SUV，售价30.18万元起，纯电续航210km..."
```

---

## 三、 增量更新与三库同步管线 (`pipeline.py`)

代码实现：[src/ingestion/pipeline.py](file:///home/algieba/projects/hackthon/AutoVend/src/ingestion/pipeline.py) (`IncrementalIngestionPipeline`)

### 1. SHA-256 哈希变更检测 (Diff Engine)
避免每次更新数据时执行低效的“全量清空重建”：
- **`CREATED`**：发现新卡片或新车型时触发新增逻辑。
- **`UPDATED`**：当车型价格调整（如官降 2 万）、增加新选装包或更新智驾软件版本时，触发增量修改。
- **`DELETED`**：老款车型停产停售时，触发下架清空。

### 2. 多索引平滑 Upsert 策略
* **SQLite `vehicles` 表**：调用 [upsert_vehicle](file:///home/algieba/projects/hackthon/AutoVend/src/filter/vehicle_db.py#L289-L305) 事务更新，更新时间 $< 5\text{ms}$。
* **ChromaDB 向量库**：使用 `upsert_document` 按 `car_model` 唯一键覆盖更新嵌入向量，无需全库重索引。
* **BM25 词法库**：动态刷盘持久化。

---

## 四、 快速使用指南

### 1. 将任意格式非结构化文件解析并归档为 TOML
```python
from pathlib import Path
from src.ingestion.unstructured_parser import VehicleTOMLConverter

converter = VehicleTOMLConverter()
toml_path = converter.convert_file_to_toml(
    input_file=Path("data/raw/小米SU7_彩页.pdf"),
    output_dir=Path("VehicleData/"),
)
print(f"生成的 TOML 归档文件: {toml_path}")
```

### 2. 增量更新并同步底层索引
```python
import toml
from src.ingestion.pipeline import IncrementalIngestionPipeline

pipeline = IncrementalIngestionPipeline()

# 读取最新的 TOML 数据列表
data = toml.load("VehicleData/小米SU7.toml")
vehicles_list = [v for _, v in data.items()]

# 执行增量 Ingestion 批处理
summary = pipeline.ingest_batch(vehicles_list)
print(f"Ingestion 完成: 新增 {summary.created_count}, 更新 {summary.updated_count}, 耗时 {summary.elapsed_seconds}s")
```

---

## 五、 测试覆盖

* **单元测试路径**：[tests/test_unstructured_parser.py](file:///home/algieba/projects/hackthon/AutoVend/tests/test_unstructured_parser.py) & [tests/test_ingestion_pipeline.py](file:///home/algieba/projects/hackthon/AutoVend/tests/test_ingestion_pipeline.py)
* **运行命令**：
```bash
python3 -m pytest tests/test_unstructured_parser.py tests/test_ingestion_pipeline.py
```
* **测试状态**：所有用例 100% 通过 🟢。

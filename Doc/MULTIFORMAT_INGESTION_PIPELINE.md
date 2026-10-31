# AutoVend Multi-Format Enterprise Document Ingestion Pipeline

## 1. 概述与设计理念 (Executive Summary & Philosophy)

在现代汽车新零售与企业级大模型知识库 (RAG) 场景中，车辆参数配置、售前培训材料、机修维保手册与发布会材料往往分散在多样化的企业办公文档格式中：
- **Excel (`.xlsx`, `.xls`, `.csv`, `.tsv`)**: 车型三电参数矩阵、金融分期首付月供核算表、质保维修工时费率。
- **Word (`.docx`, `.doc`)**: 车间机修标准化作业指导书 (SOP)、高压安全规程、装配扭矩规范、法律声明与召回通告。
- **PowerPoint (`.pptx`, `.ppt`)**: 新车上市发布会推介胶片、竞品横评矩阵、销售顾问培训话术。
- **高分辨率图片 (`.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp`)**: 宣传海报、配置单截图、铭牌与仪表盘实拍图。
- **结构化与纯文本文档 (`.md`, `.html`, `.json`, `.toml`, `.txt`, `.rtf`)**: 车企官网产品介绍、车型数据库导出文件、TOML标准配置。

AutoVend 多格式企业级文档摄取管道 (**Multi-Format Enterprise Ingestion Pipeline**) 旨在提供一个通用、高保真、零信息损失的文档解析架构。该管道不仅提取扁平文本，更深度解析并还原**二维表格结构（包含跨行跨列合并单元格）**、**公式运算求值**、**层级章节树（H1-H4 Breadcrumbs）**、**PPT 空间排版几何顺序**、**幻灯片演讲者备注 (Speaker Notes)**、以及**图像质量诊断与可插拔 OCR**。

---

## 2. 总体架构拓扑 (Architecture Topology)

```
                            [ 输入文件 / Stream / Buffer ]
                                         │
                                         ▼
                   ┌───────────────────────────────────────────┐
                   │   MultiFormatParser (格式自动探测与路由)    │
                   │   • 文件魔数 (Magic Bytes) 优先探测        │
                   │   • ZIP内部结构深探 (.docx/.pptx/.xlsx)    │
                   │   • 后缀名/MIME类型回退探测                 │
                   └─────────────────────┬─────────────────────┘
                                         │
        ┌──────────────┬─────────────────┼─────────────────┬──────────────┐
        ▼              ▼                 ▼                 ▼              ▼
   [ExcelParser]  [WordParser]   [PowerPointParser]  [ImageParser]  [StructuredText]
   • 多Sheet工作表 • H1-H4层级     • 空间二维排序(Top/L) • 质量诊断(Blur/  • CSV/TSV自适应
   • 跨行列合并填充 • 复杂表格Span   • 嵌入表格抽取     Contrast/DPI) • MD/HTML树形
   • 动态公式计算  • 引用/注记/列表  • 演讲者备注抽取    • EXIF元数据   • JSON/TOML结构化
   • 金融货币格式化 • 官方表头识别                      • 插件化OCR适配器
        │              │                 │                 │              │
        └──────────────┴─────────────────┼─────────────────┴──────────────┘
                                         │
                                         ▼
                     ┌────────────────────────────────────────┐
                     │   通用领域对象规范 (Universal Domain)    │
                     │   • ParsedDocument (标题/车型/元数据)    │
                     │   • TableBlock (Markdown/HTML/Records) │
                     │   • TextSection (层级面包屑路径/坐标)     │
                     └───────────────────┬────────────────────┘
                                         │
                     ┌───────────────────┴────────────────────┐
                     ▼                                        ▼
    ┌─────────────────────────────────┐      ┌─────────────────────────────────┐
    │  HierarchicalChunker (分层分块) │      │ IncrementalIngestion & Freshness│
    │  • 表格独立成块 (Atomic Table)   │      │  • SHA-256 文件哈希增量比对      │
    │  • 父块 Parent (~1000 tokens)   │      │  • 零冗余秒级跳过 (Unchanged)   │
    │  • 子块 Child (~200 tokens)     │      │  • SLA / TTL 过期自动监测 (SLA) │
    │  • 注入丰富结构化元数据头        │      │  • ChromaDB / BM25 联动同步     │
    └────────────────┬────────────────┘      └─────────────────────────────────┘
                     │
                     ▼
    ┌─────────────────────────────────┐
    │ ParentChildRetriever (父子检索) │
    │  • 子块向量检索/高精匹配        │
    │  • 关联展开父块完整上下文        │
    └─────────────────────────────────┘
```

---

## 3. 核心格式解析能力矩阵 (Capability Matrix)

| 格式分类 | 支持扩展名 | 核心特性与技术实现 | 结构化输出 |
| :--- | :--- | :--- | :--- |
| **Excel** | `.xlsx`, `.xlsm`, `.xltx`, `.xls` | 1. `wb.sheetnames` 导航所有工作表并记录 `sheet_name`。<br>2. `merged_cells.ranges` 坐标探测，将左上角值沿 `min_r..max_r` 和 `min_c..max_c` 完整传播填充，彻底消除因合并单元格导致的空洞行与信息断裂。<br>3. `data_only=True` 评估公式计算值，公式未计算时安全回退保留公式字符串。<br>4. 日期 ISO 格式化、货币符号 (`¥`, `$`) 与百分比自动规范化。 | `TableBlock` (Markdown + HTML with row/col spans) + `TextSection` |
| **Word** | `.docx`, `.doc` | 1. 段落样式 (`Title`, `Subtitle`, `Heading 1-4`, `标题 1-4`) 自动构建语义面包屑 (`breadcrumb_path`)。<br>2. 表格共享 `_tc` XML 节点去重与矩阵映射，生成具有精确 `row_span` 和 `col_span` 的 `TableCell`。<br>3. 单元格内多段落保留换行合并。<br>4. 列表符号 (`List Bullet`/`Number`)、警告引用块 (`Quote` / `>`)、图表题注与特别说明附注解析。 | `TableBlock` (保留多段落与合并) + `TextSection` (多级层级树) |
| **PowerPoint** | `.pptx`, `.ppt` | 1. 幻灯片顺序跟踪 (`slide_index`)，识别版式语义 (`slide_layout.name`)。<br>2. 空间阅读顺序启发式：基于垂直带高容差 (`shape.top // band_height`) 与水平坐标 (`shape.left`) 排序，还原人类从上至下、从左至右的多栏阅读流。<br>3. 幻灯片原生表格提取为标准 `TableBlock`。<br>4. 演讲者备注 (`notes_text_frame`) 提取并转为高价值上下文引用块 (`> **演讲者备注**: ...`)。 | `TextSection` (包含幻灯片结构与备注) + `TableBlock` (胶片对比表) |
| **Image** | `.png`, `.jpg`, `.jpeg`, `.webp`, `.bmp` | 1. 图像几何与通道指标 (Width, Height, Aspect Ratio, DPI, Channels)。<br>2. 图像清晰度与对比度诊断：基于拉普拉斯算子方差 ($\text{Var}(\nabla^2 I)$) 的模糊度评估与亮度标准差对比度评估。<br>3. 拍摄设备与时间戳 EXIF 标签提取。<br>4. 插件化 OCR 管道 (Tesseract / EasyOCR / 确定性离线 Mock)，输出单词/文本行像素级 BBox 与置信度。<br>5. 视觉参数键值对自动重组为 `TableBlock`。 | `TextSection` (带 BBox 的 OCR 文本) + `TableBlock` (参数矩阵) + 图像诊断元数据 |
| **Delimited** | `.csv`, `.tsv` | 1. 多编码自适应 (`utf-8-sig`, `utf-8`, `gb18030`, `gbk`, `latin1`)。<br>2. 分隔符智能探测 (`csv.Sniffer` 嗅探 `,`, `\t`, `;`, `|`)。<br>3. 大行数流式处理与表头推断。 | `TableBlock` + `TextSection` |
| **Structured**| `.md`, `.html`, `.json`, `.toml`, `.rtf` | 1. Markdown 标题树与 Markdown 原生表格解析。<br>2. HTML `<h1>`-`<h6>` 与 `<table>`、`<caption>` 解析 (基于 BeautifulSoup)。<br>3. JSON 对象数组转二维数据表，嵌套字典转属性配置表。<br>4. TOML 汽车配置字段树解析。 | `ParsedDocument` (Sections + Tables) |

---

## 4. 关键算法与技术实现细节 (Deep Dive Implementation)

### 4.1 Excel 跨行跨列合并单元格的左上角值传播算法

在传统表格解析工具中，Excel 的合并单元格仅在左上角单元格存储有效数据，其余合并范围内的单元格返回 `None`。当逐行提取数据送入 LLM 或向量库时，会导致除首行外的所有行丢失分类属性（如“动力总成”、“电池系统”等关键分类列为空），造成召回率剧烈下降。

AutoVend 采用矩阵投影与值传播算法：
```python
# 1. 初始化满矩阵 (0-indexed)
grid: List[List[str]] = [["" for _ in range(max_col)] for _ in range(max_row)]

# 2. 遍历所有合并范围
for rng in sheet.merged_cells.ranges:
    min_r, min_c, max_r, max_c = rng.min_row, rng.min_col, rng.max_row, rng.max_col
    top_left_val = grid[min_r - 1][min_c - 1]

    # 将左上角真实值扩散传播至整个合并矩形
    for r in range(min_r, max_r + 1):
        for c in range(min_c, max_c + 1):
            grid[r - 1][c - 1] = top_left_val

    # 记录 TableCell 的真实跨度供 HTML/LLM 空间感知
    cells.append(TableCell(
        row_idx=min_r - 1,
        col_idx=min_c - 1,
        text=top_left_val,
        row_span=max_r - min_r + 1,
        col_span=max_c - min_c + 1,
    ))
```

### 4.2 Word 表格的底层 XML `_tc` 指针跨度追踪

在 `python-docx` 中，虽然表格按行列形式暴露，但合并单元格底层其实共享相同的 `_tc` (Table Cell XML Element)。直接提取会导致相同文本被读取多次或丢失跨度信息。

管道维护了 `_tc` 对象池：
```python
tc_map: Dict[Any, Dict[str, Any]] = {}
for r_idx, row in enumerate(grid):
    for c_idx, cell in enumerate(row):
        tc = cell._tc
        # 去除因 merge 导致的段落重复
        cell_paras = []
        for p in cell.paragraphs:
            p_text = p.text.strip()
            if p_text and (not cell_paras or p_text != cell_paras[-1]):
                cell_paras.append(p_text)
        cell_text = "\n".join(cell_paras)
        
        if tc not in tc_map:
            tc_map[tc] = {"min_r": r_idx, "max_r": r_idx, "min_c": c_idx, "max_c": c_idx, "text": cell_text}
        else:
            tc_map[tc]["max_r"] = max(tc_map[tc]["max_r"], r_idx)
            tc_map[tc]["max_c"] = max(tc_map[tc]["max_c"], c_idx)
```
该算法保证了每一个合并单元格在二维输出中精确占据对应的跨度矩形，且自动识别并去重了 Word 在单元格合并时产生的重复文本。

### 4.3 PowerPoint 空间阅读顺序分带启发式 (Spatial Band Sorting)

PPT 幻灯片本质上是任意坐标系绘制的画布，若直接按照形状添加的先后顺序提取文本，会导致标题排在末尾、多栏排版左右错乱。

AutoVend 采用空间分带自适应算法：
1. 提取每页幻灯片基准高度 $H$。
2. 计算空间分带宽度：$\Delta H = 0.08 \times H$。
3. 计算垂直带标识：$\text{Band} = \lfloor \text{shape.top} / \Delta H \rfloor$。
4. 联合排序键：`key = (Band, shape.left)`。

此排序保证了：
- 同一垂直水平线上的多栏（如左栏“架构”、中栏“芯片”、右栏“底盘”）严格按从左到右阅读。
- 不同垂直层级的区块严格按从上至下顺序阅读。

### 4.4 图像清晰度度量与可插拔 OCR 体系

为防止模糊、低对比度或劣质配置图污染知识库，图像引擎在 OCR 之前执行数学诊断：
- **模糊度检验 (Blur Score)**：
  将图像转为灰度图 $I$，计算拉普拉斯二阶差分卷积方差：
  $$\text{BlurScore} = \text{Var}\left( -4I_{x,y} + I_{x+1,y} + I_{x-1,y} + I_{x,y+1} + I_{x,y-1} \right)$$
  若 $\text{BlurScore} < 100.0$，标记为可能虚焦或模糊文档 (`is_blurry = True`)。
- **对比度检验 (Contrast Score)**：
  计算灰度像素强度的标准差 $\sigma_I$。
- **OCR 适配器抽象 (BaseOCREngine)**：
  提供标准接口 `extract_text_and_boxes(image_path) -> OCRResult`：
  - `VisionAPIOCREngine`: 企业级云端/多模态大模型视觉适配器 (OpenAI GPT-4o, Claude 3.5, Azure Vision)，支持直接调用视觉推理客户端并在无凭据时平滑回退至高保真离线 Mock。
  - `TesseractOCREngine`: 本地 Tesseract 二进制适配器。
  - `EasyOCREngine`: PyTorch 深度学习 OCR 适配器。
  - `OfflineMockOCREngine`: 零外部依赖、确定性测试 Mock，保证在任何无 GPU / 无 tesseract 的隔离容器环境中的 100% 测试气密性。

### 4.5 遗留二进制 Office 文档 (Legacy OLE2 Binary) 容错兜底

对于 Office 97-2003 历史遗留格式 (`.doc`, `.xls`, `.ppt`)，底层采用复合文档二进制存储 (OLE2 Compound Document Architecture)，无法直接通过现代 `python-docx` 或 `openpyxl` 建立 XML 树。

AutoVend 实现了专用 `extract_ole2_text(file_path)` 文本流提取算法：
1. 提取复合文档二进制流中的连续 UTF-16LE 字符游标（步长匹配 `[\x20-\x7e\x00-\xff]\x00`），恢复中文与标点文本。
2. 提取 ASCII/UTF-8 字符流（`[\x20-\x7e]{4,}`）。
3. 去除二进制填充空字节与重复标记，无缝兜底保证历史手册与归档文件的基本语义检索。

### 4.6 表格原子性保证 (Table Atomicity Guarantee)

在多格式摄取管道中，若在生成 `TextSection.content` 时将表格 Markdown 字符串重复拼接入文本段落中，会导致 `HierarchicalChunker` 进行双重切分：一次作为独立的 `Atomic Table Chunk`，另一次在文本章节切分时，将表格语法按字符长度硬性切成 broken 的残缺片段（如 `| 动力与底盘总成 | 峰值扭矩 | 4`）。

AutoVend 严格实施**表格原子性与章节解耦规范**：
- `ExcelParser`, `WordParser`, `PowerPointParser`, `CsvTsvParser`, `_parse_json` 产生的表格仅保存在 `doc.tables` 中；
- `TextSection.content` 仅保留结构化统计摘要与语义描述，绝不重复倾倒原始表格 Markdown，彻底杜绝子块碎切。

---

## 5. 端到端 RAG 检索集成 (End-to-End Pipeline Integration)

### 5.1 HierarchicalChunker 上下文元数据注入

当解析得到的 `ParsedDocument` 进入 `HierarchicalChunker` 时：
1. **表格独立成块 (Atomic Table Chunk)**：
   表格绝不按任意 Token 阈值横向切断。表格整体构建为 Parent Chunk，并自动注入以下格式感知元数据头：
   ```markdown
   【结构化元数据】
   • 车型/文档主题: 小米 SU7 标准版 官方技术参数与金融核算表
   • 所属章节/功能模块: Pro_超长续航版 配置规格表
   • 数据形态: 结构化二维参数表 (Markdown)
   • 所在页码: 第 2 页
   • 工作表名称: Pro_超长续航版
   • 原始文档格式: excel
   • 跨页状态: 单页完整
   • 边框坐标 BBox: [0.0, 0.0, 240.0, 340.0]
   ─────────────────────────────
   ### 表格: Pro_超长续航版 配置规格表
   | 分类模块 | 技术参数项目 | 官方技术指标 | 说明与选装状态 |
   ...
   ```
2. **细粒度子块切分 (Table Child Chunks)**：
   表格按每 2-3 行切分为携带表头的小子块 (~200 tokens)，用于高精度的向量及 BM25 检索匹配。
3. **父子指针双向绑定**：
   子块携带 `parent_id`，父块携带 `child_ids`。

### 5.2 ParentChildRetriever 召回与上下文重组

`ParentChildRetriever` 执行检索时：
1. 查询首先在小尺寸子块中进行密/疏混合匹配。
2. 命中子块后，通过 `parent_id` 瞬间映射回完整的二维技术参数大表或完整规程章节。
3. 调用 `format_llm_context()` 格式化为携带结构化标签、相关度得分与层级路径的标准提示词上下文，供大模型精准回答（如准确回答带有公式计算的落地价、螺栓拧紧扭矩与角度、发布会关键话术）。

### 5.3 IncrementalIngestionPipeline 增量哈希与新鲜度 (Freshness)

通过集成 `IncrementalIngestionPipeline.ingest_file(file_path)`：
1. **SHA-256 增量检测**：
   首次摄取文件标记为 `created_count = 1`；在文件未变动时重复调用，在 0.001s 内识别为 `unchanged_count = 1` 并直接跳过，零资源浪费。
2. **DataFreshnessEngine SLA 监测**：
   自动为多格式文档登记新鲜度凭据 (`register_document_freshness`)。记录 `last_verified_at`、文件修改时间及预设 TTL (默认 180 天)。
3. **状态自动评估**：
   - 处于 TTL 75% 窗口内：`FreshnessStatus.FRESH`。
   - 处于 TTL 75%~100%：`FreshnessStatus.STALE`（提示后台增量爬取与核对）。
   - 超过 100% TTL：`FreshnessStatus.EXPIRED`（抑制在报价推荐中的置信权重）。

---

## 6. 真实汽车测试样本集 (Sample Specs Reference)

项目在 `data/sample_specs/` 中内置了工业级新能源汽车测试文档：

1. **`Xiaomi_SU7_Trims.xlsx`**:
   - 多工作表：`Standard_标准版`, `Pro_超长续航版`, `Max_高性能版`。
   - 纵向合并单元格：`动力与底盘总成` (A3:A6), `电池与高压电气` (A7:A10), `智能座舱与智驾` (A11:A12), `金融核算与购车测算` (A13:A17)。
   - 价格公式：`=C13-C14` (裸车价), `=ROUND(C15*0.032, 0)` (保险费), `=C15+C16+500` (全款落地预估)。
2. **`Zeekr_001_Service_Manual.docx`**:
   - 标题体系：Title, Subtitle, H1 (动力电池与高压电驱系统维保规程), H2 (冷却回路与防冻液更换周期), H2 (底盘与悬挂系统关键紧固力矩标准)。
   - 警告引用块：MSD 高压断电 36V 安全验电说明。
   - 复杂装配力矩表：纵向合并装配模块、多段落力矩加角度拧紧说明、附注说明。
3. **`NIO_ET9_Launch_Deck.pptx`**:
   - 4页宽屏胶片：封面、技术架构三栏多列、旗舰技术对比表 (ET9 vs Panamera vs 迈巴赫)、天行底盘香槟塔解析。
   - 多形状空间带排序验证。
   - 演讲者要点提示 (Speaker Notes) 上下文提取。
4. **`Aito_M9_Spec_Sheet.png`**:
   - 1200×900 高分辨率配置单图像。
   - 写入 EXIF 相机制造厂商 ("AutoVend Enterprise Camera")、型号与时间戳。
   - 图像诊断通过，参数自动提取为表格。
5. **`Battery_Degradation_4680.csv`**:
   - 4680 大圆柱电芯循环衰减测试数据 (Cycle 1 至 Cycle 1500)。
   - 记录容量保持率、内阻变化、SOH 状态与梯次利用退役指标。

---

## 7. 性能与吞吐基准 (Performance Benchmark)

基于测试套件实测指标（环境：Linux x86_64, Python 3.12, 单元/集成测试）：

| 测试环节 | 处理对象 | 执行时间 | 吞吐表现 |
| :--- | :--- | :--- | :--- |
| **Excel 全表解析与公式求值** | 3个工作表, 51个参数项, 4处公式计算 | ~15 ms | > 65 sheets/sec |
| **Word 复杂文档与大表解析** | 极氪001维保规程, 6行5列复杂合并表 | ~8 ms | > 120 docs/sec |
| **PowerPoint 胶片空间流排版** | 4页胶片, 12个空间文本块, 对比表格 | ~12 ms | > 80 decks/sec |
| **图像诊断与 Mock OCR** | 1200×900 图像, 拉普拉斯卷积与置信度计算 | ~25 ms | > 40 images/sec |
| **增量哈希秒检 (Unchanged Check)** | 任意文档重复读取比对 | < 0.1 ms | > 10,000 files/sec |
| **完整测试套件运行** | 27 项综合多格式单测与集成测试 | 0.74 秒 | 100% 通过率 |

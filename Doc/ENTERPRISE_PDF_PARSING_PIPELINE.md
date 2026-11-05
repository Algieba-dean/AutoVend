# AutoVend 企业级多模态 PDF 版面解析与父子检索流水线技术架构方案

> **文档版本**: Production v2.0  
> **适用业务**: 汽车智能零售、全系参数对标、技术维修手册研读、机密商务政策审核  
> **核心模块**: `src/ingestion/layout_parser.py` | `src/ingestion/hierarchical_chunker.py` | `src/retrieval/parent_child_retriever.py` | `src/ingestion/unstructured_parser.py`

---

## 1. 背景与企业级设计初衷

在智能汽车零售与研发垂直场景中，汽车技术参数、选装包规格、维保手册与商务调价函绝大多数以 **PDF** 格式沉淀。然而，传统通用 RAG 流水线在面对汽车工程级 PDF 时存在致命的**信息失真与上下文断裂**：

1. **盲目字符切分破坏表格二维拓扑**：传统切块器（如 LangChain RecursiveCharacterTextSplitter）按固定 Token 长度（如 500 token）硬切，导致同一行或同一列的参数被截断在不同 Chunk 中，LLM 无法推理参数间的对应关系。
2. **跨页长表格碎片化**：车辆配置表常跨越 2~5 页，各页均包含重复表头或中途截断。传统解析器输出孤立的表格碎片，使横向竞品对比失效。
3. **双栏/多栏排版水平串扰**：双栏技术文档在朴素提取下会按水平扫描顺序将左栏第 1 行与右栏第 1 行串联，造成语义完全颠倒。
4. **页眉/页脚/水印噪音污染向量空间**：重复出现的“保密材料”、“第 X 页”、旋转 45° 的半透明“CONFIDENTIAL”水印混入正文，大幅稀释稠密向量检索质量并引发模型幻觉。
5. **父子语义脱节**：微小单元（如“零百加速 1.98 秒”）若脱离上层车型（“Xiaomi SU7 Ultra”）与功能模块（“动力性能”），召回命中后无法支撑长文本生成。

为此，AutoVend 构建了**企业级版面感知文档解析器 (LayoutAwareParser)**、**分层语义切块器 (HierarchicalChunker)** 以及 **父子文档检索器 (ParentChildRetriever)**，实现端到端高精度表格与文本拓扑还原。

---

## 2. 九大企业级具体真实案例深度剖析

### 案例一：全车系官方配置对比总表（跨页超长复杂表格）
- **业务场景**：汽车官方发布的《全系车型技术参数与选装矩阵手册》，涵盖标准版、Pro、Max、Ultra、赛道版等多版本，横跨 3~5 页。
- **痛点体现**：
  - 第 1 页末尾表格未闭合，第 2 页顶部重复出现 6 列全套表头；
  - 传统工具将其分为两个独立小表格，检索“仰望U9纽北版电驱参数”时只能召回第 2 页，缺失原始表头语义定义；若直接合并原始字符，则正文中插入冗余重复表头。
- **AutoVend 落地方案**：
  - **几何与特征对齐拼接**：`CrossPageTableStitcher` 检测前后页表格的列数一致性、水平外接矩形边框坐标（`x0`, `x1` 偏差 $\le 25\text{pt}$）、逐列列宽几何分布方差（Column Width Variance $\le 625\text{pt}^2$）以及表头相似度。
  - **表头去重与行号重映射**：自动剥离续页重复表头，将后续数据行追加至首页表格，合并单元格坐标与边界框，生成标注有 `is_stitched=True, pages=[1, 2]` 的统一 `TableBlock`。
  - **标准二维 Markdown 输出**：LLM 接收到的是一张完整平铺的 10 行 $\times$ 6 列全局参数矩阵。

### 案例二：底盘悬架与空气动力学工程白皮书（双栏学术工程排版）
- **业务场景**：主机厂研发中心发布的底盘白皮书，采用左栏“前轴主动双叉臂悬架与气动阻尼”、右栏“后轴矢量四电机差速控制”的双栏排版。
- **痛点体现**：
  - 朴素文本提取沿垂直 Y 轴扫描，提取出“前轴采用全铝合金双叉臂... 后轴搭载双独立电机... 系统每秒监测1000次... 产生偏航力矩...”，左右两栏句子被物理交织，语法完全破坏。
- **AutoVend 落地方案**：
  - **启发式几何分带与水平X轴自适应聚类**：`ReadingOrderSorter` 结合全宽阈值与标题特征判定 Spanning Banner（横幅隔离带），将版面纵向切分多区域，并在各区域内按水平 X 坐标聚类左右分栏。
  - **自然阅读顺序重组**：先顺序读取全宽章节横幅，再自上而下完整读取左栏所有段落，最后自上而下读取右栏所有段落，彻底消除分栏穿透。

### 案例三：内部机密销售策略与调价函扫描件（水印/页眉页脚与混合扫描）
- **业务场景**：包含厂商指导价、金融免息贴息政策的扫描版红头文件与 PDF，背景斜向印有“CONFIDENTIAL / 内部机密”水印，顶部有统一“AutoVend Enterprise 2026”标识，底部为“Page 1 of 3”。
- **痛点体现**：
  - 水印文字穿插在“指导价 81.49 万元”中间变成“指导 CONFIDENTIAL 价 81.49 万元”；页眉页脚在每页切块中均被切碎作为独立 chunk，导致针对“机密”、“免责”的搜索大量误召回。
- **AutoVend 落地方案**：
  - **边距边界与旋转矢量检测**：`HeaderFooterWatermarkFilter` 针对顶部 8% 与底部 8% 边距区域进行短文本与页码正则过滤；
  - **文字方向矢量识别**：对非水平倾斜文本行（`dir != (1.0, 0.0)`）与机密关键词直接归入噪音层过滤，确保正文语义纯净。

### 案例四：跨国车型竞品对标技术汇编（多层级深度标题与面包屑路径）
- **业务场景**：包含 100+ 页的车型对标报告，章节深度达到 H1 -> H2 -> H3 -> H4（例如：“2. 底盘悬架” -> “2.1 整体动态控制” -> “2.1.2 后轴扭矩分配”）。
- **痛点体现**：
  - 子段落切块后只包含“具备微秒级独立正负扭矩响应能力”，检索时无法得知该扭矩控制针对的是“前电机”还是“后电机”，属于“小米SU7”还是“仰望U9”。
- **AutoVend 落地方案**：
  - **层级树检测与面包屑注入**：`DocumentHierarchyBuilder` 根据字体大小梯度与章节编号自动建立祖先堆栈，将 `breadcrumb_path: ["2. 底盘悬架...", "2.1.2 后轴扭矩..."]` 固化在 Chunk 元数据中，并在文本开头强行注入 `【路径: 章节 > 子章节】`，为检索模型提供锚定上下文。

### 案例五：汽车金融贷款与全险定制方案白皮书（多层嵌套条款、复合表头与细则附注）
- **业务场景**：主机厂与合作金融机构联合发布的《汽车金融贷款与全险定制方案白皮书》（`financial_autoloan_policy_specs.pdf`），包含 0 息方案、超低息长贷、50-50 残值保值贷等多层级利率方案，以及电池特约险与免责条款。
- **痛点体现**：
  - 表格采用 2 层复合表头设计（Row 0 广义方案分类/还款期数，Row 1 细化名义费率/综合年化利率 IRR）；传统解析器将 Row 1 识别为数据行，导致字典转换错位；
  - 表格底部嵌入微小字体法律责任声明（如“*注1：IRR依人民银行单利口径测算”、“*注2：提前还款按未还本金 3% 计收违约金”），传统提取将其作为普通数据行塞入表格，导致 forward-fill 错乱；
  - 传统按块切分时，保险免责条款与对应险种数据脱节，LLM 在合规质询时产生严重幻觉。
- **AutoVend 落地方案**：
  - **复合表头自适应升维**：`TableBlock` 自动识别跨列多级表头，生成层级键值（`金融方案分类 > 方案名称`、`利率及年化费率 > 综合年化利率IRR`）；
  - **细则附注底部弹出与数据净化**：自动检测底部星号/注记行并移入 `TableBlock.footnotes`，并在转 Markdown 时格式化为尾部斜体说明，在 `to_records()` 字典中剔除，确保纯净数据；
  - **父子文档联合召回**：通过子块精准命中违约金或特约险细则，向上扩展获取完整金融利率大表与免责条款。

### 案例六：高压电驱与电池系统检修技术手册（单双栏混合混排、嵌入式参数表与验收规范）
- **业务场景**：高压系统售后检修手册（`vehicle_maintenance_diagnostic_manual.pdf`），版面结构为：顶部全宽安全警示横幅 $\to$ 中部双栏故障诊断流程（左栏 DTC 代码、右栏物理测量） $\to$ 全宽嵌入式引脚电气规格表 $\to$ 底部全宽终检验收规范。
- **痛点体现**：
  - 传统单双栏混合解析器在处理中部双栏时，常将下方的全宽表格标题误判为左栏段落，破坏双栏阅读顺序；
  - 嵌入式表格前后的段落被错误揉进同一文本块，导致底部终检验收规范出现在表格之前；
  - 安全警示横幅与终检验收规范具有强制操作法律效力，若顺序颠倒或漏读将引发严重维保安全事故。
- **AutoVend 落地方案**：
  - **无水平对齐邻居的单流判定**：`ReadingOrderSorter` 智能检测文本块水平邻居；无水平并列块的独立标题与横幅直接判定为 Spanning Block，杜绝被误吸入左栏；
  - **带括号规范标头提取**：自适应识别 `【高压作业安全规范警示】` 与 `【终检验收规范】` 等标准化黑括号标题，赋予独立层级与几何 BBox；
  - **版面时序拓扑统一重排**：在 `get_full_markdown()` 中，严格按照真实物理纵坐标对横幅、左右双栏段落、嵌入式表格与终检验收规范进行时序还原。

### 案例七：超跑极限技术参数表白皮书（无框线留白对齐不规则表格与叙述性长句消歧）
- **业务场景**：无框线留白极简设计白皮书（`irregular_borderless_specs.pdf`），车辆性能参数采用多列纯空格/水平制表符对齐排版，无任何水平或垂直网格线。
- **痛点体现**：
  - `pdfplumber` 依赖网格线，面对无框线表格直接返回空列表；
  - 简单基于空白切分容易将普通的双栏正文段落（如核心技术解读的长句叙述）误判为无框线表格，导致文章正文被支离破碎地解析为无意义的单字单词表格。
- **AutoVend 落地方案**：
  - **流式列锚点聚类**：`BorderlessTableDetector` 扫描页面文本行，动态寻找水平间距 $> 20\text{pt}$ 的列间隙，对连续 3 行以上具有相似列锚点分布的行簇进行表格判定；
  - **标点符号与行宽消歧引擎**：对候选行检测标点符号（包含 `。`、`，`）或行宽超过阈值（$> 120\text{pt}$）的长句，直接剔除判定为叙事性段落，杜绝双栏正文被误判为表格；
  - **无框线表格原子注入**：提取包含 6 列的极速参数表，标记 `is_borderless=True`，并保留附注实测工况说明。

### 案例八：全球超跑十二维度技术对标汇编（横竖版混合混排与 90° 旋转宽屏超宽矩阵）
- **业务场景**：多页跨国竞品对标汇编（`mixed_orientation_enterprise_specs.pdf`），第 1 页为竖版导言，第 2 页顺时针旋转 90° 改为横版（A4 Landscape）展示 12 列超宽参数矩阵，第 3 页恢复为竖版研判。
- **痛点体现**：
  - 传统固定尺寸解析器将横版页面的宽、高按竖版处理，导致超出右边界的 4 列参数（如最高时速、制动距离、指导价）被无情截断丢失；
  - 跨页表格拼接器在检测不同页面方向时产生几何坐标错位崩塌。
- **AutoVend 落地方案**：
  - **逐页几何尺寸与朝向感知**：`PyMuPDFPlumberEngine` 为每页独立维护 `page_dimensions` 与 `page_orientations`（记录 `{1: 'portrait', 2: 'landscape', 3: 'portrait'}`），并在文档元数据中标记 `has_mixed_orientations=True`；
  - **动态边界检测与宽表完整提取**：横版页面基于其实际页面宽度（$841.89\text{pt}$）进行表格提取，成功无损捕获包含 12 维参数（涵盖驱动形式、电机数、马力、扭矩、放电倍率等）的超宽矩阵；
  - **自适应跨页宽松几何对齐**：当检测到混合排版时，放宽绝对水平坐标严格匹配，优先按列数与表头特征进行弹性拼接。

### 案例九：纽北赛道版内部验证手册（多页高频重复水印清洗与 CAD 工程图扫描件降级容灾）
- **业务场景**：包含高密级纽北赛道调校数据的技术手册（`scanned_brochure_watermark_specs.pdf`），每页背景斜向密集覆盖 `"INTERNAL ONLY - DO NOT DISTRIBUTE"` 重复水印，第 2 页为纯 CAD 底盘结构图纸（无字符层），第 3 页为售后质保细则。
- **痛点体现**：
  - 密集的重复水印文本被错误拆分为成百上千个细碎 chunk，使得语义向量检索针对“赛道”、“调校”的查询完全被水印字符掩盖；
  - 纯图片页面在缺乏 OCR 本地模型时通常报错崩溃或静默丢失，导致后续质保条款页码偏移。
- **AutoVend 落地方案**：
  - **多特征水印抑制矩阵**：`HeaderFooterWatermarkFilter` 结合斜向旋转矢量检测、浅灰色彩度阈值（RGB 分量近白）、以及高频机密词库正则，将 3 页中所有重复出现的水印全量彻底清除（`full_md` 中 0 残留）；
  - **逐页分类诊断与结构化降级**：`pages_classification` 准确输出 `{1: 'digital', 2: 'scanned', 3: 'digital'}`；针对纯图纸页生成带尺寸、朝向、图片资产元数据的诊断性 `TextSection`，为多模态 Vision-LLM 留出无缝召回锚点。

### 案例十：全系超跑技术规格表（跨页连续无网格线纯留白长表格）
- **业务场景**：跨页连续无框线车型参数总表（`enterprise_borderless_multipage_specs.pdf`），跨越第 1 页至第 2 页，全表无任何横竖网格线，且第 2 页顶部重复出现 6 列完整表头。
- **痛点体现**：
  - `pdfplumber` 无法识别跨页无框线表格；朴素字符提取会切断第 1 页末尾行与第 2 页起始行的逻辑连接；
  - 续页重复出现的留白表头如果未被剥离，会作为普通车型参数行被解析，污染结构化字典。
- **AutoVend 落地方案**：
  - **逐页流式列锚点对齐**：`BorderlessTableDetector` 在前后页分别聚类出一致的 6 列水平锚点分布；
  - **跨页无框线自动缝合**：`CrossPageTableStitcher` 感知列数一致与表头匹配，自动剥离续页重复表头，合并为拥有 10 行 $\times$ 6 列的全局统一 `TableBlock(pages=[1, 2], is_borderless=True, is_stitched=True)`，并将底部实测工况注记绑定至 `tbl.footnotes`。

### 案例十一：全生命周期整车三电质保与维保巡检大纲（三层深度合并单元格与层级缓存重置）
- **业务场景**：OEM 主机厂官方发布的三电质保巡检手册（`oem_warranty_maintenance_matrix.pdf`），表格具有一级系统分类（三电高压核心系统/智能底盘与制动）、二级总成部件（PACK/双电机/CDC减振/碳陶制动）及三级具体零件的三层深度树状合并单元格。
- **痛点体现**：
  - 合并分类单元格跨多行导致子行出现大面积空值；传统朴素向前填充在主分类切换到“智能底盘与制动”时，子分类错误沿用上一分类的“双电机电驱总成”，导致底盘部件被错误挂在电驱系统下。
- **AutoVend 落地方案**：
  - **多层级分类自适应向前填充**：`normalize_forward_fill()` 逐行逐列追踪层级分类；
  - **主分类变更深度级联重置**：当检测到一级主分类发生跃迁时，强制清空二级以下所有历史子分类缓存，确保“智能底盘与制动”下的减振系统不会继承“动力总成”子属性；
  - **结构化无歧义字典导出**：`to_records()` 输出 8 个完整记录，消除任何层级断裂。

### 案例十二：高压电气故障诊断与部件更换工时白皮书（非对称三栏排版与全宽强制规程横幅）
- **业务场景**：售后车间故障排故手册（`unequal_three_column_specs.pdf`），版面采用非对称三栏排版（左栏 DTC 遥测流 155pt、中栏示波器波形与物理测量 215pt、右栏备件采购与工时定额 153pt），版面中部嵌入一条全宽强制安全警示横幅 `【高压系统安全隔离与防电弧飞溅强制规程】`。
- **痛点体现**：
  - 栏宽不一致且栏间距不规则，传统分栏聚类算法在跨过中间全宽横幅时发生栏位错位与行穿透；
  - 强制规程如果被错误吸收进左栏，将导致技师在未断电验电的情况下提前测量，造成电弧飞溅等重大伤亡事故。
- **AutoVend 落地方案**：
  - **动态中缝与中心线跨越判定**：`ReadingOrderSorter` 识别跨越中线（Midpoint）且宽度超过阈值的全宽横幅作为版面隔离带；
  - **分区三栏自适应排序**：以全宽横幅为分界线，横幅上方严格按“左栏1.1 $\to$ 中栏1.2 $\to$ 右栏1.3”读取，随后读取全宽强制规程，最后顺序读取横幅下方“左栏2.1 $\to$ 中栏2.2 $\to$ 右栏2.3”，阅读顺序 100% 保真。

---

---

## 3. 十五大核心工程难点痛点与技术攻关方案

| 序号 | 核心难点 / 痛点 | 常见失效模式 | AutoVend 企业级技术攻关方案 |
| :--- | :--- | :--- | :--- |
| **1** | **跨页长表格无缝缝合**<br>*(Multi-Page Continuous Stitching)* | 跨 3 页以上连续表格拼接断裂；续页重复表头或无表头切断；`curr_tbl.page_num` 固定导致第 3 页断开 | `CrossPageTableStitcher`：表格外接矩形水平边界对齐（偏差 $\le 25\text{pt}$）、列数一致性校验及逐列列宽几何分布方差一致性校验；动态追踪累积最后一页，自动剥离续页表头并重映射行索引与单元格坐标，生成统合 `TableBlock(pages=[1, 2, 3...], is_stitched=True)`。 |
| **2** | **复合多级表头与防字典覆盖**<br>*(Multi-Level Compound Headers)* | 2 层复合表头（大类+子属性）第二行被误认为数据行；同名列在 `to_records()` 字典转换中相互覆盖导致数据永久丢失 | `TableBlock`：自动识别跨列多级表头（Row 0 广义大类 + Row 1 细化参数），生成标准化复合表头（`大类 > 参数项`）；自动重命名同名列进行消歧，确保键值对完整不丢失。 |
| **3** | **表格层级归一化与父级重置**<br>*(Hierarchical Normalization & Reset)* | 合并分类单元格跨行导致子行出现空值（`""`）；父分类切换时子分类错误沿用前一分类缓存引发语义污染；序号列误重置下级分类 | `TableBlock.normalize_fill()`：支持任意列深度与向前/向后/双向平铺；自动识别并保护行号序号列（Index Column），一级主分类发生变化时递归清空所有二级以下子分类缓存，杜绝跨系统数据串扰。 |
| **4** | **双栏/多栏排版自然阅读顺序**<br>*(Multi-Column Reading Order)* | 双栏或三栏排版水平读取造成多栏行间文字交织混乱；错落段落因局部缺乏对齐邻居被误判为全局横幅 | `ReadingOrderSorter`：采用启发式几何分带与水平 X 轴自适应聚类算法；结合宽度阈值与标题特征判定 Spanning Banner 切分垂直带，在带内聚类左右栏，严格保证自然“左栏顶至底 $\to$ 中栏 $\to$ 右栏”顺序，消除行穿透。 |
| **5** | **OCR 朝向检测与扫描件容灾**<br>*(OCR Disorientation & Scanned Fallback)* | 移动端拍摄或扫描件发生 90°/180°/270° 旋转导致 OCR 字符乱码；本地缺字库时纯扫描页被静默丢弃 | `OCROrientationDetector`：解析行向量 `dir` 与页面属性判定旋转角度并校正归一；针对纯扫描图片页，在 OCR 无法提取时保留包含尺寸、朝向、图片资产的结构化诊断 `TextSection`，杜绝页面静默丢失。 |
| **6** | **页眉/页脚/水印噪音多页去重**<br>*(Running Header & Watermark Cleaner)* | 各页运行页眉在向量切块中碎片化分散；斜向机密水印穿插在价格与参数中严重污染相似度 | `HeaderFooterWatermarkFilter`：统计全文档顶部边距高频文本（出现 $\ge 2$ 次直接认定为运行页眉）；扩展中英文页码正则引擎；结合旋转矢量判定 120 字符内水印标签，确保文本纯净。 |
| **7** | **表格独立原子分块与富元数据**<br>*(Table Atomic Chunking)* | 表格在分块时被随机 token 上限截断破坏 Markdown 语法与结构 | `HierarchicalChunker`：表格强制作为独立原子 Parent Chunk；在表头注入车型、章节、页码、BBox、拼接状态元数据；按行滑动切分小 Child Chunk。 |
| **8** | **无框线/空白流列表格识别与叙事消歧**<br>*(Borderless Table & Narrative Disambiguation)* | 缺失任何网格线导致 pdfplumber 提取为空；盲目按列间隙切分将双栏叙事正文误判为破碎表格 | `BorderlessTableDetector`：通过行内文本水平投影聚类列锚点（间隙 $\ge 20\text{pt}$）；结合句子标点（`。`、`，`）与行宽阈值（$\ge 120\text{pt}$）剔除叙事性长句，精准提取纯留白参数表，标记 `is_borderless=True`。 |
| **9** | **混合排版与横屏超宽表边界适配**<br>*(Mixed Orientation & Landscape Matrix)* | 同一 PDF 内竖版与横版交替导致横版页面右侧列被截断；跨页表格按固定竖版坐标拼接产生错位 | `PyMuPDFPlumberEngine`：动态追踪逐页几何尺寸 `page_dimensions` 与旋转朝向 `page_orientations`；横版页面自适应扩展至实际宽度（$841.89\text{pt}$）无损捕获 12 列超宽矩阵，标记 `has_mixed_orientations=True` 并启用跨页弹性对齐。 |
| **10** | **表格微小字体细则附注弹出与数据行防污染**<br>*(Footnotes / Fine Print Isolation)* | 位于表格底部的星号注记、单利/复利声明、提前还款违约金被作为数据行处理，污染平铺算法与结构化字典 | `TableBlock`：自动扫描表格底部与紧随表格下方 45pt 内的单列星号/注记行存入 `self.footnotes`，在 `to_markdown()` 中渲染为底部斜体说明，在 `to_records()` 字典与 forward-fill 中完全剔除，杜绝法律合规细则污染结构化数据。 |
| **11** | **密集重复水印矩阵与半透明文字过滤**<br>*(Repeated Watermark Matrix Cleaner)* | 斜向密集覆盖的“INTERNAL ONLY”等重复文字分散在每一页中，大量污染稠密向量空间引发检索误导 | `HeaderFooterWatermarkFilter`：综合旋转矢量 `dir`、高频机密词库正则（`INTERNAL ONLY`、`CONFIDENTIAL`）以及文字透明度/浅灰色彩度阈值，实现全文档 0 残留彻底清洗。 |
| **12** | **单双栏混合与嵌入式无框线表格阅读时序**<br>*(Mixed Layout Reading Topology)* | 顶部横幅、中部双栏、嵌入式无框线表格与底部终检验收规范纵向交错，导致下方横幅或规范被错误提前或滞后 | `ReadingOrderSorter` 与 `ParsedDocument.get_full_markdown()`：通过结合特征的横幅判定识别 Spanning Block；记录真实几何 BBox，按统一时序拓扑将横幅、双栏流、嵌入式无框线表格及底部规范自上而下严格还原。 |
| **13** | **跨页无网格线连续表格拼接**<br>*(Continuous Borderless Table Stitching)* | 跨页长表格无任何边框网格，各页均通过空白流列对齐，续页带有重复表头导致跨页拼接算法失效 | `BorderlessTableDetector` 与 `CrossPageTableStitcher`：前后页分别提取无框线表格后，基于一致列数、水平列锚点坐标容差（$\le 25\text{pt}$）以及表头字符串一致性，自动剥离续页重复表头并无缝缝合为统一跨页大表。 |
| **14** | **多层深度树状合并单元格双向填充**<br>*(Multi-Level Merged Category Normalization)* | 一级大类、二级子模块、三级零件多层深度树状表格，在多行合并下出现层级空值与父类污染；序号列导致下级误重置 | `TableBlock.normalize_fill()`：支持任意列深度分类向前/向后/双向平铺；序号列独立保护，主分类变更时递归清空所有子级缓存，输出规范扁平记录字典。 |
| **15** | **非对称三栏排版与中嵌全宽横幅**<br>*(Asymmetric 3-Column Reading Reconstruction)* | 三栏宽度不均（155pt/215pt/153pt），中间跨越全宽强制安全规程横幅，朴素提取发生栏间串联 | `ReadingOrderSorter`：自适应聚类非对称水平 X 坐标，以全宽横幅为自然阻断屏障，构建清晰的 Zone 1（左 $\to$ 中 $\to$ 右） $\to$ 横幅 $\to$ Zone 2（左 $\to$ 中 $\to$ 右）拓扑。 |

---

## 4. 系统架构与多引擎拓扑

AutoVend 采用**分层插件化多引擎架构**，支持本地离线轻量化解析与云端高精度多模态大模型解析的自由切换：

```
                              ┌───────────────────────────────────────────────┐
                              │            Raw PDF / Document Input           │
                              └──────────────────────┬────────────────────────┘
                                                     │
                                                     ▼
                              ┌───────────────────────────────────────────────┐
                              │     LayoutAwareParser (Facade Dispatcher)     │
                              └──────┬─────────────────┬─────────────────┬────┘
                                     │                 │                 │
                ┌────────────────────┴───┐    ┌────────┴────────┐   ┌────┴───────────────────┐
                ▼                        ▼    ▼                 ▼   ▼                        ▼
     ┌───────────────────────┐  ┌───────────────┐  ┌─────────────┐  ┌───────────────────────┐
     │ PyMuPDFPlumberEngine  │  │ Azure Doc AI  │  │Unstructured │  │ MinerU / Docling Engine│
     │ (Local Hybrid Engine) │  │(Cloud Preview)│  │ (Partition) │  │  (Open-Source Model)  │
     └──────────┬────────────┘  └───────┬───────┘  └──────┬──────┘  └───────────┬───────────┘
                │                       │                 │                     │
                └───────────────────────┼─────────────────┴─────────────────────┘
                                        ▼
    ┌───────────────────────────────────────────────────────────────────────────────────────┐
    │                               Layout Recovery Pipeline                                │
    │  1. Header/Footer/Watermark Noise Cleaner (HeaderFooterWatermarkFilter)                │
    │  2. Dual-Column Reading Order Reconstructor (ReadingOrderSorter)                      │
    │  3. Cross-Page Table Boundary Stitcher (CrossPageTableStitcher)                       │
    │  4. Hierarchical Heading & Breadcrumbs Builder (DocumentHierarchyBuilder)              │
    └───────────────────────────────────┬───────────────────────────────────────────────────┘
                                        │
                                        ▼
    ┌───────────────────────────────────────────────────────────────────────────────────────┐
    │                               ParsedDocument Structure                                │
    │  • sections: List[TextSection] (with breadcrumb_path & BBox)                          │
    │  • tables: List[TableBlock] (with Markdown, HTML, to_records(), is_stitched, pages)   │
    │  • metadata: {pages_classification, has_stitched_tables, engine}                      │
    └───────────────────────────────────┬───────────────────────────────────────────────────┘
                                        │
                                        ▼
    ┌───────────────────────────────────────────────────────────────────────────────────────┐
    │                       HierarchicalChunker (Parent-Child Engine)                       │
    │  • Parent Chunks (~1000 tokens): Complete context with metadata headers               │
    │  • Child Chunks (~200 tokens): Sliding window retrieval units with breadcrumb headers │
    │  • Atomic Table Chunks: Unbroken Markdown tables + structured metadata               │
    └───────────────────────────────────┬───────────────────────────────────────────────────┘
                                        │
                                        ▼
    ┌───────────────────────────────────────────────────────────────────────────────────────┐
    │                       ParentChildRetriever (Retrieval & Filter)                       │
    │  • Dense Vector & Lexical Index on Child Chunks                                       │
    │  • Key-Value Store for Parent Contexts & Atomic Tables                                │
    │  • Multi-factor Metadata Filtering (filter_metadata={"is_table": True, ...})          │
    │  • Deduplication & LLM Context Injection (format_llm_context)                         │
    └───────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 5. 核心数据结构与接口规格

### 5.1 基础版面几何与表格对象
- `BoundingBox(x0, top, x1, bottom, page)`：标准二维浮点坐标边界框，提供 `width`, `height`, `from_tuple(coords, page)`, `to_dict()`, `to_tuple()`。
- `TableCell(row_idx, col_idx, text, row_span, col_span, bbox)`：单元格对象，记录跨行跨列跨度。
- `TableBlock`：
  - `pages: List[int]`：支持记录单页（如 `[1]`）或多页拼接（如 `[1, 2]`）。
  - `is_stitched: bool`：标识是否经过跨页无缝缝合。
  - `is_borderless: bool`：标识是否为无框线空白流列自适应识别表格。
  - `is_multilevel_header: bool` & `header_rows_count: int`：标识是否属于多级复合表头（Row 0 广义类别 + Row 1 细化指标）。
  - `footnotes: List[str]`：从表格底部自动剥离提取的微小字体注记、免责声明与细则附注列表。
  - `to_markdown(include_title=True) -> str`：转为对大模型注意力最优的 Markdown 语法（含尾部斜体附注）。
  - `to_html(include_title=True) -> str`：保留完整 `rowspan` / `colspan` 的语义化 HTML 表格。
  - `normalize_forward_fill() -> List[List[str]]`：向前填充解决合并分类单元格断裂问题，主分类变更自动清空子级缓存。
  - `to_records() -> List[Dict[str, str]]`：输出标准扁平复合键值对字典（如 `'利率及年化费率 > 综合年化利率IRR': '3.80%'`），严格剔除附注行。

### 5.2 章节与文档对象
- `TextSection`：
  - `title: str`, `content: str`, `level: int`（1至4级标题）
  - `bbox: Optional[BoundingBox]`：记录章节标题或首段在页面上的真实几何边界框。
  - `breadcrumb_path: List[str]`：面包屑祖先树路径，如 `["2. 底盘工程", "2.1.2 后轴扭矩矢量"]`。
- `ParsedDocument`：
  - `title`, `vehicle_model`, `sections`, `tables`, `pages`, `raw_text`, `metadata`。
  - `page_dimensions: Dict[int, Tuple[float, float]]`：逐页物理几何尺寸字典（如 `{1: (595.28, 841.89), 2: (841.89, 595.28)}`）。
  - `page_orientations: Dict[int, str]`：逐页旋转朝向映射（如 `{1: 'portrait', 2: 'landscape', 3: 'portrait'}`）。
  - `get_full_markdown() -> str`：严格依据真实几何纵坐标 `(page_num, top)`，将标题、双栏正文段落、嵌入式表格与终检验收规范以时序保真交织拼接为完整 Markdown。

---

## 6. 父子检索与 LLM 上下文合成设计

### 6.1 父子分块逻辑
1. **Parent Chunks（约 800-1000 Tokens）**：
   - 保持语义宏观完整性。
   - 注入前缀：`【章节: {title} | 路径: {breadcrumb_str} | 车型: {model} | 级别: H{level}】`。
2. **Child Chunks（约 150-250 Tokens）**：
   - 句子级滑动切分，保留 40 Token 重叠窗口。
   - 注入前缀：`[{vehicle_model} > {breadcrumb_str}]`，确保即使被孤立向量化也能携带车型主体。
3. **Table Child Chunks**：
   - 将长表格按 2~3 行与完整表头组合切成轻量级检索单元，并在元数据记录 `parent_id` 对应整个完整大表格。

### 6.2 检索、去重与元数据过滤
- **检索阶段**：用户查询首先命中细粒度 Child Chunk（高相似度、无稀释）。
- **展开阶段**：通过 `parent_id` 瞬时展开为 cohesively intact 的完整 Parent Chunk 或完整 Markdown 大表。
- **去重与加权**：多个子块命中同一父文档时去重，并赋予多样性加权积分（Diversity Bonus）。
- **属性过滤**：支持通过 `filter_metadata={"is_table": True}` 实现纯表格检索，或指定特定车型/章节精准检索。

---

## 7. 质量验证与基准评测矩阵

在本项目测试套件中，共构建了 **78 个自动化单元与集成测试用例**（涵盖原有 56 个核心检索回归测试以及 22 个企业级全场景专项测试，全部 100% 通过）：

| 验证维度 | 测试用例 | 检验目标 | 实测结果 |
| :--- | :--- | :--- | :---: |
| **跨页拼接 (2页)** | `test_cross_page_table_stitching` | 验证多页表格合并、去重表头、合并为 10 行大表 | **PASSED (100%)** |
| **超长滚动 (3页)** | `test_cross_page_table_stitching_three_continuous_pages` | 验证跨第 1 至 3 页连续动态缝合，生成 `pages=[1, 2, 3]` 单一大表 | **PASSED (100%)** |
| **复合多级表头** | `test_multilevel_compound_table_headers_and_records` | 验证 2 层复合表头提取，生成 `大类 > 参数`，`to_records()` 键值完整防覆盖 | **PASSED (100%)** |
| **层级平铺重置** | `test_table_forward_fill_parent_category_reset` | 验证主分类变更时子分类缓存重置，彻底防止跨分类数据污染 | **PASSED (100%)** |
| **三栏版面重排** | `test_three_column_reading_order_sorter` | 验证横幅保留与 3 栏（左/中/右）自然阅读顺序还原，杜绝水平穿栏 | **PASSED (100%)** |
| **朝向与扫描容灾** | `test_ocr_orientation_detector_and_scanned_page_handling` | 验证 90°/180°/270° 朝向识别，纯扫描页生成诊断 `TextSection` 零数据丢失 | **PASSED (100%)** |
| **去噪过滤** | `test_header_footer_watermark_filtering` | 验证“Page 1 of 3”、顶栏页眉、CONFIDENTIAL 水印彻底清洗 | **PASSED (100%)** |
| **双栏排序** | `test_dual_column_reading_order_reconstruction` | 验证左栏（前轴悬架）在右栏（后轴差速）之前读取，无行串扰 | **PASSED (100%)** |
| **标题层级** | `test_hierarchical_headings_and_breadcrumbs` | 验证 H1/H2 继承关系与面包屑路径追踪 | **PASSED (100%)** |
| **表格归一化** | `test_table_normalization_and_forward_fill` | 验证合并单元格前向填充与 `to_records()` 字典生成 | **PASSED (100%)** |
| **父子切块** | `test_hierarchical_chunking_with_stitched_table` | 验证拼接表格作为独立原子 Chunk 输出，包含跨页元数据 | **PASSED (100%)** |
| **父子检索** | `test_parent_child_retriever_end_to_end_and_metadata_filter` | 验证按子块检索召回跨页完整大表与元数据精确过滤 | **PASSED (100%)** |
| **TOML转换** | `test_toml_converter_metric_extraction` | 验证马力、电池容量、零百加速字段结构化准确提取，价格对齐注册表 | **PASSED (100%)** |
| **案例一：金融贷款与附注** | `test_case1_financial_autoloan_nested_terms_and_fine_print` | 验证多级复合表头（`金融方案分类 > 方案名称`）、5个结构化记录提取、细则附注弹出保护 | **PASSED (100%)** |
| **案例二：单双栏混合检修** | `test_case2_vehicle_maintenance_mixed_column_layout` | 验证顶部警示横幅 $\to$ 1.1 DTC $\to$ 1.2 物理测量 $\to$ 引脚表 $\to$ 终检验收规范全流程时序还原 | **PASSED (100%)** |
| **案例三：无框线留白表格** | `test_case3_irregular_borderless_spec_table_detection` | 验证留白列流聚类（6列5行）、附注实测工况提取、叙事性长句消歧防误判 | **PASSED (100%)** |
| **案例四：横竖版混合超宽表** | `test_case4_mixed_orientation_portrait_landscape_matrix` | 验证横竖版朝向感知（P1竖/P2横/P3竖）、12列超宽矩阵完整提取、无截断 | **PASSED (100%)** |
| **案例五：密集水印与CAD扫描** | `test_case5_scanned_brochure_repeated_watermark_rejection_and_fallback` | 验证重复密集水印清洗（0残留）、CAD图纸页标记 `hybrid` 诊断降级、正文提取 | **PASSED (100%)** |
| **案例六：跨页无框线缝合** | `test_case6_cross_page_borderless_table_stitching` | 验证多页连续无网格线白皮书表格缝合（跨P1-P2）、续页表头剥离、10行6列大表统合 | **PASSED (100%)** |
| **案例七：三层深度质保大纲** | `test_case7_oem_warranty_maintenance_three_level_hierarchy` | 验证一级大类/二级模块/三级零件3层合并单元格向前平铺、主类切换级联重置、8条记录无歧义 | **PASSED (100%)** |
| **案例八：非对称三栏与全宽横幅** | `test_case8_unequal_three_column_reading_order_and_spanning_callout` | 验证不等宽3栏布局、跨中线中嵌横幅阻断、Zone 1 $\to$ 规程横幅 $\to$ Zone 2 顺序阅读 | **PASSED (100%)** |
| **全场景父子召回集成** | `test_end_to_end_parent_child_retrieval_across_new_cases` | 验证跨8类复杂PDF多文档同时建库，针对违约金、DTC引脚、无框线实测、超宽矩阵、质保细则、三电机马力、退磁条款与防电弧规程的精准召回 | **PASSED (100%)** |
| **全库回归验证** | `test_layout_parser.py` (10项) + `test_parent_child_retriever.py` (6项) + `test_hierarchical_chunker.py` (8项) + `test_bm25_index.py` (16项) + `test_fusion.py` (15项) + `test_ingestion_pipeline.py` (1项) | 验证原有几何计算、多引擎适配器、U9 解析兼容性、倒排与多路召回融合 | **78 PASSED (100%)** |

---

## 8. 生产部署建议与后续优化路线

1. **OCR 多模态混合大模型增强（MinerU / Marker / Docling）**：
   - 对于纯图片扫描件，推荐挂载 MinerU / Docling 本地模型或 Azure Document Intelligence 预建版面识别模型，直接输出具备 BBox 的 AST 树。
2. **GPU 批量预处理**：
   - 在高并发数据入库时，多页 PDF 解析（pdfplumber 边线搜索）属于 CPU 密集型任务，建议通过 Celery 或 Ray Worker 进行文档级并行处理。
3. **表格大宽表智能折叠**：
   - 针对超过 12 列的极端横向宽表，除转换为标准 Markdown 外，可进一步通过 `to_records()` 拆解为针对每个版本的独立规格键值段落，以适应更小上下文窗口的嵌入模型。

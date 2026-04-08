# 混合检索系统：SQLite粗筛 + RAG精排

基于结构化标签的SQLite粗筛，结合BGE-M3语义精排，通过混合意图解析（规则引擎优先 + LLM fallback）实现高精度车辆检索。

## 整体架构

```
用户查询 → [意图解析层] → 结构化条件 → [SQLite粗筛层] → 候选集 → [RAG精排层] → 最终排序 → LLM回答
                ↓                           ↓                        ↓
        规则引擎优先             树形/范围/枚举/别名策略     BGE-M3语义相似度
        LLM fallback            降级策略保证有结果          多维度评分
```

## 标签分类体系（基于 LabelsTree.json）

### A. 树形标签（多级层次结构）

**车型层级** `vehicle_category` — 3层: top → middle → bottom
```
sedan → small sedan    → [micro sedan, compact sedan]
         mid-size sedan → [b-segment sedan]
         mid-large sedan→ [c-segment sedan, d-segment sedan]
suv   → crossover suv  → [compact suv, mid-size suv, mid-to-large suv]
         body-on-frame  → [off-road suv, all-terrain suv]
mpv   → family mpv     → [compact mpv, mid-size mpv, large mpv]
         business mpv   → [mid-size business mpv, large-size business mpv]
sports car → convertible→ [two-door convertible, four-door convertible]
              hardtop   → [two-door hardtop, four-door hardtop]
```

**品牌层级** `brand` — 3层: area → country → brand
```
european → germany       → [volkswagen, audi, porsche, bentley, bugatti, lamborghini, bmw, mercedes-benz]
           france        → [peugeot, renault]
           united kingdom→ [jaguar, land rover, rolls-royce]
           sweden        → [volvo]
american → usa           → [chevrolet, buick, cadillac, ford, tesla]
asian    → japan         → [toyota, honda, nissan, suzuki, mazda]
           korea         → [hyundai]
           china         → [byd, geely, changan, great wall motor, nio, xiaomi, xpeng]
```

### B. 范围标签 + 别名系统（有序候选值 + 人类友好别名）

| 标签 | 候选值 | 别名 |
|------|--------|------|
| prize | below 10,000 ~ above 100,000 (7档) | cheap, economy, mid-range low-end, mid-range, mid-range high-end, high-end, luxury |
| horsepower | below 100hp ~ above 400hp (5档) | low, lower-medium, medium, high, extra-high |
| motor_power | below 70kw ~ above 400kw (6档) | low ~ extra-high |
| torque | below 200n·m ~ above 500n·m (5档) | low ~ extra-high |
| zero_to_100 | above 10s ~ below 4s (5档) | slow, medium, fast, very fast, extreme |
| top_speed | below 160km/h ~ above 300km/h (5档) | low ~ extreme |
| wheelbase | 2300-2650mm ~ above 3100mm (5档) | small ~ luxury spacious |
| trunk_volume | 200-300L ~ above 500L (4档) | small ~ luxury |
| passenger_space | 2.5-3.5m³ ~ above 5.5m³ (4档) | small ~ luxury |
| chassis_height | 100-130mm ~ above 200mm (4档) | low ride ~ off-road chassis |
| battery_capacity | 30-50kWh ~ above 100kWh (4档+none) | small ~ extra-large |
| fuel_tank_capacity | 30-50L ~ above 70L (3档+none) | small ~ large |
| fuel_consumption | 4-6L/100km ~ above 8L (3档+none) | low ~ high |
| electric_consumption | 10-12kWh ~ above 14kWh (3档+none) | low ~ high |
| driving_range | 300-400km ~ above 800km (3档) | short, medium, long |

### C. 枚举标签（精确匹配，无别名）

| 标签 | 候选值 |
|------|--------|
| powertrain_type | gasoline, diesel, hybrid, plug-in hybrid, range-extended, BEV |
| design_style | sporty, business |
| drive_type | front-wheel, rear-wheel, all-wheel |
| suspension | independent, non-independent |
| seat_layout | 2/4/5/6/7-seat |
| color | bright, neutral, dark |
| interior_material_texture | wood trim, metal trim |
| seat_material | leather, fabric |

### D. 布尔标签（Yes/No）
abs, esp, voice_interaction, ota_updates, adaptive_cruise_control, traffic_jam_assist, automatic_emergency_braking, lane_keep_assist, remote_parking, auto_parking, blind_spot_detection, fatigue_driving_detection, city_commuting, highway_long_distance, cargo_capability

### E. 等级标签（有序Low/Medium/High）
noise_insulation, body_line_smoothness, passability, off_road_capability, cold_resistance, heat_resistance, airbag_count(数值型)

### F. 模糊标签 — AmbiguousLabels（粗筛降权，精排侧重）
size, vehicle_usability, aesthetics, energy_consumption_level, comfort_level, smartness, family_friendliness

## 匹配策略

### 1. 树形展开匹配
查询任意层级，自动展开到bottom level，在SQLite中用 `IN (...)` 查询：
- "suv" → vehicle_category_bottom IN (compact suv, mid-size suv, mid-to-large suv, off-road suv, all-terrain suv)
- "european" → brand IN (volkswagen, audi, ..., volvo)

### 2. 范围区间匹配
利用有序候选值列表的**索引位置**实现区间比较：
- **精确**: "200-300hp" → horsepower = "200-300 hp"
- **至少**: "至少200hp" → 候选值index ≥ index("200-300 hp")
- **至多**: "低于300hp" → 候选值index ≤ index("200-300 hp")
- **区间**: "200-400hp" → index("200-300 hp") ≤ index ≤ index("300-400 hp")

### 3. 别名映射匹配
用户说"便宜的车" → alias "cheap" → 映射到 prize "below 10,000"
用户说"动力强劲" → alias "high" → 映射到 horsepower "300-400 hp" 或 "above 400 hp"

### 4. 降级策略
```
Level 0: 全部条件（精确+模糊）匹配
Level 1: 去除模糊标签(AmbiguousLabels)，仅精确标签
Level 2: 去除等级标签，保留核心（品牌/车型/价格/动力类型）
Level 3: 仅保留品牌或车型
Level 4: 放弃粗筛，直接RAG全库搜索
```
每级检查候选集大小，目标50-200辆，过少则降级。

## 实施步骤

### Phase 1: 基础设施

**Step 1.1** `src/filter/label_registry.py` — 标签注册表
- 加载 LabelsTree.json
- 分类为: tree / range / enum / boolean / grade / ambiguous
- 管理范围标签的有序候选值和index映射
- 管理别名到实际值的映射
- 树形结构的任意层级到叶子节点展开
- **扩展**: 支持中文别名映射（如"电动"→"battery electric vehicle"）

**Step 1.2** `src/filter/vehicle_db.py` — SQLite车辆数据库
- 建表: vehicles表包含 car_model(PK) + 所有PreciseLabels字段 + 所有AmbiguousLabels字段
- 所有值统一小写存储，便于case-insensitive匹配
- 索引: brand, vehicle_category_bottom, prize, powertrain_type, drive_type
- 从TOML文件批量导入（复用data_loader逻辑）
- DB文件存储于 `data/vehicles.db`

**Step 1.3** `src/filter/filter_engine.py` — 过滤引擎
- 接收结构化查询dict → 生成SQL WHERE子句 → 执行查询
- 策略分派: 根据label_registry判断标签类型，选择匹配策略
- 树形标签: 展开后用 IN
- 范围标签: 用有序index做范围比较
- 别名标签: 先转换为实际值再匹配
- 支持AND组合（所有条件取交集）
- 降级控制器: 根据结果集大小决定是否降级

### Phase 2: 意图解析层

**Step 2.1** `src/filter/query_parser.py` — 规则引擎
- 价格解析: 正则匹配中英文价格表达（30万、$30k、30-40万、budget 30k）
- 品牌识别: 中英文品牌名+常见别名（奔驰→mercedes-benz、大众→volkswagen）
- 车型识别: 支持各层级关键词（SUV、轿车、跑车、紧凑型、中大型等）
- 功能提取: 关键词→标签映射（电动→BEV、7座→7-seat、四驱→all-wheel drive）
- 性能提取: "快"→acceleration alias "fast"、"省油"→fuel_consumption alias "low"

**Step 2.2** `src/filter/llm_parser.py` — LLM意图解析（fallback）
- Prompt模板: 将自然语言转为结构化JSON，schema与label_registry对齐
- 输出格式: `{"brand": "volvo", "vehicle_category_top": "suv", "prize_alias": "mid-range"}`
- 输出验证: 确保key和value在label_registry中合法

### Phase 3: 管道整合

**Step 3.1** `src/retrieval/hybrid_pipeline.py` — 混合检索管道
```python
class HybridPipeline:
    def search(self, user_query: str) -> SearchResponse:
        # 1. 意图解析（规则优先，LLM fallback）
        structured_query = self.parse_intent(user_query)
        
        # 2. SQLite粗筛（带降级策略）
        candidates = self.coarse_filter(structured_query)
        
        # 3. RAG精排（在候选集内语义排序）
        if candidates:
            results = self.semantic_rerank(user_query, candidates)
        else:
            results = self.full_rag_search(user_query)
        
        return results
```

**Step 3.2** 改造 `VehicleRetriever`
- 新增方法: 接收候选car_model列表，仅在这些候选中做语义排序
- ChromaDB where过滤: `{"car_model": {"$in": [候选列表]}}`

### Phase 4: 测试

**Step 4.1** 单元测试
- label_registry: 树形展开、范围索引、别名映射
- filter_engine: 各策略独立测试 + 组合条件
- query_parser: 各类自然语言输入的解析准确性

**Step 4.2** 集成测试
- 端到端: "我想要一辆30-40万的纯电SUV" → 粗筛→精排→结果

## 目录结构

```
src/
├── filter/                    # 新增：结构化过滤模块
│   ├── __init__.py
│   ├── label_registry.py      # 标签注册表
│   ├── vehicle_db.py          # SQLite车辆数据库
│   ├── filter_engine.py       # 过滤引擎
│   ├── query_parser.py        # 规则引擎意图解析
│   └── llm_parser.py          # LLM意图解析（fallback）
├── retrieval/                 # 新增：检索管道
│   ├── __init__.py
│   └── hybrid_pipeline.py     # 混合检索管道
├── rag/                       # 现有：语义检索（改造retriever）
└── llm/                       # 现有：LLM模块
```

## 关键设计决策

- **SQLite而非内存字典**: 支持复杂SQL、范围查询、索引加速，数据持久化
- **别名系统**: LabelsTree.json已提供alias，扩展中文别名覆盖更多用户表达
- **降级保底**: 4级降级策略，确保始终有结果返回
- **混合意图解析**: 规则引擎快速处理80%常见查询，LLM处理剩余复杂语义

## 数据来源

- **LabelsTree.json**: 标签定义、树形结构、别名映射（已有，可扩展）
- **VehicleData/*.toml**: 1281辆车的完整标签数据
- **SQLite**: Python标准库sqlite3，零额外依赖

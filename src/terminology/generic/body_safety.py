"""
Generic Body Safety & Lightweight Manufacturing Technical Terminology (src/terminology/generic/body_safety.py).
Contains 17 comprehensive generic body safety & manufacturing technologies (category="车身安全").
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

GENERIC_BODY_SAFETY_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 一体化超大吨位压铸技术 (Gigacasting)
    TechnologyEntity(
        id="generic_gigacasting_integrated_die_casting",
        name="一体化超大吨位压铸技术 (Gigacasting)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Gigacasting Integrated Ultra-Large Die-Casting Technology",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="车身先进制造/一体化压铸",
        aliases=[
            "一体化压铸",
            "大压铸",
            "gigacasting",
            "压铸后地板",
            "压铸前机舱",
            "超大吨位压铸",
        ],
        summary="采用6000吨至16000吨级超巨型压铸机与免热处理铝合金材料，将原本由数十上百个冲压钢板、上千个焊点构成的车身下体总成瞬间一体化压铸成型的革命性车身工艺。",
        description=(
            "传统汽车白车身由数百个钢板冲压件通过机器人点焊、涂胶拼接而成，焊点多、公差累积大且车身笨重。"
            "一体化大压铸（Gigacasting）利用超高压射出机构将700℃液态免热处理铝合金在毫秒内注入巨型精密模具中，一次性铸造出整块一体化后地板或前机舱结构。"
            "不仅直接减少70多道传统冲压焊接工序，消除1000多个焊点，车身结构轻量化减重10%~20%，更使车身后部扭转刚度跃升30%以上，抗扭抗冲击性能坚固无比。"
        ),
        technical_principles=[
            "千吨级免热处理强韧铝合金材料配方抑制冷缩变形与微观气孔",
            "万吨级锁模力液压机与真空微米级高速熔融铝液射出充型模流控制",
        ],
        advantages=[
            "零部件集成度极高：将上百个零件合为一体，彻底消除焊点松动撕裂与焊道异响隐患",
            "轻量化与超高刚度：车身减重15%以上，后桥扭转刚度大幅跃升，操控更加紧致沉稳",
            "大幅缩短整车生产节拍与工厂焊装车间占地面积，降低规模化量产制造成本",
        ],
        limitations=[
            "超大压铸模具与万吨级设备初次重资产投资极其巨大，仅适合超大规模量产车型",
            "若发生严重恶性追尾导致一体化压铸件主梁变形受损，无法局部钣金敲打，维修更换成本较高（需配合分段可更换溃缩吸能盒设计保护）",
        ],
        sub_variants={
            "后地板一体化大压铸": "行业最普及的核心方案（如特斯拉Model Y、小鹏G6/X9、极氪001/007）",
            "前机舱+后地板双一体化压铸": "前后双大压铸旗舰架构（如特斯拉Cybertruck、小米SU7）",
        },
        representative_vehicles=["特斯拉Model Y/Cybertruck", "小米SU7(9100t大压铸)", "小鹏X9/G6(前后双压铸)", "极氪001/007/009", "问界M9(9000t压铸)"],
        standard_labels=["一体化压铸", "Gigacasting", "万吨级压铸", "免热处理铝合金", "消灭千个焊点", "车身超高刚度"],
        equivalence_group_id=EquivalenceDomain.GIGACASTING_STRUCTURE,
        sales_talking_points=[
            "向追求车身安全性与操控品质的客户展示白车身模型：‘整块后地板是万吨巨型压铸机一秒压铸成型的完整铝合金，没有一个焊接缝隙，就像一整块坚硬无比的金属盾牌，不仅追尾时坚不可摧，而且激烈过弯时后轴极度紧绷扎实！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 2. 热成型硼钢与潜艇级超高强笼式安全车身
    TechnologyEntity(
        id="generic_hot_stamped_boron_steel_cage",
        name="热成型硼钢与潜艇级超高强笼式安全车身",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Hot-Stamped Boron Steel & Submarine-Grade Cage Safety Body",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="被动安全结构/车身钢材",
        aliases=[
            "热成型钢",
            "潜艇级热成型钢",
            "2000mpa热成型钢",
            "笼式车身",
            "超高强钢",
            "硼钢",
        ],
        summary="在乘员舱A柱、B柱、门槛梁与车顶侧梁大量采用抗拉强度高达1500MPa-2000MPa的超高强度热成型硼钢，构建起如坚固潜水艇般的乘员防护生存座舱。",
        description=(
            "车辆在遭遇严重侧面碰撞或翻滚撞击时，车门B柱与车顶是保护乘员头部免受挤压的最后防线。"
            "热成型钢将特种含硼合金钢板加热至950℃奥氏体状态后在模具中瞬间加压淬火冷却，屈服强度与抗拉强度跃升至1500MPa至2000MPa（相当于指甲盖大小承受20吨重压而不变形）。"
            "将这些超硬热成型钢与高强度钢环抱组合成球笼式环形闭合骨架，在恶劣撞击时如同铁笼牢牢护住车内乘员，车门在碰撞后依然能正常解锁打开。"
        ),
        technical_principles=[
            "热冲压成形快速水冷模内淬火工艺获得完全致密的马氏体超高强显微晶体组织",
            "A柱、B柱与门槛梁形成全封闭立体闭合传力闭环环状结构（Ring-Shaped Cage Structure）",
        ],
        advantages=[
            "极限抗压变形能力极强：承受数十吨重压与重卡侧撞依然维持乘员舱生存空间完整",
            "顶压与翻滚防护达到中保研与全球五星安全碰撞测试超最高等级优秀评级",
            "碰撞后A柱不弯折、B柱不折断、车门不卡死，为事故后黄金逃生争分夺秒",
        ],
        limitations=[
            "材料硬度极高，后市场普通维修车间无法通过常规电焊切割钣金修复，必须整体总成级更换",
            "热成型钢延展性相对较低，不能用于车头溃缩吸能区，必须与柔性吸能低碳钢分级科学搭配",
        ],
        sub_variants={
            "1500MPa军工级热成型钢": "主流20万级以上车型B柱与前围门槛标配",
            "2000MPa核潜艇级特种热成型钢": "顶级旗舰车型A柱与车门内部防撞梁核心加强件",
        },
        representative_vehicles=["沃尔沃全系(硼钢安全鼻祖)", "问界M9/M7", "理想L系列", "极氪001/009", "蔚来全系", "小米SU7(2000MPa热成型钢)"],
        standard_labels=["热成型钢", "2000MPa", "潜艇级高强钢", "笼式车身", "乘员舱零变形", "五星安全碰撞"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向视家人安全为第一位的客户讲解：‘我们的A柱和B柱采用的是2000兆帕潜艇级热成型硼钢，一平方厘米能扛得住两头成年大象的重量！哪怕在高速上被大货车侧面撞击，车门柱也绝不弯折，死死捍卫车里全家人的生命通道！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 3. 全铝车身与高比例钢铝混合轻量化架构
    TechnologyEntity(
        id="generic_aluminum_steel_hybrid_body",
        name="全铝车身与高比例钢铝混合轻量化架构",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="All-Aluminum & High-Percentage Steel-Aluminum Hybrid Body Architecture",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="车身轻量化技术/材料工程",
        aliases=[
            "全铝车身",
            "钢铝混合车身",
            "轻量化车身",
            "铝合金车身",
            "全铝底盘结构",
            "车身轻量化",
        ],
        summary="在前悬架塔顶、前机舱横梁、四门两盖及底盘摆臂大量采用低密度高韧性航空级铝合金材料，既实现整车减重数百公斤提升纯电续航，又确保前后50:50黄金轴荷比与极致抗腐蚀能力。",
        description=(
            "纯电动车动力电池重量普遍在500-700公斤，如果车身依然采用纯钢，整备质量将突破2.5吨甚至3吨，直接牺牲加速制动性能与电耗续航。"
            "高比例钢铝混合架构巧妙兼顾了钢与铝的物理长处：乘员核心安全舱采用高强度热成型钢保证抗撞刚度；"
            "车头吸能区、四门两盖、前机舱塔顶及前后底盘副车架大量采用6系/7系铝合金锻造铸件，整车减重超150至300公斤，"
            "不仅有效抵消沉重电池包负担，使车身重心更低、过弯反应更灵敏轻巧，且铝合金永不生锈穿孔，整车寿命大幅延长。"
        ),
        technical_principles=[
            "SPR自冲铆接（Self-Piercing Riveting）与FDS流钻螺钉实现异种金属钢铝无缝冷连接",
            "航空级结构胶粘接实现连续胶接缝，隔绝钢铝电化学腐蚀电位差",
        ],
        advantages=[
            "大幅减重150-300公斤：操控轻快灵活如燃油小钢炮，刹车距离显著缩短，电耗更低续航更长",
            "防腐蚀抗氧化能力超强，在沿海高盐雾潮湿环境行驶十年底盘依然光洁如新",
            "实现前后轴50:50完美配重平衡，底盘滤振动作极其干净利落",
        ],
        limitations=[
            "钢铝异种金属连接工艺极其复杂，生产线需配备高精密昂贵的SPR冷铆机器人",
            "铝合金外覆盖件若发生剐蹭凹陷，钣金拉拔修复难度高于普通钢板",
        ],
        sub_variants={
            "高比例钢铝混合架构": "当前业内公认综合性能与维修成本最佳黄金平衡点（铝合金占比50%-75%）",
            "全铝空间框架 (ASF)": "极致轻量化百万级超豪华方案（如早期奥迪A8、捷豹XFL、蔚来ES8一代）",
        },
        representative_vehicles=["蔚来全系(铝合金占比超70%)", "小米SU7", "极氪001", "特斯拉Model S/X", "阿维塔11/12"],
        standard_labels=["钢铝混合车身", "全铝底盘", "轻量化减重", "永不生锈", "50:50配重", "操控灵活敏捷"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向追求驾驶操控和底盘质感的客户介绍：‘我们车在底盘和车身大量使用了航空级铝合金，整整减重了两三百公斤！车身轻了，不仅跑得快刹得住、续航更扎实，过减速带底盘砰砰两声特别紧凑高级，十几年都不会生锈！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 4. 转向与制动全硬件级系统双冗余安全备份
    TechnologyEntity(
        id="generic_dual_source_redundancy_steering_braking",
        name="转向与制动全硬件级系统双冗余安全备份",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Dual-Hardware Redundancy Architecture for Steering & Braking",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="底盘线控安全/高可用架构",
        aliases=[
            "硬件双冗余",
            "双电源冗余",
            "线控双冗余",
            "转向冗余",
            "制动冗余",
            "双备份安全",
        ],
        summary="专为高阶无人自动驾驶正向开发的车规级底层硬件安全架构，在电源供电、通信总线、传感器、转向电机控制器及线控制动系统全链路配备两套互相独立的物理备份。",
        description=(
            "在传统汽车上，如果刹车泵或电瓶发生单点烧毁短路，车辆会瞬间失去转向助力和刹车助力，后果不堪设想；而高阶智驾甚至允许驾驶员脱手脱脚，对单点故障容错率必须为零。"
            "全硬件双冗余系统配备主副两块独立低压蓄电池和双路冗余供电配电网；转向机内置两套独立的六相无刷绕组和两套独立控制器（ECU）；"
            "制动系统由主线控制动（One-Box）与辅助EPB电子驻车稳定系统组成双备份。即使主系统在高速120km/h遭遇雷击、破损或芯片短路彻底瘫痪，"
            "副备份系统在千分之一秒内无感瞬间接管，确保车辆依然具备完整的减速刹车和避险靠边转向能力，万无一失。"
        ),
        technical_principles=[
            "ISO 26262 ASIL-D全生命周期最高安全完整性等级独立双通道异构设计",
            "双路独立环形车规车载以太网与CAN-FD通信总线互为心跳热备份",
        ],
        advantages=[
            "彻底杜绝单点故障风险：即便主电路主电机瞬间烧毁，备份系统无缝接管，车依然能稳稳刹停",
            "高阶城市NOA与无人代客泊车的最强安全基石，给驾驶员最高等级的安全感",
            "双独立蓄电池供电，避免智能座舱大功率用电器瞬间亏电导致整车趴窝断电",
        ],
        limitations=[
            "硬件元器件数量成倍增加，全车线束与控制器物理布置更加紧凑复杂",
            "双冗余硬件采购与研发标定成本显著高于普通单通道传统车型",
        ],
        sub_variants={
            "双电源供电冗余": "主副双12V蓄电池热备份供电",
            "六相分瓣双冗余转向机": "一套电机内集成两套独立三相驱动线圈，坏掉一套仍有一半转向力矩",
        },
        representative_vehicles=["蔚来全系(全栈硬件双冗余)", "小米SU7 Max", "极氪001/007", "极越01", "特斯拉Model S/X(HW3/4双冗余)"],
        standard_labels=["全硬件双冗余", "双电源双备份", "ASIL-D功能安全", "转向不失效", "制动双保险", "零单点故障"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "向最注重极致可靠性的客户说明：‘我们车在底盘上采用的是航空客机级别的双冗余设计！就像飞机有两套发动机两套飞控一样，刹车、转向、电瓶全都有两套独立备份，哪怕在高速路上主系统被外力损坏，备用系统瞬间接管把车安全停好，绝对可靠！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 5. 超长保压远端侧气帘与中央安全气囊
    TechnologyEntity(
        id="generic_multi_chamber_side_curtain_airbag",
        name="超长保压远端侧气帘与中央安全气囊",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Extended-Retention Side Curtain & Far-Side Center Airbags",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="被动安全系统/气囊约束系统",
        aliases=[
            "超长保压气帘",
            "侧气帘",
            "远端气囊",
            "中央气囊",
            "前排中央安全气囊",
            "侧气囊",
        ],
        summary="覆盖前后排整侧车窗的超长一体式侧气帘（保压时间超6秒），结合主副驾之间弹出的前排远端中央气囊，彻底消除侧撞时两名乘客头部激烈相撞与翻滚多次抛出车外的致命伤。",
        description=(
            "在真实翻滚事故中，车辆在地面连续翻滚数圈通常长达5-6秒，传统气囊炸开后0.5秒内立刻泄气瘪掉，导致乘员在后续二次翻滚中头部猛烈撞击车窗甚至被甩出车外。"
            "超长保压侧气帘采用OPW一体织造高气密无缝气袋与高密封冷气冷气气体发生器，爆破展开后在6秒甚至10秒后依然保持80%以上的气压硬度，在连续多次翻滚中持续充当柔软厚实的充气防护墙；"
            "同时，前排主副驾座椅内侧配备‘远端中央气囊’，在侧面受撞瞬间在两人之间极速爆开，彻底阻止主驾与副驾乘员身体甩向中间发生致命的‘头碰头’悲剧。"
        ),
        technical_principles=[
            "OPW（One Piece Woven）一体成型无拼接经纬织造工艺根除接缝漏气",
            "冷气式高压储气罐发生器与双级点火精确泄压微孔控制技术",
        ],
        advantages=[
            "连续翻滚6秒以上持续充气保护，有效防止乘员躯干和头部被甩出车外",
            "前排中央远端气囊填补业内乘员间相互磕碰的被动安全死角",
            "前后排全尺寸贯穿式大面积覆盖，兼顾矮小儿童与身材高大乘员头部防护",
        ],
        limitations=[
            "一体织造高密封气袋与冷气阀门制造成本显著高于传统缝线式普通热气囊",
            "对气囊盖板与顶棚内饰缝线的高低温撕裂弱化线精密激光雕刻工艺要求极高",
        ],
        sub_variants={
            "6秒超长保压贯穿侧气帘": "覆盖A柱到D柱整侧超大面积，主流五星安全标配",
            "前排中央远端安全气囊": "从主驾靠背右侧爆开，隔绝主副驾头部碰撞",
        },
        representative_vehicles=["沃尔沃全系", "理想全系(标配侧气帘及后排防翻滚保护)", "问界M9/M7", "极氪001/009", "蔚来全系标配"],
        standard_labels=["超长保压侧气帘", "6秒保压防翻滚", "远端中央气囊", "防止头碰头", "全车贯穿气帘", "生命守护神"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向家庭用户展示被动气囊细节：‘普通车的侧气帘炸开不到一秒就漏光瘪了，万一发生翻滚根本护不住后排；我们的侧气帘能坚挺保压整整6秒钟以上，像一堵厚实的充气城堡一样死死把全家人护在车内，而且前排中间还会炸出中央气囊防止两个人头撞头，全方位保护每一个家人！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 6. 全速域全场景自动紧急制动系统 (AEB)
    TechnologyEntity(
        id="generic_aeb_automatic_emergency_braking",
        name="全速域全场景自动紧急制动系统 (AEB)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="All-Speed Full-Scenario Autonomous Emergency Braking (AEB)",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="主动安全系统/前向主动避撞",
        aliases=[
            "aeb",
            "自动紧急制动",
            "主动刹车",
            "主动紧急制动",
            "全向防碰撞",
            "cas防碰撞",
        ],
        summary="融合激光雷达、摄像头与毫米波雷达的前向主动安全制动系统，在最高120-135km/h高速工况下对静止故障车、夜间横穿行人、两轮电瓶车及儿童实现稳定刹停避险。",
        description=(
            "高速公路前车急刹或夜间路面突然窜出横穿行人是致命交通事故的高发地带。传统AEB受限于传感器感知极限和刹车建压速度，通常只能在40-60km/h低速起作用，车速稍快就无法刹停只能减轻碰撞。"
            "全场景高阶AEB融合了激光雷达超远测距与线控制动百毫秒瞬时建压，识别速度跨越至120km/h甚至135km/h以上的高速巡航极速；"
            "不仅能精准分辨夜间全黑无灯路段身穿黑衣的行人，还能识别倒地的自行车、倾翻的货车与低矮障碍物，在碰撞发生前数秒自动紧急全力刹死制动，真正化险为夷。"
        ),
        technical_principles=[
            "多传感器时空联合时序滤波与微秒级碰撞时间（TTC - Time to Collision）动态风险预测",
            "线控制动（One-Box）电机毫秒级直推建立100bar极限液压与全车四轮防抱死精细控制",
        ],
        advantages=[
            "刹停速度上限大幅提升：支持最高120-135km/h高速工况稳定刹停静止前车",
            "全天候全光照抗干扰：黑夜、逆光、进出隧道与大雾雨天依然具备坚固的主动防撞制动力",
            "极大削减‘幽灵刹车’虚警率，人机共驾安心从容",
        ],
        limitations=[
            "在冰雪、严重油污等极限超低附着力路面，物理抓地力受到轮胎极限限制，实际刹停距离会延长",
            "驾驶员急打方向盘或深踩油门人工接管时，系统会根据安全逻辑退出或降级以尊重驾驶员最高意图",
        ],
        sub_variants={
            "基础视觉/毫米波AEB": "工作速域中低速（4-60km/h），满足法规基本要求",
            "融合激光雷达全向超高速AEB": "工作速域突破120-135km/h，兼顾后向倒车防撞与横向紧急避让（如华为CAS、小鹏、理想）",
        },
        representative_vehicles=["鸿蒙智行全系(全向防碰撞系统CAS)", "小米SU7", "极氪001/007", "理想L系列", "小鹏G6/G9/X9", "沃尔沃全系"],
        standard_labels=["AEB主动刹车", "全速域防碰撞", "135km/h刹停", "夜间行人避让", "静止车避撞", "救命神盾"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向客户播放权威媒体AEB测试夜间刹停视频：‘您看，在完全没有路灯的深夜高速上以120公里时速飞驰，前面突然出现一辆黑色抛锚静止车，人的肉眼根本来不及反应，但我们的激光雷达AEB提前150米看清并在碰撞前稳稳刹停，这才是真正救命的技术！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 7. 动力电池底护板与多层装甲防碰撞防护梁
    TechnologyEntity(
        id="generic_battery_pack_underbody_armor",
        name="动力电池底护板与多层装甲防碰撞防护梁",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Battery Pack Underbody Armor & Multilayer Anti-Collision Crash Beams",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="电池物理防护/底盘防护",
        aliases=[
            "电池装甲",
            "电池底护板",
            "电池托盘防刮底",
            "高强钢底护板",
            "电池侧向防护梁",
        ],
        summary="由高强度耐磨底板、吸能蜂窝缓冲层、侧面多腔挤压铝合金防撞梁构成的动力电池金钟罩防护系统，抵御车辆托底刮擦、飞石重击与侧面圆柱碰撞电芯侵入。",
        description=(
            "纯电汽车动力电池包挂载于底盘下方，遇到路面凸起大石头、尖锐井盖或野外越野托底飞石刮底时，极易刺穿电池包底部导致电芯破损短路起火。"
            "电池底盘装甲采用三层复合防护结构：底部采用高强抗冲击复合钢板/防弹纤维耐磨底护板（抗冲击能量超1000J），承受坚硬凸起飞石撞击而不破损；"
            "中间铺设航天级蜂窝吸能缓冲减震气凝胶；电池包两侧更嵌有多腔体厚壁挤压铝合金门槛防撞梁（吸能行程达200mm以上），"
            "即便在极端侧向撞击树木或电线杆（侧柱碰）时，侧向防撞梁逐级溃缩吸收海量动能，确保电池电芯舱体零变形、零受挤压破损。"
        ),
        technical_principles=[
            "高延展性铝合金多腔挤压梁与高强度耐磨冲压底护板多级梯度吸能",
            "有限元拓扑碰撞仿真优化电芯模组与外壳侧壁安全防挤压间隙空间",
        ],
        advantages=[
            "极限抗刮底抗托底：路面遭遇坑洼异物尖锐撞击底部，电池外壳坚硬完好绝不漏液",
            "侧向圆柱碰撞（侧柱碰）严苛测试下电芯完全零受压变形，不发生短路自燃",
            "兼顾全天候底盘防泥水、防高浓度融雪剂盐雾飞溅腐蚀",
        ],
        limitations=[
            "多层重型金属底护板与侧防撞梁增加整车自重与离地间隙布局考量",
            "底护板与车体固定点必须采用防锈防疲劳的高强度紧固连接工艺",
        ],
        sub_variants={
            "高强钢冲压防刮底护板": "经典耐磨耐撞击方案，防护硬度高",
            "防弹芳纶纤维与钛合金底护板复合装甲": "极轻量化且防弹级抗穿刺顶级方案（如极氪、特斯拉选装）",
        },
        representative_vehicles=["极氪001/007(九宫格电池防撞梁)", "小米SU7(14层硬核电池防护)", "蔚来全系", "小鹏G9/X9", "比亚迪仰望U8/腾势"],
        standard_labels=["电池底盘装甲", "九宫格防撞梁", "防刮底防托底", "侧柱碰零变形", "电芯金钟罩", "防刺穿"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "蹲下指给客户看底盘防护：‘很多人买电车最怕走烂路刮底盘把电池刮坏起火，您看我们的电池底部配备了超厚特种合金防刮装甲，两侧还有九宫格铝合金吸能大梁，哪怕路面有大石头托底狠撞，电池内部也毫发无损，安心开随便开！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 8. 主动式行人保护弹起机盖系统
    TechnologyEntity(
        id="generic_active_pedestrian_protection_hood",
        name="主动式行人保护弹起机盖系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Active Deployable Pedestrian Protection Hood System",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="被动安全系统/行人碰撞保护",
        aliases=[
            "主动式机盖",
            "行人保护",
            "弹起式机盖",
            "机盖弹起",
            "碰撞弹起发动机盖",
        ],
        summary="在前保险杠布置光纤压力传感器，在车辆不幸撞击行人瞬间火工机构在20-30毫秒内主动将前引擎盖后部向上弹起50-80mm，形成吸能缓冲空间防止行人头部硬磕内部坚硬机件。",
        description=(
            "在人车碰撞事故中，行人被撞飞后头部最容易砸在前挡风玻璃下沿或前机舱盖后部。机舱盖下方紧挨着坚硬的电机、减速箱或前机舱金属支架，头部猛烈撞击极易造成颅骨骨折等致命伤害。"
            "主动式行人保护系统在前杠内部嵌设光纤碰撞压力传感器，精准识别是否撞击了人体腿部（并智能排除撞击雪糕筒或小动物）。"
            "一旦判定撞击行人，后铰链处的微型火药点火膨胀执行器在25毫秒内瞬间将机舱盖后端弹起50至80毫米，在引擎盖与下方坚硬硬构件之间腾出一个充满弹性的“金属气囊软垫空间”，"
            "极大地吸收行人头部撞击冲击力，挽救生命。"
        ),
        technical_principles=[
            "保险杠内置硅胶气压管/光纤应变传感器精准分辨人体腿部冲击波形",
            "微型烟火微爆执行器（Pyrotechnic Actuators）瞬时点火将机盖铰链锁扣解脱并举升顶起",
        ],
        advantages=[
            "大幅降低人车不幸碰撞时行人的致残率与死亡率，欧洲E-NCAP行人保护全项拿满分",
            "在保持轿跑前机舱超低趴流线低风阻造型的同时，兼顾严苛的行人头部安全法规要求",
        ],
        limitations=[
            "火工件触发弹起后不可逆，通常需要更换机盖铰链与点火器总成（部分新型车型支持机械可复位）",
            "若发生低速撞击大型铁桩或特定异物，需精细标定算法以防误弹起增加维修成本",
        ],
        sub_variants={
            "火工微爆弹起机构": "展开响应速度极快（<25ms），业内主流标准配置",
            "电机弹簧机械可逆弹起": "触发后可去售后简易复位恢复，无需报废火工件",
        },
        representative_vehicles=["极氪001/007", "领克08/09", "沃尔沃全系", "奔驰E级/C级", "宝马5系"],
        standard_labels=["主动式机盖", "行人保护", "25毫秒弹起", "欧洲五星安全", "头部缓冲吸能", "生命关怀"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向注重全方位社会责任与五星碰撞的客户介绍：‘真正的豪车不仅保护车里的乘客，连车外的行人也温柔守护；万一发生意外，前机盖会在0.02秒内主动弹起变成一个弹性气垫，最大程度减轻对行人的伤害，这代表了欧洲最顶级的严苛安全标准！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 9. 超低风阻流线外形与空气动力学套件 (Cd < 0.20)
    TechnologyEntity(
        id="generic_low_drag_aerodynamic_design",
        name="超低风阻流线外形与空气动力学套件 (Cd < 0.20)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Ultra-Low Aerodynamic Drag Design & Active Aero Kit (Cd < 0.20)",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="车身空气动力学/低风阻工程",
        aliases=[
            "低风阻",
            "空气动力学",
            "超低风阻",
            "风阻系数",
            "主动进气格栅",
            "隐藏式门把手",
        ],
        summary="通过水滴形流线水滴车身、平整纯平底盘封板、主动进气格栅(AGS)、隐藏式平推门把手及主动电动尾翼，将整车风阻系数压低至0.195-0.21极值，高速电耗大幅削减。",
        description=(
            "在车速达到120km/h时，电动汽车60%至70%的能量都消耗在克服空气阻力上。风阻系数（Cd）每降低0.01，高速纯电续航直接增加10至15公里。"
            "超低风阻工程结合数字CFD超级流体仿真与数十轮全比例风洞吹风实验：采用流畅下压的水滴大溜背曲线、前后轮气帘导流槽消除轮胎空腔乱流、"
            "车头配备主动开闭式进气格栅（高速闭合导流，需要散热时开启）、全车底盘覆盖全平整空气动力学护板以及自动升降的电动升降尾翼，"
            "使空气如丝绸般贴合车身滑过，既大幅增加续航，又让高速行驶下的风噪宛如静止。"
        ),
        technical_principles=[
            "纳维-斯托克斯方程多相流高精度网格空气动力学涡流剥离控制仿真",
            "前后气帘、平整化底盘导流扩散器与车尾截断微下压尾翼的涡流抑制作业",
        ],
        advantages=[
            "高速巡航能效极高：百公里电耗显著降低1-2度电，高速长途续航更真实坚挺",
            "高速风噪被压制到极低分贝，车内静谧性显著优于传统高迎风方正燃油车",
            "高速超车时气流下压力稳定，车辆紧贴地面不发飘",
        ],
        limitations=[
            "极致流线大溜背造型对后排乘客头部垂直空间与后备箱装载纵向容积有一定设计权衡挑战",
            "隐藏式门把手与主动格栅等电动活动部件对冬季破冰防冻有严苛测试要求",
        ],
        sub_variants={
            "主动进气格栅 (AGS)": "根据电机电池温度多挡电机控制百叶窗自适应开合",
            "主动升降电动尾翼": "随车速自动升起提供最高数十公斤空气下压力保证抓地稳定",
        },
        representative_vehicles=["小米SU7(Cd 0.195标杆)", "极氪001/007", "小鹏P7+/G6", "保时捷Taycan", "特斯拉Model 3/S", "理想MEGA(水滴子弹头)"],
        standard_labels=["超低风阻", "Cd 0.195", "主动进气格栅", "纯平底盘封板", "高速超长续航", "主动电动尾翼"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "向追求长续航与轿跑颜值的客户介绍：‘跑车一样的绝美大溜背不只是为了帅，更拥有全球量产车顶尖的超低风阻系数！高速上开得越快越省电，而且高速开起来车身稳如磐石，车里几乎听不到呼呼的风噪！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 10. 超高扭转刚度车身架构 (>40000 N·m/deg)
    TechnologyEntity(
        id="generic_high_rigidity_torsional_body",
        name="超高扭转刚度车身架构 (>40000 N·m/deg)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Ultra-High Torsional Rigidity Body Architecture (>40000 N·m/deg)",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="车身结构工程/抗扭刚度",
        aliases=[
            "扭转刚度",
            "车身扭转刚度",
            "超高刚度车身",
            "抗扭刚度",
            "车身抗扭",
            "40000刚度",
        ],
        summary="车身抵御扭曲变形的物理极限刚度指标突破40000至50000+ N·m/deg，带来赛车级无松散变形的底盘整体感、终身零车身异响以及无惧交叉轴单轮离地的极限通过性。",
        description=(
            "传统燃油车扭转刚度普遍在20000至28000 N·m/deg，开过几年后车身金属疲劳，过减速带或走烂路时内饰到处咯吱咯吱异响，单轮开上马路牙子甚至后备箱关不上。"
            "得益于一体化电池车身（CTB/CTC）与超高强笼式钢铝混合拓扑设计，现代高端纯电架构将车身整车扭转刚度推向了40000至51000 N·m/deg的超跑级殿堂。"
            "车身就像一块整齐密实的整体实心金属块，激烈过弯变道车身跟随速度极快毫无迟滞与扭动，历经数万公里颠簸考验内饰依然严丝合缝、终身零异响，被动碰撞吸能表现亦极度稳定可靠。"
        ),
        technical_principles=[
            "三维闭合力流传导环与多向封闭盒型连续断面闭环结构设计",
            "动力电池壳体作为受力构件融入整车传力拓扑，形成三明治刚度放大效应",
        ],
        advantages=[
            "底盘操控感极其紧致沉稳：方向盘一打车尾立刻精准跟进，毫无大车松散感",
            "彻底杜绝中控台与车门胶条长期异响松散，车身使用十年依然紧实如新",
            "交叉轴单轮悬空或斜坡停车时车门开启顺畅如常，车身毫无扭曲咬死",
        ],
        limitations=[
            "要达到40000以上超高刚度需要精密的有限元断裂力学拓扑计算与昂贵的高强度材料匹配",
            "刚度极高对悬架衬套与减振器的初段细腻滤震标定提出了更高要求",
        ],
        sub_variants={
            "40000+ N·m/deg高级刚度": "豪华主流高端纯电轿车与SUV（如极氪001、问界M9）",
            "50000+ N·m/deg极限超跑刚度": "顶级超跑与极致一体化车身架构（如小米SU7 51000、仰望U8/U9）",
        },
        representative_vehicles=["小米SU7(51000 N·m/deg)", "极氪001(40000 N·m/deg)", "问界M9", "仰望U8/U9", "劳斯莱斯闪灵"],
        standard_labels=["扭转刚度", "50000刚度", "超跑级刚度", "终身零异响", "整车不松散", "操控指哪打哪"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "把车单轮开上高台阶让客户开关后备箱：‘您看，在车轮悬空车身受到最大扭曲力的极限状态下，所有的车门和后备箱依然能轻柔关闭，缝隙毫厘不差！超过40000甚至50000的高刚度让车身坚固得像一块整铁，开上好几年内饰也绝不会咯吱异响！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 11. 预碰撞主动可逆预紧安全带
    TechnologyEntity(
        id="generic_pre_crash_active_tensioning_seatbelt",
        name="预碰撞主动可逆预紧安全带",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Pre-Crash Reversible Active Tensioning Seatbelt System",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="被动安全系统/约束系统",
        aliases=[
            "预紧安全带",
            "主动预紧安全带",
            "可逆安全带",
            "预碰撞安全带",
            "电机预紧安全带",
        ],
        summary="由高扭矩无刷伺服电机驱动的智能安全带，在ADAS传感器探测到紧急碰撞危险瞬间提前快速收紧织带将乘员身体死死绑紧在座椅靠背上，危险解除后自动柔和释放。",
        description=(
            "传统安全带只有机械锁止卡齿，遇到急刹或碰撞时乘员身体会先向前冲出一段距离才被硬性卡住，不仅造成胸口肋骨勒伤，更可能导致头部过早砸向气囊。"
            "可逆电机主动预紧安全带与前向毫米波雷达、激光雷达及急转弯横向G值传感器联动。"
            "当系统预判前车急刹有追尾风险（在碰撞前0.3秒），伺服电机以毫秒级速度强效反转卷簧收紧织带数厘米，消除衣服空隙，提前将乘员牢牢‘焊’在座椅深处；"
            "若成功刹停避险未发生碰撞，电机会悄无声息地反转放松织带恢复舒适松弛；如遇疲劳驾驶，电机还会轻轻连续点动抽动安全带，物理触感温柔唤醒驾驶员。"
        ),
        technical_principles=[
            "电机驱动滚轴微秒级主动正反向无级力矩张力控制与离合脱开机制",
            "与车辆ESP、AEB主动安全预警信号总线极速毫秒级触发联锁控制",
        ],
        advantages=[
            "提前0.3秒消除乘员身体与靠背间隙，乘员碰撞前向位移减少60%以上，大幅减轻颈部与胸腔撞击伤害",
            "完全可逆重复使用：急刹避险后自动松开，无需去4S店报废更换安全带总成",
            "支持疲劳触感轻拉提醒、激烈过弯主动收紧夹紧，兼顾运动操控与日常舒适",
        ],
        limitations=[
            "相比传统纯机械弹簧安全带卷收器成本高出数倍，线束与微电控更为复杂",
            "电机收紧力度需多段柔性曲线调校，避免对孕妇或儿童产生突兀勒压不适感",
        ],
        sub_variants={
            "主动双向预紧式安全带": "电机提前预紧 + 碰撞瞬间火药微爆终极锁止双重双保险",
        },
        representative_vehicles=["奔驰S级/E级(PRE-SAFE系统)", "极氪001/007", "问界M9", "蔚来ET7/ES8", "小米SU7 Max"],
        standard_labels=["主动预紧安全带", "可逆电机收紧", "提前0.3秒束缚", "防肋骨勒伤", "防疲劳触感拉扯", "豪华车标配"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "现场带客户体验一脚急刹：‘您感觉到了吗？在刹车踩下的瞬间安全带立刻主动有力地把您向后拉进座椅里，身体完全没有向前栽倒，危险过去后又轻轻松开，这才是顶级豪华车才有的主动安全关怀！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 12. 高压电气毫秒级碰撞主动断电保护与火工熔断器 (Pyrofuse)
    TechnologyEntity(
        id="generic_high_voltage_electrical_pyrofuse_cut",
        name="高压电气毫秒级碰撞主动断电保护与火工熔断器 (Pyrofuse)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Millisecond Pyrofuse High-Voltage Disconnect & Crash Safety Protection",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="高压电气安全/防触电起火",
        aliases=[
            "火工开关",
            "碰撞断高压",
            "pyrofuse",
            "高压秒断",
            "毫秒级断电",
            "碰撞主动断电",
        ],
        summary="在碰撞气囊点火信号触发的瞬间（<2毫秒），通过微型火药微爆机械斩断高压铜排母线，并在毫秒级完成电机逆变器残余高压电容泄放，彻底杜绝短路起火与触电风险。",
        description=(
            "电动汽车工作在400V甚至800V致命超高压下，一旦发生剧烈碰撞导致高压电缆破损金属裸露碰触车身铁皮，可能引发巨大电弧火花引燃内饰，更会让救援人员面临触电致命危险。"
            "火工熔断器（Pyrofuse）串联在动力电池高压总回路正负极总线上。在安全气囊碰撞传感器检测到剧烈碰撞信号的千分之一秒内，微型火药瞬间爆炸，"
            "驱动绝缘耐火活塞像高速铡刀一样硬生生将粗壮的高压铜排斩断并推入物理绝缘盲端，彻底切断电池包与整车的高压电气物理连接；"
            "同时逆变器主电容通过专用放电回路在3秒内将残余电压安全泄放至60V安全电压以下，确保事故现场绝对无电弧、无触电、救援无顾忌。"
        ),
        technical_principles=[
            "微型烟火药剂纳秒级引爆产生超高气体冲击压推断特种铜排（斩断时间<2ms）",
            "主电机逆变器主动高频PWM短路快速主动放电技术（Active Discharge）",
        ],
        advantages=[
            "断电速度极快（2毫秒内物理断开），彻底杜绝剧烈车祸后高压电弧引燃燃油或内饰",
            "事故后整车外壳无残留漏电电压，消防人员与急救人员可立即无顾虑剪切破拆救人",
            "与传统慢速电磁继电器相比，不会因为触点大电流熔焊粘连而导致断不开电",
        ],
        limitations=[
            "火工斩断属于不可逆硬件动作，事故触发后需回厂更换高压配电盒内的火工熔断开关模块",
            "对传感器防误爆误触发诊断逻辑有严谨的逻辑互锁校验要求",
        ],
        sub_variants={
            "单向火工熔断器": "单极切断高压回路",
            "双极全切断火工开关": "正极与负极双回路同时微爆物理隔离，安全性拉满（如保时捷Taycan、特斯拉、蔚来）",
        },
        representative_vehicles=["特斯拉全系", "保时捷Taycan", "蔚来全系", "理想全系", "极氪001/007", "小米SU7"],
        standard_labels=["火工断电", "Pyrofuse", "2毫秒断高压", "防撞击起火", "快速残压泄放", "营救安全兜底"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向担心电车碰撞漏电起火的客户剖析底层安全：‘只要车子检测到发生撞击，气囊爆开的同一毫秒内，电池内部的火药开关就会像闸刀一样硬生生把高压电线炸断，整辆车的高压电瞬间归零，既绝不起火花也不漏电，给全家人最高级别的安全铠甲！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 13. A/B柱热气胀成型与复合防侵入结构
    TechnologyEntity(
        id="generic_a_b_pillar_composite_reinforcement",
        name="A/B柱热气胀成型与复合防侵入结构",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Hydroformed / Gas-Formed & Composite Reinforced A/B Pillar Anti-Intrusion Structure",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="车身先进制造/结构防侵入",
        aliases=[
            "a柱热成型",
            "b柱复合材料",
            "防侵入b柱",
            "热气胀成型",
            "高强a柱",
            "高强b柱",
        ],
        summary="在狭窄的A柱与B柱内部采用中空管件高压热气胀成型工艺，或嵌入碳纤维复合材料增强筋，大幅提升截面模量与抗弯折抗侵入能力，碰撞时死保驾驶员头部生存空间。",
        description=(
            "在小偏置25%碰撞（车头一角蹭撞壁障）或重型SUV侧撞B柱事故中，车柱极易发生中间折曲断裂，导致车顶塌陷或车轮直接顶进驾驶舱切断驾驶员双腿。"
            "新一代A/B柱复合结构摒弃了传统数张平整钢板简单贴合焊接的老工艺，采用超高压高温热气胀成型技术（THF/Hydroforming），"
            "将高强钢中空无缝钢管通过内部上千个大气压的气体胀形为复杂的闭合变截面整体管梁，或者在B柱内腔灌注高强度吸能发泡结构胶与碳纤维增强嵌件；"
            "在碰撞瞬间形成超强抗弯截面支撑力，即使面对猛烈斜向削头撞击，车柱依然如定海神针般挺立不倒。"
        ),
        technical_principles=[
            "超高压气体在模内对高温合金管坯进行内部膨胀成形，制备高惯性矩无缝闭口薄壁截面",
            "碳纤维/玻纤热固性复合材料增强筋板与高附着力环氧结构发泡胶常温膨胀固化",
        ],
        advantages=[
            "抗弯刚度相比传统单片拼焊柱提升50%以上，25%小偏置碰撞A柱毫无弯折断裂",
            "大幅减小A柱盲区横向厚度，在保障潜水艇级刚度的同时让驾驶员转弯视野更开阔",
            "全方位防范侧面SUV保险杠高度侵入，保障乘员头部和胸腔绝对生存空间",
        ],
        limitations=[
            "管件高压热气胀成型设备精密复杂，成形节拍速度相比冲压略微偏长",
            "碳纤维复合增强件生产成本较高，目前主要应用于中高端旗舰车型",
        ],
        sub_variants={
            "热气胀中空一体A柱管梁": "超细A柱视野与超强抗折断平衡（如本田极氪部分旗舰车型）",
            "钢铝碳纤维多材料复合B柱": "宝马Carbon Core碳纤维核心与极氪车身防撞加强梁",
        },
        representative_vehicles=["极氪001/009", "宝马7系/i7(Carbon Core)", "问界M9", "沃尔沃XC90", "蔚来ET7/ET9"],
        standard_labels=["A柱防弯折", "B柱防侵入", "热气胀成型", "碳纤维复合筋", "25%偏置碰撞通关", "超强视野"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向重视被动碰撞碰撞评测的客户说明：‘我们车的A柱内部隐藏着超高强度的中空整体膨胀管梁，甚至加入了碳纤维增强结构！正面以最严苛的小角度撞击水泥墩，A柱不仅绝不弯折，而且车门依然能轻松拉开逃生，安全级别无懈可击！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 14. 全车双层夹胶声学隔音防紫外线玻璃
    TechnologyEntity(
        id="generic_acoustic_laminated_double_glass",
        name="全车双层夹胶声学隔音防紫外线玻璃",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="All-Around Acoustic Laminated Double-Glazed UV-Protection Glass",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="座舱隔音舒适与安全/车窗玻璃科技",
        aliases=[
            "双层夹胶玻璃",
            "声学隔音玻璃",
            "隔音玻璃",
            "夹胶玻璃",
            "双层隔音玻璃",
        ],
        summary="在全车前风挡、四门车窗甚至后三角窗全系采用两层钢化/半钢化玻璃夹嵌0.76mm专用声学PVB阻尼树脂薄膜，不仅中高频外界噪音隔绝率提升数倍，更杜绝事故飞石击穿与玻璃飞溅割伤。",
        description=(
            "普通单层钢化玻璃受到撞击时会瞬间碎成无数尖锐小颗粒飞溅，划伤乘客面部，且对外界呼啸的高速风噪和货车喇叭声隔绝能力微弱。"
            "双层夹胶声学玻璃由两块汽车浮法玻璃在高温高压灭菌釜中紧紧复合一层声学高分子PVB/EVA阻尼胶膜。"
            "中间的树脂层能够吸收高频声波振动能量，使高速120km/h巡航下的风噪降低3至5分贝；"
            "更重要的是安全防护价值：即便遭遇重锤击打、高速飞石或侧面撞击翻滚，玻璃即使产生蛛网裂纹依然被胶膜死死粘连在一起，绝不穿透、绝不脱落飞溅，有效防盗抢防甩出。"
        ),
        technical_principles=[
            "多层声学高分子阻尼树脂薄膜剪切粘弹性形变耗散高频声能波",
            "PVB内夹胶层吸收99%以上UVA/UVB有害紫外线光谱波段",
        ],
        advantages=[
            "图书馆级静谧：显著隔绝外界大货车噪音、施工喧嚣与高速呼啸风噪",
            "防飞石防穿透极高安全性：破损后整体粘连不飞溅，防止碎玻璃划伤乘员眼睛与面部",
            "99%隔绝紫外线，防止夏季烈日手臂被晒黑晒伤，保护内饰真皮仪表不老化开裂",
        ],
        limitations=[
            "全车四门夹胶玻璃比普通单层玻璃厚度和重量略有增加（门板电机升降扭矩要求更高）",
            "玻璃边缘加工封边防水工艺若不良可能随长期雨水渗透产生局部微小起雾脱胶",
        ],
        sub_variants={
            "全车四门双层夹胶隔音玻璃": "主流20万级以上高品质旗舰车型标配方案",
            "前风挡双层镀银隔热夹胶玻璃": "在隔音基础上增加多层真空磁控溅射金属银纳米涂层，阻隔红外热量",
        },
        representative_vehicles=["理想L系列(全系标配四门双层夹胶)", "小米SU7", "极氪001/007", "小鹏G9/X9", "问界M9/M7", "蔚来全系"],
        standard_labels=["双层夹胶玻璃", "声学隔音", "防碎裂飞溅", "隔绝99%紫外线", "高速静谧无声", "静音座舱标配"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "带客户敲击车窗玻璃并升降感受：‘很多合资车只有前挡风是夹胶的，后排为了省钱用单层薄玻璃；我们全车前后四门全部标配双层夹胶声学玻璃，车门一关窗户一升，外界车水马龙立刻按下了静音键，而且哪怕遭遇石头猛砸，玻璃也绝不会破裂飞溅伤人！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 15. 健康环保座舱低VOC环保材质与空气净化体系
    TechnologyEntity(
        id="generic_cabin_eco_friendly_low_voc_materials",
        name="健康环保座舱低VOC环保材质与空气净化体系",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Eco-Friendly Low-VOC Cabin Materials & Comprehensive Air Purification System",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="座舱健康与环保材料/空气治理",
        aliases=[
            "低voc",
            "环保座舱",
            "无异味座舱",
            "母婴级健康座舱",
            "水性皮革",
            "车载空气净化",
        ],
        summary="从源头杜绝传统沥青阻尼片与劣质胶水，全车采用水性环保皮革、母婴级健康织物及CN95+等离子主动空气杀菌净化系统，实现新车暴晒提车依然‘零异味、零甲醛’。",
        description=(
            "传统新车提车时车内往往刺鼻难闻，烈日暴晒后甲醛、苯等挥发性有机化合物（VOC）浓度更是超标数十倍，严重危及孕妇、婴儿与过敏体质人群健康。"
            "健康环保座舱从材料最源头进行无毒重塑：以食品级低气味发泡材料、水性环保合成PU皮革、水性超纤绒及无毒水性热熔胶彻底淘汰传统含沥青、苯类溶剂的有毒材料；"
            "车内更配备激光PM2.5传感器、微米级CN95空气滤芯、负离子发生器与紫外光等离子主动杀菌模块，"
            "夏天通过手机App远程提前开启‘座舱智能换气与暴晒排毒’，开门上车空气清新如雨后森林，达到中汽研‘母婴级健康座舱’认证。"
        ),
        technical_principles=[
            "水性聚氨酯树脂（Waterborne PU）无有机溶剂乳化合成聚合反应",
            "CN95熔喷静电驻极滤芯物理拦截配合双极电晕放电产生高浓度活性负氧离子",
        ],
        advantages=[
            "提车当天即可放心带刚出生的婴儿和孕妇乘坐，彻底告别炭包除甲醛的漫长等待",
            "即便在夏天户外40℃高温烈日暴晒一整天，开门进车依然毫无呛人刺鼻异味",
            "主动过滤99%以上花粉、飞絮及微小病菌气溶胶，对鼻炎与易过敏人群极度友好",
        ],
        limitations=[
            "环保水性发泡与水性合成面料的采购成本显著高于传统溶剂型廉价皮革",
            "车规级CN95复合空调滤芯需定期（如每半年至一年）更换维护以保证最佳净化拦截效率",
        ],
        sub_variants={
            "水性环保生物基皮革": "触感温润亲肤，VOC释放量接近于零",
            "智能远程高温自洁与等离子净化系统": "停车暴晒时自动监测车内空气并定时通风换气排毒",
        },
        representative_vehicles=["沃尔沃全系(鼻子小组环保鼻祖)", "理想全系(全车标配母婴级认证面料)", "问界M9", "极氪001/007", "蔚来全系"],
        standard_labels=["母婴级健康座舱", "零甲醛零异味", "低VOC环保材质", "CN95空气净化", "夏天暴晒无异味", "守护全家健康"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "邀请刚有宝宝或准备备孕的夫妻客户深呼吸闻车内空气：‘很多新车一进门熏得眼睛疼嗓子痒，我们全车从源头就坚决不用一滴劣质胶水和有毒沥青，采用母婴级环保面料，新车到手零甲醛、零异味，孕妇和刚满月的宝宝坐进来完全不用担心健康！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 16. 前机舱三段式碰撞溃缩吸能传力路径
    TechnologyEntity(
        id="generic_three_point_load_path_subframe",
        name="前机舱三段式碰撞溃缩吸能传力路径",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Three-Load-Path Front Structure & Controlled Crash Energy Absorption",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="车身结构工程/碰撞力学传导",
        aliases=[
            "碰撞传力路径",
            "吸能溃缩",
            "三段式吸能",
            "吸能盒",
            "传力结构",
            "副车架脱落",
        ],
        summary="在前机舱设计上纵梁、下纵梁及副车架三条独立的闭环吸能传力骨架，并在遭遇剧烈撞击时通过前副车架主动脱落下沉机制，避免沉重的动力前总成挤压侵入乘员舱。",
        description=(
            "在高速正面强烈碰撞中，如果车头吸能结构单一，冲击力会直接穿透机舱撞向驾驶员双腿。纯电动车前机舱虽然没有发动机，但同样布置了前置电驱动总成、制动泵与热管理阀组。"
            "三段式碰撞传力结构将前机舱撞击力合理分流到三条主通道：上通道引导至A柱下三角区与车门上梁；中通道由超大截面主纵梁吸能盒风琴式折叠吸能；下通道引导至坚固的前副车架并传递至车底中央通道与两侧门槛梁。"
            "同时前副车架固定螺栓采用剪切断裂溃缩设计，遭遇大撞击瞬间螺栓主动切断，前电机整体向下方地面脱落下沉，绝不向后侵入驾驶员腿部空间。"
        ),
        technical_principles=[
            "薄壁高强钢/挤压铝吸能盒风琴式渐进压溃折叠（Progressive Buckling）力学设计",
            "前悬架副车架可剪切断裂螺栓受控失效下沉导向斜面拓扑结构",
        ],
        advantages=[
            "梯度渐进式溃缩吸收80%以上撞击动能，极大降低传递到车内乘员身体的瞬间加速度峰值（降G值）",
            "前电机受控主动脱落下沉，杜绝前驱动总成破壁侵入座舱切伤挤压前排乘员双腿",
            "小碰撞时仅损坏最前端独立螺栓连接吸能盒，维修无需切大梁，大幅降低出险理赔成本",
        ],
        limitations=[
            "机舱多路径拓扑传力设计极其考验超级计算机非线性有限元仿真计算与实车碰撞试验验证",
            "前机舱各零部件支架必须严格按照碰撞脱开路径避让布置，空间利用率规划要求极高",
        ],
        sub_variants={
            "三传力路径前舱结构": "上、中、下三层独立连续封闭传力通道",
            "副车架碰撞主动下沉导向机构": "大冲击下受力螺栓剪切，电机顺着斜滑块向底盘下方滑移",
        },
        representative_vehicles=["理想全系(前机舱三路径吸能+副车架下沉)", "极氪001/007", "小米SU7", "问界M9", "沃尔沃全系"],
        standard_labels=["三段式吸能", "碰撞传力路径", "副车架主动下沉", "风琴式吸能盒", "防电机侵入腿部", "吸能保乘员"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向注重被动安全的客户深入讲解车身工程：‘车头撞烂并不代表车不结实，关键是能不能吸走能量保住人！我们的车头有三层吸能大梁像风琴一样逐级折叠吸收撞击力，而且遇到极端大车祸，前面的电机还会自动往地上掉，绝不会被撞进车里挤伤您的双腿！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
    # 17. 隐藏式门把手断电机械联动应急开门机构
    TechnologyEntity(
        id="generic_door_hidden_safety_emergency_unlock",
        name="隐藏式门把手断电机械联动应急开门机构",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Hidden Door Handle Mechanical Linkage & Power-Loss Emergency Ejection System",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="车门安全结构/事故逃生冗余",
        aliases=[
            "隐藏式门把手应急解锁",
            "机械应急拉手",
            "断电开门",
            "门把手自动弹出",
            "双重应急解锁",
        ],
        summary="针对隐藏式电动门把手在车辆碰撞起火断电后无法弹开的致命痛点正向研发的软硬件安全逃生系统，配备碰撞高压毫秒级自动解锁弹出、微秒超级电容储能及车门内外纯机械物理连杆开门机构。",
        description=(
            "隐藏式电动门把手因降低风阻和造型美观被广泛采用，但若遭遇严重车祸整车断电，门把手若无法弹开，车外救援人员和路人无法拉开车门，车内乘客可能错失逃生黄金时间。"
            "新一代安全隐藏式门把手配备三层安全冗余：第一层，安全气囊爆开瞬间由独立备用超级电容毫秒级驱动全车四门电动锁止机构自动全解锁并将外门把手强力弹开；"
            "第二层，外门把手保留纯物理机械按压翘起结构（即便彻底断电，用力按压前端即可机械翘起后端拉开）；"
            "第三层，车内前后门板均设计有醒目的纯机械物理拉索手柄，轻轻一拉即可直接通过钢丝拉索硬性解开机械门锁，无论断电、泡水还是极端侧撞均能秒级开门逃生。"
        ),
        technical_principles=[
            "独立后备超级电容（Supercapacitor）事故高压断电毫秒级自主持续供电释放",
            "车内车外纯机械钢丝拉索与摇臂机构并联跨接电子微动开关，实现电控与机械双解耦",
        ],
        advantages=[
            "彻底破解电动车事故‘断电锁死打不开门’的行业致命安全焦虑",
            "车内车外双向纯机械物理开门保障，断电、泡水、落水无感逃生自救",
            "门锁系统满足全球最严苛的事故后救援人员徒手开门法规测试",
        ],
        limitations=[
            "每个车门需额外布置独立机械拉索、摇臂与后备储能电容，增加了门板内部重量与结构复杂度",
            "需要向初次购车车主进行车内物理应急拉手位置的交车科普演示",
        ],
        sub_variants={
            "半隐藏式物理门把手": "保留外把手下方物理按键与微凹槽机械拉手，天然防夹手防断电（如小米SU7、极氪007部分）",
            "全隐藏式电动弹出+内外双机械拉索": "兼顾极致纯平流线与物理连杆终极逃生兜底",
        },
        representative_vehicles=["小米SU7(半隐藏式安全门把手)", "极氪001/007", "理想L系列", "小鹏G9/X9", "蔚来全系"],
        standard_labels=["隐藏门把手安全", "断电自动弹出", "内外双机械拉手", "超级电容后备电源", "事故黄金逃生", "零锁死隐患"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "现场拉动车内物理拉索与车外把手给客户演示：‘很多客户担心隐藏门把手车祸断电打不开门，您看我们的车，即便彻底拔掉电瓶断电，在车外按一下依然能机械拉开，车内门把手下方更有专用的机械拉索，一拉立刻开门，无论遇到什么极端情况都能秒级开门逃生，安全第一！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="车身安全",
    ),
]

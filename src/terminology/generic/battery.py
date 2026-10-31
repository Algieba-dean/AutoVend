"""
Generic Battery & Electrical Technical Terminology (src/terminology/generic/battery.py).
Contains 17 comprehensive generic battery technologies (category="电池形态").
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

GENERIC_BATTERY_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 三元锂动力电池 (Original)
    TechnologyEntity(
        id="generic_ternary_lithium_battery",
        name="三元锂动力电池",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Ternary Lithium-ion Battery (NMC/NCA)",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="动力电池/正极材料化学体系",
        aliases=[
            "三元锂",
            "三元锂电池",
            "nmc电池",
            "ncm电池",
            "高镍三元锂",
            "三元锂电芯",
            "ternary lithium",
        ],
        summary="采用镍钴锰（NCM）或镍钴铝（NCA）作为正极材料的动力电池，能量密度极高、放电倍率强劲且低温续航达成率高，是中高端长续航纯电车首选。",
        description=(
            "三元锂电池具有单体能量密度高（可达250-300Wh/kg以上）、充放电电压平台高、高低温适应性能均衡的特点。"
            "在我国北方严寒冬季（-20℃），三元锂电池活性与放电容量衰减显著低于磷酸铁锂；但在受到极端热冲击或机械穿刺时，三元锂热失控释放氧气自燃的温度较磷酸铁锂低，依赖高级BMS与热阻隔防护。"
        ),
        technical_principles=[
            "层状氧化物镍钴锰固溶体电极储锂反应，高镍提供高容量，钴稳定结构，锰保障安全",
            "高导电电解液与快充石墨/硅碳负极体系",
        ],
        advantages=[
            "能量密度高，同等电池包重量和体积下能塞入更大度数，实现700-1000km超长续航",
            "冬季低温耐寒性能好，北方冰雪天气续航衰减明显优于磷酸铁锂",
            "瞬间放电功率大，支持超跑级3秒甚至2秒内零百弹射起步",
        ],
        limitations=[
            "正极材料使用镍、钴等贵金属，成本和售价高于磷酸铁锂",
            "热失控分解温度约200℃，对电池包被动安全结构与液冷温控要求极严苛",
        ],
        sub_variants={
            "NCM523 / NCM622": "中镍三元，热稳定性与成本平衡",
            "NCM811 / 超高镍": "高镍高能量密度体系，主打800km+极限续航与轻量化",
        },
        representative_vehicles=["小米SU7 Max", "极氪001超长续航版", "特斯拉Model Y长续航版", "蔚来100kWh版", "保时捷Taycan"],
        standard_labels=["三元锂电池", "高能量密度", "超长续航", "低温抗寒", "高性能放电"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "北方寒冷地区或经常跑长途跨省的客户，首推三元锂版本：冬天电量更扎实耐用，夏天跑高速掉电更慢；",
            "追求极致加速和顶配体验的客户，说明三元锂放电倍率高，能发挥双电机超千匹马力的巅峰性能。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 2. 磷酸铁锂动力电池 (Original)
    TechnologyEntity(
        id="generic_lfp_battery",
        name="磷酸铁锂动力电池",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Lithium Iron Phosphate Battery (LFP)",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="动力电池/正极材料化学体系",
        aliases=[
            "磷酸铁锂",
            "铁锂",
            "磷酸铁锂电池",
            "lfp",
            "lfp电池",
            "铁锂电池",
            "刀片铁锂",
            "金砖铁锂",
        ],
        summary="采用橄榄石结构磷酸铁锂作为正极材料的电池，热稳定性超高（不起火爆燃）、循环充放电寿命极长、不含稀缺贵金属，安全经济与日常耐用性极佳。",
        description=(
            "磷酸铁锂电池（LFP）正极P-O共价键极其牢固，在500-800℃高温下也不会分解释放氧气，从化学本质上彻底杜绝了剧烈爆燃危险。"
            "同时其循环充放电寿命通常可达3000-5000次以上，日常可随意充满至100%而不会损伤电芯健康度；弱点在于质量能量密度略低，且-10℃以下低温容量衰减较快。"
        ),
        technical_principles=[
            "橄榄石晶体结构提供稳固三维骨架，防止高充放电深度下的晶格塌陷",
            "低阻抗碳包覆纳米级正极颗粒技术配合宽温区导电电解液",
        ],
        advantages=[
            "极致安全：针刺、挤压、过充均不起火不爆炸，热失控自燃风险极低",
            "超长循环寿命：正常家用车开10年以上电池健康度依然饱满",
            "日常充电无顾虑：支持频繁充满至100%而无过充析锂受损风险，成本更亲民",
        ],
        limitations=[
            "低温环境充放电活性下降，北方严寒冬季续航达成率偏低",
            "电压放电曲线过于平缓，SOC剩余电量算法估算难度大，需定期满充校准",
        ],
        sub_variants={
            "传统LFP电芯": "标准方壳/软包铁锂",
            "磷酸锰铁锂 (LMFP)": "掺杂锰元素提升单体工作电压，兼顾铁锂安全与近三元能量密度",
        },
        representative_vehicles=["比亚迪全系刀片电池车型(汉/海豹/秦PLUS)", "特斯拉Model Y标准续航", "极氪007(金砖电池)", "小米SU7标准版"],
        standard_labels=["磷酸铁锂", "LFP", "高安全性", "长循环寿命", "耐过充", "高性价比"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "面对最在乎电池自燃安全和使用寿命的家庭客户，重点介绍铁锂‘针刺不起火、怎么用都不怕坏’的踏实安全感；",
            "日常城市代步客户推荐铁锂：充电桩随便插、天天充到100%也不伤电池，且车价便宜好几万，经济实惠。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 3. 半固态与全固态动力电池 (Original)
    TechnologyEntity(
        id="generic_solid_state_battery",
        name="半固态与全固态动力电池",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Semi-Solid & All-Solid-State Battery",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="前沿动力电池/固态电解质技术",
        aliases=[
            "半固态电池",
            "固态电池",
            "全固态电池",
            "固态锂电池",
            "半固态",
            "固态电解质",
            "solid-state battery",
        ],
        summary="使用固态聚合物/氧化物/硫化物电解质取代易燃液态电解液的下一代动力电池，能量密度跨越至360-500Wh/kg，无漏液不起火，实现1000km+超长续航。",
        description=(
            "固态电池（Solid-State Battery）是全球公认的终极动力电池方向。半固态电池保留约5%-10%浸润液态电解质作为过渡量产方案，"
            "全固态电池完全取消液态溶剂。固态电解质具备不可燃、耐高温、机械强度高等特性，能够安全匹配金属锂负极和超高镍高压正极，"
            "彻底解决液态电池热失控起火与能量密度瓶颈，但在常温离子电导率与界面阻抗上仍处在产业化攻坚阶段。"
        ),
        technical_principles=[
            "固态电解质（聚合物/氧化物陶瓷/硫化物微晶）传导锂离子，彻底隔绝枝晶穿刺与短路",
            "高活性金属锂或纳米硅碳复合负极大幅缩减体积与重量",
        ],
        advantages=[
            "超高能量密度：360~500Wh/kg，乘用车轻松实现1000公里至1200公里真实续航",
            "本质极高安全：耐高温撞击穿刺，彻底消除易燃有机液体电解质起火风险",
            "工作温区极宽：低温环境下依然保持极佳导电性与续航达成率",
        ],
        limitations=[
            "制造工艺极其精密苛刻，当前处于规模化量产初期，成本昂贵",
            "全固态电池界面阻抗与快充循环寿命仍需时间走向全面普惠",
        ],
        sub_variants={
            "半固态电池 (凝胶/混合固液)": "已实现小批量量产上车装配（如蔚来150kWh包、智己光年固态电池）",
            "全固态电池": "0液态成分，预计2026-2028年逐步实现工业级规模量产示范",
        },
        representative_vehicles=["蔚来ET7(150kWh半固态电池)", "智己L6(第一代光年固态电池)"],
        standard_labels=["固态电池", "半固态电池", "1000km续航", "固态电解质", "本质安全", "高能量密度"],
        equivalence_group_id=EquivalenceDomain.SOLID_STATE_BATTERY_TECH,
        sales_talking_points=[
            "向追求科技最前沿、想要‘千公里续航且完全不担心自燃’的高端先锋客户，介绍半固态电池的划时代意义；",
            "客观向客户说明当前已落地的半固态电池多作为顶配或选装租赁方案，享受第一波前沿科技红利。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 4. CTB 电池车身一体化技术 (Original)
    TechnologyEntity(
        id="generic_ctb_technology",
        name="CTB电池车身一体化技术",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Cell-to-Body (CTB) Integrated Battery Structure",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="电池成组结构/车身集成",
        aliases=[
            "ctb",
            "ctb技术",
            "电池车身一体化",
            "cell to body",
            "ctb电池",
            "电池车身集成",
        ],
        summary="将电池包上盖与车身地板合二为一的结构创新，电池不仅是储能装置更是整车高刚度骨架，整车抗扭刚度跃升至40000+ N·m/deg，并极大释放乘员舱垂直头部空间。",
        description=(
            "CTB（Cell to Body）技术将动力电池电芯、托盘、上盖与下车体地板深度融合为类蜂窝三明治受力体。"
            "相比传统先将电芯做成模组、再做成电池包、再螺栓挂载到底盘下方的做法，CTB省去了车身地板层与电池上壳体两层冗余结构，"
            "电池包直接作为底盘传力结构的一部分参与正面与侧面碰撞吸能，大幅优化整车Z向垂直高度与轻量化表现。"
        ),
        technical_principles=[
            "类蜂窝三明治高强度仿生力学拓扑设计",
            "电池上盖作为乘员舱地板，密封胶与高强度结构胶粘接实现密封与结构双重承载",
        ],
        advantages=[
            "整车扭转刚度成倍增长（突破40000 N·m/deg），激烈驾驶底盘极其扎实一体",
            "乘员舱垂直Z向厚度节省10-15mm，纯电轿车坐姿不再高耸，头部空间显著宽敞",
            "碰撞吸能路径多维分散，侧柱碰安全防护能力质的飞跃",
        ],
        limitations=[
            "电池包与车身高度集成，售后维修如果单体电芯故障需专用开盖工位或整包更换",
            "对车身装配工艺与全密封涂胶质量要求极高",
        ],
        sub_variants={
            "CTB (比亚迪方案)": "基于刀片电池长电芯充当高强度横梁与车身结合",
            "CTB (小米倒置电芯方案)": "电芯倒置+双大面泄压阀+车身地板集成",
        },
        representative_vehicles=["比亚迪海豹", "比亚迪海狮07", "小米SU7", "腾势Z9GT"],
        standard_labels=["CTB", "电池车身一体化", "高抗扭刚度", "Z向空间优化", "三明治受力结构"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向担心纯电轿车‘坐姿像踩小板凳、顶头压抑’的客户展示：CTB把电池盖做成地板，坐姿低矮舒展，头部宽裕；",
            "向看重安全和操控的客户强调：CTB让车身抗扭刚度比肩百万级豪华超跑，过减速带整体性极强，绝无松散异响。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 5. CTC 电池底盘一体化技术 (Original)
    TechnologyEntity(
        id="generic_ctc_technology",
        name="CTC电池底盘一体化技术",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Cell-to-Chassis (CTC) Integrated Architecture",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="电池成组结构/底盘一体化",
        aliases=[
            "ctc",
            "ctc技术",
            "电池底盘一体化",
            "cell to chassis",
            "ctc电池",
            "底盘集成电芯",
        ],
        summary="将电芯直接集成在车辆底盘下车体纵横梁内部的极致集成方案，完全取消电池包壳体和独立托盘，实现底盘轻量化与空间利用率的最大化。",
        description=(
            "CTC（Cell to Chassis）将电池完全融合为汽车底盘的基础结构件。下车体不仅是悬架和传动系统的载体，其下部箱体即为电池电芯布置腔体。"
            "电芯直接涂胶固定在底盘纵梁之间，前后连接一体化压铸车身。相比CTB（电池与车身集成），CTC将下车体底盘与电池彻底同构，零件减少数百个，整车重量大幅降低。"
        ),
        technical_principles=[
            "下车体底盘承载骨架与电池模组箱体完全同构熔接",
            "底盘空间利用率从传统40%~50%提升至70%以上",
        ],
        advantages=[
            "减少大量壳体和螺栓紧固件，极致减重，提升整车续航里程",
            "提升整车制造自动化率与总装节拍，降低整车制造成本",
        ],
        limitations=[
            "底盘与电池密不可分，底盘托底严重碰撞若伤及底板维修成本极高",
            "电芯单体可拆卸维护性几乎为零",
        ],
        sub_variants={
            "特斯拉CTC": "4680电芯+前后一体压铸+座椅直接固定在电池上盖",
            "零跑CTC": "国内率先量产量无独立电池包下车体方案",
        },
        representative_vehicles=["特斯拉Model Y (4680奥斯汀版)", "零跑C01/C10"],
        standard_labels=["CTC", "电池底盘一体化", "极致轻量化", "空间最大化", "集成化制造"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "对比传统油改电平台，CTC是纯电正向研发的代表作：没有冗余电池铁壳子，车重轻能耗低，续航更实惠；",
            "向追求科技感的客户展示特斯拉与行业最新制造趋势：座椅直接安装在电池结构上，集成度登峰造极。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 6. 4680 大圆柱电池 (Original)
    TechnologyEntity(
        id="generic_4680_cylindrical_cell",
        name="4680大圆柱电池",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="4680 Large Cylindrical Battery Cell",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="动力电池/电芯物理形态",
        aliases=[
            "4680大圆柱",
            "大圆柱电池",
            "全极耳大圆柱",
            "46系列电芯",
            "4680 cell",
            "4680大圆柱电池",
        ],
        summary="直径46毫米、高80毫米的全新一代大型圆柱形电芯，采用无极耳/全极耳设计使内阻与发热量骤减，兼顾超高能量密度、大倍率快充与机械结构高强度。",
        description=(
            "4680大圆柱电池由特斯拉提出并引发宝马、松下、宁德时代等巨头跟进。圆柱形结构具备天然优秀的径向耐压物理特性（受力均匀），"
            "全极耳设计将电流传输距离缩短数十倍，解决了传统大电芯发热难散热的物理死穴，不仅充放电发热量仅为传统圆柱电池的五分之一，"
            "更极大提升了连续高速大功率快充耐受力与产线卷绕制造速度。"
        ),
        technical_principles=[
            "无极耳（Shingled / Tables）激光连续焊接成型，电流沿轴向横截面均匀扩散",
            "高张力钢壳圆柱结构承受高膨胀硅基负极内应力，杜绝膨胀形变变形",
        ],
        advantages=[
            "内部阻抗极低，快充发热极小，高倍率充放电性能和安全性极佳",
            "单体电芯容量较2170电池提升5倍，整车电芯数量从四千多颗大幅精简至八百颗左右",
            "钢壳圆柱受力均匀，单颗热失控时不易产生多米诺连锁扩散",
        ],
        limitations=[
            "全极耳激光连续揉平与焊接工序极其精密，早期量产良品率门槛极高",
            "圆柱体之间天然存在蜂窝空隙，体积能量密度利用率考验模组热管理填充工艺",
        ],
        sub_variants={
            "高镍三元4680": "主打高性能高能量密度长续航（特斯拉Cybertruck、宝马新世代）",
            "磷酸铁锂4680": "主打极致成本控制与储能商用长寿命",
        },
        representative_vehicles=["特斯拉Cybertruck", "特斯拉Model Y(美版)", "宝马新世代概念车(Neue Klasse)"],
        standard_labels=["4680电池", "大圆柱电芯", "全极耳", "低内阻快充", "高结构强度"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向客户科普：传统小圆柱电池发热大、方壳电池膨胀易挤压，4680大圆柱兼顾圆柱的钢壳耐撞与无极耳的超低发热，快充不伤电池；",
            "结合宝马新世代与特斯拉前沿技术，突出大圆柱作为未来新能源豪华标杆的领航地位。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 7. CTP 无模组动力电池成组技术
    TechnologyEntity(
        id="generic_ctp_technology",
        name="CTP 无模组动力电池集成技术 (Cell-to-Pack)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Cell-to-Pack (CTP) Modularless Battery Architecture",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="电池成组结构/无模组集成",
        aliases=[
            "ctp",
            "ctp技术",
            "无模组电池",
            "cell to pack",
            "大模组电池",
            "麒麟电池ctp",
        ],
        summary="取消传统中间模组侧板、端板与线束紧固件的电池集成技术，电芯直接组装成电池包，体积利用率从40%跃升至70%以上。",
        description=(
            "传统电池包由‘电芯-模组-电池包’三级装配，包含大量无能量的铝侧板和螺栓支架。CTP技术直接跨越中间模组，"
            "将大尺寸电芯整齐密排于托盘中，省去数百个机械结构件，大幅提升质量能量密度与体积利用率，代表作为宁德时代麒麟电池（CTP 3.0）。"
        ),
        technical_principles=[
            "高强度弹性隔热垫兼充结构梁与热阻隔双功能",
            "一体化集成多功能弹性夹层液冷板，水冷面积提升4倍",
        ],
        advantages=[
            "体积利用率突破72%，相同外形尺寸下可装入更多电量，整车轻松跑出超长续航",
            "零部件数量减少40%，生产线组装自动化率与生产节拍极大提升",
        ],
        limitations=[
            "无模组封装后，单个电芯故障的售后无损拆换难度高于传统独立模组电池",
        ],
        representative_vehicles=["极氪001麒麟版", "理想MEGA", "小米SU7 Pro", "蔚来100kWh电池包"],
        standard_labels=["CTP技术", "无模组电池", "体积利用率突破70%", "高能量密度成组"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向注重续航的客户解释：CTP就像把行李箱多余的内衬格子拆掉，同样大小的箱子能多装30%的衣物，电池包轻了电量反而更多。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 8. 钠离子动力电池技术
    TechnologyEntity(
        id="generic_sodium_ion_battery",
        name="钠离子动力电池技术 (Sodium-ion Battery)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Sodium-ion Battery Technology",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="动力电池/新型正负极电化学体系",
        aliases=[
            "钠电池",
            "钠离子电池",
            "钠电",
            "sodium ion",
            "钠离子动力电池",
        ],
        summary="以地壳储量丰富的金属钠离子为电荷载体的革命性电池，零下20℃放电保持率高达90%，成本低廉且绝不起火，是严寒高纬度代步车理想电源。",
        description=(
            "钠元素在地壳中含量高达2.75%，远超稀缺的锂资源（0.0065%），原料成本极为低廉且不受国际地缘政治卡脖子。"
            "钠离子电池在极寒-20℃环境下依然拥有90%以上的容量保持率，常温下充电15分钟即可充满80%，并在运输时允许彻底零伏特放电（零自燃隐患）。"
        ),
        technical_principles=[
            "普鲁士蓝类或层状氧化物正极配合硬碳微孔负极嵌入脱嵌机制",
            "铝箔取代铜箔作为负极集流体，成本大幅降低且无过度放电溶解风险",
        ],
        advantages=[
            "极低温性能极其出众，北方大雪纷飞时几乎零续航衰减",
            "原料成本极低，不受碳酸锂价格暴涨周期波动的冲击",
        ],
        limitations=[
            "质量能量密度目前在160Wh/kg左右，低于主流三元锂，主要适配A00级微型车和储能",
        ],
        representative_vehicles=["奇瑞QQ冰淇淋钠电版", "江淮钇为3钠电版", "宁德时代AB混合电池系统车型"],
        standard_labels=["钠离子电池", "零下20度抗寒", "低成本原料", "零伏特安全运输"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向高寒地区微型代步车客户推荐：冬天再冷电池也能正常放电跑满里程，早晨插枪快充十几分钟就满电出门。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 9. 磷酸锰铁锂动力电池体系 (LMFP)
    TechnologyEntity(
        id="generic_lithium_manganese_iron_phosphate",
        name="磷酸锰铁锂动力电池体系 (LMFP)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Lithium Manganese Iron Phosphate Battery (LMFP)",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="动力电池/高电压橄榄石正极材料",
        aliases=[
            "磷酸锰铁锂",
            "lmfp",
            "m3p电池",
            "锰铁锂",
            "lmfp电池",
            "高电压铁锂",
        ],
        summary="在磷酸铁锂晶格中掺杂锰元素的高性能升级电芯，将放电工作电压平台从3.2V提升至4.1V，能量密度提升15%~20%，兼顾铁锂安全与三元续航。",
        description=(
            "磷酸锰铁锂（LMFP）被誉为‘升级版磷酸铁锂’。由于锰离子的引入，其理论能量密度显著超越传统LFP，逼近NCM523三元水平；"
            "同时继承了橄榄石晶体极强的热稳定性（耐受600℃高温不分解），结合纳米碳包覆技术解决了早期锰溶出与导电率低的难题，正迅速成为主流纯电与混动车核心配置。"
        ),
        technical_principles=[
            "Fe/Mn固溶体晶格拓扑结构，利用Mn3+/Mn4+高电位氧化还原电对提升平台电压",
            "固相合成共沉淀包覆与晶界高导电性石墨烯网络修饰",
        ],
        advantages=[
            "能量密度比传统铁锂提升20%，使得中大型纯电车搭载安全铁锂也能突破700km续航",
            "低温放电衰减明显优于传统磷酸铁锂，兼具长循环寿命与低成本优势",
        ],
        limitations=[
            "制造中锰离子的溶解与电解液发生副反应需精密表面包覆工艺抑制",
        ],
        representative_vehicles=["智界S7(部分版本搭载M3P)", "特斯拉Model 3改款车型规划搭载", "奇瑞星途星纪元ES"],
        standard_labels=["磷酸锰铁锂", "LMFP", "4.1V高电压平台", "兼顾安全与长续航", "M3P电池"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向既想要铁锂绝对安全、又想要三元锂超长续航的纠结用户推荐：LMFP是两者的完美合体，续航扎实耐用，安全寿命完全拉满。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 10. 刀片长薄型结构动力电芯
    TechnologyEntity(
        id="generic_blade_battery_form",
        name="长薄化刀片动力电芯结构形态",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Blade Thin-Long Cell Structural Form",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="动力电池/结构化电芯形态",
        aliases=[
            "刀片形态",
            "长薄电芯",
            "短刀电芯",
            "长刀电芯",
            "刀片结构",
            "结构性电芯",
        ],
        summary="长度通常达0.6米至1米左右、厚度仅十余毫米的长薄状扁平铝壳电芯，单体自身即可充当底盘结构梁，兼具极佳散热与超强抗形变刚度。",
        description=(
            "传统方形电芯较厚，中心发热极难散出且成组时需要大量结构横梁。刀片形态将电芯极限拉长展薄，"
            "极大的表面积使电芯内部热量可瞬间通过侧面大面积液冷板带走；同时电芯像排列的积木横梁一样紧密卡紧在电池包两端，赋予电池包极强的横向抗压受力能力。"
        ),
        technical_principles=[
            "大长宽比（Aspect Ratio）卷绕/叠片工艺与双端出极耳对称设计",
            "结构化电芯本体参与承载整车扭转剪切载荷",
        ],
        advantages=[
            "超大表面积带来顶级散热效率，高倍率大电流快充不积聚核心热量",
            "电芯自身充当电池包横梁，消除冗余梁结构，大幅提升成组体积效率",
        ],
        limitations=[
            "超长极片连续叠片/卷绕对制造车间洁净度与极片对齐精度要求极其苛刻",
        ],
        representative_vehicles=["比亚迪汉", "比亚迪海豹", "吉利银河E8(神盾短刀电池)", "长安启源A07"],
        standard_labels=["刀片电芯形态", "长薄化结构", "电芯即结构梁", "大面积快速散热"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向客户展示刀片电芯像厚厚的钢板一样坚挺：‘每一片电芯都是坚不可摧的加强梁，侧面撞击时几百片刀片并排死死顶住，电芯绝不会变形自燃。’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 11. 方形铝壳硬壳动力电芯
    TechnologyEntity(
        id="generic_square_aluminum_shell_cell",
        name="方形铝壳动力电芯 (Prismatic Aluminum Cell)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Prismatic Aluminum-Cased Battery Cell",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="动力电池/金属硬壳封装形态",
        aliases=[
            "方形铝壳",
            "方壳电池",
            "方形电芯",
            "prismatic cell",
            "铝壳硬包电芯",
        ],
        summary="采用激光密封焊接高强度铝合金外壳的矩形电芯，机械防护强度高、防爆防穿刺能力强且空间空间利用率高，是中国新能源车最普及的电芯形态。",
        description=(
            "方形铝壳电芯（Prismatic Cell）内部采用成熟的叠片或卷绕工艺，外部由薄壁强韧铝合金冲压壳体包裹，顶盖集成防爆安全泄压阀与极柱。"
            "方壳形态在电池包内排列紧密规则，几何空隙接近于零；硬质铝壳为内部脆弱电极提供了极佳的防跌落、防挤压和防泥石飞溅防护。"
        ),
        technical_principles=[
            "连续激光顶盖焊缝密封与全自动氦气微漏洞检漏工艺",
            "顶盖集成机械式翻转防爆泄压膜（OSD）短路热释放保护",
        ],
        advantages=[
            "成组几何规则，空间填充系数远高于圆柱电池（无圆柱间三角死角）",
            "铝合金外壳抗冲击刚度高，生产自动化流水线极其成熟，良品率极高",
        ],
        limitations=[
            "单体电芯体积与容量偏大，若发生单体热失控释放的总能量较大，对相邻隔热要求高",
        ],
        representative_vehicles=["理想L系列", "问界M9", "蔚来ES6", "小鹏G6", "宝马i3/iX3"],
        standard_labels=["方形铝壳电芯", "空间填充率高", "高强度外壳", "全球最普及形态"],
        equivalence_group_id=None,
        sales_talking_points=[
            "说明方形铝壳电芯是全球技术最成熟、装车量最大、经过数百万辆实车验证的安全硬壳方案，品质坚若磐石。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 12. 软包聚合物层叠动力电芯
    TechnologyEntity(
        id="generic_soft_pack_pouch_cell",
        name="软包聚合物层叠动力电芯 (Pouch Cell)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Pouch Lithium-Polymer Battery Cell",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="动力电池/铝塑膜轻量封装形态",
        aliases=[
            "软包电池",
            "软包电芯",
            "pouch cell",
            "铝塑膜软包",
            "聚合物软包",
        ],
        summary="采用极轻高阻隔铝塑复合膜封装的扁平片状电芯，重量极轻、单体质量能量密度同级最高，即便热失控也仅发生胀气胀破而绝无金属爆炸破片飞溅。",
        description=(
            "软包电芯（Pouch Cell）取消了沉重的金属钢壳或铝壳，电芯内部由正负极片与隔膜层层叠片而成，外表面由热封铝塑膜保护。"
            "因去除了笨重金属外壳，软包电芯重量比同容量铝壳轻10%以上；即使内部发生短路剧烈胀气，较薄的热封边会受压温和裂开发气泄压，绝不会产生硬壳爆炸。"
        ),
        technical_principles=[
            "多层复合铝塑薄膜（尼龙层+铝箔层+PP热封层）高精度热压密封",
            "高对齐度叠片（Stacking）工艺，内部电流密度分布极其均匀",
        ],
        advantages=[
            "质量能量密度极高，同等电池重量下整车自重最轻、操控更轻盈敏捷",
            "热失控时只胀气冒烟而不剧烈爆炸飞溅，对乘员舱被动安全极其友好",
        ],
        limitations=[
            "铝塑膜抗尖锐物体机械穿刺能力弱于金属硬壳，电池包整体需要极强防护壳体保护",
            "充放电循环过程中电芯厚度膨胀率相对较大，模组需要设计预留弹性吸收空间",
        ],
        representative_vehicles=["保时捷Taycan", "奥迪e-tron GT", "奔驰EQS", "通用奥特能平台部分车型"],
        standard_labels=["软包电芯", "轻量化封装", "极佳被动安全", "胀气不爆炸", "豪车青睐形态"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向追求超跑级极致轻量化和高级安全的客户说明：保时捷Taycan等顶级纯电跑车均采用软包电芯，车重更轻且永远不会发生金属外壳爆炸。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 13. 硅碳复合高容量负极材料技术
    TechnologyEntity(
        id="generic_silicon_carbon_anode",
        name="硅碳复合高容量负极材料技术",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Silicon-Carbon Composite Anode Material",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="动力电池/负极材料进阶技术",
        aliases=[
            "硅碳负极",
            "硅基负极",
            "掺硅补锂",
            "硅氧负极",
            "高容量硅碳",
        ],
        summary="利用金属硅理论克容量高达石墨10倍的物理特性，将纳米硅颗粒与多孔碳基质复合的下一代负极技术，突破电芯能量密度300Wh/kg天花板。",
        description=(
            "传统石墨负极理论比容量仅为372mAh/g，已接近物理极限。硅的理论比容量高达4200mAh/g，但嵌锂时体积会剧烈膨胀300%导致极片粉化脱落；"
            "硅碳复合技术将纳米级硅颗粒巧妙包埋在导电碳基质微孔结构中，既吸收了硅膨胀应力，又大幅提升了电芯储锂容量，实现长续航与4C超快充兼得。"
        ),
        technical_principles=[
            "纳米多孔碳结构缓冲硅晶格膨胀应力与高强韧弹性粘结剂网络",
            "预锂化（Pre-lithiation）技术弥补首次充放电SEI膜不可逆锂离子消耗",
        ],
        advantages=[
            "比容量大幅飞跃，带动整包电量在不增加体积的前提下增加10%~20%",
            "快充时锂离子扩散阻抗低，支持数倍于纯石墨负极的大电流极速充入",
        ],
        limitations=[
            "硅膨胀收缩仍对长周期循环寿命提出极大挑战，目前工业界多采用3%~10%低比例掺杂",
        ],
        representative_vehicles=["特斯拉Model S Plaid", "小米SU7 Max", "极氪001 FR", "智己L6"],
        standard_labels=["硅碳负极", "突破石墨极限", "4200mAh高容量", "大倍率快充底座"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向技术流用户介绍：电池里加入了最先进的纳米硅碳负极，电芯内部像海绵吸水一样吸纳海量锂离子，续航轻松突破800公里且充电极快。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 14. 高镍单晶正极动力电池材料体系
    TechnologyEntity(
        id="generic_high_nickel_cathode",
        name="高镍单晶正极动力电池材料体系",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="High-Nickel Single-Crystal Cathode Material",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="动力电池/正极材料进阶技术",
        aliases=[
            "高镍正极",
            "单晶高镍",
            "高镍三元",
            "811高镍",
            "9系高镍",
            "单晶三元锂",
        ],
        summary="将正极镍元素摩尔占比提升至80%甚至90%以上，并采用无晶界破裂的单晶颗粒生长的顶级三元正极材料，兼具极高比容量与优异高温抗裂循环性。",
        description=(
            "镍含量越高电池能量密度越大，但传统多晶高镍在多次充放电膨胀收缩中晶粒间极易产生微裂纹，导致内部短路热失控。"
            "单晶高镍通过特殊高温熔盐晶体生长工艺，消除了内部晶界缺陷；颗粒坚固如微型金刚石，即使在高电压与剧烈压实下也不破碎，兼得高能量与高温长寿命。"
        ),
        technical_principles=[
            "高温熔盐结晶法生长无晶界单晶颗粒，极大提升抗机械剪切破裂能力",
            "表面气相外延惰性氧化物包覆与微量元素锆/铝/钛体相离子掺杂改性",
        ],
        advantages=[
            "单体克容量高达210mAh/g以上，支持纯电轿车整包电量轻松突破100kWh",
            "高温耐受性比传统多晶高镍提升显著，夏季暴晒高温下循环寿命大幅延长",
        ],
        limitations=[
            "对生产车间低湿度要求近乎极限，且原材料高纯镍钴开采提炼成本高",
        ],
        representative_vehicles=["特斯拉Cybertruck", "小米SU7 Max", "蔚来ET7", "保时捷Taycan Turbo"],
        standard_labels=["高镍单晶正极", "NCM811/9系", "无晶裂技术", "超长寿命长续航"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "针对纠结电池衰减的高端买家：单晶高镍电芯内部没有微裂纹磨损，不仅续航超长，而且即便天天快充开很多年依然动力澎湃衰减微弱。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 15. 动力电池热失控阻隔与定向防爆泄压系统
    TechnologyEntity(
        id="generic_battery_thermal_runaway_prevention",
        name="动力电池热失控阻隔与定向防爆泄压技术",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Battery Thermal Runaway Containment & Directional Venting",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="电池安全/热失控被动安全防御",
        aliases=[
            "热失控阻隔",
            "电池气凝胶隔热",
            "定向泄压",
            "无热蔓延电池",
            "防爆阀泄压",
            "云母板隔热",
        ],
        summary="在电芯之间设置航天级耐千度气凝胶隔热垫与排气导流通道的安全体系，即使单个电芯发生热失控，高温高压火焰瞬间向车底定向排出，绝不波及邻近电芯与乘员舱。",
        description=(
            "动力电池自燃的核心元凶是‘热蔓延多米诺骨牌效应’。现代高安全电池包在每个电芯大面均贴附厚度仅1-2mm的气凝胶阻燃层，可耐受1200℃高温冲击；"
            "同时在电池箱体底部设计专用单向泄压防爆阀与独立耐高温排气汇流通道，毫秒级将高温烟雾与炽热气流定向喷射至车辆下方地面，乘员舱内零烟雾、零明火。"
        ),
        technical_principles=[
            "二氧化硅超临界纳米多孔气凝胶超低导热系数（<0.02 W/(m·K)）物理隔热",
            "底部独立排气通道+毫秒级爆破泄压阀热流瞬态流体动力学定向导流",
        ],
        advantages=[
            "真正实现‘单颗电芯热失控、整包不起火不蔓延’，国家安全强标全优达标",
            "为车内驾乘人员提供充足的逃生自救黄金时间，乘员舱底板温升不烫脚",
        ],
        limitations=[
            "隔热气凝胶与独立排气通道占用了微量模组内部体积，成组工程设计精度极高",
        ],
        representative_vehicles=["极氪001(金砖电池)", "小米SU7(倒置电芯+全贯通烟道)", "比亚迪海豹", "问界M9"],
        standard_labels=["热失控阻隔", "气凝胶耐千度隔热", "定向车底泄压", "零热蔓延不起火"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向最关注全家生命安全的客户做演示：即便极端外力刺破单颗电芯，火焰也会顺着底盘专属烟道瞬间排出车外，车内既闻不到烟也看不到火，绝对安心。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 16. 干法电极制造工艺 (Dry Battery Electrode)
    TechnologyEntity(
        id="generic_dry_electrode_process",
        name="干法电极制造工艺 (Dry Battery Electrode)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Dry Battery Electrode (DBE) Process",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="电池制造/无溶剂绿色制造工艺",
        aliases=[
            "干法电极",
            "dbe工艺",
            "无溶剂电极",
            "干法电极技术",
            "dry electrode",
        ],
        summary="取消传统有毒有机化学溶剂（NMP）调制与数百米烘烤隧道的颠覆性电极制造工艺，大幅节省生产耗电与占地，是动力电池制造成本减半的核心武器。",
        description=(
            "传统湿法工艺需将电极粉末与NMP溶剂搅拌成泥浆，涂布在铜铝箔后通过数十米长的高耗能干燥炉烘烤数天，耗电极大且产生化学废气。"
            "干法工艺直接将活性粉末与PTFE纤维聚合物干粉混合，通过高压精密轧辊直接碾压成自支撑致密极片薄膜，彻底告别烘干炉，能耗降低超80%、占地缩减三分之二。"
        ),
        technical_principles=[
            "PTFE细丝原纤化网络受剪切力形成自支撑三维立体多孔高韧性骨架薄膜",
            "多辊连续伺服高压超精密热复合轧延贴合金属箔集流体",
        ],
        advantages=[
            "制造能耗骤降超80%，工厂占地面积缩小70%，综合电芯制造成本预期降低超15%",
            "没有溶剂干燥产生的微裂纹与粘结剂漂移，电极压实密度更高、电子导电更顺畅",
        ],
        limitations=[
            "负极干法相对成熟，但高硬度正极材料干法成膜极度易碎裂，工业良品率仍在突破期",
        ],
        representative_vehicles=["特斯拉Cybertruck(4680电芯正负极干法逐步导入)"],
        standard_labels=["干法电极", "DBE工艺", "无溶剂制造", "能耗降低80%", "制造成本颠覆者"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向关注未来工业与前沿制造的科技精英说明：干法电极是新能源汽车制造工艺的工业革命，它让电动车电池成本像摩尔定律一样持续大幅下探。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
        is_generic=True,
        generic_category="电池形态",
    ),

    # 17. BMS 主动均衡电荷智能管理系统
    TechnologyEntity(
        id="generic_bms_active_balancing",
        name="BMS 主动均衡电荷智能管理系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="BMS Active Charge Balancing System",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="电池管理/双向无损电荷转移均衡",
        aliases=[
            "主动均衡",
            "bms主动均衡",
            "主动均衡bms",
            "无损电荷转移",
            "双向能量均衡",
        ],
        summary="通过双向DC-DC变换电路将高电量电芯的电荷无损转移输送给低电量电芯的高级BMS系统，消除木桶效应，把整包可用可用电量榨取至最后一滴。",
        description=(
            "电池包由数百颗电芯串并联组成，传统被动均衡只是简单通过发热电阻把高电量电芯多余电量‘白白放电烧掉’，效率极低且发热严重。"
            "主动均衡系统通过高频开关电感/变压器，以高达数安培的电流将多余电量直接泵入电压落后的短板电芯中，消除发热，显著延长整包寿命并挽回数十公里续航。"
        ),
        technical_principles=[
            "双向反激隔离式微型DC-DC拓扑实现电芯间与模组间的能量无损双向流转",
            "电化学阻抗与OCV开路电压在线估算神经网络实时调度均衡策略",
        ],
        advantages=[
            "均衡电流可达数安培（是传统被动均衡几十倍），行驶与静止状态均能高效补平压差",
            "彻底消除木桶短板效应，老车使用多年后依然能保持刚买车时的扎实续航",
        ],
        limitations=[
            "每个电芯通道均需配备独立双向功率开关管与磁性元件，BMS主板物料成本增加",
        ],
        representative_vehicles=["保时捷Taycan", "蔚来ES8", "极氪001 FR", "高端定制长寿命商用客车"],
        standard_labels=["BMS主动均衡", "无损电荷转移", "消除木桶短板", "延长电池生命周期"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向担心电池开几年各电芯老化不均匀、续航崩塌的客户说明：主动均衡就像一个贴心的搬运工，时刻把电量平分给每个电芯，开八年十年电池依然健康整齐。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="电池形态",
    ),
]

"""
Generic Chassis & Suspension Technical Terminology (src/terminology/generic/chassis.py).
Contains 18 comprehensive generic chassis technologies (category="悬架形式").
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

GENERIC_CHASSIS_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 麦弗逊式独立悬架 (Original)
    TechnologyEntity(
        id="generic_macpherson_suspension",
        name="麦弗逊式独立悬架",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="MacPherson Strut Suspension",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="悬架形式/独立悬架",
        aliases=[
            "麦弗逊",
            "麦弗逊悬架",
            "麦弗逊独立悬架",
            "麦弗逊式悬架",
            "麦弗逊式前悬架",
            "macpherson",
            "macpherson strut",
            "麦弗逊前悬",
        ],
        summary="由螺旋弹簧和减振器滑柱合二为一的经典独立悬架，结构紧凑小巧、成本经济、占用前机舱横向空间极小，为发动机/前电机布局创造极佳空间。",
        description=(
            "麦弗逊悬架（MacPherson Strut）由减振器支柱、螺旋弹簧以及下控制A臂组成。其减振支柱兼具减振和车轮转向主销的双重功能。"
            "由于结构高度集成精简，麦弗逊悬架是全球乘用车最普及的前悬架方案，但其侧向受力主要由减振滑柱承受，极限工况下的横向刚度弱于双叉臂。"
        ),
        technical_principles=[
            "滑柱式单主销几何拓扑，下A臂约束纵向与部分横向自由度",
            "减振支柱承受垂向载荷与弯矩，集成螺旋弹簧与缓冲块",
        ],
        advantages=[
            "结构紧凑，重量轻，大幅节省前轴机舱横向布置空间",
            "零部件数量少，制造成本低，维修更换便捷经济",
        ],
        limitations=[
            "横向刚度相对有限，刹车点头和急转弯侧倾抑制能力不如双叉臂",
            "由于减振滑柱直接承受弯矩，摩擦阻力略大，极端路况细腻滤震略逊",
        ],
        sub_variants={
            "传统麦弗逊": "单件下控制臂与减振滑柱结构",
            "双球节麦弗逊": "下A臂解耦为两根独立连杆，形成虚拟主销，显著改善操控指向性与转向手感（宝马广泛采用）",
        },
        representative_vehicles=["大众高尔夫", "丰田凯美瑞", "比亚迪秦PLUS", "比亚迪海豚", "特斯拉Model 3(前悬为双叉臂，此列为对比参考)"],
        standard_labels=["麦弗逊悬架", "独立悬架", "机舱空间优化", "经济实用底盘"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向追求车内空间和经济实用的家用车客户解释：前麦弗逊悬架能留出更大的前备箱或车内腿部空间，且后期保养维护极其省心省钱。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 2. 双叉臂式独立悬架 (Original)
    TechnologyEntity(
        id="generic_double_wishbone_suspension",
        name="双叉臂式独立悬架",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Double Wishbone Suspension",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="悬架形式/独立悬架",
        aliases=[
            "双叉臂",
            "双叉臂悬架",
            "双叉臂独立悬架",
            "双叉臂式悬架",
            "双A臂",
            "double wishbone",
            "双横臂",
            "双横臂独立悬架",
        ],
        summary="由上下两根横向控制叉臂（A臂）组成的顶级独立悬架，上下臂共同吸收横向冲击力，提供极强的侧向支撑刚度与贴地抓地力，是运动跑车与高端豪华车的黄金标配。",
        description=(
            "双叉臂悬架（Double Wishbone）拥有上下不等长控制臂。减振器与弹簧仅承担垂向减振任务，不承受横向弯矩；"
            "车轮在上下跳动时，通过上下叉臂的几何长短差异可主动改变车轮外倾角，保证轮胎胎面始终垂直贴紧路面，极大提升过弯极限与刹车防点头能力。"
        ),
        technical_principles=[
            "双横向控制臂几何约束，实现横向力与垂向力的完全解耦",
            "通过不等长控制臂设计优化车轮跳动外倾角补偿与滚动中心高度",
        ],
        advantages=[
            "横向刚度极高，急转弯时抗侧倾能力出色，轮胎贴地面积最大化",
            "刹车防点头、加速防抬头特性优异，操控精准路感清晰",
        ],
        limitations=[
            "占用前机舱横向空间较大，对发动机或前电驱布置要求苛刻",
            "零部件数量多、制造装配精度要求极高，整车制造成本昂贵",
        ],
        sub_variants={
            "传统A臂双叉臂": "单件铸造或冲压上下A字形控制臂",
            "双球节虚拟主销双叉臂": "上下叉臂均解耦为独立双连杆，转向主销轴线更贴近轮心，操控极致细腻",
        },
        representative_vehicles=["特斯拉Model S", "蔚来ET7", "极氪001", "保时捷Taycan", "小米SU7"],
        standard_labels=["双叉臂悬架", "顶级运动操控", "横向高刚度", "豪车黄金底盘"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向看重操控质感与驾驶信心的客户对比：‘双叉臂悬架是百万超跑的标配，上下两根铝合金叉臂死死拉住车轮，过弯高速变道车身极其平稳不发晃。’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 3. 多连杆式独立悬架 (Original)
    TechnologyEntity(
        id="generic_multilink_suspension",
        name="多连杆式独立悬架",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Multi-Link Independent Suspension",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="悬架形式/独立悬架",
        aliases=[
            "五连杆",
            "多连杆",
            "五连杆悬架",
            "五连杆独立悬架",
            "多连杆独立悬架",
            "multi-link",
            "multilink",
            "四连杆",
            "后多连杆",
        ],
        summary="由三根或以上（常见为四连杆或五连杆）独立连杆约束车轮跳动的先进悬架，能够精确解耦各个方向的力与力矩，实现舒适性与操控稳定性的极致均衡。",
        description=(
            "多连杆悬架（Multi-Link）通过多根控制连杆精细定位车轮空间姿态。五连杆悬架分别控制车轮的横向、纵向、垂直及前束角变化，"
            "在车轮颠簸跳动过程中能使前束角发生微小随动改变，在不牺牲直线滤震舒适性的前提下提供超强的高速过弯轨迹循迹性，广泛用作高端车型后悬架。"
        ),
        technical_principles=[
            "空间多连杆运动机构拓扑约束，精确控制车轮运动学五自由度",
            "弹性运动学衬套（Elastokinematics）调校实现受力自适应前束偏转",
        ],
        advantages=[
            "调校自由度极高，能够兼得如履平地的滤震舒适感与极致抓地循迹性",
            "高速变道稳定，后轮循迹性强，有效抑制后轴横向摆动",
        ],
        limitations=[
            "结构复杂，橡胶衬套与球头数量较多，底盘重量偏重且长年使用后衬套老化需维护",
            "对整车悬架参数标定算法与工程调校功底要求极高",
        ],
        sub_variants={
            "四连杆悬架": "兼顾成本与操控的常见前/后悬方案",
            "五连杆独立悬架": "最高规格多连杆形态，各方向受力完全独立解耦调校",
        },
        representative_vehicles=["奔驰S级", "奥迪A6L", "理想L9", "蔚来ES6", "小鹏G9"],
        standard_labels=["五连杆独立悬架", "多连杆悬架", "后悬高级标配", "舒适与操控平衡"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向家庭出行与追求舒适乘坐质感的买家强调：‘五连杆悬架能把路面的冲击碎震分解吸收在各根连杆衬套中，后排老人孩子久坐不易颠簸晕车。’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 4. CDC 连续阻尼可调减振系统 (Original)
    TechnologyEntity(
        id="generic_cdc_damping",
        name="CDC 连续可变阻尼减振系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Continuous Damping Control (CDC)",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="悬架控制/阻尼调节",
        aliases=[
            "cdc",
            "cdc减振器",
            "cdc电磁减振",
            "连续阻尼控制",
            "可变阻尼减振",
            "自适应阻尼",
            "电控减振",
        ],
        summary="通过电磁比例阀在毫秒级内无级调节减振器内部油液流速的半主动悬架技术，每秒调节上百次，实现‘颠簸路面变软吸震、激烈驾驶变硬支撑’。",
        description=(
            "CDC（Continuous Damping Control）系统由车身加速度传感器、车轮位移传感器、电控减振器及中央ECU组成。"
            "当系统检测到车辆经过减速带或坑洼时，电磁阀迅速增大油孔开度使悬架变软充分滤震；在紧急变道或刹车时，电磁阀缩小油孔使悬架变硬稳住车身姿态。"
        ),
        technical_principles=[
            "电磁比例阀无级调节液压减振器阀系开度（调节周期5-10ms）",
            "基于天棚原理（Skyhook）与地面反馈的半主动悬架控制算法",
        ],
        advantages=[
            "每秒调节阻尼上百次，大幅抑制车身起伏余震与刹车点头",
            "相比空气悬架成本与维护难度显著更低，可靠性高且终身免充气维护",
        ],
        limitations=[
            "仅能调节阻尼软硬，无法改变车身离地高度（需与空气弹簧组合使用方可调高低）",
        ],
        sub_variants={
            "外置电磁阀CDC": "电磁控制阀位于减振器筒身外部，散热更佳调节范围更宽",
            "内置电磁阀CDC": "电磁阀高度集成于减振活塞杆内部，空间结构更紧凑",
        },
        representative_vehicles=["比亚迪汉(千山翠版)", "理想L7/L8", "极氪001", "别克君越", "问界M7"],
        standard_labels=["CDC可变阻尼", "毫秒级软硬调节", "天棚控制算法", "告别晃荡颠簸"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向预算适中又想要豪车滤震质感的用户说明：CDC是性价比极高的底盘利器，能让车身在经过颠簸减速带时干脆利落一吸到底，没有恼人的来回晃悠。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 5. 空气悬架系统 (Original)
    TechnologyEntity(
        id="generic_air_suspension",
        name="空气悬架系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Air Suspension System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="悬架控制/刚度与高度调节",
        aliases=[
            "空悬",
            "空气悬架",
            "空气悬挂",
            "单腔空悬",
            "单腔空气悬架",
            "air suspension",
            "气动悬架",
        ],
        summary="用充气式高强度橡胶气囊替代传统螺旋钢制弹簧的高级悬架系统，支持车身高度大范围升降并提供如漂浮云端的隔绝感滤震。",
        description=(
            "空气悬架由空气弹簧气囊、储气罐、电动空气压缩机、分配阀及高度传感器组成。不仅能在高速巡航时自动降低车身减小风阻和电耗，"
            "在复杂烂路主动升高车身防止磕碰底盘电池，并能在静止装载重物时自动调平车身姿态，配合CDC形成‘魔毯’级乘坐体验。"
        ),
        technical_principles=[
            "压缩空气作为非线性弹性介质，具有动刚度随载荷自适应调节特性",
            "电控空压机与气路分配阀协同实现四轮车身离地高度精确闭环调节",
        ],
        advantages=[
            "车身离地间隙随心调节，兼顾轿车级低风阻操控与SUV级高通过性",
            "高频细碎振动吸收极佳，带来如履平地的顶级豪华悬浮漂浮感",
        ],
        limitations=[
            "橡胶气囊在长年极端高低温与砂石环境下存在老化磨损漏气可能，长周期维护成本高于金属弹簧",
            "单腔空气悬架无法在同等高度下独立调节弹簧主刚度软硬（需双腔/三腔解决）",
        ],
        sub_variants={
            "开式空气悬架": "直接从外界抽取空气压缩，充气噪音稍大，极端严寒下气路有结冰凝露风险",
            "闭式空气悬架": "高压氮气在储气罐与气囊间封闭循环，升降响应快数倍、噪音更低且终身无结冰担忧",
        },
        representative_vehicles=["理想L9", "蔚来ES8", "极氪001", "奔驰S级", "宝马X7", "保时捷卡宴"],
        standard_labels=["空气悬架", "底盘高度调节", "魔毯滤震", "豪车尊贵配置"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "带客户体验后备箱装载模式（车尾一键降低几厘米方便放行李），以及烂路一键升高防托底，展示空气悬架不可替代的实用尊贵价值。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 6. 主动后轮转向系统 (Original)
    TechnologyEntity(
        id="generic_rear_wheel_steering",
        name="主动后轮转向技术",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Active Rear Wheel Steering (RWS)",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="转向系统/后桥随动与主动转向",
        aliases=[
            "后轮转向",
            "后轴转向",
            "四轮转向",
            "主动后轮转向",
            "rear wheel steering",
            "rws",
            "后轮主动转向",
            "四轮转向系统",
        ],
        summary="后轮可随工况主动偏转一定角度的底盘转向技术，实现‘低速前轮反向偏转一把掉头、高速前轮同向偏转平稳变道’，彻底化解大车笨拙难题。",
        description=(
            "在车速较低时（如<40km/h），后轮与前轮反向偏转（通常3-10度），大幅缩短虚拟轴距，使5米级甚至5.3米级大型D级豪车拥有类似A级紧凑小车的极小转弯半径；"
            "在车速较高时，后轮与前轮同向偏转，车身如‘蟹行’平移般变道，消除后排乘员因车尾甩摆导致的晕车不适。"
        ),
        technical_principles=[
            "后桥独立电控执行伺服电机驱动梯形连杆机构拉动后车轮偏转",
            "随速自适应算法：低速反相偏转减小转弯半径，高速同相偏转抑制横摆角速度滞后",
        ],
        advantages=[
            "窄路调头、地库直角弯拐弯与狭窄侧方停车一把进，开大车像开小车一样轻松",
            "高速紧急变道或过弯时后轴稳定性极高，后排乘坐体验极其平稳防晕车",
        ],
        limitations=[
            "后桥机械结构高度紧凑且成本昂贵，占用部分后排下车体空间与后备箱深度",
        ],
        sub_variants={
            "小角度后轮转向": "最大转向角度±3度左右，成本适中，多用于中大型运动轿车",
            "大角度后轮转向": "最大转向角度可达±8度至±12度，多用于大型豪华行政轿车及MPV",
        },
        representative_vehicles=["奔驰S级", "智己L6/LS6", "小鹏X9", "保时捷Panamera", "奥迪A8L"],
        standard_labels=["主动后轮转向", "一把掉头", "5.4米转弯半径", "防晕车变道"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "针对担心5米大车难停难开的客户，带其去窄路实测一把掉头：‘后轮一转，转弯半径比大众高尔夫还小，哪怕新手开大车进狭窄老小区也毫无压力。’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 7. 智能双腔空气悬架
    TechnologyEntity(
        id="generic_dual_chamber_air_suspension",
        name="智能双腔空气悬架技术",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Intelligent Dual-Chamber Air Suspension",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="悬架控制/多腔刚度调节",
        aliases=[
            "双腔空悬",
            "双腔空气悬架",
            "双腔空气弹簧",
            "dual chamber air suspension",
            "双室空悬",
        ],
        summary="在单腔空气悬架基础上增加独立副气室与电磁阀的高阶悬架，可在保持车身高度不变的前提下毫秒级切换弹簧基础刚度，兼顾极致舒适与强劲支撑。",
        description=(
            "单腔空悬只能调节车身高度，弹簧刚度调节范围受限。双腔空气弹簧通过电磁阀通断主副气室气路："
            "需要舒适时双腔相通增加气囊容积，弹簧变软过滤细微颠簸；需要激烈驾驶或过弯时切断副气室，有效容积变小使弹簧瞬间变硬，提供抗侧倾支撑力。"
        ),
        technical_principles=[
            "电控切换双气室连通状态改变气囊有效受压容积与动刚度",
            "车身动态传感器实时采集侧向加速度与转向角速度驱动毫秒级切换",
        ],
        advantages=[
            "彻底打破传统空悬要舒适就软趴趴、要运动就硬邦邦的矛盾",
            "刚度调节跨度可达40%以上，抗侧倾与防制动点头表现远胜单腔空悬",
        ],
        limitations=[
            "气囊制造工艺复杂，装配与电控系统成本显著高于单腔系统",
        ],
        representative_vehicles=["保时捷卡宴", "小鹏G9", "蔚来ES8", "理想L9 Ultra"],
        standard_labels=["双腔空气悬架", "刚度无级切换", "抗侧倾支撑", "双气室电磁阀"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "对比单腔空悬车型，强调双腔空悬能真正做到‘要软如魔毯，要硬如跑车’，兼得商务舒适与山路过弯激情。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 8. 智能三腔空气悬架
    TechnologyEntity(
        id="generic_triple_chamber_air_suspension",
        name="智能三腔空气悬架技术",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Intelligent Triple-Chamber Air Suspension",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="悬架控制/超宽刚度域调节",
        aliases=[
            "三腔空悬",
            "三腔空气悬架",
            "三气室悬挂",
            "triple chamber air suspension",
        ],
        summary="配备三个独立可调气室的顶级空气悬架，拥有四种不同的物理弹簧刚度梯度，实现从极致赛道硬核支撑到顶级行政奢华悬浮的全维度跨越。",
        description=(
            "三腔空气弹簧内部设有主气室与两个分级副气室，通过两组高频电磁阀组合控制开闭状态。可在全开（三腔通畅柔和）、开双腔（适度支撑）、"
            "单开主腔（极端刚硬）之间自由切换，刚度调节动态范围超过传统单腔数倍，常见于保时捷Panamera等顶级超豪华运动轿车。"
        ),
        technical_principles=[
            "多气室并联网络与独立高速电磁旁通阀阵列",
            "多阶刚度非线性多项式拟合控制算法",
        ],
        advantages=[
            "行业物理弹簧刚度调节跨度最大，兼具超跑级极限过弯抗侧倾与劳斯莱斯级滤震",
            "响应极快，可在一次车轮颠簸行程中完成刚度调整",
        ],
        limitations=[
            "制造成本极高，结构极为紧凑复杂，目前主要普及于百万级超豪华轿车与SUV",
        ],
        representative_vehicles=["保时捷Panamera", "保时捷Taycan", "保时捷Macan EV"],
        standard_labels=["三腔空气悬架", "顶级空气弹簧", "多阶刚度调节", "超跑级底盘技术"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向追求顶尖物理极限的保时捷或高端豪车买家讲解：三腔空悬是目前气动弹簧的科技巅峰，带来毫无妥协的极致驾乘品质。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 9. MRC 主动电磁感应悬架
    TechnologyEntity(
        id="generic_mrc_magnetic_damping",
        name="MRC 主动电磁感应悬架系统 (Magnetic Ride Control)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Magnetic Ride Control (MRC)",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="悬架控制/磁流变液体阻尼调节",
        aliases=[
            "mrc",
            "电磁悬架",
            "磁流变减振器",
            "mrc电磁悬挂",
            "主动电磁感应悬架",
            "magnetic ride control",
        ],
        summary="利用磁流变液体受磁场激发微秒级改变黏度的超高响应半主动悬架，每秒监测路面高达1000次，被誉为全球响应最快的减振系统之一。",
        description=(
            "MRC减振器内部注入了含有极细微磁性铁颗粒的碳氢化合物液体。活塞线圈通电产生磁场时，原本游离的铁颗粒在微秒级时间内排列成链状阻碍液体流动，"
            "减振阻尼瞬间变硬；断电时磁链立即瓦解阻尼变软。响应速度仅需1毫秒（比传统CDC电磁机械阀快数十倍），广泛应用于法拉利超跑与凯迪拉克黑翼车型。"
        ),
        technical_principles=[
            "磁流变液（MR Fluid）在外加磁场作用下的流变学相变效应",
            "无机械运动阀体阀片磨损，全电流激励无机械磨损控制",
        ],
        advantages=[
            "响应极速（达1000Hz/每秒千次计算调节），完全抹平路面高频细碎振动",
            "没有机械阀体延迟与卡滞异响，耐久度极高",
        ],
        limitations=[
            "磁流变液体专利成本高昂，且长期高温剧烈剧烈赛道工况下液体具有一定使用寿命周期",
        ],
        representative_vehicles=["凯迪拉克CT5-V Blackwing", "法拉利458/488", "奥迪R8", "雪佛兰科尔维特C8"],
        standard_labels=["MRC电磁悬架", "磁流变减振", "每秒1000次调节", "超跑级瞬态响应"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向性能车车迷展示MRC电磁悬架‘毫秒级磁场相变’的神奇机制：每秒对路面扫描1000次，即使路面瞬间坑洼也能在车轮下落瞬间稳稳拉住。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 10. 扭力梁式非独立/半独立悬架
    TechnologyEntity(
        id="generic_torsion_beam_suspension",
        name="扭力梁式非独立/半独立后悬架",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Torsion Beam Rear Suspension",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="悬架形式/半独立悬架",
        aliases=[
            "扭力梁",
            "扭力梁悬架",
            "板悬",
            "扭力梁后悬",
            "半独立悬架",
            "torsion beam",
        ],
        summary="由一根高韧性横梁连接两侧车轮的经典后悬架形式，具备无与伦比的后排与后备箱空间利用率以及极高结构耐久度，是紧凑型家用车的最强空间利器。",
        description=(
            "扭力梁后悬架两侧纵向摆臂通过中间可受扭转变形的横梁刚柔结合相连。一侧车轮跳动时横梁发生微小扭转，兼具部分防倾杆功能。"
            "由于省去了多根复杂的横向拉杆与大型副车架，后排地板与后备箱深槽容积可做到极致深凹平整，在紧凑型纯电和燃油家用车中应用极广。"
        ),
        technical_principles=[
            "变截面高强度弹簧钢横梁抗扭转与抗弯曲力学耦合",
            "拖曳臂纵向引导与斜置大尺寸减振器优化空间包络",
        ],
        advantages=[
            "结构简单皮实耐操，几乎终身免维护，不易损坏",
            "大幅释放后排脚部横向空间与后备箱纵向容积，空间得房率同级第一",
        ],
        limitations=[
            "单侧车轮剧烈颠簸会通过横梁传递干涉对侧车轮，剧烈烂路乘坐舒适度弱于五连杆独立悬架",
        ],
        representative_vehicles=["大众高尔夫(部分车型)", "比亚迪元PLUS", "本田飞度", "日产轩逸"],
        standard_labels=["扭力梁悬架", "空间利用率最高", "经济耐用", "紧凑车空间神器"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向注重后排大空间与后备箱实用装载的务实买家解释：扭力梁省下的底盘空间全变成了后排的大沙发和超大后备箱，且后期维修保养费用极低。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 11. 全线控转向系统 (Steer-by-Wire)
    TechnologyEntity(
        id="generic_steer_by_wire",
        name="全线控转向系统 (Steer-by-Wire)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Steer-by-Wire (SbW) System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="转向系统/机械解耦线控转向",
        aliases=[
            "线控转向",
            "steer by wire",
            "sbw",
            "电传转向",
            "无机械转向柱",
            "随速转向比线控",
        ],
        summary="彻底移除方向盘与转向车轮之间物理机械轴杆连接的革命性转向技术，通过电信号传递意图，实现无限可变转向比与方向盘折叠收拢。",
        description=(
            "由方向盘手感模拟器、转向执行电机及三冗余电子控制单元构成。低速泊车时仅需轻转半圈方向盘即可将车轮打满，高速行驶传动比自动变大确保沉稳不晃；"
            "由于没有机械硬连接，路面恶劣冲击震颤不会打手，且在L3/L4自动驾驶时方向盘可完全静止甚至缩进仪表台，释放座舱活动空间。"
        ),
        technical_principles=[
            "双/三冗余电控传感器与双绕组高功率无刷伺服电机容错设计",
            "路感力矩实时虚拟反馈算法（根据车速、侧向G值模拟轮胎回正力矩）",
        ],
        advantages=[
            "掉头停车无需频繁交叉倒手打方向盘，动作优雅敏捷",
            "彻底消除转向柱正面碰撞刺入乘员舱伤人的安全隐患",
        ],
        limitations=[
            "全车电气与功能安全冗余要求极高，行业法律法规准入认证流程严格",
        ],
        representative_vehicles=["特斯拉Cybertruck", "蔚来ET9", "雷克萨斯RZ(线控版)"],
        standard_labels=["全线控转向", "Steer-by-Wire", "可变转向比", "高阶智驾硬件基石"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "向追求未来科技感的客户展示线控转向：低速掉头只需转动小半圈即可调头，没有繁琐的打方向轮圈动作，未来感十足。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 12. One-Box 一体化线控制动系统
    TechnologyEntity(
        id="generic_brake_by_wire_one_box",
        name="One-Box 一体化线控制动系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="One-Box Integrated Brake-by-Wire System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="制动系统/高集成度电子机械制动",
        aliases=[
            "one-box",
            "onebox",
            "一体化线控制动",
            "线控刹车",
            "ipb",
            "博世ipb",
            "集成式线控液压制动",
        ],
        summary="将刹车踏板感模拟器、真空助力泵、ABS与ESP车身电子稳定系统高度集成为单一体积模块的顶尖线控制动系统，建压时间缩短至150毫秒以内。",
        description=(
            "One-Box由电机直接驱动液压主缸建压，踩下刹车踏板时脚感与实际卡钳液压解耦，由传感器采集踩踏深度后电机极速泵油。"
            "紧急刹车建压速度比传统真空助力器快3倍，使100-0km/h制动距离显著缩短数米，并且在能量回收与机械刹车衔接时脚踏板完全不震动、不顶脚。"
        ),
        technical_principles=[
            "无刷电机滚珠丝杠直接驱动液压活塞快速建压（<150ms达100bar）",
            "踏板位移传感器+踏板脚感模拟弹簧阻尼机构实现踏板感完全可编程解耦",
        ],
        advantages=[
            "AEB自动紧急制动刹停反应极其迅猛，显著缩短致命事故制动距离",
            "刹车踏板软硬可随驾驶模式自由切换，能量回收电刹车脚感平滑细腻",
        ],
        limitations=[
            "高度集成化导致单体零部件制造成本较高，系统故障时依赖备份机械液压回路兜底",
        ],
        representative_vehicles=["比亚迪海豹", "蔚来ES6", "小米SU7", "极氪007", "特斯拉Model 3(配置博世iBooster/IPB)"],
        standard_labels=["One-Box线控刹车", "极速150ms建压", "刹车距离缩短", "踏板感可编程"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向关注行车安全的客户强调：配备One-Box线控刹车能在突发危险时比普通车快零点几秒拉满制动力，多这几米距离就能避免重大追尾追尾。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 13. Two-Box 分体式线控制动系统
    TechnologyEntity(
        id="generic_brake_by_wire_two_box",
        name="Two-Box 分体式线控制动系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Two-Box Split Brake-by-Wire System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="制动系统/分体式冗余线控方案",
        aliases=[
            "two-box",
            "twobox",
            "分体式线控制动",
            "ibooster+esp",
            "双冗余线控刹车",
        ],
        summary="由电子制动助力器（如博世iBooster）与车身电子稳定程序（ESP）两套独立物理总成组成的线控制动方案，具备极佳的物理硬件级安全冗余。",
        description=(
            "在Two-Box方案中，电子助力器负责常规踩踏刹车与轻度制动建压，ESP控制单元负责防抱死与极限车身姿态纠偏。"
            "当其中任意一套总成出现供电或通信故障时，另一套系统可独立接管提供完整的100%全额驻车制动力，在高阶自动驾驶车型中广受青睐。"
        ),
        technical_principles=[
            "iBooster机电伺服助力总成与ESP车身稳定总成双向解耦与总线热备协同",
            "分布式制动液压管路物理隔离与故障自动安全仲裁切换",
        ],
        advantages=[
            "天然具备双重物理硬件级冗余，满足高阶无人驾驶极端可靠性安全要求",
            "模块拆分更易于在不同紧凑机舱空间内灵活布置",
        ],
        limitations=[
            "相比One-Box体积与线束重量略重，建压响应速度比One-Box稍慢数十毫秒",
        ],
        representative_vehicles=["特斯拉早期Model S/X", "大众ID.4", "部分高阶智驾测试车"],
        standard_labels=["Two-Box制动", "双重制动冗余", "iBooster助力", "高可靠架构"],
        equivalence_group_id=None,
        sales_talking_points=[
            "对于特别看重无人驾驶绝对安全备份的用户，说明Two-Box拥有独立双系统热备份，即使一套系统故障另一套也能稳稳刹停。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 14. 48V 电动主动防倾杆系统
    TechnologyEntity(
        id="generic_active_stabilizer_bar",
        name="48V 电动主动防倾杆系统 (Active Roll Stabilization)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="48V Active Roll Stabilization (ARS)",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="车身控制/主动横向抗侧倾",
        aliases=[
            "主动防倾杆",
            "主动稳定杆",
            "48v防倾杆",
            "ars",
            "主动抗侧倾系统",
            "active roll stabilization",
        ],
        summary="横梁中央配备高扭矩48V伺服电机的主动稳定杆，在车辆急转弯时主动施加反向扭转力矩抵消侧倾，让重达2.5吨的豪华大车实现‘过弯零侧倾’。",
        description=(
            "传统机械防倾杆是一根固定刚度钢棒，过弯虽能抗侧倾但在直道压单侧坑洼时会引起车身恼人的左右横晃。48V主动防倾杆在直道行驶时电机解耦断开，"
            "左右车轮完全独立跳动滤震极佳；一旦检测到高速入弯，电机毫秒级施加高达1200N·m反向反扭力矩，硬生生把车身扳平，过弯姿态如贴地滑行。"
        ),
        technical_principles=[
            "48V无刷行星齿轮减速伺服电机驱动左右断开式稳定杆施加动态预紧扭矩",
            "横向加速度传感器前馈与方向盘转角闭环协同姿态控制",
        ],
        advantages=[
            "高速劈弯时车身侧倾角度被强行压缩在1度以内，驾驶信心与舒适感极高",
            "直线行驶完全解耦，大幅提升单侧过坑洼颠簸时的后排乘坐平稳性",
        ],
        limitations=[
            "需要全车配备48V高功率低压电气供电系统，电机及减速器成本极其高昂",
        ],
        representative_vehicles=["保时捷卡宴(PDCC)", "奥迪SQ7", "宾利添越", "宝马X5 M"],
        standard_labels=["主动防倾杆", "48V抗侧倾", "过弯零侧倾", "豪华底盘黑科技"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向追求极致驾驶质感的SUV客户演示：‘坐在高重心的豪华大SUV里以80公里时速盘桥过急弯，车身完全平平的没有半点向外甩的感觉。’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 15. 高压电驱液压全主动悬架
    TechnologyEntity(
        id="generic_hydraulic_full_active_suspension",
        name="高压电驱液压全主动悬架系统 (Fully Active Suspension)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Electro-Hydraulic Fully Active Suspension",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="悬架控制/全主动能量做功悬架",
        aliases=[
            "全主动悬架",
            "液压全主动悬架",
            "全主动底盘",
            "fully active suspension",
            "电驱液压悬架",
        ],
        summary="取消传统防倾杆、由各车轮独立高压电驱液压泵主动推拉车轮的终极底盘悬架，能在路面剧烈起伏时反向伸缩车轮，实现‘车轮跳动、车身绝对悬浮不动’。",
        description=(
            "不同于空气悬架和CDC只能被动吸收路面能量，全主动悬架各轮端配备超大功率电机泵执行器，能主动对外做功拉起或压下车轮。"
            "当车轮遇到减速带时，电机泵瞬间吸起车轮跨过坎坷；过坑时主动向下蹬紧车轮，甚至能实现车辆原地原地跳舞、原地跳跃跳石与三轮平衡行驶的奇迹表现。"
        ),
        technical_principles=[
            "45V-800V高压伺服电驱集成双向微型液压泵驱动独立液压缸做功",
            "全向三维动力学六自由度超高频（>100Hz）实时前馈闭环控制",
        ],
        advantages=[
            "车身完全与路面物理起伏解耦，车头堆叠香槟塔高速碾压连续坎水滴不洒",
            "彻底消除过弯侧倾、急刹点头与加速仰头，达成悬架物理极限性能",
        ],
        limitations=[
            "造价极其昂贵且系统功率消耗较高，目前仅定位于百万级超旗舰车型",
        ],
        representative_vehicles=["蔚来ET9(天行底盘)", "保时捷Panamera(Active Ride)", "仰望U9(云辇-X)"],
        standard_labels=["全主动悬架", "香槟塔不倒", "电驱液压泵", "底盘终极科技"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向追求顶奢豪车的高净值客户介绍全主动悬架：这是底盘技术的皇冠明珠，能让颠簸烂路彻底变成如镜水面般的纯平滑行。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 16. eLSD 电子限滑差速器系统
    TechnologyEntity(
        id="generic_electronic_limited_slip_differential",
        name="eLSD 电子限滑差速器系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Electronic Limited-Slip Differential (eLSD)",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="传动与限滑/电子机械多片离合差速锁",
        aliases=[
            "elsd",
            "电子限滑差速器",
            "后桥elsd",
            "电子差速锁",
            "多片离合限滑差速器",
        ],
        summary="位于驱动桥内部通过电控多片离合器毫秒级无级分配左右车轮扭矩的高性能差速器，过弯时将更多扭矩推向外侧车轮消除推头，脱困时瞬间锁死单侧打滑轮。",
        description=(
            "传统开放差速器在单侧车轮打滑时整车失去动力，而机械差速锁锁死后无法在铺装路面高速转弯。eLSD由电机或电液执行器精确压紧离合器片，"
            "从0%完全开放到100%完全刚性锁止仅需数十毫秒。高速出弯时主动将扭矩偏置至外侧车轮，产生横摆力矩把车头拉入弯心，极大提升循迹极限。"
        ),
        technical_principles=[
            "电机驱动滚珠斜坡或电液比例阀压紧湿式多片离合器摩擦片",
            "集成车轮滑移率、方向盘角度及横摆角速度实时前馈多维差速控制",
        ],
        advantages=[
            "出弯能更早更深踩加速踏板，彻底消除前驱/四驱车辆出弯‘推头转向不足’",
            "在冰雪、泥泞对开路面行驶，动力自动瞬间转移至有附着力车轮，脱困极强",
        ],
        limitations=[
            "相比普通差速器机构零件多、自重增加，且长期高负荷漂移磨损离合器片",
        ],
        representative_vehicles=["极氪001 FR", "阿尔法·罗密欧Giulia", "宝马M3", "领克03+ Cyan"],
        standard_labels=["eLSD电子限滑", "消除推头", "扭矩主动偏置", "出弯加速神兵"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向驾驶爱好者重点推介：有了eLSD，过急弯时感觉像是有一只无形的手死死把车头往弯道内侧拉，出弯一脚油门车尾极度听话平稳。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 17. 弯道制动扭矩矢量控制系统
    TechnologyEntity(
        id="generic_torque_vectoring_brake",
        name="弯道制动扭矩矢量控制系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Torque Vectoring by Braking (TVbB)",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="底盘动态控制/轻量化电子扭矩矢量",
        aliases=[
            "扭矩矢量制动",
            "弯道制动控制",
            "cbc弯道制动",
            "内侧轮微制动",
            "电子扭矩分配",
        ],
        summary="依靠ESP对弯道内侧车轮实施微小精准点刹来消除转向不足的轻量化底盘控制技术，无需昂贵硬件即可显著提升过弯犀利度。",
        description=(
            "在车辆高速入弯时，系统检测到前轮即将发生推头滑动趋势，立刻通过ESP液压阀对弯道内侧后轮或前轮施加微弱制动力。"
            "内侧受阻如同圆规支点，瞬间在车身质心产生向弯心旋转的横摆力矩，帮助车辆稳稳顺滑咬合弯道切线，显著提升极限过弯速度。"
        ),
        technical_principles=[
            "利用现有ESP/ESC刹车液压阀系高精度独立脉冲轮缸建压控制",
            "整车偏航角速度误差实时反馈与横向加速度前馈联合PID补偿",
        ],
        advantages=[
            "无需额外增加任何笨重昂贵的机械差速器硬件，依靠纯软件算法全面提升操控性",
            "对于前驱或经济型纯电车而言能极大改善原厂底盘的过弯笨重感",
        ],
        limitations=[
            "依靠刹车片摩擦消耗部分动力，在极限赛道连续激烈跑圈时刹车负荷与热衰退增加",
        ],
        representative_vehicles=["福特福克斯", "保时捷PTV(基础版)", "广汽传祺影豹", "比亚迪海豹(iTAC包含类似制动介入)"],
        standard_labels=["制动扭矩矢量", "内侧点刹助转", "消除推头", "软件操控增强"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向注重灵动操控的年轻买家说明：这项技术就像老司机在弯道里悄悄帮你轻轻带了一脚内侧车轮刹车，让你过急弯也能从容自如不飘。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),

    # 18. 路面预瞄魔毯悬架系统
    TechnologyEntity(
        id="generic_road_preview_suspension",
        name="路面预瞄魔毯悬架系统 (Road Preview Active Suspension)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Road Preview Active Magic Carpet Suspension",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="底盘感知/前瞻视觉地形扫描预调节",
        aliases=[
            "魔毯悬架",
            "路面预瞄",
            "魔毯底盘",
            "智能魔毯",
            "路况预瞄悬架",
            "road preview",
        ],
        summary="融合前置双目摄像头或激光雷达以每秒数十次频率扫描前方路面起伏，提前预知减速带坑洼并在车轮压过前50毫秒调整悬架软硬的高阶智慧底盘。",
        description=(
            "传统底盘再优秀也是在车轮压上坑洼颠簸‘挨打了’之后才被动响应。魔毯预瞄系统将智驾感知系统与底盘域打通，在车前5至15米处以毫米级精度重构路面高程图；"
            "在车轮即将接触减速带前微秒级主动释放阻尼软化悬架吞噬震动，过坎之后立即复原支撑，让车内乘员几乎感受不到减速带的存在。"
        ),
        technical_principles=[
            "前视立体视觉双目测距与激光雷达三维点云微高程提取算法",
            "车辆行驶轨迹与车轮触地点前馈时序预测与阻尼电磁阀提前建压",
        ],
        advantages=[
            "彻底破解被动悬架的滞后性，颠簸化解于无形，乘员平稳如坐魔毯",
            "大幅减缓颠簸对车身骨架和内饰零件的冲击疲劳，提升整车长期静谧性",
        ],
        limitations=[
            "暴雪冰封、积水反光严重或暴雨浓雾极端能见度下前视光学识别精度会有所衰减",
        ],
        representative_vehicles=["奔驰S级(魔毯智能空气悬挂)", "理想L9(智能魔毯)", "鸿蒙智行问界M9(途灵底盘)", "蔚来ET7(4D舒适领航)"],
        standard_labels=["魔毯悬架", "路面预瞄", "前瞻摄像头扫描", "减速带如履平地"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "现场带客户过展厅门口的减速带，体验车轮轻轻碾过而水杯里的水完全不起波澜的奇妙魔毯滤震感，豪华说服力极强。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="悬架形式",
    ),
]

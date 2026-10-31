"""
Xiaomi Proprietary Automotive Technology Registry (src/terminology/brands/xiaomi.py).
Contains 30 comprehensive proprietary technologies for Xiaomi EV.
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

XIAOMI_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 小米 800V 碳化硅高压平台 (V800架构) (Original)
    TechnologyEntity(
        id="xiaomi_v800_sic",
        name="小米 800V 碳化硅高压平台 (V800架构)",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi 800V Silicon Carbide High-Voltage Architecture (V800)",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高压超快充与碳化硅电控平台",
        aliases=[
            "v800",
            "800v",
            "800v架构",
            "800v碳化硅",
            "800v高压碳化硅",
            "v800架构",
            "v800电车架构",
            "小米800v",
            "871v",
            "871v高压平台",
            "碳化硅高压平台",
            "全栈800v碳化硅",
            "小米超充",
            "小米v800",
        ],
        summary="小米汽车全栈自研800V高压平台，最高工作电压高达871V，全栈采用高规格碳化硅（SiC）芯片，实现充电15分钟补能510公里的极速补能体验。",
        description=(
            "小米V800架构（真800V全栈碳化硅高压平台）是小米SU7高配车型的核心技术支柱。最高电压达到871V，在电机、电控、空调压缩机、充电机、OBC及DC-DC"
            "全链路采用碳化硅功率器件。相比传统400V架构，发热更少、功率密度更高，极大压缩了服务区充电时间，并提升了能耗利用率。"
        ),
        technical_principles=[
            "最高871V电气绝缘与耐压设计，全链路碳化硅MOSFET功率半导体应用",
            "自研高压线束与集成式热管理热泵系统",
            "超大充电倍率支持（最高4C充电），充电峰值功率突破300kW以上",
        ],
        advantages=[
            "充电速度极快，在特来电/国家电网/自建超充桩上充电15分钟补能超500km",
            "碳化硅导通与开关损耗相比传统IGBT降低60%以上，续航更扎实",
            "全链路800V而非400V升压假800V，系统级综合工况效率极高",
        ],
        limitations=[
            "碳化硅芯片及高耐压组件制造成本昂贵，通常配置在25-30万以上高配车型（如SU7 Max）",
            "在老旧20-30kW低功率快充桩上无法完全发挥800V极致充电优势",
        ],
        sub_variants={
            "V800全栈800V (871V)": "配置于SU7 Max与Ultra，全碳化硅+宁德时代麒麟电芯",
            "400V全域平台 (486V)": "配置于SU7标准版与Pro版，平衡成本与性能",
        },
        representative_vehicles=["小米SU7 Max", "小米SU7 Ultra"],
        standard_labels=["800V高压架构", "全栈碳化硅SiC", "871V真800V", "4C超快充", "极速补能"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "对经常自驾远行或关注充电排队时间的用户，突出喝一杯咖啡（15分钟）补能510公里的无感体验；",
            "科普“真800V（871V）全链路碳化硅”与部分竞品“仅电池升压的伪800V”的能耗与发热差异。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 2. 小米摩德纳平台架构 (Original)
    TechnologyEntity(
        id="xiaomi_modena",
        name="小米摩德纳平台架构",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Modena Platform Architecture",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="智能纯电整车模块化架构",
        aliases=[
            "摩德纳",
            "摩德纳架构",
            "摩德纳平台",
            "modena",
            "小米摩德纳",
            "modena架构",
        ],
        summary="小米汽车正向自研的智能纯电动车底盘平台，深度融合全栈高压、一体化大压铸、CTB倒置电芯与低风阻空气动力学设计。",
        description=(
            "摩德纳平台是小米历时多年、耗资超百亿从底层正向研发的纯电技术底座。平台不仅涵盖了轻量化高刚度前后车身悬架几何，"
            "还原生支持五十余项整车跨域无感升级，具备极低重心（443mm）与极佳的前后轴荷比（50:50），赋予车辆超跑级操控基础。"
        ),
        technical_principles=[
            "全栈模块化底盘平台设计，预留单电机后驱、双电机四驱及三电机超级四驱拓展能力",
            "三电系统与大压铸车身底板物理融合，前双叉臂+后五连杆全铝悬架匹配",
        ],
        advantages=[
            "实现Cd 0.195全球超低风阻系数车身比例",
            "实现443mm超低整车质心，过弯极限和防侧倾表现极强",
        ],
        limitations=[
            "目前首期仅推出轿车品类，SUV及MPV车型平台拓展落地需后续产品迭代",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7", "小米SU7 Pro", "小米SU7 Max", "小米SU7 Ultra"],
        standard_labels=["智能纯电整车架构", "50:50轴荷比", "全铝双叉臂五连杆", "低风阻超跑姿态"],
        equivalence_group_id=None,
        sales_talking_points=[
            "强调小米并非代工组装，而是从零自研模具与底盘结构的正向原生大厂平台。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 3. 小米超级电机 (V6 / V6s / V8s) (Original)
    TechnologyEntity(
        id="xiaomi_hyperengine",
        name="小米超级电机 (V6 / V6s / V8s)",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi HyperEngine Super Motors (V6/V6s/V8s)",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="超高转速永磁同步电驱",
        aliases=[
            "小米电机",
            "小米超级电机",
            "v8s",
            "v6s",
            "v6",
            "v8s电机",
            "27200rpm",
            "hyperengine",
            "小米v8s",
        ],
        summary="小米自研高性能驱动电机系列，其中V8s电机转速高达27200rpm，采用960MPa超高强度特种硅钢与双向立体油冷技术，单电机功率高达425kW (578PS)。",
        description=(
            "小米超级电机突破行业转速天花板，V6/V6s电机转速达21000rpm，自研V8s电机转速达27200rpm（预研转速更突破35000rpm）。"
            "通过超高强度硅钢片保证转子在巨大离心力下不解体，双向立体油冷实现定子和转子全方位直接散热，实现连续高功率输出不衰减。"
        ),
        technical_principles=[
            "超高屈服强度硅钢片（960MPa），定转子微米级极间隙控制",
            "双向立体油冷技术：定子全温区油道+转子内部S型穿轴油冷",
            "全SiC电控高频开关技术，电机最高效率达98.11%",
        ],
        advantages=[
            "极致极速与持续高负荷输出能力（整车极速超300km/h甚至350km/h）",
            "高功率密度，体积重量比同功率传统电机降低25%以上",
        ],
        limitations=[
            "超高转速对轴承寿命与动平衡工艺要求极高，V8s量产初期单机成本高昂",
        ],
        sub_variants={
            "HyperEngine V6": "转速21000rpm，功率220kW，400V架构专用",
            "HyperEngine V6s": "转速21000rpm，功率275kW，800V碳化硅架构专用",
            "HyperEngine V8s": "转速27200rpm，功率425kW (578匹马力)，峰值扭矩635N·m",
        },
        representative_vehicles=["小米SU7", "小米SU7 Max", "小米SU7 Ultra"],
        standard_labels=["超高转速电机", "27200rpm", "双向立体油冷", "超大马力电驱", "赛道级持续输出"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向年轻性能车爱好者突出百公里加速（SU7 Max 2.78秒，Ultra 1.98秒）与连续多次弹射不限扭矩的硬核实力；",
            "对比特斯拉Plaid等传统竞品，突出自研高转速与散热工艺的全球领先参数。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 4. 小米 CTB 一体化电池技术 (倒置电芯) (Original)
    TechnologyEntity(
        id="xiaomi_ctb_battery",
        name="小米 CTB 一体化电池技术 (倒置电芯)",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Inverted-Cell CTB Integrated Battery",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="电池车身一体化与高安全泄压",
        aliases=[
            "小米ctb",
            "倒置电芯",
            "小米倒置电芯",
            "ctb倒置电芯",
            "小米电池",
            "ctb",
            "ctb电池",
        ],
        summary="采用独特的电芯倒置技术与CTB电池车身一体化，泄压阀朝下定向喷发，实现77.8%超高体积利用率和车内乘员舱极致安全隔离。",
        description=(
            "小米与宁德时代联合研发CTB电池包，创新性地采用电芯倒置安装方案。当电池遭遇极端热失控时，高温高压喷发物直接朝车底喷出，"
            "完全杜绝向乘员舱蔓延。同时双大面水冷板面积达7.8m²，实现强劲控温。"
        ),
        technical_principles=[
            "电芯泄压阀倒置朝向地面，防爆阀与电气连接上下隔离",
            "165片气凝胶隔热垫与7.8平米超大冷却面积",
        ],
        advantages=[
            "极端热失控下乘员舱0火0烟，安全冗余高",
            "释放车顶高度17mm，轿跑车型后排头部空间显著宽敞",
        ],
        limitations=[
            "底盘遭遇极强下部托底穿刺时，倒置防爆阀保护需强化底部防护装甲",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Max", "小米SU7 Pro"],
        standard_labels=["CTB倒置电芯", "电池车身一体化", "乘员舱零热失控扩散", "超薄电池包"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向客户说明坐姿不顶头的原因正是由于薄型倒置电芯，兼顾舒适空间与消防级物理安全。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 5. 小米超级大压铸技术 (9100t) (Original)
    TechnologyEntity(
        id="xiaomi_gigacasting",
        name="小米超级大压铸技术 (9100t)",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi 9100t Super Die-Casting (Titans Metal)",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="一体化高压铸造车身结构",
        aliases=[
            "小米大压铸",
            "小米超级大压铸",
            "9100t",
            "9100吨压铸",
            "泰坦合金",
            "一体化大压铸",
        ],
        summary="自研9100吨超大锁模力一体化压铸集群与自研泰坦合金材料，将后地板72个零件一体压铸为1个，减少840个焊点。",
        description=(
            "小米整车后地板采用9100吨超级一体化压铸机一次压铸成型。自研了高强高韧免热处理铝合金材料“小米泰坦合金”，"
            "车身减重17%，后地板结构刚度大幅提升，并设计了三段式可维修溃缩缓冲防撞结构以降低售后维修成本。"
        ),
        technical_principles=[
            "超大吨位高压冷室压铸，AI实时质检",
            "三段式防撞设计：易损碰撞区采用螺栓连接吸能盒，大压铸本体避开低速碰撞区",
        ],
        advantages=[
            "整车轻量化，车身整体性及扭转刚度高",
            "巧妙解决了一体化压铸车主最担心的“小磕碰整车报废”高保费痛点",
        ],
        limitations=[
            "极高速重大恶性事故导致压铸主骨架形变时仍需大型专业工位维修",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7", "小米SU7 Max", "小米SU7 Ultra"],
        standard_labels=["一体化大压铸", "9100t压铸", "后地板一体成型", "高强免热处理合金"],
        equivalence_group_id=EquivalenceDomain.GIGACASTING_STRUCTURE,
        sales_talking_points=[
            "针对客户关于“一体化压铸撞了修不起、保费贵”的顾虑，主动讲解小米三段式可拆卸维修缓冲设计，打消疑虑。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 6. Xiaomi HyperOS 澎湃智能座舱操作系统
    TechnologyEntity(
        id="xiaomi_hyperos",
        name="小米澎湃智能座舱操作系统 (HyperOS)",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi HyperOS Smart Cockpit System",
        category=TechCategory.COCKPIT_OS,
        subcategory="跨端统一原生人车家全生态OS",
        aliases=[
            "澎湃os",
            "hyperos",
            "小米澎湃",
            "澎湃车机",
            "人车家全生态",
            "车机手机互联",
        ],
        summary="小米‘人车家全生态’核心操作系统，1.49秒极速开机，手机应用免安装上车流转，中控屏自由分屏与无缝桌面协同。",
        description=(
            "基于骁龙8295旗舰芯片与小米澎湃底层Linux内核重构，支持手机靠近车机无缝跨屏流转。手机微信定位一键上车，"
            "手机刷视频上车直接在中控大屏继续播，Pad直接吸附后排变控车扩展屏，全屋米家智能家居在中控实时感知控制。"
        ),
        technical_principles=[
            "HyperConnect分布式设备跨端互联网络",
            "动态渲染流水线与硬件级加速，触控跟手时延极低",
        ],
        advantages=[
            "生态无敌：国内数亿米粉设备丝滑联动，操作逻辑完全同手机平板一致零学习成本",
            "车机冷启动速度仅1.49秒，挂D挡即可出发，完全无等待感",
        ],
        limitations=[
            "部分深度联动功能非小米手机用户体验会有微小差异",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7全系", "小米SU7 Ultra"],
        standard_labels=["澎湃OS", "HyperOS", "人车家互联", "1.49秒极速开机", "跨端流转"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "带客户上车演示：‘手机往中控一放，手机界面立刻出现在大屏上，甚至后排吸两个iPad就能让后排朋友调节空调和座椅，米家生态体验无与伦比！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 7. CarloT 物理接口拓展生态
    TechnologyEntity(
        id="xiaomi_carlot",
        name="小米 CarloT 车载智能硬件拓展生态",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi CarloT Hardware Expansion Ecosystem",
        category=TechCategory.COCKPIT_OS,
        subcategory="中控大屏四向磁吸与物理拓展坞接口",
        aliases=[
            "carlot",
            "物理按键拓展",
            "屏幕拓展按键",
            "螺纹拓展接口",
            "磁吸支架接口",
        ],
        summary="屏幕四向预留标准螺纹接口与中控扩展物理按键配件，支持实体空调按键、香氛机、手机支架自由插拔拓展。",
        description=(
            "为了兼顾极简科技感与实体机械按键手感，小米首创中控大屏四周标准机械物理螺纹与Pin脚拓展接口。"
            "用户可随时吸附安装手感极佳的实体空调风量按键琴键面板、双表盘拓展仪表或专属手机无线充支架，软硬一体随心定制。"
        ),
        technical_principles=[
            "标准1/4螺纹机械固定与隐藏式Pogo-Pin多功能电气通信",
            "车机总线协议自动识别插入外设并动态加载UI驱动",
        ],
        advantages=[
            "彻底解决纯触控盲操不便痛点，满足喜欢机械按键质感的传统车主",
            "官方与第三方周边配件生态极丰富，车内个性化空间巨大",
        ],
        limitations=[
            "拓展配件需额外选装购买",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7全系"],
        standard_labels=["CarloT", "物理按键扩展", "螺纹拓展接口", "Pogo-Pin", "个性化座舱"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "针对嫌电车全触控屏幕开车盲操不安全的客户：‘看中控大屏下面，我们一秒就能咔嗒吸上机械实体按键，盲操调节温度手感极佳！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 8. Xiaomi Pilot Max 全栈自研高阶智驾系统
    TechnologyEntity(
        id="xiaomi_pilot_max",
        name="小米高阶智驾系统 Xiaomi Pilot Max",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Pilot Max Autonomous Driving System",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="端到端大模型全场景智能辅助驾驶",
        aliases=[
            "xiaomi pilot",
            "xiaomi pilot max",
            "小米智驾",
            "小米pilot",
            "端到端代客泊车",
            "城市领航辅助",
        ],
        summary="搭载双NVIDIA DRIVE Orin芯片与超远距激光雷达，全系标配端到端大模型无图城市领航辅助与代客泊车AVP。",
        description=(
            "Xiaomi Pilot Max配备508TOPS算力双Orin-X、一体式激光雷达、11颗高清摄像头及12颗超声波雷达。"
            "采用端到端感知大模型与端到端决策规控一体化算法，支持复杂路口借道绕行、跨楼层代客泊车与极窄机械库位自动停入。"
        ),
        technical_principles=[
            "感知决策端到端神经网络架构模型",
            "激光雷达与4D毫米波雷达时间空间双重对齐",
        ],
        advantages=[
            "机械车位与断头路车位泊入成功率行业顶尖",
            "城市领航变道果断丝滑，无高精地图依赖全国都能开",
        ],
        limitations=[
            "标准版车型配备Xiaomi Pilot单芯片纯视觉版，无激光雷达",
        ],
        sub_variants={
            "Xiaomi Pilot Pro": "单Orin-X 84TOPS纯视觉方案，支持高速NOA",
            "Xiaomi Pilot Max": "双Orin-X 508TOPS+禾赛超远距激光雷达，支持城市全场景NOA",
        },
        representative_vehicles=["小米SU7 Max", "小米SU7 Pro", "小米SU7 Ultra"],
        standard_labels=["Xiaomi Pilot", "端到端智驾", "激光雷达", "城市NOA", "代客泊车AVP"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "展示小米实测代客泊车视频：‘车停在车库门口人直接下车走人，车子自己下地库找车位倒进去，遇到会车还会主动倒车避让！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 9. 小米 SU7 Ultra 三电机巅峰四驱系统
    TechnologyEntity(
        id="xiaomi_triple_motor_ultra",
        name="小米 SU7 Ultra 三电机巅峰四驱系统",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi SU7 Ultra Tri-Motor Peak AWD Powertrain",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="赛道级三电机全矢量超跑动力",
        aliases=[
            "su7 ultra",
            "小米三电机",
            "1548马力",
            "双v8s",
            "纽北战车",
            "su7ultra动力",
        ],
        summary="由两台V8s电机加一台V6s电机组成的巅峰三电机四驱系统，综合最大马力高达1548匹，零百加速仅需1.98秒。",
        description=(
            "后轴搭载双V8s电机（单台425kW），前轴搭载一台V6s电机（288kW），整车峰值功率达到1138kW（1548PS）。"
            "极速突破350km/h，配备赛道专用高功率三元锂赛道电池与全碳纤维轻量化车身套件，原型车征战纽伯格林北环创全球四门车最速纪录。"
        ),
        technical_principles=[
            "双V8s后轴同轴异构超紧凑集成驱动总成",
            "后轴左右轮扭矩独立矢量无级差速动态分配（每秒500次调校）",
        ],
        advantages=[
            "零百加速1.98秒，0-200km/h仅需5.86秒，极速超350km/h",
            "连续纽北跑圈动力不降额不热过载",
        ],
        limitations=[
            "旗舰超跑定位，售价与轮胎磨损成本相对较高",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Ultra"],
        standard_labels=["三电机四驱", "1548马力", "零百1.98秒", "极速350km/h", "纽北最速四门车"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向追求极致性能的超跑用户阐述：‘1548匹马力，直接干翻百万保时捷和特斯拉Plaid，在纽北刷出全球最速纪录的中国顶级超跑！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 10. 小米闭环空气悬架与 CDC 连续阻尼控制
    TechnologyEntity(
        id="xiaomi_air_cdc_suspension",
        name="小米智能闭环空气悬架与 CDC 减振系统",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Closed-Loop Air Suspension with CDC Damping",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="智能自适应阻尼与闭环空簧底盘",
        aliases=[
            "小米空悬",
            "小米空气悬架",
            "闭环空悬",
            "小米cdc",
            "自适应阻尼悬架",
        ],
        summary="采用闭环空气弹簧与连续可变阻尼减振器，支持车身高度±50mm调节与五挡高度设定，兼顾超跑低趴姿态与烂路通过性。",
        description=(
            "相比开式空气悬架，闭环系统充气响应速度提升数倍且抗外界温湿度干扰强。配合前后CDC电磁阻尼阀，"
            "系统每秒扫描路况1000次，过弯时智能拉紧外侧悬架抑制侧倾，高速巡航时自动下沉车身降低风阻。"
        ),
        technical_principles=[
            "集成储气罐闭环充放气拓扑架构，气动效率高",
            "加速度与轮位传感器全时采样配合CDC比例电磁阀控制",
        ],
        advantages=[
            "上下车迎宾模式自动降至最低姿态，优雅便捷",
            "兼具运动驾驶贴地感与高级行政轿车滤震质感",
        ],
        limitations=[
            "仅标准配备于SU7 Max及高阶配置车型",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Max", "小米SU7 Ultra"],
        standard_labels=["闭环空气悬架", "CDC连续阻尼", "五挡车身高度调节", "运动底盘调校"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向注重驾控高级感的车主说明：‘高速上车身自动降得像超跑一样贴地，遇到地库陡坡一键升起底盘绝不托底，既帅气又实用！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 11. 小米碳纤维运动空气动力学套件
    TechnologyEntity(
        id="xiaomi_carbon_aero_kit",
        name="小米碳纤维全车空气动力学套件",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Carbon Fiber Aerodynamics Kit",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="轻量化热压罐碳纤维风洞气动套件",
        aliases=[
            "碳纤维套件",
            "小米碳纤维",
            "大尾翼",
            "碳纤维前唇",
            "赛道下压力",
        ],
        summary="全车采用超大面积热压罐级真碳纤维空气动力学套件，在高速和赛道状态下提供高达285kg超强整车下压力。",
        description=(
            "涵盖超大固定碳纤维尾翼、碳纤维车顶、碳纤维侧裙、前唇及车尾主动扩散器。不仅整车减重数十公斤，"
            "更利用赛道风洞流体动力学精准设计，将高速空气高效转化为贴地负压，显著提升过弯横向抓地极限。"
        ),
        technical_principles=[
            "航天级T700高强碳纤维预浸料热压罐成型",
            "CFD流体动力学与风洞实车多倾角气动平衡",
        ],
        advantages=[
            "最高提供285kg下压力，300km/h极速行驶车身极其稳固贴地",
            "质感无敌，真碳纤维纹理兼具极致战斗视觉冲击",
        ],
        limitations=[
            "纯碳纤维配件磕碰后需专业碳纤维修复或更换",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Ultra", "小米SU7运动外观选装包"],
        standard_labels=["碳纤维套件", "赛道下压力", "空气动力学", "真碳车顶", "超稳过弯"],
        equivalence_group_id=None,
        sales_talking_points=[
            "带客户近距离欣赏碳纤维纹理：‘这可不是贴纸，而是正儿八经和超跑同规格的热压罐干碳纤维，车顶、尾翼全都是，高速稳得像吸在地上！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 12. 小米自研泰坦合金 (Titans Metal)
    TechnologyEntity(
        id="xiaomi_titan_alloy",
        name="小米自研泰坦合金材料",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Titans Metal (Heat-Treatment-Free Alloy)",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="高强高韧免热处理压铸专用铝合金材料",
        aliases=[
            "泰坦合金",
            "小米泰坦合金",
            "免热处理合金",
            "自研铝合金",
            "titans metal",
        ],
        summary="小米联合国家级重点实验室自研的超强韧免热处理压铸铝合金材料，流动性强、成型无缩孔且杜绝了热处理形变。",
        description=(
            "大型一体化压铸零件面积超大，传统铝合金需高温淬火热处理极易扭曲变形。小米通过自研材料配方与AI算法模拟上千种微量元素配比，"
            "成功研制出兼具超高屈服强度与良好延伸率的泰坦合金，无需热处理即可满足9100吨大压铸后地板的严苛刚度与抗冲击要求。"
        ),
        technical_principles=[
            "稀土微合金化配方与晶界强化阻碍位错扩展",
            "免固溶热处理自时效强化工艺",
        ],
        advantages=[
            "消除热处理翘曲变形缺陷，零件尺寸精度达毫米级",
            "抗冲击韧性优异，发生严重碰撞时有效吸能不开裂",
        ],
        limitations=[
            "专属冶炼母合金配方成本高",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7全系", "小米SU7 Ultra"],
        standard_labels=["泰坦合金", "免热处理铝合金", "高强韧材料", "一体化压铸专用", "车身轻量化"],
        equivalence_group_id=EquivalenceDomain.GIGACASTING_STRUCTURE,
        sales_talking_points=[
            "突出小米底层材料科学研发实力：‘从材料配方开始自己搞，泰坦合金保证了大压铸又轻又硬，撞击变形不断裂，技术底子非常硬！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 13. 小米 0.195Cd 超低风阻流体设计
    TechnologyEntity(
        id="xiaomi_aerodynamic_drag",
        name="小米 0.195Cd 全球超低风阻空气动力学设计",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi 0.195Cd Ultra-Low Aerodynamic Drag Design",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="风洞优化极致低阻流体工程",
        aliases=[
            "0.195cd",
            "小米风阻",
            "超低风阻",
            "鹅卵石后视镜",
            "空气动力学风阻",
        ],
        summary="历经数十次风洞实验打磨出全球量产轿车最低风阻系数之一（Cd 0.195），百公里纯电高速电耗大幅降低。",
        description=(
            "全车设计了8组风道、17个真风口以及水滴形鹅卵石激光雷达、流线后视镜与平整底盘护板。"
            "高速行驶时空气阻力是最大电耗杀手，风阻系数每降低0.01可增加续航10公里以上，0.195Cd为小米SU7赋予了扎实的高速超长续航。"
        ),
        technical_principles=[
            "前机舱盖曲面气流引导与前轮外侧侧气帘导流",
            "全平化整车底盘底护板与后下扩散器顺畅导流",
        ],
        advantages=[
            "高速能耗极低，CLTC续航轻松突破800km甚至830km",
            "大幅减小高速风噪，营造极为静谧的高级座舱氛围",
        ],
        limitations=[
            "极致流线造型对后备箱垂直掀背开口高度略有妥协",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7标准版", "小米SU7 Pro", "小米SU7 Max"],
        standard_labels=["0.195Cd风阻", "超低风阻", "空气动力学", "高速省电", "超低风噪"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向算能耗账的用户算一笔账：‘0.195全球超低风阻，让你在高速跑120km/h的时候电量不狂掉，续航不虚标，省下的就是真金白银！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 14. 小米电动升降尾翼与主动格栅
    TechnologyEntity(
        id="xiaomi_su7_tail_wing",
        name="小米电动升降后扰流板与 AGS 主动进气格栅",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Electric Rear Spoiler & AGS Active Grille Shutter",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="主动智能可变空气动力学套件",
        aliases=[
            "小米电动尾翼",
            "电动尾翼",
            "升降尾翼",
            "ags进气格栅",
            "主动进气格栅",
        ],
        summary="支持四挡角度可调的电动升降尾翼与智能开闭主动进气格栅，兼顾低速低风阻与高速高稳定性下压力。",
        description=(
            "后尾翼具备0°、5°、12°、25°四挡高度与角度电动调节，提供最大130kg下压力；"
            "车头AGS进气格栅根据热管理与冷却需求自动开合，关闭时减阻提升续航，全开时快速为三电系统散热。"
        ),
        technical_principles=[
            "车速传感器与制动G值信号联动自动触发",
            "步进电机微步精准定位与防夹保护机制",
        ],
        advantages=[
            "高速大脚刹车时尾翼自动升起充当空气制动减速伞",
            "支持车机屏幕或物理按键随心手动开启，仪式感与帅气拉满",
        ],
        limitations=[
            "北方冰雪暴雪天气需注意手动清理缝隙积雪防结冰阻滞",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Max", "小米SU7 Ultra", "小米SU7 Pro(选配)"],
        standard_labels=["电动尾翼", "四挡调节", "AGS主动进气格栅", "空气制动", "拉风造型"],
        equivalence_group_id=None,
        sales_talking_points=[
            "按动中控按钮为客户展开尾翼：‘看这个电动尾翼，不仅帅得像保时捷，跑高速还能自动升起来压紧车身，超车变道稳如泰山！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 15. 小米碳陶瓷高性能制动系统
    TechnologyEntity(
        id="xiaomi_ceramic_brakes",
        name="小米高性能碳陶瓷制动盘与 Akebono 卡钳",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Carbon Ceramic Brake Kit with Akebono Calipers",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="赛道级耐极温碳陶制动总成",
        aliases=[
            "小米碳陶刹车",
            "超大碳陶盘",
            "akebono卡钳",
            "430mm刹车盘",
            "超跑制动系统",
        ],
        summary="前盘直径达430mm全球乘用车最大尺寸碳陶瓷盘之一，搭配前六活塞高性能运动卡钳，百公里刹停距离低至30.8米。",
        description=(
            "专为小米SU7 Ultra研发的高性能碳陶制动套件，耐受温度超过1300℃，搭配定制高性能制动皮。"
            "连续10次以上超高速全力紧急制动完全零热衰减，总重量相比同尺寸铸铁刹车盘减重超57公斤，极大解放簧下质量。"
        ),
        technical_principles=[
            "碳化硅强化碳纤维复合基体材料",
            "前六活塞固定式对向高刚度一体锻造卡钳",
        ],
        advantages=[
            "100-0km/h制动距离仅30.8米，安全刹车边界极高",
            "极大幅度减轻轮端旋转惯量，转向手感轻盈灵敏",
        ],
        limitations=[
            "主要配备于赛道旗舰版本，低温未暖盘状态制动有微小碳陶摩擦声音",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Ultra"],
        standard_labels=["碳陶刹车盘", "Akebono卡钳", "30.8米制动距离", "零热衰退", "超跑制动"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向追求极速安全的客户强调：‘跑得快更要刹得住！430mm巨大碳陶盘配六活塞卡钳，百公里刹停只要30米出头，带给你绝对的安全底气！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 16. 小米双大面立体电池液冷技术
    TechnologyEntity(
        id="xiaomi_water_cooling_battery",
        name="小米双大面立体电芯液冷系统",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Dual-Surface High-Efficiency Liquid Cooling",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="超大面积电芯直接水冷控温技术",
        aliases=[
            "双大面水冷",
            "小米电池冷却",
            "7.8平米水冷板",
            "立体冷却流道",
        ],
        summary="双大面电芯直接贴合液冷板设计，换热面积高达7.8m²为行业平均值的3倍，实现极限持续充电不过热降额。",
        description=(
            "传统电池包仅在电芯底部铺设单块冷板，电芯上下温差大。小米采用双侧大面冷却流道，冷板面积拓展至7.8平方米，"
            "即使在盛夏40℃高温环境下以300kW以上大功率超充，电芯温升依然能稳定控制在最适宜区间，保护电池寿命不衰减。"
        ),
        technical_principles=[
            "微通道挤出铝合金蛇形水冷流道",
            "高导热结构胶全贴合传热设计",
        ],
        advantages=[
            "散热能力提升300%，快充末端依然保持高电流不降频",
            "电芯间温差控制在2℃以内，大幅延长动力电池整车寿命",
        ],
        limitations=[
            "冷却管路密集度高，制造气密性测试标准极严",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Max", "小米SU7 Ultra"],
        standard_labels=["双大面水冷", "7.8平米冷板", "超充不过热", "电池长寿命", "高效均温"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "夏天长途充电极力推荐：‘很多电车大夏天超充一会儿就烫得降速，小米7.8平米超级水冷就像给每个电芯装了直吹空调，充电又快又稳！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 17. 小米全自研高频碳化硅逆变功率模块
    TechnologyEntity(
        id="xiaomi_inverter_sic",
        name="小米自研第三代 SiC 碳化硅功率模块",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi 3rd Generation SiC Power Inverter Module",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="高开关频率耐高温碳化硅电控核心",
        aliases=[
            "小米碳化硅逆变器",
            "自研sic模块",
            "碳化硅电控",
            "高频sic",
            "电驱逆变器",
        ],
        summary="小米深度自研的SiC碳化硅MOSFET功率电控模块，耐压高达1200V，电控最高效率高达99.85%。",
        description=(
            "采用自主定制纳米银烧结工艺与铜线键合结构，大幅降低寄生电感与开关损耗。在极小体积内承受高达750A以上持续工作电流，"
            "将电能近乎零损耗地转化为驱动机械能，是小米SU7强劲弹射起步和超低综合电耗的核心秘密武器。"
        ),
        technical_principles=[
            "双面银烧结高导热低热阻封装",
            "微型化低杂散电感母排电气集成",
        ],
        advantages=[
            "电控效率高达99.85%，电能转换损耗降至极限",
            "体积缩小45%，极大降低整车电驱总成重量",
        ],
        limitations=[
            "对SiC衬底晶圆制造品质与纯度依赖高",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Max", "小米SU7 Ultra"],
        standard_labels=["自研碳化硅", "SiC逆变器", "99.85%电控效率", "纳米银烧结", "超强耐压"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "强调电控自研硬实力：‘碳化硅芯片直接自研封装，损耗少了电车续航自然就实打实更长，每度电都用在刀刃上！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 18. 纽北级全赛道散热系统
    TechnologyEntity(
        id="xiaomi_track_cooling_system",
        name="小米纽北级全赛道高效冷却系统",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Nürburgring-Grade Track Cooling System",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="全工况赛道级大功率散热热管理",
        aliases=[
            "赛道冷却系统",
            "纽北散热",
            "小米赛道冷却",
            "超大风道散热",
            "三电机散热",
        ],
        summary="专为严苛赛道全功率刷圈打造的高效冷却循环，支持连续跑纽北北环两圈动力不衰减、不过热限扭。",
        description=(
            "普通纯电车在赛道激烈驾驶半圈往往因电池或电机过热进入‘乌龟模式’限速。小米赛道冷却系统配备双大功率电子风扇、"
            "超大前格栅通风散热水箱及独立电机润滑油冷回路，散热功率高达40kW以上，保障1548匹马力全开狂飙不软脚。"
        ),
        technical_principles=[
            "大流量变频水泵与高压独立冷却循环双分区架构",
            "电机转子中心轴高速注油喷射冷却流道",
        ],
        advantages=[
            "真正能下赛道的纯电超跑，告别开两圈就过热趴窝的尴尬",
            "赛道连续高负荷弹射起步与极限极速测试动力稳定如一",
        ],
        limitations=[
            "赛道全力散热模式下机舱高速风扇运转声音较为明显",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Ultra"],
        standard_labels=["赛道冷却", "纽北不限扭", "40kW散热功率", "全功率刷圈", "赛道级热管理"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向性能车发烧友保证：‘别家电车下赛道跑半圈就限扭，小米SU7 Ultra在纽北连续跑完20多公里最严酷赛道，动力依旧满格输出！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 19. 2000MPa 超高强笼式钢铝混合车身
    TechnologyEntity(
        id="xiaomi_ultra_high_steel",
        name="小米 2000MPa 铠甲笼式钢铝混合车身",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi 2000MPa Armored Hybrid Steel-Aluminum Cage Body",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="超强被动碰撞安全与超高扭转刚度",
        aliases=[
            "2000mpa车身",
            "铠甲笼式车身",
            "小米车身安全",
            "51000扭转刚度",
            "潜艇级热成型钢",
        ],
        summary="整车扭转刚度突破51000 N·m/deg超越百万级劳斯莱斯，全车关键骨架采用2000MPa潜艇级热成型钢与高强铝合金。",
        description=(
            "乘员舱A柱、B柱、顶梁采用超高强度热成型钢闭环笼式设计，高强钢与铝合金占比超过90.1%。"
            "在国内外最严苛的偏置碰撞、侧柱碰与车顶静压测试中，乘员舱A柱完全零弯曲变形，全车车门碰撞后一把拉开逃生。"
        ),
        technical_principles=[
            "超高强度热成型冲压与激光拼焊一体化骨架",
            "三条独立碰撞载荷分散路径将撞击力快速引流至全车底板",
        ],
        advantages=[
            "51000 N·m/deg行业顶级刚度，彻底消除车身过坎异响，操控扎实感爆棚",
            "碰撞被动安全达到C-NCAP、E-NCAP全球双五星超标水平",
        ],
        limitations=[
            "超高强度钢材冲压工艺与模具制造成本极高",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7全系", "小米SU7 Ultra"],
        standard_labels=["2000MPa热成型钢", "51000刚度", "铠甲车身", "碰撞零变形", "五星安全标准"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "给最注重安全的家庭用户看刚度数据：‘51000的扭转刚度比劳斯莱斯幻影还要硬！A柱B柱全是2000兆帕潜艇钢，开在路上就是移动的安全堡垒！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 20. 56 英寸超宽视角 AR-HUD
    TechnologyEntity(
        id="xiaomi_56_inch_hud",
        name="小米 56 英寸超宽全景 AR-HUD 抬头显示",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi 56-Inch Ultra-Wide Panoramic AR-HUD",
        category=TechCategory.COCKPIT_OS,
        subcategory="大画幅沉浸式增强现实行车投影",
        aliases=[
            "56英寸hud",
            "小米ar-hud",
            "小米hud",
            "全景hud",
            "超大抬头显示",
        ],
        summary="投影画幅高达56英寸、视场角达10度×3.6度超宽视角的AR-HUD，亮度达13000nit强光直射依旧清晰通透。",
        description=(
            "不仅显示车速、限速与导航方向，更将车道引导箭头、前车跟车动态光带与周围行人车辆识别框直接三维融合投影在前风挡外7.7米路面上，"
            "配合自适应环境光敏调节，无论烈日正射还是深夜隧道进出，画面始终清爽锐利、绝不眩晕。"
        ),
        technical_principles=[
            "自由曲面反射光学放大镜与DLP高对比度光机",
            "低延迟图形渲染引擎与智驾感知目标实时重叠",
        ],
        advantages=[
            "画幅超大，重要路况信息一目了然，驾驶全程目光完全不离开正前方",
            "13000nit超高亮度，戴偏光墨镜也能清晰看清投影内容",
        ],
        limitations=[
            "仅配备于高配版本（SU7 Max与Ultra），选装成本相对较高",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Max", "小米SU7 Ultra"],
        standard_labels=["56英寸AR-HUD", "13000nit超高亮", "全景抬头显示", "车道级AR导航"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "让客户坐进驾驶位体验：‘一抬头眼前就是56英寸超大影院级AR导航，箭头直接贴在真实马路上，开车完全不用低头看仪表盘！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 21. 翻转式运动液晶行车仪表屏
    TechnologyEntity(
        id="xiaomi_flip_instrument",
        name="小米 7.1 英寸翻转式运动全液晶仪表屏",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi 7.1-Inch Rotating Sports Driver Display",
        category=TechCategory.COCKPIT_OS,
        subcategory="机械电动翻转行车运动仪表",
        aliases=[
            "翻转仪表",
            "小米翻转屏",
            "翻转仪表盘",
            "开机翻转",
            "运动仪式感仪表",
        ],
        summary="踩下刹车一键启动时优雅电动翻转展开的7.1英寸全液晶仪表，带来如迈凯伦超跑般的专属启动仪式感。",
        description=(
            "中控行车仪表在熄火锁车时收纳翻平，纯平极简；当车主携带钥匙上车或踩下制动踏板时，"
            "仪表台内置微型静音电机驱动屏幕平稳翻转直立，显示精炼纯粹的胎压、时速、动能及赛道挡位数据，科技仪式感拉满。"
        ),
        technical_principles=[
            "超微型步进减速电机与双连杆铰链翻转机构",
            "防卡滞防夹力矩检测与开机信号微秒级唤醒",
        ],
        advantages=[
            "每次启动出行的专属高定仪式感，深受年轻车主喜爱",
            "不遮挡正前方宽阔驾驶视野，信息排布极简专注驾驶",
        ],
        limitations=[
            "机械翻转机构日常使用需注意避免在中控台堆放硬物杂物阻挡翻转",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7全系", "小米SU7 Ultra"],
        standard_labels=["翻转仪表", "启动仪式感", "超跑同款翻转屏", "专注驾驶", "极简科技"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "让客户亲自按下一键启动：‘看！一脚刹车踩下去屏幕优雅翻转立起来，就像价值千万的迈凯伦超跑，每次开车都充满仪式感！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 22. 小米双模直接式宽温域高效热泵
    TechnologyEntity(
        id="xiaomi_dual_mode_heat_pump",
        name="小米双模直接式综合高效热泵系统",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Dual-Mode Direct Heat Pump Thermal Management",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="全气候三电与座舱冷媒直热集成架构",
        aliases=[
            "小米热泵",
            "双模热泵",
            "直接式热泵",
            "宽温域双模热泵",
            "超低温制热",
        ],
        summary="全球首创双模直接式高效热泵，直接在-20℃极寒天气下不依赖高耗电PTC完成座舱采暖与电池快速预热。",
        description=(
            "整合了直接式电驱余热回收与冷媒直热循环两大模式。在北方冬季，直接利用电机电控运转微小余热并倍增转化为座舱暖风，"
            "将冬季低温续航达成率提升至同级领先水平，徹底摆脱电车‘冬天不敢开暖风’的刻板印象。"
        ),
        technical_principles=[
            "多通阀全集成式换热矩阵与双级压缩补气增焓",
            "电池直冷直热与乘员舱冷媒回路跨域耦合控制",
        ],
        advantages=[
            "超低温度制热COP能效高达2.2以上，大幅节省电池电量",
            "极速除霜除雾，冷车启动吹出暖风仅需几十秒",
        ],
        limitations=[
            "在零下25℃以下极端冰冻天气仍需辅助加热冗余",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7全系", "小米SU7 Ultra"],
        standard_labels=["双模热泵", "宽温域制热", "冷媒直冷直热", "冬季电耗优化", "余热回收"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "解决北方买车最大痛点：‘自研双模热泵直接从电机里抽余热吹暖风，冬天零下15度车里暖和如春，续航依然坚挺！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 23. 小米自适应 ADB 矩阵大灯
    TechnologyEntity(
        id="xiaomi_adaptive_beam",
        name="小米自适应 ADB 智能矩阵大灯",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Adaptive ADB Matrix LED Headlights",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="智能车灯高精动态避让与远光矩阵",
        aliases=[
            "小米矩阵大灯",
            "adb大灯",
            "水滴大灯",
            "自适应矩阵大灯",
            "不眩目远光",
        ],
        summary="采用四透镜水滴造型自适应ADB矩阵大灯，照明距离突破400米，夜间长开远光自动抠图避让对向来车不眩目。",
        description=(
            "大灯造型灵感源自大自然水滴，内嵌高精度LED矩阵发光芯片与智能感知相机联动。"
            "当系统检测到对向来车或前方同向跟车时，毫秒级独立熄灭对应区域的单个像素光源，在保证路面全景大范围照亮的同时杜绝让前车司机晃眼。"
        ),
        technical_principles=[
            "分区独立驱动高功率LED发光单元",
            "智能辅助驾驶视觉摄像头前向车辆识别与动态光斑遮蔽算法",
        ],
        advantages=[
            "400米超远夜间照射视野，极大提前发现路边行人和动物隐患",
            "夜间走国道高速全程自动远光，无需手忙脚乱频繁切近光",
        ],
        limitations=[
            "前挡风摄像头区域如果遭遇泥泞严重遮挡需先刮洗干净",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7全系", "小米SU7 Ultra"],
        standard_labels=["ADB矩阵大灯", "400米超远照射", "自动防眩目", "水滴大灯", "夜间安全"],
        equivalence_group_id=None,
        sales_talking_points=[
            "强调夜间行车安全：‘夜里跑国道长开远光完全不用管，对面来车大灯自动把对方车牌和驾驶室位置扣黑，对方不晃眼，你的路看得清清楚楚！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 24. CarWith 智能跨端手机互联框架
    TechnologyEntity(
        id="xiaomi_carwith",
        name="小米 CarWith 智慧跨端车机互联系统",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi CarWith Intelligent Cross-Device Framework",
        category=TechCategory.COCKPIT_OS,
        subcategory="跨品牌手机与车机无感无线投屏互联",
        aliases=[
            "carwith",
            "小米carwith",
            "无线carwith",
            "车机互联",
            "手机投屏",
        ],
        summary="专为各品牌智能手机量身打造的无线车机互联框架，支持无线秒级自动连接、导航投屏与全生态语音操控。",
        description=(
            "CarWith支持除小米手机外的主流安卓智能设备及CarPlay深度互联。上车即连无感投屏，"
            "将手机中的高德/百度地图、QQ音乐、网易云音乐无损投射至车机大屏，且车机大屏触控指令可反向操作手机，延迟低至数十毫秒。"
        ),
        technical_principles=[
            "Wi-Fi 6高速局域直连与低延迟音视频编码压缩传输",
            "多分辨率动态适配渲染引擎与车端麦克风降噪回传",
        ],
        advantages=[
            "非小米手机用户同样享受顶级车机互联体验，开放包容",
            "支持双向无线音频与导航无缝巡航流转",
        ],
        limitations=[
            "极老旧机型可能不支持Wi-Fi 5G频段直连",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7全系"],
        standard_labels=["CarWith", "无线投屏", "车机互联", "开放生态", "极低时延"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向非小米手机用户打消顾虑：‘即便你用的是苹果或者其他品牌手机，小米汽车全面支持CarPlay和CarWith，上车秒连同样极其丝滑！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 25. 小米智能机械车位泊车与代客泊车 (AVP)
    TechnologyEntity(
        id="xiaomi_pinpoint_parking",
        name="小米全场景机械库位与代客泊车系统",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Precision Mechanical & Automated Valet Parking (AVP)",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="高精度极窄车位与复杂多层代客泊车",
        aliases=[
            "机械车位泊车",
            "小米代客泊车",
            "极窄泊车",
            "avp代客泊车",
            "遥控泊车",
        ],
        summary="业内公认最强量产机械车位泊车系统，支持窄至车身仅多出10cm的极窄机械立体车位一把停入与离车遥控入库。",
        description=(
            "依托四轮独立高精度轮速测距与激光雷达/环视摄像头毫米级点云融合，精准识别立体机械升降车位的窄铁轨边缘与立柱。"
            "遇到极窄车位人无法开门时，车主可先下车，在手机APP上轻轻滑动，车辆自动收起后视镜自主对正泊入，停好自动熄火锁车。"
        ),
        technical_principles=[
            "超声波与环视相机融合近场盲区三维点云重建",
            "厘米级轨迹动态重规划与全线控精准刹车方向微调",
        ],
        advantages=[
            "解决绝大多数新手司机甚至老司机最头疼的‘地下老旧立体机械车位’痛点",
            "支持人在车外手机遥控进出，再狭窄的死胡同和车位也能停",
        ],
        limitations=[
            "地下车位地面严重积水反光时需按系统提示慢速监视泊入",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Max", "小米SU7 Pro", "小米SU7 Ultra"],
        standard_labels=["机械车位泊车", "AVP代客泊车", "遥控泊入", "窄车位神器", "毫米级精度"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "现场带客户看实测视频：‘很多大商场地库只有老式机械立体车位，别人不敢停，小米汽车一把就能自己倒进去，停好自动锁车，太省心了！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 26. 小米自研 ASIL-D 级电池智能管理系统 (BMS)
    TechnologyEntity(
        id="xiaomi_bms_thermal",
        name="小米全自研 ASIL-D 级高安全电池管理系统 (BMS)",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi ASIL-D High-Safety Battery Management System",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="毫秒级电芯全生命周期安全监控与云端防护",
        aliases=[
            "小米bms",
            "asil-d电池管理",
            "电池健康管理",
            "云端电池管家",
            "电芯全时监控",
        ],
        summary="达到汽车功能安全最高级别ASIL-D认证的自研BMS系统，全天候24小时毫秒级监控每颗电芯电压温度与微短路先兆。",
        description=(
            "结合车端边缘计算与小米云端AI超算中心，全生命周期跟踪记录电池健康度与阻抗变化趋势。"
            "能提前上百小时预警早期微小内部短路或绝缘异常，杜绝热失控风险隐患，实现电池10年衰减率极低。"
        ),
        technical_principles=[
            "电化学阻抗谱（EIS）车端在线快速测量技术",
            "多核安全冗余架构MCU与双路隔离采样芯片",
        ],
        advantages=[
            "最高功能安全ASIL-D认证，严防过充、过放、高温与短路",
            "云端大模型联动，充电时自动匹配最健康放电电流策略",
        ],
        limitations=[
            "极长期处于地下完全无网络覆盖车库时云端协同预警需在车辆出库后同步",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7全系", "小米SU7 Ultra"],
        standard_labels=["自研BMS", "ASIL-D最高安全", "电芯毫秒监控", "阻抗在线测量", "防自燃预警"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向注重安全可靠的家庭用户解释：‘ASIL-D是汽车行业最严的安全认证，24小时连着云端AI盯着每一个电芯，开十年电池依然安全健康！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 27. 小米全场景人车家互联生态协议
    TechnologyEntity(
        id="xiaomi_human_car_home",
        name="小米‘人车家全生态’无缝硬件互联协议",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Human x Car x Home Hardware Protocol",
        category=TechCategory.COCKPIT_OS,
        subcategory="万物互联端到端软硬件互联框架",
        aliases=[
            "人车家全生态协议",
            "米家上车",
            "车载智能家居控制",
            "离家回家模式",
            "小米生态协议",
        ],
        summary="打通手机、汽车与全屋米家智能硬件底层协议，快到家时自动开空调煮饭，在车内即可通过小爱同学掌控全屋一切。",
        description=(
            "通过HyperConnect协议，车载小爱同学无缝连接全屋上千种米家智能硬件。"
            "回家途中快到小区2公里时，车机自动触发‘回家场景’：客厅空调自动调至舒适温度、空气净化器开启、电热水器开始加热；离家自动锁门关闭全车全屋电器。"
        ),
        technical_principles=[
            "地理围栏自动触发技术配合端到端安全身份认证",
            "低功耗蓝牙、局域网与蜂窝跨网关统一路由通信",
        ],
        advantages=[
            "行业唯一具备完整手机、汽车、全屋智能家居全闭环生态体系",
            "操作简单自然，一句话掌控所有家庭设备",
        ],
        limitations=[
            "智能家居控制依赖家庭网络及米家智能硬件设备",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7全系", "小米SU7 Ultra"],
        standard_labels=["人车家全生态", "米家联动", "地理围栏场景", "智能家居控制", "HyperConnect"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向追求智慧生活品质的车主演示：‘快到家时跟车机说一句马上到家了，家里空调、灯光、热水器自动全开好，真正的未来智能生活！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 28. 小米赛道级全主动底盘预研系统
    TechnologyEntity(
        id="xiaomi_full_active_chassis",
        name="小米全主动智能底盘悬架系统",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Fully Active Intelligent Chassis System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="高压电驱全主动悬架与极限姿态控制",
        aliases=[
            "小米全主动悬架",
            "小米全主动底盘",
            "全主动悬架",
            "原地起跳",
            "主动悬架预研",
        ],
        summary="采用48V高压电驱全主动执行机构，具备四轮独立举升控制，实现全速过弯0侧倾与颠簸路面完全悬浮的‘磁悬浮飞毯’体验。",
        description=(
            "小米前瞻自研全主动智能底盘，每个减振器配备独立高功率伺服电机执行器，直接输出高达数千牛的主动举升或下压力。"
            "完全摆脱传统防倾杆和减振器弹簧的机械耦合束缚，支持连续过减速带车身水平如镜，甚至支持车辆原地离地起跳脱困。"
        ),
        technical_principles=[
            "高压大扭矩伺服电机执行单元与滚珠丝杠机械放大",
            "路面超宽带毫米波雷达预瞄与前馈毫秒级运控算法",
        ],
        advantages=[
            "实现真正意义上的车身全维度零俯仰、零侧倾",
            "面对剧烈坑洼路段车厢如悬浮在半空般平稳",
        ],
        limitations=[
            "系统造价与能耗要求极高，首期搭载于旗舰超级车型或作为预研前瞻技术发布",
        ],
        sub_variants={},
        representative_vehicles=["小米全主动底盘技术原型车", "小米SU7 Ultra未来进化版"],
        standard_labels=["全主动底盘", "48V主动悬架", "0侧倾0俯仰", "磁悬浮体验", "前瞻底盘技术"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "展示小米全主动底盘过坎原地起跳与0侧倾视频，证明小米不仅做座舱厉害，在硬核机械底盘领域同样具备全球顶尖自研技术！",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 29. 小米四活塞高性能运动卡钳与打孔通风盘
    TechnologyEntity(
        id="xiaomi_brembo_brakes",
        name="小米四活塞高性能 Brembo 制动系统",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi Brembo Four-Piston Sport Brake Kit",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="大尺寸打孔通风刹车盘与对向卡钳",
        aliases=[
            "brembo卡钳",
            "小米四活塞",
            "布雷博卡钳",
            "打孔通风盘",
            "33.3米刹车",
        ],
        summary="标配前对向四活塞Brembo运动铝合金卡钳与大尺寸打孔通风盘，实现百公里刹车距离仅33.3米的卓越制动水准。",
        description=(
            "在SU7 Max上标配原厂Brembo前对向四活塞铝合金固定卡钳，配合大直径高导热螺旋通风打孔刹车盘。"
            "制动脚感极其线性坚实，抗热衰退能力出色，连续长下坡或激烈跑山制动衰减极微，刹车信心极其充足。"
        ),
        technical_principles=[
            "对向四活塞液压均匀压紧刹车皮",
            "定向螺旋通风孔道快速引流空气带走摩擦热",
        ],
        advantages=[
            "100-0km/h制动距离短至33.3米，同级别纯电轿跑领跑水准",
            "原厂运动卡钳色彩丰富（黄/红），视觉运动感极强",
        ],
        limitations=[
            "激烈驾驶后刹车盘边缘有轻微粉尘，需定期洗车清洁",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7 Max", "小米SU7 Pro(选装)"],
        standard_labels=["Brembo卡钳", "四活塞制动", "33.3米刹停", "打孔通风盘", "线性脚感"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "试驾中带客户体验大脚急刹：‘33.3米刹停距离！踩下去车身稳如泰山，完全没有廉价车的晃晃悠悠，安全感直接拉满！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 30. 小米澎湃大模型智能语音车控助手 (小爱同学)
    TechnologyEntity(
        id="xiaomi_xiaoai_copilot",
        name="小米澎湃大模型小爱同学车控助手",
        brand="小米 (Xiaomi)",
        brand_key="xiaomi",
        english_name="Xiaomi XiaoAI LLM-Powered Voice Co-Pilot",
        category=TechCategory.COCKPIT_OS,
        subcategory="多模态生成式AI大模型车载语音",
        aliases=[
            "小爱同学",
            "车载小爱",
            "小爱大模型",
            "大模型语音助手",
            "车内语音控车",
        ],
        summary="接入端云结合大模型的车载智能助手，具备视觉识别与超强自然语言理解，支持‘看见什么就能问什么’与全车功能深度语音操控。",
        description=(
            "深度融合车载感知摄像头与多音区阵列麦克风。不仅能实现连续语音不唤醒、一次说十个指令依次执行，"
            "更能通过前向摄像头问它‘前面那辆是什么车’、‘右边那座山叫什么名字’，像随车携带了一个无所不知的私人金牌导游。"
        ),
        technical_principles=[
            "端侧高能效推理引擎与云端千亿参数大模型混合架构",
            "全车十音区分区定向波束成形声源定位",
        ],
        advantages=[
            "识别准确率高达99%，支持前后排四独立乘客免唤醒同时对话互不打扰",
            "结合全车摄像头具备多模态视觉问答与百科全书级闲聊陪伴能力",
        ],
        limitations=[
            "涉及复杂百科深度问答时在无信号地下深层车库略有受限",
        ],
        sub_variants={},
        representative_vehicles=["小米SU7全系", "小米SU7 Ultra"],
        standard_labels=["小爱同学", "大模型车控", "免唤醒语音", "视觉问答", "多音区交互"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "带客户上车体验说话：‘小爱同学，把左后车窗降下来一半，副驾座椅加热开到二挡，顺便查一下前面红绿灯还有几秒，一句话全部搞定，极其听话！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),
]

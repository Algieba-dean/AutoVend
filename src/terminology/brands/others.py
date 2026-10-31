"""
Other OEM Proprietary Automotive Technology Registry (src/terminology/brands/others.py).
Contains proprietary technologies for IM, GAC Aion, GWM, Chery, Porsche, Mercedes, BMW.
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

OTHER_OEM_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 智己灵蜥数字底盘
    TechnologyEntity(
        id="im_lizard_chassis",
        name="智己灵蜥数字底盘",
        brand="智己汽车 (IM Motors)",
        brand_key="im",
        english_name="IM Digital Lizard Chassis",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="主动底盘控制与全数字线控四轮转向",
        aliases=[
            "灵蜥",
            "灵蜥数字底盘",
            "灵蜥底盘",
            "智己底盘",
            "智己灵蜥",
            "lizard chassis",
            "im lizard",
            "灵晰底盘",
            "灵蜥算法",
            "智慧四轮转向",
            "后轮转向",
            "智己后轮转向",
            "蟹行模式",
        ],
        summary="上汽集团与智己全栈自研的智慧数字底盘系统，主打全数字线控联控、智慧四轮后轮转向（双向共12度大转角）及全场景蟹行平移能力。",
        description=(
            "智己灵蜥数字底盘以中央智慧数字中枢为大脑，将后轮转向、空气悬架、电控阻尼减振器（CDC）、四轮电驱动及制动系统全面统合控制。"
            "可实现双向最高12度的后轮转向，令近5米长的大车转弯半径仅为4.99米（比大众Polo更灵活），并具备对角线斜向平移的‘蟹行模式’，"
            "有效解决断头路倒车、狭窄侧方泊车及高速突发冰雪路面打滑摆尾问题。"
        ),
        technical_principles=[
            "整车全域数字X/Y/Z三轴六自由度协同运动控制算法",
            "大转角后轮线控主动转向机构与四轮扭矩矢量分配深度融合",
            "毫秒级路面工况预瞄与姿态防倾防翻控制闭环",
        ],
        advantages=[
            "大车开出小车感：转弯半径打破行业极限（4.99米），狭窄地库一把调头",
            "极致窄位泊车脱困：独创蟹行模式支持斜向横移入位，告别侧方停车前后刮碰",
            "单侧湿滑积水路面紧急制动跑偏抑制率达80%以上",
        ],
        limitations=[
            "大角度后轮转向机构对底盘后轴悬架安装空间占用较大",
            "线控系统控制复杂度高，极寒冰雪工况下防尘密封耐久性要求苛刻",
        ],
        sub_variants={
            "灵蜥标准版": "全数字底盘协同控制+CDC可变阻尼",
            "灵蜥高阶版": "全架构线控四轮转向+空悬+CDC+蟹行模式",
        },
        representative_vehicles=["智己L6", "智己LS6", "智己L7"],
        standard_labels=["灵蜥数字底盘", "智慧四轮转向", "蟹行模式", "后轮转向", "超小转弯半径", "防甩尾"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "向新手司机或女性车主重点介绍：灵蜥底盘让近5米长大车比飞度还灵活，窄胡同掉头一把过，路边侧方停车斜着滑进车位；",
            "向注重安全操控的客户强调：高速下暴雨单边积水压过去不偏舵不失控，底盘每秒计算千次主动帮你稳住车身。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 2. 广汽埃安弹匣电池 2.0 系统
    TechnologyEntity(
        id="gac_magazine_battery",
        name="广汽埃安弹匣电池2.0系统",
        brand="广汽埃安 (GAC Aion)",
        brand_key="gac_aion",
        english_name="GAC Aion Magazine Battery 2.0 System",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高安全电芯与动力电池系统防护",
        aliases=[
            "弹匣电池",
            "弹匣电池2.0",
            "广汽弹匣电池",
            "埃安弹匣电池",
            "magazine battery",
            "弹夹电池",
            "弹匣系统",
        ],
        summary="广汽埃安自研的高安全动力电池系统安全技术，以‘弹匣安全舱’独立网格隔热与自愈型涂层闻名，通过整包枪击与针刺不起火严苛试验。",
        description=(
            "广汽埃安弹匣电池通过超高耐热稳定电芯、超强隔热电池安全舱、极速降温三维速冷系统以及全时第5代电池管理系统（BMS）四维安全防线，"
            "实现动力电池从单体电芯热失控到整包阻断无热蔓延。"
            "升级的弹匣电池2.0更引入了纳米陶瓷航空级隔热气凝胶与自愈合电解液技术，行业首创通过‘军用步枪子弹贯穿不起火爆燃’极限试验。"
        ),
        technical_principles=[
            "独立安全网格弹匣舱设计，隔绝单体电芯热蔓延向相邻电芯扩散",
            "相变吸热降温微晶材料与高通量双向液冷板高效压制温升",
            "全时微秒级BMS电池监控预警与主动灭火排气导流通道",
        ],
        advantages=[
            "无论是三元锂还是磷酸铁锂体系，整包针刺均实现不起火、不爆炸",
            "极端恶劣底盘刮底托底穿刺工况下具备极高安全冗余，电池自燃概率接近于零",
        ],
        limitations=[
            "多重防护装甲与厚绝热隔层在一定程度上增加了电池包整体结构死重",
            "电池包体积成组效率略受防爆格舱隔板占用影响",
        ],
        sub_variants={
            "弹匣电池1.0": "整包针刺不起火磷酸铁锂/三元锂系统",
            "弹匣电池2.0": "枪击贯穿不起火，搭载超耐热纳米气凝胶与自愈合体系",
        },
        representative_vehicles=["AION Y Plus", "AION S MAX", "AION V", "昊铂GT", "昊铂HT"],
        standard_labels=["弹匣电池", "针刺不起火", "枪击不起火", "电池安全舱", "纳米隔热气凝胶", "零自燃"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向对新能源自燃心存芥蒂的谨慎客户重点剖析：弹匣电池通过了子弹射击穿透测试都不起火，日常碰撞穿刺更是固若金汤；",
            "强调广汽埃安累计上百万辆营运与家用车保有量下的极佳自燃安全口碑记录，打消电池寿命与安全性疑虑。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 3. 长城 Hi4 / Hi4-T 智能电混四驱系统
    TechnologyEntity(
        id="gwm_hi4_hybrid",
        name="长城Hi4/Hi4-T智能电混四驱系统",
        brand="长城汽车 (GWM)",
        brand_key="gwm",
        english_name="GWM Hi4 / Hi4-T Intelligent Hybrid 4WD Platform",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="前后双电机电混四驱与越野架构",
        aliases=[
            "hi4",
            "hi4-t",
            "长城hi4",
            "长城hi4-t",
            "坦克hi4-t",
            "坦克hi4",
            "智能四驱电混",
            "智能电混",
            "智能混动",
            "hi4t",
            "坦克混动",
            "hi4性能版",
        ],
        summary="长城汽车全栈自研的智能电混四驱架构，以‘两驱的能耗与价格享受四驱的性能’为主打；针对硬派越野专属研发Hi4-T机械纵置混动架构，配备三把锁与非承载大梁。",
        description=(
            "长城Hi4体系包含面向城市SUV的Hi4/Hi4性能版，以及面向硬派越野的Hi4-T。"
            "Hi4通过前后双电机分布式混动架构，前轴双电机（发电+驱动）集成多挡DHT，后轴独立大功率电驱动，彻底消除传统机械四驱传动轴死重，实现智能九种动态工况无缝切换；"
            "Hi4-T则是非承载硬派越野专属，保留完整机械分动箱、传动轴与前后差速锁，电机并联于发动机与纵置9HAT变速箱之间，确保在极端电量耗尽越野脱困时依然拥有100%硬核机械四驱脱困力。"
        ),
        technical_principles=[
            "前后轴双电机分布式串并联混动构型，实现低成本高可靠全工况电四驱",
            "Hi4-T保留机械四驱纵置大梁结构，电机与内燃机双动力无缝叠加，机械三把锁真正硬派脱困",
            "iTVC智能扭矩矢量控制系统毫秒级防滑防甩尾",
        ],
        advantages=[
            "Hi4让城市用户花两驱车的钱买到全时四驱车，雨雪湿滑安全性质的飞跃且馈电油耗仅5L级别",
            "Hi4-T在重度越野攀爬、戈壁冲沙时持续大扭矩输出不衰减，彻底避免纯电四驱越野电机连续高温过热退磁报警的死穴",
        ],
        limitations=[
            "Hi4-T机械大梁结构自重大，日常城市拥堵路段能耗高于城市承载式增程SUV",
            "多挡机械变速齿轮箱在极少数特定急踩刹车又瞬时大脚油门时可能存在极轻微挡位换挡迟疑",
        ],
        sub_variants={
            "Hi4": "前后双电机城市DHT混动电四驱（如哈弗猛龙、枭龙MAX）",
            "Hi4性能版": "三挡DHT电混四驱（如魏牌高山、蓝山智驾版）",
            "Hi4-T": "纵置并联非承载式硬派越野机械混动（如坦克300/400/500/700 Hi4-T）",
        },
        representative_vehicles=["坦克300 Hi4-T", "坦克400 Hi4-T", "坦克500 Hi4-T", "魏牌蓝山智驾版", "哈弗猛龙"],
        standard_labels=["Hi4", "Hi4-T", "智能电混四驱", "机械三把锁", "硬派越野混动", "两驱能耗四驱性能"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "看重越野穿越的硬派玩家强推Hi4-T：‘真正的硬派越野必须有机械大梁和机械传动轴！纯电越野电机连续爬陡坡5分钟就过热趴窝，Hi4-T就算没电了靠发动机和三把锁也能带你平安走出无人区！’",
            "家庭城市SUV客户推荐Hi4：下雨天立交桥打滑、冬天冰雪路面四驱比两驱救命几倍，买Hi4花两驱钱享受四驱安全。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 4. 奇瑞鲲鹏超能混动 C-DM 系统
    TechnologyEntity(
        id="chery_kunpeng_cdm",
        name="奇瑞鲲鹏超能混动C-DM系统",
        brand="奇瑞汽车 (Chery)",
        brand_key="chery",
        english_name="Chery Kunpeng Super Hybrid C-DM",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="超能混动专用发动机与DHT电驱",
        aliases=[
            "鲲鹏超能混动",
            "鲲鹏混动",
            "鲲鹏c-dm",
            "c-dm",
            "cdm",
            "奇瑞混动",
            "鲲鹏cdm",
            "kunpeng c-dm",
            "超能混动cdm",
        ],
        summary="奇瑞汽车打造的第三代超能混动系统，由最高热效率44.5%的第五代ACTECO混动专用发动机、三挡超级电混DHT及全时智能电控组成，综合续航突破1400公里。",
        description=(
            "奇瑞鲲鹏超能混动C-DM以‘技术奇瑞’发动机深厚底蕴为基石。其第五代ACTECO 1.5TGDI发动机具备深度米勒循环、高滚流燃烧室及第四代i-HEC智效燃烧系统，"
            "实现行业顶级44.5%热效率与高升功率。"
            "配合支持全速域并联的三挡DHT或单挡无级电混DHT，可在18km/h极低车速提前切入发动机直驱，"
            "实现零百加速4秒级破百，高速极速超240km/h，百公里馈电油耗低至4.2L，综合续航轻松突破1400km。"
        ),
        technical_principles=[
            "第五代ACTECO高效混动发动机（热效率44.5%）配合深度米勒循环与高压直喷",
            "三挡双电机DHT变速器，全速域串并联与超宽直驱速比覆盖",
            "电池守护者系统抗撞击防起火及极寒-35℃低温冷启动保障",
        ],
        advantages=[
            "发动机热效率高且动力强劲，馈电工况绝无‘小马拉大车’的动力匮乏",
            "极速上限高：多挡DHT使得中后段超车底气强，极速可跑至240km/h，高速巡航极其节油",
            "机械耐造性好：全球严苛工况验证，皮实抗造可靠度极佳",
        ],
        limitations=[
            "三挡机械齿轮箱结构精密，不同工况模式频繁切换时的平顺性软件标定需要持续迭代",
            "品牌年轻化与智能座舱人机交互感知相比新势力仍需进一步强化用户沟通",
        ],
        sub_variants={
            "三挡DHT性能版": "注重中后段高速超车性能与全速域驱动（如星途星纪元ET、风云T9）",
            "无级电混DHT版": "注重极致平顺性与入门家用车极致节油（如风云A8）",
        },
        representative_vehicles=["奇瑞风云T9", "奇瑞风云T10", "星途星纪元ET", "捷途山海T2", "风云A8"],
        standard_labels=["鲲鹏混动", "C-DM", "44.5%热效率", "三挡DHT", "全速域并联", "1400km续航"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "向追求皮实耐用和发动机技术的务实客户重点强调：‘技术奇瑞’发动机全球出口几十万台，44.5%热效率实打实，高速馈电油耗低、动力随叫随到；",
            "对比单挡混动竞品：突出三挡DHT在高速120km/h以后再提速超车更有力，跑长途巡航油耗更省。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 5. 保时捷 Active Ride 与 800V 电气架构
    TechnologyEntity(
        id="porsche_active_ride",
        name="保时捷Active Ride与800V电气架构",
        brand="保时捷 (Porsche)",
        brand_key="porsche",
        english_name="Porsche Active Ride & 800V High Voltage Architecture",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="全主动电液悬架与800V高压快充",
        aliases=[
            "保时捷active ride",
            "active ride",
            "pasm",
            "pscm",
            "保时捷800v",
            "保时捷悬架",
            "保时捷底盘",
            "porsche active ride",
            "active ride悬架",
        ],
        summary="保时捷研发的革命性全主动车身控制底盘与全栈800V高压快充电气架构，每个减振器配独立电动液压泵，以13Hz高频全主动抵消车身侧倾俯仰。",
        description=(
            "保时捷Active Ride颠覆了传统空气弹簧加防倾杆的物理构造，彻底取消了传统机械防倾杆。"
            "每个车轮配备双阀独立减振器，并各自连接一个独立的微型电动液压泵，能够直接主动向减振腔注入高压油液，主动在车轮和车身之间施加巨大推力或拉力。"
            "在急加减速与过弯时，车身完全保持0俯仰0侧倾，甚至能主动像摩托车一样向弯道内侧轻微倾斜抵消离心力。"
            "同时搭配全栈800V高压平台，支持最高320kW直流超快充，10%充至80%仅需18分钟。"
        ),
        technical_principles=[
            "四轮独立高速电动液压泵直驱减振阻尼腔，主动力调节频率高达13Hz",
            "全电控解耦底盘控制体系彻底取代物理机械式横向稳定杆",
            "800V高压直流架构配合高导热油冷电驱与双速比后桥变速器",
        ],
        advantages=[
            "物理极限车身姿态控制：急踩刹车车头不低反微抬，极限弯道0侧倾，彻底消灭乘坐离心眩晕",
            "上下车自适应迎宾：拉开车门瞬间车身毫秒级主动抬高55mm，优雅从容进出",
            "赛道级连续抗热衰：800V高压架构支持几十次弹射起步连续无动力衰减",
        ],
        limitations=[
            "系统依赖高压电网与大功率液压电机，整套底盘系统成本极为昂贵，仅作为保时捷顶配选装",
            "系统结构紧凑精密度极高，售后维修与配件造价高昂",
        ],
        sub_variants={
            "PASM (保时捷主动悬挂管理)": "基础版连续自适应阻尼调节系统",
            "Porsche Active Ride": "旗舰级无防倾杆全主动电动液压悬架系统",
        },
        representative_vehicles=["新款保时捷Taycan", "保时捷Panamera E-Hybrid", "保时捷Macan EV"],
        standard_labels=["Porsche Active Ride", "保时捷底盘", "全主动悬架", "0侧倾", "800V高压", "320kW超充"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "面对追求顶级驾驶仪式感与豪车排面的高净值客户：‘保时捷Active Ride是底盘工业皇冠上的明珠，拉开车门瞬间车身自动跳起迎宾，激烈过弯如贴地飞行毫无侧倾’；",
            "对比普通空气悬架，强调Active Ride是真正的主动液压推拉车身，不是被动受力缓冲，带来真正的跑车级高级感。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 6. 奔驰 EVA 架构与 AMG 高性能电驱系统
    TechnologyEntity(
        id="mercedes_eva_amg",
        name="奔驰EVA架构与AMG高性能电驱系统",
        brand="梅赛德斯-奔驰 (Mercedes-Benz)",
        brand_key="mercedes",
        english_name="Mercedes-Benz EVA Platform & AMG High Performance Electric Drive",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="纯电专属平台与AMG轴向磁通高性能电驱",
        aliases=[
            "奔驰eva",
            "eva架构",
            "eva平台",
            "amg电驱",
            "奔驰amg电驱",
            "4matic+",
            "奔驰纯电架构",
            "mercedes eva",
            "奔驰mma",
        ],
        summary="奔驰大型豪华纯电专属EVA平台与AMG高性能电驱动架构，搭载全轮驱动4MATIC+动态扭矩矢量分配、后轮主动转向系统及下一代超高功率密度轴向磁通电机。",
        description=(
            "梅赛德斯-奔驰EVA（Electric Vehicle Architecture）平台专为中大型及大型纯电轿车与SUV打造，"
            "采用低风阻弓形车身设计（Cd 0.20打破量产车风阻纪录），配备最大108kWh超大高安全电池包与自研智能热管理BMS。"
            "在AMG版本中，搭载前后AMG专属调校永磁同步电机，输出超千牛米扭矩，配合AMG TORQUE 4MATIC+每秒进行10000次轮间扭矩分配，"
            "并引入收购自YASA的下一代超轻量化轴向磁通电机（Axial Flux Motor），能量密度达传统电机三倍。"
        ),
        technical_principles=[
            "EVA纯电专属高刚度轻量化铝合金/高强钢混合车身架构",
            "AMG专属高功率逆变器与陶瓷轴承永磁电机，高转速动态热阻隔冷却",
            "超紧凑轴向磁通电机技术（体积与重量仅为传统径向磁通电机的三分之一）",
        ],
        advantages=[
            "百年奔驰豪华造车底蕴：顶级NVH深海级静谧性与行政级魔毯底盘调校",
            "极限风阻优化带来优秀的真实高速长续航表现（CLTC续航超700-800km）",
            "AMG血统强悍性能：零百加速仅3秒级别，高速再加速底气极其平稳优雅",
        ],
        limitations=[
            "整车弓形车身设计线条偏圆润圆滑，部分传统燃油车大标立标老客户审美接受需一定过程",
            "车机系统智能座舱生态与本土化互联网应用丰富度相比国内新势力存在追赶空间",
        ],
        sub_variants={
            "EVA标准豪华版": "单电机后驱/双电机四驱EQE、EQS豪华舒适取向",
            "AMG高性能电驱版": "前后AMG特调电机，支持漂移模式与超跑声浪模拟（EQE 53 / EQS 53 AMG）",
        },
        representative_vehicles=["奔驰EQS", "奔驰EQE", "奔驰EQE SUV", "AMG EQS 53 4MATIC+"],
        standard_labels=["奔驰EVA", "AMG电驱", "轴向磁通电机", "弓形车身", "低风阻", "行政级豪华"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向追求顶奢豪华品质与品牌沉淀的商务老板讲解：‘百年奔驰做纯电，最核心的就是底盘静音和车身安全性，弓形车身风阻低至0.20，跑高速稳健如高铁，绝无廉价塑料感；’",
            "向追求性能的客户推荐AMG版本：感受AMG专业赛道团队调教的底盘与每秒万次的四驱响应，优雅与狂暴兼得。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 7. 宝马第六代 eDrive 与新世代架构
    TechnologyEntity(
        id="bmw_gen6_edrive",
        name="宝马第六代eDrive电力驱动与新世代平台",
        brand="宝马 (BMW)",
        brand_key="bmw",
        english_name="BMW Gen6 eDrive & Neue Klasse Architecture",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="800V第六代高压电驱与大圆柱电池体系",
        aliases=[
            "第六代edrive",
            "宝马edrive",
            "edrive 6",
            "edrive6",
            "宝马第六代edrive",
            "新世代架构",
            "neue klasse",
            "bmw edrive",
            "宝马大圆柱",
            "bmw neue klasse",
        ],
        summary="宝马革命性的纯电核心架构与新世代（Neue Klasse）技术，全系升级全栈800V高压电气平台、第六代高能量密度大圆柱电芯及全新励磁同步电机，整车能效提升25%。",
        description=(
            "宝马第六代eDrive技术代表了宝马全面迈入纯电正向研发全新纪元的里程碑。"
            "新世代平台彻底摒弃油电共用架构，全栈搭载800V高压系统，采用标准46mm直径的大圆柱锂电池，"
            "电芯能量密度提高20%，续航里程增加30%，充电时间缩短30%（充10分钟跑300公里）。"
            "电驱方面坚持宝马自研自产励磁同步电机（EESM），完全不使用稀土金属，高转速区间无退磁衰减，配合‘超级大脑’域控制器，实现终极纯粹的宝马人车合一操控乐趣。"
        ),
        technical_principles=[
            "无稀土电励磁同步电机（EESM），转子电流可精确矢量调节，高速能效优于永磁电机且完全无磁阻损耗",
            "46mm全新高镍大圆柱电池CTP集成设计配合全栈800V超快充",
            "四大高性能中央超级控制计算机（Super-Brain）统一调度动力、底盘与自动驾驶",
        ],
        advantages=[
            "不依赖稀土环保可持续，高速150km/h以上狂飙没有永磁电机反电动势退磁风险，动力越踩越有",
            "800V大圆柱极速补能：长途充电大幅提速，冬季严寒能效衰减大幅缓解",
            "纯粹驾驶乐趣基因：传承宝马50:50前后重量平衡与敏锐转向质感",
        ],
        limitations=[
            "新世代首款量产车预计2025-2026年全面推向市场，老款在售i3/iX3仍基于第五代技术过渡",
            "大圆柱电芯量产初期的产业链协同与规模化成本需要爬坡时间",
        ],
        sub_variants={
            "第五代eDrive (现款在售)": "400V电励磁同步电机体系（如宝马i3、i4、i5、iX3）",
            "第六代eDrive (新世代标配)": "800V+46系大圆柱电芯+中央超级算力大脑",
        },
        representative_vehicles=["宝马新世代iX3", "宝马新世代轿车概念车", "宝马i4 M50", "宝马i7 xDrive60"],
        standard_labels=["宝马第六代eDrive", "新世代平台", "800V架构", "46大圆柱", "无稀土励磁电机", "人车合一操控"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向追求驾驶操控乐趣的忠实Bimmer说明：‘开宝马电车，要的就是那个指哪打哪的底盘质感！宝马自研励磁电机不含稀土、高速完全不掉力，新世代全栈800V和大圆柱把充电和能效做到极致；’",
            "对比新势力强调百年宝马悬架调校功底：过坎韧性十足，激烈驾驶不眩晕不抛跳。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),
]

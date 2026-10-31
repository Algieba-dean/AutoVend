"""
Zeekr / Geely Proprietary Automotive Technology Registry (src/terminology/brands/zeekr.py).
Contains 30 comprehensive proprietary technologies for Zeekr / Geely High-End EV.
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

ZEEKR_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. SEA 浩瀚智能进化体验架构 (Original)
    TechnologyEntity(
        id="zeekr_sea",
        name="SEA 浩瀚智能进化体验架构",
        brand="吉利 / 极氪 (Zeekr / Geely)",
        brand_key="zeekr",
        english_name="SEA (Sustainable Experience Architecture)",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="全尺寸纯电原创整车开发架构",
        aliases=[
            "浩瀚架构",
            "sea浩瀚",
            "sea架构",
            "浩瀚平台",
            "极氪浩瀚",
            "吉利浩瀚",
            "sea",
        ],
        summary="吉利耗资超200亿耗时5年正向研发的全球化纯电原生架构，轴距带宽覆盖1800mm-3300mm，支持从紧凑型轿车到豪华全尺寸SUV/MPV全覆盖。",
        description=(
            "SEA浩瀚架构是目前行业延展性极强的全球化模块化造车架构。硬件层具备超强结构刚性与纯电防撞吸能体系，全栈支持800V高压电气布局与双叉臂五连杆高端底盘布局；"
            "涵盖了极氪、沃尔沃、极星、Smart、路特斯等全球多品牌核心主力车型。"
        ),
        technical_principles=[
            "全尺寸灵活带宽布局，软硬件解耦与域集中式SOA电子电气架构",
            "原生纯电下车身与一体式热成型门环极致碰撞安全设计",
        ],
        advantages=[
            "底盘机械素质极高，被誉为新能源造车界的操控标杆底座",
            "碰撞安全被动防护表现传承沃尔沃安全基因，极佳的柱碰与翻滚防护",
        ],
        limitations=[
            "因追求极高机械刚性与安全冗余用料，整车自重普遍略微偏重",
        ],
        sub_variants={
            "SEA-E": "紧凑型入门架构（Smart精灵#1、极氪X）",
            "SEA-1 / SEA-2": "中大型高端乘用车架构（极氪001、极氪007）",
            "SEA-M": "未来移动出行及无人驾驶专属架构",
        },
        representative_vehicles=["极氪001", "极氪007", "极氪009", "极氪X", "极越01", "Smart精灵#1", "沃尔沃EM90"],
        standard_labels=["纯电原创架构", "全域800V兼容", "沃尔沃级被动安全", "高延展性底盘架构"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向注重机械操控质感与安全车身的客户推荐：极氪001历经多次严苛碰撞无一自燃的“公路坦克”口碑正是源自SEA浩瀚架构底蕴。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 2. 极氪金砖电池 (800V超快充自研磷酸铁锂) (Original)
    TechnologyEntity(
        id="zeekr_golden_battery",
        name="极氪金砖电池 (800V超快充自研磷酸铁锂)",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Golden Battery (800V LFP)",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="全栈自研800V高安全超快充磷酸铁锂电芯",
        aliases=[
            "金砖电池",
            "金砖",
            "金砖超充电池",
            "极氪金砖",
            "golden battery",
            "金砖二代",
            "金专电池",
            "金专",
        ],
        summary="极氪自研全球量产超快充磷酸铁锂电池，体积利用率高达83.7%，全栈800V高压快充，实现充电15分钟续航增加超500公里，并经受超严苛火烧穿刺测试。",
        description=(
            "金砖电池打破了传统磷酸铁锂电池体积利用率低的瓶颈，采用“三明治”夹层结构与极简结构件设计，将成组体积利用率推至83.7%。"
            "在全栈800V极充桩支持下，最大充电倍率达到4.5C-5.5C，并首创通过“超压针刺+700℃火烧240秒”超国标极限热失控测试。"
        ),
        technical_principles=[
            "电芯内部多极耳结构降低阻抗，配合高导离子电解液突破磷酸铁锂快充瓶颈",
            "专属金色耐高压绝缘防护涂层，绝缘耐压高达4000V",
        ],
        advantages=[
            "兼顾磷酸铁锂的超长使用寿命、高安全性与接近三元锂的快充速度",
            "自研自造有效降低整车终端指导售价，性价比极高",
        ],
        limitations=[
            "受制于磷酸铁锂化学本性，在极度寒冷北方冬季的表显续航达成率仍需依靠热泵与电池预加热保障",
        ],
        sub_variants={
            "金砖一代": "充电15分钟补能500km，4.5C充电倍率",
            "金砖二代": "充电倍率提升至5.5C，充电10.5分钟补能从10%到80%",
        },
        representative_vehicles=["极氪007", "极氪001", "极氪7X"],
        standard_labels=["金砖电池", "800V磷酸铁锂快充", "83.7%体积利用率", "耐高温高压安全电池", "4.5C超充"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "突出“充得快还耐造”：向客户说明这是目前市面上补能速度最快的磷酸铁锂电池，兼具低用车成本与高安全性。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 3. 极氪自研浩瀚智驾系统 (Original)
    TechnologyEntity(
        id="zeekr_haohan_ad",
        name="极氪自研浩瀚智驾系统",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Haohan Intelligent Driving (Haohan AD / G-Pilot)",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="端到端无图高阶智能驾驶系统",
        aliases=[
            "浩瀚智驾",
            "极氪浩瀚智驾",
            "浩瀚智驾系统",
            "浩瀚智驾2.0",
            "浩瀚高阶智驾",
            "极氪智驾",
            "haohan ad",
            "g-pilot",
            "极氪端到端智驾",
            "无图城市nzp",
            "nzp领航",
            "指尖泊车",
            "浩瀚直驾",
        ],
        summary="极氪全栈自研高阶智能驾驶系统，搭载双Orin-X高算力芯片与超长距激光雷达，采用端到端Plus架构与数字先觉网络，支持全国无图城市NZP领航辅助与全场景智能泊车。",
        description=(
            "极氪自研浩瀚智驾（Haohan AD 2.0）是吉利与极氪面向全场景出行的自研智驾解决方案。"
            "硬件层面全系标配激光雷达与双英伟达DRIVE Orin-X芯片（最高508 TOPS算力）；"
            "算法层面引入端到端Plus架构与类人决策大模型，摆脱高精地图依赖，实现全国城市主干道、环岛、狭窄掉头路口丝滑领航；"
            "同时支持全场景遥控泊车、指尖泊车与记忆泊车。"
        ),
        technical_principles=[
            "双NVIDIA DRIVE Orin-X芯片（508 TOPS）+ 超长距顶置激光雷达+高清摄像头多源融合感知",
            "自研端到端Plus大模型架构，将感知与规划决策网络一体化，通行决策拟人化与无图全域覆盖",
            "数字先觉网络（Scenery Prediction Network），提前预判前向加塞与突发异形障碍物",
        ],
        advantages=[
            "全国无图都能开，城市NZP变道果断丝滑，无画龙减速感",
            "机械车位与极窄车位泊车成功率极高，支持离车指尖泊车与遥控泊车",
            "全系标配高规格智驾硬件，OTA高频迭代升级，无需额外高昂买断选装费用",
        ],
        limitations=[
            "早前Mobileye方案老款车型与浩瀚自研架构不兼容，升级存在车型代际差异",
            "极度恶劣暴雨暴雪或逆光泥污遮挡激光雷达时需驾驶员接管",
        ],
        sub_variants={
            "浩瀚智驾 2.0 (端到端Plus)": "搭载双Orin-X + 激光雷达，支持全国无图城市NZP与指尖泊车",
            "浩瀚智驾基础版": "支持高速NZP与全场景L2+辅助驾驶",
        },
        representative_vehicles=["极氪001", "极氪007", "极氪7X", "极氪MIX", "极氪009"],
        standard_labels=["浩瀚智驾", "城市NZP", "端到端智驾", "激光雷达高阶智驾", "无图城市领航", "智能泊车"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "面对注重智驾平顺度与科技感的年轻用户，突出极氪浩瀚智驾2.0端到端无图全国开、变道超车如老司机般拟人的从容感；",
            "对比华为ADS与小鹏XNGP，突出极氪全系标配激光雷达与高算力芯片的高性价比诚意，以及机械车位与狭窄车位指尖遥控泊车的实用便利。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 4. 极氪全栈全域 800V 高压架构
    TechnologyEntity(
        id="zeekr_800v_all_domain",
        name="极氪全栈全域 800V 高压系统架构",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Full-Stack All-Domain 800V High-Voltage Architecture",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="全栈全域高压碳化硅超快充平台",
        aliases=[
            "极氪800v",
            "极氪全栈800v",
            "全域800v",
            "极氪800v架构",
            "真800v平台",
        ],
        summary="从电池、电机、电控、空调压缩机到车载充电机全链路覆盖的高压碳化硅架构，最高电压达818V，整车能耗大幅优化。",
        description=(
            "极氪在新一代车型（全新001、007、7X等）上全面普及全栈800V高压系统。不仅充电速度翻倍，"
            "全链路碳化硅MOSFET功率器件使电驱转换效率突破98.5%，极大降低车辆日常通勤与冬季高速电耗，彻底告别假800V。"
        ),
        technical_principles=[
            "全链路高耐压耐冲击SiC碳化硅功率模块",
            "800V高压集成温控热泵与电池高压双极充放电路",
        ],
        advantages=[
            "匹配极充桩充电10分钟补能近400-500公里",
            "导通损耗降低50%以上，续航达成率极其扎实",
        ],
        limitations=[
            "在极老旧的低压500V公共桩上需依赖车端升压模块充能",
        ],
        sub_variants={},
        representative_vehicles=["极氪001", "极氪007", "极氪7X", "极氪009光辉"],
        standard_labels=["全栈800V", "全域高压", "SiC碳化硅", "超低电耗", "极速快充"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向客户解释‘真800V’：‘极氪连空调和电动机都是真正的800V碳化硅，夏天开冷气冬天开暖风，电量都耐用得多！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 5. 极氪 001 FR 四电机碳纤维分布式电驱动总成 (1300PS)
    TechnologyEntity(
        id="zeekr_quad_silicon_carbide",
        name="极氪四电机分布式电驱总成 (001 FR 1300PS)",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Quad-Motor Distributed Electric Powertrain (1300PS)",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="四电机独立驱动与超跑级马力输出",
        aliases=[
            "极氪四电机",
            "001 fr动力",
            "1300马力",
            "极氪fr",
            "坦克掉头",
            "四电机分布式电驱",
        ],
        summary="四个车轮各自配备独立永磁同步电机，整车最大综合马力高达1300匹，零百加速仅需2.02秒，支持沥青路面坦克掉头。",
        description=(
            "极氪完全自主研发的四电机分布式驱动系统。单轮电机峰值功率超300kW，搭配自研四轮扭矩矢量控制系统（ZVC），"
            "左右轮反向旋转可在柏油路面轻松完成坦克原地掉头，且过弯时外侧车轮主动施加正扭矩、内侧负扭矩，弯道操控极限远超千万级燃油超跑。"
        ),
        technical_principles=[
            "前双电机双轴高集成总成 + 后双电机同轴独立总成",
            "微秒级ZVC四轮独立扭矩矢量实时计算调度",
        ],
        advantages=[
            "1300匹马力狂暴输出，零百加速2.02秒，极速超280km/h",
            "支持在铺装高附着力柏油马路原地掉头，转弯半径随心控制",
        ],
        limitations=[
            "定位高性能猎装旗舰超跑，造价与轮胎消耗相对较高",
        ],
        sub_variants={},
        representative_vehicles=["极氪001 FR", "极氪009光辉(四驱高功)"],
        standard_labels=["四电机电驱", "1300马力", "零百2.02秒", "沥青路面坦克掉头", "超跑性能"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向追求极限性能的车迷讲解：‘四个电机独立控制四个车轮，1300匹马力直接碾压法拉利，柏油马路上原地就能画圆掉头，中国电车顶级机械艺术！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 6. ZVC 极氪极能矢量扭矩控制系统
    TechnologyEntity(
        id="zeekr_zvc_vectoring",
        name="极氪 ZVC 极能扭矩矢量控制系统",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Vectoring Control (ZVC) Dynamic System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="四轮毫秒级独立力矩差动操控系统",
        aliases=[
            "zvc",
            "极氪zvc",
            "极能扭矩矢量控制",
            "扭矩矢量控制",
            "弯道圣手",
        ],
        summary="掌控四轮独立电机的动力学算法大脑，每秒计算处理数千次，在弯道中通过外侧轮加速和内侧轮反拖拉扯车身，过弯快如轨道车。",
        description=(
            "传统机械差速器过弯需通过单侧刹车打齿限制打滑，损耗动力。ZVC通过电机直接以微秒级精度微调各轮扭矩输出，"
            "入弯时主动制造横摆力矩消除推头（转向不足），出弯时瞬间向外侧后轮输送大扭矩，车身姿态平稳如吸附在地面轨道上飞驰。"
        ),
        technical_principles=[
            "整车动力学六自由度质心侧偏角估算模型",
            "电机直接扭矩正反向快速分配，无需液压刹车钳干预",
        ],
        advantages=[
            "弯道极限过弯速度提升数十公里/小时，过急弯信心极大增强",
            "雨雪结冰路面单侧车轮悬空打滑时，毫秒级将动力转移至有抓地力车轮脱困",
        ],
        limitations=[
            "在搭载双电机/四电机的四驱高性能版车型上能发挥最大潜能",
        ],
        sub_variants={},
        representative_vehicles=["极氪001 FR", "极氪001四驱版", "极氪007四驱版"],
        standard_labels=["ZVC扭矩矢量", "轨道车过弯", "防推头", "四轮独立力矩", "毫秒级分配"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "带客户激烈过弯体验：‘高速拐急弯不用频繁踩刹车，ZVC在后台通过电机直接把你拉进弯心，车身没有一丝晃动，操控极其犀利！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 7. 极氪魔毯双腔空气悬架与 CCD 电磁减振系统
    TechnologyEntity(
        id="zeekr_magic_carpet_ccd",
        name="极氪智能双腔空气悬架与 CCD 电磁减振系统",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Dual-Chamber Air Suspension with CCD Damping",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="智能多挡高度与刚度可调高端底盘",
        aliases=[
            "极氪空悬",
            "极氪双腔空悬",
            "极氪魔毯",
            "ccd电磁减振",
            "五挡高度调节",
        ],
        summary="采用行业旗舰双腔空气弹簧配合CCD电磁连续可调减振器，支持车身高度最大70mm调节与刚度瞬间双挡切换。",
        description=(
            "由路特斯与吉利欧洲工程中心联合调校。双腔空簧不仅能调整车身离地间隙（迎宾模式降低、越野模式抬高），"
            "在急加减速与高速过弯时通过气阀关闭副气室，刚度瞬间暴增提升侧向支撑；CCD减振器每秒扫描路况上千次，颠簸路面滤震细腻高级。"
        ),
        technical_principles=[
            "德国威巴克大容积双腔空气弹簧与闭式高压供气系统",
            "加速度传感器与激光预瞄前馈CCD可变阻尼阀闭环控制",
        ],
        advantages=[
            "兼顾猎装轿跑低趴运动贴地姿态与SUV级野外通过性",
            "双腔刚度瞬切，彻底消除单腔空悬容易开大船晃动的毛病",
        ],
        limitations=[
            "部分车型为选装配置或高配标配",
        ],
        sub_variants={},
        representative_vehicles=["极氪001全系(高配/选装)", "极氪009", "极氪7X"],
        standard_labels=["双腔空气悬架", "CCD电磁减振", "五挡高度调节", "路特斯团队调校", "运动豪华兼具"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "现场调节车身升降给客户看：‘想要运动一键降到底盘贴地，想要露营过烂路一键升到20公分高，双腔刚度随时调软硬，底盘质感比宝马5系还扎实！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 8. 极氪智能后轮主动转向系统 (±8.4°)
    TechnologyEntity(
        id="zeekr_active_rear_steering",
        name="极氪大角度智能后轮主动转向系统 (±8.4°)",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Intelligent Active Rear-Wheel Steering Architecture (±8.4°)",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="高灵动大角度电控后轮独立转向",
        aliases=[
            "极氪后轮转向",
            "±8.4度后轮转向",
            "极氪主动后轮转向",
            "大车小拐弯",
            "转弯半径5米",
        ],
        summary="后轮最大支持双向±8.4度大角度主动转向，让超过5米长的大型豪华猎装轿车转弯半径仅5.3米，掉头比高尔夫小车还灵活。",
        description=(
            "低速行驶与倒车移库时，后轮与前轮呈反方向偏转最大8.4度，极大缩短车辆虚拟轴距，狭窄断头路掉头一把过；"
            "高速变道超车时，后轮与前轮同向微偏转，消除大车尾部甩动与迟滞，变道如横向滑行般稳健高级。"
        ),
        technical_principles=[
            "后桥高刚性电动丝杠伺服电机转向机构",
            "整车车速与横摆角速度前馈自适应偏转映射算法",
        ],
        advantages=[
            "转弯掉头极其轻快灵巧，开5米大车毫无笨重心理负担",
            "高速连续变道车身一体感极强，后排乘客完全不头晕",
        ],
        limitations=[
            "主要配备于极氪001 FR及全新001高阶版本",
        ],
        sub_variants={},
        representative_vehicles=["极氪001 FR", "全新极氪001高配版"],
        standard_labels=["后轮转向", "±8.4度转向", "5.3米转弯半径", "猎装操控", "大车灵巧"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "让客户开进狭窄路口掉头：‘五米多长的大猎装，方向盘一把打过去直接调头过来，旁边开两厢小车的司机都看呆了，灵活性满分！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 9. 极氪中段一体式压铸蜻蜓结构与一体式压铸后端铝车身
    TechnologyEntity(
        id="zeekr_mega_gigacasting",
        name="极氪一体式压铸后端铝车身与蜻蜓结构",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Gigacasting Rear Underbody with Dragonfly Structure",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="超大吨位高压一体铸造安全轻量化车体",
        aliases=[
            "极氪大压铸",
            "蜻蜓结构",
            "一体式压铸后端",
            "公路坦克大压铸",
            "7200吨压铸",
        ],
        summary="采用7200吨巨型压铸机将后车身近80个零件一体铸造成型，首创仿生蜻蜓结构中段，车身刚度与抗冲击扭转能力大幅提升。",
        description=(
            "在极氪009和极氪001上率先实现全球最大量产一体化压铸后地板。零件减少近80个，焊点减少近800个，"
            "车身后半段扭转刚度提升11%以上。结合首创的仿生‘蜻蜓’中段局部压铸加固，在严苛尾部追尾测试中承受超大货车猛烈撞击，第三排乘员舱结构完好如初。"
        ),
        technical_principles=[
            "超大吨位压铸机高速充型与自研免热处理高强韧铝合金",
            "拓扑优化仿生蜻蜓翅脉蜂窝筋条抗冲击力传导路径",
        ],
        advantages=[
            "‘公路坦克’称号名不虚传，在多起被重卡严重追尾实战中第三排零侵入变形",
            "整车轻量化减重16%，消除长期烂路行驶焊点松脱异响",
        ],
        limitations=[
            "极端恶性破坏性大撞击后需通过专业厂返厂激光校准",
        ],
        sub_variants={},
        representative_vehicles=["极氪009", "极氪001", "极氪7X", "极氪MIX"],
        standard_labels=["一体式压铸后端", "蜻蜓结构", "公路坦克", "后排防追尾", "高刚度铝合金"],
        equivalence_group_id=EquivalenceDomain.GIGACASTING_STRUCTURE,
        sales_talking_points=[
            "展示网上极氪009被重型搅拌车追尾而车身完好的真实事故照片：‘后地板是一整块7200吨压铸出来的航天铝合金，硬抗重卡追尾，家人的命永远摆在第一位！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 10. 宁德时代 140kWh 麒麟电池超长续航包 (1032km)
    TechnologyEntity(
        id="zeekr_qilin_140kwh",
        name="极氪-宁德时代 140kWh 麒麟超长续航电池包",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr-CATL 140kWh Qilin Ultra-Long Range Battery Pack",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="量产最高电量千里纯电续航电池",
        aliases=[
            "140度麒麟电池",
            "140kwh电池",
            "千里续航",
            "1032公里续航",
            "极氪麒麟电池",
            "千里续航版",
        ],
        summary="全球首发搭载宁德时代第三代CTP麒麟电池，总电量高达140kWh，CLTC综合纯电续航里程突破1032公里。",
        description=(
            "采用三元锂高镍正极材料与麒麟多功能弹性夹层水冷结构，系统能量密度高达200Wh/kg以上。"
            "彻底打破纯电车续航天花板，单次满电即可从北京一口气开到南京，或从广州直通武汉中途无需进充电站，告别任何续航焦虑。"
        ),
        technical_principles=[
            "电芯大面双向微通道液冷散热面积提升4倍",
            "高镍811三元正极与高压实高能量密度低膨胀硅碳负极体系",
        ],
        advantages=[
            "CLTC续航突破1032公里，一年日常上下班只需充两三次电",
            "大面水冷控温均匀，支持长期满充满放衰减极其缓慢",
        ],
        limitations=[
            "140度超大容量三元锂选装包造价较高，面向高端长途出行客户",
        ],
        sub_variants={},
        representative_vehicles=["极氪001 WE 140kWh千里续航版", "极氪009 WE版"],
        standard_labels=["140kWh电池", "1032km超长续航", "麒麟电池", "千里纯电续航", "高能量密度"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向跨省长途商务用户推荐：‘140度巨无霸电池，满电跑1000公里以上，跨省开长途油车都要进两次加油站，你一枪都不用充直接开到目的地！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 11. 极氪极充 V3 全液冷超快充桩体系 (800kW)
    TechnologyEntity(
        id="zeekr_v3_supercharger_800a",
        name="极氪极充 V3 800kW 全液冷超快充桩体系",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr V3 800kW Liquid-Cooled Ultra-Fast Charging Station",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="单枪800kW全球量产最高功率超充终端",
        aliases=[
            "极充v3",
            "800kw超充",
            "极氪超充桩",
            "极充站",
            "单枪800a",
        ],
        summary="全球量产最高单枪输出功率超充桩之一，最大功率达800kW，最大输出电流达800A，实现充电10分钟补能500公里。",
        description=(
            "极氪自建的高端专属超快充网络。采用全模块全液冷循环，即使在盛夏全功率输出时桩身与枪线依然保持冰凉静音；"
            "配备智能地锁与车牌即插即充无感自动支付，让极氪车主在长途路网中享受如同特权般的极速补能。"
        ),
        technical_principles=[
            "直流高压柜与超轻量化液冷循环枪线终端拓扑",
            "智能功率动态动态分配与微网储能协同削峰填谷",
        ],
        advantages=[
            "800kW巅峰功率，插上枪电量百分比几乎肉眼可见飞速上涨",
            "线缆极细极轻，单手轻松拖动，拔插优雅毫不费劲",
        ],
        limitations=[
            "需在已布局极充V3的自建品牌专属充电站网点使用",
        ],
        sub_variants={},
        representative_vehicles=["极氪全系800V车型"],
        standard_labels=["极充V3", "800kW超快充", "单枪800A", "全液冷枪线", "自建超充网络"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "给客户看极充桩充电实测：‘800千瓦单枪功率，电量百分比几秒钟就跳一个字，上个卫生间洗洗手回来电已经充到了80%，太夸张了！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 12. 极氪 STARGATE 一体式智慧灯幕 (90 英寸)
    TechnologyEntity(
        id="zeekr_smart_stargate_screen",
        name="极氪 STARGATE 90 英寸一体式智慧灯幕",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr STARGATE 90-Inch Integrated Smart Light Curtain",
        category=TechCategory.COCKPIT_OS,
        subcategory="车头巨幅曲面微米级外置高亮交互屏幕",
        aliases=[
            "stargate灯幕",
            "智慧灯幕",
            "极氪灯幕",
            "90英寸灯幕",
            "车前画画屏",
            "可手绘灯语",
        ],
        summary="全球最大90英寸一体式曲面外置智慧灯幕，内嵌1711颗高功率LED灯珠，支持中控屏自由手绘涂鸦图案实时投射在前脸上。",
        description=(
            "横贯车头的极简未来主义光幕，具备30帧/秒刷新率与高达10000nit超高亮度，强光直射依然清晰可见。"
            "车主不仅可选择‘欢庆节日’、‘爱心表白’等多种预设迎宾灯语，还能在中控屏幕上手写文字或涂鸦，车头前脸实时同步亮起你的个性手绘画作。"
        ),
        technical_principles=[
            "汽车级微曲面透光PC外壳与防飞石防紫外线老化纳米涂层",
            "独立GPU图形驱动与1711颗独立控光LED像素点阵动态映射",
        ],
        advantages=[
            "开在路上回头率100%，极具辨识度的未来赛博朋克前脸",
            "支持车外行人礼让沟通动画（如显示绿色行人走道斑马线）",
        ],
        limitations=[
            "前保险杠局部重度撞击损坏后修复换件成本高于普通塑料车头",
        ],
        sub_variants={},
        representative_vehicles=["极氪007", "极氪007 Performance"],
        standard_labels=["STARGATE灯幕", "90英寸外置大屏", "手绘灯语", "10000nit亮度", "前脸交互"],
        equivalence_group_id=None,
        sales_talking_points=[
            "拿手指在中控屏画一个笑脸：‘看！车头90英寸巨幅灯幕上立刻亮出你的手绘笑脸，开在路上所有人都在拍照，回头率绝对爆表！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 13. 极氪 MIX 对开无 B 柱双向隐藏式外摆安全车门
    TechnologyEntity(
        id="zeekr_hidden_b_pillar",
        name="极氪 MIX 全球首创对开无 B 柱双向超大外摆门",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr MIX B-Pillarless Dual-Sided Hidden Sliding Doors",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="车门隐藏式双热成型B柱与超大对开门机构",
        aliases=[
            "极氪mix开门",
            "无b柱对开门",
            "隐藏式b柱",
            "外摆滑移门",
            "宝宝巴士开门",
            "1.48米超大开口",
        ],
        summary="取消传统车身固定B柱，将潜艇级2000MPa热成型钢立柱深埋在前后滑动对开车门内部，打开后带来高达1.48米全球最大进出开口。",
        description=(
            "极氪MIX开创性地取消了传统的中间B柱阻隔。前后车门完全对向滑移电动打开，露出1.48米巨幅开阔大门口；"
            "车门内部深埋了两根2000MPa超高强度热成型钢柱（隐藏式B柱），配合上下双向卡扣锁死，在严苛侧面碰撞中抗撞强度丝毫不逊传统硬B柱车身。"
        ),
        technical_principles=[
            "门内嵌入式超高强热成型钢梁与天地双向高承载锁舌机械自锁",
            "全电动双导轨外摆滑移机构与全包覆式防夹多维毫米波防夹雷达",
        ],
        advantages=[
            "全车侧面门一开如同没有墙壁的客厅，抱宝宝上车或老人进出完全不用弯腰低头",
            "上下车开口巨大，搬运露营大装备、折叠婴儿车直接轻松迈入",
        ],
        limitations=[
            "极其复杂的双导轨电机铰链制造与防尘防水密封工艺成本高",
        ],
        sub_variants={},
        representative_vehicles=["极氪MIX"],
        standard_labels=["无B柱设计", "双向对开门", "隐藏式B柱", "1.48米大开口", "宝宝巴士空间"],
        equivalence_group_id=None,
        sales_talking_points=[
            "按下按钮打开对开门让全家体验：‘门一打开就像自家的阳台落地窗，完全没有B柱挡路，抱着孩子直接走进去，全世界只有极氪做到了这个黑科技！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 14. 极氪 270 度超大角度可旋转前后排面对面移动座椅
    TechnologyEntity(
        id="zeekr_swivel_front_seats",
        name="极氪 270 度超大角度电动旋转移动前排座椅",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr 270-Degree Power Swivel & Longitudinal Sliding Seats",
        category=TechCategory.COCKPIT_OS,
        subcategory="百变全景车内起居室与对坐茶歇机构",
        aliases=[
            "旋转座椅",
            "极氪旋转前排",
            "270度旋转",
            "前后对坐客厅",
            "移动大客厅",
        ],
        summary="前排主副驾座椅均支持电动一键向后旋转270度，与后排形成面对面对坐的大客厅，配合前后滑动中岛秒变移动茶室。",
        description=(
            "率先搭载于极氪MIX。前排座椅安全带直接固定在座椅本体上（不受旋转影响），中控岛台支持超长距离电动前后移动。"
            "停车露营时，前排两个座椅转过来面对后排，中岛升起变成折叠小方桌，全家人坐在车内打扑克、喝茶聊天、吃便当，真正把车变成了移动的温馨起居室。"
        ),
        technical_principles=[
            "全集成式高承载精密电动旋转盘齿轮电机与锁止机构",
            "座椅一体式集成预紧安全带（All-Belts-to-Seats, ABTS）碰撞力学测试认证",
        ],
        advantages=[
            "彻底颠覆汽车必须‘所有人朝前坐’的百年约束，车内社交属性拉满",
            "下雨天或炎热户外，全家人在车内面对面围坐就餐打牌，乐趣无穷",
        ],
        limitations=[
            "仅允许在车辆安全挂P挡驻车状态下开启旋转模式",
        ],
        sub_variants={},
        representative_vehicles=["极氪MIX"],
        standard_labels=["270度旋转座椅", "面对面对坐", "车内大客厅", "移动茶室", "露营社交神器"],
        equivalence_group_id=None,
        sales_talking_points=[
            "现场一键将主副驾转过来面对后排：‘看！转过来直接面对面，中间升起小桌子，一家四口在车里喝下午茶打掼蛋，外面下再大雨车里也是温馨的大客厅！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 15. 吉利全栈自研双向车载卫星消息与双向卫星通话技术
    TechnologyEntity(
        id="zeekr_satellite_comm",
        name="极氪自研车载双向卫星消息与卫星语音通信",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr In-Car Two-Way Satellite Voice & Messaging Communication",
        category=TechCategory.COCKPIT_OS,
        subcategory="天通一号与吉利未来出行高轨/低轨卫星直连",
        aliases=[
            "卫星通信",
            "车载卫星电话",
            "双向卫星消息",
            "无人区卫星求救",
            "极氪卫星通信",
        ],
        summary="无地面蜂窝移动信号时直接连入高轨/低轨卫星，支持双向收发卫星短信与卫星语音电话，无人区穿越不失联的生命之线。",
        description=(
            "依托吉利自建的‘吉利未来出行星座’与国家天通卫星系统。在无人区戈壁、罗布泊或深山老林手机完全没信号时，"
            "车机自带的高增益卫星相控阵天线自动对星对齐。不仅能向家人发送带经纬度坐标的报平安短信，还支持拨打双向卫星紧急救援通话，为生命安全兜底。"
        ),
        technical_principles=[
            "车顶一体化高增益相控阵微带卫星天线与低噪声放大器（LNA）",
            "北斗三号/天通一号双模车载基带通信协议芯片",
        ],
        advantages=[
            "自驾穿越川藏线、青藏线和无人区彻底告别失联恐慌",
            "遇到极端自然灾害地面基站全毁断网时，依然享有独一无二的天基应急通讯保障",
        ],
        limitations=[
            "在地下封闭车库或密闭长隧道内卫星电磁波受山体建筑物遮挡无法直连",
        ],
        sub_variants={},
        representative_vehicles=["极氪001 FR", "极氪007(高配/选装)", "极氪009光辉"],
        standard_labels=["车载卫星通信", "双向卫星电话", "无人区不失联", "天通卫星", "吉利星座"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向喜欢自驾川藏线越野的探险车主强调：‘走阿里中线或者大西北无人区，手机全没信号的时候，车机直接连太空卫星打电话发求救信号，关键时刻能救命！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 16. 极氪 ZEEKR OS 智能座舱系统与 Kr AI 大模型
    TechnologyEntity(
        id="zeekr_zeekr_os",
        name="极氪 ZEEKR OS 智能座舱系统与 Kr AI 大模型",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="ZEEKR OS Smart Cockpit with Kr AI Large Language Model",
        category=TechCategory.COCKPIT_OS,
        subcategory="高通8295算力驱动的高拟人车载交互系统",
        aliases=[
            "zeekr os",
            "极氪车机",
            "kr ai大模型",
            "eva语音",
            "极氪车机6.0",
        ],
        summary="基于高通骁龙8295顶级旗舰座舱芯片与Kr AI大模型，操作流畅度丝滑如飞，EVA智能语音助手支持全场景免唤醒拟人化车控。",
        description=(
            "ZEEKR OS全面重构底层渲染流水线，触控响应延迟缩减至毫秒级。结合端侧与云端Kr AI大模型能力，"
            "EVA智能伙伴不仅能实现‘打开座椅通风、把空调调大一档、导航到最近的极充站’三指令一句话并行执行，还能理解各种口语化上下文模糊指令。"
        ),
        technical_principles=[
            "高通骁龙8295车规旗舰芯片（算力高达30TOPS NPU）",
            "自研动态3D实时游戏级虚幻引擎（Unreal Engine）车辆数字孪生微动渲染",
        ],
        advantages=[
            "车机彻底摘掉早期车机卡顿帽子，丝滑度完全媲美最新款旗舰平板",
            "3D桌面车模随真实车身状态同步联动，所见即所控",
        ],
        limitations=[
            "早期820A芯片老款老车机需通过售后硬件付费升级8155/8295享受完整体验",
        ],
        sub_variants={},
        representative_vehicles=["极氪全系在售车型"],
        standard_labels=["ZEEKR OS", "高通8295芯片", "Kr AI大模型", "EVA语音助手", "丝滑车机"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "带客户上手滑动中控大屏：‘现在的极氪车机全系标配高通8295顶级芯片，屏幕跟手度就像最新款iPad一样丝滑，语音助手一秒唤醒毫无迟滞！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 17. 极氪 35.5 英寸 AR-HUD 增强现实抬头显示
    TechnologyEntity(
        id="zeekr_ar_hud_35inch",
        name="极氪 35.5 英寸 AR-HUD 增强现实抬头显示",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr 35.5-Inch Augmented Reality Head-Up Display",
        category=TechCategory.COCKPIT_OS,
        subcategory="大画幅视网膜级全天候车道级投影",
        aliases=[
            "极氪hud",
            "35.5英寸hud",
            "极氪ar-hud",
            "车道级ar导航",
            "雪地高亮hud",
        ],
        summary="投射画幅高达35.5英寸的高清全彩AR-HUD，支持雪地专属高对比度高亮模式，车道级贴地导航与智驾车距直观显示。",
        description=(
            "拥有高达12000nit超强亮度与超高色彩饱和度，具备专属设计的‘雪地模式’（在冰天雪地白茫茫反光环境下自动强化深色对比度边缘）。"
            "将车速、岔道导航虚实重叠光毯、NZP智驾红绿避让框直接精准悬浮投射在视线前方，长途驾驶眼睛无需频繁在近景仪表与远景路面间变焦调节。"
        ),
        technical_principles=[
            "高精度非球面反射镜组与防畸变图像抗拉伸几何算法",
            "智驾目标空间点云与车辆俯仰姿态动态补偿贴合算法",
        ],
        advantages=[
            "画幅开阔不晃眼，彻底解决雪天和强烈逆光下HUD发白看不清的痛点",
            "行车核心信息一览无遗，大大提高高速行车的主动安全性",
        ],
        limitations=[
            "前挡风玻璃投影区域若有较多鸟粪灰尘遮挡需先喷玻璃水清洁",
        ],
        sub_variants={},
        representative_vehicles=["极氪001", "极氪007", "极氪7X", "极氪009"],
        standard_labels=["35.5英寸AR-HUD", "雪地模式", "12000nit高亮", "车道级贴地指引", "防眩晕投影"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "带客户上车看HUD显示：‘35.5英寸超大画幅，大太阳底下看得一清二楚，冬天去东北滑雪还有专门的雪地抗反光模式，不用低头超安全！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 18. 极氪第二代金砖电池 (5.5C 超快充放电倍率)
    TechnologyEntity(
        id="zeekr_golden_battery_v2",
        name="极氪第二代金砖电池 (5.5C 极速充电倍率)",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Golden Battery 2.0 (5.5C Ultra-Fast Charging LFP)",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="新一代超快充高安全磷酸铁锂电池",
        aliases=[
            "第二代金砖电池",
            "金砖2.0",
            "金砖二代",
            "5.5c金砖",
            "10.5分钟快充",
        ],
        summary="全球充电速度最快的磷酸铁锂电池，充电倍率跃升至5.5C，电量从10%充至80%仅需10.5分钟，彻底追平甚至超越三元锂快充水平。",
        description=(
            "在第一代金砖电池基础上深度升级纳米级固液界面与超快离子导电通道。采用全新超导低阻电解液与多孔厚电极拓扑，"
            "在保证磷酸铁锂极致耐高温与高本征安全性的前提下，实现10.5分钟狂充80%电量，真正把磷酸铁锂推上了全球超快充神坛。"
        ),
        technical_principles=[
            "超快离子晶界迁移促进剂与低阻抗纳米碳包覆磷酸铁锂正极材料",
            "三维立体环绕散热水道与多极耳极速放热均温技术",
        ],
        advantages=[
            "充电速度打破磷酸铁锂‘慢充’的传统魔咒，10.5分钟补足数百公里续航",
            "循环充放电寿命超4000次，开几十万公里电池衰减微乎其微",
        ],
        limitations=[
            "需在全栈800V且支持高电流的超快充桩端才能发挥5.5C极致倍率",
        ],
        sub_variants={},
        representative_vehicles=["极氪007 2025款", "极氪7X 75kWh版本"],
        standard_labels=["第二代金砖电池", "5.5C超充", "10.5分钟快充", "磷酸铁锂巅峰", "超长循环寿命"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向纠结电池类型的客户科普：‘谁说铁锂电池充电慢？第二代金砖电池10分半钟充到80%，比很多昂贵的三元锂充得还快，而且更耐造不自燃！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 19. 极氪 YAMAHA 高级环绕立体声音响系统 (28 扬声器杜比全景声)
    TechnologyEntity(
        id="zeekr_yamaha_audio",
        name="极氪 YAMAHA 殿堂级全景环绕立体声音响 (28扬声器)",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr YAMAHA Master Surround Sound 28-Speaker System",
        category=TechCategory.COCKPIT_OS,
        subcategory="日本雅马哈大师调校7.1.4空间音频",
        aliases=[
            "雅马哈音响",
            "yamaha音响",
            "极氪雅马哈",
            "28个扬声器",
            "极氪头枕音响",
            "7.1.4杜比全景声",
        ],
        summary="由日本YAMAHA调音大师专属声学校准，最高配备28个发声单元、2400W额定功放及主副驾双头枕扬声器，重现专业音乐厅听感。",
        description=(
            "极氪与日本殿堂级乐器与音响巨头雅马哈深度合作。车内包含天花板全景声天空扬声器、大口径超低音单元及四个座椅头枕独立音响；"
            "搭载YAMAHA独家数字信号处理算法与杜比全景声解码，不仅音乐三频层次分明，更能实现主驾导航指引声音独立耳语、乘客音乐纯净享受。"
        ),
        technical_principles=[
            "YAMAHA专属声学均衡DSP芯片与车内多反射面几何声学调谐",
            "座椅头枕双近场微型发声单元与主驾声学隐私降噪算法",
        ],
        advantages=[
            "乐器泛音与人声现场感极强，宛如置身东京三得利音乐厅正中央",
            "主驾驶听导航电话完全不打扰后排家人听音乐或睡觉休息",
        ],
        limitations=[
            "追求极致音质需配合车机内置的无损母带格式高码率音乐源播放",
        ],
        sub_variants={},
        representative_vehicles=["极氪001", "极氪007", "极氪7X", "极氪009"],
        standard_labels=["YAMAHA音响", "雅马哈大师调校", "28扬声器", "7.1.4全景声", "头枕独立扬声器"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "上车播放一段雅马哈钢琴独奏：‘听这钢琴琴弦敲击的声音和余音，日本百年雅马哈大师亲自调校，头枕还能单独听导航，高级感直接拉满！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 20. 极氪 PTM 全域热管理系统与冷媒直热热泵
    TechnologyEntity(
        id="zeekr_ptm_heat_pump",
        name="极氪 PTM 全域智能热管理系统与直接式热泵",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr PTM All-Domain Thermal Management & Direct Heat Pump",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="宽温域电驱电池座舱协同冷热循环",
        aliases=[
            "ptm热管理",
            "极氪热泵",
            "直接式热泵",
            "宽温域热管理",
            "冬季续航优化",
        ],
        summary="深度融合电驱余热回收与冷媒直热循环的综合热管理系统，支持-30℃至40℃宽温域运行，冬季采暖能耗大幅降低。",
        description=(
            "PTM（Powertrain Thermal Management）打通了电池液冷回路、电驱油冷回路与座舱空调三大域。"
            "在严寒北方冬季，直接吸收电机高速运转微弱废热注入电池与驾驶室，使整车冬季续航达成率提升15%以上，并极大缩短极寒冬季快充预热时间。"
        ),
        technical_principles=[
            "高压电子膨胀阀与自研集成式多通智能换热换向矩阵阀件",
            "双向闪发补气增焓微型变频涡旋压缩机系统",
        ],
        advantages=[
            "极寒环境制热COP高达2.0以上，冬季开暖风不再心疼电量掉电快",
            "大功率激烈驾驶时强力压制电芯温升，杜绝热过载限速",
        ],
        limitations=[
            "复杂多通阀体保养需使用极氪原装长寿命特种冷冻油液",
        ],
        sub_variants={},
        representative_vehicles=["极氪全系在售车型"],
        standard_labels=["PTM热管理", "宽温域热泵", "电机余热回收", "冬季续航坚挺", "冷热高效调度"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向北方车主说明耐寒能力：‘极氪标配PTM全域热管理，零下20度利用电机余热给车厢吹暖风，冬天跑高速掉电慢、充电快，彻底放心！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 21. 极氪 2000MPa 一体成型超高强车门防撞横梁
    TechnologyEntity(
        id="zeekr_cross_door_beam",
        name="极氪 2000MPa 一体热成型钢车门防撞梁架构",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr 2000MPa Hot-Formed Ultra-High Strength Door Anti-Collision Beams",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="侧面碰撞抵御与侧柱碰装甲级安全",
        aliases=[
            "车门防撞梁",
            "2000mpa防撞梁",
            "极氪侧碰安全",
            "公路坦克车身",
            "双防撞梁",
        ],
        summary="四个车门内部深嵌2000MPa潜艇级热成型钢超强防撞梁，侧面柱碰抗击力达到中保研标准的数倍，严防侧碰侵入挤压乘员。",
        description=(
            "侧面碰撞是日常交通中最致命的事故类型之一（侧面缓冲溃缩区极短）。极氪在全车车门内布置了高抗弯曲刚度的2000MPa热成型钢管梁，"
            "配合门槛内部的高刚度铝合金多宫格吸能梁，将侧撞冲击力快速向车顶A/B/C柱与车底坚固骨架均匀分散，构筑刀枪不入的‘金钟罩’。"
        ),
        technical_principles=[
            "航天级高强韧热成型硼钢变截面滚压热煨弯成型",
            "门槛挤压铝合金蜂窝十宫格能量吸收溃缩区协同传力",
        ],
        advantages=[
            "被誉为‘最硬侧碰保护’，在多次真实恶性十字路口侧面被大车猛烈撞击中座舱零侵入",
            "车身整体扭转刚度突破40000 N·m/deg，颠簸烂路绝不咯吱异响",
        ],
        limitations=[
            "超高强特种硼钢材料冲压模具成本极高",
        ],
        sub_variants={},
        representative_vehicles=["极氪001", "极氪007", "极氪7X", "极氪009"],
        standard_labels=["2000MPa防撞梁", "公路坦克", "侧碰零侵入", "十宫格门槛", "被动安全第一"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "让客户用力敲击车门下半部：‘车门里面藏着2000兆帕潜艇钢梁，网上无数车友事故实测，侧面被大货车撞击A柱B柱依然笔直，车门照样拉开逃生！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 22. 极氪电芯双大面直接冷却液冷板设计
    TechnologyEntity(
        id="zeekr_direct_cooling_pack",
        name="极氪电芯双大面直接液体冷却与均温系统",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Dual-Sided Direct Liquid Cooling & Thermal Equalization",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高热传导微通道电芯立体散热技术",
        aliases=[
            "双大面冷却",
            "极氪电芯散热",
            "立体液冷板",
            "微通道冷板",
        ],
        summary="改变传统电池包单底面冷板散热布局，冷却液板直接垂直夹在每颗电芯的两个超大侧面，换热效率提升300%。",
        description=(
            "电芯在大电流快充时主要通过侧面大面积向外发热。极氪双大面冷却技术将蛇形微通道铝制水冷板紧密贴合在每个电芯侧面，"
            "充放电过程中电芯内部最大温差不超过2℃，即使在4.5C-5.5C持续超级暴冲下依然将电池稳稳控制在黄金适宜温度，从根本上杜绝热积聚失控。"
        ),
        technical_principles=[
            "微细挤压薄壁多孔铝冷板结构设计",
            "高导热绝缘导热胶垫双向弹性紧密贴合包覆",
        ],
        advantages=[
            "极限快充不限流不跳闸，快充高功率平台维持时间同级最长",
            "电芯各区域受热极其均匀，大幅延长整车电池全生命周期健康度",
        ],
        limitations=[
            "水冷板与电芯集成度高，制造检测工艺气密性严苛",
        ],
        sub_variants={},
        representative_vehicles=["极氪001", "极氪007", "极氪7X"],
        standard_labels=["双大面冷却", "立体散热", "超充不发烫", "电池长寿命", "微通道冷板"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向注重电池寿命的用户讲解：‘每两颗电池中间都夹着一层直接水冷板，超快充时电池一点都不发烫，充电又快又保护电池不早衰！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 23. 极氪前双球节全铝双叉臂独立悬架
    TechnologyEntity(
        id="zeekr_dual_wishbone_virtual",
        name="极氪前全铝虚拟主销双球节双叉臂悬架",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr All-Aluminum Virtual-Kingpin Dual-Ball-Joint Front Suspension",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="超跑级高极限精准转向运动前悬",
        aliases=[
            "双球节双叉臂",
            "极氪前悬架",
            "全铝双叉臂",
            "虚拟主销",
            "宝马同款悬架",
        ],
        summary="前悬架采用上下全铝摆臂且下控制臂拆解为两根带独立球节的连杆，虚拟主销外移，高速过弯转向极其精准犀利且无方向盘拉扯感。",
        description=(
            "传承保时捷与宝马性能车的经典顶级前桥底盘架构。上下摆臂、转向节与前副车架均采用昂贵的高强度锻造铝合金，"
            "大幅减小簧下质量。下摆臂双球节设计使车轮转向主销随转向角度动态外移，极大提升车轮在极限过弯时的轮胎接地面积，贴地抓地力惊人。"
        ),
        technical_principles=[
            "虚拟转向主销几何学运动拓扑与抗前倾抗俯仰角设计",
            "锻造航空级铝合金控制臂轻量化与低惯性阻尼衬套匹配",
        ],
        advantages=[
            "转向手感极其指哪打哪无虚位，过弯时前轮抓地力坚韧无比",
            "簧下重量大幅减轻，碾过细碎颠簸路面减振器回弹极其利索不拖泥带水",
        ],
        limitations=[
            "全铝锻造件与多个高精度球销铰链制造成本远超普通麦弗逊悬架",
        ],
        sub_variants={},
        representative_vehicles=["极氪001", "极氪007", "极氪009", "极氪7X"],
        standard_labels=["全铝双叉臂", "双球节虚拟主销", "精准操控", "超跑级底盘", "轻量化簧下"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向追求操控和驾驶质感的买家强调：‘看看这前轮里面又粗又亮的锻造全铝双叉臂，这可是保时捷帕拉梅拉同款的顶级前悬架，开起来指哪打哪毫无虚位！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 24. 极氪赛道漂移模式与可调前后动力分配
    TechnologyEntity(
        id="zeekr_drift_mode",
        name="极氪智能赛道漂移模式与前后轮驱动偏置",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Intelligent Track Drift Mode & Dynamic Torque Biasing",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="纯后驱自由切换与极限横滑漂移辅助",
        aliases=[
            "极氪漂移模式",
            "漂移模式",
            "纯后驱切换",
            "赛道驾驶模式",
            "后驱漂移",
        ],
        summary="在中控屏一键开启赛道漂移模式，前电机断开动力输出彻底化身纯后驱大马力性能车，关闭车身稳定控制尽情享受定圆漂移乐趣。",
        description=(
            "专为爱好赛道和漂移运动的车主研发。在普通模式下是安全稳重的全时电四驱，"
            "在赛道模式下可设定前后轴扭矩输出比例为0:100，ESC车身稳定系统完全退出干预，配合大功率后置驱动电机的大扭矩瞬间爆发，轻松在封闭赛道上完成华丽的拉烟横移漂移。"
        ),
        technical_principles=[
            "前后轴逆变器动力完全物理/电控解耦与电机弱磁输出控制",
            "方向盘反打角速度与横摆角速度实时监控辅助安全锁止边界",
        ],
        advantages=[
            "一辆车同时拥有四驱的雨雪安全与后驱超跑的极致漂移乐趣",
            "赛道可玩性极高，深受性能车爱好者与年轻改装车主狂热追捧",
        ],
        limitations=[
            "必须在安全封闭赛道或专业驾控场地由具备专业漂移技巧的驾驶员操作",
        ],
        sub_variants={},
        representative_vehicles=["极氪001 FR", "极氪001四驱版", "极氪007四驱性能版"],
        standard_labels=["漂移模式", "纯后驱切换", "赛道可玩性", "拉烟漂移", "大马力操控"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向喜欢漂移和玩车的年轻买家演示：‘在屏幕上点一下漂移模式，前轮断电变成纯后驱，去赛道里一脚电门直接甩尾起漂，性能乐趣完全不输百万M Power！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 25. 极氪无门把手隐藏式压感车门与自动避障电动开门
    TechnologyEntity(
        id="zeekr_touch_door",
        name="极氪感应压感无门把手与智能全自动避障电动门",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Flush Touch-Sensitive & Auto-Obstacle-Avoidance Power Doors",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="纯平车身感应进出与毫米波雷达主动防撞电动门",
        aliases=[
            "极氪电动门",
            "无门把手车门",
            "压感车门",
            "自动避障开门",
            "感应开门",
        ],
        summary="取消传统外凸门把手实现纯平车身侧颜，B柱触控感应开门，车门内置毫米波雷达全天候智能避障，绝不磕碰旁边车辆或马路牙子。",
        description=(
            "极氪首创将车门把手完全抹平，车侧如镜面般平滑降低风阻。车主走近轻触B/C柱压感开关或踩刹车，车门自动电动平缓弹开；"
            "每个车门内部深埋多颗高灵敏度超声波与毫米波防撞雷达，自动侦测侧方柱子、低矮花坛与路过电动车，遇到障碍精准悬停防撞，优雅尊崇。"
        ),
        technical_principles=[
            "门内隐藏式多通道毫米波近距离雷达与电容式触控按键",
            "车门无级位置自适应闭环伺服电机与无刷扭矩防夹反馈",
        ],
        advantages=[
            "踩下刹车踏板主驾车门自动电动吸合关闭，上下车仪式感媲美劳斯莱斯",
            "纯平车身完全消除传统门把手冬天被冻住弹不出来的北方痛点",
        ],
        limitations=[
            "在极狭窄车位两侧有极近障碍物时，车门出于安全避障会限制开门角度",
        ],
        sub_variants={},
        representative_vehicles=["极氪001", "极氪007", "极氪009", "极氪X"],
        standard_labels=["智能电动门", "无门把手", "毫米波避障", "踩刹车关门", "劳斯莱斯级仪式感"],
        equivalence_group_id=None,
        sales_talking_points=[
            "坐进主驾驶踩一脚刹车展示：‘上车坐好只要轻轻踩一脚刹车，车门自己悄无声息关上吸合，就像劳斯莱斯一样尊贵！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 26. 极氪 ADB 自适应防眩目矩阵大灯与迎宾投影
    TechnologyEntity(
        id="zeekr_matrix_headlight",
        name="极氪自适应智能防眩目 ADB 矩阵 LED 大灯",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Adaptive Driving Beam (ADB) Matrix LED Headlights",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="高精微米级独立像素矩阵控光与智能照明",
        aliases=[
            "极氪矩阵大灯",
            "adb大灯",
            "防眩目大灯",
            "自动远光避让",
            "极氪车灯",
        ],
        summary="配备多分区独立可控的高亮度LED矩阵大灯，照明射程突破450米，夜间长开远光自动精准抠出对向来车位置避免晃眼。",
        description=(
            "大灯深度联动前视感知摄像头。在没有路灯的漆黑高速公路上，远光灯全程开启以获得极致开阔的视野，"
            "当系统识别到前向有同向行车或对向来车时，以毫秒级速度关闭对应车辆区域的单个像素光源，其余路面依然保持如同白昼般明亮照耀。"
        ),
        technical_principles=[
            "多通道LED独立可编程恒流驱动与光学聚光透镜",
            "ADAS智能视觉摄像头对向目标像素级动态轮廓跟踪算法",
        ],
        advantages=[
            "450米超远夜间照射射程，极大提前看清散落物和故障车",
            "夜间走国道高速全程无需手忙脚乱频繁来回切换远近光",
        ],
        limitations=[
            "雨刮器刮扫不净导致前风挡摄像头区域被大块污泥糊住时需先刮洗干净",
        ],
        sub_variants={},
        representative_vehicles=["极氪001", "极氪007", "极氪7X", "极氪009"],
        standard_labels=["ADB矩阵大灯", "450米超远射程", "自动防眩目", "夜间安全保障", "智能分区控光"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向常跑夜路的客户讲解：‘跑夜路大灯一直开着远光，前方400多米照得通亮，对面来车大灯自动扣出黑框不晃对面眼睛，既安全又有礼貌！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 27. 极氪高精度超长距激光雷达智驾感知矩阵
    TechnologyEntity(
        id="zeekr_lidar_super_sensing",
        name="极氪超长距高精度顶置激光雷达感知系统",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Ultra-Long Range Precision Roof-Mounted LiDAR Sensing Matrix",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="全天候冗余多模态三维环境激光点云感知",
        aliases=[
            "极氪激光雷达",
            "顶置激光雷达",
            "超长距雷达",
            "浩瀚激光感知",
            "200米雷达",
        ],
        summary="采用新一代车规级超长距激光雷达，探测距离达200米以上，配合11颗高清摄像头，构建风雨无阻的全天候物理三维视界。",
        description=(
            "在极氪新一代全系车型上全面普及标配。不受大逆光、黑夜强光、无照明隧道等恶劣视觉光影干扰，"
            "每秒发射上百万个激光脉冲，精准测量200米外前方车辆、反光锥桶、小动物及倒地树枝的三维坐标，为端到端高阶智驾提供绝对可靠的安全兜底。"
        ),
        technical_principles=[
            "混合固态高频扫描架构与车规级SPAD光电阵列探测器",
            "硬件级时钟同步与摄像头图像2D/3D时空坐标系毫秒级标定",
        ],
        advantages=[
            "全系主流车型标配激光雷达，不需要买最贵顶配才能享有顶级安全硬件",
            "黑夜与进出隧道瞬间视觉致盲工况下，激光雷达依然明察秋毫稳稳刹停",
        ],
        limitations=[
            "顶置瞭望塔式布局日常洗车时建议避免高压水枪贴近近距离猛烈冲洗镜头",
        ],
        sub_variants={},
        representative_vehicles=["极氪001 2025款", "极氪007", "极氪7X", "极氪MIX", "极氪009"],
        standard_labels=["激光雷达", "全系标配雷达", "200米探测", "全天候安全", "物理点云感知"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "突出极氪加量不加价的厚道配置：‘很多车企要加两三万选装激光雷达，极氪全系直接标配，黑夜里200米外掉的小石头都能看清，安全绝不缩水！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 28. 极氪双 NVIDIA DRIVE Orin-X 高算力智驾计算平台
    TechnologyEntity(
        id="zeekr_dual_orin_noa",
        name="极氪自研双英伟达 DRIVE Orin-X 算力平台 (508TOPS)",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Dual NVIDIA DRIVE Orin-X 508TOPS High-Computing Platform",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="高吞吐量车规级智驾域控制器与双芯片冗余",
        aliases=[
            "双orin-x",
            "508tops算力",
            "极氪orin",
            "浩瀚算力平台",
            "英伟达orin芯片",
        ],
        summary="配备两颗英伟达DRIVE Orin-X芯片，综合算力高达508TOPS，专为端到端多模态大模型高速吞吐实时计算设计。",
        description=(
            "算力是运行端到端AI大模型的决定性基石。双Orin-X平台提供业界一流的浮点算力储备，"
            "两颗芯片互为热备份安全冗余，能以每秒上百帧的速度并发处理全车激光雷达、毫米波雷达与十余颗超高清摄像头的海量数据流，赋能城市NZP从容无图领航。"
        ),
        technical_principles=[
            "双Orin-X芯片PCIe高速总线直连与锁步安全冗余校验",
            "极氪自研深度定制化轻量级嵌入式实时操作系统RTOS",
        ],
        advantages=[
            "算力充沛无瓶颈，未来数年内持续OTA进化端到端大模型毫无压力",
            "双芯片冗余设计，即使单颗芯片遭遇极端硬件故障车辆仍能安全平稳靠边泊停",
        ],
        limitations=[
            "高算力芯片在盛夏极高负荷运行时需依靠水冷循环高效散热",
        ],
        sub_variants={},
        representative_vehicles=["极氪001", "极氪007", "极氪7X", "极氪MIX", "极氪009"],
        standard_labels=["双Orin-X", "508TOPS算力", "英伟达芯片", "芯片安全冗余", "端到端算力基石"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向懂芯片的年轻买家阐述算力储备：‘508 TOPS的双Orin-X算力天花板，大模型随便跑，未来五年内不断OTA升级都不会落伍卡顿！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 29. 极氪 SEA-M 浩瀚-M 专属智能无人驾驶与出行架构
    TechnologyEntity(
        id="zeekr_sea_m",
        name="极氪 SEA-M 浩瀚-M 智能出行与无人驾驶专属架构",
        brand="吉利 / 极氪 (Zeekr / Geely)",
        brand_key="zeekr",
        english_name="Zeekr SEA-M Autonomous Mobility Architecture",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="无B柱胶囊座舱与全无人驾驶Robotaxi出行平台",
        aliases=[
            "sea-m",
            "浩瀚-m",
            "sea-m架构",
            "极氪无人驾驶架构",
            "robotaxi平台",
            "胶囊座舱架构",
        ],
        summary="专为未来移动出行和高阶无人驾驶打造的原生架构，实现无B柱对开门、超大轴长比以及与Waymo联合开发无人驾驶出行车辆。",
        description=(
            "SEA-M架构打破了传统车辆发动机舱和前悬的束缚，以胶囊车厢为灵感，在紧凑的外廓尺寸内榨取超过64%的极致轴长比与内部空间。"
            "具备全冗余线控底盘（转向、制动、电源全双重备份），是全球首个支持L4级无人驾驶商业化量产运营的前瞻架构。"
        ),
        technical_principles=[
            "线控转向、线控制动、低压供电与通信全链路ASIL-D双重物理硬件冗余",
            "平整化高集成下底盘与超大角度前轮大转向角几何设计",
        ],
        advantages=[
            "空间得房率行业第一，极小转弯半径让大型胶囊空间车辆在市区极度灵活",
            "为无人驾驶出行车辆提供全球顶级标准的安全硬件冗余",
        ],
        limitations=[
            "前瞻性极强，面向未来智慧出行生态与极氪MIX等先锋物种品类",
        ],
        sub_variants={},
        representative_vehicles=["极氪MIX", "Waymo RT6定制无人驾驶车"],
        standard_labels=["SEA-M架构", "无人驾驶平台", "双重硬件冗余", "极致空间得房率", "未来胶囊出行"],
        equivalence_group_id=None,
        sales_talking_points=[
            "突出极氪与全球自动驾驶巨头Waymo的联合研发背景：‘连谷歌Waymo都选极氪SEA-M架构在美国跑无人出租车，底盘安全冗余全球顶级！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 30. 极氪碳纤维超高转速电机转子包覆技术 (21000rpm)
    TechnologyEntity(
        id="zeekr_carbon_rotor_motor",
        name="极氪碳纤维转子包裹超高转速永磁电机 (21000rpm)",
        brand="极氪 (Zeekr)",
        brand_key="zeekr",
        english_name="Zeekr Carbon-Sleeve High-RPM PMSM Traction Motor (21000rpm)",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="碳纤维预应力套筒超大功率密度驱动电机",
        aliases=[
            "极氪碳纤维转子",
            "21000转电机",
            "碳纤维电机",
            "高转速永磁电机",
            "001fr电机",
        ],
        summary="采用航天级碳纤维丝以极高预紧力将转子紧密包裹，电机转速突破21000rpm，功率密度达每公斤4.4kW，极速持续输出不衰退。",
        description=(
            "为了实现极氪001 FR与高性能车型的狂暴马力与极速，极氪攻克了碳纤维转子复合包裹工艺。"
            "有效抵消电机两万转以上超高转速产生的离心撕裂力，转子气隙微米级压缩，效率更高，整车极速突破280km/h依然保持平直饱满的功率输出。"
        ),
        technical_principles=[
            "微张力高精度碳纤维数控缠绕与环氧树脂真空浸渍固化",
            "空心轴内置微通道高速油冷与定子直接喷油降温",
        ],
        advantages=[
            "转速突破21000rpm，高速后段加速推背感持续不软脚",
            "体积缩小30%以上，大幅减轻整车电驱动系统重量",
        ],
        limitations=[
            "高精度碳纤维套筒缠绕加工制造精度工艺复杂昂贵",
        ],
        sub_variants={},
        representative_vehicles=["极氪001 FR", "极氪001四驱高性能版"],
        standard_labels=["碳纤维转子", "21000rpm电机", "高功率密度", "极速不衰退", "赛道级电驱"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向懂车的朋友科普电机工艺：‘碳纤维像紧箍咒一样套在电机转子上，两万一千转都不解体，高速开到两百多依然推背感强烈！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),
]

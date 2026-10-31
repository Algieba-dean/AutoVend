"""
Generic Powertrain & Electrical Technical Terminology (src/terminology/generic/powertrain.py).
Contains 17 comprehensive generic powertrain and charging technologies (category="补能与电气").
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

GENERIC_POWERTRAIN_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 增程式电动系统 (Original)
    TechnologyEntity(
        id="generic_erev_powertrain",
        name="增程式电动系统 (EREV)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Extended Range Electric Vehicle (EREV)",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="混动电驱/增程动力架构",
        aliases=[
            "增程",
            "增程式",
            "增程式电动",
            "erev",
            "增程混动",
            "增程器",
            "增程式插电",
            "增程车",
        ],
        summary="全时全域纯电驱驱动，由内燃机作为‘增程发电机’专职发电补能而不直接驱动车轮的动力架构，既享受纯电车的静谧平顺，又具备‘有油就有电’的零长途焦虑。",
        description=(
            "增程式电动（EREV - Extended Range Electric Vehicle）的传动核心理念是‘串联解耦’。车辆底盘只有驱动电机与车轮硬连接，"
            "发动机（增程器）与车轮没有任何离合器或变速箱物理机械连接。增程器始终保持在最高热效率转速区间平稳运转带动发电机发电，"
            "发出来的电量一部分供电机直接驱动车辆，多余电量存储进动力电池。市区充电当纯电车开，长途出门加油即可续航破千公里，无排队充电压迫感。"
        ),
        technical_principles=[
            "发动机与发电机同轴直连，发电机解耦全串联能量管理",
            "内燃机转速彻底与车速解耦，始终锁定在最佳BSFC高效燃油消耗率岛",
        ],
        advantages=[
            "驾驶体感100%纯电：动力随踩随有、平顺线性、绝无传统燃油车换挡顿挫",
            "彻底消除补能与里程焦虑：国庆长途出行无需在服务区排队数小时抢充电桩，加油站5分钟加满油即可再跑1000公里",
            "结构精简少故障：相比多挡混动取消了复杂的湿式多片离合器和变速箱挡位机构，机械可靠性极高",
        ],
        limitations=[
            "高速公路120km/h以上极速超车持续巡航时，能量经历‘油转电再转机械能’二次损耗，高速油耗略高于发动机直驱混动",
            "在极端严重馈电情况下，若增程器发电功率小于高速爬坡电机消耗，可能会面临短时动力轻微受限",
        ],
        sub_variants={
            "单增程后驱": "单电机后驱+增程器，经济省油（如理想L6、零跑C11）",
            "双电机四驱增程": "前后双电机四驱+增程器，兼顾强劲加速与越野脱困（如问界M9增程版、理想L9）",
        },
        representative_vehicles=["理想L6/L7/L8/L9", "问界M5/M7/M9增程版", "深蓝S07/L07", "阿维塔07增程版", "仰望U8"],
        standard_labels=["增程", "EREV", "全电驱动", "无里程焦虑", "大电池长续航", "高效增程器"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "向只有一辆车、既想要纯电舒适又经常长途自驾过年回家的家庭客户首推：平日上下班纯电成本每公里几分钱，长途开空调狂奔无焦虑；",
            "对比插混车型说明：增程没有变速箱顿挫异响，开起来就是一辆安静丝滑的高级纯电车，老人小孩乘坐不头晕不恶心。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 2. 插电式混合动力系统 (Original)
    TechnologyEntity(
        id="generic_phev_powertrain",
        name="插电式混合动力系统 (PHEV)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Plug-in Hybrid Electric Vehicle (PHEV)",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="混动电驱/多挡串并联电混",
        aliases=[
            "插混",
            "插电混动",
            "phev",
            "并联混动",
            "串并联混动",
            "dht混动",
            "双电机混动",
            "插电式",
        ],
        summary="配备外接充电口并支持纯电行驶的串并联混合动力系统，发动机与电动机既可分别独立驱动，又可在高速通过离合直驱车轮，高速节油与爆发力俱佳。",
        description=(
            "插电式混合动力（PHEV）拥有多种工作模式：纯电模式（纯电机驱动）、串联模式（发动机发电电机驱动）、并联模式（发动机与电机同时出力巅峰输出）"
            "以及直驱模式（中高速巡航发动机通过直驱离合器直接驱动车轮）。多挡DHT（如两挡/三挡）能够在中低速提前切入发动机并联直驱，"
            "消除高速大负荷馈电下的能耗偏高问题，适应全速域全工况超强动力与超低综合油耗。"
        ),
        technical_principles=[
            "混动专用高压缩比阿特金森/米勒循环发动机与多挡DHT双电机变速器集成",
            "智能离合器与行星齿轮组实现全自动毫秒级模式无缝切换",
        ],
        advantages=[
            "高速巡航燃油经济性极强：发动机可在高效转速直驱车轮，无二次能量转换损耗",
            "并联全力加速动力极其凶悍：发动机与前后双电机同时满功率爆发，中后段加速储备充沛",
            "纯电通勤成本低，馈电长途综合续航突破1200km至1500km",
        ],
        limitations=[
            "包含发动机、离合器、多挡变速齿轮箱及电驱动，机械构件复杂度高于增程和纯电，保养成本略高",
            "低电量极端工况下如果发动机频繁介入，NVH震动抑制调校若不佳可能会有轻微介入感",
        ],
        sub_variants={
            "单挡DHT串并联": "结构极简，以电为主（如比亚迪DM-i）",
            "多挡DHT (2挡/3挡)": "支持全速域并联，注重高速性能与极速脱困（如长城Hi4、奇瑞鲲鹏C-DM、吉利雷神电混）",
        },
        representative_vehicles=["比亚迪秦L/汉DM-i", "长城坦克300 Hi4-T", "奇瑞风云T9", "领克08 EM-P", "吉利银河L7"],
        standard_labels=["插电混动", "PHEV", "串并联", "DHT变速箱", "发动机直驱", "超低馈电油耗"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "向经常跑跨省高速、对高速油耗和超车爆发力要求高的客户推荐插混：中高速直驱更省油，满载超车底气十足；",
            "对比传统燃油车强调：市区当电车开不烧一滴油，绿牌免购置税，综合续航轻松突破1400公里。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 3. 单/双/三/四电机独立驱动总成 (Original)
    TechnologyEntity(
        id="generic_multi_motor_drive",
        name="单/双/三/四电机独立驱动总成",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Single / Dual / Tri / Quad Motor Electric Drive",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="电驱系统/多电机分布式动力",
        aliases=[
            "双电机",
            "单电机",
            "四电机",
            "三电机",
            "双电机四驱",
            "四电机独立驱动",
            "单电机后驱",
            "多电机驱动",
            "双电机驱动",
            "分布式电驱",
        ],
        summary="由1至4台电机组成的纯电驱动体系：单电机经济后驱/前驱；双电机全时电四驱（百公里3-4秒）；三/四电机四轮独立分布式矢量控制，实现超跑加速与原地掉头。",
        description=(
            "电动机相较内燃机具有体积小、响应快（毫秒级扭矩输出）以及正反转自如的天然优势。"
            "单电机适合城市轻快代步；双电机省去沉重的机械传动轴和分动箱，前后轴毫秒级动态调配扭矩；"
            "三电机与四电机架构则为每个车轮赋予独立自由驱动力，两边车轮反向旋转可实现坦克级原地掉头，单侧车轮悬空或雨雪打滑时可百分百将扭矩转移至抓地轮，极限防滑脱困。"
        ),
        technical_principles=[
            "独立永磁同步/交流异步电机与减速箱集成电驱动总成",
            "中央底盘域控制器毫秒级四轮扭矩矢量分配与横摆力矩直接控制（DYC）",
        ],
        advantages=[
            "双电机四驱雨雪湿滑路面起步不打滑，过弯循迹稳定性远胜传统机械四驱",
            "四电机独立驱动可实现原地掉头、水面浮水行驶、极端120km/h单轮爆胎平稳不侧翻的极限安全",
            "零百加速从容跨入2秒俱乐部，动力爆发平顺无顿挫",
        ],
        limitations=[
            "双电机及以上配置增加整备质量和电耗，日常城市能耗略高于单电机",
            "四电机系统造价昂贵，主要装配于百万级旗舰超跑或高端硬派越野",
        ],
        sub_variants={
            "单电机 (前驱/后驱)": "主流高能效长续航代步之选",
            "双电机 (前感应+后永磁 / 双永磁)": "中高端性能四驱标配（3秒级破百）",
            "三电机 / 四电机独立驱动": "顶级超跑与硬派越野（如极氪001 FR、仰望U8/U9、特斯拉Plaid）",
        },
        representative_vehicles=["小米SU7 Max(双电机)", "极氪001(双电机/四电机FR)", "仰望U8/U9(四电机易四方)", "特斯拉Model S Plaid(三电机)"],
        standard_labels=["单电机", "双电机四驱", "四电机独立驱动", "扭矩矢量控制", "原地掉头", "超跑级零百加速"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "对安全和操控在意的客户强推双电机四驱：‘雨雪湿滑天气四驱抓地力稳如泰山，超车变道只需轻点电门瞬时完成’；",
            "追求极限推背感和黑科技的客户推荐三/四电机：不仅有秒杀千万超跑的加速体验，更有原地掉头和爆胎防失控的降维安全保障。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 4. 800V高压碳化硅系统架构 (Original)
    TechnologyEntity(
        id="generic_800v_sic_architecture",
        name="800V高压碳化硅系统架构",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="800V High-Voltage SiC (Silicon Carbide) Platform",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高压电气/碳化硅功率半导体",
        aliases=[
            "800v",
            "800v架构",
            "800v高压平台",
            "800v平台",
            "全栈800v",
            "800v高压碳化硅",
            "碳化硅",
            "sic",
            "sic功率模块",
            "高压sic",
        ],
        summary="整车电气系统工作电压升级至800V（实际650V-871V）并采用碳化硅功率芯片的顶尖架构，电能传输热损耗减半，实现充电10-15分钟续航增加300-500km。",
        description=(
            "根据物理学公式焦耳定律（$P=UI, Q=I^2Rt$），在同等充电功率下，电压翻倍至800V意味着充电电流减半，线束与电池发热量直接锐减至四分之一。"
            "结合第三代半导体碳化硅（SiC）功率器件的高耐压、耐高温与微秒级高频开关特性，电机逆变器效率突破99%，整车综合续航提升5%~10%。"
            "在支持大功率快充的充电桩上，可承受300kW~500kW超充峰值，彻底告别服务区漫长等待。"
        ),
        technical_principles=[
            "全域高压化：电池包、电机逆变器、电空调压缩机、DC-DC转换器全系耐受800V-900V高压",
            "SiC碳化硅MOSFET功率半导体高频低内阻替代传统低效硅基IGBT",
        ],
        advantages=[
            "极速补能：充电10-15分钟即可补能300km至500km，喝杯咖啡时间即可满血出发",
            "整车高能效：碳化硅极大减少逆变热损耗，百公里电耗显著降低，续航更扎实",
            "自适应升压兼容：插在普通400V公共桩上也能通过车端升压模块跑满充电桩上限功率",
        ],
        limitations=[
            "碳化硅衬底晶圆与高压耐热绝缘器件成本远高于传统400V硅基器件",
            "极高电压对全车电磁屏蔽（EMC）与高压绝缘防漏电技术要求极其严格",
        ],
        sub_variants={
            "全栈全域800V": "电池、电驱、空调压缩机、车载充电机全链路800V高压碳化硅",
            "局部准800V / 500V-600V": "部分核心部件升压，过渡期方案",
        },
        representative_vehicles=["小米SU7 Max(871V)", "极氪001/007", "小鹏G6/G9/X9", "问界M9纯电版", "保时捷Taycan", "蔚来ET9(900V)"],
        standard_labels=["800V高压平台", "碳化硅", "SiC", "超快充", "低能耗", "升压充电"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "面对担心纯电跑长途充电慢的客户：‘800V就是未来的绝对主流，充电15分钟续航就多了300多公里，上个洗手间的时间就充满了！’",
            "对比400V竞品：突出800V碳化硅不仅充电快，平时开电耗也更省，冬天开暖风更不容易掉电，保值率远高一代。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 5. 4C / 5C 超快充技术体系 (Original)
    TechnologyEntity(
        id="generic_ultra_fast_charging_4c_5c",
        name="4C / 5C 超快充技术体系",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="4C / 5C Ultra-Fast Charging Technology",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="充电技术/高倍率极速补能",
        aliases=[
            "4c",
            "5c",
            "4c超充",
            "5c超充",
            "4c快充",
            "5c快充",
            "4c电池",
            "5c电池",
            "4c极速充电",
            "5c极速充电",
            "超充倍率",
            "5c麒麟电池",
        ],
        summary="充电倍率达电池额定容量4至5倍的极致补能体系（1C代表1小时充满，5C代表12分钟充满），最高充电功率超500kW，真正实现‘充电和加油一样快’。",
        description=(
            "充电倍率C（C-rate）衡量电池充放电快慢。传统新能源车普遍在1C~2C倍率（充电需30~45分钟）。"
            "4C与5C超充体系依靠负极高导锂纳米网络、超高电导率电解液及大面强效双向液冷技术，允许高达400A-600A超大电流瞬间涌入电芯，"
            "5C倍率下实现10%充至80%仅需10-12分钟，极速补能500公里，将电动车的长途出行补能体验真正拉到了传统燃油车加油的同一水平线。"
        ),
        technical_principles=[
            "多孔石墨快充负极与界面低能垒去溶剂化设计，彻底抑制大电流锂枝晶析出",
            "立体大面水冷板与电芯直接贴合，换热面积增加数倍，电芯温升控制在极小区间",
        ],
        advantages=[
            "补能时间压缩至极限：10分钟补充400-500公里续航，长途服务区无滞留压力",
            "高倍率放电性能协同提升，电池持久输出峰值功率，防连续衰减",
        ],
        limitations=[
            "需要匹配600kW以上液冷超充桩网络，若在老旧低功率桩上无法发挥最大5C峰值",
            "极速超充对电芯热管理与BMS健康监测算法提出极高要求",
        ],
        sub_variants={
            "4C超充体系": "普遍支持15分钟充至80%，当前主流旗舰标配",
            "5C超充体系": "峰值功率突破520kW，10-12分钟充至80%（如理想MEGA、极氪001/007麒麟/神行版）",
        },
        representative_vehicles=["理想MEGA(5C麒麟)", "极氪001(95kWh神行4C / 100kWh麒麟5C)", "小鹏G9(4C超充版)", "极氪007"],
        standard_labels=["4C超充", "5C超充", "高充放倍率", "液冷超充", "充电如加油", "10分钟补能500km"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向排斥纯电的传统燃油车车主介绍：‘5C超充让充电就像去加油站加油，停好车插上枪，刷个短视频或者买杯咖啡就补了400公里，完全改变用车生活方式；’",
            "结合品牌自建高压超充站网络，展现极致补能便利性与高端服务壁垒。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 6. 全自动换电补能系统 (Original)
    TechnologyEntity(
        id="generic_automated_battery_swapping",
        name="全自动换电补能系统",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Fully Automated Battery Swapping System",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="补能体系/车电分离快换",
        aliases=[
            "换电",
            "全自动换电",
            "换电站",
            "换电模式",
            "车电分离",
            "baas",
            "3分钟换电",
            "电池快换",
            "battery swap",
        ],
        summary="采用高精度机器人自动化机构在3至5分钟内完成全车动力电池拆装更换的补能系统，支持‘车电分离’降低初始购车价格，且电池始终在站端接受专业健康体检与恒温延寿慢充。",
        description=(
            "全自动换电系统将补能时间彻底缩短到与燃油车加油完全一致（单次换电只需3分钟）。"
            "车辆驶入换电站后通过激光雷达自适应泊车定位，举升机升起车辆，全自动RGV穿梭换电机器人通过高扭矩快换螺栓机构卸下亏电电池包并装入满电健康电池包。"
            "同时配合‘车电分离（BaaS）’购车模式，车主购车时可少付7~12万元电池成本，以月租形式租用电池，彻底免除电池衰减与二手车贬值的心里负担。"
        ),
        technical_principles=[
            "高寿命无损快换水冷加锁螺栓机构与浮动高压电连接器（承受万次插拔）",
            "站端多工位恒温恒湿集中智能仓储慢充仓与电芯全生命周期X光体检",
        ],
        advantages=[
            "极致补能速度：3-5分钟全自动完成，全程无需下车，刮风下雨暴雪天从容优雅",
            "解决电池寿命与二手残值焦虑：电池永远租用换新，电芯更新换代（如出新大容量电池）可随时按需灵活升级",
            "车电分离大幅降低提车门槛：裸车价格立减数万元，购车预算更亲民",
        ],
        limitations=[
            "换电站重资产建设与土地电网扩容成本极高，依赖全国广泛网络覆盖",
            "需要跨车型、跨品牌采用标准统一规格的电池包物理尺寸与卡扣接口",
        ],
        sub_variants={
            "乘用车第四代全自动换电站": "蔚来四代站（支持多品牌、23块电池仓、单次换电2.5分钟）",
            "商用车重卡底盘换电": "针对物流牵引车的高负荷快换系统",
        },
        representative_vehicles=["蔚来全系(ES6/ET5/ET7/EC6)", "乐道L60", "飞凡F7", "极氪(曹操出行换电车)"],
        standard_labels=["全自动换电", "车电分离", "BaaS", "3分钟补能", "电池灵活升级", "消除残值衰减焦虑"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "面对担心‘几年后电池衰减换电池贵死’的客户：‘换电车主永远不用担心电池衰减！电池所有权属于换电体系，每次换上来的都是经过站端健康体检的好电池，以后出了更大度数还能直接租用升级；’",
            "下雨天或严寒冬天的绝佳体验：坐在车内吹着空调听着歌，3分钟自动换好满电电池出发，不用像别人那样冒雨拔插沉重冰凉的充电枪。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 7. 永磁同步电机 (PMSM)
    TechnologyEntity(
        id="generic_permanent_magnet_synchronous_motor",
        name="永磁同步电机 (PMSM)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Permanent Magnet Synchronous Motor (PMSM)",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="电驱动系统/驱动电机",
        aliases=[
            "永磁同步",
            "永磁电机",
            "pmsm",
            "永磁同步电动机",
            "永磁转子",
            "扁线永磁电机",
        ],
        summary="转子采用稀土钕铁硼强磁体材料的交流驱动电机，拥有极高的工作效率和功率密度，是新能源汽车最主流的高效主驱动力源。",
        description=(
            "永磁同步电机由定子三相交流电产生旋转磁场，与转子永磁体磁场同步旋转产生电磁转矩。由于转子无需励磁电流产生磁场，"
            "基本消除了转子电阻发热损耗，电机在常用中低转速和日常工况下平均效率超过95%，非常适合城市通勤与长距离巡航节电。"
        ),
        technical_principles=[
            "转子内嵌钕铁硼永磁体提供恒定极性磁通",
            "定子交流逆变器矢量控制（FOC）产生精确电磁推力",
        ],
        advantages=[
            "电驱动效率极高，日常工况下电耗极低，有效增加整车纯电续航",
            "体积小、重量轻、功率扭矩密度极高，便于集成在前后桥机舱中",
        ],
        limitations=[
            "超高速巡航时转子产生反电动势，需要弱磁控制，高转速区间效率有所下滑",
            "依赖稀土钕铁硼矿产资源，原料成本受金属价格波动影响较大",
        ],
        sub_variants={
            "表贴式永磁 (SPM)": "磁钢贴于转子表面，制造简单，转速上限中等",
            "内置式永磁 (IPM)": "磁钢深嵌转子冲片内部，具备磁阻转矩，适合高速运转",
        },
        representative_vehicles=["比亚迪汉/海豹", "特斯拉Model 3/Y后驱版", "小鹏G6/P7", "小米SU7后驱版"],
        standard_labels=["永磁同步", "PMSM", "高效率", "稀土永磁", "低能耗驱动"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向注重日常电耗与续航的客户推荐：永磁电机不仅轻便安静，而且中低速效率极高，日常上下班开电耗极省。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 8. 交流异步感应电机 (IM)
    TechnologyEntity(
        id="generic_ac_induction_asynchronous_motor",
        name="交流异步感应电机 (IM)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="AC Induction Asynchronous Motor",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="电驱动系统/驱动电机",
        aliases=[
            "交流异步",
            "感应电机",
            "异步电机",
            "ac induction",
            "异步电动机",
            "鼠笼感应电机",
        ],
        summary="转子采用导电条鼠笼结构的感应式电动机，不依赖稀土永磁体，高速过载能力强且滑行无拖拽阻力，常用于双电机四驱车型的前辅驱电机。",
        description=(
            "交流异步电机利用定子旋转磁场在转子鼠笼中感应出电流并产生电磁力驱动旋转。其最大特点是转子在无激励电流时不产生磁场，"
            "车辆在单电机巡航工况下切断前电机供电时，转子可以零反电动势自由滑行，无需额外机械离合器脱开即可消除铁损和磁阻拖拽，高速爆发力与极速持久性极好。"
        ),
        technical_principles=[
            "电磁感应原理，转子感应电动势与滑差率协同作用产生转矩",
            "切断励磁即无阻力自由滑行，实现零拖滞电解耦",
        ],
        advantages=[
            "不含稀土材料，制造成本较低，耐受高温与极端机械过载",
            "高速巡航断电滑行阻力几乎为零，完美充当前驱副电机提升整体能效",
            "短时过载能力强，瞬时加速爆发力威猛",
        ],
        limitations=[
            "低负荷运转时励磁损耗较大，城市低速工况下的综合效率略低于永磁同步电机",
            "功率因数相对偏低，需要匹配容量更大的逆变器驱动",
        ],
        sub_variants={
            "铜转子感应电机": "转子导条采用纯铜以降低内阻提升效率",
            "铝转子感应电机": "铸铝鼠笼转子，成本极低，重量轻",
        },
        representative_vehicles=["特斯拉Model S/X", "蔚来ES6/ET7(前感应电机)", "极氪001(前感应四驱版)"],
        standard_labels=["交流异步", "感应电机", "前辅驱首选", "无磁阻拖滞", "高速爆发力"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向追求操控和性能的客户介绍：前异步+后永磁是性能车黄金搭档，日常后驱省电，超车时前电机瞬间唤醒爆发出狂暴四驱加速。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 9. 扁线发卡绕组电机 (Hairpin)
    TechnologyEntity(
        id="generic_hairpin_flat_wire_motor",
        name="扁线发卡绕组电机 (Hairpin)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Hairpin Flat Wire Winding Motor",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="电机制造技术/绕组工艺",
        aliases=[
            "扁线电机",
            "发卡电机",
            "hairpin",
            "扁线发卡",
            "多层扁线绕组",
            "8层扁线",
        ],
        summary="采用矩形截面铜扁线如发卡般插入定子铁芯槽内焊接成型的电机制造技术，槽满率大幅提升至70%以上，热阻大幅下降，电机峰值功率与散热能力跨越式增长。",
        description=(
            "传统圆铜线电机绕组内部存在大量圆形间隙，槽满率仅40%左右。扁线发卡绕组技术通过高精度自动化机器人将矩形漆包铜线折成U型发卡状插入铁芯槽中并进行激光焊接。"
            "扁线与扁线贴合极紧密，槽满率超过70%，直阻明显减小，发热大幅降低。同时扁线端部长度缩短20%以上，电机轴向尺寸更短，重量大幅减轻。"
        ),
        technical_principles=[
            "矩形截面扁铜线精密成型与定子铁芯槽高密度紧密叠合",
            "激光或微弧脉冲精密焊机对发卡端头进行无损高质量焊接",
        ],
        advantages=[
            "槽满率相比圆线提高30%以上，导电截面增加，铜损显著下降，CLTC综合效率提高1%~2%",
            "扁线间导热接触好，散热效率倍增，电机可持续输出大功率时间翻倍",
            "电机轴向尺寸缩短，体积更紧凑，减轻机舱空间占用与车身整备质量",
        ],
        limitations=[
            "高速运转时高频交变电流引起明显的集肤效应（Skin Effect）与邻近效应，高转速下交流阻抗上升",
            "自动化专用生产线投资巨大，对绕线与绝缘层防损伤工艺要求极高",
        ],
        sub_variants={
            "4层/6层扁线绕组": "早期量产方案，工艺相对成熟",
            "8层/10层/12层超多层扁线": "降低集肤效应损耗，转速突破21000rpm的旗舰电驱方案",
        },
        representative_vehicles=["比亚迪全系e平台3.0", "小米SU7(HyperEngine电机)", "极氪001/007", "特斯拉Model 3/Y"],
        standard_labels=["扁线电机", "Hairpin", "高槽满率", "低铜损", "紧凑轻量", "高功率密度"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向注重技术的客户介绍：扁线电机就像把杂乱的圆木变成了规整堆叠的方砖，体积更小、动力更强、发热更低，是现代高阶电驱的标配技术。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 10. SiC碳化硅功率逆变器
    TechnologyEntity(
        id="generic_silicon_carbide_inverter",
        name="SiC碳化硅功率逆变器",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Silicon Carbide (SiC) Power Inverter",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="电驱动控制器/功率半导体",
        aliases=[
            "碳化硅逆变器",
            "sic逆变器",
            "碳化硅控制器",
            "sic电控",
            "sic功率模块",
        ],
        summary="采用第三代宽禁带半导体碳化硅MOSFET开关管的电控逆变器，实现超高频开关与超低开关损耗，逆变效率高达99.5%，显著增加续航并缩减控制器体积。",
        description=(
            "电机逆变器负责将动力电池的直流电转换为驱动电机的三相交流电。传统硅基IGBT器件在几千赫兹高频开关下发热巨大、能量损耗明显。"
            "碳化硅（SiC）击穿电场强度是硅的10倍，电子饱和漂移速度是硅的2倍，导热率是硅的3倍。SiC逆变器开关损耗降低70%以上，"
            "支持20kHz以上高频调制，极大削减电流谐波与电机高频啸叫噪音，使整车CLTC纯电续航直接增加5%以上。"
        ),
        technical_principles=[
            "宽禁带SiC MOSFET单晶晶圆制备与纳米银烧结低热阻封装",
            "纳秒级高速驱动与低寄生电感母排拓扑设计",
        ],
        advantages=[
            "功率逆变效率突破99.5%，能量损耗极低，直接延长整车综合续航里程",
            "开关频率高，驱动电机运转电流波形更平滑，几乎彻底消除电机高频电磁啸叫声",
            "耐受高温（可达175-200℃），散热水冷散热模块体积可缩减50%",
        ],
        limitations=[
            "SiC衬底晶圆长晶速度缓慢，缺陷率较高，导致器件制造成本显著高于硅基IGBT",
            "极高开关速度产生较大的电压变化率（dv/dt），对电机漆包线耐压等级提出更高要求",
        ],
        sub_variants={
            "单面水冷SiC模块": "主流高集成度碳化硅电控方案",
            "双面水冷微通道SiC模块": "顶级大电流高功率方案，持续输出能力极佳",
        },
        representative_vehicles=["小米SU7", "极氪001/007", "保时捷Taycan", "小鹏G6/G9", "蔚来ET7/ET9"],
        standard_labels=["碳化硅逆变器", "SiC电控", "99%逆变效率", "静音电机驱动", "轻量化高功率密度"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向追求安静与续航的客户普及：碳化硅电控是电动车的心脏控制器，不仅让车更省电、续航多跑几十公里，而且踩电门时没有任何尖锐刺耳的电机电流啸叫。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 11. 多挡DHT专用混合动力变速器
    TechnologyEntity(
        id="generic_multispeed_dht_transmission",
        name="多挡DHT专用混合动力变速器",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Multi-Speed Dedicated Hybrid Transmission (Multi-Speed DHT)",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="混动变速箱/机械传动",
        aliases=[
            "多挡dht",
            "2挡dht",
            "3挡dht",
            "混动专用变速箱",
            "dht变速箱",
            "智能多挡混动",
        ],
        summary="集成发电机、驱动电机及2至3挡变速齿轮机构的混动变速器，让发动机在极低车速（如20-30km/h）即可参与直驱，兼顾低速大扭矩脱困与极速巡航低能耗。",
        description=(
            "单挡混动变速器（如传统单挡DHT）通常需要车速达到60-70km/h以上才能进入发动机直驱，低速大负荷爬坡或亏电超车时只能依靠串联发电，效率略有损失。"
            "多挡DHT（2挡或3挡）设置了不同的速比齿轮：1挡齿比大，适合低速急加速、爬坡与重载并联直驱；2/3挡齿比小，适合高速巡航降转速节油。"
            "结合全智能工况判断，实现全速域内燃机与双电机的最优动力协同释放。"
        ),
        technical_principles=[
            "双电机同轴/双轴布置，集成行星齿轮或定轴齿轮变速换挡机构",
            "电控液压或电子无缝离合器同步器换挡，动力无中断扭矩补偿",
        ],
        advantages=[
            "直驱速域宽泛：20km/h以上即可切入直驱，全工况动力输出底气充足",
            "高速巡航转速低，降低高速行驶风噪与发动机轰鸣，提升巡航燃油经济性",
            "大速比低挡位提供强悍轮端扭矩，越野爬坡与重载拖挂能力突出",
        ],
        limitations=[
            "齿轮挡位与离合机构增加系统重量和机械复杂度，对控制策略平顺性标定要求极高",
            "制造成本和后续机械齿轮润滑保养需求略高于单挡混动系统",
        ],
        sub_variants={
            "2挡DHT混动变速器": "结构与效率的平衡方案（如长城Hi4、广汽GMC）",
            "3挡DHT混动变速器": "全速域强动力方案（如吉利雷神3挡变频电驱DHT Pro）",
        },
        representative_vehicles=["领克08 EM-P(3挡DHT)", "吉利银河L7(3挡DHT)", "长城坦克500 Hi4-T", "哈弗枭龙MAX"],
        standard_labels=["多挡DHT", "3挡混动", "2挡电混", "全速域直驱", "爬坡大扭矩", "高速低油耗"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "向经常自驾跑山路、越野或长途高速的用户推荐多挡混动：低速有专门的大扭矩挡位爬坡猛，高速有高挡位让发动机在最佳工况转速直驱，动力随叫随到还特别省油。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 12. 发动机直驱离合混动架构
    TechnologyEntity(
        id="generic_direct_drive_clutch_hybrid",
        name="发动机直驱离合混动架构",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Direct-Drive Clutch Hybrid Architecture",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="混动电驱/驱动控制",
        aliases=[
            "发动机直驱",
            "混动直驱",
            "高速直驱",
            "直驱离合器",
            "并联直驱",
        ],
        summary="在混动系统中通过湿式液压离合器直接将发动机动力硬连接至驱动轴的传动技术，省去发电机到电机的二次转换损耗，实现高速工况最高的机械传动效率。",
        description=(
            "在纯串联或增程模式下，燃油化学能需要经历‘发动机燃烧转化为旋转机械能 - 发电机发电转化为电能 - 逆变器整流变频 - 驱动电机转化为轮端机械能’的多次转换，综合转换效率约为85%~88%。"
            "在时速80-120km/h的高速稳定巡航工况下，直接闭合直驱离合器，将发动机输出轴与车轮直连，机械传动效率高达97%以上，"
            "将内燃机高效率转速区间直接转化为轮端推力，彻底消除高速长途巡航电能转换的‘热能损耗’。"
        ),
        technical_principles=[
            "电控液压湿式多片离合器或单片摩擦离合器毫秒级柔顺结合",
            "电机在离合器啮合瞬间进行转速主动同步与扭矩削峰填谷",
        ],
        advantages=[
            "高速巡航油耗比纯串联增程低10%~15%，跑跨省长途更经济环保",
            "大油门全力超车时，发动机直驱与驱动电机全力并联放电，动力输出极其汹涌",
        ],
        limitations=[
            "低速频繁拥堵工况下无法直驱，依然依赖电驱，系统存在离合器磨损与标定要求",
            "离合器结合点若软件调校不精细，偶发工况下可能察觉轻微扭矩切换抖动",
        ],
        sub_variants={
            "单挡固定速比直驱": "中高速固定单速比直驱（如比亚迪DM-i）",
            "多挡速比离合直驱": "支持低速与高速多挡直驱（如长城Hi4、奇瑞C-DM）",
        },
        representative_vehicles=["比亚迪秦L/宋PLUS DM-i", "本田雅阁e:PHEV", "长城哈弗H6插混", "奇瑞风云A8"],
        standard_labels=["发动机直驱", "直驱离合器", "机械直连", "高速极省油", "并联双动力"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "对比串联增程说明：跑高速巡航时发动机通过离合器直接驱动车轮，没有电能二次损耗，车速越快越显省油优势，长途跨省出行成本极低。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 13. 多合一电驱集成总成 (X-in-1)
    TechnologyEntity(
        id="generic_all_in_one_electric_drive",
        name="多合一电驱集成总成 (X-in-1)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Highly Integrated X-in-1 Electric Drive Powertrain",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="电驱动架构/深度集成化",
        aliases=[
            "多合一电驱",
            "八合一电驱",
            "七合一电驱",
            "三合一电驱",
            "高度集成电驱",
            "x-in-1",
        ],
        summary="将驱动电机、电机控制器、减速箱、车载充电机(OBC)、DC-DC、高压配电箱(PDU)、BMS及整车控制器(VCU)等深度一体化整合的电驱动力模块。",
        description=(
            "早期电动汽车采用分立零部件布局，部件之间需要大量粗笨的高压三相电缆、水冷软管和金属支架连接，空间利用率低且总重量偏大。"
            "多合一电驱总成（如八合一或十二合一）通过共壳体、共散热水道及母排内部直连设计，省去几乎所有外部高压线束与连接器，"
            "整体重量降低15%~25%，体积缩减20%以上，不仅显著提高整车装配效率与可靠性，还为车内座舱与储物空间创造了富余空间。"
        ),
        technical_principles=[
            "功率电子与电机减速器共用高强度铝合金一体化压铸壳体",
            "高压母排内部刚性铜排直连消除接插件接触阻抗与EMC辐射",
        ],
        advantages=[
            "大幅减重与缩减占用空间，提升整车能效与前后行李厢容积",
            "取消外部高压铜线束与接头，大幅减少渗漏点与电气接插件故障率",
            "整车模块化装配工序大幅精简，制造成本和维修一致性高",
        ],
        limitations=[
            "高度集成后若内部某单一芯片或元器件受损，拆解单独维修成本较高",
            "电机电磁场对紧密贴合的微电控主板抗电磁干扰设计提出了极高挑战",
        ],
        sub_variants={
            "三合一电驱": "电机 + 减速器 + 逆变器（行业标准基础普及型）",
            "八合一/十二合一超级总成": "集成电机、控制器、减速器、OBC、DC-DC、PDU、VCU、BMS（如比亚迪八合一）",
        },
        representative_vehicles=["比亚迪海豚/元PLUS(八合一)", "长安深蓝SL03", "广汽埃安Hyper GT", "吉利极氪007"],
        standard_labels=["多合一电驱", "八合一", "深度集成", "高集成电动力", "减重省空间", "无外部高压线束"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向注重空间与可靠性的客户讲解：全车核心电驱动部件全部高科技集成在一个紧凑模块内，没有裸露易老化的高压粗线，车内空间更大，整车耐用性更有保障。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 14. 电机定转子主动喷淋直冷技术 (油冷电机)
    TechnologyEntity(
        id="generic_oil_cooled_electric_motor",
        name="电机定转子主动喷淋直冷技术 (油冷电机)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Direct Stator & Rotor Oil-Cooling Technology for Electric Motors",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="电驱散热技术/油冷热管理",
        aliases=[
            "油冷电机",
            "转子主动喷油",
            "定子喷淋冷却",
            "直冷电机",
            "油冷电驱",
        ],
        summary="采用绝缘低粘度传热冷却油直接喷淋浸润电机绕组端部与转子铁芯的先进散热技术，突破外壳水套导热瓶颈，电机持续输出峰值功率大幅提升30%以上。",
        description=(
            "传统电机采用外壳环形水冷套（水冷），冷却液只能在电机外壳铝壁流动，热量需要穿透定子铁芯和绝缘层才能被带走，导热路径长，转子内部发热难以散出。"
            "油冷电机采用高绝缘耐压合成冷却油，通过空心电机轴主动离心喷油和定子端部微孔多点喷淋，直接冲刷发热源（扁线绕组铜线与转子磁钢），"
            "散热效率提升数倍，支持车辆连续多次全油门弹射起步和德国不限速高速持续极速狂飙而不发生电机过热降频限扭。"
        ),
        technical_principles=[
            "中空转子轴内部导油孔依靠高速旋转离心力向磁钢端部强效甩油",
            "定子顶部喷淋油管精确对准多层发卡扁线焊点实现强制浸润换热",
        ],
        advantages=[
            "直接冷却热源，温升显著降低，电机峰值功率持续时间延长3倍以上",
            "油液具备绝缘与润滑双重特性，兼顾减速器齿轮箱润滑，精简油路系统",
            "支持极端工况下反复连续弹射起步不衰减",
        ],
        limitations=[
            "转子高速旋转时浸入油液会产生轻微搅油阻力损耗，需要精细设计刮油与导流板",
            "要求采用超低粘度、高闪点、与漆包线绝缘漆长期兼容的高等级绝缘合成油",
        ],
        sub_variants={
            "定子喷淋油冷": "仅在定子绕组两端布置喷淋管，结构简单",
            "转子轴心甩油+定子双喷淋": "全方位立体直冷，适用于超高性能赛道级电机（如小米V8s、极氪FR）",
        },
        representative_vehicles=["小米SU7 Max", "特斯拉Model 3/Y", "极氪001 FR", "比亚迪海豹", "蔚来ET5"],
        standard_labels=["油冷电机", "主动喷淋直冷", "转子甩油冷却", "连续弹射不衰减", "高效热管理"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向追求极致性能的年轻车主介绍：很多普通电车连续弹射两三次电机就过热报警疲软了，而油冷电机内部有高科技绝缘油直接给发热铜线冲凉降温，随便连续弹射十次依然满血输出！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 15. 液冷超充枪与高压液冷线缆
    TechnologyEntity(
        id="generic_liquid_cooled_charging_cable",
        name="液冷超充枪与高压液冷线缆",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Liquid-Cooled Charging Gun and Cable Architecture",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高压超充硬件/热管理线缆",
        aliases=[
            "液冷充电枪",
            "液冷超充线",
            "液冷快充桩",
            "液冷充电线缆",
            "600a液冷枪",
        ],
        summary="在线缆内部注入循环冷却液进行强制带走大电流发热的充电连接技术，不仅支持高达600A-800A的超大电流持续传输，更使线缆重量减轻50%，单手轻松握持插拔。",
        description=(
            "在传统风冷快充桩上，想要通过250A以上大电流，线缆铜芯必须做得极粗极沉（重达十几斤），女性车主甚至两手都难以拖动插拔，且枪头极易过热发烫导致充电降速保护。"
            "液冷超充技术在电缆导线周围包裹了专用冷却液循环管道，充电时水泵强效带走铜导体阻抗发热。铜截面积大幅减小，"
            "整根线缆外径纤细柔软如普通加油管，单手提枪毫不费力，同时稳定承载600A甚至800A电流，真正实现600kW超大功率极速输出。"
        ),
        technical_principles=[
            "线缆内部导线与低电导率冷却液循环回路同轴一体化共挤成型",
            "充电枪端子嵌入高精度PT100温度传感器实时闭环温控反馈",
        ],
        advantages=[
            "持续承载600A-800A极限大电流，不发生温升降功率保护",
            "线缆直径小、重量轻（比传统风冷线减重50%以上），无论男女单手即可优雅插拔",
            "枪头温升控制优异，长时间大功率充电触碰绝不烫手，安全级别高",
        ],
        limitations=[
            "液冷线缆与桩内冷却泵阀循环系统成本明显高于传统普通风冷充电机",
            "长期弯折使用下对内部液冷软管密封防漏液耐久性要求极高",
        ],
        sub_variants={
            "单相油冷/水冷充电机": "使用绝缘冷却油或水乙二醇混合液的循环方案",
            "600kW兆瓦级超级液冷桩": "全套桩体+枪线全液冷散热（如华为600kW全液冷超充、理想5C桩）",
        },
        representative_vehicles=["理想5C超充桩配套车型", "华为全液冷超充站配套车型", "极氪极充V3配套车型", "小鹏S4超快充"],
        standard_labels=["液冷超充枪", "轻便插拔", "600A大电流", "持续大功率充电", "全液冷快充桩"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向女性车主或家庭用户贴心介绍：很多公共快充桩的充电枪又粗又硬还沾满泥水，两只手都拎不动；我们的液冷枪线又细又软，重量比普通包包还轻，单手优雅插拔，充电速度快几倍还不发烫！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 16. 车网互动双向充放电 (V2G / V2L)
    TechnologyEntity(
        id="generic_v2g_bidirectional_charging",
        name="车网互动双向充放电 (V2G / V2L)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Vehicle-to-Everything Bidirectional Power Transfer (V2G / V2L)",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="双向电能传输/智能电网交互",
        aliases=[
            "v2g",
            "v2l",
            "对外放电",
            "双向逆变放电",
            "车对网放电",
            "车对车充电",
            "v2v",
        ],
        summary="支持车辆动力电池对外输出220V/380V交流电的双向电能交互技术，既可在户外露营时为电烤炉、投影仪等电器供电，又可在用电峰谷期向电网反向送电赚取收益。",
        description=(
            "传统新能源汽车充电是单向输入。车网互动技术通过车端双向OBC（车载充电机）或专用直流放电桩，实现电能双向互通。"
            "对外放电（V2L - Vehicle to Load）支持3.3kW~6kW的220V家用插排输出，户外露营可随时吃火锅、煮咖啡、开移动家庭影院；"
            "车对网（V2G - Vehicle to Grid）允许车辆在夜间谷电时段低价买电，在白天用电高峰期反向售电给国家电网赚取峰谷差价，车辆化身为‘移动巨型充电宝’。"
        ),
        technical_principles=[
            "全桥双向谐振DC-DC变换器与双向四象限PWM逆变拓扑",
            "智能防孤岛保护与电网同频同相并网控制算法",
        ],
        advantages=[
            "极大丰富用车生活场景：露营用电自由，断电停电时可作为家庭应急备用电源",
            "通过V2G削峰填谷，参与电网需求侧响应，为车主创造被动经济收益",
            "紧急情况下可作为移动救援车，通过V2V（车对车）为趴窝亏电友车反向救援补能",
        ],
        limitations=[
            "频繁向电网反向放电会增加动力电池充放电循环次数，对电池寿命管理有一定要求",
            "V2G大规模商用依赖电网双向计量电表升级与电力市场交易政策支持",
        ],
        sub_variants={
            "V2L (车对负载对外放电)": "车端3.3kW~6.6kW交流放电枪输出，户外露营必备",
            "V2G (车对电网互动)": "大功率与电网双向调度交互",
            "V2V (车对车紧急救援充电)": "直接通过专用转接线为其他电动车紧急充电",
        },
        representative_vehicles=["比亚迪全系(VTOL对外放电)", "小鹏G6/G9", "理想全系", "蔚来全系", "极氪001/007"],
        standard_labels=["V2L对外放电", "V2G车网互动", "露营用电自由", "移动电站", "家庭应急电源", "双向充放电"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向爱好自驾露营的客户展示：车里带着相当于几十个大号户外移动电源的电量，插上放电排插就能直接带起电磁炉、烤箱、咖啡机，周末带家人孩子去郊外露营其乐融融；",
            "向家庭用户说明应急价值：家里一旦停电，车子可以反向给家里冰箱和照明供电好几天，居家安全感满满。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
    # 17. 增程专用高热效率专用发动机
    TechnologyEntity(
        id="generic_range_extender_internal_combustion",
        name="增程专用高热效率专用发动机",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Dedicated Range-Extender Engine (High Thermal Efficiency ICE)",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="内燃机工程/增程器专用动力",
        aliases=[
            "专用增程器",
            "增程专用发动机",
            "阿特金森增程器",
            "高热效率增程发动机",
            "增程内燃机",
        ],
        summary="专为增程发电工况正向深度定制的内燃机，取消全速域机械宽幅调速要求，全聚焦于高压缩比、高滚流比与超高热效率（普遍超40%~45%），静音发电机油转换率极高。",
        description=(
            "传统燃油车发动机需要兼顾怠速、急加速、极速狂飙等极其宽泛复杂的工况，热效率往往只有30%~35%，且噪音震动难以压制。"
            "增程专用发动机彻底摆脱了复杂的机械负载工况，只需在恒定的发电转速点（如1500~2500rpm）稳定输出转矩。"
            "工程师可以极限优化阿特金森/米勒循环超高压缩比、350bar高压缸内直喷以及废气再循环（EGR）技术，热效率轻松突破41%~45%，"
            "一升汽油可稳定发出3.3至3.6度电，配合双平衡轴与全包覆声学罩，运转声几乎完全隐形于环境底噪中。"
        ),
        technical_principles=[
            "高几何压缩比（12.5~15:1）与深度米勒循环进气门早关（EIVC）",
            "高滚流燃烧室设计结合350bar/500bar高压燃油微粒化喷射",
        ],
        advantages=[
            "超高发电油电转换比：1升油发电突破3.3kWh以上，显著降低亏电油耗",
            "转速高度平稳受控，配合全悬置衬套与声学隔音包覆，舱内感知无震动无轰鸣",
            "零部件精简：取消不必要的可变气门升程等复杂机械，制造成本低且运行极其皮实耐用",
        ],
        limitations=[
            "因专注于定点高效发电，低转速扭矩响应和宽域动态提速性能不如传统宽域燃油机",
            "对燃油清洁度与高压缩比爆震控制标定有一定要求",
        ],
        sub_variants={
            "1.5T四缸增程专用发动机": "中大型高端增程SUV黄金动力源（如理想L系列、问界M7/M9）",
            "1.5L自然吸气增程发动机": "紧凑型代步增程轿车经济动力源（如长安深蓝）",
        },
        representative_vehicles=["问界M9/M7(1.5T深度米勒)", "理想L7/L8/L9(1.5T四缸增程器)", "阿维塔07增程版", "深蓝S07"],
        standard_labels=["增程专用发动机", "高热效率", "阿特金森循环", "一升油发3.5度电", "图书馆级静音", "专用增程器"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "向嫌弃传统插混发动机噪音大的客户展示：增程器专门为了发电而生，启动时转速非常柔和，车内老人小孩根本察觉不到发动机在工作，而且一升油能发3度半的电，又安静又省钱！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="补能与电气",
    ),
]

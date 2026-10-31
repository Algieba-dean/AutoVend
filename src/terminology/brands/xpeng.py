"""
XPeng Proprietary Automotive Technology Registry (src/terminology/brands/xpeng.py).
Contains 30 comprehensive proprietary technologies for XPeng / MONA ecosystems.
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

XPENG_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 小鹏 XNGP (Original)
    TechnologyEntity(
        id="xpeng_xngp",
        name="小鹏 XNGP 全场景智能导航辅助驾驶",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG XNGP All-Scenario Navigation Guided Pilot",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="端到端AI大模型全场景智能驾驶",
        aliases=[
            "xngp",
            "小鹏xngp",
            "xngp智驾",
            "小鹏智驾",
            "ngp",
            "xpeng ngp",
            "天玑智驾",
        ],
        summary="小鹏全栈自研高阶智能辅助驾驶系统，依托端到端大模型与双Orin-X高算力芯片，支持全国范围内城市与高速无图全场景领航开城。",
        description=(
            "小鹏汽车国内最早布局高阶辅助驾驶研发体系。XNGP系统从传统人工手写规则全面进化为神经网络端到端大模型架构，"
            "能够应对无保护左转、拥堵路口变道博弈、环岛汇入通行及跨楼层代客泊车，智驾可用里程和行车丝滑度位列行业第一梯队。"
        ),
        technical_principles=[
            "端到端架构（神经网直接拟合输入视频流到驾驶轨迹）",
            "自研超强XNet静态/动态感知网络及XPlanner实时轨迹规划器",
        ],
        advantages=[
            "全国道路只要有导航就能开，复杂路况超车并线果断老练",
            "智能泊车及记忆泊车（VPA）成功率与易用度处于行业顶尖水准",
        ],
        limitations=[
            "在未选配双Orin高算力硬件的Pro基础版车型上仅支持高速公路NGP，无法使用城市XNGP",
        ],
        sub_variants={
            "Pro版": "单Orin芯片/纯视觉方案，支持高速NGP与全场景泊车",
            "Max版": "双Orin芯片+双激光雷达，支持全国城市XNGP高阶领航辅助",
        },
        representative_vehicles=["小鹏G6", "小鹏G9", "小鹏X9", "小鹏P7+"],
        standard_labels=["全场景城市NGP", "端到端AI智驾", "激光雷达高阶辅助驾驶", "全场景智能泊车"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向追求高科技智能出行与长途高速防疲劳的用户推荐，安排实际道路试驾感受自动变道超车的拟人果断。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 2. 扶摇全域架构 (Original)
    TechnologyEntity(
        id="xpeng_fuyao",
        name="SEPA 2.0 扶摇全域智能进化架构",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="SEPA 2.0 Fuyao Architecture",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="全栈800V高压+前后一体压铸纯电架构",
        aliases=[
            "扶摇架构",
            "sepa 2.0",
            "扶摇平台",
            "小鹏扶摇",
            "sepa2.0",
            "sepa",
        ],
        summary="小鹏历时5年耗资百亿研发的整车技术架构，集成了全栈800V高压SiC碳化硅平台、前后一体化铝压铸车身与CIB电池车身一体化技术。",
        description=(
            "扶摇架构使小鹏车型在补能效率、整车制造成本和车身扭转刚度上实现了飞跃。全系标配800V超快充（5分钟补能200km+），"
            "并国内首家量产前后一体化铝压铸车身，整车扭转刚度达41600 N·m/deg，并标配X-EEA电子电气架构支持极速整车级OTA。"
        ),
        technical_principles=[
            "全栈全域800V高压SiC碳化硅高压电驱平台",
            "前后一体化高压铝压铸 + CIB电池底盘一体化结构",
        ],
        advantages=[
            "不仅车端800V，在全国通用公共充电桩上通过升压技术也能获得比竞品更快的充电功率",
            "整车轻量化且刚度极强，车身NVH静谧性显著改善",
        ],
        limitations=[
            "早期推出车型内饰豪华感及品牌溢价相比豪华车略需沉淀",
        ],
        sub_variants={},
        representative_vehicles=["小鹏G6", "小鹏G9", "小鹏X9"],
        standard_labels=["全栈800V架构", "前后一体化铝压铸", "CIB电池一体化", "高能能电驱底盘"],
        equivalence_group_id=None,
        sales_talking_points=[
            "对比20万级同价位竞品多为400V老旧平台，强调小鹏扶摇架构“标配即800V+一体压铸”的降维打击质价比。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 3. 小鹏 XNet 深度视觉神经网络感知架构
    TechnologyEntity(
        id="xpeng_xnet_perception",
        name="小鹏 XNet 深度视觉神经网络感知架构",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG XNet Deep Visual Perception Network",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="BEV多相机时空融合感知大模型",
        aliases=[
            "xnet",
            "小鹏xnet",
            "xnet2.0",
            "xnet深度视觉",
            "bev感知网络",
            "动态静态xnet",
        ],
        summary="小鹏全栈自研的深度视觉神经网络架构，将车身四周摄像头的多传感器原始图像实时投影至BEV鸟瞰空间，实现动静态环境高精感知。",
        description=(
            "XNet通过自研神经网络将多个摄像头采集的时序视频帧融合成3D全局视角。在XNet 2.0中进一步融入了占用网络（Occupancy Network），"
            "不仅能够精准识别红绿灯、斑马线、行人和车辆，还能对任意未标注的不规则障碍物进行体素网格化重构，彻底摆脱对高精地图的严重依赖。"
        ),
        technical_principles=[
            "时空联合Transformer架构与BEV（鸟瞰视角）多相机特征拼接投影",
            "Occupancy占用网络实现通用未知物理障碍物三维立体网格化重建",
        ],
        advantages=[
            "无图城市NOA感知基石，在无高精地图区域依然能清晰识别车道拓扑",
            "极大减少传感器硬件异构融合误差，提升雨雾暗光工况下的检测置信度",
        ],
        limitations=[
            "网络参数量极其庞大，需要搭配高吞吐算力芯片与超算中心海量数据训练",
        ],
        representative_vehicles=["小鹏G6", "小鹏G9", "小鹏X9", "小鹏P7+"],
        standard_labels=["XNet感知网络", "BEV鸟瞰视角", "占用网络Occupancy", "无图导航基础"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向科技极客客户解释：小鹏通过XNet算法让汽车具备了像人类大脑一样的时空三维感知能力，看路比老司机还清楚。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 4. 小鹏 XPlanner 神经网络规划大模型
    TechnologyEntity(
        id="xpeng_xplanner",
        name="小鹏 XPlanner 神经网络轨迹规划大模型",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG XPlanner Neural Trajectory Planner",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="端到端拟人化规控行为决策模型",
        aliases=[
            "xplanner",
            "小鹏xplanner",
            "规划大模型",
            "小鹏规划大模型",
            "端到端规划器",
            "拟人化规控",
        ],
        summary="基于数千万公里人类老司机优质驾驶轨迹训练生成的神经网络规划大模型，大幅消除传统规则算法的生硬刹车、机械顿挫与无效变道。",
        description=(
            "传统智驾使用大量人工编写的‘if-else’规则代码，在复杂城中村、加塞严重路口常常陷入犹豫停顿。XPlanner由海量专家驾驶数据训练而成，"
            "能够像老司机一样提前预判周围车辆走行动机，在环岛通行、借道绕行与狭窄车道会车时表现出丝滑、自信且合乎安全礼仪的博弈决策能力。"
        ),
        technical_principles=[
            "生成式轨迹预测与强化学习博弈控制算法",
            "端到端多任务联合优化网络，减少感知与规控各层级之间的信息衰减",
        ],
        advantages=[
            "大幅减少城市智驾‘画龙’、急刹顿挫和无效变道，乘坐舒适感无限接近老司机",
            "复杂拥堵路段汇入与变道博弈成功率超过95%，通行效率显著提高",
        ],
        limitations=[
            "面对极端偶发边缘工况（Corner Cases）仍需配合底层安全防碰撞规则兜底",
        ],
        representative_vehicles=["小鹏G6", "小鹏G9", "小鹏X9", "小鹏P7+"],
        standard_labels=["XPlanner规划器", "端到端规控", "老司机拟人驾驶", "动态博弈决策"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "在试驾城市复杂路况时，让客户体验开启XNGP后在加塞车流中平顺切入变道，感受超越普通司机的丝滑果断。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 5. 小鹏天玑 AIOS 车机操作系统
    TechnologyEntity(
        id="xpeng_tianji_os",
        name="小鹏天玑 AIOS 车载全场景智能操作系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG AI Dimensity OS (Tianji OS)",
        category=TechCategory.COCKPIT_OS,
        subcategory="端到端AI大模型全栈车机操作系统",
        aliases=[
            "天玑os",
            "小鹏天玑",
            "天玑系统",
            "ai天玑",
            "天玑aios",
            "xos天玑",
        ],
        summary="行业首个将AI端到端大模型深度全面应用于座舱与智驾的车载操作系统，支持分屏多任务、AI小P语音大模型与SR实景驾驶感知融合渲染。",
        description=(
            "天玑系统界面重新定义了车机交互逻辑。支持主副驾左右分屏自由切换，智驾SR大模型实景渲染覆盖全国所有车道及人行横道；"
            "系统内置AI小P大模型，拥有常识推理、行程智能规划与车控逻辑组合能力，并支持全场景‘AI保镖’与‘AI代驾’点到点跨城市路线记忆。"
        ),
        technical_principles=[
            "高通骁龙8295P旗舰座舱算力底座与自研跨域数据软总线",
            "端云协同多模态AI大语言模型蒸馏与车载硬件低时延适配框架",
        ],
        advantages=[
            "系统UI操作如旗舰平板般跟手，分屏任务流转高效合理",
            "SR实景大模型将车身感知到的全部三维物理世界纤毫毕现渲染在屏幕上，掌控感极强",
        ],
        limitations=[
            "部分基于大模型的深度语义解析对弱网地库环境依赖端侧离线轻量模型",
        ],
        representative_vehicles=["小鹏X9", "小鹏G6", "小鹏G9", "小鹏P7+"],
        standard_labels=["天玑AIOS", "AI小P大模型", "全场景分屏", "SR大模型全景渲染"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "现场演示天玑OS的多任务分屏与AI小P连续多意图语音交互，让客户感受行业第一梯队的丝滑车机体验。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 6. 小鹏 Xmart OS 智能座舱系统
    TechnologyEntity(
        id="xpeng_xos_cockpit",
        name="小鹏 Xmart OS 智能座舱操作系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG Xmart OS Smart Cockpit System",
        category=TechCategory.COCKPIT_OS,
        subcategory="全场景全时连续语音交互智能座舱",
        aliases=[
            "xmart os",
            "xmart",
            "小鹏车机",
            "全场景语音",
            "全时语音",
            "小p语音",
        ],
        summary="小鹏汽车经典智能座舱系统，首创车载全场景全时免唤醒语音交互与百万级丰富应用生态，奠定了小鹏汽车智能化先锋口碑。",
        description=(
            "Xmart OS在国内最早实现‘连续对话、可见即可说、随时打断、四音区独立识别’的语音交互体验。车内任何乘员只需直接开口说出指令，"
            "无需念出‘你好小P’即可精准响应。系统支持海量车载娱乐App、冥想空间场景模式以及深度的智能家居跨生态远程联动。"
        ),
        technical_principles=[
            "四音区声源定位定向拾音与车载声学降噪分离降回声算法",
            "高并发GUI语义解析树与‘可见即可说’无缝组件遍历映射",
        ],
        advantages=[
            "语音响应速度低于1秒，全车软硬件功能超90%均可通过语音操控",
            "多意图并行执行能力强，支持一句话说出多个不同车控需求",
        ],
        limitations=[
            "早期车型受芯片算力制约，在部分复杂3D渲染动效上不如最新8295P车型华丽",
        ],
        representative_vehicles=["小鹏P7", "小鹏G3i", "小鹏P5"],
        standard_labels=["Xmart OS", "全场景免唤醒语音", "可见即可说", "四音区声源定位"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "连续说出‘关闭车窗、调低温度、播放周杰伦的歌’等多条长指令，向客户展示小P零延迟秒级执行的震撼能力。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 7. 小鹏图灵自研 AI 芯片
    TechnologyEntity(
        id="xpeng_turing_chip",
        name="小鹏图灵自研 AI 芯片 (XPENG Turing AI Chip)",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG Turing In-House AI Chip",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="面向大模型的多核异构高算力车规SoC",
        aliases=[
            "图灵芯片",
            "小鹏图灵",
            "图灵ai芯片",
            "小鹏自研芯片",
            "turing芯片",
            "40核处理器",
        ],
        summary="小鹏汽车全栈自研的高性能车规级AI算力芯片，专为大模型设计，单颗芯片算力相当于多颗主流旗舰智驾芯片，面向高阶智驾、智能座舱与人形机器人。",
        description=(
            "图灵芯片集成40核高性能处理器与自研神经网络加速单元（NPU），具备极高的数据吞吐能效比。能够直接原生运行300亿参数大模型，"
            "并在芯片级集成了双核独立安全岛，达到ASIL-D最高功能安全等级，为小鹏从辅助驾驶跃升至完全无人驾驶（Robotaxi）及具身智能提供算力底座。"
        ),
        technical_principles=[
            "面向Transformer与扩散大模型定制的片上向量计算单元架构",
            "超高带宽片上互联网络（NoC）与硬件级独立安全岛隔离架构",
        ],
        advantages=[
            "一颗芯片即可同时驱动高阶智能驾驶与复杂座舱多模态大模型",
            "能效比极高，降低PCB板卡空间占用并大幅削减外部供应链硬件采购成本",
        ],
        limitations=[
            "自研芯片流片与软件工具链生态需要长期软件工程积累与适配测试",
        ],
        representative_vehicles=["小鹏P7+", "小鹏未来换代新车型", "小鹏飞行汽车与人形机器人"],
        standard_labels=["图灵芯片", "自研AI芯片", "40核高性能处理器", "大模型专用SoC"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "对比那些依赖英伟达或高通公版方案的竞品，展示小鹏在底层硬核芯片研发上的技术硬实力与成本自主权。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 8. 小鹏“鹰眼”纯视觉高阶智驾感知方案
    TechnologyEntity(
        id="xpeng_hawkeye_vision",
        name="小鹏“鹰眼”视觉高阶智驾方案 (XPENG AI Hawkeye Vision)",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG AI Hawkeye Visual Sensing Solution",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="高动态轻量化纯视觉端到端智驾系统",
        aliases=[
            "鹰眼视觉",
            "小鹏鹰眼",
            "鹰眼智驾",
            "纯视觉方案",
            "鹰眼感知",
            "hawkeye",
        ],
        summary="小鹏首创的行业领先单/双目高动态鹰眼视觉智驾系统，取消昂贵的激光雷达，依靠超高感光摄像头与端到端大模型实现同等甚至更强的高阶智驾表现。",
        description=(
            "鹰眼方案采用行业顶尖的高动态范围（HDR）车载摄像头，感光度提升数倍，即便在逆光出隧道、暴雨夜间及无路灯乡村也能精准捕捉微小路面信息。"
            "配合端到端大模型在端侧的高效运算，不仅让高阶智能驾驶成本大幅下探，使20万以下车型标配全场景高阶智驾，更实现了全球道路通用通行。"
        ),
        technical_principles=[
            "Lofic高动态感光技术，彻底解决进出隧道瞬时强光过曝与夜间眩光失真",
            "纯视觉三维占据网格与时序流体光流估计算法",
        ],
        advantages=[
            "大幅削减激光雷达硬件成本，让普通工薪家庭用车也能享受顶级城市高阶领航",
            "没有车顶激光雷达凸起‘犄角’，车顶流线更加平滑美观且风阻更低",
        ],
        limitations=[
            "面对极端浓雾或者严重泥泞遮挡镜头表面时，依赖算法置信度降级告警",
        ],
        representative_vehicles=["小鹏P7+", "MONA M03"],
        standard_labels=["鹰眼视觉", "纯视觉高阶智驾", "Lofic高动态摄像头", "零激光雷达全场景领航"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向追求科技质价比的用户推荐：小鹏鹰眼视觉打破了‘不装激光雷达就没有高阶智驾’的迷信，用算法实力给用户省钱。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 9. 小鹏 S4 超快充桩体系
    TechnologyEntity(
        id="xpeng_s4_supercharger",
        name="小鹏 S4 液冷超快充桩网络体系",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG S4 Liquid-Cooled Supercharger",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="480kW高压大电流液冷充电桩基础设施",
        aliases=[
            "s4超充",
            "小鹏s4",
            "s4充电桩",
            "480kw超充",
            "小鹏液冷超充",
            "s4快充",
        ],
        summary="小鹏自建的高功率超快充桩，单桩峰值充电功率高达480kW，最大输出电流670A，充电5分钟可补能200公里以上。",
        description=(
            "S4超充桩采用高压全液冷循环散热技术，充电枪线直径仅约3厘米，单手即可轻松提起插拔；"
            "结合全栈800V碳化硅车型，可在15分钟内将电量从10%充至80%，并配备即插即充、智能地锁联动与车端智能预热升温技术。"
        ),
        technical_principles=[
            "液冷电缆与液冷枪头强制循环循环回路，温升控制极佳",
            "动态功率智能调配母线拓扑，实现多桩并联高低压自适应匹配",
        ],
        advantages=[
            "充电速度极快，在服务区上个洗手间喝杯水的时间即可完成补能继续出发",
            "枪线极轻巧柔韧，彻底告别传统笨重油腻粗黑充电枪的不良体验",
        ],
        limitations=[
            "需搭配支持800V高压超充的车型方可拉满480kW峰值功率",
        ],
        representative_vehicles=["小鹏G9", "小鹏G6", "小鹏X9", "小鹏P7+"],
        standard_labels=["S4超充", "480kW液冷充电", "670A最大电流", "5分钟补能200km"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向担心充电慢耽误时间的客户演示S4超充实测充电曲线，5分钟补能200公里的速度彻底消除纯电焦虑。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 10. 小鹏 S5 超快充桩技术体系
    TechnologyEntity(
        id="xpeng_s5_supercharger",
        name="小鹏 S5 极速全液冷超快充体系",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG S5 Ultra Fast Liquid-Cooled Supercharger",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="800kW超千伏级极速补能基础设施",
        aliases=[
            "s5超充",
            "小鹏s5",
            "s5充电桩",
            "800kw超充",
            "小鹏s5超充",
            "极速液冷超充",
        ],
        summary="小鹏新一代旗舰级液冷超充桩，最大输出功率飙升至800kW，峰值充电电流高达800A，实现‘一秒补充超过一公里’的梦幻补能速度。",
        description=(
            "S5在S4基础上进一步提升电压等级与电流承受能力，原生支持最高1000V高压平台，配备极速启动逻辑（插枪即充响应时延压缩至13秒以内）；"
            "融合储能柜与智能微电网技术，即便在电网负荷紧张的高速服务区也能瞬时爆发出800kW超高峰值功率。"
        ),
        technical_principles=[
            "千伏级高耐压功率开关模块与超高导热系数全液冷集成散热",
            "储充一体化智能调峰微电网（BESS）与车-桩-网高频通信协议",
        ],
        advantages=[
            "补能速度达到物理充电极限，‘一秒一公里’真正比肩传统燃油车加油体验",
            "结合场站储能，不受普通电网变压器容量不足的瓶颈限制",
        ],
        limitations=[
            "场站建设技术标准极高，目前主要优先布局于国家主干高速公路核心服务区",
        ],
        representative_vehicles=["小鹏全系800V高压纯电车型"],
        standard_labels=["S5超充桩", "800kW超级快充", "一秒一公里", "储充一体化微电网"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向追求最前沿科技的客户说明小鹏在全国极速铺设的S5超充网络，享受行业最高天花板补能速度。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 11. 小鹏全栈 800V 高压碳化硅电驱动平台
    TechnologyEntity(
        id="xpeng_800v_sic_platform",
        name="小鹏全栈 800V 高压 SiC 碳化硅平台系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG Full-Stack 800V High Voltage SiC Platform",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="全链路高压碳化硅动力电气系统",
        aliases=[
            "小鹏800v",
            "小鹏800v碳化硅",
            "小鹏碳化硅平台",
            "小鹏全栈800v",
            "小鹏800v高压平台",
        ],
        summary="不仅电池端800V，包括电机、电控、空调压缩机、DC-DC等在内的全链路800V高压电气系统，综合工况电驱效率高达95.5%。",
        description=(
            "相较市面上部分‘伪800V’（仅快充端升压、其余仍为400V部件），小鹏全栈800V在车身内部全部采用高耐压碳化硅功率器件。"
            "高压使得同等功率下电流缩小一半，电阻发热损耗大幅降低，车辆不仅充电极快，而且百公里综合电耗低至13.2kWh，续航达成率处于行业第一梯队。"
        ),
        technical_principles=[
            "全链路碳化硅MOSFET功率半导体应用，开关损耗比传统IGBT降低超60%",
            "高集成度智能升压充电技术，在传统第三方400V普通桩上也能满功率快充",
        ],
        advantages=[
            "续航扎实不虚标，百公里电耗极低，冬季与高速工况续航衰减显著小于同行",
            "在任何第三方充电桩都能自动升压充电，充电速度比普通400V车快30%以上",
        ],
        limitations=[
            "碳化硅衬底晶圆成本相对较高，对制造工艺公差与绝缘防护等级要求极其严苛",
        ],
        representative_vehicles=["小鹏G6", "小鹏G9", "小鹏X9", "小鹏P7+"],
        standard_labels=["全栈800V", "SiC碳化硅电驱", "超低百公里电耗", "全国充电桩自动升压"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "对比很多号称800V但电耗高得吓人的竞品，强调小鹏实打实的全栈800V带来的超低能耗与高续航达成率。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 12. 小鹏 CIB 电池车身一体化技术
    TechnologyEntity(
        id="xpeng_cib_battery",
        name="小鹏 CIB 电池车身一体化技术 (Cell Integrated Body)",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG CIB (Cell Integrated Body) Technology",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="电池包结构与下车身一体化集成设计",
        aliases=[
            "cib",
            "小鹏cib",
            "cib电池",
            "小鹏电池车身一体化",
            "电池上盖车身地板一体化",
        ],
        summary="小鹏创新的电池集成技术，将电池包上盖直接作为车身地板，释放车内垂直头部空间并大幅增强整车抗侧碰与扭转刚度。",
        description=(
            "传统纯电动车由于底盘额外悬挂厚重电池包，往往导致车内乘员坐姿‘小板凳’且头部空间压抑。小鹏CIB技术将电池包上盖与车身下地板融为一体，"
            "垂直空间节省数厘米，同时电池包作为坚固受力梁参与整车承载，使车身扭转刚度突破40000 N·m/deg，带来极其沉稳的行驶质感与顶级碰撞安全。"
        ),
        technical_principles=[
            "电池托盘与车身门槛梁、横梁的高刚度结构级机械粘结与环氧胶封闭",
            "电芯三维蜂窝吸能拓扑，遇侧面猛烈撞击时电芯舱形变量降低超30%",
        ],
        advantages=[
            "车内垂直头部空间显著充裕，后排乘客坐姿自然舒展不压抑",
            "整车扭转刚度与底盘整体感极强，过坑洼颠簸不松散零杂音",
        ],
        limitations=[
            "一体化封装后若需更换内部单个模组施工流程复杂，通常采用售后整包养护",
        ],
        representative_vehicles=["小鹏G6", "小鹏X9"],
        standard_labels=["CIB电池车身一体化", "释放头部空间", "超高扭转刚度", "侧碰高安全防护"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "让高个子客户坐进后排体验充裕的头顶空间，说明这就是CIB电池车身一体化带来的空间魔法。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 13. 小鹏前后一体化高压铝压铸制造技术
    TechnologyEntity(
        id="xpeng_front_rear_gigacasting",
        name="小鹏前后一体化高压铝压铸制造工艺",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG Front & Rear Integrated High-Pressure Die-Casting",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="超万吨级巨型压铸车身制造技术",
        aliases=[
            "小鹏一体压铸",
            "前后一体压铸",
            "小鹏压铸",
            "12000吨压铸",
            "前后一体化铝压铸",
        ],
        summary="中国首家量产前后一体化铝压铸车身的汽车品牌，使用高达12000吨锁模力压铸机，将数百个钣金件化繁为简合二为一。",
        description=(
            "在小鹏扶摇架构产线上，12000吨超级压铸岛将原本由数百个冲压件焊接而成的前后车身结构，分别以两个超大单体铸铝件一次性压铸成型。"
            "车身减重17%，焊点减少近300个，不仅彻底杜绝了长期车身疲劳虚焊异响，更大幅提升了后碰与前碰时对乘员舱的稳固防护。"
        ),
        technical_principles=[
            "自研高延展率免热处理高强韧铝合金材料，抗冲击韧性极佳",
            "高真空多点精密温控压铸模具与微米级激光在线探伤质检",
        ],
        advantages=[
            "整车轻量化效果显著，操控响应更灵敏，整车静谧NVH表现质的飞跃",
            "消除焊接形变公差，车门车窗接缝均匀细腻，长期驾驶坚固如初",
        ],
        limitations=[
            "前期模具研发投入与超大吨位压铸机固定资产折旧成本极高",
        ],
        representative_vehicles=["小鹏G6", "小鹏X9"],
        standard_labels=["前后一体压铸", "12000吨超级压铸", "免热处理高强铝", "车身轻量化"],
        equivalence_group_id=EquivalenceDomain.GIGACASTING_STRUCTURE,
        sales_talking_points=[
            "向注重造车做工与耐久度的客户强调：小鹏是中国第一个量产前后双一体压铸的品牌，车身刚度媲美百万级豪华跑车。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 14. 小鹏主动式后轮转向系统 (X9 搭载)
    TechnologyEntity(
        id="xpeng_rear_wheel_steering",
        name="小鹏主动式后轮转向系统 (Active Rear-Wheel Steering)",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG Active Rear-Wheel Steering System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="后轴随动与主动线控转向执行系统",
        aliases=[
            "小鹏后轮转向",
            "x9后轮转向",
            "小鹏主动后轮转向",
            "5.4米转弯半径",
        ],
        summary="小鹏在旗舰MPV X9上全系标配的主动后轮转向技术，后轮转向角度达±5度，使近5.3米庞大MPV拥有5.4米甚至比智能小车还小的转弯半径。",
        description=(
            "彻底颠覆了传统大型MPV‘开起来像开大船’、窄巷无法掉头、地库停车艰难的刻板印象。低速转向时后轮与前轮反向偏转，"
            "窄路单车道一把就能轻松掉头完成；高速行驶时后轮与前轮同向偏转，变道平滑没有侧倾甩尾感，第三排乘客完全不会出现眩晕不适。"
        ),
        technical_principles=[
            "后桥高精度无刷伺服电机驱动转向推杆与双重电子冗余锁止",
            "整车动力学协调控制器（VDC）毫秒级动态计算最佳随速偏转角",
        ],
        advantages=[
            "全系标配无需加钱选装，5.3米大车在老城区窄路掉头犹如小钢炮般灵活自如",
            "高速变道姿态平稳，彻底解决大型车后排乘员晕车难题",
        ],
        limitations=[
            "后桥机械结构高度紧凑，对底盘后轴悬架布局提出了极高工程挑战",
        ],
        representative_vehicles=["小鹏X9"],
        standard_labels=["主动后轮转向", "5.4米转弯半径", "MPV一把掉头", "告别开大船感"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "带看MPV的家庭客户试驾一把掉头与侧方停车，让客户亲身感受‘比普通B级轿车还灵活好开’的巨大反差魅力。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 15. 小鹏智能双腔空气悬架系统
    TechnologyEntity(
        id="xpeng_active_air_suspension",
        name="小鹏智能双腔空气悬架与可变阻尼系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG Intelligent Dual-Chamber Air Suspension System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="主动双腔空气弹簧与连续阻尼控制悬架",
        aliases=[
            "小鹏双腔空悬",
            "小鹏空气悬挂",
            "智能可变空气悬架",
            "小鹏双腔空气悬架",
        ],
        summary="小鹏配备的智能双腔空气悬架系统，支持车身高度最大90mm无级调节，并在单腔与双腔之间毫秒级切换弹簧刚度与阻尼软硬。",
        description=(
            "系统配备德国原装进口威巴克双气室空气弹簧与闭式高压供气系统。不仅能在迎宾模式下优雅下趴方便老人小孩上下车，"
            "在非铺装烂路自动升高底盘防止刮蹭电池；更能根据实时车速、转向角与路况，毫秒级切换主副气室刚度，抑制过弯侧倾与制动点头。"
        ),
        technical_principles=[
            "双气室电磁切断阀技术，刚度调节范围比传统单腔空气悬架提升40%以上",
            "闭式充放气回路与高频CDC可变阻尼电磁减振器联合无缝调度",
        ],
        advantages=[
            "既能提供如悬浮魔毯般抹平路面小碎震的舒适，又能在高速劈弯时给予充足支撑韧劲",
            "离地间隙随速自动升降，降低高速风阻并提升整车续航",
        ],
        limitations=[
            "高端豪华配置，通常搭载于旗舰高配车型，中低配车型多为CDC或传统螺旋弹簧",
        ],
        representative_vehicles=["小鹏G9", "小鹏X9"],
        standard_labels=["双腔空气悬架", "威巴克空簧", "迎宾下趴模式", "车身高度90mm调节"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向重视全家出行舒适度的高端客户展示双腔空悬的高低调节与软硬阻尼切换，展现越级奢华底盘质感。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 16. 小鹏 VPA 跨楼层停车场记忆泊车
    TechnologyEntity(
        id="xpeng_vpa_memory_parking",
        name="小鹏 VPA 跨楼层停车场记忆泊车系统 (Valet Parking Assist)",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG VPA Cross-Floor Memory Parking Assist",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="地下多层立体车库自主导航巡航泊车",
        aliases=[
            "vpa",
            "小鹏vpa",
            "小鹏记忆泊车",
            "小鹏跨楼层记忆泊车",
            "vpa记忆泊车",
            "地库自主泊车",
        ],
        summary="小鹏行业首创的跨楼层停车场自主记忆泊车系统，在没有GPS信号的地下车库支持最长2公里跨楼层自主巡航、避障并泊入私家车位。",
        description=(
            "车主只需带领车辆开进地库一次完成建图学习，之后每次进入车库入口即可一键开启VPA。车辆会自动跨越减速带、下坡道跨楼层、"
            "礼让会车与行人、遇到占位自动绕行，并在抵达目标车位后自动完成倒车入库，整个过程无需驾驶员干预脚踏板与方向盘。"
        ),
        technical_principles=[
            "SLAM空间建图与多传感器融合车道线/立柱语义定位算法",
            "离线地下车库高精拓扑地图存储与动态障碍物局部重规划策略",
        ],
        advantages=[
            "彻底解决大商场或地下多层车库迷路、找车位繁琐与倒车技术差的痛点",
            "即使没有手机信号与GPS卫星定位的封闭深层地库依然稳定可靠运行",
        ],
        limitations=[
            "首次使用前需要车主驾驶车辆完成一次完整的路线建图学习过程",
        ],
        representative_vehicles=["小鹏P7", "小鹏P5", "小鹏G6", "小鹏G9", "小鹏X9"],
        standard_labels=["VPA记忆泊车", "跨楼层地库巡航", "SLAM离线建图", "地下车库自主入库"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "邀请对停车有心理压力的客户在商场或展厅地库体验VPA跨楼层记忆泊车，全程放手自动驶入车位，成交杀手锏。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 17. 小鹏离车泊入与全场景代客泊车功能
    TechnologyEntity(
        id="xpeng_valet_parking",
        name="小鹏全场景代客泊车与离车泊入系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG Remote & Valet Auto Parking System",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="驾驶员下车离车无人自主泊入/泊出",
        aliases=[
            "离车泊入",
            "小鹏代客泊车",
            "小鹏自动泊车",
            "手机遥控泊车",
            "窄位离车泊入",
            "apa智能泊车",
        ],
        summary="小鹏行业公认标杆级的自动泊车体系，支持驾驶员提前下车后车辆自主完成泊入狭窄车位，以及用手机APP遥控进出极限极窄车位。",
        description=(
            "针对老旧小区或商场两边都有立柱墙壁的超窄车位（停进去后人打不开车门），车主可在车位前下车，在手机APP或车机上点击离车泊入；"
            "车辆将自动折叠后视镜、自主蠕行打方向微调并完美居中泊入车位，停好后自动熄火锁车，取车时同样支持手机遥控直线开出车位。"
        ),
        technical_principles=[
            "超声波与环视摄像头近距离微米级边缘缝隙探测与距离估算",
            "蓝牙BLE手机近场高精度定位与毫秒级防碰撞电子刹车控制",
        ],
        advantages=[
            "在左右两侧仅剩二三十厘米的极限狭窄车位也能轻松停入，避免人被困在车内爬不出来的尴尬",
            "自动泊车识别率超98%，支持无划线车位、斜列车位及机械车位",
        ],
        limitations=[
            "遥控过程中车主需站在车身数米范围内保持手机蓝牙连接不断开",
        ],
        representative_vehicles=["小鹏全系车型"],
        standard_labels=["离车泊入", "手机遥控泊车", "超窄车位泊车", "全场景APA"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "现场演示把车开到两辆紧贴的车中间，销售下车关门后车子自己稳稳停进去，给客户极强的科技震撼。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 18. 小鹏 XPILOT 智能辅助驾驶系统
    TechnologyEntity(
        id="xpeng_xpilot",
        name="小鹏 XPILOT 智能辅助驾驶系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG XPILOT Driving Assistance System",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="L2+级高稳定性ADAS驾驶辅助套件",
        aliases=[
            "xpilot",
            "小鹏xpilot",
            "xpilot3.0",
            "xpilot3.5",
            "小鹏lcc",
            "小鹏高速ngp",
        ],
        summary="小鹏奠定智能化基石的经典智能辅助驾驶系统体系，涵盖车道居中辅助（LCC）、自适应巡航（ACC）与高速导航辅助驾驶（高速NGP）。",
        description=(
            "从XPILOT 2.5到XPILOT 3.5，小鹏历经数亿公里实路验证，实现了极高的跟车舒适性与车道线居中稳定性。"
            "即便在没有城市高阶智驾硬件的车型上，标配的XPILOT也能在长途高速和城市快速路上一键开启，自动巡航、超车变道、进出匝道，大幅减轻驾驶疲劳。"
        ),
        technical_principles=[
            "毫米波雷达+超声波+高灵敏前视摄像头多源传感器硬件融合",
            "纵横向控制解耦算法与舒适制动加减速平滑插值模型",
        ],
        advantages=[
            "高速公路行驶百公里接管次数极低，长途自驾如释重负",
            "弯道居中居中率极高，经过大曲率弯道不压线不画龙",
        ],
        limitations=[
            "主要服务于高速与快速路封闭场景，在复杂城市开放道路红绿灯路段功能受限",
        ],
        representative_vehicles=["小鹏P7", "小鹏P5", "小鹏G3i", "MONA M03"],
        standard_labels=["XPILOT", "高速NGP", "车道居中LCC", "ACC自适应巡航"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向长途通勤频繁的客户说明标配XPILOT的高速NGP功能，上高速后基本只需手扶方向盘，长途开几百公里不腰酸腿疼。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 19. 小鹏汇天分体式飞行汽车“陆地航母”体系
    TechnologyEntity(
        id="xpeng_flying_car_aeroht",
        name="小鹏汇天分体式飞行汽车与“陆地航母”系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG AEROHT Modular Flying Car & Land Aircraft Carrier",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="陆空一体化模块化飞行汽车工程",
        aliases=[
            "小鹏汇天",
            "飞行汽车",
            "小鹏飞行汽车",
            "陆地航母",
            "aeroht",
            "分体式飞行汽车",
            "evtol",
        ],
        summary="小鹏旗下汇天自主研发的全球首款分体式飞行汽车，分为陆行母舰与双人eVTOL飞行体两部分，开辟了低空经济与未来立体交通先河。",
        description=(
            "陆行母舰采用6x6全轮驱动增程越野车身，内部后备箱通过全自动机械手臂可将双人纯电垂直起降（eVTOL）飞行器收纳并充能。"
            "到达风景优美营地或空旷场地后，飞行体自动滑出展开旋翼，支持单杆一键起飞、空中自动航线规划及全向避障降落，实现说飞就飞的梦想。"
        ),
        technical_principles=[
            "全复合碳纤维轻量化机身与多旋翼冗余安全气动布局（双旋翼失效仍可安全着陆）",
            "大功率超快车载全自动对中充电坞站与一键全自动机构机械展开机构",
        ],
        advantages=[
            "彻底破解传统飞行汽车‘地面开不走、天上飞不动’的尴尬妥协难题",
            "低空经济领军标杆，极大地拔高了小鹏汽车探索未来的科技创新形象",
        ],
        limitations=[
            "需要国家低空空域适航认证与指定空域飞行报备，消费级普及需逐步展开",
        ],
        representative_vehicles=["小鹏汇天分体式飞行汽车“陆地航母”"],
        standard_labels=["小鹏汇天", "分体式飞行汽车", "陆地航母", "eVTOL垂直起降", "低空经济先锋"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向客户介绍小鹏在飞行汽车领域的全球领先探索成果，展示小鹏不仅是车企、更是未来立体出行科技先锋的宏伟格局。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 20. 小鹏“铁臂”与 Iron 人形机器人具身智能体系
    TechnologyEntity(
        id="xpeng_iron_robot",
        name="小鹏“铁臂”与 Iron 人形机器人具身智能架构",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG Iron Humanoid Robot & Embodied AI Architecture",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="车端大模型与机器人具身智能协同系统",
        aliases=[
            "小鹏机器人",
            "iron人形机器人",
            "小鹏iron",
            "具身智能",
            "小鹏铁臂",
            "图灵芯片机器人",
        ],
        summary="小鹏自研的高仿真人形机器人与工业具身智能系统，搭载自研图灵AI芯片与天玑大模型内核，实现从智能汽车到人形机器人的算力与算法复用。",
        description=(
            "Iron人形机器人身高178cm，拥有60多个活动自由度与仿生手高精度末端执行器。其核心大脑直接复用小鹏汽车自动驾驶端到端神经网络与大语言模型，"
            "能够与汽车装配工厂无缝协同工作，并在智能展厅接待客户，展示了小鹏全栈自研AI算法在具身物理世界的终极进化形态。"
        ),
        technical_principles=[
            "自研高密度力矩伺服关节与毫米波/激光视觉融合末端自适应规控",
            "小鹏图灵芯片搭载端到端多模态大模型在物理空间的空间动作映射生成",
        ],
        advantages=[
            "车厂智驾算法与机器人具身智能无缝共享训练数据与超算基础设施",
            "在智能制造与智慧零售展厅提供前所未有的科技交互体验",
        ],
        limitations=[
            "人形机器人量产制造与复杂工业场景精细动作长期可靠性处于落地爬坡期",
        ],
        representative_vehicles=["小鹏智慧工厂制造产线", "小鹏旗舰品牌中心"],
        standard_labels=["Iron人形机器人", "具身智能", "图灵芯片赋能", "高自由度仿生关节"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向追求未来尖端科技的年轻精英强调：小鹏的AI大模型不仅能开车，还能赋能人形机器人，是全链条自主研发的真正硬科技公司。",
        ],
        maturity=TechMaturity.CONCEPT,
    ),

    # 21. 小鹏 AI 天玑端到端大模型
    TechnologyEntity(
        id="xpeng_ai_dimensity",
        name="小鹏 AI 天玑大模型端到端协同架构",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG AI Dimensity End-to-End Foundation Model",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="座舱认知与智驾行为联合大模型",
        aliases=[
            "ai天玑大模型",
            "小鹏端到端大模型",
            "天玑大模型",
            "小鹏大模型",
            "多模态大模型架构",
        ],
        summary="业内首家打通智驾与座舱两端算法底层壁垒的综合大模型架构，让汽车不仅具备老司机级的驾驶手艺，更拥有通晓万物的博学感知大脑。",
        description=(
            "AI天玑大模型使车辆摆脱了传统智驾与智能座舱‘两张皮’的割裂状态。当车主向语音助手发出‘前面有堵车，帮我绕行并找一家评分最高的快餐厅’时，"
            "大模型能够端到端解析语义，直接联动实时导航大模型规划避堵路线，并联动智驾系统自动开启避障通行，实现真正的全智能闭环。"
        ),
        technical_principles=[
            "多模态知识图谱与车端智驾行为联合嵌入向量空间对齐",
            "端云联合强化学习闭环与自动化标注大模型流水线",
        ],
        advantages=[
            "人车交互更聪明自然，彻底告别必须逐条下达死板指令的繁琐操作",
            "智驾算法版本每两天进化一次，迭代速度比传统手写规则快30倍",
        ],
        limitations=[
            "复杂多重语义复合指令对网络时延与端侧神经推理芯片性能要求极高",
        ],
        representative_vehicles=["小鹏P7+", "小鹏X9", "小鹏G6", "小鹏G9"],
        standard_labels=["AI天玑大模型", "端到端协同", "高频自迭代进化", "座舱智驾全融合"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "强调小鹏汽车拥有行业公认迭代最快、最聪明的端到端AI大模型体系，车子买回家后越开越聪明。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 22. 小鹏 X-opera 音乐厅级立体音响系统
    TechnologyEntity(
        id="xpeng_sound_system",
        name="小鹏 X-opera 音乐厅级车载声学系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG X-opera Acoustic Sound System",
        category=TechCategory.COCKPIT_OS,
        subcategory="多通道全景声沉浸式音响系统",
        aliases=[
            "x-opera",
            "小鹏音响",
            "xopera",
            "小鹏全景声",
            "20扬声器音响",
            "音乐座舱",
        ],
        summary="小鹏全栈自研的豪华车载音响系统，配备多达20+高品质扬声器与杜比全景声解码，打造声临其境的移动金色大厅音乐座舱。",
        description=(
            "X-opera系统包含主驾专享头枕扬声器、独立重低音单元及天空声道。主驾导航播报仅通过头枕发声，完全不干扰后排家人听音乐或睡觉休息；"
            "经过国际知名声学大师专属调音，拥有超强动态还原范围与细腻人声质感，支持多种大师预设音效与空间立体声混音增强。"
        ),
        technical_principles=[
            "自研高动态范围DSP功放芯片与全主动分频调音拓扑",
            "双头枕扬声器声场独立相消算法，实现主驾私密通话零漏音",
        ],
        advantages=[
            "主驾听导航/接打电话与乘员听音乐互不干扰，家庭出行极度和谐舒适",
            "全景声空间感极佳，高音清澈甜美、低音澎湃震撼不轰头",
        ],
        limitations=[
            "发挥极致声效需要搭配高品质无损音源或杜比全景声专属曲库",
        ],
        representative_vehicles=["小鹏G9", "小鹏X9", "小鹏P7+", "小鹏G6"],
        standard_labels=["X-opera音响", "杜比全景声", "主驾私享头枕扬声器", "移动音乐厅"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "在展车内播放无损人声与交响乐片段，让客户感受主驾头枕私享声音隔离与全车沉浸声场的震撼包围感。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 23. 小鹏太空零重力宇航座椅
    TechnologyEntity(
        id="xpeng_zero_gravity_seat",
        name="小鹏太空零重力宇航舒享座椅系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG Zero-Gravity Aviation Seat System",
        category=TechCategory.COCKPIT_OS,
        subcategory="人体工程学零重力头等舱座椅",
        aliases=[
            "小鹏零重力座椅",
            "小鹏太空零重力座椅",
            "宇航座椅",
            "二排零重力",
            "一键零重力姿态",
        ],
        summary="模拟宇航员在太空失重姿态的人体工学豪华座椅，一键实现躯干与大腿夹角128度黄金舒适角度，极致释放腰椎与下肢受力压力。",
        description=(
            "座椅采用超柔抗疲劳慢回弹海绵与高档Nappa真皮包覆，配备一体式超长电动腿托、腰托四向调节、石墨烯快速加热与10点式背部深层气囊按摩。"
            "当开启零重力模式时，坐垫整体向后上方抬升倾斜，使心脏与膝盖处于同一水平线，让乘员在行驶途中体验如漂浮于云端般的无压放松感。"
        ),
        technical_principles=[
            "NASA宇航级中立姿态（Neutral Body Posture）多连杆无级连动调节机构",
            "高张力静音传动齿轮箱与压力分布矩阵式感应记忆调节",
        ],
        advantages=[
            "长途高速乘坐几个小时腰不酸背不疼，比家里顶级按摩椅还要舒适",
            "即使在颠簸非铺装路面行驶，零重力受力状态下身体受到的震动冲击也能削减超50%",
        ],
        limitations=[
            "开启零重力完全后仰姿态时，会适度压缩后方第三排的纵向腿部空间",
        ],
        representative_vehicles=["小鹏X9", "小鹏G9"],
        standard_labels=["零重力座椅", "NASA中立姿态", "一体式电动腿托", "10点气囊按摩"],
        equivalence_group_id=None,
        sales_talking_points=[
            "让客户坐进第二排一键开启零重力姿态并打开气囊按摩，5分钟的极致享受足以打动对家庭舒适度要求极高的客户。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 24. 小鹏 21.4英寸车载吸顶娱乐大屏
    TechnologyEntity(
        id="xpeng_rear_entertainment_screen",
        name="小鹏 21.4英寸生态级车载后排吸顶娱乐大屏",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG 21.4-Inch Rear Ceiling Entertainment Display",
        category=TechCategory.COCKPIT_OS,
        subcategory="高规格车载多媒体影音显示系统",
        aliases=[
            "21.4寸大屏",
            "小鹏吸顶屏",
            "后排娱乐屏",
            "吸顶电视",
            "小鹏后排大屏",
            "电动吸顶大屏",
        ],
        summary="同级尺寸极具震撼力的21.4英寸电动翻折吸顶大屏，支持0-75度无级角度电动调节与莱茵低蓝光护眼认证，后排全家人的移动巨幕影院。",
        description=(
            "在小鹏X9中，这块21.4英寸巨幕完美融入车顶环形顶棚造型。不仅能通过遥控器或小P语音电动开启关闭，"
            "还支持无线投屏、多应用分屏、儿童动画专属护眼模式，结合X-opera音响系统，让长途旅行中后排老人小孩彻底摆脱无聊，乐在其中。"
        ),
        technical_principles=[
            "低功耗广色域全高清IPS防眩光面板与无级静音步进电机减速机构",
            "车规级超低温耐受与极端碰撞防飞溅安全强化玻璃工艺",
        ],
        advantages=[
            "尺寸同级领先，视野开阔震撼，即使坐在第三排也能获得极佳观影效果",
            "支持防晕车画质调节技术，行驶颠簸观影不易产生恶心眩晕感",
        ],
        limitations=[
            "完全下翻展开时在一定程度上遮挡主驾内后视镜的中央视野（通常搭配流媒体后视镜解决）",
        ],
        representative_vehicles=["小鹏X9"],
        standard_labels=["21.4英寸吸顶屏", "电动无级调节", "莱茵低蓝光认证", "后排移动影院"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "展示语音一键开启21.4寸巨幕并播放4K动画片，直接击中带娃家庭用户的核心痛点。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 25. 小鹏 X9 第三排电动一键隐藏式魔术折叠座椅
    TechnologyEntity(
        id="xpeng_x9_stowable_seats",
        name="小鹏 X9 第三排电动一键隐藏收纳魔术座椅系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG X9 Third-Row Electric Stow-Away Magic Seats",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="下沉式纯平空间机构工程",
        aliases=[
            "x9魔术座椅",
            "第三排电动折叠",
            "隐藏式收纳座椅",
            "三排一键翻折",
            "纯平后备箱",
            "小鹏魔术折叠",
        ],
        summary="小鹏X9独创的第三排电动魔术折叠技术，一键自动收折并完全沉入后备箱凹槽，瞬间将大7座MPV变身容积达2554升的超大纯平大平层SUV。",
        description=(
            "传统MPV第三排座椅大多只能向前翻折靠背或挂在车侧，既占用后备箱高度又遮挡侧窗视线。小鹏攻克了后轴结构与后轮转向布置的极限空间挑战，"
            "第三排座椅可完全电动下沉翻转，与后备箱底板融为一体形成绝对纯平空间，可轻松放入多辆山地自行车、高尔夫球包或露营充气大床。"
        ),
        technical_principles=[
            "复杂多连杆空间轨迹反转电动铰链与轻量化高刚度骨架",
            "底盘后下车身深坑下沉冲压与后轴后轮转向紧凑集成包络设计",
        ],
        advantages=[
            "7座状态下后备箱下沉空间依然能装下7个大行李箱；4座状态下瞬间拥有大平层超大空间",
            "全电动操作，无需手动费力搬动沉重座椅，老人女性也能优雅单指操作",
        ],
        limitations=[
            "第三排下方为座椅收纳凹槽，取消了传统备胎布置空间",
        ],
        representative_vehicles=["小鹏X9"],
        standard_labels=["魔术折叠座椅", "第三排完全沉入纯平", "后备箱2554L容积", "全电动一键翻转"],
        equivalence_group_id=None,
        sales_talking_points=[
            "现场演示长按按钮，第三排座椅自动反转沉入地板变身大平层的神奇过程，让客户直呼空间魔术师。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 26. 小鹏 X-EEA 集中式电子电气架构
    TechnologyEntity(
        id="xpeng_x_eea_architecture",
        name="小鹏 X-EEA 集中式电子电气架构",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG X-EEA Centralized Electrical & Electronic Architecture",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="千兆以太网中央计算与区域控制架构",
        aliases=[
            "x-eea",
            "x-eea3.0",
            "xeea",
            "小鹏电子电气架构",
            "中央超算架构",
            "区域控制器架构",
        ],
        summary="国内领先的中央超算+区域控制电子电气架构，以千兆以太网为主干总线，实现软硬件完全解耦与全车控制器极速无感OTA升级。",
        description=(
            "打破了传统汽车ECU数量庞大、线束纷繁复杂的陈旧构型。将整车数十个分散控制器高度集中到中央超算与左右区域控制器中；"
            "不仅整车线束长度缩短了数百米、大幅减轻车重，而且支持整车固件30分钟无感静默升级，甚至在升级过程中车辆依然能正常开门使用。"
        ),
        technical_principles=[
            "千兆以太网高速通信骨干网与高可靠CAN-FD双环网拓扑冗余",
            "自研SOA面向服务软件中间件，全车硬件传感器与执行器全部API服务化",
        ],
        advantages=[
            "OTA升级速度极快且极少发生死机卡顿，常用常新永不过时",
            "整车各域数据互通零壁垒，软件工程师能以极低成本开发各种跨域联动新功能",
        ],
        limitations=[
            "底层软件中间件架构极其复杂，要求车企具备极强的全栈代码自研实力",
        ],
        representative_vehicles=["小鹏G6", "小鹏G9", "小鹏X9", "小鹏P7+"],
        standard_labels=["X-EEA架构", "中央超算", "千兆以太网主干", "整车静默OTA"],
        equivalence_group_id=None,
        sales_talking_points=[
            "告诉注重长期用车体验的理性买家：小鹏拥有全国最顶尖的电子电气架构，整车OTA像智能手机更新App一样轻快无感。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 27. 小鹏全集成高效宽温域热泵空调系统
    TechnologyEntity(
        id="xpeng_high_voltage_heat_pump",
        name="小鹏全集成高效宽温域热泵空调系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG Integrated Wide-Temperature-Range Heat Pump",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="多热源高效热管理集成控制系统",
        aliases=[
            "小鹏热泵",
            "宽温域热泵",
            "热泵空调",
            "小鹏热管理",
            "低温热泵系统",
            "冬季续航热泵",
        ],
        summary="支持低至零下30℃严寒工况的高效热泵系统，深度统筹电驱废热、电池热量与座舱暖风，将冬季低温续航达成率提升超15%。",
        description=(
            "针对纯电动汽车在北方寒冷冬季开暖风‘电量崩塌式下降’的顽疾，小鹏自研了全集成多热源热泵系统。"
            "通过复杂的集成阀岛与电子膨胀阀，在严寒环境下不仅能从零下30度的室外空气中搬运微弱热量，还能将电机运转的废热、甚至乘客散发的热量收集用于加热电池与吹暖风，大幅节省PTC电热丝的剧烈电耗。"
        ),
        technical_principles=[
            "宽温域双转子电动压缩机与超低流动阻力八通集成热管理阀岛",
            "电驱余热主动回收与电池热平衡自适应相变微循环控制",
        ],
        advantages=[
            "北方冬季开暖风再也不用扣扣搜搜，百公里能耗依然维持在极佳水准",
            "夏季制冷降温极速，从酷暑暴晒到体感凉爽仅需2-3分钟",
        ],
        limitations=[
            "高集成度热泵管路在极低温初期启动阶段压缩机运转声音略有可察觉的高频声",
        ],
        representative_vehicles=["小鹏G6", "小鹏G9", "小鹏X9", "小鹏P7+"],
        standard_labels=["宽温域热泵", "零下30度耐寒", "冬季续航提升15%", "电驱余热回收"],
        equivalence_group_id=None,
        sales_talking_points=[
            "针对北方地区或担心冬天电车续航腰斩的客户，用宽温域热泵技术消除北方车主的冬季里程焦虑。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 28. 小鹏自研高性能超高效三合一 SiC 碳化硅高压电驱总成
    TechnologyEntity(
        id="xpeng_silicon_carbide_motor",
        name="小鹏自研超高效三合一 SiC 碳化硅电驱动总成",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG High-Performance In-House 3-in-1 SiC Electric Drive",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="高转速碳化硅集成电驱总成",
        aliases=[
            "小鹏电机",
            "小鹏碳化硅电机",
            "小鹏电驱总成",
            "800v碳化硅电机",
            "三合一高压电驱",
        ],
        summary="小鹏全栈自研的高性能三合一高压电驱总成，最高转速突破20000rpm，集成碳化硅功率模块与扁线定子绕组，功率密度高达行业前沿的2.5kW/kg。",
        description=(
            "将电机、逆变电控与单级减速器深度融合为超小体积总成。定子采用8层扁线Hairpin工艺，转子采用高效转子直冷油冷技术，"
            "在保障瞬间爆发数十千瓦充沛扭矩（带来3秒级零百加速快感）的同时，在日常市区中低速拥堵路况依然拥有98%以上的超高能量转化效率。"
        ),
        technical_principles=[
            "8层Hairpin扁线定子铜线排布与离心力内部油道直接喷淋冷却",
            "车规级SiC碳化硅晶圆功率模块封装与自研微秒级PWM高频调制",
        ],
        advantages=[
            "体积极其紧凑轻量，为乘员舱腾出更多空间且电耗极低",
            "高转速工况下NVH啸叫声极微弱，车内加速平顺安静如同高铁",
        ],
        limitations=[
            "超高转速对轴承动平衡公差与电磁抑制提出了极高的精密制造要求",
        ],
        representative_vehicles=["小鹏G6", "小鹏G9", "小鹏X9"],
        standard_labels=["自研碳化硅电驱", "最高转速20000rpm", "8层扁线Hairpin", "超高功率密度"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "带客户体验急加速推背感，同时引导客户注意几乎听不到任何刺耳的电机高频电流啸叫，展现深厚电驱功底。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 29. 小鹏 360度电池包全维度安全防护架构
    TechnologyEntity(
        id="xpeng_battery_safety_system",
        name="小鹏 360度全维度高安全电池防护体系",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG 360-Degree Comprehensive Battery Safety Architecture",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="多层次物理防护与热失控主动防御",
        aliases=[
            "小鹏电池安全",
            "十宫格吸能结构",
            "小鹏电池防爆",
            "电池全维度防护",
            "小鹏无自燃电池",
        ],
        summary="小鹏严密构建的电池物理防撞与热失控隔离体系，具备十宫格侧边吸能门槛梁与千摄氏度无明火热阻隔舱，保障电池全生命周期零自燃。",
        description=(
            "在物理防撞层面，车身侧边门槛梁采用十宫格航空级多腔铝合金挤压铝结构，能承受高达80吨侧碰冲击而不挤压电芯；"
            "在热安全层面，每个电芯之间均包裹航天级气凝胶隔热层，配合自研毫秒级高压切断熔断装置与IP68级长达48小时深水防浸泡能力，筑牢安全底线。"
        ),
        technical_principles=[
            "十宫格蜂窝多级溃缩吸能门槛梁物理拓扑拓扑学",
            "电芯独立单体定向防爆泄压阀与云端毫秒级微短路阻抗预警算法",
        ],
        advantages=[
            "通过了远超国标的极其严苛针刺、挤压、高温暴晒及底部球击试验",
            "侧面遭受严重撞击时能够迅速吸纳撞击动能，保证乘员与电芯绝对完好",
        ],
        limitations=[
            "多层防撞梁与气凝胶防火阻燃包覆使电池包周边结构用料相对扎实偏厚",
        ],
        representative_vehicles=["小鹏G6", "小鹏G9", "小鹏X9", "小鹏P7+"],
        standard_labels=["360度电池安全", "十宫格吸能门槛梁", "航天级气凝胶隔热", "IP68级深水防泡"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向对电动车电池安全性有疑虑的家庭用户展示十宫格侧边防撞梁切面模型，证明小鹏电池安全用料货真价实。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 30. 小鹏 AI 智能底盘与魔毯路况感知预瞄系统
    TechnologyEntity(
        id="xpeng_ai_chassis",
        name="小鹏 AI 智能底盘与魔毯路况感知预瞄系统",
        brand="小鹏 (XPENG)",
        brand_key="xpeng",
        english_name="XPENG AI Intelligent Magic Carpet Chassis System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="视觉预瞄与空悬阻尼毫秒级自适应控制",
        aliases=[
            "小鹏魔毯底盘",
            "ai智能底盘",
            "小鹏路面预瞄",
            "小鹏魔毯",
            "小鹏智能魔毯",
            "小鹏底盘预瞄",
        ],
        summary="小鹏结合智驾摄像头视觉路况扫描与智能悬架的协同控制系统，提前15米识别前方减速带与坑洼路面，主动软化阻尼实现如履平地。",
        description=(
            "传统底盘只能在车轮压上坑洼颠簸后被动吸收震动。小鹏AI底盘通过前向高清摄像头以每秒数十帧的速率扫描前方路面高程起伏，"
            "在车轮压上减速带前微秒级主动调整双腔空悬高度与CDC可变阻尼减振器硬度，车身起伏晃动降低超60%，乘车舒适度媲美百万级豪车魔毯底盘。"
        ),
        technical_principles=[
            "深度学习高精度前向立体视觉路面三维几何重建网络",
            "底盘预见性前馈控制器（Feed-Forward Control）与垂向动力学快速协同解算",
        ],
        advantages=[
            "经过连续减速带或恶劣破损路面时车身如履平地，后排乘客看手机电脑不晕车",
            "结合智驾导航大数据，自动记忆常走路线的隐形坑洼并智能提前预警应对",
        ],
        limitations=[
            "暴雪覆盖完全遮挡路面纹理或暴雨极端逆光条件下视觉前视识别精度会有所减弱",
        ],
        representative_vehicles=["小鹏G9", "小鹏X9"],
        standard_labels=["AI智能底盘", "路面视觉预瞄", "魔毯悬架", "减速带主动滤震"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "带客户试驾时故意碾压减速带或井盖，体验AI智能底盘‘提前预知、轻柔化解’的高级魔毯滑行质感。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),
]

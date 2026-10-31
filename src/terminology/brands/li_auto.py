"""
Li Auto Proprietary Automotive Technology Registry (src/terminology/brands/li_auto.py).
Contains 30 comprehensive proprietary technologies for Li Auto (Ideal).
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

LI_AUTO_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 理想魔毯空气悬架 2.0 系统 (Original)
    TechnologyEntity(
        id="ideal_magic_carpet",
        name="理想魔毯空气悬架 2.0 系统",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Magic Carpet Air Suspension 2.0",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="家庭舒适型空气悬架与自研域控制",
        aliases=[
            "魔毯",
            "魔毯空气悬架",
            "理想魔毯",
            "magic carpet",
            "理想魔毯悬架",
            "理想双腔空悬",
            "理想双腔空气悬架",
            "理想悬架",
        ],
        summary="专为中国家庭打造的舒适型底盘系统，集成双腔/单腔空气弹簧、CDC连续可调阻尼与自研域控制器，提供如魔毯般平稳柔和的滤震和防晕车体验。",
        description=(
            "理想魔毯空气悬架系统由理想全栈自研XCU中央域控制器驱动，针对中国家庭高频出行的城市减速带、碎石路与高速起伏进行深度工程标定。"
            "提供舒适魔毯与运动魔毯双模式，可主动调节车身离地高度（最大调节幅度数十毫米），停车时具备便捷上下车自动迎宾降车身功能。"
        ),
        technical_principles=[
            "自研全铝前双叉臂+后五连杆悬架架构，空气弹簧+CDC减振器毫秒级阻尼调节",
            "全栈自研整车运动姿态控制算法，对多成员负载进行自适应水平高度校平",
        ],
        advantages=[
            "滤震风格极其偏向中国家庭喜爱的舒适大船感，后排老人孩子不易晕车",
            "上下车与装卸行李时车身自动下降，极富人性化关怀仪式感",
            "全系空气弹簧享有超长原厂质保保障",
        ],
        limitations=[
            "偏重舒适舒适性调校，在极致激烈的赛道驾驶中极限侧倾抑制略逊于硬派性能悬架",
        ],
        sub_variants={
            "魔毯单腔版": "搭载于L7/L8部分版本，单腔空簧+CDC阻尼调节",
            "魔毯双腔版": "搭载于L9与MEGA，双腔空气弹簧支持刚度多挡瞬态切换，支撑性更上一层楼",
        },
        representative_vehicles=["理想L9", "理想L8", "理想L7", "理想MEGA"],
        standard_labels=["智能空气悬架", "双腔空簧", "CDC连续阻尼可调", "家庭舒适魔毯底盘", "自动迎宾升降"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "主打家庭成员乘坐舒适：现场邀请客户带家人体验二排过坎体验，感受“如履平地”的轻柔回弹；",
            "对比传统BBA豪车需花费数万元选装空气悬架，强调理想旗舰全系标配的高价值感。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 2. 理想增程电动系统 (1.5T四缸增程器) (Original)
    TechnologyEntity(
        id="ideal_range_extender",
        name="理想增程电动系统 (1.5T四缸增程器)",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Range-Extended Electric Powertrain",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="增程式纯电驱动动力总成",
        aliases=[
            "理想增程",
            "理想增程式",
            "理想增程系统",
            "理想增程电动",
            "1.5t增程器",
            "理想增程器",
            "城市用电长途发电",
        ],
        summary="“城市用电、长途发电”的高效增程系统，采用高热效率1.5T四缸增程器搭配前后大功率双电机智能四驱，实现超1300公里超长综合续航。",
        description=(
            "理想汽车坚持的增程动力架构中，增程器（发动机）从始至终不参与机械直驱车轮，仅作为高效发电机组为电池与驱动电机供电。"
            "车辆在任何工况下都保留100%纯电动的平顺加速响应和无顿挫静谧感，彻底消除节假日高速服务区抢充电桩的里程焦虑。"
        ),
        technical_principles=[
            "1.5T高热效率米勒循环四缸增程器，静音与震动经多级吸音降噪深度优化",
            "双电机全时智能四驱，前后扭矩自适应分配，保留纯电直接驱动感",
        ],
        advantages=[
            "城市上下班完全使用家充纯电，每公里成本仅需几分钱到一毛钱",
            "长途出行随时进加油站3分钟加满，综合续航1300-1400km，无任何里程焦虑",
            "四缸增程器运转极其安静，告别早期三缸增程抖动噪声",
        ],
        limitations=[
            "高速亏电巡航油耗略高于同级别重度混动车（如DM-i），略依赖规律充电以享受最佳经济性",
        ],
        sub_variants={},
        representative_vehicles=["理想L6", "理想L7", "理想L8", "理想L9"],
        standard_labels=["增程式混合动力", "四缸增程器", "前后双电机四驱", "超1300km综合续航", "无充电焦虑"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "直击多孩家庭长途返乡痛点：冬天开暖风跑高速不用算计续航，随时加油说走就走；日常工作日又能当纯电车开省钱。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 3. 理想 5C 超充麒麟电池 (Original)
    TechnologyEntity(
        id="ideal_5c_qilin",
        name="理想 5C 超充麒麟电池",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto 5C Ultra-Fast Charging Qilin Battery",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="800V高倍率超快充锂电池",
        aliases=[
            "5c超充",
            "5c麒麟电池",
            "理想5c",
            "5c充电",
            "充电12分钟500公里",
            "理想麒麟电池",
        ],
        summary="理想与宁德时代联合研发的800V全栈高压5C超充电池，具备行业顶尖的5C充电倍率，实现充电12分钟续航增加500公里。",
        description=(
            "理想5C超充电池搭载于理想纯电车型（MEGA），峰值充电功率突破520kW，充电电流超过700A。通过超高导电解液、低阻抗隔膜与立体双大面水冷，"
            "将高倍率充电产生的巨大热量瞬间带走，在极宽SOC区间内维持峰值充电平台。"
        ),
        technical_principles=[
            "联合定制宁德时代麒麟架构，大面水冷面积相比传统底面水冷增大5倍",
            "全栈800V高压电气平台与自建5C超充桩群深度协同",
        ],
        advantages=[
            "充电速度达到全球量产乘用车顶峰，10%-80%充电仅需约10-12分钟",
            "冬季极寒环境下依靠超强热管理依然具备极高充电倍率",
        ],
        limitations=[
            "目前仅搭载于理想旗舰级高端纯电车型，且需匹配理想自建5C超充桩才能激活极致充电速度",
        ],
        sub_variants={},
        representative_vehicles=["理想MEGA"],
        standard_labels=["5C超充电池", "800V高压麒麟电池", "充电12分钟500km", "520kW峰值快充"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向考虑纯电MPV但担心补能效率的客户展示：上个洗手间的功夫车已充至80%，完全比肩燃油加油效率。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 4. 理想 AD Max 智能驾驶系统 (双 Orin-X + 激光雷达)
    TechnologyEntity(
        id="ideal_ad_max",
        name="理想 AD Max 高阶智能驾驶系统",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto AD Max Advanced Autonomous Driving System",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="双芯片高算力端到端全场景领航智驾",
        aliases=[
            "ad max",
            "admax",
            "理想ad max",
            "理想智驾",
            "端到端+vlm",
            "全国无图noa",
            "车位到车位智驾",
        ],
        summary="配备双英伟达Orin-X芯片（508TOPS）与禾赛激光雷达，采用端到端E2E+VLM视觉语言大模型双系统，实现全国都能开的城市NOA与车位到车位。",
        description=(
            "理想AD Max引入业内领先的‘端到端+VLM（视觉语言大模型）’双系统架构。端到端快系统负责毫秒级类人反应，"
            "VLM慢系统负责理解潮汐车道、施工警示牌、特殊交通手势与导航路况逻辑，支持从车位启动直接贯通地库泊车位全场景自主导航。"
        ),
        technical_principles=[
            "端到端神经网络模型实时生成行驶轨迹",
            "车载VLM视觉语言大模型理解物理世界复杂文字与语义标志",
        ],
        advantages=[
            "全国城市无图NOA开城全覆盖，道路适应性极强",
            "变道超车极其果断，遇到坑洼施工标志牌会像人类一样提前减速看懂文字",
        ],
        limitations=[
            "暴雪大雾视线不良等极端恶劣天气系统仍要求人工主动接管",
        ],
        sub_variants={
            "AD Pro": "单地平线征程5芯片（128TOPS），纯视觉方案，支持高速NOA",
            "AD Max": "双Orin-X（508TOPS）+激光雷达，支持全场景城市NOA及车位到车位",
        },
        representative_vehicles=["理想L9全系", "理想L8 Max/Ultra", "理想L7 Max/Ultra", "理想MEGA"],
        standard_labels=["AD Max", "端到端+VLM", "双Orin-X", "激光雷达", "车位到车位", "城市NOA"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "展示实测无图NOA视频：‘不仅能自己看懂施工警示牌上的文字，连复杂的环岛、掉头和修路改道都能一把顺滑通过，老司机感十足！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 5. 理想 Mind GPT 车载认知大模型与‘理想同学’
    TechnologyEntity(
        id="ideal_mind_gpt",
        name="理想 Mind GPT 车载认知大模型与理想同学",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Mind GPT Multi-Modal Cognitive LLM",
        category=TechCategory.COCKPIT_OS,
        subcategory="车载全自研多模态认知大模型与拟人语音",
        aliases=[
            "mind gpt",
            "mindgpt",
            "理想同学",
            "自研大模型",
            "车载大模型",
            "多模态大模型",
        ],
        summary="理想自研全场景多模态认知大模型Mind GPT，赋予‘理想同学’超强百科问答、孩子辅导作业、百科看图答疑及全车语音交互能力。",
        description=(
            "Mind GPT拥有1.3万亿Token高质量基底训练，深度融入全车座舱交互。副驾孩子随口问‘恐龙为什么灭绝’、‘窗外的植物是什么’，"
            "理想同学结合摄像头视觉即问即答；具备声纹记忆，精准识别车内每个家庭成员并提供千人千面的贴心服务。"
        ),
        technical_principles=[
            "自研大模型轻量化车端推理加速引擎与云端千亿MoE混合架构",
            "全车六音区高动态麦克风阵列与声纹特征分离技术",
        ],
        advantages=[
            "全车六音区完全独立免唤醒，老人孩子都能轻松唤起",
            "带娃长途路上的最强大脑，讲故事、对古诗、答疑解惑应有尽有",
        ],
        limitations=[
            "涉及复杂长文大模型生成时在完全无信号深山弱网需等待",
        ],
        sub_variants={},
        representative_vehicles=["理想L系列全系", "理想MEGA"],
        standard_labels=["Mind GPT", "理想同学", "车载认知大模型", "带娃神器", "六音区免唤醒"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "在展厅让客户的孩子跟理想同学说话：‘理想同学不仅是车机，还是孩子的贴身家教和百科老师，一路上再也不吵着闹着要看手机了！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 6. 理想 SS Max 智能空间五屏三维交互系统
    TechnologyEntity(
        id="ideal_ss_intelligent_space",
        name="理想 SS Max 智能空间五屏三维交互系统",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto SS Max 5-Screen 3D Interactive Smart Space",
        category=TechCategory.COCKPIT_OS,
        subcategory="前后排五屏联动与三维空间手势微动手势交互",
        aliases=[
            "ss max",
            "五屏联动",
            "理想智能空间",
            "后排吸顶屏",
            "三维手势交互",
            "安全驾驶交互屏",
        ],
        summary="由HUD、方向盘安全交互屏、中控大屏、副驾娱乐屏及后排OLED电动吸顶屏组成的五屏联动系统，支持隔空手势控屏交互。",
        description=(
            "理想汽车首创将传统仪表盘精简为方向盘上方触控小屏+超大画幅HUD，中控与副驾配备双15.7英寸3K三星OLED大屏，"
            "后排配备15.7英寸电动折叠OLED吸顶娱乐屏。车顶配备TOF深度传感器，后排乘客伸出手掌捏合即可隔空选中并拖拽播放电影。"
        ),
        technical_principles=[
            "双高通骁龙8295P车规旗舰算力芯片架构",
            "TOF 3D飞行时间深度传感器与骨骼关节点手势追踪算法",
        ],
        advantages=[
            "全车每个座位都有专属顶级屏幕，长途旅行全家其乐融融",
            "后排老人孩子不用起身探头，靠在椅背上隔空摆摆手就能换电影",
        ],
        limitations=[
            "后排吸顶屏展开时需适应通过流媒体后视镜观察后车",
        ],
        sub_variants={
            "SS Pro": "单颗8295芯片，前排双联屏+HUD（无后排吸顶屏）",
            "SS Max": "双8295芯片，前排双联屏+后排OLED吸顶屏+TOF手势",
        },
        representative_vehicles=["理想L9全系", "理想L8 Max/Ultra", "理想L7 Ultra", "理想MEGA"],
        standard_labels=["SS Max", "五屏交互", "3K OLED屏", "隔空手势控车", "后排吸顶屏"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "让全家人坐进车里：‘爸爸开车看HUD，妈妈在副驾刷热播剧，后面两个孩子在吸顶大屏上看动画片，全家人都开开心心！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 7. 理想 MEGA 水滴造型 0.215Cd 全球超低风阻设计
    TechnologyEntity(
        id="ideal_mega_aerodynamics",
        name="理想 MEGA 水滴形极低风阻空气动力学车身",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto MEGA Water-Drop 0.215Cd Aerodynamics Design",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="高铁级水滴流线大型纯电MPV气动外形",
        aliases=[
            "mega造型",
            "水滴车头",
            "0.215cd风阻",
            "理想mega设计",
            "高铁造型",
            "mpv低风阻",
        ],
        summary="颠覆传统传统MPV方盒子造型，采用高铁列车级水滴形前脸与流线气动收口，实现全球大型MPV最低的0.215Cd超低风阻。",
        description=(
            "大型MPV高速最大能耗杀手是迎风面积与风阻系数。理想MEGA从车头大曲率一体式弧形风挡到车尾气流顺滑收束（类似水滴气动学），"
            "打破了MPV方盒子的物理限制，百公里电耗仅为惊人的15.9kWh，让5.35米大型七座豪华旗舰具备如轿车般的高速低电耗。"
        ),
        technical_principles=[
            "全平整化底盘导流与无缝水滴式车顶弧线曲面连续过渡",
            "A柱一体热成型大曲率双层静音玻璃平滑顺接",
        ],
        advantages=[
            "高速巡航每百公里电耗仅15.9kWh，纯电MPV高速续航极其扎实",
            "极低风阻带来无与伦比的高速静音效果，后排如同图书馆",
        ],
        limitations=[
            "极具颠覆性的科幻先锋造型在传统保守审美市场有一定讨论度",
        ],
        sub_variants={},
        representative_vehicles=["理想MEGA"],
        standard_labels=["MEGA水滴造型", "0.215Cd风阻", "低电耗MPV", "高铁列车风范", "极致静谧"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向纠结纯电MPV高速续航的客户算能耗：‘传统MPV高速电耗动辄25度，MEGA靠0.215高铁水滴风阻降到15.9度，跑高速又安静又省电！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 8. 理想车载双温冷暖双用压缩机冰箱
    TechnologyEntity(
        id="ideal_refrigerator_dual_temp",
        name="理想车载智能双温智能压缩机冷暖冰箱",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Dual-Temperature Compressor In-Car Refrigerator",
        category=TechCategory.COCKPIT_OS,
        subcategory="真正车载直流变频压缩机制冷与加热恒温箱",
        aliases=[
            "理想冰箱",
            "理想车载冰箱",
            "理想双温冰箱",
            "理想压缩机冰箱",
            "理想冷暖冰箱",
            "离车保温24小时",
        ],
        summary="配备真正直流变频压缩机，支持0℃至7℃冷藏及35℃至50℃暖奶保温，锁车后支持离车持续保温长达24小时。",
        description=(
            "不同于部分竞品使用的廉价半导体制冷片（降温慢且温差小），理想全系采用真正专用车规直流变频压缩机。"
            "夏天迅速冰镇饮料与水果，冬天为哺乳期宝妈恒温温热牛奶或早餐；支持手机APP远程一键提前开启，下车自动保持恒温一整天。"
        ),
        technical_principles=[
            "超紧凑车规级防倾斜变频直流压缩机",
            "高密度聚氨酯微孔发泡保温箱体与高低压智能电源管理",
        ],
        advantages=[
            "制冷迅速，半小时内快速冰透可乐与婴儿辅食",
            "离车持续工作24小时耗电仅0.5度，随时喝上冰爽饮品或温热母乳",
        ],
        limitations=[
            "占用前排扶手箱下方部分储物容积",
        ],
        sub_variants={},
        representative_vehicles=["理想L9全系", "理想L8 Ultra", "理想L7 Ultra", "理想MEGA"],
        standard_labels=["车载压缩机冰箱", "冷暖双用", "离车保温24小时", "奶爸车必备", "带娃神器"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向宝爸宝妈展示冰箱：‘真正的压缩机冰箱，夏天冰镇可乐水果，冬天给宝宝热奶保温，下车锁车它还能持续保温一整天，全家出游幸福感爆棚！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 9. 理想铂金全景声音响系统 (21扬声器杜比全景声 7.3.4)
    TechnologyEntity(
        id="ideal_platinum_sound",
        name="理想铂金音响系统 (21扬声器杜比全景声 7.3.4)",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Platinum Sound 21-Speaker Dolby Atmos 7.3.4 System",
        category=TechCategory.COCKPIT_OS,
        subcategory="高保真家庭全景声影院级车载音响",
        aliases=[
            "理想音响",
            "铂金音响",
            "7.3.4音响",
            "21个扬声器",
            "理想杜比全景声",
            "理想全景声",
            "2160w功放",
        ],
        summary="配备21个专业声学扬声器、3个双音圈超重低音炮与2160W超大功放，构筑7.3.4杜比全景声移动音乐厅与影院体验。",
        description=(
            "由资深金耳朵团队历时数万小时打造，配备4个顶棚天空声道扬声器与双层重低音矩阵。"
            "配合二排三排OLED大屏与座椅4D震动反馈，在车内观看战争大片时，飞机呼啸掠过头顶的声效与炮火震颤座椅身临其境，震撼全家感官。"
        ),
        technical_principles=[
            "全数字化DSP独立通道功放与Dirac Live声场空间相位校准算法",
            "7.3.4物理声道全景声布局与座椅触觉4D动感低频震动电机联动",
        ],
        advantages=[
            "全家看电影如同置身顶级杜比全景声巨幕影院VIP包厢",
            "人声极其温暖饱满，长途开车听歌彻底消除疲倦",
        ],
        limitations=[
            "高规格2160W铂金版主要标配于各车型的高配/顶配版本",
        ],
        sub_variants={},
        representative_vehicles=["理想L9", "理想L8 Ultra", "理想L7 Ultra", "理想MEGA"],
        standard_labels=["铂金音响", "7.3.4全景声", "21扬声器", "2160W大功放", "4D座椅振动"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "播放杜比全景声大片给客户体验：‘听！直升机从车顶飞过去的声音清清楚楚，座椅还在跟着低音炮震动，不用花钱去电影院，车里就是移动豪华影院！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 10. 理想堡垒级五星高强度钢铝车身安全架构
    TechnologyEntity(
        id="ideal_high_strength_cage",
        name="理想堡垒级五星安全标准高强钢铝车身",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Fortress High-Strength Steel-Aluminum Safety Body",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="全方位防碰撞高强乘员舱骨架",
        aliases=[
            "理想车身安全",
            "堡垒安全车身",
            "中保研全G",
            "25%偏置碰撞全优",
            "双侧25%碰撞",
        ],
        summary="在中保研与中汽研碰撞测试中拿下所有测评维度全G（优秀）大满贯，热成型钢占比超高，全车乘员舱无死角严密防护。",
        description=(
            "理想全系车型正反向自研‘堡垒车身’，在中保研严苛的主副驾双侧25%小偏置碰撞、侧面撞击及车顶抗压测试中全部获得顶级G级评级。"
            "标配全车侧气帘超长保压6秒以上，第三排乘员头部同样享有后纵梁大行程溃缩吸能与气帘保护，彻底破除大SUV第三排不安全的传统偏见。"
        ),
        technical_principles=[
            "双前防撞梁与环形封闭式副车架下沉吸能设计",
            "B柱与下门槛超大截面高强度热成型钢一体拼焊",
        ],
        advantages=[
            "主驾与副驾双侧小偏置碰撞同等最高G级保护，绝不在副驾安全性上偷工减料",
            "第三排距离后尾门留足充足溃缩缓冲空间，全家三代出行安全放心",
        ],
        limitations=[
            "极高强度用料使车身整备质量相对扎实厚重",
        ],
        sub_variants={},
        representative_vehicles=["理想L9", "理想L8", "理想L7", "理想L6", "理想MEGA"],
        standard_labels=["堡垒安全车身", "中保研全G评价", "双侧25%偏置碰撞全优", "第三排安全防护"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向看重全家安全的客户展示中保研碰撞实测成绩单：‘不仅主驾碰撞优秀，连副驾也是全G满分！第三排后方留足了厚实溃缩区，全家人坐哪儿都安全！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 11. 理想超大型一体化压铸后地板及铝纵梁
    TechnologyEntity(
        id="ideal_integrated_die_casting",
        name="理想超大一体化压铸后地板与防撞梁",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Integrated Gigacasting Rear Underbody",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="大吨位轻量化一体压铸铝车身构件",
        aliases=[
            "理想大压铸",
            "一体化后地板",
            "mega后地板压铸",
            "一体压铸铝纵梁",
        ],
        summary="采用超大吨位高压铸造机将后地板数十个冲压焊接散件集成化为一体铸件，减重明显且大幅提升第三排抗追尾安全刚性。",
        description=(
            "在理想MEGA和新一代架构上应用大型一体化压铸技术。自研免热处理高延伸率铝合金，"
            "将原本密集的焊点与接缝彻底消除，车尾抗冲击扭转刚度提升20%以上，并在后纵梁预留可拆卸溃缩吸能螺栓盒，兼顾极端安全与日常维修经济性。"
        ),
        technical_principles=[
            "万吨级一体高压压铸成型与全自动化工业机器人组装",
            "三段式后碰撞力分解与纵向渐进溃缩吸能齿形设计",
        ],
        advantages=[
            "第三排乘客被动安全防追尾抗挤压刚度大幅提升",
            "消除焊接毛刺与应力集中点，车身经久耐用零异响",
        ],
        limitations=[
            "大型压铸模具初期研发投入高昂",
        ],
        sub_variants={},
        representative_vehicles=["理想MEGA", "理想下一代高端纯电车型"],
        standard_labels=["一体化压铸后地板", "免热处理铝合金", "第三排防撞强化", "车身抗扭", "无异响刚性"],
        equivalence_group_id=EquivalenceDomain.GIGACASTING_STRUCTURE,
        sales_talking_points=[
            "向担心第三排被追尾的客户讲解：‘后地板是整块一体成型的大铸铝件，两根粗壮纵梁贯穿车尾，承受高速追尾撞击牢不可破！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 12. 理想全车 Nappa 真皮 SPA 级十六点气动按摩座椅
    TechnologyEntity(
        id="ideal_sovereign_seats",
        name="理想全车十点/十六点气动按摩座椅系统",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Pneumatic Multi-Point Spa Massage Seats",
        category=TechCategory.COCKPIT_OS,
        subcategory="全车三排均享的全身气动舒享理疗座椅",
        aliases=[
            "理想按摩座椅",
            "十六点按摩",
            "十点按摩",
            "全车座椅加热通风",
            "nappa真皮座椅",
            "spa级按摩",
        ],
        summary="打破豪车‘只有主驾副驾才有按摩’的惯例，实现第一排、第二排全系标配十点/十六点深层气动按摩与全车加热通风。",
        description=(
            "全车采用优质天然Nappa真皮包覆与复合舒适慢回弹海绵，内部布置10-16个独立气囊，"
            "支持波浪、猫步、腰部深度拉伸等多种仿真人按摩模式。即便是第三排乘客也标配座椅靠背电动调节与座椅加热，让车内没有一个‘低人一等’的座位。"
        ),
        technical_principles=[
            "静音微型气泵与多通路高灵敏度电磁充放气阀组",
            "符合脊柱生物力学的腰椎气动三档多向支撑",
        ],
        advantages=[
            "真正做到全家平权，车内父母长辈、妻子孩子坐在任何位置都享有顶级尊崇舒适",
            "长途开几个小时腰部肌肉不酸痛，长途远行完全没有传统汽车的疲惫感",
        ],
        limitations=[
            "全功能真皮气动按摩座椅使全车自重略有增加",
        ],
        sub_variants={},
        representative_vehicles=["理想L9", "理想L8", "理想L7", "理想L6", "理想MEGA"],
        standard_labels=["十六点按摩座椅", "全车平权", "Nappa真皮", "腰椎支撑", "带通风加热"],
        equivalence_group_id=None,
        sales_talking_points=[
            "请全家人一起坐上车打开按摩模式：‘别家车只有司机或者老板位才有按摩，理想全车前后排每一个座位都有深层气动按摩和加热通风，让长辈孩子坐哪儿都舒坦！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 13. 理想第三排电动魔术折叠翻平机构
    TechnologyEntity(
        id="ideal_three_row_flat_fold",
        name="理想第三排魔术一键全平电动收纳机构",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Third-Row Magic Power-Folding Flat-Floor System",
        category=TechCategory.COCKPIT_OS,
        subcategory="电动翻折沉降纯平超大后备箱空间",
        aliases=[
            "三排魔术翻折",
            "后排一键放倒",
            "纯平后备箱",
            "后备箱空间扩展",
            "一键折叠三排",
        ],
        summary="在后备箱按键一键电动放倒或翻起第三排座椅，放倒后形成完全纯平平整巨大地台，后备箱纵深达两米以上。",
        description=(
            "专为家庭大件行李与搬家露营设计。通过双静音电动推杆连杆机构，轻轻按动后备箱侧面按键，"
            "第三排座椅靠背与坐垫协同联动向前翻折平铺，与后备箱地板无缝对接连成一体纯平，轻松容纳山地自行车、高尔夫球包、婴儿推车及双人露营充气大床垫。"
        ),
        technical_principles=[
            "大扭矩低速静音蜗轮蜗杆电动铰链推杆",
            "防夹力敏电流检测与座椅安全锁止机械双重确认",
        ],
        advantages=[
            "放倒后没有任何凸起台阶，平整度完美，装卸沉重大件行李顺滑推入",
            "无需手动费劲拉绳子拉动笨重座椅，后备箱一键优雅搞定",
        ],
        limitations=[
            "折叠机构下方需要预留电机齿轮安装空间",
        ],
        sub_variants={},
        representative_vehicles=["理想L9", "理想L8", "理想MEGA"],
        standard_labels=["三排魔术折叠", "一键纯平", "两米纵深大空间", "电动放倒", "露营平铺大床"],
        equivalence_group_id=None,
        sales_talking_points=[
            "打开后备箱按下一键电动放倒：‘按一下按钮，三排座椅自己平稳翻倒，变成一张两米长的全平大床，装婴儿车不用拆轮子直接推上去！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 14. 理想方向盘安全驾驶交互屏与 HUD 协同
    TechnologyEntity(
        id="ideal_steering_touch_screen",
        name="理想方向盘安全驾驶交互屏与大画幅 HUD 协同系统",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Steering Wheel Mini-Touch Display & Coordinated HUD",
        category=TechCategory.COCKPIT_OS,
        subcategory="方向盘微型触控与抬头显示信息融合",
        aliases=[
            "方向盘交互屏",
            "方向盘小屏",
            "安全驾驶交互屏",
            "hud协同小屏",
            "取消传统仪表盘",
        ],
        summary="取消传统笨重仪表盘，在方向盘中央创新加入一块触控小屏配合超大HUD，只显示必要挡位能耗，让前方视野极度通透开阔。",
        description=(
            "传统大仪表盘经常被方向盘上缘遮挡视线。理想首创将速度和导航投在视线正前方的超清HUD上，"
            "方向盘正中央嵌入一块小巧的Mini-LED触控屏，显示纯电/燃油模式、挡位及小计里程，更可直接用大拇指在方向盘小屏上滑动切换动力模式，极简又安全。"
        ),
        technical_principles=[
            "车规级防眩光Mini-LED低温高亮度触控面板",
            "方向盘旋转角度阻尼信号滤波与画面防眩晕设计",
        ],
        advantages=[
            "彻底消除低头看仪表盘的驾驶分心危险，前方挡风玻璃视野一览无余毫无遮挡",
            "大拇指不用离开方向盘就能轻触切换纯电优先或油电混合模式",
        ],
        limitations=[
            "从传统燃油车过渡而来的车主最初两天需适应看HUD的视线焦点",
        ],
        sub_variants={},
        representative_vehicles=["理想L9", "理想L8", "理想L7", "理想L6", "理想MEGA"],
        standard_labels=["方向盘交互屏", "Mini-LED小屏", "无传统仪表", "极简视野", "HUD协同"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "让客户握住方向盘看向正前方：‘看前方毫无遮挡的大视野，时速和导航直接悬浮投在挡风玻璃上，大拇指碰碰方向盘小屏就能切换驾驶模式，开起来极其清爽！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 15. 理想全栈自研 800V 碳化硅五合一高效电驱动总成
    TechnologyEntity(
        id="ideal_800v_sic_drive",
        name="理想全自研 800V 高压碳化硅五合一电驱动总成",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto 800V SiC 5-in-1 High-Efficiency Electric Drive Unit",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="高压紧凑轻量化自研碳化硅电驱",
        aliases=[
            "理想800v电驱",
            "五合一电驱",
            "自研碳化硅电驱",
            "400kw电驱",
            "mega动力总成",
        ],
        summary="理想汽车完全自研的800V碳化硅电驱总成，功率密度突破4.3kW/kg，最高工况效率高达98.2%，为大型车赋予超低电耗与强劲动力。",
        description=(
            "集成电机、碳化硅逆变器、减速器、高压配电与热管理水套五合一紧凑结构。"
            "采用自研高频第三代SiC碳化硅功率模块，导通损耗降低50%以上，前后双电机综合输出功率达400kW（544马力），百公里加速仅5.5秒。"
        ),
        technical_principles=[
            "自研超薄晶圆SiC功率芯片定制塑封",
            "高速转子内置永磁体V型拓扑与扁线定子高压绝缘灌封",
        ],
        advantages=[
            "电控综合效率达98.2%，使5.35米长的全尺寸MPV实现堪比中型轿车的低电耗",
            "体积极其紧凑，为底盘前后桥释放巨大的乘员舱和下沉后备箱空间",
        ],
        limitations=[
            "碳化硅高端器件制造对洁净度与供应链良品率要求极高",
        ],
        sub_variants={},
        representative_vehicles=["理想MEGA", "理想下一代全尺寸纯电SUV"],
        standard_labels=["800V碳化硅电驱", "五合一总成", "98.2%最高效率", "超低电耗", "400kW动力"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向注重能耗的客户强调自研电驱：‘全栈800V自研碳化硅，效率高达98.2%，这么大一台豪华旗舰MPV，百公里电耗比很多紧凑纯电SUV还要低！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 16. 理想全国 5C 超级充电桩网络
    TechnologyEntity(
        id="ideal_supercharge_network",
        name="理想 5C 兆瓦级超级充电站与液冷充电网络",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto 5C Megawatt-Level Liquid-Cooled Supercharging Network",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高速干线与城市核心超快充体系",
        aliases=[
            "理想5c超充站",
            "理想超充桩",
            "520kw超充",
            "理想充电网络",
            "高速超充站",
        ],
        summary="单桩峰值功率高达520kW的超快充网络，全面覆盖全国主要高速服务区与核心商圈，充电枪线极其轻盈单手提拿。",
        description=(
            "理想汽车大规模自建的高速与城市全液冷5C超级充电站。每个车位配备全液冷充电线缆（重量仅为传统沉重枪线的三分之一），"
            "车主停车插入插枪即充，配合独立智能地锁与车牌自动识别降锁，有效杜绝燃油车占位，长途自驾享受极速尊享补能体验。"
        ),
        technical_principles=[
            "站端箱变兆瓦级动态储能调度与直流微网技术",
            "智能车牌识别防占位地锁与车云端无感自动扣费闭环",
        ],
        advantages=[
            "充电12分钟增加500公里续航，长途高速服务区补能体验彻底比肩加油",
            "全液冷轻量化枪线，力气小的女士也能单手轻松提起插枪",
        ],
        limitations=[
            "目前全国核心高速路网正在高速加密扩建中",
        ],
        sub_variants={},
        representative_vehicles=["理想MEGA", "理想L全系纯电优先/增程通用"],
        standard_labels=["理想5C超充", "520kW峰值功率", "轻量化液冷枪", "高速服务区覆盖", "防占位智能地锁"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "给客户看理想高速超充站分布图：‘国家各大高速干线服务区全都在建理想5C超充，带地锁不怕被油车占位，10分钟充好电接着出发！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 17. 理想增程器智能液压悬置主动隔振系统
    TechnologyEntity(
        id="ideal_active_engine_mount",
        name="理想增程器专属智能液压悬置隔振系统",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Range-Extender Hydraulic Vibration-Isolation Mounts",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="全频段发动机点火与运转主动滤震隔振",
        aliases=[
            "液压悬置",
            "增程器减振",
            "无感点火",
            "发动机隔振",
            "增程静音技术",
        ],
        summary="专为增程器定制的大容量智能液压减振悬置，点火与熄火瞬间彻底吸收机械震动，车内完全感受不到发动机启停。",
        description=(
            "增程车最怕发动机启停时的‘抖动一下’破坏纯电质感。理想研发了特种流体流变液压悬置系统，内部包含双节流通道与阻尼惯性通道，"
            "在增程器点火瞬间以反向液压阻尼完全中和震动冲击，哪怕在车内手扶方向盘或看中控水杯，水面波纹都不会发生一丝颤动。"
        ),
        technical_principles=[
            "多自由度大排量非线性橡胶液压复合解耦结构",
            "增程器点火转速匹配与飞轮平顺性电控动态扭矩补偿",
        ],
        advantages=[
            "彻底消灭增程器介入时的‘身体一颤’，乘员无从察觉增程器何时启动",
            "长期使用胶套耐磨抗老化，十年如一日保持出色的静音平稳质感",
        ],
        limitations=[
            "液压衬套制造密封工艺与耐久性测试极其严苛",
        ],
        sub_variants={},
        representative_vehicles=["理想L9", "理想L8", "理想L7", "理想L6"],
        standard_labels=["液压悬置", "增程器无感启停", "抗抖动", "极致静音", "纯电质感"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "在车内启动增程器让客户摸方向盘：‘您看，我现在手动把增程器点火启动，方向盘和座椅纹丝不动，水杯里的水连一丝涟漪都没有，这就是底气！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 18. 理想三温区独立恒温双效新风过滤空调
    TechnologyEntity(
        id="ideal_three_zone_fresh_air",
        name="理想三温区独立恒温双效新风过滤空调系统",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Three-Zone Independent Climate with Dual-Filter Air Purification",
        category=TechCategory.COCKPIT_OS,
        subcategory="多温区母婴级健康座舱空气洁净系统",
        aliases=[
            "三温区空调",
            "母婴级空调",
            "双效新风",
            "负离子空气净化",
            "理想空调系统",
        ],
        summary="主驾、副驾、后排独立三温区精准控温，配备CN95级活性炭双层复合滤芯与负离子杀菌，获得中汽研‘母婴级健康座舱’顶级认证。",
        description=(
            "全车配备三组独立变频电动膨胀阀与独立蒸发箱风机，爸爸怕热开21度、妈妈怕冷开25度、后排宝宝开23度互不干扰；"
            "具备驻车自动空气干燥防发霉异味技术，车内空气始终清爽干净，甲醛释放量低至国标五分之一，呵护易敏感宝宝呼吸健康。"
        ),
        technical_principles=[
            "前后双蒸发器多风道独立无级伺服风门控制",
            "AQS空气质量传感器自动内外循环切换与高压负离子发生器",
        ],
        advantages=[
            "解决全家人在车上对温度需求不同的经典矛盾，每个人都有专属舒适区",
            "新车提车没有任何刺鼻气味，刚出生的婴儿也能安心乘坐",
        ],
        limitations=[
            "多风道系统结构复杂度较高，建议每年定期更换空调滤芯",
        ],
        sub_variants={},
        representative_vehicles=["理想L系列全系", "理想MEGA"],
        standard_labels=["三温区空调", "母婴级健康座舱", "无异味新车", "CN95过滤", "独立温控"],
        equivalence_group_id=None,
        sales_talking_points=[
            "邀请注重健康的孕妇或宝妈上车深呼吸：‘很多新车一坐进去一股刺鼻塑料味，理想是中汽研五星母婴健康座舱，新车完全零异味，对小宝宝呼吸系统最安全！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 19. 理想哨兵模式低功耗守卫系统
    TechnologyEntity(
        id="ideal_sentinel_guard",
        name="理想低功耗智能哨兵守护系统",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Low-Power Intelligent Sentry Guard System",
        category=TechCategory.COCKPIT_OS,
        subcategory="全天候环视视觉与微震动感知驻车防御",
        aliases=[
            "理想哨兵模式",
            "低功耗哨兵",
            "驻车守护",
            "行车记录仪录像",
            "手机远程查看",
        ],
        summary="锁车后以极低功耗保持全车高清环视摄像头守卫，发生碰撞或有人靠近时自动录制事件视频并推送手机App提醒。",
        description=(
            "针对传统哨兵模式耗电快的问题，理想采用专用低功耗芯片配合边缘视觉唤醒算法。平时处于微瓦级休眠，"
            "当车身震动传感器检测到外力碰擦或视觉雷达检测到异常逗留时微秒级唤醒录制视频，一整天耗电量相比传统方案降低50%以上。"
        ),
        technical_principles=[
            "专用低功耗边缘协处理器（Low-Power Co-Processor）待机检测",
            "震动加速度阈值防猫狗路过误报自适应滤波算法",
        ],
        advantages=[
            "防刮碰、防恶意划车，遇到无良肇事者开门杀一查一个准",
            "耗电极低，长期出差停在机场或地库两周也能放心开着哨兵",
        ],
        limitations=[
            "电量低于20%时系统出于防亏电保护会自动停止待机",
        ],
        sub_variants={},
        representative_vehicles=["理想L系列全系", "理想MEGA"],
        standard_labels=["理想哨兵", "低功耗待机", "开门杀取证", "防碰擦录像", "远程手机提醒"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "消除停地库被刮的烦恼：‘不仅录得清清楚楚，而且功耗特别低，停在高铁站一个星期哨兵一直开着也掉不了几公里电，安全感十足！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 20. 理想 3.5kW 大功率 V2L 户外放电系统
    TechnologyEntity(
        id="ideal_v2l_discharge",
        name="理想 3.5kW 大功率车外交流放电系统 (V2L)",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto 3.5kW High-Power V2L External Power Discharge",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="多功能户外大功率交流移动电源",
        aliases=[
            "理想外放电",
            "v2l外放电",
            "3.5kw放电",
            "露营插座",
            "对外放电枪",
        ],
        summary="支持最大3.5kW超大功率对外输出220V标准交流电，车内配备220V专用插座，带全家露营随时变身移动供电中心。",
        description=(
            "通过专用外放电转换插头插入慢充口即可输出3.5kW纯正弦波220V交流电。能同时带动大功率电磁炉火锅、空气炸锅、户外投影仪和电水壶；"
            "车内后排更自带标配的220V 1.1kW插座，办公笔记本电脑随时插上高速充电，办公娱乐两不误。"
        ),
        technical_principles=[
            "双向逆变OBC拓扑电路与过载漏电超快切断保护",
            "车机大屏自定义设置防亏电最低放电终止百分比阈值",
        ],
        advantages=[
            "真正实现野外‘用电自由’，带娃自驾露营告别烧柴生火的安全隐患",
            "即使是增程车型，油箱里的油随时能转化成巨量度数电量，露营用电无限续杯",
        ],
        limitations=[
            "使用户外插排需选用具备防雨保护的正规国标插线板",
        ],
        sub_variants={},
        representative_vehicles=["理想L系列全系", "理想MEGA"],
        standard_labels=["V2L外放电", "3.5kW大功率", "车内220V插座", "露营野炊神器", "无限用电"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向爱好露营野餐的家庭讲解：‘去郊外露营不用带任何发电机，直接用车上的电煮咖啡、涮火锅、吹电风扇，就算电用完了增程器还能随时发电，电量管够！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 21. 理想跨楼层代客泊车与记忆泊车 (AVP)
    TechnologyEntity(
        id="ideal_auto_valet_parking",
        name="理想自研全场景跨楼层代客泊车系统 (AVP)",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Cross-Floor Automated Valet Parking (AVP)",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="地下复杂停车场自主导航寻位与自动泊入",
        aliases=[
            "理想代客泊车",
            "理想跨楼层记忆泊车",
            "avp记忆泊车",
            "地库自主泊车",
            "自动寻车位",
        ],
        summary="支持长达数公里的地下多层地库自主巡航、自动避让会车行人、上下螺旋陡坡并自主停入指定私人车位。",
        description=(
            "进入自家地下车库口，车主在屏幕上点击‘开始代客泊车’即可放手。车辆自主沿记忆路线下陡坡、过减速带、避让穿插行人和对向会车；"
            "如果自己车位被占，还能自主在周围寻找空余车位停入，停好后自动挂P挡拉手刹熄火，全程流畅自然如老司机代驾。"
        ),
        technical_principles=[
            "激光雷达与纯视觉SLAM地下弱GPS环境高精度定位建图",
            "动态时空障碍物避让重规划与坡道防溜车高精度制动线控",
        ],
        advantages=[
            "彻底解放每天下班回家在地库晕头转向找车位的疲劳",
            "面对地下连续多层螺旋陡坡，车辆循迹极其稳定不刮轮毂",
        ],
        limitations=[
            "初次使用需驾驶员正常行驶路线完成一次路线学习建图",
        ],
        sub_variants={},
        representative_vehicles=["理想L系列AD Max车型", "理想MEGA"],
        standard_labels=["AVP代客泊车", "跨楼层泊车", "地库记忆巡航", "螺旋坡道通行", "老司机泊车"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "现场演示地库记忆泊车：‘车开到小区地库门口就可以放心交给它，车子自己下B2层慢悠悠拐弯开到你车位倒进去，省心极了！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 22. 理想全域集中式双备份无感 OTA 升级体系
    TechnologyEntity(
        id="ideal_ota_matrix_update",
        name="理想全域集中式全车双备份无感 OTA 架构",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Full-Domain Dual-Backup Seamless FOTA Architecture",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="高可靠零打扰软件快速迭代体系",
        aliases=[
            "理想ota",
            "无感ota升级",
            "夜间自动升级",
            "全域ota",
            "双备份升级",
        ],
        summary="支持全车驱动、底盘、座舱、智驾数十个控制器整车静默并发升级，升级中途断电自动安全回退，夜间无感进化。",
        description=(
            "理想汽车成立以来以超快的高频OTA更新著称，几乎每个月都有重大功能进化。系统在后台利用夜间静默下载校验，"
            "凌晨两点自动无感完成安装并重启各域控制器。车主早晨上车直接开启‘全新功能版本’，整个过程对车主完全零打扰、零等待。"
        ),
        technical_principles=[
            "千兆以太网高速并发刷写与全控制器A/B双镜像校验",
            "车主用车时间规律AI预测，精准锁定无用车夜间窗口自动安装",
        ],
        advantages=[
            "高频进化：买车几年后，智驾越来越聪明、车机功能越来越丰富，真正实现‘常用常新’",
            "电信级双镜像备份，彻底杜绝OTA失败导致车辆无法开动的风险",
        ],
        limitations=[
            "夜间预约升级需保证车辆动力电池电量高于最低安全阈值",
        ],
        sub_variants={},
        representative_vehicles=["理想全系车型"],
        standard_labels=["理想OTA", "常用常新", "双备份安全", "夜间无感升级", "月月有新功能"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向担心电车几年后落伍的客户承诺：‘理想每个月都有大版本OTA，你的车就像智能手机一样天天在进化，开三年依然跟刚上市的新车一样好用！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 23. 理想全天候电池热失控‘无火’安全防爆盾
    TechnologyEntity(
        id="ideal_bms_safety_shield",
        name="理想全天候动力电池无火安全防护体系 (防爆盾)",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto All-Weather Thermal Runaway Fire-Free Battery Shield",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高阻燃隔热垫与定向毫秒泄压防爆包",
        aliases=[
            "电池防爆盾",
            "无火电池",
            "理想电池安全",
            "热失控不扩散",
            "底部加厚装甲",
        ],
        summary="电芯之间填充航天级气凝胶隔热阻燃材料与超强底部钢铝复合装甲，通过国家最严苛托底球击与单体热失控不起火测试。",
        description=(
            "动力电池包上盖和底部采用潜艇级高强冲压防护结构，电芯之间配备耐千度高温气凝胶隔热垫与定向定向向下排气通道。"
            "即使单个电芯由于极端外力穿刺发生热失控，高温高压气体毫秒级排向车外，邻近电芯温升不到30℃，确保整车永不起火、永不蔓延。"
        ),
        technical_principles=[
            "电芯间双向绝热与航天级纳米微孔气凝胶阻燃介质",
            "单向防爆阀定向高压下排气与毫秒级高压回路主动断电Pyro-Fuse",
        ],
        advantages=[
            "实现物理级别的单体热失控0起火、0蔓延至乘员舱",
            "底盘配备多层抗磨防撕裂复合装甲，即使路面大石块剧烈托底也伤不到电芯",
        ],
        limitations=[
            "加厚防撞防护壳体对电池包整备重量提出更高轻量化设计要求",
        ],
        sub_variants={},
        representative_vehicles=["理想全系车型"],
        standard_labels=["电池防爆盾", "不起火电池", "气凝胶隔热", "防托底底盘装甲", "乘员舱安全"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向最关心自燃风险的客户保证：‘电池下面有加厚的防弹级装甲，电芯之间全是航天隔热材料，哪怕大石头狠狠磕到底盘，电池也绝对不起火！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 24. 理想双电机智能全时电四驱扭矩分配
    TechnologyEntity(
        id="ideal_dual_motor_4wd",
        name="理想前后双电机智能全时电四驱系统",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Dual-Motor Intelligent Full-Time AWD System",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="毫秒级电四驱智能动态动态扭矩平衡",
        aliases=[
            "理想双电机四驱",
            "智能电四驱",
            "全时电四驱",
            "前后双电机",
            "脱困四驱",
        ],
        summary="全系标配前后双电机全时电四驱，系统综合功率330kW（449马力），百公里加速5秒级，雨雪湿滑路面毫秒级防滑脱困。",
        description=(
            "摆脱了传统燃油车笨重的机械传动轴和分动箱。前永磁同步/感应异步电机与后永磁同步电机完全电解耦控制，"
            "系统以微秒级刷新率根据四轮附着力实时调整前后轴扭矩分配（从0:100到100:0无级跳变），不仅加速如离弦之箭，在湿滑结冰弯道更是平稳贴地。"
        ),
        technical_principles=[
            "微秒级双MCU逆变器协同与全轮防滑ASR/ESP联合运控",
            "前轴感应异步电机（无拖拽阻力）或高功率永磁电机按工况智能休眠",
        ],
        advantages=[
            "全系标配四驱，没有低配两驱‘减配’，百公里加速稳稳进5.3-5.5秒",
            "冬天开去东北雪乡或者雨天高速，四驱抓地力赋予全车稳稳的安全感",
        ],
        limitations=[
            "主打公路全天候安全平稳与轻度越野脱困，并非针对攀爬大岩石重度极限越野",
        ],
        sub_variants={},
        representative_vehicles=["理想L9", "理想L8", "理想L7", "理想L6", "理想MEGA"],
        standard_labels=["全时智能电四驱", "全系标配四驱", "5秒级零百加速", "雨雪防滑", "前后独立电机"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "强调全系标配诚意：‘理想绝不搞便宜但容易打滑的两驱低配，全系标配前后双电机智能四驱，雨雪湿滑路面起步超车稳如泰山！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 25. 理想后排 15.7 英寸 3K OLED 电动吸顶娱乐屏
    TechnologyEntity(
        id="ideal_rear_entertainment_oled",
        name="理想 15.7 英寸 3K 超清 OLED 电动吸顶娱乐屏",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto 15.7-Inch 3K OLED Power-Folding Rear Entertainment Display",
        category=TechCategory.COCKPIT_OS,
        subcategory="车规级防眩柔性OLED折叠吸顶娱乐中心",
        aliases=[
            "后排吸顶屏",
            "15.7英寸oled",
            "电动吸顶大屏",
            "理想后排娱乐",
            "二排大电视",
        ],
        summary="采用三星定制3K车规超清OLED大屏，通过中控或语音电动折叠开合，超高对比度与低蓝光护眼认证，全家后舱观影神器。",
        description=(
            "后排娱乐屏拥有车规级超高耐温与抗震结构，具备德国莱茵硬件级低蓝光护眼认证，孩子长时间观看不伤眼、不疲劳。"
            "支持HDMI和Type-C一线直连任天堂Switch或索尼PS5游戏机，搭配车内220V电源与双无线手柄，长途服务区变身亲子游戏对战房。"
        ),
        technical_principles=[
            "三星车规级OLED面板低蓝光硬件调光技术",
            "超薄轻量化静音伺服电机与无级开合角度防夹微动开关",
        ],
        advantages=[
            "3K分辨率画质极其细腻，黑色深邃色彩绚丽",
            "一线直连Switch游戏机，长途出游孩子沉浸在马里奥赛车中不哭不闹",
        ],
        limitations=[
            "后排吸顶屏展开时需适应通过流媒体后视镜观察后车",
        ],
        sub_variants={},
        representative_vehicles=["理想L9全系", "理想L8 Ultra", "理想L7 Ultra", "理想MEGA"],
        standard_labels=["后排吸顶屏", "3K OLED超清", "低蓝光护眼", "Switch直连游戏", "后舱娱乐神器"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "给客户的孩子拿出一副Switch手柄：‘插上一根线，二排大屏立刻变成游戏机，两个孩子坐在后排一边玩一边笑，旅途一点都不枯燥！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 26. 理想 AD Pro 高速领航辅助系统 (地平线征程5平台)
    TechnologyEntity(
        id="ideal_ad_pro",
        name="理想 AD Pro 高速智能驾驶领航系统 (征程5)",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto AD Pro Highway NOA System (Horizon Journey 5)",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="高性价比单芯片全国高速领航与智能泊车",
        aliases=[
            "ad pro",
            "adpro",
            "理想ad pro",
            "征程5智驾",
            "高速noa",
            "标配高速领航",
        ],
        summary="基于地平线征程5芯片（128TOPS算力）的全栈自研纯视觉高阶智驾系统，全系标配全国高速与城市快速路无缝NOA领航辅助。",
        description=(
            "在理想L系列Pro车型上全系标配，无需额外花钱订阅或选装。采用自研视觉大模型算法与800万像素高清感知相机，"
            "在全国所有高速公路和环线高架上实现自动上下匝道、精准识别锥桶避障、自主变道超车及全场景自动泊车入位。"
        ),
        technical_principles=[
            "地平线征程5高效神经网络BPU架构深度异构优化",
            "前向800万超清视觉大动态范围高感光成像融合",
        ],
        advantages=[
            "买车即标配，终身免费使用，全国高速长途自驾彻底解放双脚",
            "芯片功耗极低，散热稳定，性能够用且性价比极高",
        ],
        limitations=[
            "不支持复杂城市内部红绿灯地面道路的领航辅助（城市NOA需选AD Max）",
        ],
        sub_variants={},
        representative_vehicles=["理想L6 Pro/Max", "理想L7 Pro", "理想L8 Pro"],
        standard_labels=["AD Pro", "地平线征程5", "标配高速NOA", "自主上下匝道", "终身免费智驾"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向预算务实的家庭推荐Pro版：‘不用加几万块选装高阶包，入门版就标配高速NOA，跑高速自己变道超车下匝道，终生免费用，性价比绝顶！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 27. 理想全场景超大画幅抬头显示系统 (HUD)
    TechnologyEntity(
        id="ideal_hud_holographic",
        name="理想超大画幅超高清全景抬头显示系统 (HUD)",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Ultra-Large High-Definition Panoramic HUD",
        category=TechCategory.COCKPIT_OS,
        subcategory="视网膜级全色域前风挡全景投影",
        aliases=[
            "理想hud",
            "全彩hud",
            "超大抬头显示",
            "高清hud",
            "视网膜级hud",
        ],
        summary="投射距离达数米、具备视网膜级清晰度的大画幅全彩HUD，阳光直射依旧清晰锐利，将车速、导航与智驾车道线全面融合展示。",
        description=(
            "由理想自研微型光机驱动，亮度自适应高达上万尼特。全彩投射导航转弯车道、限速标志、盲区变道预警红条及AD智驾自车识别状态，"
            "画面平整绝无重影与眩晕，驾驶全程无需低头，视线始终聚焦在前方真实道路上。"
        ),
        technical_principles=[
            "自由曲面反射光学放大系统抗色差畸变矫正",
            "环境照度毫秒感知高动态背光矩阵无极调光",
        ],
        advantages=[
            "画质细腻如手机Retina屏，戴太阳墨镜也能清晰辨认投影内容",
            "信息排布简洁专业，完全替代传统仪表盘，夜间长途驾驶眼睛不疲劳",
        ],
        limitations=[
            "强逆光或大雪覆盖前挡风投影区时需保证玻璃表面清洁",
        ],
        sub_variants={},
        representative_vehicles=["理想L9全系", "理想L8全系", "理想L7全系", "理想L6全系", "理想MEGA"],
        standard_labels=["理想全景HUD", "视网膜级清晰度", "超大画幅", "防眩晕投影", "安全不低头"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "坐在驾驶位向客户展示HUD投影：‘前方路面上漂浮着全彩导航箭头，连变道盲区有车都会亮起红光警示，视线完全不用离开马路，开车特别安心！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 28. 理想魔毯双腔空气悬架 Max/Ultra 增强版
    TechnologyEntity(
        id="ideal_magic_carpet_max",
        name="理想魔毯双腔空气悬架 Max/Ultra 增强版",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Dual-Chamber Magic Carpet Air Suspension Pro/Max",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="双腔空气弹簧多挡刚度毫秒级自适应切换",
        aliases=[
            "魔毯双腔版",
            "理想双腔空悬",
            "双腔魔毯",
            "刚度可调空悬",
            "l9双腔悬架",
        ],
        summary="采用行业顶级的双腔空气弹簧架构，不仅能调车身高低，还能毫秒级切换悬架单双腔容积改变底盘刚度软硬。",
        description=(
            "在单腔空悬只能调高低的基础上，双腔空悬引入了主副气室电磁阀切换。过平路颠簸时双腔开启气室容积变大，滤震柔和如大船；"
            "高速急转弯或刹车时电磁阀瞬间关闭副腔，空气刚度提升40%以上，死死撑住车身消除侧倾与俯仰点头，达成极致的操控与舒适两立。"
        ),
        technical_principles=[
            "大容量主腔与外置副气室快速电磁阀开关拓扑",
            "侧向加速度传感器与方向盘角速度毫秒前馈刚度闭环",
        ],
        advantages=[
            "彻底解决‘开大船容易晕车侧倾’的痛点，兼备魔毯舒适与德系操控支撑",
            "全家满载时根据乘员重量自动校平前后轴高度，姿态始终挺拔如初",
        ],
        limitations=[
            "硬件结构较单腔空簧更复杂，成本主要搭载于高端旗舰车型（L9与MEGA）",
        ],
        sub_variants={},
        representative_vehicles=["理想L9全系", "理想MEGA全系"],
        standard_labels=["双腔魔毯悬架", "双腔空簧", "刚度软硬可调", "抗侧倾极佳", "旗舰专属底盘"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "带客户体验双腔空悬过弯：‘看！过减速带像坐在软沙发上，但是在高速匝道大角度过弯时，双腔气阀瞬间锁死，这么大一台全尺寸SUV几乎完全不侧倾！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 29. 理想端到端 E2E + VLM 双系统自动驾驶大模型
    TechnologyEntity(
        id="ideal_e2e_vlm_model",
        name="理想端到端 E2E + VLM 双系统自动驾驶大模型",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Dual-System E2E + VLM Autonomous Driving Foundation",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="快系统与慢系统双脑协同具身智能智驾架构",
        aliases=[
            "e2e+vlm",
            "理想端到端",
            "理想端到端大模型",
            "快慢系统智驾",
            "vlm世界模型",
            "理想双系统大模型",
        ],
        summary="模拟人类大脑‘快反应直觉+慢思考逻辑’的革命性智驾大模型架构，具备极强类人老司机本能与复杂场景常识理解能力。",
        description=(
            "参考诺贝尔奖心理学家丹尼尔·卡尼曼《思考，快与慢》理论设计。端到端快系统（System 1）以每秒数十帧的极速直接完成感知到动作输出；"
            "车载VLM视觉语言大模型（System 2）充当沉稳副驾驶，在遇到不按常理出牌的特殊事故现场或异形指示牌时进行逻辑常识推理，指导快系统安全决策。"
        ),
        technical_principles=[
            "多模态视觉特征输入直接映射连续转向刹车轨迹空间",
            "车载22亿参数轻量化VLM高维语义推理引擎微秒级反馈",
        ],
        advantages=[
            "遇到复杂的无车道线乡道、潮汐车道与环岛变道游刃有余",
            "能像人类一样看懂交警挥动的指挥手势与临时摆放的红白隔离墩",
        ],
        limitations=[
            "对车载计算硬件算力要求极高，仅支持搭载双Orin-X的AD Max硬件架构",
        ],
        sub_variants={},
        representative_vehicles=["理想L系列AD Max车型", "理想MEGA"],
        standard_labels=["E2E+VLM", "快慢双系统", "类人思考", "常识逻辑推理", "新一代智驾"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向追求顶尖AI大模型的科技客户阐述：‘理想把诺贝尔奖的思考快与慢理论做进了汽车大脑，直觉反应加逻辑思考，真正让车具备了人类司机的智慧！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 30. 理想全栈自研整车中央域控制器 (XCU)
    TechnologyEntity(
        id="ideal_xcu_central_controller",
        name="理想全栈自研整车中央域控制器 (XCU)",
        brand="理想 (Li Auto)",
        brand_key="li_auto",
        english_name="Li Auto Full-Stack In-House Central Domain Controller (XCU)",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="底盘动力热管理一体化中央控制中枢",
        aliases=[
            "xcu控制器",
            "理想xcu",
            "中央域控",
            "底盘中央控制器",
            "xcu整车大脑",
        ],
        summary="理想完全自主研发的中央域控制器，将增程系统、底盘空气悬架、热管理及整车配电高度集成于单一大脑，实现整车跨系统毫秒协同。",
        description=(
            "打破了传统汽车各ECU各自为政的壁垒。XCU控制器由理想电子团队自主从PCB电路板级设计，"
            "编写了数百万行底层固件代码。当车辆遇到颠簸坑洼时，XCU在几毫秒内同时向空气悬架下达调节指令、向电机下达扭矩抑制指令，实现全车如一体的绝顶平顺性。"
        ),
        technical_principles=[
            "多核高性能车规MCU与AUTOSAR自适应软件架构",
            "软硬件深度全解耦，支持跨系统统一算力池调度",
        ],
        advantages=[
            "软硬件完全自主可控，不受国外Tier 1零部件大厂的卡脖子与冗长开发周期限制",
            "悬架、电机、热管理深度打通，实现极致顺滑的一体化驾乘体验",
        ],
        limitations=[
            "需要庞大的自研软硬件工程团队持续维护底层代码库",
        ],
        sub_variants={},
        representative_vehicles=["理想L系列全系", "理想MEGA"],
        standard_labels=["XCU中央域控", "全栈自研", "底盘动力融合", "软硬件一体", "毫秒级协同"],
        equivalence_group_id=None,
        sales_talking_points=[
            "讲清自研核心控制器的重要性：‘理想把底盘、电机和悬架的大脑全部自研合一，过坑时悬架和电机会在同一毫秒互相打配合，这就是为什么理想开起来比别人都舒服！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),
]

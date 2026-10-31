"""
BYD Proprietary Automotive Technology Registry (src/terminology/brands/byd.py).
Contains 30 comprehensive proprietary technologies for BYD / Denza / Yangwang / Fangchengbao.
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

BYD_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 云辇智能车身控制系统 (Original)
    TechnologyEntity(
        id="byd_disus",
        name="比亚迪云辇智能车身控制系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD DiSus Intelligent Body Control System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="主动车身控制与垂向底盘悬架",
        aliases=[
            "云辇",
            "云辇系统",
            "云辇底盘",
            "云撵",
            "云撵系统",
            "disus",
            "yunnian",
            "云辇-c",
            "云辇-a",
            "云辇-p",
            "云辇-x",
            "云辇c",
            "云辇a",
            "云辇p",
            "云辇x",
            "disus-c",
            "disus-a",
            "disus-p",
            "disus-x",
        ],
        summary="比亚迪自研全栈智能车身垂直方向控制系统，根据不同车型定位划分为C、A、P、X四个级别，涵盖阻尼可调、空气悬架、液压悬架与全主动悬架。",
        description=(
            "云辇系统（DiSus）是比亚迪针对新能源汽车垂直方向运动控制完全自主研发的体系化解决方案。"
            "包含云辇-C（智能阻尼车身控制，毫秒级自适应阻尼调节）、云辇-A（智能空气车身控制，支持单/双腔高低与刚度可调）、"
            "云辇-P（智能液压车身控制，四轮联动四级刚度调节，支持200mm行程调节与原地掉头姿态平稳）、"
            "云辇-X（全主动车身控制，双目摄像头+双阀液压全主动执行，支持0侧倾、跳舞及单轮腾空行驶）。"
        ),
        technical_principles=[
            "全车传感器纳秒级感知（车身高度、加速度、横摆角、双目预瞄雷达）",
            "中央域控制器集中融合计算，实现俯仰、侧倾、横摆及垂向全维度解耦控制",
            "液压/气压双向高压蓄能器与自适应电磁阀毫秒级调节",
        ],
        advantages=[
            "极大抑制急刹点头与加速抬头，提升防晕车舒适度",
            "越野场景下云辇-P可实现超高抗冲击与四轮平衡，极高通过性",
            "云辇-X可实现全主动姿态平衡与超跑极限过弯0侧倾",
        ],
        limitations=[
            "高端版本（P与X）系统结构较重、造价与维护成本较高",
            "入门级云辇-C仅具备CDC连续阻尼可调，无法调节车身绝对离地间隙",
        ],
        sub_variants={
            "云辇-C": "智能阻尼车身控制系统（基于电磁阀连续可变阻尼CDC）",
            "云辇-A": "智能空气车身控制系统（空簧+CDC，具备高度与刚度多挡可调）",
            "云辇-P": "智能液压车身控制系统（主动高压液压多级刚度可调，适用于高端硬派越野）",
            "云辇-X": "全主动车身控制系统（主动电驱液压驱动，全主动0侧倾、原地起跳）",
        },
        representative_vehicles=["仰望U8", "仰望U9", "腾势N7", "腾势D9", "腾势Z9GT", "比亚迪汉", "比亚迪唐", "方程豹豹5"],
        standard_labels=["智能车身控制系统", "连续可变阻尼减振器(CDC)", "智能空气悬架", "全主动液压悬架", "垂直控制", "防点头防侧倾"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "面对追求驾乘舒适与防止晕车的家庭客户，重点介绍云辇-C/A消除起步抬头与刹车点头的平稳体验；",
            "面对对比豪华越野的客户，重点突出云辇-P的主动悬架四轮联动与自适应升降抗造能力；",
            "对比合资/豪华品牌底盘，突出比亚迪自研软硬件深度融合闭环、维修更换体系成熟且性价比高。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 2. 易四方四电机独立驱动架构 (Original)
    TechnologyEntity(
        id="byd_e4",
        name="比亚迪易四方四电机独立驱动架构",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD e4 Quad-Motor Independent Drive Platform",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="多电机独立电驱与扭矩矢量控制",
        aliases=[
            "易四方",
            "易四方技术",
            "易四方平台",
            "e4",
            "byd e4",
            "四电机独立驱动",
            "四电机独立转向",
            "原地掉头",
            "应急浮水",
        ],
        summary="国内首个量产四电机独立驱动技术架构，通过四个车轮的完全解耦独立电机与中央协同控制，实现原地坦克掉头、高速爆胎平稳可控及应急浮水脱困能力。",
        description=(
            "易四方技术平台以四个独立永磁同步电机分别驱动四个车轮，单电机峰值功率可达220-240kW，整车综合功率突破1100匹马力。"
            "摆脱了传统传动轴与转向机机构的限制，通过四轮差动扭矩实现左右轮反向旋转（原地掉头）以及极端爆胎工况下的毫秒级扭矩实时纠偏。"
        ),
        technical_principles=[
            "前后双电驱双轴高集成总成，四电控高度集成架构",
            "四轮扭矩矢量分配算法毫秒级响应（计算周期比传统机械ESP快100倍）",
            "IP68级整车级防水密封与应急浮水推进姿态闭环控制",
        ],
        advantages=[
            "实现非铺装与高附着路面的圆心原地掉头，最小转弯半径缩减至极致",
            "单轮甚至双轮爆胎时，其余轮毫秒级反向施加扭矩，车身不失控、不跑偏",
            "超跑级动力输出，极速及加速性能极强（仰望U9零百2.36秒）",
        ],
        limitations=[
            "重量与三电体积较大，目前仅配置在百万级高端旗舰车型上",
            "高附着力柏油路面频繁原地掉头对轮胎磨损极高",
        ],
        sub_variants={
            "易四方越野版": "匹配大减速比轮边减速机构，强化极低速大扭矩攀爬与应急脱困（仰望U8）",
            "易四方赛道版": "匹配超高转速电机与超薄硅钢片，注重赛道极速与弯道精准扭矩矢量分配（仰望U9）",
        },
        representative_vehicles=["仰望U8", "仰望U9"],
        standard_labels=["四电机独立驱动", "四轮扭矩矢量控制", "原地掉头", "超强动力输出", "应急浮水安全脱困"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向高端越野与性能车客户推荐时，突出其相比传统机械差速锁更强、响应更快的安全冗余与爆发力；",
            "高速安全卖点：重点说明120km/h单轮爆胎时系统能瞬时接管保持直线行驶的极致安全特性。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 3. 刀片电池系统 (Original)
    TechnologyEntity(
        id="byd_blade_battery",
        name="比亚迪刀片电池系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD Blade Battery System",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高安全磷酸铁锂结构化动力电池",
        aliases=[
            "刀片电池",
            "刀片电芯",
            "blade battery",
            "磷酸铁锂刀片",
            "二代刀片电池",
            "第二代刀片电池",
        ],
        summary="采用扁平长条形设计的磷酸铁锂高安全结构化电池，不仅电芯具备无模组高成组率，且通过行业最严苛针刺试验不起火不冒烟。",
        description=(
            "刀片电池将磷酸铁锂电芯做成长条扁平化（长度通常为600mm-1000mm），直接跳过模组（Module）组装成电池包（CTP架构）。"
            "扁平电芯自身兼顾结构梁作用，散热面积大、产热率低、结构刚度极高，显著提升了体积利用率（超过60%）和安全性。"
        ),
        technical_principles=[
            "无模组设计（CTP），电芯直接固定在包体内壳体充当结构件",
            "磷酸铁锂材料放热启动温度高（>500℃），耐过充与内短路性能优异",
            "超长散热路径与蜂窝铝板上下保护结构",
        ],
        advantages=[
            "极高本征安全性，针刺贯穿不发生热失控",
            "充放电循环寿命达3000次以上，衰减极慢",
            "生产良品率高，成本控制优势巨大",
        ],
        limitations=[
            "受制于磷酸铁锂材料特性，冬季极寒工况下放电功率与充电速度受环境温度影响较大",
            "重量能量密度相比高端三元锂电池略逊一筹",
        ],
        sub_variants={
            "一代刀片电池": "第一代CTP成组技术，能量密度约140Wh/kg",
            "二代高能量密度刀片电池": "全新纳米结构与轻量化PACK，能量密度提升至180Wh/kg以上，支持快充倍率提升",
        },
        representative_vehicles=["比亚迪汉", "比亚迪唐", "秦PLUS", "宋PLUS", "海豹", "海豚", "腾势D9"],
        standard_labels=["磷酸铁锂电池", "CTP无模组电池包", "针刺不起火高安全电池", "长寿命动力电池"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "针对顾虑电车自燃和电池寿命的保守型客户，强调针刺不爆不起火以及超长质保承诺；",
            "结合全车终身质保权益，化解消费者对电车二手贬值与换电成本的担忧。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 4. DM-i / DM-p 超级混动系统 (Original)
    TechnologyEntity(
        id="byd_dmi_dmp",
        name="比亚迪 DM-i / DM-p 超级混动系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD DM-i / DM-p Super Hybrid System",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="双电机双模式插电式混合动力架构",
        aliases=[
            "dm-i",
            "dmi",
            "dm-p",
            "dmp",
            "超级混动",
            "比亚迪混动",
            "第五代dmi",
            "第五代dm",
            "dm5.0",
            "ehs电混",
        ],
        summary="以电为主的双电机插电混动系统。DM-i侧重极致超低油耗与平顺长续航；DM-p侧重四驱强劲动力与脱困通过性。",
        description=(
            "比亚迪DM超级混动采用自主研发的高热效率插混专用发动机（骁云发动机热效率达46%以上）与EHS双电机电混系统。"
            "绝大部分城市工况下采用电动机纯电或串联增程驱动，高速高负荷工况采用发动机直驱或并联发力，彻底解决了传统燃油车和早期PHEV亏电油耗高的痛点。"
        ),
        technical_principles=[
            "以大功率电机驱动和大容量动力电池为主，发动机主要充当增程发电和高速直驱角色",
            "无传统多挡自动变速箱，单挡减速直驱，传动效率超98%",
            "电控采用碳化硅功率模块，全温区智能热管理体系",
        ],
        advantages=[
            "亏电油耗极低（第五代DM百公里亏电油耗低至2.9L）",
            "综合续航里程突破2000公里，无任何里程与节假日充电焦虑",
            "全速域动力输出平顺如纯电，无换挡顿挫感",
        ],
        limitations=[
            "高速120km/h以上再加速爆发力相比大排量纯燃油或多挡PHEV后劲稍平淡",
            "DM-i车型多为前驱单电机，脱困性能不如全时机械四驱或DM-p四驱",
        ],
        sub_variants={
            "DM-i": "以经济节能为第一目标，主打超长续航与超低能耗",
            "DM-p": "以四驱性能为导向，前后双电机强劲四驱，百公里加速进4秒级",
            "DMO": "超级混动越野平台（非承载式车身专用，大梁与纵置发动机融合）",
        },
        representative_vehicles=["秦L", "海豹06", "宋Pro", "汉DM-i", "唐DM-p", "腾势D9 DM-i", "豹5 (DMO)"],
        standard_labels=["插电式混合动力(PHEV)", "双电机混动架构", "超低亏电油耗", "超长综合续航", "以电为主混动"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "针对家中有单台车需求、常跑长途且无法安装私家充电桩的客户，DM-i是无续航焦虑首选；",
            "对比日系双擎油混，强调绿牌免购置税、纯电通勤0油费、动力平顺迅猛三大差异化优势。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 5. CTB 电池车身一体化技术 (Original)
    TechnologyEntity(
        id="byd_ctb",
        name="比亚迪 CTB 电池车身一体化技术",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD CTB (Cell to Body) Technology",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="车身结构与三电底盘深度融合",
        aliases=[
            "ctb",
            "byd ctb",
            "电池车身一体化",
            "车身电池一体化",
            "海豹ctb",
        ],
        summary="将刀片电池上盖与车身地板合二为一，电池包既是动力源又是车身超强刚性结构件，实现超40000 N·m/deg的百万豪车级车身扭转刚度。",
        description=(
            "比亚迪CTB（Cell to Body）技术打破了传统车身底板与电池包分开安装的思维，将刀片电池直接作为车身底部传力承载结构。"
            "车身结构简化，纵向乘坐空间增加，整车重心大幅降低，赋予车辆极高的抗扭曲刚度与侧碰防护能力。"
        ),
        technical_principles=[
            "电池包上壳体作为车身下地板，形成蜂窝类三明治结构",
            "纵横梁与车身门槛梁无缝焊接，力传导均匀扩散",
        ],
        advantages=[
            "整车扭转刚度突破40500 N·m/deg，操控稳健与NVH表现显著提升",
            "垂向空间释放，车内Z向坐姿更低更自然，拒绝小板凳坐姿",
        ],
        limitations=[
            "电池包与车身高度集成，若遭遇极严重底盘磕碰托底，维修更换复杂度和工时费较高",
        ],
        sub_variants={},
        representative_vehicles=["海豹", "腾势N7", "宋L", "海狮07 EV"],
        standard_labels=["CTB电池车身一体化", "高扭转刚度车身", "低重心运动底盘", "轻量化车身结构"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "对比传统油改电或常规纯电车，向追求驾驶质感的客户阐述40000+刚度带来的弯道侧向支撑与静谧性。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 6. DMO 超级混动越野平台
    TechnologyEntity(
        id="byd_dmo",
        name="比亚迪 DMO 超级混动越野平台",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD DMO Dual Mode Off-Road Platform",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="非承载式专业越野电驱混动架构",
        aliases=[
            "dmo",
            "dmo平台",
            "dmo混动",
            "超级混动越野平台",
            "豹式掉头",
            "方程豹dmo",
        ],
        summary="专为硬派越野打造的插混专用非承载式架构，以电驱为主融合高强车架大梁，支持前后双电驱与智能电四驱豹式掉头。",
        description=(
            "DMO平台融合CTC电池底盘一体化大梁与纵置EHS电混系统，集成前后电子差速锁和能量中锁，"
            "实现500kW+系统综合功率、100%爬坡度，并可实现转弯半径仅3.4米的‘豹式掉头’。"
        ),
        technical_principles=[
            "纵置EHS混动总成与越野专用后驱总成布局",
            "CTC电池与非承载式大梁一体化结构，扭转刚度提升38%",
            "前后轴电子无级扭矩分配与电控差速锁联动",
        ],
        advantages=[
            "兼顾极限越野强脱困能力与城市铺装路低油耗（百公里7.8L）",
            "CTC大梁一体化降低越野质心，翻滚风险显著低于传统硬派越野",
        ],
        limitations=[
            "非承载车身整备质量较大，极速受限在180km/h左右",
        ],
        sub_variants={"DMO电驱越野": "方程豹豹5/豹8搭载版本"},
        representative_vehicles=["方程豹豹5", "方程豹豹8"],
        standard_labels=["DMO混动", "非承载式车身", "CTC电池底盘一体化", "豹式掉头", "智能电四驱"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "向越野爱好者强调：DMO彻底终结了越野车‘市区油耗高、舒适性像开拖拉机’的痛点，周末去西藏穿越，平时上下班纯电开。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 7. 第五代 DM 技术 (DM 5.0)
    TechnologyEntity(
        id="byd_dm5",
        name="比亚迪第五代 DM 技术",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD 5th Generation DM Hybrid Technology",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="极致超高热效率插电混动系统",
        aliases=[
            "第五代dm",
            "dm5",
            "dm5.0",
            "第5代dm",
            "46.06%热效率",
            "百公里油耗2.9L",
            "比亚迪第五代混动",
        ],
        summary="全球最高46.06%发动机热效率与百公里2.9L超低亏电油耗插混系统，满油满电综合续航突破2100公里。",
        description=(
            "第五代DM技术以插混专用高效发动机（46.06%最高有效热效率）、EHS电混系统及插混专用刀片电池为三大基石，"
            "全温区热管理架构覆盖前舱、座舱、电池三大域，电驱综合工况效率达到92%创纪录水平。"
        ),
        technical_principles=[
            "超高压缩比16:1与高滚流气道阿特金森循环",
            "球形燃烧室与分段多次喷射燃烧系统",
            "超低黏度机油与低摩擦涂层活塞环",
        ],
        advantages=[
            "全球量产发动机最高热效率46.06%",
            "百公里综合亏电油耗降至2.9L（NEDC工况），每公里油费不到0.2元",
            "满油满电超长续航2100公里，一箱油横跨大半个中国",
        ],
        limitations=[
            "高速持续超车时发动机转速攀升，NVH噪音较中低速略微明显",
        ],
        sub_variants={"DM 5.0插混": "秦L、海豹06首发搭载版本"},
        representative_vehicles=["秦L", "海豹06", "宋L DM-i", "宋PLUS DM-i第五代"],
        standard_labels=["第五代DM", "46.06%热效率", "2100km续航", "百公里2.9L油耗", "EHS电混"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "面对普通通勤家用客户：‘一箱油开2100公里，从北京开到广州不用进加油站，亏电油耗比摩托车还省！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 8. e平台3.0 Evo
    TechnologyEntity(
        id="byd_e_platform_3_evo",
        name="比亚迪 e平台3.0 Evo",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD e-Platform 3.0 Evo",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="高集成全域800V纯电骨干架构",
        aliases=[
            "e平台3.0evo",
            "e平台3.0 evo",
            "e-platform 3.0 evo",
            "evo平台",
            "十二合一电驱",
        ],
        summary="集成了十二合一智能电驱、全域高压架构、智能升流快充与内骨骼式CTB安全的全新一代纯电进化架构。",
        description=(
            "e平台3.0 Evo在原有e平台3.0基础上深度重构，行业首创十二合一智能电驱系统（电机转速达23000rpm），"
            "搭载全域智能快充解决方案，包含智能升压、双枪超充及末端快充全场景脉冲自加热体系。"
        ),
        technical_principles=[
            "十二合一电驱集成驱动电机、逆变器、减速器、BMS、DC-DC、OBC及PDU",
            "全域高压SiC碳化硅模块与电驱升压充电架构",
        ],
        advantages=[
            "电驱体积减小20%，电机最高效率达97.5%",
            "公共快充桩全兼容，充电10-80%大幅缩短至25分钟内",
        ],
        limitations=[
            "高度集成度对单一零部件损坏时的模块化维修提出更高要求",
        ],
        sub_variants={},
        representative_vehicles=["海狮07 EV", "海豹EV 2025款"],
        standard_labels=["e平台3.0 Evo", "十二合一电驱", "全域800V", "智能升流充电", "内骨骼CTB"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "告诉看重充电速度和冬季用车的客户：Evo架构不仅充电快，而且不挑桩，老旧500V桩能自动升压快充，冬天充电也不慢。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 9. e平台3.0 (Original Base)
    TechnologyEntity(
        id="byd_e_platform_3",
        name="比亚迪 e平台 3.0",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD e-Platform 3.0",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="纯电专属模块化整车架构",
        aliases=[
            "e平台3.0",
            "e-platform 3.0",
            "八合一电驱",
            "宽温域热泵",
            "byd e3.0",
        ],
        summary="比亚迪专为纯电动车打造的整车模块化架构，首创八合一电动力总成、宽温域高效热泵系统及专属纯电底盘骨架。",
        description=(
            "e平台3.0解耦传统前舱布局，实现短悬长轴大空间，全系标配高集成八合一电驱与宽温域热泵，"
            "使电动车在-30℃至60℃极端气候下均能保持优秀的续航和热管理表现。"
        ),
        technical_principles=[
            "八合一电动力总成深度模块化集成",
            "冷媒直冷直热热泵与电机余热深度回收系统",
        ],
        advantages=[
            "空间利用率极高，A级车轴距达到B级车乘坐空间",
            "冬季低温续航达成率提升20%以上",
        ],
        limitations=[
            "初期版本未普及全域800V碳化硅架构",
        ],
        sub_variants={},
        representative_vehicles=["元PLUS", "海豚", "海豹", "海鸥"],
        standard_labels=["e平台3.0", "八合一电动力", "宽温域热泵", "纯电专属架构"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "强调比亚迪纯电绝非油改电，后排地板纯平、机舱短小轴距超长，车内空间宽敞舒适。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 10. DiLink 智能座舱网联系统
    TechnologyEntity(
        id="byd_dilink",
        name="比亚迪 DiLink 智能网联系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD DiLink Intelligent Cockpit Network System",
        category=TechCategory.COCKPIT_OS,
        subcategory="开放安卓生态智能座舱系统",
        aliases=[
            "dilink",
            "dilink系统",
            "dilink100",
            "dilink150",
            "旋转pad",
            "自适应旋转屏",
            "比亚迪座舱",
        ],
        summary="以自适应旋转悬浮Pad和100%安卓应用生态为特色的车载智能座舱网联系统，支持全场景语音与丰富车载娱乐。",
        description=(
            "DiLink依托高性能定制车规芯片与开放安卓底层架构，支持横竖屏自动旋转切换，适配数百万款安卓生态APP，"
            "并具备四音区独立语音识别、毫秒级免唤醒连续指令交互及全场景K歌娱乐系统。"
        ),
        technical_principles=[
            "车规级高算力SoC（高通定制及自研芯片）",
            "重力感应自适应旋转机构与深度定制UI引擎",
            "开放式应用市场框架与底层整车安全隔离沙箱",
        ],
        advantages=[
            "APP生态无限扩展，刷抖音看剧竖屏横屏自动贴合",
            "支持车载KTV、游戏手柄多外设扩展娱乐体验强",
        ],
        limitations=[
            "长期安装大量第三方APP可能导致系统内存碎片化与略微卡顿",
        ],
        sub_variants={
            "DiLink 100": "主流中高端车型搭载（高通芯片）",
            "DiLink 150": "旗舰车型搭载，4nm高算力座舱芯片",
        },
        representative_vehicles=["比亚迪汉", "比亚迪唐", "海豹", "宋L", "腾势N7"],
        standard_labels=["DiLink座舱", "自适应旋转Pad", "安卓车机生态", "四音区语音交互", "车载KTV"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向年轻客户展示：‘屏幕能自动旋转，停车等人的时候竖屏刷抖音、横屏看大片，全家一起车内K歌，娱乐性满分！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 11. 天神之眼高阶智能驾驶辅助系统 (DiPilot)
    TechnologyEntity(
        id="byd_gods_eye",
        name="比亚迪天神之眼高阶智驾系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD God's Eye Advanced Intelligent Driving System",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="自研高阶领航辅助驾驶系统",
        aliases=[
            "天神之眼",
            "天神之眼智驾",
            "dipilot",
            "dipilot100",
            "dipilot300",
            "bas3.0",
            "比亚迪智驾",
            "城市领航",
        ],
        summary="比亚迪自研整车级高阶智能驾驶系统，基于中央计算平台与感知融合算法，实现高速NOA与城市NOA领航辅助。",
        description=(
            "天神之眼（BAS 3.0+）融合英伟达Orin-X高算力芯片、多颗激光雷达、毫米波雷达及高清相机，"
            "打通智驾与云辇底盘、整车驱动控制系统，实现路面预瞄、红绿灯自主通行、全场景自动泊车与代客泊车。"
        ),
        technical_principles=[
            "整车级多域融合中央计算架构架构",
            "BEV空间感知融合与OCC占用网络",
            "智驾算法与云辇悬架底盘毫秒级联动协同控制",
        ],
        advantages=[
            "智驾与底盘深度融合，过减速带和变道姿态极稳",
            "泊车能力强，支持断头路与极窄车位全自动泊入",
        ],
        limitations=[
            "无图城市NOA开城节奏相比新势力头部梯队推进稍慢",
        ],
        sub_variants={
            "DiPilot 100": "高速领航辅助（高快NOA）",
            "DiPilot 300": "城市领航辅助（全场景城市NOA+激光雷达）",
        },
        representative_vehicles=["腾势N7", "腾势Z9GT", "仰望U8", "比亚迪汉EV天神之眼款", "海狮07 EV"],
        standard_labels=["天神之眼", "DiPilot", "城市NOA", "高速领航", "激光雷达智驾", "底盘智驾联动"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "纠正‘比亚迪只有三电没有智驾’的刻板印象：天神之眼是整车级智驾，不仅能自主变道超车，还能提前预判坑洼主动调软底盘！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 12. 双枪超充技术
    TechnologyEntity(
        id="byd_dual_gun_charging",
        name="比亚迪双枪超充技术",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD Dual-Gun Supercharging Technology",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="公共快充桩电流翻倍快充方案",
        aliases=[
            "双枪超充",
            "双枪充电",
            "双枪快充",
            "两把枪充电",
            "腾势双枪",
        ],
        summary="利用车身左右两个充电口同时插入两根充电枪，将公共快充桩电流叠加翻倍，让普通快充桩瞬间变身超充桩。",
        description=(
            "比亚迪首创双枪并联快充技术，车端配备双充电机与双升压逆变架构。即使在老旧低功率公共快充桩上，"
            "通过同时插入两把普通快充枪，即可实现最大230kW的超快充功率，15分钟补能350公里。"
        ),
        technical_principles=[
            "双路独立高压充电回路与中央分流BMS控制",
            "动态负载电流自动平衡算法，防止单路桩端跳闸",
        ],
        advantages=[
            "不依赖车企自建专属高成本超充桩，全国数百万根公共国标桩均可享受超充",
            "充电功率翻倍，服务区排队补能时间大幅压缩",
        ],
        limitations=[
            "高峰期占用两个公共充电车位，需遵守充电站规范",
        ],
        sub_variants={},
        representative_vehicles=["腾势D9 EV", "腾势N7", "方程豹豹8"],
        standard_labels=["双枪超充", "公共桩升速", "双路快充", "快速补能", "不挑桩"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "解决长途自驾痛点：‘不用专门去找专用的800V超充桩，普通高速服务区插两根枪就是超充，别人充一辆的时间你已经满电出发！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 13. 全场景智能脉冲自加热技术
    TechnologyEntity(
        id="byd_pulse_heating",
        name="比亚迪全场景全气候脉冲自加热技术",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD All-Scenario Pulse Self-Heating Technology",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="动力电池极速内自加热技术",
        aliases=[
            "脉冲自加热",
            "电池脉冲加热",
            "全气候脉冲自加热",
            "极寒脉冲加热",
        ],
        summary="通过高频充放电脉冲电流激发电池电芯内部电化学产热，使电池在-30℃极寒环境下实现极速自升温和满功率快充。",
        description=(
            "传统电池加热依赖外部液冷板PTC导热，热传导效率低且耗电大。脉冲自加热利用电机控制器与电池之间的谐振高频脉冲电流，"
            "直接让电芯内部均匀发热，升温速率达传统外加热的数倍，极大改善极寒冬季充放电性能。"
        ),
        technical_principles=[
            "电机定子绕组与电池构成LC高频谐振回路",
            "电芯本征内阻热效应均匀内发热",
            "BMS高频采样保护各单体电压不超上限",
        ],
        advantages=[
            "升温速度提升230%，电池由内而外受热均匀无温差衰减",
            "极寒冬季充电时间缩短40%，续航保持率大幅提升",
        ],
        limitations=[
            "极寒驻车状态启动自加热需消耗少量电池启动电量",
        ],
        sub_variants={},
        representative_vehicles=["海狮07 EV", "腾势Z9GT", "仰望U8"],
        standard_labels=["脉冲自加热", "极寒充电优化", "电芯内加热", "冬季续航保障"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "北方客户极力推荐：冬天在东北零下20度，电池自己从内部脉冲秒热，再也不用像老电车那样在充电桩前干等预热半小时！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 14. iTAC 智能扭矩控制系统
    TechnologyEntity(
        id="byd_itac",
        name="比亚迪 iTAC 智能扭矩控制系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD iTAC Intelligent Torque Adaptation Control",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="电驱动直接扭矩矢量防滑控制",
        aliases=[
            "itac",
            "itac系统",
            "智能扭矩控制系统",
            "itac扭矩控制",
        ],
        summary="超越传统轮速传感器的电机级防滑技术，毫秒级预测车轮打滑趋势并自适应调节扭矩输出，实现冰雪路面极速脱困与稳定行驶。",
        description=(
            "传统ESP依赖轮速传感器检测转速差，感知延迟通常达数十毫秒。iTAC通过电机旋变传感器直接读取电机角速度变化，"
            "提前50毫秒预判车轮滑移趋势，通过扭矩转移、回拨扭矩甚至反向负扭矩快速恢复抓地力。"
        ),
        technical_principles=[
            "电机旋变传感器毫秒级微小转速波动监测",
            "多自由度车辆动力学滑移率动态预估",
            "驱动电机微秒级扭矩调节无需频繁启动液压刹车",
        ],
        advantages=[
            "在冰雪、湿滑路面起步不打滑、过弯不推头甩尾",
            "介入无机械刹车打齿震动，过程如丝般平顺自然",
        ],
        limitations=[
            "主要发挥在四驱与高性能双电机车型上",
        ],
        sub_variants={},
        representative_vehicles=["海豹四驱性能版", "腾势N7", "宋L四驱版"],
        standard_labels=["iTAC", "防打滑控制", "电机旋变传感", "冰雪稳定性", "扭矩矢量控制"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "针对雨雪天气较多地区的客户：‘冬天雨雪路面大脚踩电门，车子依然走直线不摆尾，比传统机械ESP快了几十倍，安全感拉满！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 15. 十二合一智能电动力总成
    TechnologyEntity(
        id="byd_twelve_in_one_motor",
        name="比亚迪十二合一智能电动力总成",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD 12-in-1 Intelligent Electric Powertrain",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="超高度集成纯电电驱总成",
        aliases=[
            "十二合一电驱",
            "12合一电驱",
            "12合1电动力总成",
            "23000转电机",
        ],
        summary="全球首款量产十二合一电驱动总成，集成电机、减速器、碳化硅电控及车载充配电核心部件，电机转速高达23000rpm。",
        description=(
            "在行业八合一电驱基础上进一步融合了BMS、高低压DC-DC、车载OBC、高压配电箱及智能升压模块，"
            "实现功率密度提升40%，整车机舱空间节省20%，电机峰值转速突破23000rpm，极速表现与能耗均大幅领先。"
        ),
        technical_principles=[
            "多域集成三维立体拓扑架构设计",
            "超薄低铁损高耐压硅钢片与高速动平衡转子",
        ],
        advantages=[
            "功率密度高达3.2kW/kg，极致紧凑轻量化",
            "极速更高（搭载车型极速轻松突破225km/h）且NVH电磁啸叫大幅降低",
        ],
        limitations=[
            "制造精度与散热密封工艺极其严苛",
        ],
        sub_variants={},
        representative_vehicles=["海狮07 EV", "海豹EV 2025款"],
        standard_labels=["十二合一电驱", "23000rpm电机", "高功率密度", "电驱动总成", "微型化机舱"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向追求极速与动力效率的客户讲解：‘电机转速高达23000转，不仅起步快，高速120km/h以上再加速依然推背感强烈！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 16. 八合一电动力总成 (Original Base)
    TechnologyEntity(
        id="byd_eight_in_one_motor",
        name="比亚迪八合一电动力总成",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD 8-in-1 Electric Powertrain",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="高集成电驱三电系统",
        aliases=[
            "八合一电驱",
            "8合1电驱",
            "8合一电动力总成",
            "byd 8-in-1",
        ],
        summary="全球首款量产深度集成的八合一电动力总成，融合驱动电机、减速器、电机控制器及充配电核心部件，综合效率超89%。",
        description=(
            "八合一总成集成了驱动电机、减速箱、电机控制器、PDU配电盒、DC-DC转换器、OBC车载充电机、VCU整车控制器及BMS电池管理器，"
            "消除大量线束接插件，大幅减轻系统重量，综合效率达到行业标杆水平。"
        ),
        technical_principles=[
            "多合一铝合金共壳体集成制造",
            "全功能主被动安全监控集成在VCU/MCU主控板",
        ],
        advantages=[
            "体积重量大幅减轻16%，故障率显著降低",
            "整车电耗更低，释放车内实用空间",
        ],
        limitations=[
            "单体集成度高，单个附件损坏需专业售后总成检测",
        ],
        sub_variants={},
        representative_vehicles=["海豚", "元PLUS", "海鸥", "海豹"],
        standard_labels=["八合一电驱", "高集成电动力", "超轻量化", "低电耗"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "突出集成化带来的高可靠性：线束减少一半，接插件减少上百个，故障点更少、能耗更低更耐用。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 17. 宽温域高效热泵系统
    TechnologyEntity(
        id="byd_broad_temp_heat_pump",
        name="比亚迪宽温域高效热泵系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD Wide-Temperature Range Efficient Heat Pump System",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="全气候智能冷媒直热综合热管理",
        aliases=[
            "宽温域热泵",
            "比亚迪热泵",
            "冷媒直冷直热",
            "十一通阀热泵",
        ],
        summary="支持-30℃至60℃宽温域工作的高效热泵空调系统，深度回收电机与电池余热，极寒冬天暖风不再消耗大量电量。",
        description=(
            "采用环保冷媒直接对电池和乘员舱进行冷却与加热，突破了传统热泵在-10℃以下制热衰减的物理极限，"
            "在-30℃极寒天气下依然能稳定高效运行，将电能用于驱动车辆，提升低温续航达20%。"
        ),
        technical_principles=[
            "十一通阀集成式冷媒分配模块",
            "双级压缩及闪发补气增焓技术",
            "乘员舱、电池与电驱余热深度跨域调度",
        ],
        advantages=[
            "采暖COP能效比达2-3倍于传统PTC电阻丝加热",
            "显著改善纯电车冬天开空调不敢跑高速的里程缩水焦虑",
        ],
        limitations=[
            "管路与多通阀结构复杂度高",
        ],
        sub_variants={},
        representative_vehicles=["海豹", "海狮07 EV", "元PLUS", "腾势N7"],
        standard_labels=["宽温域热泵", "冷媒直冷直热", "冬季续航提升", "余热回收", "低温制热"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "消除冬天不敢开暖风的顾虑：‘比亚迪全系标配宽温域热泵，零下20度暖风随便吹，不用心疼电量掉得快！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 18. 云辇-C 智能阻尼车身控制系统
    TechnologyEntity(
        id="byd_super_chassis_yunnian_c",
        name="比亚迪云辇-C 智能阻尼车身控制系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD DiSus-C Intelligent Damping Body Control System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="连续可变电磁阀阻尼可调悬架",
        aliases=[
            "云辇-c",
            "云辇c",
            "disus-c",
            "云辇cdc",
            "智能阻尼悬架",
        ],
        summary="通过高频电磁阀无级调节减振器阻尼力，毫秒级自适应调节软硬，实现‘平路兼顾舒适，过弯兼顾支撑’。",
        description=(
            "云辇-C通过加速度传感器与控制单元实时监控车身运动，对电磁减振阀进行毫秒级无级调节。"
            "遇到细碎颠簸时阻尼变软吸收震动，高速急转弯或急刹时阻尼变硬提供强有力支撑，抑制车辆推头与侧倾。"
        ),
        technical_principles=[
            "外置或内置式无级电磁可调减振器阀芯",
            "垂向加速度传感器闭环反馈",
        ],
        advantages=[
            "性价比极高，普及到20万级大众主流车型",
            "大幅提升后排家庭乘员防晕车能力",
        ],
        limitations=[
            "无法调整车身离地间隙（高度不变）",
        ],
        sub_variants={},
        representative_vehicles=["比亚迪汉", "比亚迪唐", "海豹", "宋L", "腾势D9"],
        standard_labels=["云辇-C", "CDC连续阻尼", "电磁悬架", "防眩晕底盘", "毫秒级调节"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向追求乘坐品质的家庭客户说明：‘过减速带不颠簸，刹车不点头，家里老人孩子坐后排不晕车！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 19. 云辇-A 智能空气车身控制系统
    TechnologyEntity(
        id="byd_yunnian_a_double_chamber",
        name="比亚迪云辇-A 智能空气车身控制系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD DiSus-A Intelligent Air Body Control System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="智能多腔空气悬架车身系统",
        aliases=[
            "云辇-a",
            "云辇a",
            "disus-a",
            "双腔空簧",
            "智能空气悬架",
            "随动侧翼支撑",
        ],
        summary="结合单/双腔空气弹簧与连续阻尼可调减振器的高阶悬架系统，具备高度与刚度多挡可调及座椅随动侧翼主动包裹功能。",
        description=(
            "云辇-A拥有高达150mm以上车身高度调节行程，支持刚度双腔切换与迎宾主动降低。"
            "独创多系统协同联动，过弯时座舱侧翼支撑气囊随动充气主动夹紧驾驶员身体，带来极致人车合一体感。"
        ),
        technical_principles=[
            "大容量空气弹簧与封闭式双向空气压缩供气系统",
            "座椅侧翼充气气囊与转向角、侧向G值算法毫秒级联动",
        ],
        advantages=[
            "高级豪华质感如履平地，上下车及高速巡航自动调节高度降低风阻",
            "极限驾驶下座椅主动包裹身体，抗侧倾体验无与伦比",
        ],
        limitations=[
            "气囊与气泵系统在极寒或极端越野下需注意防尘防撞保护",
        ],
        sub_variants={"云辇-A单腔版": "腾势N7搭载", "云辇-A双腔版": "腾势Z9GT搭载"},
        representative_vehicles=["腾势N7", "腾势Z9GT"],
        standard_labels=["云辇-A", "空气悬架", "双腔空簧", "迎宾模式", "随动侧翼支撑"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "对比BBA豪华空气悬架：‘不仅悬架能升降调软硬，过弯时座椅侧翼还会自动充气抱住你的腰，豪华与操控兼得！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 20. 云辇-P 智能液压车身控制系统
    TechnologyEntity(
        id="byd_yunnian_p_hydraulic",
        name="比亚迪云辇-P 智能液压车身控制系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD DiSus-P Intelligent Hydraulic Body Control System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="主动高压液压多级刚度越野车身控制",
        aliases=[
            "云辇-p",
            "云辇p",
            "disus-p",
            "智能液压车身控制",
            "三级刚度调节",
            "200mm悬架行程",
        ],
        summary="全球首款硬派越野专属智能液压车身控制系统，支持四轮联动平衡、三级刚度调节与高达200mm行程举升。",
        description=(
            "云辇-P采用重型高压液压减振架构，具备四轮液压油路互联与多级充氮蓄能器。"
            "可在飞坡落地瞬间瞬时切换至第三级极限防触底超高刚度，承受整车飞跃落地冲击，并在交叉轴越野时实现四轮抓地平衡。"
        ),
        technical_principles=[
            "高压液压双向泵站与四轮交叉互联管路",
            "一级至三级复合蓄能器机械液压刚度跳变",
        ],
        advantages=[
            "越野抗冲击极限极高，支持1.5米跌落防触底",
            "涉水深度大幅举升，平稳通过极限交叉轴深坑",
        ],
        limitations=[
            "液压管路阀件重量较大，成本极高",
        ],
        sub_variants={},
        representative_vehicles=["仰望U8", "方程豹豹8"],
        standard_labels=["云辇-P", "液压悬架", "四轮联动", "三级刚度", "硬派越野", "防飞坡触底"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向硬派越野玩家介绍：‘飞坡落地不磕底，车轮离地自动补油压贴紧地面，城市开如魔毯，野外开如坦克！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 21. 云辇-X 全主动车身控制系统
    TechnologyEntity(
        id="byd_yunnian_x_full_active",
        name="比亚迪云辇-X 全主动智能车身控制系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD DiSus-X Fully Active Body Control System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="全主动电驱液压车身控制超跑底盘",
        aliases=[
            "云辇-x",
            "云辇x",
            "disus-x",
            "全主动悬架",
            "原地起跳",
            "单轮行驶",
            "0侧倾",
        ],
        summary="比亚迪顶尖全主动车身控制系统，单轴举升速率达500mm/s，可实现车辆原地起跳、全速过弯0侧倾与三轮安全行驶。",
        description=(
            "云辇-X集合了双目立体预瞄视觉、主动电驱大功率液压执行器及中央大脑，直接对各车轮施加独立的垂向升降力。"
            "彻底脱离被动吸收路面颠簸，实现车身与路面物理颠簸完全解耦，甚至支持超跑原地垂直跳起及单轮脱落后平稳行驶。"
        ),
        technical_principles=[
            "大功率伺服电机高压电驱液压一体泵",
            "路面3D点云预瞄与主动作动力正反向施加",
        ],
        advantages=[
            "实现物理意义上的‘过弯0侧倾、急刹0俯仰’",
            "在单轮发生不可逆损毁时，通过三轮自平衡继续安全行车",
        ],
        limitations=[
            "能耗较高且制造成本极其昂贵，专用于顶级旗舰超跑",
        ],
        sub_variants={},
        representative_vehicles=["仰望U9"],
        standard_labels=["云辇-X", "全主动悬架", "0侧倾", "原地起跳", "三轮平衡", "电驱液压主动底盘"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "展示仰望U9跳舞跳起和赛道0侧倾视频，证明中国自研底盘技术已经超越国外老牌百万超跑！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 22. DiLink AR-HUD 超大画幅抬头显示
    TechnologyEntity(
        id="byd_hud_ar",
        name="比亚迪 AR-HUD 增强现实抬头显示系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD AR-HUD Augmented Reality Head-Up Display",
        category=TechCategory.COCKPIT_OS,
        subcategory="智能前风挡光学车道级投影交互",
        aliases=[
            "byd ar-hud",
            "比亚迪ar-hud",
            "arhud",
            "50英寸ar-hud",
            "车道级hud",
        ],
        summary="投射距离达7.5米、等效50英寸以上的车道级AR增强现实抬头显示，将导航转向指引与智驾预警直接贴合真实路面。",
        description=(
            "基于自主光学曲面镜模组与图形算法，在驾驶员视线前方投射清晰的3D实景融合导航箭头、前车跟车距离警示及盲区变道预警，"
            "彻底免除低头看仪表或中控导航带来的驾驶安全分心隐患。"
        ),
        technical_principles=[
            "自由曲面反射镜光学抗畸变矫正算法",
            "IMU与智驾视觉车道线实时空间标定贴合",
        ],
        advantages=[
            "大画幅、超强抗眩光（阳光直射清晰可见）",
            "导航箭头直接画在前方真实转弯车道上，绝不走错岔道口",
        ],
        limitations=[
            "强逆光极端工况下投影对比度略受考验",
        ],
        sub_variants={},
        representative_vehicles=["腾势N7", "腾势Z9GT", "仰望U8", "宋L"],
        standard_labels=["AR-HUD", "车道级导航", "增强现实投影", "安全不低头"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向注重安全与科技感的客户展示：‘眼睛看着路面就行，哪个路口要转弯路面上直接标大箭头，再也不怕复杂立交桥走错路！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 23. 全场景数字钥匙 (NFC + UWB)
    TechnologyEntity(
        id="byd_smart_entry_nfc_uwb",
        name="比亚迪全场景数字车钥匙技术",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD All-Scenario Digital Car Key (NFC & UWB)",
        category=TechCategory.COCKPIT_OS,
        subcategory="无感智能进出与解闭锁技术",
        aliases=[
            "nfc车钥匙",
            "uwb车钥匙",
            "比亚迪手机钥匙",
            "后视镜nfc",
            "无感开门",
            "没网没电开门",
        ],
        summary="业内首创后视镜NFC刷卡开门并全面升级UWB厘米级无感迎宾解闭锁，手机没电没网也能刷开上车启动。",
        description=(
            "集成后视镜集成式NFC天线与多节点UWB超宽带射频锚点。不仅支持主流苹果、华为、小米等全生态手机/手表触碰开门，"
            "即使手机关机彻底没电数小时内依然能正常刷卡开锁，UWB更支持揣在兜里靠近车辆自动解锁并点亮迎宾光毯。"
        ),
        technical_principles=[
            "NFC近场磁场感应与安全SE安全芯片加密通信",
            "ToF飞行时间测距UWB天线矩阵精确到厘米级定位防中继攻击",
        ],
        advantages=[
            "彻底告别传统实体车钥匙，全家权限手机一键远程分享",
            "手机即使停机、没网、关机没电依然能顺利开锁发动车辆",
        ],
        limitations=[
            "部分老旧千元安卓机可能缺失UWB芯片，需通过NFC或蓝牙进出",
        ],
        sub_variants={},
        representative_vehicles=["比亚迪汉", "比亚迪唐", "海豹", "秦L", "仰望U8"],
        standard_labels=["数字钥匙", "NFC钥匙", "UWB无感解锁", "没电开锁", "后视镜刷卡"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向家庭客户说明便利性：‘出门不用带任何车钥匙，手机哪怕彻底没电关机了，贴一下后视镜也能上车开走，绝对不掉链子！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 24. VTOL 移动电站与 VTOV 对车充放电技术
    TechnologyEntity(
        id="byd_vtov_vtol",
        name="比亚迪 VTOL 移动电站与对车放电技术",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD VTOL (Vehicle to Load) & VTOV (Vehicle to Vehicle) Power Tech",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高功率双向逆变移动放电技术",
        aliases=[
            "vtol",
            "vtov",
            "对外放电",
            "移动电站",
            "对外放电6kw",
            "车对车充电",
            "露营放电",
        ],
        summary="最大支持6kW以上超大功率车外放电与对外车充，随时化身户外超级移动充电宝，轻松驱动大功率露营厨电甚至电焊机。",
        description=(
            "利用双向OBC车载充电机及电机电控逆变电路，输出220V标准工频正弦波交流电。"
            "不仅能带动电磁炉、电烤箱、咖啡机、投影仪等露营设备，还能通过专用线缆对半路没电的抛锚友车进行救援充电（VTOV）。"
        ),
        technical_principles=[
            "双向半桥/全桥高频逆变拓扑电路",
            "整车BMS设定电量防过放安全锁止阈值",
        ],
        advantages=[
            "放电功率达6kW，市面大部分插排和工业设备轻松驱动",
            "自驾露营体验跃升，野外吃火锅吹空调生活品质大幅改善",
        ],
        limitations=[
            "大功率持续放电需留意预留返程安全续航电量",
        ],
        sub_variants={},
        representative_vehicles=["比亚迪唐", "汉", "方程豹豹5", "腾势D9", "元PLUS"],
        standard_labels=["VTOL外放电", "移动电站", "VTOV救援放电", "露营神器", "220V交流电源"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向喜欢户外和全家露营的客户介绍：‘周末带全家去野外，不用带发电机，直接用车上的电吃火锅、煮咖啡、看露天电影，太惬意了！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 25. 易三方三电机独立驱动与后轮双电机转向平台
    TechnologyEntity(
        id="byd_e3_platform",
        name="比亚迪易三方整车智能控制平台",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD e3 Tri-Motor Intelligent Driving Platform",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="三电机独立电驱与双后轮协同独立转向",
        aliases=[
            "易三方",
            "易三方技术",
            "e3平台",
            "三电机独立驱动",
            "后轮双电机转向",
            "圆规掉头",
            "腾势z9gt易三方",
        ],
        summary="全球首款整车智电融合三电机独立驱动平台，前单电机+后双电机配合后轮双电机独立转向，支持圆规掉头与极致灵动泊车。",
        description=(
            "易三方技术打破了传统机械结构束缚，后轮搭载两个独立转向电机与两个驱动电机，后轮转向角度达双向±10°且可同向或反向独立偏转。"
            "实现转弯半径仅4.62米的‘圆规掉头’、极窄断头路内八字易三方泊车以及高速爆胎毫秒级车身稳定控制。"
        ),
        technical_principles=[
            "后轴双电机独立驱动+双电机独立转向四维执行机构",
            "整车运控架构（VMC）与算法超算毫秒级融合分配",
        ],
        advantages=[
            "近5.2米长的大型豪华旗舰轿车转弯半径比紧凑型A0级小车还小",
            "支持‘圆规掉头’（前轮锁止为圆心，后轮绕前轮旋转掉头）",
        ],
        limitations=[
            "底盘后轴高度集成度极高，机械制造精度与成本严苛",
        ],
        sub_variants={},
        representative_vehicles=["腾势Z9GT", "腾势Z9"],
        standard_labels=["易三方", "三电机独立驱动", "后轮双电机独立转向", "圆规掉头", "极小转弯半径"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向看重操控和大车灵活性的商务/家庭客户演示：‘车长近5米2，转弯掉头比飞度还小，断头路一把自动泊进去，开起来极其轻盈！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 26. 腾势帝瓦雷剧院级音响系统
    TechnologyEntity(
        id="byd_devialet_sound",
        name="比亚迪腾势帝瓦雷剧院级音响系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD Denza Devialet Theater Sound System",
        category=TechCategory.COCKPIT_OS,
        subcategory="法国帝瓦雷顶级声学联合调校系统",
        aliases=[
            "帝瓦雷音响",
            "腾势帝瓦雷",
            "devialet",
            "帝瓦雷声学",
            "升降扬声器",
        ],
        summary="比亚迪与法国声学殿堂品牌帝瓦雷联合定制打造的豪华车载音响，具备超低超重低音与升降声学高音单元。",
        description=(
            "采用帝瓦雷独家SAM扬声器主动匹配技术与SPACE空间环绕声渲染算法，车内配备超大功率低音炮与全景扬声器，"
            "低音下潜深度达20Hz级，中高音清脆通透，重现巴黎歌剧院级震撼声场体验。"
        ),
        technical_principles=[
            "SAM（Speaker Active Matching）声学闭环反馈算法",
            "高功率车载功放与中控台升降式帝瓦雷高音发声单元",
        ],
        advantages=[
            "低频震撼有力且无任何失真杂音，人声层次感极佳",
            "启动时中控高音扬声器优雅升起，仪式感拉满",
        ],
        limitations=[
            "仅搭载于腾势等高端豪华序列车型",
        ],
        sub_variants={},
        representative_vehicles=["腾势N7", "腾势Z9GT", "腾势D9"],
        standard_labels=["帝瓦雷音响", "车载声学", "SAM技术", "升降高音单元", "杜比全景声"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "上车播放一段无损音乐给追求品质的客户试听：‘这是法国国宝级帝瓦雷音响，家里买一台帝瓦雷都要几万块，车里直接标配全套剧院系统！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 27. 仰望碳陶制动盘与六活塞运动卡钳系统
    TechnologyEntity(
        id="byd_carbon_ceramic_brake",
        name="比亚迪碳陶瓷复合制动盘系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD Carbon Ceramic Matrix Brake System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="赛道级轻量化耐高温制动系统",
        aliases=[
            "碳陶刹车",
            "碳陶制动盘",
            "仰望刹车",
            "六活塞卡钳",
            "赛道级制动",
        ],
        summary="采用碳纤维增强碳化硅复合材质超大制动盘，耐热温度突破1000℃，抗热衰退极强且簧下减重显著。",
        description=(
            "专为大马力超跑与大型高性能SUV研发，前盘直径达400mm以上，搭配固定式对向多活塞高刚性铝合金卡钳。"
            "连续多次100-0km/h极进制动零热衰退，刹车盘寿命大幅超越传统灰铸铁盘，有效抑制高温刹车点头与制动力疲软。"
        ),
        technical_principles=[
            "碳化硅陶瓷基复合材料（C/SiC）高温烧结成型",
            "内部螺旋定向空气冷却风道与打孔排屑散热设计",
        ],
        advantages=[
            "极耐高温不起火不衰减，100-0km/h制动距离短至32米级",
            "四个刹车盘累计减重超20公斤，显著降低簧下质量改善操控悬架响应",
        ],
        limitations=[
            "极寒初段未暖盘时刹车摩擦系数略需适应，单套维护更换成本高",
        ],
        sub_variants={},
        representative_vehicles=["仰望U9", "仰望U8豪华版", "腾势Z9GT首发版"],
        standard_labels=["碳陶制动盘", "六活塞卡钳", "赛道级制动", "超短刹车距离", "簧下减重"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向追求极速性能与赛道驾驶的买家说明：‘就算在赛道里连续跑几十圈，刹车踏板脚感依然坚挺如初，没有一点热衰退！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 28. 比亚迪智能驾驶车载预瞄路况感知系统
    TechnologyEntity(
        id="byd_road_preview_sensing",
        name="比亚迪全地形路面预瞄感知系统",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD Road Preview Surface Sensing System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="双目立体视觉与悬架前馈融合控制",
        aliases=[
            "路面预瞄",
            "双目预瞄",
            "全地形预瞄",
            "前馈减振",
            "魔毯预瞄",
        ],
        summary="通过车顶双目立体视觉相机以15米超前距离扫描路面起伏坑洼，提前给云辇悬架发送前馈调节指令平稳过坎。",
        description=(
            "传统悬架是在车轮压过减速带‘感觉到振动’后才被动调节阻尼，而路面预瞄系统以每秒上百帧的高精度3D深度视觉，"
            "提前测量前方路面凸起、井盖与坑洼高度，在车轮触碰障碍前的数毫秒内主动抬升车轮或调软阻尼，如履平地。"
        ),
        technical_principles=[
            "高动态双目立体视觉微距深度点云匹配算法",
            "车速传感器与悬架执行器前馈时间延迟精准补偿",
        ],
        advantages=[
            "将车身颠簸冲击加速度降低50%以上，过减速带车身几乎平稳不动",
            "避免夜间或阴雨天看不清路障导致托底或爆胎风险",
        ],
        limitations=[
            "大雾、暴雪严重遮挡风挡时视觉预瞄精度会适度降级",
        ],
        sub_variants={},
        representative_vehicles=["腾势N7", "腾势Z9GT", "仰望U8"],
        standard_labels=["路面预瞄", "双目立体视觉", "前馈悬架控制", "如履平地", "减速带平稳"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "在试驾时带客户过减速带：‘看前方这排减速带，车顶双目已经看清了，悬架自动提前化解冲击，车内水杯里的咖啡一滴都不会洒出来！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 29. 方程豹非承载式CTC防扭车架大梁
    TechnologyEntity(
        id="byd_fangchengbao_ctc_chassis",
        name="比亚迪方程豹 CTC 越野安全车架大梁",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD Fangchengbao CTC Off-Road Ladder Frame",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="硬派越野电池车架深度集成安全拓扑",
        aliases=[
            "方程豹大梁",
            "ctc大梁",
            "越野车架",
            "高强钢梯形车架",
            "非承载车身大梁",
        ],
        summary="采用96%高强钢打造的梯形非承载式车架，将动力电池深嵌在大梁内部作为承载构件，整车扭转刚度高出传统越野车38%。",
        description=(
            "彻底重塑传统硬派越野底盘构造，将刀片电池作为车架横纵梁的核心抗扭成员，电池包下部配备三层超高强度抗磨冲压防护板。"
            "有效杜绝极端岩石攀爬与交叉轴扭曲引起的车身异响和电池挤压变形变形风险。"
        ),
        technical_principles=[
            "大截面冷拔等强抗扭梯形梁架构",
            "多点橡胶隔振大衬套将车架振动与乘员舱完全物理隔离",
        ],
        advantages=[
            "车架扭转刚度突破40000 N·m/deg，颠簸烂路绝不咯吱异响",
            "电池包离地间隙大且被高强双层钢梁全包裹保护，极端越野零磕碰风险",
        ],
        limitations=[
            "车身重心虽较传统燃油越野低，但整备质量依然超过2.8吨",
        ],
        sub_variants={},
        representative_vehicles=["方程豹豹5", "方程豹豹8"],
        standard_labels=["CTC车架大梁", "非承载式车身", "梯形大梁", "防扭安全", "越野防托底"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "让客户蹲下看底盘大梁：‘看看这粗壮的双层高强钢大梁，电池深藏在中间，底部有加厚装甲，去野外哪怕底盘磕大石头也伤不到电池分毫！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 30. 骁云插混专用高热效率发动机
    TechnologyEntity(
        id="byd_xiaoyun_engine",
        name="比亚迪骁云插混专用发动机",
        brand="比亚迪 (BYD)",
        brand_key="byd",
        english_name="BYD Xiaoyun Plug-in Hybrid Dedicated Engine",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="插电混动专用高能效内燃机动力总成",
        aliases=[
            "骁云发动机",
            "骁云1.5l",
            "骁云1.5t",
            "插混专用发动机",
            "高热效率发动机",
            "阿特金森循环发动机",
        ],
        summary="专为DM-i/DM-p超级混动定制研发的高热效率发动机家族，取消传统轮系皮带，热效率全面突破43%-46%。",
        description=(
            "骁云发动机摒弃传统机械水泵、皮带轮与发电机，全附件实现电动化解耦。采用阿特金森循环、高滚流进气道、"
            "高达15.5:1至16:1的超高压缩比以及低摩擦活塞涂层技术，工作时长期稳定运行在最省油的黄金高效工况区间。"
        ),
        technical_principles=[
            "全附件电动化（电动水泵、电空调压缩机、无轮系皮带）",
            "深阿特金森循环配合EGR废气再循环率超25%",
        ],
        advantages=[
            "长期处于最高热效率转速区间充当发电机，远离低效工况",
            "机械磨损极小，维护保养成本极低，寿命长久可靠",
        ],
        limitations=[
            "低转速扭矩较弱，必须配合大功率P1/P3驱动电机协同做功",
        ],
        sub_variants={
            "骁云1.5L自然吸气": "热效率43.04%-46.06%，主打秦/海豹系列极致节油",
            "骁云1.5Ti涡轮增压": "热效率40%以上，兼顾大车型高负荷动力储备（汉/唐/方程豹）",
        },
        representative_vehicles=["秦L", "海豹06", "汉DM-i", "唐DM-p", "宋Pro DM-i"],
        standard_labels=["骁云发动机", "插混专用", "高热效率", "阿特金森循环", "无皮带轮系", "超低油耗"],
        equivalence_group_id=EquivalenceDomain.HYBRID_POWERTRAIN_SYSTEM,
        sales_talking_points=[
            "向对比传统燃油车的客户讲清楚原理：‘传统汽车发动机在市区走走停停效率只有20%，而骁云发动机只负责发电，一直运转在最高效率点，所以油耗才能做到不可思议的2L多！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),
]

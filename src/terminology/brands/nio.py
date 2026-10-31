"""
NIO Proprietary Automotive Technology Registry (src/terminology/brands/nio.py).
Contains 30 comprehensive proprietary technologies for NIO / Onvo / Firefly ecosystems.
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

NIO_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 蔚来换电体系 (Original)
    TechnologyEntity(
        id="nio_power_swap",
        name="蔚来可充可换可升级换电网络体系 (Power Swap)",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Power Swap Network & BaaS Architecture",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="全自动极速换电与车电分离生态",
        aliases=[
            "蔚来换电",
            "蔚来换电站",
            "换电架构",
            "四代换电站",
            "power swap",
            "蔚来baas",
            "蔚来车电分离",
            "蔚来电池租用",
        ],
        summary="蔚来独树一帜的能源服务基石，全自动换电仅需3分钟，支持电池灵活升级与车电分离（BaaS）购车方案，彻底消除电池老化衰减贬值顾虑。",
        description=(
            "蔚来全系车型原生标配统一换电机构与专利水冷电气快换接口。第四代换电站配备全自动泊入与多颗激光雷达，全自动换电全程仅需约3分钟。"
            "结合BaaS（Battery as a Service）车电分离政策，购车立减数万元电池款；且车主可根据长途出行需求随时在APP中按月/按天租用大容量100度或150度固态电池。"
        ),
        technical_principles=[
            "车身专利锁止机构（数千次插拔无松动高抗疲劳设计）与自研液冷快速对接阀",
            "换电站恒温恒湿电池集中健康体检与智能梯次慢充养护网络",
        ],
        advantages=[
            "补能时间甚至比燃油车加油还快（3分钟满电复活），暴雨大雪天不下车在车内吹空调即可完成补能",
            "车主永远不用担心自己车上的电池衰减老化贬值，每次换电都是健康满血电池",
            "灵活租用电池：平时市区代步租小电池省钱，过年自驾跨省临时升级大电池",
        ],
        limitations=[
            "车身底部需要预留统一定位结构与锁止机构空间，车身轻量化与低趴度需做工程妥协",
            "换电站重资产建设投入极大，偏远三四线县市覆盖密度仍需持续铺设",
        ],
        sub_variants={
            "第三代换电站": "配备2颗激光雷达，服务能力提升至每天408次",
            "第四代换电站": "配备4颗英伟达Orin-X芯片+6颗激光雷达，支持多品牌多规格电池极速兼容换电",
        },
        representative_vehicles=["蔚来ES6", "蔚来ET5", "蔚来ET5T", "蔚来EC6", "蔚来ES8", "蔚来ET7", "乐道L60"],
        standard_labels=["全自动极速换电", "3分钟换电满电", "BaaS车电分离", "电池灵活租用升级", "电池终身无衰减顾虑"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "针对纠结电池衰减和电车开几年二手残值崩塌的客户，说明BaaS车电分离与换电网络是目前抵抗二手车电池贬值的最佳解法；",
            "对比任何快充桩，强调暴雨/寒冬天气坐在车里听歌3分钟换完电的尊贵舒适体验。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 2. 蔚来天行底盘 (Original)
    TechnologyEntity(
        id="nio_skyride",
        name="蔚来天行全主动智能底盘 (SkyRide)",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO SkyRide Full Active Chassis System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="高压电驱液压全主动悬架与线控转向",
        aliases=[
            "天行",
            "天行底盘",
            "天行全主动底盘",
            "skyride",
            "蔚来天行",
            "天行线控转向",
            "天行后轮转向",
        ],
        summary="全球首创原生集成线控转向、后轮转向与全主动悬架的“天行智能底盘”，每个车轮配备独立电驱液压泵，实现百万豪车级“香槟塔不倒、颠簸如平地”的奇迹表现。",
        description=(
            "蔚来天行底盘（搭载于旗舰轿车ET9）采用全主动悬架，直接取消了传统防倾杆，各车轮通过超高响应的45V高性能电驱液压泵执行器独立做功。"
            "调节频次与力量比空气悬架快数十倍，实现车身完全不随路面起伏晃动。同时配备全线控转向与最大8.3度后轮转向，实现极佳的低速掉头灵活性与高速平移稳健性。"
        ),
        technical_principles=[
            "45V高压全主动电驱液压执行单元（毫秒级主动推拉车轮）",
            "线控转向（Steer-by-Wire）实现方向盘与车轮机械解耦，全电信号控制与多重冗余安全备份",
        ],
        advantages=[
            "实现车头放香槟塔过连续减速带滴水不洒的极致平稳，完全抹平路面颠簸",
            "大车身具备小车般的转弯半径，停车与窄路掉头极轻松",
        ],
        limitations=[
            "软硬件架构极其复杂且高精度执行器造价极高，目前仅定位于80万级行政级旗舰车型",
        ],
        sub_variants={},
        representative_vehicles=["蔚来ET9"],
        standard_labels=["全主动悬架", "线控转向系统", "后轮大角度转向", "车身姿态绝对平稳", "天行底盘"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向高端商务接待客户展示“香槟塔过坎”视频，展现超越迈巴赫与劳斯莱斯的底盘科技巅峰水平。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 3. 蔚来天枢操作系统 (Original)
    TechnologyEntity(
        id="nio_skyos",
        name="蔚来天枢 SkyOS 整车全域操作系统",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO SkyOS Vehicle Operating System",
        category=TechCategory.COCKPIT_OS,
        subcategory="整车底层全场景分布式实时操作系统",
        aliases=[
            "天枢",
            "天枢skyos",
            "skyos",
            "天枢系统",
            "蔚来天枢",
            "整车全域操作系统",
        ],
        summary="国内首个整车全域全场景操作系统，覆盖车控、智驾、座舱及移动互联全维度，构建高带宽、低时延、高安全的新能源汽车智能数字中枢。",
        description=(
            "天枢SkyOS包含SkyOS-H（整车多媒体座舱）、SkyOS-M（轻量高安全实时车控）、SkyOS-R（智能驾驶极致低时延控制）等多个子内核。"
            "打破了传统汽车各ECU芯片烟囱式林立的壁垒，实现整车异构算力融合调度与毫秒级协同响应。"
        ),
        technical_principles=[
            "1+4+N整车全域操作系统技术架构，支持多操作系统内核混合部署",
            "自研高性能IPC通信与全链路软硬件故障隔离机制",
        ],
        advantages=[
            "全车跨域数据吞吐极大提速，OTA升级速度提升数倍且永不死机",
            "彻底掌握汽车底层代码主权，软硬件协同效率极高",
        ],
        limitations=[
            "属于底层软件工程，对终端普通消费者的直观视觉冲击力不如外显大屏UI直观",
        ],
        sub_variants={},
        representative_vehicles=["蔚来ET9", "蔚来新一代NT3.0车型"],
        standard_labels=["整车全域操作系统", "微内核高安全架构", "毫秒级实时车控", "软件定义汽车底座"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向注重底层安全性与长期软件OTA升级潜力的理性用户介绍自研底层系统的长期生命力与稳定性保障。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 4. 蔚来超感系统 Aquila
    TechnologyEntity(
        id="nio_aquila_sensor",
        name="蔚来超感系统 Aquila (NIO Aquila Super Sensing)",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Aquila Super Sensing System",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="高阶智能驾驶感知硬件系统",
        aliases=[
            "aquila",
            "蔚来aquila",
            "超感系统",
            "蔚来超感系统",
            "aquila超感系统",
            "超远距激光雷达瞭望塔",
        ],
        summary="蔚来第二代车型标配的超感硬件架构，包含超远距高精度激光雷达、800万像素高清摄像头及高位瞭望塔式布局，感知距离达500米。",
        description=(
            "Aquila超感系统拥有33个高性能感知硬件，包括1个超远距离高精度1550nm激光雷达、7个800万像素高清摄像头、4个300万像素高感光环视摄像头、"
            "5个毫米波雷达、12个超声波传感器、2个高精度定位单元及1个ADMS驾驶员状态感知摄像头，高位瞭望塔设计视野开阔无遮挡。"
        ),
        technical_principles=[
            "1550nm波长激光雷达，最远探测距离500米，对人眼安全且穿透雾霾雨雪能力强",
            "车顶瞭望塔式传感器布局，减少地面杂波反射并获得更高视角盲区缩减",
        ],
        advantages=[
            "标配全套顶级高阶感知硬件，全系一视同仁无需额外加钱选装",
            "远距离小障碍物检测精度行业领先，保障高速120km/h下的感知反应裕量",
        ],
        limitations=[
            "车顶犄角布局对风阻系数与外观低风阻流线有轻微工程影响",
        ],
        representative_vehicles=["蔚来ES6", "蔚来ET5", "蔚来ET7", "蔚来ES8", "蔚来EC7"],
        standard_labels=["Aquila超感系统", "1550nm激光雷达", "800万高清摄像头", "车顶瞭望塔布局"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "强调蔚来从入门级ET5到旗舰ES8全系标配激光雷达与33个传感器，不搞减配套路。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 5. 蔚来超算平台 Adam
    TechnologyEntity(
        id="nio_adam_supercomputing",
        name="蔚来超算平台 Adam (NIO Adam Supercomputing)",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Adam Supercomputing Platform",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="高算力智能驾驶集中式计算平台",
        aliases=[
            "adam",
            "蔚来adam",
            "超算平台",
            "蔚来超算平台",
            "adam超算",
            "1016tops",
            "四颗orin",
        ],
        summary="蔚来NT2.0全系标配的超强算力平台，搭载4颗NVIDIA Drive Orin X芯片，总算力高达1016 TOPS，实现毫秒级复杂多任务感知与规划。",
        description=(
            "Adam超算平台不仅拥有1016 TOPS超高算力，而且创新构建了完备的冗余算力体系：2颗主算力芯片运行主算法模型，"
            "1颗专用算力芯片负责群体智能与车端大模型训练，1颗独立备份芯片负责全域冗余接管，确保智能驾驶安全永不掉线。"
        ),
        technical_principles=[
            "四颗NVIDIA Orin-X芯片协同架构，总算力1016 TOPS，高带宽总线互联",
            "算力芯片独立分区部署，实现多重功能安全与容错冗余热备份",
        ],
        advantages=[
            "1016 TOPS标配算力储备极大，持续承接最新端到端大模型OTA无压力",
            "算力双冗余保障，在芯片突发故障时实现无缝安全降级停泊",
        ],
        limitations=[
            "高算力芯片功耗与散热需求较高，对整车低压电气系统及热管理要求严苛",
        ],
        representative_vehicles=["蔚来ES6", "蔚来ET5", "蔚来ET7", "蔚来ES8", "蔚来EC6"],
        standard_labels=["Adam超算平台", "1016TOPS算力", "四Orin芯片", "算力冗余备份"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "告诉注重科技保值率的用户，友商多为单颗或双颗Orin，蔚来标配四颗Orin超千TOPS算力，5年OTA算力不落伍。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 6. 蔚来神玑 NX9031 自研智驾芯片
    TechnologyEntity(
        id="nio_shenji_nx9031",
        name="蔚来神玑 NX9031 自研高阶智能驾驶芯片",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Shenji NX9031 Autonomous Driving Chip",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="高集成度车规自研高阶算力SoC",
        aliases=[
            "神玑",
            "神玑nx9031",
            "nx9031",
            "蔚来神玑",
            "蔚来自研芯片",
            "神玑芯片",
        ],
        summary="蔚来首款自研5nm车规级高阶智能驾驶芯片，拥有超500亿颗晶体管，单芯片性能可匹敌四颗业界主流旗舰芯片，首发搭载于行政旗舰ET9。",
        description=(
            "神玑NX9031采用先进制程工艺，拥有32核高性能CPU核组与自研高吞吐NPU计算引擎，集成高动态范围车规ISP图像处理器。"
            "可高效运行各类生成式大模型与端到端智驾网络，在超低时延图像处理与高并发任务处理上具备极强的算力效率。"
        ),
        technical_principles=[
            "5nm车规先进制程，高密度晶体管集成与异构多核并行计算架构",
            "自研高动态ISP（支持6.5Gpixel/s超高像素吞吐与超低图像时延）",
        ],
        advantages=[
            "单颗神玑芯片实现多颗主流芯片算力融合，降低PCB体积并显著缩减能耗",
            "软硬件垂直一体深度协同，智驾感知与规划算法直接在硬件级实现最优指令加速",
        ],
        limitations=[
            "先进制程研发流片投入巨大，首期主要搭载于高端旗舰车型",
        ],
        representative_vehicles=["蔚来ET9"],
        standard_labels=["神玑NX9031", "自研5nm芯片", "车规高阶SoC", "自研ISP影像引擎"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "对比依赖外购通用芯片的品牌，展现蔚来深厚底层硬核芯片自研实力与长期成本技术掌控力。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 7. 蔚来 Banyan 智能系统
    TechnologyEntity(
        id="nio_banyan_system",
        name="蔚来 Banyan 智能系统架构",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Banyan Smart System",
        category=TechCategory.COCKPIT_OS,
        subcategory="第二代整车智能化座舱系统",
        aliases=[
            "banyan",
            "蔚来banyan",
            "banyan系统",
            "蔚来榕树系统",
            "banyan智能系统",
        ],
        summary="蔚来NT2.0平台的整车智能系统代号，整合了座舱应用、全景声影音、底盘感知以及全车生态，提供每月持续迭代的高品质数字车生活。",
        description=(
            "Banyan系统构建在第二代智能硬件平台之上，深度融合高通骁龙8155/8295座舱芯片，具备强大的UI动效渲染、全场景连续语音识别交互、"
            "4D舒适领航智能底盘悬架预瞄联动，并通过软硬件深度融合实现了极其流畅细腻的豪华车规交互体验。"
        ),
        technical_principles=[
            "微内核分布式通信总线，跨屏幕、跨域数据高帧率零卡顿同步渲染",
            "4D舒适领航算法：根据历史路面大数据和实时激光雷达地形扫描动态调整悬架阻尼",
        ],
        advantages=[
            "OTA迭代更新频率高，持续新增功能且UI美学在行业内独树一帜",
            "底盘悬架与路面感知智能打通，过减速带及坑洼路段自动柔和滤震",
        ],
        limitations=[
            "早期版本在部分第三方App生态丰富度上保持了严格的高画质审核，扩充速度相对克制",
        ],
        representative_vehicles=["蔚来ES6", "蔚来ET5", "蔚来ET7", "蔚来ES8", "蔚来EC6", "蔚来ET5T"],
        standard_labels=["Banyan智能系统", "4D舒适领航", "车载全景声", "全域OTA迭代"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "为用户演示4D舒适领航功能，展示蔚来座舱如何与底盘联动，提前识别路面坑洼提前抬升调节悬架阻尼。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 8. 蔚来 NOMI 车载人工智能伙伴及 NOMI GPT
    TechnologyEntity(
        id="nio_nomi_gpt",
        name="蔚来 NOMI 车载人工智能助手及 NOMI GPT",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO NOMI AI Companion & NOMI GPT",
        category=TechCategory.COCKPIT_OS,
        subcategory="情感化实体车载AI交互机器人",
        aliases=[
            "nomi",
            "蔚来nomi",
            "nomi gpt",
            "nomi机器人",
            "nomi mate",
            "nomi halo",
            "车载人工智能伴侣",
        ],
        summary="全球首个量产的车载实体人工智能交互伙伴，搭载端云一体大模型NOMI GPT，具备拟人化表情反馈、声纹识别与深度多轮逻辑对话能力。",
        description=(
            "NOMI位于中控台正上方，配备可动圆形OLED屏幕与高精度舵机，能根据乘员位置转头交流并显示数十种灵动情绪表情。"
            "升级NOMI GPT大模型后，不仅支持毫秒级可见即可说的全车控制，还能解答百科、策划旅行攻略、甚至进行富有同理心的情感陪伴沟通。"
        ),
        technical_principles=[
            "多模态大语言模型（LLM）端云协同调度与汽车专属知识图谱蒸馏",
            "微型高耐用度伺服机构与情绪拟态视觉算法，实现车内乘员声源定位与视线对视",
        ],
        advantages=[
            "具有极大的人格化温度，改变了传统语音助手的冰冷机械感，深得家庭与女性乘员喜爱",
            "全车免唤醒多音区精准识别，支持连续不间断复合指令下达",
        ],
        limitations=[
            "NOMI Mate实体圆头硬件在部分低配车型上为选装件（标配为NOMI Halo光环）",
        ],
        representative_vehicles=["蔚来ES6", "蔚来ET5", "蔚来ET7", "蔚来ES8", "蔚来EC7", "蔚来ET5T"],
        standard_labels=["NOMI车载AI", "NOMI GPT大模型", "实体情感机器人", "多音区连续语音控制"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "带家属或小朋友试驾时重点演示NOMI的表情包互动与童话故事互动，客户满意度转化率极高。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 9. 蔚来 PanoCinema 全景数字座舱
    TechnologyEntity(
        id="nio_pano_cinema",
        name="蔚来 PanoCinema 全景数字座舱",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO PanoCinema Panoramic Digital Cockpit",
        category=TechCategory.COCKPIT_OS,
        subcategory="全景声学与沉浸式影音数字座舱",
        aliases=[
            "panocinema",
            "蔚来panocinema",
            "全景数字座舱",
            "蔚来7.1.4杜比全景声",
            "蔚来ar眼镜",
            "panocinema全景座舱",
        ],
        summary="蔚来软硬件一体化全感官沉浸座舱，标配23个扬声器7.1.4杜比全景声音响系统，支持定制AR/VR智能眼镜直连带来百英寸巨幕体验。",
        description=(
            "PanoCinema将声学、光学、车身震动与车内空气香氛系统深度联动。拥有1000W高功率23扬声器系统，原生支持杜比全景声音乐专区；"
            "车机原生提供AR眼镜DisplayPort高带宽低时延接口，戴上眼镜即可在车内享受等效6米201英寸的3D全高清巨幕影音。"
        ),
        technical_principles=[
            "7.1.4物理声道声学拓扑布局（7环绕+1重低音+4天空声道），自研数字信号调音算法",
            "车端高带宽DP直出与六自由度空间定位交互协议",
        ],
        advantages=[
            "全系标配顶级7.1.4杜比全景声，声场定位精准通透，行业公认第一梯队音响",
            "AR巨幕扩展方案解决了车内多块实体大液晶屏遮挡视线与眩光的弊端",
        ],
        limitations=[
            "AR眼镜需要选配专用外设眼镜硬件，部分容易晕车的乘客在行驶中使用巨幕可能略有不适",
        ],
        representative_vehicles=["蔚来ET7", "蔚来ES8", "蔚来EC7", "蔚来ES6", "蔚来ET5"],
        standard_labels=["PanoCinema全景座舱", "7.1.4杜比全景声", "AR巨幕眼镜互联", "23扬声器千瓦音响"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "在展车内播放高品质杜比全景声音频试听片段，用无可挑剔的声场层次征服音乐爱好者客户。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 10. 蔚来 BaaS 电池租用服务方案
    TechnologyEntity(
        id="nio_baas_battery_leasing",
        name="蔚来 BaaS 电池租用服务方案 (Battery as a Service)",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO BaaS (Battery as a Service)",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="车电分离商业与金融技术体系",
        aliases=[
            "蔚来baas",
            "蔚来车电分离",
            "蔚来电池租用",
            "电池租用服务",
            "租电池买车",
            "baas方案",
        ],
        summary="蔚来创新的车电分离商业模式，买车无需购买电池，立减7万或12.8万元车价，每月支付租金，享有终身免费电池质保与换电技术升级权益。",
        description=(
            "BaaS彻底解耦了车辆底盘与电池资产的所有权。车主以更低的门槛购入整车，由蔚能电池资产公司负责电池资产管理与维护。"
            "车主无需承担电池日后衰减折旧带来的二手车贬值损失，且每月租金可累计为换电积分或享受租电满额抵扣政策。"
        ),
        technical_principles=[
            "法律与资产权属分离机制，车电独立产权登记与全生命周期数字资产追踪",
            "云端电池健康监控与全天候无损梯次循环利用机制",
        ],
        advantages=[
            "大幅拉低购车首付和总门槛，75kWh电池立减7万，100kWh电池立减12.8万",
            "规避二手车因电池损耗造成的断崖式折价，二手车买家同样可继续租电",
        ],
        limitations=[
            "需按月稳定缴纳电池租金，长期持有数年后累计租金可能超过电池买断价",
        ],
        representative_vehicles=["蔚来全系车型", "乐道L60"],
        standard_labels=["BaaS电池租用", "车电分离", "购车立减7万", "二手车残值保障"],
        equivalence_group_id=None,
        sales_talking_points=[
            "为预算有限的年轻客户算账：采用BaaS方案20多万即可入手高配蔚来，月租几百元，无需担心电池寿命。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 11. 蔚来 150kWh 超长续航半固态电池包
    TechnologyEntity(
        id="nio_150kwh_battery",
        name="蔚来 150kWh 超长续航半固态电池包",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO 150kWh Ultra Long Range Semi-Solid Battery Pack",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高能量密度半固态动力电芯技术",
        aliases=[
            "150度电池",
            "150kwh电池",
            "蔚来150度固态电池",
            "150度半固态电池",
            "超长续航电池包",
            "千公里续航电池",
        ],
        summary="全球首款实现量产级商业化上车并支持换电的150kWh超大容量半固态电池包，电芯能量密度高达360Wh/kg，真实综合续航轻松突破1000公里。",
        description=(
            "该电池包采用固液混合电解质技术，能量密度处于全球动力电池第一梯队。即使容量大幅扩充至150度，其外形尺寸与重量仍严格匹配蔚来现有换电站标准规格。"
            "车主无需一次性买断高达几十万的电池包，可在春节出远门或长途自驾前在蔚来APP中按天/按月灵活临时租用升级。"
        ),
        technical_principles=[
            "固液电解质复合技术与高镍正极+硅碳负极化学体系，单体能量密度360Wh/kg",
            "超薄轻量化CTP结构与高效液冷温控管理，尺寸与标准换电箱完全兼容",
        ],
        advantages=[
            "实测高速/冬季续航超1000公里，彻底终结纯电长途自驾续航焦虑",
            "支持按天租用，日常用小电池、长途用大电池，资金利用效率最高",
        ],
        limitations=[
            "半固态电芯材料成本极高，目前主要以日租/月租灵活服务形式投放",
        ],
        representative_vehicles=["蔚来ET7", "蔚来ES6", "蔚来ET5", "蔚来ES8"],
        standard_labels=["150kWh半固态电池", "360Wh/kg能量密度", "实测续航超1000km", "换电站日租升级"],
        equivalence_group_id=EquivalenceDomain.SOLID_STATE_BATTERY_TECH,
        sales_talking_points=[
            "用李斌实测单次续航1044公里的实际案例打消长途跨省疑虑，突出平时不用买、出门按天租的超高灵活性。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 12. 蔚来 900V 全沉浸式超高压电气架构
    TechnologyEntity(
        id="nio_et9_900v_platform",
        name="蔚来 900V 全沉浸式超高压电气架构",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO 900V High Voltage Electrical Architecture",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="超千伏级全域高压电气拓扑系统",
        aliases=[
            "900v",
            "蔚来900v",
            "925v高压",
            "900v架构",
            "900v碳化硅平台",
            "全域900v",
        ],
        summary="蔚来在行政旗舰ET9上首发的全域900V超高压平台，最高工作电压高达925V，拥有全行业领先的充电倍率与整车高压线束极致减重特性。",
        description=(
            "该架构包含高压电驱、超快充电池、空调压缩机、DC-DC及换电设备全链路高压化。峰值充电功率超600kW，实现充电5分钟补能255公里；"
            "得益于925V高电压，整车高压线束截面积大幅收窄，整车线束减重数百克至数公斤，大幅提升高转速下的能量转化效率。"
        ),
        technical_principles=[
            "全栈900V器件耐压选型（SiC功率芯片耐压等级提升至1200V以上）",
            "超低内阻电芯拓扑与全液冷大倍率直充热平衡回路",
        ],
        advantages=[
            "补能极快，5分钟快速补充250km+里程，配合换电形成“超充+换电”双王炸",
            "高电压降低线路发热损耗，电机高速运转效率更高更节能",
        ],
        limitations=[
            "对公共桩兼容性需要配套专用升压模块，全域高压元器件物料成本高",
        ],
        representative_vehicles=["蔚来ET9"],
        standard_labels=["全域900V平台", "最高工作电压925V", "5分钟补能255km", "全链路SiC碳化硅"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向追求极致补能科技的用户展示：蔚来不仅有全行业独家的3分钟换电，还有高达925V的行业最高电压快充平台。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 13. 蔚来全线控转向系统
    TechnologyEntity(
        id="nio_steer_by_wire",
        name="蔚来全线控转向技术 (Steer-by-Wire)",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Steer-by-Wire (SbW) System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="完全电信号机械解耦转向架构",
        aliases=[
            "蔚来线控转向",
            "et9线控转向",
            "蔚来sbw",
            "方向盘机械解耦",
            "可变转向比线控",
        ],
        summary="彻底取消传统方向盘与转向前轮之间机械传动轴的线控转向系统，实现方向盘转角任意调配与颠簸打手路感零传递。",
        description=(
            "由电信号和冗余电机直接控制前轮转向角度。低速掉头或倒车入库时，方向盘无需交叉打满一整圈，仅转动微小角度即可实现车轮大角度偏转；"
            "高速行驶时传动比自动变大确保直线行驶沉稳不发飘；同时配备三电源、双电机、多组传感器全冗余设计，满足ASIL-D最高安全等级。"
        ),
        technical_principles=[
            "三通道硬件电气冗余与双电控转向执行电机容错仲裁机制",
            "实时可变转向比算法与路感模拟力矩反馈电机控制",
        ],
        advantages=[
            "狭窄车位停车和掉头双手无需倒手转圈，操作轻快优雅",
            "隔绝路面恶劣冲击振动，同时未来支持高阶自动驾驶时方向盘收折收拢",
        ],
        limitations=[
            "法规与成本门槛高，消费者对完全无机械连接的心理适应需时间建立信任",
        ],
        representative_vehicles=["蔚来ET9"],
        standard_labels=["全线控转向", "Steer-by-Wire", "ASIL-D高安全冗余", "随速可变转向比"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "突出线控转向是未来L3/L4自动驾驶时代座舱革命的核心配置，带来百万豪车级的开阔感与从容感。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 14. 蔚来后轮转向系统
    TechnologyEntity(
        id="nio_rear_wheel_steering",
        name="蔚来大角度后轮主动转向系统",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Active Rear Wheel Steering System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="后桥独立主动线控转向执行系统",
        aliases=[
            "蔚来后轮转向",
            "8.3度后轮转向",
            "蔚来主动后轮转向",
            "后轴转向系统",
        ],
        summary="蔚来旗舰车型配备的主动后轮转向技术，后轮最大转向角达8.3度，使得5.3米大型D级旗舰轿车拥有类似紧凑两厢车般的10.9米极小转弯直径。",
        description=(
            "在低速工况下，后轮与前轮反向偏转，显著减小转弯半径，在窄巷穿梭、地库急弯与侧方停车时如鱼得水；"
            "在高速变道或弯道超车时，后轮与前轮同向偏转，消除车辆变道甩尾滞后感，实现平稳平移滑行般的平顺姿态。"
        ),
        technical_principles=[
            "高扭矩无刷伺服电机驱动双向后轮转向拉杆机构",
            "整车动力学协调控制器（VMC）根据车速与横摆角速度实时动态计算后轮目标偏角",
        ],
        advantages=[
            "超长轴距行政轿车具备如A级小车般的窄路掉头能力",
            "高速过弯或紧急避障时车身稳定性与后排乘坐舒适度大幅飞跃",
        ],
        limitations=[
            "后轴布局复杂，挤占部分后备箱深层储物空间及后轮悬架空间",
        ],
        representative_vehicles=["蔚来ET9"],
        standard_labels=["主动后轮转向", "8.3度后转向角", "10.9米转弯直径", "高速蟹行平移变道"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "针对担心车长超5.3米不好停不好开的行政客户，强调配备8.3度后轮转向后，掉头比高尔夫还灵活。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 15. 蔚来智能双腔空气悬架系统
    TechnologyEntity(
        id="nio_air_suspension_system",
        name="蔚来智能双腔闭式空气悬架系统",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Intelligent Dual-Chamber Air Suspension System",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="多腔空气弹簧与高度/刚度自适应悬架",
        aliases=[
            "蔚来双腔空悬",
            "蔚来双腔空气悬挂",
            "闭式双腔空簧",
            "蔚来空气悬架",
            "智能空气弹簧",
        ],
        summary="蔚来高端SUV及轿车配备的闭式双腔空气悬架系统，支持车身高度正负数十毫米升降，并可根据路况毫秒级切换单双气室刚度。",
        description=(
            "相较传统单腔空气悬架只能调节车身离地高度，双腔空气悬架内部设有两个独立气室与电磁切断阀。需要舒适滤震时双腔开启提供柔和阻尼；"
            "激烈过弯或紧急刹车时毫秒级关闭主气室，悬架瞬间硬化提供强劲侧向抗侧倾支撑，兼顾如履平地的舒适与精准操控。"
        ),
        technical_principles=[
            "闭式高压空气充放气系统，充气升降响应速度比开式提升数倍，噪音更小且无结冰风险",
            "电控旁通气阀毫秒级通断调节主副气室有效容积",
        ],
        advantages=[
            "彻底破解‘要舒适就忽悠、要操控就颠簸’的悬架物理矛盾",
            "支持后备箱一键装载高度降低与高速行驶自适应低风阻下趴",
        ],
        limitations=[
            "空气弹簧橡胶皮囊在超长年限极端恶劣气候下具有自然老化周期，后续维护成本高于普通钢制弹簧",
        ],
        representative_vehicles=["蔚来ES8", "蔚来EC7", "蔚来ET7", "蔚来ES7"],
        standard_labels=["双腔空气悬架", "闭式空悬系统", "刚度高度双调节", "抗侧倾动态支撑"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向追求豪华乘坐质感的家庭客户演示空悬不同高度与软硬模式的动态变化，体现顶级旗舰底盘底气。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 16. 蔚来自研 ICC 智能底盘域控制器
    TechnologyEntity(
        id="nio_icc_chassis_controller",
        name="蔚来自研 ICC 智能底盘域控制器",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO ICC (Intelligent Chassis Controller)",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="集中式底盘电子电气域控制器",
        aliases=[
            "icc",
            "蔚来icc",
            "底盘域控制器",
            "智能底盘域控",
            "蔚来自研icc",
        ],
        summary="中国首个全栈自研的集中式智能底盘域控制器，打破国外传统Tier 1黑盒垄断，将驱动、制动、转向与空悬阻尼调度融为一体。",
        description=(
            "蔚来ICC统管全车空气悬架、CDC减振器、电子驻车、制动防抱死及电驱扭矩分配。使底盘具备了自主OTA升级进化能力，"
            "并结合前方激光雷达与摄像头路况扫描数据，在车轮压过井盖坑洼前50毫秒即刻预设阻尼软硬，带来神奇的如丝般滑行感。"
        ),
        technical_principles=[
            "跨域信号实时总线采集，毫秒级算力融合控制空气弹簧气压与电磁阀开度",
            "自主知识产权底盘控制算法代码，摆脱博世/大陆等国外供应商黑盒限制",
        ],
        advantages=[
            "底盘调校可以通过空中OTA定期优化改善，越开越好开越舒服",
            "软硬件自主掌控，对中国复杂路况（减速带、非铺装修路）适应性调校极佳",
        ],
        limitations=[
            "底层软件调校工作量极大，需要海量实车工程测试数据长期喂养训练",
        ],
        representative_vehicles=["蔚来ES6", "蔚来ET5", "蔚来ET7", "蔚来ES8", "蔚来EC6"],
        standard_labels=["ICC底盘域控", "全栈自研底盘软件", "底盘全域OTA", "路况自适应预调节"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "突出蔚来拥有中国极少数全栈掌握底盘核心软件代码的能力，车主底盘舒适度能随着版本更新不断成长。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 17. 蔚来 Power Journeys 充换电补能路线网络
    TechnologyEntity(
        id="nio_power_journeys",
        name="蔚来 Power Journeys 加电路线网络",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Power Journeys Network",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="自驾风景线与极境能源补给网络",
        aliases=[
            "power journeys",
            "加电路线",
            "蔚来加电路线",
            "川藏线加电",
            "丝绸之路加电",
            "独库公路换电",
        ],
        summary="蔚来开辟的连接全国各大风景名胜与极境自驾公路的充换电走廊网络，覆盖川藏线、青藏线、丝绸之路及独库公路等偏远自驾路线。",
        description=(
            "蔚来不仅在各大一二线核心城市铺设充换电站，更致力于打破纯电车无法远征西藏、新疆的传统认知禁锢。"
            "联合沿线驿站与景区部署高功率超充站及换电站，配合专属路线路书服务，让蔚来车主开纯电车也能随心所欲畅游祖国大好河山。"
        ),
        technical_principles=[
            "高寒、高海拔自适应充放电设备选型与离网分布式光储充一体化方案",
            "蔚来能源云（NIO Power Cloud）全链路智能寻桩与长途路径补能精准导航规划",
        ],
        advantages=[
            "彻底破解电动车开不出城市的自驾偏见，独享318川藏线等全国绝美自驾专线充换电服务",
            "官方自建网络维护保障及时，高海拔及冬季不掉链子",
        ],
        limitations=[
            "极偏远高原景区日常车流量较少，运营维护成本显著高于市区场站",
        ],
        representative_vehicles=["蔚来全系车型"],
        standard_labels=["Power Journeys", "川藏自驾充换电", "丝绸之路加电", "能源云路径规划"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向爱好自驾露营、向往西藏新疆长途旅行的客户展示318川藏加电路线图，展现蔚来无与伦比的出行自由度。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 18. 蔚来 Power Mobile 移动加电车服务
    TechnologyEntity(
        id="nio_power_mobile",
        name="蔚来 Power Mobile 移动加电车应急救援服务",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Power Mobile Charging Van",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="移动车载应急直流快充装备与服务",
        aliases=[
            "power mobile",
            "加电车",
            "蔚来加电车",
            "移动充电车",
            "一键加电",
            "道路应急加电",
        ],
        summary="蔚来自主研制部署的车载移动式直流充电机车队，如同移动的巨型充电宝，车主遇电量耗尽或紧急情况下一键呼叫上门快速补充电量。",
        description=(
            "Power Mobile基于纯电动封闭厢式车改装，搭载大容量储能电池包与大功率双枪直流快充系统。在高速路段、偏远道路或车主不便挪车时，"
            "加电专员可在半小时内赶赴现场，充入数十度电量支撑车主抵达下一个服务区或换电站，是蔚来‘无忧服务’的核心防线。"
        ),
        technical_principles=[
            "车对车（V2V）高压直流快速电能传输与微电网逆变直流充电控制",
            "蔚来云端调度算法根据城市交通路况指派最近加电车极速响应",
        ],
        advantages=[
            "极端突发趴窝情况下无需等待拖车，在路边就地快速充入救命电量",
            "一键加电无感服务：车主在开会或睡觉时加电专员即可完成补能",
        ],
        limitations=[
            "依靠人工道路派发与专属车辆，服务高峰期可能需要排队等待调度",
        ],
        representative_vehicles=["蔚来全系车型"],
        standard_labels=["Power Mobile", "移动加电车", "一键加电", "V2V道路应急补能"],
        equivalence_group_id=None,
        sales_talking_points=[
            "对于新手司机或极度担忧高速半路没电抛锚的买家，介绍加电车犹如私人保险，给予绝对心理安全感。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 19. 蔚来专属智能家充桩 (Power Home)
    TechnologyEntity(
        id="nio_power_home",
        name="蔚来专属智能家充桩体系 (Power Home)",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Power Home Smart Wallbox",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="家用交流/直流智能充电与双向V2G装备",
        aliases=[
            "power home",
            "蔚来家充桩",
            "蔚来智能家充桩",
            "7kw家充桩",
            "11kw家充桩",
            "20kw家充桩",
            "v2g充电机",
        ],
        summary="蔚来为私家车位打造的极简美学智能家充桩，涵盖7kW/11kW交流桩与20kW直流快充桩，支持蓝牙无感鉴权、预约错峰谷电充电及V2G车网互动。",
        description=(
            "采用铝合金流线型设计与车规级防护工艺。当车主拔枪靠近车辆充电口时，充电口盖自动感应弹开；插枪即可无感自启动充电。"
            "深度绑定蔚来APP，支持设置凌晨波谷低电价时段自动通电，并在电网负荷高峰期支持车身向电网或家庭应急反向放电（V2G/V2H）。"
        ),
        technical_principles=[
            "超宽电压兼容逆变模块与智能温控安全短路热失控多重熔断保护",
            "蓝牙广播近场自动握手协议与国标加密通信协议集成",
        ],
        advantages=[
            "无感插枪即充，告别繁琐刷卡扫码流程，设计做工高级考究",
            "支持预约谷电充电，百公里电费成本低至几元钱",
        ],
        limitations=[
            "需要自有产权车位或具备电力局报装电表安装条件的固定停车位",
        ],
        representative_vehicles=["蔚来全系车型"],
        standard_labels=["Power Home", "智能家充桩", "无感感应插枪", "预约谷电充电", "V2G车网互动"],
        equivalence_group_id=None,
        sales_talking_points=[
            "对拥有固定车位的客户，介绍每天晚上插枪享受几分钱一度的谷电，早晨出门都是满电的惬意生活。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 20. 蔚来 640kW 全液冷超快充桩
    TechnologyEntity(
        id="nio_power_charger",
        name="蔚来 640kW 全液冷超快充桩体系",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO 640kW Liquid-Cooled Power Charger",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="大功率全液冷直流充电基础设施",
        aliases=[
            "蔚来超充桩",
            "640kw超充",
            "蔚来640kw",
            "全液冷超快充",
            "蔚来液冷超充",
            "765a大电流充电桩",
        ],
        summary="蔚来自研的行业峰值功率超快充桩，单桩最大输出功率高达640kW，最大输出电流765A，配备轻量化自研超柔液冷枪线。",
        description=(
            "针对全行业所有品牌新能源车全面开放。其全液冷循环散热架构使枪线重量降至传统风冷粗壮线缆的一半以下，即使力气较小的女性用户也能单手轻松提枪插拔；"
            "支持最高1000V宽电压输出，智能动态分配各枪功率，让支持高压超充的车型真正发挥出数分钟满电的极致速度。"
        ),
        technical_principles=[
            "全液冷散热回路设计，高压电缆与终端枪头全程强制液冷冷却",
            "功率池共享与矩阵式自适应动态功率分配母排系统",
        ],
        advantages=[
            "640kW峰值功率全球名列前茅，真正实现‘一杯咖啡时间满电出发’",
            "枪线极细极轻仅重2.4kg，单手操作毫无负担且夏季暴晒充电不降功率",
        ],
        limitations=[
            "场地电网容量要求极高，通常需配套独立箱变变压器或储能柜",
        ],
        representative_vehicles=["蔚来ET9", "蔚来全系车型", "全行业符合国标快充纯电车型"],
        standard_labels=["640kW超充桩", "765A最大电流", "全液冷轻量化枪线", "多品牌全面兼容开放"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "告知用户蔚来不仅全国换电站数量最多，自建的高功率充电桩同样是全行业最多的品牌之一，出行动力无忧。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 21. 蔚来第三代整车技术平台 NT3.0
    TechnologyEntity(
        id="nio_nt3_platform",
        name="蔚来第三代纯电技术平台 NT3.0",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Next-Gen Platform NT3.0",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="全域900V高压自研芯片智能纯电底座",
        aliases=[
            "nt3",
            "nt3.0",
            "蔚来nt3",
            "nt3平台",
            "第三代技术平台",
            "蔚来第三代平台",
        ],
        summary="蔚来面向未来十年的跨时代纯电技术平台，集全域900V高压架构、神玑自研芯片、SkyOS操作系统与天行底盘于一体，树立新时代科技旗舰标杆。",
        description=(
            "NT3.0平台代表着中国新能源汽车工业在全栈自研深度上的最高成就之一。不仅彻底实现了底盘执行器、自动驾驶计算芯片、整车底层内核操作系统的全链路自主研发，"
            "更通过极高水准的中央计算与区域控制架构，实现了车身轻量化、算力极致协同与百万级被动安全水准。"
        ),
        technical_principles=[
            "自研芯片+全域自研OS+900V高压电驱动力链路深度垂直整合",
            "中央超算集成化与跨域物理控制器极限归并",
        ],
        advantages=[
            "自主技术掌控率极高，不受国际供应链元器件制约与卡脖子",
            "整车各子系统通信时延大幅缩短至微秒级，协同响应极致迅猛",
        ],
        limitations=[
            "全新平台全新自研技术前期整车研发均摊成本高昂",
        ],
        representative_vehicles=["蔚来ET9", "蔚来新一代旗舰换代车型"],
        standard_labels=["NT3.0平台", "全栈深度自研", "中央计算架构", "百万级旗舰底座"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向追求顶尖行业技术主权与前瞻科技的高端精英用户介绍，展示中国制造在全栈自研深度上的巅峰实力。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 22. 蔚来第二代数字智能系统平台 NT2.0
    TechnologyEntity(
        id="nio_nt2_platform",
        name="蔚来第二代数字智能系统平台 NT2.0",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO 2nd Generation Platform NT2.0",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="全系标配高阶硬件的大规模量产平台",
        aliases=[
            "nt2",
            "nt2.0",
            "蔚来nt2",
            "nt2平台",
            "第二代技术平台",
            "蔚来第二代平台",
        ],
        summary="蔚来主力在售车型的核心技术底座，坚持‘全系标配即顶配’理念，全系统一配备Aquila超感系统与Adam四Orin超算平台。",
        description=(
            "NT2.0平台彻底终结了高端车高低配硬件割裂的传统弊端。无论是入门级ET5还是旗舰级ES8，其智能驾驶计算平台、激光雷达规格、"
            "车身安全结构与换电规格完全保持统一标准。平台支持前后双电机四驱，前后五连杆独立悬架，构筑起极具品牌辨识度的豪华驾控基因。"
        ),
        technical_principles=[
            "模块化高安全车身架构与统一换电几何安装基准",
            "标准化千TOPS级超算与多传感器统一硬件底座",
        ],
        advantages=[
            "买低配车也能享受与顶级旗舰完全一致的智能驾驶与安全软硬件升级待遇",
            "规模化采购与研发分摊带来极佳的长期固件维护与OTA稳定性",
        ],
        limitations=[
            "全系标配昂贵的高阶感知与计算硬件使得入门车型的绝对起售价相对固定",
        ],
        representative_vehicles=["蔚来ES6", "蔚来ET5", "蔚来ET5T", "蔚来EC6", "蔚来ES8", "蔚来ET7", "蔚来EC7"],
        standard_labels=["NT2.0平台", "全系标配即顶配", "统一智驾硬件", "全系前后双电机"],
        equivalence_group_id=None,
        sales_talking_points=[
            "对比很多竞品入门版减配激光雷达、算力芯片砍半的操作，强调蔚来2.0车型‘童叟无欺全系顶配’的良心诚意。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 23. 蔚来高强度铝合金及钢铝混合车身技术
    TechnologyEntity(
        id="nio_hybrid_steel_aluminum_body",
        name="蔚来高强度铝合金与钢铝混合车身技术",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO High-Strength Aluminum & Steel-Aluminum Hybrid Body",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="轻量化高刚度车身安全结构工程",
        aliases=[
            "蔚来全铝车身",
            "蔚来钢铝混合车身",
            "蔚来车身刚度",
            "热成型钢门环",
            "超高扭转刚度车身",
        ],
        summary="蔚来在被动安全领域的金字招牌，综合运用6系/7系航空级铝合金与2000MPa超高强度热成型钢，整车扭转刚度超过40000 N·m/deg。",
        description=(
            "从第一代ES8的全铝车身进化到第二代车型的钢铝混合车身，蔚来精准将铝合金用于前后吸能区与减重关键部位，"
            "将超高强度热成型钢用于乘员舱A/B/C柱与门槛横梁，在中保研、欧洲E-NCAP等权威安全碰撞测试中屡次取得全优最好成绩。"
        ),
        technical_principles=[
            "自冲铆接（SPR）与流钻螺接（FDS）等航空级先进冷连接复合工艺",
            "多传力路径碰撞分散吸能拓扑，保障极端侧碰柱碰乘员舱零变形",
        ],
        advantages=[
            "碰撞安全被动防护表现媲美沃尔沃，数次被车主和网友誉为‘公路坦克’",
            "车身扭转刚度极高，长期行驶剧烈颠簸下车身异响少，底盘紧绷有质感",
        ],
        limitations=[
            "铝合金部件事故后通常需要整体更换而非简单钣金敲打，维修工序相对更专业",
        ],
        representative_vehicles=["蔚来ES8", "蔚来ET7", "蔚来ES6", "蔚来EC7"],
        standard_labels=["钢铝混合车身", "超高扭转刚度", "中保研全G评分", "航空级铆接工艺"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向极度看重家庭出行安全的客户展示蔚来在国内外各类魔鬼碰撞测试中的优异表现，展现货真价实的豪华用料。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 24. 蔚来一体化压铸后地板及车身结构
    TechnologyEntity(
        id="nio_front_rear_integrated_die_casting",
        name="蔚来一体化压铸后地板与高强度压铸车身结构",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Integrated Die-Casting Rear Floor & Body Structure",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="超大吨位一体化压铸制造工艺",
        aliases=[
            "蔚来一体化压铸",
            "一体压铸后地板",
            "蔚来压铸",
            "压铸车身",
            "免热处理铝合金压铸",
        ],
        summary="蔚来采用超大吨位压铸机铸造的一体化后地板结构，将数十个传统冲压零部件一体成型铸造，显著减轻重量并提升后撞击吸收能力。",
        description=(
            "蔚来自主研发免热处理强韧铝合金材料，通过巨型压铸岛一体压铸成型。取消了数百个焊接点与连接铆钉，"
            "后地板整体减重数十公斤，同时后部碰撞弯曲刚度提升，有效保护后轴电池组与第三排乘员安全，且避免了传统热处理导致的结构变形翘曲。"
        ),
        technical_principles=[
            "自研高流动性强韧免热处理铝合金原料配方与微孔发泡控制",
            "数千吨级超大合模力高压铸造模具及真空抽气压铸工艺",
        ],
        advantages=[
            "大幅提升后舱整体扭转刚度，碰撞时吸能更均匀，安全系数大幅提升",
            "消除大量焊点疲劳断裂隐患，提升长期整车耐久性与NVH降噪静谧性",
        ],
        limitations=[
            "一体化铸件若遭受严重追尾损毁，售后维修需要切除更换模块化备件",
        ],
        representative_vehicles=["蔚来ET5", "蔚来ET5T", "蔚来ET9"],
        standard_labels=["一体化压铸后地板", "免热处理铝合金", "轻量化高刚度", "焊点归零工艺"],
        equivalence_group_id=EquivalenceDomain.GIGACASTING_STRUCTURE,
        sales_talking_points=[
            "介绍先进的一体化压铸工艺如何带来更轻、更坚固、更安静的车身底盘，提升车辆长途驾驶的静谧高级感。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 25. 蔚来女王副驾座椅系统
    TechnologyEntity(
        id="nio_lounge_seat",
        name="蔚来女王副驾系统 (NIO Queen Lounge Seat)",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Queen Lounge Seat System",
        category=TechCategory.COCKPIT_OS,
        subcategory="人体工学豪华零重力舒享座椅",
        aliases=[
            "女王副驾",
            "蔚来女王副驾",
            "零重力副驾",
            "女王座椅",
            "副驾电动腿托脚托",
            "lounge seat",
        ],
        summary="蔚来开创行业先河的豪华人体工学座椅配置，集成超长滑轨、一体式电动腿托与脚托，一键舒享如头等舱般的零重力悬浮姿态。",
        description=(
            "取消了副驾驶传统手套箱，换取极其充裕的腿部向前延展空间。副驾座椅拥有超长滑轨，不仅能向后滑至紧贴后排照顾婴幼儿，"
            "还能一键联动靠背、坐垫倾角、腿托与脚托，形成科学的160度舒展人体工学仰角，并标配多模式气囊按摩、通风与加热功能。"
        ),
        technical_principles=[
            "超长行程高承载双滑动静音电动轨道与无级联动机构",
            "心脏与膝盖同水平线零重力受力分布计算，有效降低腿部静脉回流负担",
        ],
        advantages=[
            "长途旅行中副驾乘客体验极致放松，成为无数家庭用户购车的最强决策动力",
            "座椅可大幅后移至第二排身旁，方便带娃母亲近距离喂水照顾后座婴儿",
        ],
        limitations=[
            "为了最大化腿部舒展空间取消了手套箱储物盒，随车细小票据需存放于中央扶手下方镂空层",
        ],
        representative_vehicles=["蔚来ES6", "蔚来ES8", "蔚来EC6", "蔚来EC7", "蔚来ET7"],
        standard_labels=["女王副驾", "零重力舒享姿态", "一体式电动腿托脚托", "带娃专属滑轨"],
        equivalence_group_id=None,
        sales_talking_points=[
            "试驾时务必邀请女主人坐进副驾，一键开启女王副驾零重力仰躺与背部热石按摩，体验瞬间转化成交。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 26. 蔚来行政旗舰“飞岛”中央控制台 (Executive Bridge)
    TechnologyEntity(
        id="nio_executive_bridge",
        name="蔚来行政旗舰贯穿式“飞岛”中控台 (Executive Bridge)",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Executive Bridge Console",
        category=TechCategory.COCKPIT_OS,
        subcategory="行政四座顶级纵向互联岛台系统",
        aliases=[
            "飞岛中控台",
            "蔚来行政岛台",
            "executive bridge",
            "行政桥",
            "贯穿式岛台",
            "后排行政中控台",
        ],
        summary="蔚来专为百万级行政旗舰打造的纵贯前后排豪华中控台体系，集成智能电动开合冰箱、360度多角度旋转行政小桌板及私密互联屏幕。",
        description=(
            "在旗舰车型ET9中，Executive Bridge如同一座横跨前排与后排的悬浮拱桥，将前后四个尊享独立座椅自然划分出私人领地。"
            "岛台内部隐藏了冷暖可调的电动静音车载冰箱、支持多角度无级翻折的铝合金真皮小桌板、以及专属后排商务投屏与遮阳帘多功能控制面板。"
        ),
        technical_principles=[
            "多自由度阻尼机构工程与无缝平移闭合电动机械传动体系",
            "双区独立压缩机冷暖储物控温系统（温控跨度-2℃至55℃）",
        ],
        advantages=[
            "营造出媲美私人飞机头等舱的绝对商务尊贵感与功能多用性",
            "桌板稳定性极高，在车辆高速行驶中平稳敲击笔记本电脑办公不晃动",
        ],
        limitations=[
            "固定贯穿岛台严格锁定车内为四座布局，无法满足临时五人乘坐需求",
        ],
        representative_vehicles=["蔚来ET9"],
        standard_labels=["Executive Bridge", "行政贯穿岛台", "电动冷暖冰箱", "头等舱商务小桌板"],
        equivalence_group_id=None,
        sales_talking_points=[
            "针对高端企业主和商务精英接待需求，展示拉出商务小桌板并从静音冰箱倒出香槟的高光仪式感。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
    ),

    # 27. 蔚来智能香氛与空气净化系统
    TechnologyEntity(
        id="nio_smart_fragrance",
        name="蔚来智能多区香氛与车载空气净化系统",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Smart Fragrance & Air Quality System",
        category=TechCategory.COCKPIT_OS,
        subcategory="座舱微环境健康与嗅觉感知系统",
        aliases=[
            "蔚来香氛",
            "智能香氛",
            "蔚来空气净化",
            "负离子发生器",
            "车载香氛系统",
            "森林级空气净化",
        ],
        summary="蔚来座舱健康环境管理体系，集成多款定制天然大师香氛智能切换、CN95级复合滤芯以及高浓度负氧离子发生器，保持车内森林氧吧级空气。",
        description=(
            "系统内置三款由全球知名调香大师定制的植物香氛胶囊，通过车机大屏或NOMI语音可随心切换不同香调与浓度档位；"
            "配备高精度PM2.5激光颗粒物传感器与AQS空气质量传感器，当检测到车外尾气浑浊时自动秒级切换内循环并启动抗菌防霉离子净化。"
        ),
        technical_principles=[
            "微孔分子超声雾化挥发技术与风道独立旁路混合进气",
            "双重静电驻极滤材与高频等离子负离子电极放电净化技术",
        ],
        advantages=[
            "新车提车几乎没有任何异味，全家人即刻安心上车无甲醛担忧",
            "香氛浓度均匀持久不刺鼻，多种香氛随情绪场景自由联动切换",
        ],
        limitations=[
            "香氛胶囊与CN95滤芯属于定期消耗品，消耗完毕后需在商城购置耗材更换",
        ],
        representative_vehicles=["蔚来全系车型"],
        standard_labels=["智能香氛系统", "大师定制香调", "CN95级空滤", "负氧离子净化"],
        equivalence_group_id=None,
        sales_talking_points=[
            "针对家中有婴幼儿或对车内异味敏感的过敏体质客户，强调蔚来行业领先的‘母婴级零异味健康座舱’认证。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 28. 蔚来全栈自研 300kW 高性能 SiC 碳化硅高性能电驱总成
    TechnologyEntity(
        id="nio_in_house_silicon_carbide_motor",
        name="蔚来全栈自研高性能 SiC 碳化硅电驱总成体系",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO In-House High-Performance SiC Electric Drive",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="高转速碳化硅三合一高效电驱动力总成",
        aliases=[
            "蔚来自研电机",
            "蔚来碳化硅电机",
            "300kw电机",
            "蔚来电驱",
            "双电机四驱总成",
            "碳化硅功率模块",
        ],
        summary="由蔚来旗下蔚瑞动力（XPT）全栈自主正向研发制造的高性能电驱总成，采用碳化硅（SiC）功率模块与高速永磁/感应电机组合，效率高达98.5%。",
        description=(
            "蔚来全系标配前后双电机智能四驱体系。前150kW/180kW高效感应异步电机（日常滑行零拖拽低能耗）与后210kW/300kW高性能永磁同步电机（SiC模块驱动输出超强爆发力）相配合，"
            "系统综合输出功率最高超400kW（540+马力），零百加速轻松跻身3秒俱乐部，且在极低温环境下依然拥有超高电驱热转换回馈能效。"
        ),
        technical_principles=[
            "全栈自主封装SiC碳化硅功率模块，寄生电感大幅降低，开关损耗减少70%",
            "定子扁线Hairpin绕组与转子油冷直冷技术，支持长时间连续超车不热衰减",
        ],
        advantages=[
            "全系坚持前后双电机四驱，拒绝单电机低配，雨雪路面抓地力与加速爆发力远胜单电机车型",
            "自研XPT三合一高度集成化，功率密度与NVH静谧度处于行业前沿水平",
        ],
        limitations=[
            "双电机全系标配对整车电耗基线稍有推高，相比单电机买菜代步车能耗略高",
        ],
        representative_vehicles=["蔚来ET5", "蔚来ES6", "蔚来ET7", "蔚来EC7", "蔚来ES8"],
        standard_labels=["自研SiC电驱", "全系双电机智能四驱", "XPT三合一总成", "3秒级零百加速"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向追求驾驶动力与全天候安全的客户说明：蔚来从不卖单电机‘减配版’，全系标配双电机四驱，下雪结冰天更踏实。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 29. 蔚来 NIO Link 全景互联及 NIO Phone 智能生态
    TechnologyEntity(
        id="nio_link_handset_interconnect",
        name="蔚来 NIO Link 全景互联与智能终端生态",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Link & NIO Phone Connected Ecosystem",
        category=TechCategory.COCKPIT_OS,
        subcategory="车手互联与无感跨端算力融合",
        aliases=[
            "nio link",
            "蔚来互联",
            "nio phone",
            "蔚来手机",
            "车手互联",
            "全景互联",
            "uwb车钥匙",
        ],
        summary="蔚来自主打造的车手互联技术底层协议，以车为中心打通手机、车机与智能穿戴设备，实现真正的无感钥匙、跨端剪贴板与手机算力车机融合调用。",
        description=(
            "NIO Link基于超宽带（UWB）、高带宽低时延车内Wi-Fi与蓝牙协议，构建了独立硬件级加密信道。配合蔚来自研NIO Phone手机，"
            "不仅能实现靠近即解锁的厘米级精准定位无感钥匙，更支持‘天空视窗’双系统分屏流转、车载摄像头直接作为手机高清视频直播源等极致深度生态融合。"
        ),
        technical_principles=[
            "自研NIO Link跨端分布式软总线协议与UWB高精度测距测角算法",
            "端到端国密级硬件安全芯片与生物特征加密认证",
        ],
        advantages=[
            "彻底免除携带实体物理钥匙烦恼，即便手机彻底断电没电也能通过NFC解锁开车",
            "车手互联无任何商业牛皮癣广告干扰，操作极简流畅一气呵成",
        ],
        limitations=[
            "部分极致跨端深度联动功能（如天空视窗全分辨率算力调用）需要搭配NIO Phone使用",
        ],
        representative_vehicles=["蔚来全系NT2.0及NT3.0车型"],
        standard_labels=["NIO Link", "NIO Phone互联", "UWB无感钥匙", "跨端分布式算力流转"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "演示把手机放入口袋径直走向车门即可自动解开门把手，展示未来万物互联的无感从容感。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 30. 蔚来电池云端全生命周期健康智能管理系统
    TechnologyEntity(
        id="nio_battery_health_cloud",
        name="蔚来电池云端全生命周期健康智能管理系统",
        brand="蔚来 (NIO)",
        brand_key="nio",
        english_name="NIO Battery Cloud Health & Safety Analytics",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="换电大数据云端电芯数字孪生健康诊断",
        aliases=[
            "电池云端体检",
            "蔚来电池健康系统",
            "换电站电池体检",
            "电池全生命周期管理",
            "电池数字孪生",
        ],
        summary="基于数千座换电站与数十万运营车辆的动力电池云端数字孪生系统，在每次换电过程中对电芯进行微秒级全维度透视体检，杜绝自燃与严重衰减。",
        description=(
            "每当车辆进站换电时，换电站自动对电池包进行电气阻抗、绝缘性、电芯温差与内阻全面扫描。结合云端AI算法持续比对数十亿公里运行数据，"
            "一旦发现某块电池包存在哪怕细微的一致性离散或潜在短路先兆，换电站即自动将其锁闭在仓内由专业工程团队返厂养护或拆解，车主永远拿到的是无瑕健康电池。"
        ),
        technical_principles=[
            "电化学阻抗谱（EIS）与微小短路特征波形云端神经网络分析",
            "千万级充放电曲线时序大数据离群异常模式预警模型",
        ],
        advantages=[
            "变‘车主自己操心电池坏没坏’为‘后台国家级团队每天帮你养护’，电池自燃风险几乎归零",
            "极大幅度延长动力电池日历寿命，真正实现全生命周期15年使用目标",
        ],
        limitations=[
            "依靠海量换电网络支撑，仅服务于换电体系覆盖之内的标准电池包",
        ],
        representative_vehicles=["蔚来全系车型", "乐道L60"],
        standard_labels=["电池云端健康管理", "换电站电芯体检", "电芯安全自燃预警", "15年长寿命电池"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "向担心电池日后坏了换一块要几万甚至十来万的客户说明：在蔚来换电体系下，每次进站都在做免费深度体检，永远享受顶级健康电池包。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),
]

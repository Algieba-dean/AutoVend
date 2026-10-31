"""
Generic Autonomous Driving & Algorithm Technical Terminology (src/terminology/generic/autonomous.py).
Contains 17 comprehensive generic autonomous driving technologies (category="智驾与算法").
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

GENERIC_AUTONOMOUS_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 端到端自动驾驶大模型 (Original)
    TechnologyEntity(
        id="generic_end_to_end_autonomous_driving",
        name="端到端自动驾驶大模型",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="End-to-End (E2E) Autonomous Driving",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="智驾算法/神经网络大模型",
        aliases=[
            "端到端",
            "端到端大模型",
            "端到端智驾",
            "e2e",
            "end-to-end",
            "神经网络智驾",
            "端到端辅助驾驶",
            "e2e模型",
        ],
        summary="彻底摒弃传统感知/预测/规控分模块手工堆砌代码的级联方案，由单一大模型直接输入传感器图像点云，一体化输出车辆底盘控车轨迹，驾驶行为无限逼近老司机。",
        description=(
            "传统自动驾驶采用级联模块架构：感知输出Bounding Box障碍物列表，给到预测模块，再由手写C++规则库的规划模块计算避障路线。每一层传递都存在不可逆的信息损耗与规则死角（例如遇到施工假人或水坑不知所措）。"
            "端到端大模型（E2E）将感知、预测与规划无缝整合为一个前向神经网络大模型，直接‘从光子到控制’，具备强大的未知常识推演能力，转弯变道丝滑自然，没有机械呆板顿挫。"
        ),
        technical_principles=[
            "海量人类高质量驾驶行为轨迹视频自监督与强化学习训练（RLHF）",
            "隐空间统一特征表征，消除分步串联特征转换误差与规则截断",
        ],
        advantages=[
            "驾驶行为极其拟人化：变道果断、博弈变道懂减速让行或加速抢位，乘坐体感如十年老司机",
            "上限极高：面对无保护左转、拥堵加塞、异形障碍物等长尾极端场景（Corner Cases）应对从容",
        ],
        limitations=[
            "黑盒模型不可解释性强，故障诊断与确定性安全兜底难度高，需要硬性规则安全围栏监护",
            "对车端高算力芯片（Orin-X/Thor）以及云端超算集群（EFLOPS级算力）依赖极大",
        ],
        sub_variants={
            "两段式端到端 (感知大模型+规控大模型)": "业内主流渐进式量产架构，中间保留可解释语义轨迹",
            "One-Model单模型真端到端": "无中间语义接口，端到端直接输出控制量（如特斯拉FSD V12、华为ADS 3.0）",
        },
        representative_vehicles=["特斯拉Model 3/Y(FSD V12)", "鸿蒙智行全系(ADS 3.0)", "小鹏X9/P7+(端到端AI)", "理想L系列(端到端+VLM)", "蔚来全系"],
        standard_labels=["端到端智驾", "E2E", "神经网络大模型", "拟人化驾驶", "无规则感知决策一体化"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "对比老款辅助驾驶‘像机器人一样机械刹停顿挫’，重点向客户展示端到端‘像老司机一样丝滑柔和’，该让就让、该超就超；",
            "强调车辆拥有云端大模型持续自我进化能力，‘买回去之后车越开越聪明’，无需去4S店手动升级规则包。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 2. Occupancy占用网络 / 3D栅格占用网络 (Original)
    TechnologyEntity(
        id="generic_occupancy_network",
        name="Occupancy占用网络 / 3D栅格占用网络",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="3D Occupancy Grid Network",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="智驾算法/3D环境感知表征",
        aliases=[
            "occupancy",
            "占用网络",
            "occupancy占用网络",
            "3d占用网络",
            "3d栅格",
            "空间占用网络",
            "occupancy network",
            "占用栅格",
            "god网络",
        ],
        summary="将车身周围真实三维物理空间细分为体素三维立方体，无需预先识别物体名称即可精准感知‘此处有障碍物’，彻底解决倾覆货车、散落纸箱等白名单外未知障碍物误撞痛点。",
        description=(
            "传统感知算法依赖2D目标检测分类器（如轿车、货车、行人、自行车等有限白名单标签），一旦在高速上遇到掉落的白色床垫、倾倒树木或侧翻异形半挂车，"
            "分类器因无法归类而忽略目标，导致恶性事故。Occupancy网络（3D占用网络）将三维空间体素化（如每个格子10cm×10cm×10cm），"
            "直接预测每个体素是否被占据及其运动矢量速度，不论物体是什么形状颜色，只要占了空间就绝不碰撞，极大提升自动驾驶本质安全。"
        ),
        technical_principles=[
            "多视角摄像头图像特征体素化（Voxelization）反向投影",
            "时空注意力机制时序融合预测体素占据概率与光流速度场",
        ],
        advantages=[
            "突破目标分类白名单限制，对一切未知异形障碍物具备天然免疫与紧急制动避让能力",
            "输出稠密的三维几何表面几何重建，即使在无激光雷达纯视觉方案中也能提供精确测距",
        ],
        limitations=[
            "三维立体高分辨率体素计算量庞大，占用车端NPU海量显存与算力带宽",
            "对极薄物体（如悬空塑料膜）或极端恶劣雨雪逆光反射存在噪点误检测挑战",
        ],
        sub_variants={
            "纯视觉Occupancy": "通过多摄视觉时序深度反推体素（如特斯拉、极越）",
            "多模态融合Occupancy": "融合激光雷达点云与视觉像素的高精度超稠密占用网络（如华为GOD网络、理想、小鹏）",
        },
        representative_vehicles=["特斯拉Model 3/Y", "问界M9(华为GOD网络)", "理想L9", "小鹏G9/X9", "小米SU7"],
        standard_labels=["占用网络", "Occupancy", "3D体素", "未知障碍物识别", "通用障碍物避让", "AEB主动刹车"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向极度关注行车安全的客户剖析真实场景：高速上遇到前车掉落的纸箱、倒伏的警示牌，普通车看不懂可能直接撞上去，而占用网络能直接识别‘前方有障碍占据空间’并平稳避让；",
            "说明这是新能源智能车相较传统燃油车主动安全系统（仅简单毫米波雷达）的降维升级。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 3. BEV + Transformer 鸟瞰图感知架构 (Original)
    TechnologyEntity(
        id="generic_bev_transformer",
        name="BEV + Transformer 鸟瞰图感知架构",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="BEV (Bird's Eye View) + Transformer Perception Architecture",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="智驾算法/跨视角感知融合",
        aliases=[
            "bev",
            "bev+transformer",
            "鸟瞰图",
            "bev感知",
            "transformer感知",
            "bev时序融合",
            "bird eye view",
        ],
        summary="将环车多路摄像头原始透视图像通过Transformer注意力机制直接投射为上帝视角的俯视鸟瞰图（BEV），彻底打破镜头畸变与车身遮挡，为规控提供统一时空参考系。",
        description=(
            "人类在各个角度看车身周围只能看到孤立变形的透视画面。BEV（Bird's Eye View）+ Transformer架构利用交叉注意力机制（Cross-Attention），"
            "将全车6~11颗高像素摄像头采集的2D平面图像特征，联合时序时空信息，端到端转换映射到以自车为中心的连续统一三维俯视平面坐标系。"
            "路面车道线、交通标志、相邻车道多车连续轨迹在此坐标系下一览无余，彻底消除了镜头交界处的几何拼接缝隙与物体跳变错位。"
        ),
        technical_principles=[
            "可形变交叉注意力（Deformable Cross-Attention）实现2D图像特征到3D空间BEV查询向量映射",
            "时序循环神经网络/长短期时序注意力实现动态障碍物速度与轨迹连续滤波",
        ],
        advantages=[
            "车周360度感知无接缝、无死角，有效解决大车遮挡、近距离加塞目标丢失难题",
            "直接在鸟瞰图平面输出障碍物轨迹与道路拓扑，规控算法无需进行复杂的反向坐标转换",
        ],
        limitations=[
            "大模型参数量巨大，对车端AI芯片通用矩阵运算能力和内存吞吐要求高",
            "大仰角坡道或极端颠簸路面下，地面假设标定若发生偏差需要高精度姿态动态补偿",
        ],
        sub_variants={
            "BEVDet / BEVFusion": "融合激光雷达点云与视觉的多模态BEV统一特征架构",
            "BEVFormer": "时空注意力纯视觉BEV网络标杆架构",
        },
        representative_vehicles=["理想L7/L8/L9", "小米SU7", "极氪001/007", "小鹏G6/P7+", "蔚来ET5/ES6"],
        standard_labels=["BEV", "Transformer", "鸟瞰图感知", "多摄融合", "时空时序滤波"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向科技爱好者解释：车机拥有全天候‘上帝视角’，不仅能看清正前方的车，更能洞察侧后方隔壁车道想强行加塞的车辆动向，提前减速规避；",
            "向注重自动泊车的客户展示：车位识别率高、地库立柱拐角看得清清楚楚，完全不会出现后视镜盲区刮碰。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 4. 车规级激光雷达传感器 (Original)
    TechnologyEntity(
        id="generic_lidar_sensor",
        name="车规级激光雷达传感器",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Automotive LiDAR (Light Detection and Ranging)",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="传感器硬件/光电感知",
        aliases=[
            "激光雷达",
            "lidar",
            "车顶激光雷达",
            "128线激光雷达",
            "192线激光雷达",
            "半固态激光雷达",
            "转镜激光雷达",
            "激光雷达测距",
        ],
        summary="主动发射近红外激光脉冲并接收反射光信号的高精度传感器，不受光线明暗和逆光雨雾干扰，直接输出厘米级精度的三维空间三维点云，提供终极安全冗余。",
        description=(
            "摄像头是被动光学感知（依靠外界反光），在进出隧道强光眩目、黑夜无路灯道路、强逆光或大雨大雾时识别率会断崖式下跌。"
            "车规级激光雷达（LiDAR）每秒主动发射数百万个激光脉冲，利用飞行时间法（ToF）精确测算微秒级往返时间，直接获取目标的三维空间绝对距离（测距可达150-250米）。"
            "即使面对纯黑没有路灯的深夜高速，也能一眼看破静止货车或路面异物，是当前高阶城市NOA不可替代的安全硬核防线。"
        ),
        technical_principles=[
            "纳秒级激光发射器与高灵敏硅光电倍增管（SiPM）飞行时间测距（ToF）",
            "微机电系统（MEMS）微振镜或棱镜连续旋转扫描生成高密度三维点云",
        ],
        advantages=[
            "绝对物理测距精度高（厘米级误差），直接获取三维几何外形，无视阴影幻觉与图像误判",
            "全天候全光照抗干扰：在夜间暗光、远光灯暴击、出隧道瞬时黑屏工况下依然稳定工作",
        ],
        limitations=[
            "硬件造价相对单颗摄像头明显更高，车顶安装存在轻微风阻造型考量",
            "无法识别颜色文字（如看不清交通标志牌汉字或路面白色/黄色油漆车道线），必须与视觉融合",
        ],
        sub_variants={
            "半固态转镜/棱镜激光雷达": "当前大规模量产主流（如禾赛AT128、速腾聚创M系列、华为192线）",
            "全固态Flash激光雷达": "无任何机械运动部件，体积小巧，主要用于侧向盲区补盲",
        },
        representative_vehicles=["问界M9(192线)", "小米SU7 Max", "极氪001/007", "理想L9", "蔚来全系(图达通超远距)", "智己LS6"],
        standard_labels=["激光雷达", "LiDAR", "主动发光", "暗光夜视", "厘米级点云", "高阶智驾冗余"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "面对最看重家人安全的客户：强调夜间跑高速‘视线差、前车不开灯’场景，激光雷达能穿透黑暗在200米外探测危险并主动刹停，救命神器；",
            "对比纯视觉降配车型，突出激光雷达带来的物理测距安全兜底，无需担心雨夜‘逆光致盲’引发智驾失灵退出。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 5. 无图城市领航辅助驾驶 (Original)
    TechnologyEntity(
        id="generic_mapless_urban_noa",
        name="无图城市领航辅助驾驶 (Mapless Urban NOA)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Mapless Urban Navigation on Autopilot (Urban NOA)",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="高阶智驾功能/全场景领航",
        aliases=[
            "无图noa",
            "城市noa",
            "无图城市noa",
            "无图智驾",
            "全国都能开",
            "全场景noa",
            "urban noa",
            "城市领航",
            "有路就能开",
        ],
        summary="摆脱对高精地图（HD Map）依赖的高阶领航辅助驾驶系统，依靠车端纯实时感知拓扑推演，在全国任意城市公开道路实现自动红绿灯通行、借道绕行避障与终点送达。",
        description=(
            "早期高阶智驾依赖采集成本高昂且更新周期长达数月的高精地图，一旦道路修路改道或换红绿灯，车辆立刻退出降级，导致高阶智驾只能局限在北上广深少数主干道。"
            "无图城市NOA（Mapless Urban NOA）将感知道路拓扑的能力直接搬上车端神经大模型，实时‘脑补’车道线几何连通关系，"
            "配合普通标清导航地图即可实现全国所有城市环路、主干道、甚至无车道线乡村毛细血管道路的自动通行与跟车掉头，真正做到‘全国都能开，有路就能开’。"
        ),
        technical_principles=[
            "实时道路拓扑大模型（如Road Boundary Reconstruction）实时重构路口虚拟导向线",
            "时空联合规划算法与自适应动态通行博弈决策",
        ],
        advantages=[
            "全国通开：不受地图资质与开城区域限制，三四线城市、乡镇县道甚至偏远景区均可畅享智驾",
            "对施工改道、临时封路等突发路况实时适应能力极强，绝不因地图过期而罢工",
        ],
        limitations=[
            "面对极其混乱的超大异形多岔路口或完全无标线的集市人车混行路段仍需驾驶员随时接管",
            "对车端高算力硬件与雷达视觉多源传感器的实时可靠性提出极致要求",
        ],
        sub_variants={
            "无图城市NOA": "全国所有公开道路自动导航驾驶",
            "端到端泊车代客泊车 (AVP)": "从公开道路无缝衔接地下多层车位泊车",
        },
        representative_vehicles=["华为系(问界M7/M9、享界S9)", "小鹏全系(XNGP全国通)", "理想AD Max全系", "极氪001/007", "小米SU7(全场景NOA)"],
        standard_labels=["无图城市NOA", "全国都能开", "城市领航辅助", "实时拓扑", "有路就能开", "高阶智驾标配"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "问及客户老家或日常上下班城市：‘很多友商说能城市智驾但只能在几个大城市特定几条街开，我们是无图方案，不管在哪个城市、甚至老家县城，全国都能开！’",
            "向每天饱受早晚高峰堵车困扰的上班族介绍：上下班堵在城市主干道只需扶好方向盘，红绿灯启停、变道跟车全自动完成，大幅缓解身心疲劳。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 6. 4D毫米波成像雷达 (4D Imaging Radar)
    TechnologyEntity(
        id="generic_4d_millimeter_wave_radar",
        name="4D毫米波成像雷达 (4D Imaging Radar)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="4D Millimeter-Wave Imaging Radar",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="传感器硬件/射频成像",
        aliases=[
            "4d毫米波雷达",
            "4d成像雷达",
            "4d毫米波",
            "成像雷达",
            "高分辨率毫米波雷达",
        ],
        summary="在传统3D毫米波雷达基础上增加高度俯仰测量维度，大幅提升点云通道数与水平/垂直角分辨率，可在雨雪浓雾等极端恶劣天气下穿透成像。",
        description=(
            "传统毫米波雷达只能测算距离、方位角与径向相对速度（3D），无法判断前方静止障碍物是在地面上（如静止故障车）还是在天桥或上方标牌下，因此常将静止物体滤除以防误刹。"
            "4D成像雷达增加了高度俯仰角测量，通过大规模天线阵列虚拟合成上万个点云通道，分辨率提升数十倍，能清晰区分地表减速带、路面静止抛洒物与高悬桥梁，"
            "且对暴雨、浓雾、沙尘暴具备几乎百分百的电磁波穿透力，成为高阶智驾在极端恶劣天气下的定海神针。"
        ),
        technical_principles=[
            "MIMO多发多收虚拟天线阵列与高频调频连续波（FMCW 77-79GHz）",
            "多普勒频移多径时空信号处理与俯仰向超分辨测角算法",
        ],
        advantages=[
            "全天候穿透力强：大暴雨、暴雪、沙尘、浓雾等恶劣天气下性能几乎不受衰减",
            "支持高精度俯仰测高，能够有效区分静止车辆与上方高架立交桥，减少高速AEB幽灵刹车与漏刹",
            "成本显著低于超远距激光雷达，耐久性高，无机械磨损部件",
        ],
        limitations=[
            "点云密度与横向角分辨率相比激光雷达仍有差距，难以精细重建物体精细轮廓边缘",
            "地表金属反光与多径反射效应可能引入一定的虚警噪声，依赖后端滤波算法",
        ],
        sub_variants={
            "级联多芯片方案": "多颗雷达芯片级联扩展通道，点云稠密，性能顶级",
            "集成单芯片SoC方案": "高集成度单片雷达芯片，成本经济，适合规模化普及",
        },
        representative_vehicles=["飞凡R7/F7", "宝马i7", "吉利银河", "深蓝汽车部分车型"],
        standard_labels=["4D毫米波雷达", "4D成像雷达", "全天候感知", "穿透浓雾雨雪", "静止障碍物识别"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向经常跑雨雪雾恶劣天气的车主重点说明：暴雨浓雾时眼睛和摄像头都看不清前方，但4D毫米波雷达能穿透雨雾看透前车，防追尾能力极强。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 7. 视觉语言大模型 (VLM)
    TechnologyEntity(
        id="generic_vlm_vision_language_model",
        name="视觉语言大模型 (VLM)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Vision-Language Model (VLM) for Autonomous Driving",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="智驾算法/多模态理解大模型",
        aliases=[
            "vlm",
            "视觉语言模型",
            "视觉大语言模型",
            "vlm上车",
            "端到端+vlm",
            "多模态大模型",
        ],
        summary="引入千亿级世界知识的多模态视觉语言大模型，赋予智能车对真实世界交通场景的‘认知理解能力’，能够看懂施工手势、临时标语、潮汐车道牌等复杂场景。",
        description=(
            "传统感知模型即便识别出了前方有一个黄色路牌，也无法理解路牌上用粉笔写的‘前方修路，7点至19点单向放行’这一段汉字逻辑。"
            "VLM（Vision-Language Model）将多模态大语言模型（如百亿参数级）轻量化蒸馏部署于车端或云端协同，"
            "车辆不仅能看懂交警挥动的临时临时指挥手势、路边交警反光背心标语、临时施工改道牌，还能像人类一样推理‘前面洒水车在作业，地面可能湿滑，我应该提前变道绕过它’。"
        ),
        technical_principles=[
            "多模态视觉Encoder与自回归语言Transformer解码器跨模态注意力融合",
            "车端大算力NPU异构量化压缩与Token级图文端到端推理加速",
        ],
        advantages=[
            "具备人类级世界常识推理能力，从容看懂复杂汉字指示牌、手绘改道标牌与潮汐车道",
            "能够识别并理解交警指挥手势、施工人员挥旗指示等动态突发语义",
        ],
        limitations=[
            "大模型参数量极其庞大，推理延迟在数百毫秒级，通常作为快慢双系统中的慢系统思考指导快系统",
            "车端AI芯片算力与带宽消耗巨大，需要顶配双芯片或高算力集中式域控支持",
        ],
        sub_variants={
            "车端慢系统VLM+快系统端到端": "VLM负责复杂场景常识决策思考，端到端负责高频毫秒级操纵（如理想端到端+VLM）",
            "云端超大VLM数据蒸馏": "云端训练超大VLM用于自动驾驶自动化数据标注与难题挖掘",
        },
        representative_vehicles=["理想L系列(端到端+VLM系统)", "蔚来ET9", "小鹏P7+", "极越01/07"],
        standard_labels=["VLM", "视觉语言大模型", "常识推理", "看懂施工牌", "交警手势识别", "智能车大脑"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向追求最前沿AI科技的客户介绍：以前的智驾像机器人在认死理，现在的VLM大模型给车装上了一个能看懂汉字、会思考常识的真人智慧大脑，施工修路牌看一眼就懂。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 8. 自动驾驶世界模型 (World Model)
    TechnologyEntity(
        id="generic_world_model_autonomous_driving",
        name="自动驾驶世界模型 (World Model)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Generative World Model for Autonomous Driving",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="智驾算法/时空动态生成",
        aliases=[
            "世界模型",
            "world model",
            "生成式世界模型",
            "智驾世界模型",
            "时空预测世界模型",
        ],
        summary="能够预测未来物理世界时空动态演化规律的生成式时空大模型，不仅能在云端生成数百万种逼真极端事故仿真场景，更能在车端推演‘若我变道，周围多车将如何反应’。",
        description=(
            "真实世界中，极端危险工况（如鬼探头、连环追尾、翻车侧滑）发生率极低，采集成本高且极度危险。世界模型（World Model）通过自回归扩散生成技术，"
            "学习现实物理世界的运动动力学与因果逻辑，能够输入一段真实行驶片段，自主衍生生成数十万种带有风雨雷电、横穿行人、大货车侧翻的逼真物理仿真视频闭环训练智驾模型。"
            "在车端，世界模型能够作为‘想象力引擎’，预判自车做出某种动作后周围其他交通参与者的概率反应，从而制定最安全的全局博弈策略。"
        ),
        technical_principles=[
            "时空视频扩散生成模型（Spatio-Temporal Diffusion）与物理规律一致性约束",
            "潜变量空间动态转移网络预测未来多步场景潜在状态（Latent Rollout）",
        ],
        advantages=[
            "无限生成高难度长尾Corner Case极端场景，低成本实现上亿公里高保真云端仿真闭环",
            "赋予智驾系统预判未来演进的能力，在拥堵博弈与十字路口转弯中行动更加果断自信",
        ],
        limitations=[
            "生成式大模型在云端训练与推演极其消耗算力，需要万卡级GPU超算中心支持",
            "长周期推演可能发生物理规律幻觉漂移，需要强物理先验约束纠偏",
        ],
        sub_variants={
            "云端生成式仿真世界模型": "用于生成高保真闭环测试训练场景（如特斯拉、华为、小鹏云端世界模型）",
            "车端潜空间预测模型": "轻量化预测未来数秒的多模态博弈动态演变",
        },
        representative_vehicles=["特斯拉FSD", "鸿蒙智行全系", "小鹏汽车全系", "理想汽车全系"],
        standard_labels=["世界模型", "World Model", "时空预测", "生成式仿真", "物理因果预判", "闭环训练"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向用户讲解云端技术实力：我们的车在云端拥有‘数字孪生世界’，每天有几百万个AI虚拟化身在模拟最极限的暴雨车祸场景练车，所以新车交付到您手上时就已经积累了上亿公里的老司机经验！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 9. 高速领航辅助驾驶 (Highway NOA / HWA)
    TechnologyEntity(
        id="generic_highway_noa_navigation",
        name="高速领航辅助驾驶 (Highway NOA / HWA)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Highway Navigation on Autopilot (Highway NOA)",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="高阶智驾功能/高速封闭道路",
        aliases=[
            "高速noa",
            "高速领航",
            "highway noa",
            "高速自动导航辅助",
            "高速ngp",
            "高速高架领航",
        ],
        summary="在封闭结构化道路（高速公路、城市快速路、城市高架桥）上实现基于导航路线的自主巡航、自动超越慢车、自动汇入/驶离匝道及过弯的高阶辅助驾驶功能。",
        description=(
            "高速领航辅助（Highway NOA）是高阶自动驾驶最早实现大规模成熟商业化落地的场景。在进入高速公路或城市高架后，系统接管纵向车速与横向转向，"
            "能够根据路段限速标志智能巡航，前方遇到大货车或龟速车时自动观察相邻车道盲区安全距离，打转向灯自主变道超车；"
            "在距离目标出口2公里前，提前自主向右变道并平稳减速汇入匝道，实现高速A点到B点几乎零接管的省心长途驾驶。"
        ),
        technical_principles=[
            "高速标清/高精定位与导航电子地平线（e-Horizon）路径前瞻规划",
            "多传感器融合高速车道线拟合与超远距前向雷达/视觉目标跟踪",
        ],
        advantages=[
            "极大减轻长途跨省驾驶疲劳感，有效杜绝高速分心、打瞌睡引发的追尾事故",
            "自动提前规划驶入匝道，有效避免新手司机高速错过出口或临阵强行变道的危险操作",
        ],
        limitations=[
            "遇大雾团雾、路面大面积积水、施工断路变道及极端恶劣天气仍需驾驶员高度警惕并准备随时接管",
            "目前法律法规下驾驶员仍负全责，手部必须轻扶方向盘并保持视线前方",
        ],
        sub_variants={
            "标清无图高速NOA": "依靠车端纯感知与普通导航运行，适用范围更广",
            "高精地图高速NOA": "结合高精定位地图的高精度超平稳过弯方案",
        },
        representative_vehicles=["理想全系(AD Pro/Max)", "小鹏全系(Highway NGP)", "蔚来全系(NOP+)", "鸿蒙智行全系", "特斯拉(NOA)"],
        standard_labels=["高速NOA", "高速领航", "自动进出匝道", "自主超车", "长途自驾神器", "减轻疲劳"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向经常跑高速出差或回老家的客户极力推荐：长途跑几百公里高速最累人，开启高速NOA后车子自己保持车距、自己变道超大车、自己下匝道，开一天车下来腰不酸腿不疼，轻松惬意。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 10. 代客泊车与记忆泊车系统 (AVP / HPP)
    TechnologyEntity(
        id="generic_automated_valet_parking",
        name="代客泊车与记忆泊车系统 (AVP / HPP)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Automated Valet Parking (AVP) & Home Zone Parking (HPP)",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="低速智驾功能/自动泊车生态",
        aliases=[
            "代客泊车",
            "avp",
            "记忆泊车",
            "跨楼层记忆泊车",
            "自动代客泊车",
            "遥控泊车",
            "apa",
        ],
        summary="支持驾驶员提前在车库门口下车，车辆自主跨楼层寻找车位并倒车入库；或学习常驻路线从小区门口自动开到固定地下车位的低速全自动代客泊车技术。",
        description=(
            "面对狭窄多立柱、多盲区的地下停车场，倒车入库对新手司机是巨大噩梦。记忆泊车（HPP）让车辆学习一次从地库入口到私人车位的巡航路径，"
            "之后每次到达入口即可一键开启，车辆自主避让对向来车与行人、自动上下坡跨楼层、丝滑倒车入库折叠后视镜。"
            "高阶AVP代客泊车更支持手机APP一键呼叫召车：人下班在商场电梯口等待，车辆自主从地下车位驶出开到电梯口‘接驾’，彻底告别昏暗地库找车苦恼。"
        ),
        technical_principles=[
            "基于低速环视SLAM点云建图与地库立柱视觉特征匹配定位",
            "低速高精空间碰撞检测、微小缝隙极限路径规划与毫米级线控刹停",
        ],
        advantages=[
            "解决极端狭窄车位进出难题：停好后主驾下车困难的车位，可用手机遥控自动泊入",
            "跨楼层自主寻位与一键手机召唤，极大提升尊崇感与用车便利性",
            "倒车入库一把到位，避免蹭伤立柱轮毂与车漆",
        ],
        limitations=[
            "面对无反光地坪漆、完全昏暗无光照或信号完全屏蔽的简陋地库性能可能受限",
            "跨楼层连续下陡坡与急弯错车时对避让策略保守度有一定要求",
        ],
        sub_variants={
            "APA自动泊车": "人在车内，识别垂直/水平/斜列车位一键泊入",
            "RPA手机遥控泊车": "人在车外手机蓝牙控制车辆直进直出或泊入",
            "AVP无人代客泊车": "地库门口人下车，车自主找车位停好并上锁",
        },
        representative_vehicles=["鸿蒙智行全系(泊车代客)", "小鹏G6/G9/X9", "小米SU7", "极氪001/007", "理想L系列"],
        standard_labels=["代客泊车", "AVP", "记忆泊车", "手机召唤", "遥控泊车", "一把入库"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "现场给客户演示手机遥控泊车：遇到两边车挨得极近的窄车位，您可以先潇洒下车，在手机屏幕上轻轻一点，车子自己倒进车位停得整整齐齐，再也不用侧身硬挤下车蹭脏衣服！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 11. 线控转向系统 (Steer-by-Wire)
    TechnologyEntity(
        id="generic_drive_by_wire_steering",
        name="线控转向系统 (Steer-by-Wire)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Steer-by-Wire (SbW) System",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="底盘线控执行器/线控转向",
        aliases=[
            "线控转向",
            "sbw",
            "线控方向盘",
            "电子转向",
            "无机械转向柱",
            "steer by wire",
        ],
        summary="彻底取消方向盘与前转向轮之间的刚性机械转向柱连接，全由电信号传输转向意图并由执行电机驱动车轮转向，支持随速可变转向比与方向盘手不离把全行程过弯。",
        description=(
            "传统转向系统依赖一根从方向盘延伸到车轮的钢制转向柱，无论发生碰撞还是过减速带，路面震动都会反向冲击打手，且转向圈数固定（掉头需打一圈半）。"
            "线控转向（Steer-by-Wire）彻底斩断物理轴连接，方向盘端只负责采集角度意图并通过力矩电机模拟逼真路感反馈；轮端由双冗余电机直接推动转向拉杆。"
            "转向比可在1:1到15:1之间自由软件调节：低速掉头倒车只需转动方向盘半圈（无需交叉换手），高速巡航时自动变沉稳定防飘；更无机械柱侵入座舱伤害驾驶员膝盖的隐患。"
        ),
        technical_principles=[
            "三通道冗余角位移传感器与全冗余无刷伺服电机控制器",
            "路感模拟电机实时力矩反向合成算法与故障隔离硬件安全熔断机制",
        ],
        advantages=[
            "随速无级可变转向比：低速一把打满无需倒手，高速沉稳指哪打哪，赛车级操控体验",
            "隔离路面细碎震动与冲击打手，同时保留清晰有质感的模拟路感",
            "碰撞时无金属转向柱侵入主驾腿部空间，大幅提升被动安全碰撞等级",
        ],
        limitations=[
            "无任何机械硬连接备份，必须采用双电源、双传感器、双ECU的多重全冗余安全架构，造价高昂",
            "对力感模拟算法要求极高，若调校不好可能会带来微弱的电子游戏手柄虚假感",
        ],
        sub_variants={
            "带安全离合器线控转向": "平常线控，故障瞬间离合器咬合恢复机械连接的过渡方案",
            "全线控SbW系统": "完全无转向柱纯电冗余方案（如特斯拉Cybertruck、蔚来ET9、丰田bZ4X概念版）",
        },
        representative_vehicles=["特斯拉Cybertruck", "蔚来ET9", "英菲尼迪Q50(DAS先驱)", "雷克萨斯RZ(线控版)"],
        standard_labels=["线控转向", "SbW", "可变转向比", "手不离把掉头", "全冗余安全", "下一代智能底盘"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "向喜爱操控或女性用户介绍：低速掉头进车位只需轻轻打半圈方向盘，双手根本不用忙乱交叉倒手，优雅轻松；碰撞时再也没有铁柱子顶着胸膛和膝盖，既好开又极致安全。",
        ],
        maturity=TechMaturity.PRE_RESEARCH,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 12. 线控制动系统 (One-Box / Two-Box E-Brake)
    TechnologyEntity(
        id="generic_drive_by_wire_braking",
        name="线控制动系统 (One-Box / Two-Box E-Brake)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Brake-by-Wire (One-Box / Two-Box Integrated Electronic Braking)",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="底盘线控执行器/线控制动",
        aliases=[
            "线控制动",
            "one-box",
            "线控刹车",
            "ibooster",
            "集成式电子制动",
            "two-box",
        ],
        summary="取消传统真空助力泵，由电信号感应刹车踏板行程并由伺服无刷电机极速建立制动油压的电子制动系统，建压时间缩短至100-150毫秒，刹车距离显著缩短。",
        description=(
            "纯电动车与混动车没有内燃机进气歧管的持续真空源，传统真空刹车助力器无法直接工作。"
            "线控制动系统将电子踏板感应器、ESP车身稳定控制与高压伺服建压机构集成于单一盒体内（One-Box）。"
            "当系统检测到前方紧急危险时，电机建立100bar峰值制动压力只需100-150毫秒（传统机械泵需要300-500毫秒），相当于百公里刹停距离直接缩短3-5米，堪称救命差距；"
            "同时制动能量回收与机械刹车无缝融合解耦，脚感丝滑线性不点头。"
        ),
        technical_principles=[
            "直流无刷伺服电机驱动滚珠丝杠直接推动主缸建立超高压液压",
            "踏板脚感模拟器与液压制动回路完全物理解耦，实现制动踏板解耦（Decoupled Pedal）",
        ],
        advantages=[
            "极限建压时间极快（<150ms），紧急刹车距离显著缩短数米，AEB响应极度迅速",
            "能量回收率高达95%以上，机械刹车与电驱反拖刹车平顺融合，大幅提升续航并减少刹车片磨损",
            "刹车踏板脚感可通过车机软件自由调节舒适/运动模式，无传统ABS打脚弹脚震动",
        ],
        limitations=[
            "电控系统发生致命故障时，虽然有机械备用直通阀建立基础液压，但脚感会明显偏沉",
            "对电子传感器冗余与软件防失效容错控制要求极高",
        ],
        sub_variants={
            "One-Box集成式": "将电子助力与ESC完全合并为单一部件，重量轻响应最快（如博世IPB、大陆MK C1）",
            "Two-Box分立式": "电子助力器iBooster与独立ESC两盒分立（如早期特斯拉Model 3）",
        },
        representative_vehicles=["小米SU7", "极氪001/007", "比亚迪汉/海豹", "小鹏G6/G9", "特斯拉全系"],
        standard_labels=["线控制动", "One-Box", "150ms建压", "刹车距离缩短", "能量回收无感", "AEB制动神器"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "向用户讲解安全制动：传统车的刹车建压慢，我们的线控刹车是毫秒级电机加压，遇到紧急危险能比老式刹车提前好几米刹停，很多时候这几米就是撞与不撞的救命区别！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 13. 大算力车规级智驾芯片与计算平台
    TechnologyEntity(
        id="generic_high_compute_autonomous_chip",
        name="大算力车规级智驾芯片与计算平台",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Automotive High-Compute AI SoC & Autonomous Driving Platform",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="智驾计算平台/车规级SoC",
        aliases=[
            "智驾芯片",
            "大算力芯片",
            "orin-x",
            "orin芯片",
            "车端计算平台",
            "自动驾驶芯片",
            "thor芯片",
        ],
        summary="专为自动驾驶端到端神经网络与Transformer大模型定制的车规级超高算力AI系统级芯片（SoC），单颗算力达254至1000+ TOPS，支持数十路高清传感器并行吞吐。",
        description=(
            "城市高阶领航辅助驾驶每秒需要处理数颗800万像素高清摄像头、激光雷达点云与毫米波雷达的海量原始数据流，算力门槛突破数百TOPS。"
            "车规级大算力智驾SoC（如NVIDIA Orin-X、Thor及自研AI芯片）集成了高能效深度学习加速张量核心（NPU/Tensor Core）、多核车规级CPU以及超高内存带宽。"
            "双芯片或四芯片级联平台总算力可达508至1000+ TOPS，支持多模态BEV大模型以每秒几十帧的速度超低延迟运行，并符合ISO 26262 ASIL-D最高功能安全标准。"
        ),
        technical_principles=[
            "异构多核架构（GPU+NPU+Lockstep安全CPU核心）与车规级7nm/4nm先进晶圆制程",
            "硬件级加密引擎、内存ECC校验保护与全链路ASIL-D功能安全岛设计",
        ],
        advantages=[
            "澎湃张量算力储备，支持车端端到端神经网络与VLM大模型流畅部署与OTA持续升级",
            "满足严格的车规级高低温（-40℃~105℃）耐受与十万小时抗振动抗老化要求",
            "多颗芯片冗余备份，单芯片故障时备用芯片可实现毫秒级安全降级接管",
        ],
        limitations=[
            "先进制程大算力芯片功耗较高（单板功耗往往在100W-250W），必须配备专用独立液冷散热循环板",
            "全球顶尖晶圆代工与高端芯片供应链受宏观地缘贸易格局影响较大",
        ],
        sub_variants={
            "单Orin-X平台 (254 TOPS)": "主流高速NOA与轻量城市NOA高性价比方案",
            "双Orin-X平台 (508 TOPS)": "全场景无图城市NOA与端到端大模型旗舰标配",
            "下一代Thor/自研超算平台 (1000-2000 TOPS)": "支持舱驾一体与百亿参数车端大模型中央大脑",
        },
        representative_vehicles=["小米SU7 Max(双Orin 508TOPS)", "理想AD Max(双Orin)", "极氪001/007(双Orin)", "小鹏P7+(自研/Orin)", "蔚来全系(四Orin 1016TOPS)"],
        standard_labels=["智驾芯片", "Orin-X", "508TOPS大算力", "ASIL-D功能安全", "OTA持续进化", "液冷智驾计算平台"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向科技客户阐明算力储备价值：我们车上搭载了超大算力旗舰芯片，算力相当于好几台顶配专业游戏电脑，不仅现在开得稳，未来好几年通过远程OTA升级更厉害的AI模型也绝不会卡顿淘汰！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 14. 影子模式数据闭环引擎 (Shadow Mode)
    TechnologyEntity(
        id="generic_shadow_mode_data_engine",
        name="影子模式数据闭环引擎 (Shadow Mode)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Shadow Mode & Automated Data Loop Engine",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="智驾系统工程/数据驱动闭环",
        aliases=[
            "影子模式",
            "数据闭环",
            "数据驱动",
            "自动化标注",
            "影子测试",
            "shadow mode",
        ],
        summary="车载智驾算法在后台静默运行并与人类驾驶员实际操作实时比对，当发生显著分歧或紧急接管时自动触发数据切片加密回传云端的大规模数据自迭代体系。",
        description=(
            "单靠几十辆官方测试车无法穷尽全中国复杂的长尾交通场景。影子模式（Shadow Mode）将新开发或测试中的智驾算法以后台无感‘影子’形式装入数万甚至数十万量产用户车中。"
            "算法在后台默默根据传感器输入计算转向和刹车指令，但不控制车轮；一旦发现车主踩了急刹、猛打了方向盘，或者车主的操作与算法预测产生了巨大偏差，"
            "系统自动截取前后10秒的高价值多模态传感器片段加密上传至云端超算中心，云端自动化大模型自动清洗并打标签入库重新训练，使智驾大模型拥有全国数十万真实司机的‘众包数据喂养’。"
        ),
        technical_principles=[
            "车端触发式轻量级数据触发器（Trigger Engine）与差分隐私加密回传",
            "云端PB级数据湖自动化清洗、4D自动标注大模型（Auto-labeling）与强化学习闭环迭代",
        ],
        advantages=[
            "以极低成本获取海量真实道路突发险情高价值数据，彻底解决长尾Corner Case难题",
            "算法在量产车后台静默验证数百万公里无误后才正式推送给车主，极大降低新版本Bug风险",
            "数据飞轮越转越快，交付车辆越多，车队的智驾进化速度呈指数级加快",
        ],
        limitations=[
            "对车端与云端数据通信流量带宽、云端超大规模对象存储及算力开销有巨大要求",
            "必须严格遵守国家汽车数据安全法规与地理信息合规脱敏审查标准",
        ],
        sub_variants={
            "车端触发式影子回传": "根据加速度阈值或驾驶员接管动作定向截取数据",
            "全栈云端数字孪生回放": "在云端对回传数据进行百倍加速并发回放验证",
        },
        representative_vehicles=["特斯拉全系(影子模式先驱)", "华为鸿蒙智行全系", "小鹏全系", "理想汽车全系", "极氪汽车全系"],
        standard_labels=["影子模式", "数据闭环", "数据飞轮", "自动化标注", "众包测试", "自迭代进化"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向用户讲解技术底蕴：路上跑着的几十万辆同款车都是您爱车的‘侦察兵’，一旦有人在某个路口遇到罕见施工情况，算法在云端当天就能学会，第二天您的车就已经学会了如何完美避开！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 15. 超声波雷达泊车测距传感器 (USS)
    TechnologyEntity(
        id="generic_ultrasonic_radar_sensors",
        name="超声波雷达泊车测距传感器 (USS)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Ultrasonic Sensor (USS) for Parking Distance Control",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="传感器硬件/声学测距",
        aliases=[
            "超声波雷达",
            "uss",
            "倒车雷达",
            "泊车雷达",
            "12颗超声波雷达",
        ],
        summary="利用压电陶瓷换能器发射并接收40-60kHz超声波的近距离测距传感器，测量0.15至5米范围内的障碍物距离，是全自动泊车与倒车防撞必不可少的声学卫士。",
        description=(
            "光电传感器（摄像头/激光雷达）在近距离贴脸（如小于20厘米）时往往存在视线盲区或焦距死角。超声波传感器（USS）通过压电陶瓷晶体共振发射微秒级声脉冲，"
            "利用声波在空气中反射回波的时间差精准计算厘米级障碍物距离。整车通常在前保险杠和后保险杠布置12颗（前后各4颗短距UPA用于倒车防撞，"
            "车身四角各1颗长距APA用于探测车位边缘），不受光线明暗、雨雪遮挡或透明玻璃干扰，即使在完全漆黑的地下室或面对透明落地玻璃窗也能精确测距警报。"
        ),
        technical_principles=[
            "压电陶瓷晶片逆压电效应产生声学超声脉冲波，正压电效应接收微弱回波",
            "三角定位算法利用相邻雷达交叉回波（Cross-echo）实现二维空间障碍物轮廓重建",
        ],
        advantages=[
            "超近距离盲区测距极准（精度达毫米至厘米级），贴边泊车安全可靠",
            "无惧环境光线变化，对透明玻璃墙、镜面或全黑弱光具有天然的探测能力",
            "单个元器件成本经济，耐候性极佳，历经数十年乘用车工业验证极其稳定成熟",
        ],
        limitations=[
            "探测距离短（一般最大测量距离不超过5米），完全无法应用于中高速行驶场景",
            "声波在空气中容易受到强风直吹扰动，若探头表面结了厚冰块可能会产生虚假回声",
        ],
        sub_variants={
            "短距驻车辅助雷达 (UPA)": "探测距离0.15m-2.5m，负责前后基础防撞报警",
            "长距自动泊车雷达 (APA)": "探测距离0.3m-5m，高指向性，负责扫描平行与垂直车位空间",
        },
        representative_vehicles=["小米SU7", "极氪001/007", "理想L系列", "小鹏G6/G9", "比亚迪仰望/腾势"],
        standard_labels=["超声波雷达", "USS", "倒车防撞", "APA车位扫描", "全黑探测", "近距测距卫士"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向担心倒车碰擦的客户演示：全车12颗超声波雷达像敏锐的耳朵一样环绕车身，哪怕离墙壁或者细矮消防栓只有十几厘米，中控屏也能毫厘不差显示距离并报警，倒车入库彻底告别刮碰。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 16. 车规级高动态高清感知摄像头
    TechnologyEntity(
        id="generic_monocular_stereo_camera_sensor",
        name="车规级高动态高清感知摄像头",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Automotive High-Dynamic Range (HDR) HD Perception Camera",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="传感器硬件/光学感知",
        aliases=[
            "智驾摄像头",
            "800万像素摄像头",
            "双目摄像头",
            "前视双目",
            "环视摄像头",
            "高动态摄像头",
        ],
        summary="采用车规级CMOS传感器的高动态范围（120-140dB HDR）高清车载摄像头，具备800万像素超远探测能力与LED频闪抑制技术，是自动驾驶视觉感知的绝对基石。",
        description=(
            "普通手机镜头在面对汽车大灯直射、进出隧道瞬间或者看交通红绿灯LED屏幕时会出现大片过曝白死、死黑或画面横条频闪。"
            "车规级感知摄像头采用专用汽车级CMOS图像传感器（如索尼IMX490、安森美），动态范围高达140dB，在同一个画面中能同时看清烈日强光下的路标与背阴处暗角里的行人；"
            "前视800万像素长焦镜头可在250米外识别小型车辆与交通指示标志，并配备LED频闪抑制（LFM）确保红绿灯颜色判断万无一失。"
        ),
        technical_principles=[
            "多重曝光融合（Multi-Exposure HDR）与子像素分离高动态范围架构",
            "片上LED频闪抑制（LFM）像素电路与车规级全玻璃低畸变消色差光学镜头群",
        ],
        advantages=[
            "感知信息维度最丰富：色彩、文字、标线、信号灯、车牌信息100%全收录",
            "800万像素超高清分辨率带来200米以上的超远测距视野，高速行驶预警时间极充裕",
            "工业级高低温与抗震稳定性，寿命长达十余年",
        ],
        limitations=[
            "在浓雾、强暴雪或镜头表面被厚泥浆飞溅彻底遮挡时感知效果明显受限",
            "单目测距需要通过深度神经网络推断，在未知罕见物体几何测距时需要多模态冗余校验",
        ],
        sub_variants={
            "前视800万超清双目/单目": "负责中远距离车道线识别、前车跟踪及红绿灯识别",
            "周视/侧向800万高清摄像头": "负责盲区变道汇入与十字路口横向穿行目标检测",
            "300万环视摄像头 (AVM)": "负责360度全景影像与地面积水/车位线识别",
        },
        representative_vehicles=["蔚来全系(配备多颗800万摄像头)", "小米SU7", "极氪001/007", "理想L系列", "特斯拉HW4.0全系"],
        standard_labels=["高清感知摄像头", "800万像素", "140dB高动态", "LED频闪抑制", "视觉感知基石", "超远距前视"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向客户展示进出隧道和夜间画质：普通车进出隧道屏幕会瞬间‘全白致盲’好几秒，我们的800万车规级高动态摄像头哪怕大中午正对烈日，也能把暗处车道和行人看得清清楚楚，反应比人眼还灵敏！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
    # 17. 强化学习与世界模型规控演算法 (RL Planning)
    TechnologyEntity(
        id="generic_reinforcement_learning_planning",
        name="强化学习与世界模型规控演算法 (RL Planning)",
        brand="通用汽车工程技术",
        brand_key="generic",
        english_name="Reinforcement Learning & World-Model-Guided Trajectory Planning",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="智驾算法/规划与决策控制",
        aliases=[
            "强化学习规控",
            "rl规控",
            "强化学习智驾",
            "蒙特卡洛树搜索规控",
            "老司机博弈算法",
        ],
        summary="引入基于人类驾驶奖励函数（RLHF）与蒙特卡洛树搜索（MCTS）的强化学习决策规控算法，在拥堵博弈变道、无保护左转等复杂博弈场景中展现如老司机般高超的心理战术与果断切位。",
        description=(
            "传统的规划算法基于死板的人工规则（如‘前后车距必须大于5米否则严禁变道’），在早晚高峰面对前车车距极近时往往犹豫不决、被动刹停甚至引发后车疯狂鸣笛追尾。"
            "强化学习规控（RL Planning）利用深度强化学习模型在仿真世界与海量人类高水平博弈对局中自我对弈训练，"
            "系统能够学习人类老司机的‘车头试探性微探、试探性轻点刹车给后车压迫感并观察对方反应’等高阶交互博弈动作，"
            "一旦对方减速让行则果断平顺切入，若对方加速则轻柔回正，真正做到行云流水、既不鲁莽也不怯场。"
        ),
        technical_principles=[
            "基于近端策略优化（PPO）的多目标安全舒适通行效率奖励函数（Reward Function）",
            "结合环境动态转移概率的蒙特卡洛树搜索（MCTS）前向多步长决策推演",
        ],
        advantages=[
            "极大解决早晚高峰‘汇流匝道进不去、无保护左转不敢走’的严重通行效率低下痛点",
            "动作连贯果断，博弈姿态逼真拟人，有效降低后车路怒鸣笛与恶意强行插车几率",
            "综合平衡行车安全性、乘客舒适性与通行时效性",
        ],
        limitations=[
            "模型在极端小概率边缘策略探索中可能存在超出人类常规认知的异常行为，必须设置硬编码安全边界",
            "训练过程需要构建高度复杂的非对称博弈多智能体仿真沙盒",
        ],
        sub_variants={
            "离线强化学习安全约束规控": "使用人类海量实车日志离线训练，稳定性高",
            "在线树搜索博弈决策": "在车端毫秒级实时推演多种变道切位分支策略的最优价值得分",
        },
        representative_vehicles=["华为ADS 3.0系统", "特斯拉FSD V12.5", "小鹏端到端大模型", "理想端到端架构"],
        standard_labels=["强化学习规控", "老司机博弈", "RL决策", "果断变道", "无保护左转", "通行效率翻倍"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向吐槽老款辅助驾驶‘一到拥堵加塞就犯傻不敢动’的客户做对比：老系统像刚拿驾照的新手唯唯诺诺，现在的强化学习系统像开了十年出租车的老司机，该贴车身卡位就贴、该卡身位就卡，过十字路口干净利落！",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
        is_generic=True,
        generic_category="智驾与算法",
    ),
]

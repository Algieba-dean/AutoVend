"""
Tesla Proprietary Automotive Technology Registry (src/terminology/brands/tesla.py).
Contains 30 comprehensive proprietary technologies for Tesla.
"""

from typing import List

from src.terminology.schemas import (
    EquivalenceDomain,
    TechCategory,
    TechMaturity,
    TechnologyEntity,
)

TESLA_TECHNOLOGIES: List[TechnologyEntity] = [
    # 1. 特斯拉 4680 结构化电池包 (CTC架构) (Original)
    TechnologyEntity(
        id="tesla_4680_battery",
        name="特斯拉 4680 结构化电池包 (CTC架构)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla 4680 Structural Battery Pack (CTC)",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="大圆柱无极耳电池与车身一体化底盘",
        aliases=[
            "4680",
            "4680电池",
            "4680电芯",
            "4680结构化电池",
            "无极耳电池",
            "tesla 4680",
            "ctc架构",
        ],
        summary="特斯拉自研大直径无极耳圆柱电池（直径46mm、高80mm），采用CTC（Cell to Chassis）电池底盘一体化技术，直接把座椅安装在电池包顶盖上。",
        description=(
            "4680大圆柱电池去除了传统电芯的引出极耳结构（全极耳/无极耳设计），极大缩短了电子在电池内部的传导路径，降低内阻和产热。"
            "单体电芯容量是传统2170电池的5倍。CTC技术省去了下车身底板，前后连接大型一体化压铸件，将电池本体变为车身核心抗扭力部件。"
        ),
        technical_principles=[
            "全极耳卷绕技术降低内阻，允许更大充放电电流",
            "结构化电池组与车身前后大压铸件刚性连接，承担车身结构抗弯抗扭载荷",
        ],
        advantages=[
            "零件数量大幅精简，制造成本理论下降显著",
            "整车轻量化，车身整体性更紧凑，空间利用率提升",
        ],
        limitations=[
            "量产干法电极工艺良品率攀升周期长，能量密度提升幅度前期略低于市场预期",
            "整个电池包灌胶密封，单个电芯故障几乎无法单体维修，维保成本高",
        ],
        sub_variants={},
        representative_vehicles=["Cybertruck", "Model Y (部分北美产版本)"],
        standard_labels=["4680大圆柱电芯", "全极耳高倍率电池", "CTC电池底盘一体化", "结构化电池包"],
        equivalence_group_id=EquivalenceDomain.INTEGRATED_BATTERY_SAFETY,
        sales_talking_points=[
            "对比传统方形电芯，解析大圆柱电池在受力均匀性和轻量化底盘集成上的工程前瞻性。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 2. 特斯拉 FSD / HW4.0 纯视觉自动驾驶 (Original)
    TechnologyEntity(
        id="tesla_fsd_hw4",
        name="特斯拉 FSD / HW4.0 纯视觉自动驾驶",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Full Self-Driving (FSD) / Hardware 4.0",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="端到端纯视觉神经网络智驾",
        aliases=[
            "fsd",
            "tesla fsd",
            "hw4.0",
            "hw4",
            "纯视觉智驾",
            "tesla vision",
            "特斯拉智驾",
            "特斯拉fsd",
            "全自动驾驶",
        ],
        summary="基于纯视觉方案与超强自研计算芯片（HW4.0）的端到端大模型智驾系统，彻底抛弃雷达与高精地图，完全模拟人类视觉感知驾驶。",
        description=(
            "特斯拉坚持“第一性原理”，认为人类驾驶员仅凭两只眼睛就能开车，因此自动驾驶系统也应仅靠摄像头和神经网络。"
            "FSD V12开始采用完全端到端神经网络（视频流输入，转向/油门/刹车轨迹输出），去除了几十万行手写C++代码规则，具备极高拟人化驾驶能力。"
        ),
        technical_principles=[
            "多目高清摄像头感知输入 + 纯视觉神经网络 Occupancy Network（占用网络）",
            "端到端世界模型训练与特斯拉超算集群Dojo巨量影子模式数据迭代",
        ],
        advantages=[
            "硬件成本低且不受雷达波反光干扰，全球统一算法泛化能力极强",
            "端到端大模型在复杂路况下的博弈超车行为极其拟人顺畅",
        ],
        limitations=[
            "中国大陆区域城市完全FSD落地需遵循法规与数据合规审批进程",
            "雨雾飞雪等极端恶劣视线不良天气或镜头脏污时，纯视觉感知识别面临物理极限",
        ],
        sub_variants={
            "HW3.0": "上一代自研FSD芯片硬件（约144TOPS）",
            "HW4.0": "最新一代更高分辨率摄像头与更高算力计算平台",
        },
        representative_vehicles=["Model 3", "Model Y", "Model S", "Model X", "Cybertruck"],
        standard_labels=["纯视觉端到端智驾", "HW4.0硬件", "特斯拉FSD", "大模型神经网络感知", "无雷达智驾"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "客观介绍特斯拉在北美落地端到端智驾的技术开创性，同时指导国内用户关注当前AP/EAP在高速日常通勤中的成熟度。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 3. 特斯拉一体化压铸技术 (Gigacasting) (Original)
    TechnologyEntity(
        id="tesla_gigacasting",
        name="特斯拉一体化压铸技术 (Gigacasting)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Gigacasting Technology",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="超大吨位高压一体成型车身",
        aliases=[
            "特斯拉大压铸",
            "特斯拉一体化压铸",
            "特斯拉压铸",
            "tesla gigacasting",
            "一体化大压铸车身",
            "一体化铸造",
        ],
        summary="特斯拉开创的汽车工业革命性工艺，采用6000-9000吨巨型压铸机将车身数百个冲压焊接零部件直接压铸为前后整体单个铝铸件。",
        description=(
            "特斯拉在Model Y后地板与Cybertruck车身上率先推广一体化压铸技术。通过自研免热处理铝合金材料，将原本由70-80个单独冲压零件和数百个焊接点组成的后底板结构，"
            "在数分钟内一次高压压铸成型，大幅削减车身自重、提高抗扭刚度，并极大压缩工厂产线占地面积与组装工时。"
        ),
        technical_principles=[
            "超大吨位高压锁模成型技术与定制铝合金配方（无需高温二次淬火避免热变形）",
            "结构抗扭与碰撞力传导路径在三维CAD中一体优化",
        ],
        advantages=[
            "车身整体性极佳，杜绝长期行驶后焊点松脱异响",
            "车身大幅减重，延长整车续航里程",
        ],
        limitations=[
            "若发生严重追尾导致大压铸本体断裂形变，维修成本高昂甚至直接整车报废",
        ],
        sub_variants={},
        representative_vehicles=["Model Y", "Cybertruck"],
        standard_labels=["一体化大压铸", "高压整体成型", "高强度免热处理铝合金", "轻量化车身制造"],
        equivalence_group_id=EquivalenceDomain.GIGACASTING_STRUCTURE,
        sales_talking_points=[
            "向追求车身安全性与操控刚度的客户讲解一体压铸带来的极高车体刚性与无异响品质。",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 4. FSD V12 端到端神经网络自动驾驶
    TechnologyEntity(
        id="tesla_fsd_v12_e2e",
        name="特斯拉 FSD V12 端到端神经网络架构",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla FSD V12 End-to-End Neural Network",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="神经网络彻底取代规则代码智驾大模型",
        aliases=[
            "fsd v12",
            "fsdv12",
            "端到端fsd",
            "e2e fsd",
            "无代码智驾",
            "纯神经网络驾驶",
        ],
        summary="彻底删减数十万行传统C++手写规则代码，将视频摄像头像素直接输入神经网络直接输出车辆控制信号的划时代端到端架构。",
        description=(
            "FSD V12是自动驾驶领域从‘规则驱动’迈入‘数据大模型驱动’的历史性分水岭。"
            "系统通过数百万人类优秀驾驶员视频片段进行无监督学习，学会了像人类老司机一样在狭窄车道变道探头、主动避让坑洼、雨天礼貌绕行水坑。"
        ),
        technical_principles=[
            "输入原始摄像头多帧视频流直接端到端输出轨迹控制概率分布",
            "千万级高质量影子模式车队脱困驾驶数据深度强化学习",
        ],
        advantages=[
            "驾驶博弈动作极其自然平顺，完全消除传统算法卡顿顿挫感",
            "面对极端罕见Corner Case场景具备惊人的常识泛化理解能力",
        ],
        limitations=[
            "黑盒大模型难以对单次微小决策失误进行传统行级代码单步断点归因调试",
        ],
        sub_variants={},
        representative_vehicles=["Model 3 Highland", "Model Y", "Cybertruck", "Model S Plaid"],
        standard_labels=["FSD V12", "端到端大模型", "无代码自动驾驶", "类人老司机", "第一性原理"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "向技术迷用户介绍FSD V12的震撼：‘它不再是一行行刻板代码，而是一个看了几十亿公里老司机开车录像自己学会开车的AI大脑！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 5. 特斯拉八通阀热管理系统 (Octovalve)
    TechnologyEntity(
        id="tesla_octovalve",
        name="特斯拉八通阀智能热管理系统 (Octovalve)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Octovalve Intelligent Thermal System",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="多通道集成换热歧管热泵中枢",
        aliases=[
            "八通阀",
            "octovalve",
            "特斯拉热泵",
            "特斯拉八通阀",
            "热管理八通阀",
        ],
        summary="由一个八向旋转控制阀和热泵组成的极致集成热管理中枢，支持12种不同制热/制冷模式，把整车废热榨取到极致。",
        description=(
            "传统电车空调、电机水路和电池水路相互割裂，阀门管路数十根极易漏水。特斯拉自研八通阀将所有冷媒管路集成在一个注塑阀芯体内，"
            "通过旋转阀芯在12种热回路间瞬时切换。能在寒冬把电机堵转产生的焦耳热直接转化为座舱暖气，大幅改善冬季续航。"
        ),
        technical_principles=[
            "单个微型步进电机驱动八通道同轴旋转阀芯",
            "电机故意效率降级高频发热充当紧急制热源",
        ],
        advantages=[
            "零部件减少上百个，整车热系统重量减轻数十公斤",
            "冬季极寒能耗极低，彻底杜绝传统电车开暖风里程腰斩悲剧",
        ],
        limitations=[
            "热泵工作在极寒高负荷除霜模式时压缩机运转声音略微可闻",
        ],
        sub_variants={},
        representative_vehicles=["Model 3", "Model Y", "Model S", "Model X"],
        standard_labels=["八通阀", "Octovalve", "集成热管理", "冬季续航神器", "电驱余热利用"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向工科思维客户讲解结构精妙性：‘一个八通阀把全车电动机、电脑、电池和空调连成一体，冬天连芯片发热都用来给你暖脚！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 6. 特斯拉线控转向系统 (Steer-by-Wire)
    TechnologyEntity(
        id="tesla_steer_by_wire",
        name="特斯拉全行程无机械连接线控转向系统",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Steer-by-Wire Variable Steering Architecture",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="航空级全电控解耦可变转向齿比",
        aliases=[
            "特斯拉线控转向",
            "cybertruck线控转向",
            "特斯拉steer-by-wire",
            "特斯拉无机械转向柱",
            "打满不到一圈",
            "cybertruck转向",
        ],
        summary="全球首款全行程无任何机械轴连接的量产乘用车转向系统，低速方向盘转动不到一圈即可打满车轮，颠覆百年来汽车驾驶习惯。",
        description=(
            "率先量产搭载于Cybertruck。方向盘与前转向节之间彻底取消了传统铸铁机械转向柱，纯粹依靠电线传输传感器信号。"
            "在低速掉头或倒车入库时，方向盘左右打不到180度前轮即可完全转到底，无需任何双手‘倒把’交叉打轮；高速时齿比自动变钝，平稳如磐石。"
        ),
        technical_principles=[
            "前轴双冗余无刷直流电机执行器与双独立控制器",
            "全车48V高压低延迟总线传输与转向力矩双向模拟路感电动机",
        ],
        advantages=[
            "掉头、移库、侧方停车毫不费力，再不用手忙脚乱狂打方向盘",
            "撞车时彻底消除传统转向铁柱向后撞击挤压驾驶员胸腔的致命风险",
        ],
        limitations=[
            "初次上手的驾驶员需要1-2天适应颠覆性的非线性转向手感",
        ],
        sub_variants={},
        representative_vehicles=["Cybertruck"],
        standard_labels=["线控转向", "Steer-by-Wire", "可变转向齿比", "不用倒把打轮", "转向解耦"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "演示掉头不用交替倒手：‘开大车掉头方向盘轻轻一拨前轮直接打满，就像打赛车电竞游戏一样灵动，这是汽车工业一百年来的最大革新！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 7. 特斯拉 48V 低压全车以太网电子电气架构
    TechnologyEntity(
        id="tesla_48v_low_voltage",
        name="特斯拉 48V 低压全车以太网电子电气架构",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla 48V Low-Voltage Gigabit Ethernet Architecture",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="高电压低损耗全车通信骨干网",
        aliases=[
            "48v低压架构",
            "48v电气系统",
            "全车以太网",
            "特斯拉48v",
            "取消12v电瓶",
        ],
        summary="打破汽车行业半个世纪以来的传统12V低压束缚，全车采用48V供电与千兆以太网总线，全车线束重量削减超70%。",
        description=(
            "由Cybertruck首发应用。电压从12V提高至48V后，根据P=UI，传输同等功率所需电流缩减至四分之一，线束铜线大幅变细变轻。"
            "同时全车控制器采用千兆以太网环形总线连接，指令吞吐速度达传统CAN总线的成百上千倍，并彻底消灭了容易亏电坏掉的传统铅酸小电瓶。"
        ),
        technical_principles=[
            "48V锂离子微型低压启动蓄电池",
            "百兆/千兆车规级以太网环形环网协议与分布式区域控制器Zonal架构",
        ],
        advantages=[
            "整车线束减重数十公斤，彻底杜绝小电瓶亏电车辆趴窝无法启动的顽疾",
            "高压大功率线控转向和线控刹车执行器驱动轻松无压力",
        ],
        limitations=[
            "汽车传统零部件供应链此前基于12V开发，特斯拉自研了全套48V小电机与灯光执行件",
        ],
        sub_variants={},
        representative_vehicles=["Cybertruck"],
        standard_labels=["48V低压架构", "全车千兆以太网", "线束减重", "取消铅酸电瓶", "下一代EEA"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向追求底层前瞻技术的客户解读：‘特斯拉开源了48V规范，逼着全行业跟进，彻底消灭了冬天小电瓶容易没电打不着火的世纪难题！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 8. 特斯拉 Plaid 碳纤维转子包裹三电机动力系统
    TechnologyEntity(
        id="tesla_plaid_tri_motor",
        name="特斯拉 Plaid 碳纤维包裹三电机动力系统 (1020hp)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Plaid Carbon-Sleeve Tri-Motor Powertrain (1020hp)",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="碳纤维预应力套筒超高转速三电机",
        aliases=[
            "plaid",
            "plaid三电机",
            "碳纤维转子",
            "1020马力",
            "特斯拉plaid",
            "零百2.1秒",
        ],
        summary="前单一电机加后双电机组成的三电机四驱怪兽，转子外包裹碳纤维高强套筒，突破20000rpm且极速超320km/h极速不衰减。",
        description=(
            "在超两万转的高速离心力下，普通电机转子铜条硅钢片容易膨胀飞散。特斯拉研发了极高张力碳纤维丝预应力缠绕包裹工艺，"
            "将转子死死压紧，不仅实现高达1020匹马力、零百加速2.1秒，更解决了传统电车高速后段加速乏力的弱点，极速一直推背到322km/h。"
        ),
        technical_principles=[
            "高张力碳纤维预浸带机器臂高精度精密紧箍绕线",
            "定转子超薄气隙电磁场优化与全转速平直功率输出曲线",
        ],
        advantages=[
            "0-100km/h仅需2.1秒，四分之一英里加速低至9.23秒，屠杀千万级超跑",
            "全速域功率曲线如平原般持续不跌落，极速突破322km/h",
        ],
        limitations=[
            "全油门弹射起步时瞬间加速度极强，乘坐者需警惕眩晕甚至大脑短暂缺血",
        ],
        sub_variants={},
        representative_vehicles=["Model S Plaid", "Model X Plaid"],
        standard_labels=["Plaid三电机", "碳纤维转子", "1020马力", "极速322km/h", "地表最强加速"],
        equivalence_group_id=EquivalenceDomain.MULTI_MOTOR_TORQUE_VECTORING,
        sales_talking_points=[
            "向性能超跑车迷讲解极速原理：‘碳纤维套筒把转子箍得死死的，两万转都不变形，让这辆五座家用车在直线加速赛上虐翻法拉利和布加迪！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 9. 特斯拉超硬 30X 冷轧不锈钢外骨骼车身 (Exoskeleton)
    TechnologyEntity(
        id="tesla_stainless_exoskeleton",
        name="特斯拉 30X 冷轧不锈钢外骨骼车身架构",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Ultra-Hard 30X Cold-Rolled Stainless-Steel Exoskeleton",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="免车漆防弹防凹陷承载外骨骼",
        aliases=[
            "外骨骼车身",
            "不锈钢车身",
            "30x不锈钢",
            "防弹车身",
            "cybertruck车身",
            "无车漆车身",
        ],
        summary="采用SpaceX星舰同款超硬30X冷轧不锈钢作为外蒙皮，直接充当车身受力骨架，抗撞击、防生锈、抗凹陷且无需任何车漆。",
        description=(
            "颠覆了传统汽车外表为薄铁皮、内部靠龙骨支撑的传统结构，将受力结构完全转移至车身最外层（类似昆虫外骨骼）。"
            "3mm厚的特种不锈钢甚至可阻挡9mm手枪子弹和弓箭射击，日常遭遇开门磕碰、小推车撞击完全零凹陷、不掉漆、不生锈。"
        ),
        technical_principles=[
            "多次冷轧应变硬化特种奥氏体不锈钢合金",
            "空气折弯无模具激光下料折叠制造工艺",
        ],
        advantages=[
            "抗刮耐磨抗砸，洗车保养极其省心，甚至可以用百洁布钢丝球直接清洗表面",
            "极高侧碰与翻滚安全强度，整车如同移动装甲堡垒",
        ],
        limitations=[
            "材料硬度极高无法采用传统冲压模具拉延出复杂圆润曲面，全车呈硬朗赛博科幻棱角",
        ],
        sub_variants={},
        representative_vehicles=["Cybertruck"],
        standard_labels=["外骨骼车身", "30X冷轧不锈钢", "防弹防凹陷", "免漆车身", "星舰材料"],
        equivalence_group_id=None,
        sales_talking_points=[
            "拿锤子敲打车门展示：‘用大锤直接砸上去一个坑都不会留下！不用担心开门磕到墙壁或者小石头崩漆，开三十年都不会生锈！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 10. 特斯拉全视觉 Occupancy 占用体素网络
    TechnologyEntity(
        id="tesla_occupancy_network",
        name="特斯拉纯视觉 Occupancy 3D 占用网络",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Pure-Vision 3D Occupancy Network",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="三维空间体素化通用物理障碍物重构",
        aliases=[
            "tesla occupancy",
            "特斯拉occupancy",
            "特斯拉占用网络",
            "特斯拉体素网络",
            "纯视觉3d占用",
        ],
        summary="将车身周围三维物理世界分割为微小体素立方体，即使从未见过的未知异形物体也能精准判断空间占用和阻碍。",
        description=(
            "传统自动驾驶只能识别模型库里训练过的车辆、行人和自行车（即物体分类）。占用网络将真实世界类似‘我的世界’积木一样划分为3D体素，"
            "不管前方的物体是倾斜的运木卡车、翻倒的垃圾桶还是飞舞的塑料袋，只要占用了空间就能毫秒重建体积并提前减速避让。"
        ),
        technical_principles=[
            "多相机2D图片特征提升至3D空间的NeRF神经辐射场隐式表示",
            "时间序列多帧联合体素流速估计预测运动趋势",
        ],
        advantages=[
            "无需激光雷达即可实现对未知任何异形物理障碍物的全维度空间感知",
            "彻底解决传统目标检测白名单遗漏导致的恶性幽灵刹车与追尾翻车",
        ],
        limitations=[
            "对车端车载芯片的矩阵浮点算力和内存带宽消耗极高",
        ],
        sub_variants={},
        representative_vehicles=["Model 3", "Model Y", "Model S", "Model X", "Cybertruck"],
        standard_labels=["Occupancy网络", "3D体素重建", "通用障碍物识别", "纯视觉空间理解"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "用通俗语言向用户解释：‘车子不需要认得掉在地上的是个纸箱还是行李箱，只要看到那一团空间被占了过不去，就会稳稳停下，极其聪明！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 11. 特斯拉 V4 超级充电桩体系
    TechnologyEntity(
        id="tesla_v4_supercharger",
        name="特斯拉 V4 超级充电桩终端网络",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Supercharger V4 Infrastructure",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="高压大电流液冷超快充生态",
        aliases=[
            "v4超充",
            "特斯拉v4",
            "350kw超充",
            "长枪线超充",
            "开放超充网络",
        ],
        summary="支持最高350kW甚至500kW峰值充电功率，配备更轻更长的3米液冷线缆与非特斯拉品牌兼容开放充电支持。",
        description=(
            "V4超充在原有V3超充基础上全面迭代。充电枪线加长至3米方便各品牌不同位置充电口的车型轻松插入，"
            "支持最高1000V高压平台，配备非接触式刷卡屏幕，无感插枪自动扣费启动，充电15分钟补能数百公里。"
        ),
        technical_principles=[
            "超紧凑大流量液冷电缆与高导热端子触点",
            "桩端集中整流柜兆瓦级功率动态智能共享削峰填谷",
        ],
        advantages=[
            "全国及全球覆盖最广、可用率高达99.9%的超级充电网络",
            "插枪即充，车机无感账号扣费，完全免除扫码关注公众号跳转APP的繁琐体验",
        ],
        limitations=[
            "高峰期若车位占满，离车不拔枪会产生超额资源占用超时费",
        ],
        sub_variants={},
        representative_vehicles=["Cybertruck", "Model 3", "Model Y", "Model S", "Model X"],
        standard_labels=["V4超充", "350kW功率", "即插即充", "液冷枪线", "全球超充网络"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "体验最爽的充电：‘开到超充站拔下枪插上就走，不用掏手机扫码，不用看广告，充完拔枪自动扣款，这才是真正的尊贵！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 12. 特斯拉哨兵模式 (Sentry Mode)
    TechnologyEntity(
        id="tesla_sentry_mode",
        name="特斯拉 360° 哨兵全景智能防御系统 (Sentry Mode)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Sentry Mode 360° Vision Security System",
        category=TechCategory.COCKPIT_OS,
        subcategory="离车全时视频监控与自动警戒录像",
        aliases=[
            "哨兵模式",
            "sentry mode",
            "特斯拉哨兵",
            "车身监控",
            "离车防盗录像",
            "红色大眼睛",
        ],
        summary="锁车后全车高清环视摄像头全时守卫，有人靠近或碰擦时中控大屏闪烁红眼警戒并自动保存证据视频到U盘与手机APP。",
        description=(
            "业内开创性的全方位智能防盗防刮系统。当侦测到有人在车身周围鬼祟逗留、轻度震动或恶意划车时，"
            "系统立即唤醒中控屏幕亮起警戒大眼并发出警告音；手机APP推送报警通知，车主可远程实时查看全景行车记录，剐蹭逃逸无所遁形。"
        ),
        technical_principles=[
            "视觉光流变化检测算法低功耗巡检",
            "车身加速度计与微波雷达联合入侵状态触发",
        ],
        advantages=[
            "彻底杜绝商场地库停一夜被刮花找不到肇事者的绝望痛点",
            "手机APP一键实时查看车周Live视频，安全感十足",
        ],
        limitations=[
            "开启哨兵模式一整天约消耗2-3度电（续航约减少10-15公里）",
        ],
        sub_variants={},
        representative_vehicles=["Model 3", "Model Y", "Model S", "Model X", "Cybertruck"],
        standard_labels=["哨兵模式", "Sentry Mode", "防划车录像", "远程Live监控", "全车行车记录仪"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "解决停车最大心病：‘车停在陌生路边或者老小区，哨兵模式24小时帮你盯梢，有人蹭了车机全角度录得清清楚楚，报警一抓一个准！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 13. 特斯拉爱宠模式 (Dog Mode)
    TechnologyEntity(
        id="tesla_dog_mode",
        name="特斯拉宠物关怀恒温守护系统 (Dog Mode)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Dog Mode Climate & Pet Safety Keep System",
        category=TechCategory.COCKPIT_OS,
        subcategory="离车智能座舱恒温与外界安全交互屏显",
        aliases=[
            "爱宠模式",
            "宠物模式",
            "dog mode",
            "特斯拉宠物模式",
            "车内恒温守护",
        ],
        summary="锁车离车后空调继续恒温运行，中控大屏全屏显示超大温度提示告知路人宠物安全，手机随时监控车内温度。",
        description=(
            "专门解决夏天带宠物出行临时下车办事的痛点。锁车后空调与空气循环持续运行在舒适温度，"
            "中控屏幕以巨大字体显示：‘我的主人很快回来，不用担心，车内空调开着呢，当前温度21℃’，避免热心路人误以为宠物窒息而砸窗救援。"
        ),
        technical_principles=[
            "高压动力电池持续驱动压缩机供电策略",
            "座舱温度传感器冗余监测与手机APP极端温度紧急告警推送",
        ],
        advantages=[
            "养宠家庭自驾游出行的刚需救星，极大扩展出行活动半径",
            "屏幕友好提示避免引起不必要的误会与砸车窗事件",
        ],
        limitations=[
            "当电池电量低于20%时系统出于安全保护会自动停止保持",
        ],
        sub_variants={},
        representative_vehicles=["Model 3", "Model Y", "Model S", "Model X"],
        standard_labels=["爱宠模式", "Dog Mode", "车内恒温", "大屏安全提示", "养宠必备"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "向养狗养猫车主强力展示：‘带狗狗自驾下车吃个饭，开着爱宠模式锁车走人，屏幕上大字告诉路人狗狗很舒服，不怕路人砸窗，超级人性化！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 14. 特斯拉露营模式 (Camp Mode)
    TechnologyEntity(
        id="tesla_camp_mode",
        name="特斯拉整夜持续供电露营模式 (Camp Mode)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Camp Mode Overnight Power & Climate Keep",
        category=TechCategory.COCKPIT_OS,
        subcategory="全天候驻车恒温气流与供电睡眠模式",
        aliases=[
            "露营模式",
            "camp mode",
            "特斯拉露营",
            "车内睡觉模式",
            "夜间空调持续开",
        ],
        summary="驻车时整夜持续保持座舱适宜温度、气流通风、低功耗供电与屏幕微光氛围，后排座椅放倒秒变舒适双人大床房。",
        description=(
            "在露营模式下，车辆关闭车外所有大灯与日行灯，中控屏幕保持温馨篝火动态画面或全暗微光。"
            "空调以极低静音转速整夜换气保暖或制冷，USB接口保持供电，整夜开一晚上空调仅消耗约10-15%电量，尽享自然野趣星空房。"
        ),
        technical_principles=[
            "驻车高压回路防自动休眠与微弱静音气流循环调优",
            "外灯光全闭环静默与防盗报警灵敏度自适应下调",
        ],
        advantages=[
            "告别燃油车怠速开空调一氧化碳中毒的致命风险，真正实现纯净安全的车内过夜",
            "放倒后排垫上定制床垫，随时随地享受五星级‘移动房车’酒店",
        ],
        limitations=[
            "电池电量需保证在20%以上方可开启",
        ],
        sub_variants={},
        representative_vehicles=["Model Y", "Model 3", "Model X", "Cybertruck"],
        standard_labels=["露营模式", "Camp Mode", "全夜空调", "移动大床房", "星空影院"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "放倒Model Y后排展示：‘去海边或山顶看日出，后排放倒就是1米9的大双人床，空调吹一整夜只要十几块钱电费，没有一氧化碳完全零危险！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 15. 特斯拉赛道模式 (Track Mode)
    TechnologyEntity(
        id="tesla_track_mode",
        name="特斯拉赛道模式与前后扭矩无级可调系统 (Track Mode)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Track Mode Dynamic Torque Bias & Drift Customization",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="赛道极限驾驶前后轴扭矩与稳定性自定义调节",
        aliases=[
            "track mode",
            "赛道模式",
            "漂移模式",
            "扭矩自定义",
            "前后轴扭矩可调",
        ],
        summary="在中控大屏上可自由将前后轴动力分配从100:0调节到0:100，完全关闭牵引力控制，支持极致定圆漂移与圈速计时。",
        description=(
            "专为性能车主定制。车主可在大屏上无级滑动条调节前后轴扭矩偏置比（如设定为前0后100变成纯后驱大马力漂移车），"
            "并能分级设定稳定辅助介入比例、动能回收制动强度，实时监控四轮电机、电池及四个刹车盘的热负荷温度图谱。"
        ),
        technical_principles=[
            "双电机/三电机四驱独立力矩高阶物理动力学分配",
            "轮胎微观滑移角热模型与全车实时虚拟热传感器测算",
        ],
        advantages=[
            "一辆车拥有无限种驾驶性格：平时是四驱稳重大叔，进赛道一秒变纯后驱大马力漂移狂暴机器",
            "车载G值表、纽北赛道圈速记录与行车视频联动回放分析",
        ],
        limitations=[
            "纯赛道激烈工况下轮胎磨损与高温上升极快，需在专业封闭赛道使用",
        ],
        sub_variants={},
        representative_vehicles=["Model 3 Performance", "Model S Plaid"],
        standard_labels=["Track Mode", "赛道模式", "漂移神器", "前后扭矩无级调节", "四轮温度图谱"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向追求驾驶乐趣的年轻车主展示大屏滑块：‘在屏幕上把滑块拉到最后就是100%纯后驱，一脚电门瞬间原地烧胎横着漂移，赛道可玩性无与伦比！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 16. 特斯拉生化武器防御模式 (Bioweapon Defense Mode)
    TechnologyEntity(
        id="tesla_bioweapon_defense",
        name="特斯拉医疗级生化武器防御空调系统 (HEPA)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Bioweapon Defense Mode with Hospital-Grade HEPA",
        category=TechCategory.COCKPIT_OS,
        subcategory="医疗手术室级超大HEPA高效空气净化",
        aliases=[
            "生化武器防御模式",
            "hepa滤芯",
            "超大hepa",
            "特斯拉空气净化",
            "正压防尘",
        ],
        summary="配备比普通汽车大数十倍的手术室级大尺寸HEPA滤芯，开启后车舱形成正压，过滤99.97%以上微粒、细菌与烟尘。",
        description=(
            "灵感来自医院重症监护室正压洁净房。前机舱内置巨大医用级HEPA过滤器与活性炭滤网，开启后空调强力增压运转，"
            "让车内气压始终略高于车外外界大气压，使车外的严重雾霾、沙尘暴、山火浓烟或病菌完全无法从车身缝隙渗入，车内空气始终如雨后森林般纯净。"
        ),
        technical_principles=[
            "PM0.3级高效微粒空气阻隔医用级滤纸介质",
            "全密闭车身正压气流动力学工程设计",
        ],
        advantages=[
            "在重度沙尘暴、严重雾霾或遇到车队刺鼻尾气时，车内PM2.5瞬时降为0",
            "对花粉过敏或患有哮喘鼻炎的老人孩子是绝佳的健康保护屏障",
        ],
        limitations=[
            "超大HEPA滤芯占用较多前机舱纵向空间，滤芯体积相当于传统滤网10倍",
        ],
        sub_variants={},
        representative_vehicles=["Model Y", "Model X", "Model S", "Cybertruck"],
        standard_labels=["生化武器防御", "HEPA超级滤芯", "正压防护", "PM2.5瞬间归零", "过敏体质救星"],
        equivalence_group_id=None,
        sales_talking_points=[
            "让鼻炎过敏患者体验：‘就算外面漫天沙尘暴或者刺鼻柴油烟，车里一键开启生化防御，车内空气比三甲医院手术室还要干净！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 17. 特斯拉无感蓝牙手机车钥匙系统 (Phone Key)
    TechnologyEntity(
        id="tesla_app_phone_key",
        name="特斯拉无感蓝牙手机钥匙与远程全控系统",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Seamless Phone Key & Cloud App Ecosystem",
        category=TechCategory.COCKPIT_OS,
        subcategory="全场景无感解闭锁与全球云端互联车控",
        aliases=[
            "特斯拉手机钥匙",
            "特斯拉蓝牙钥匙",
            "无感开门",
            "特斯拉手机app",
            "卡片钥匙",
        ],
        summary="业内公认最稳定灵敏的手机钥匙方案，手机放兜里走近即自动解锁，拉门即开，踩刹车即走，下车离开5米自动落锁升窗。",
        description=(
            "在车身周围布置多颗低功耗高精度蓝牙信标，通过距离梯度算法精确判断手机是位于车外、主驾驶门边还是车内。"
            "彻底消灭了传统点火按键、手刹拉杆与实体机械钥匙。配合特斯拉App，即使身在地球另一端也能一键远程开空调、鸣笛找车或授权朋友开走。"
        ),
        technical_principles=[
            "RSSI蓝牙信号强度梯度滤波与多点空间角定位算法",
            "端云双向加密握手与本地离线数字证书授权机制",
        ],
        advantages=[
            "几年不用掏钥匙，上车踩刹车就出发，彻底改变人类驾驶习惯",
            "远程授权极其简单：朋友借车微信点个链接即可免钥匙开走",
        ],
        limitations=[
            "个别安卓手机后台极端省电策略若杀掉App进程需重新开启",
        ],
        sub_variants={},
        representative_vehicles=["Model 3", "Model Y", "Model S", "Model X", "Cybertruck"],
        standard_labels=["无感手机钥匙", "走近解锁", "离车自动上锁", "无点火按键", "远程开门"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_COCKPIT_OS,
        sales_talking_points=[
            "展示极其随意的用车方式：‘揣着手机走过去拉车门就进，踩一脚刹车挂D挡就走，停好车推门离开5米车子自己锁好升窗，完全不用你管！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 18. 特斯拉基于 GPS 地理记忆的智能自适应空气悬架
    TechnologyEntity(
        id="tesla_smart_air_suspension",
        name="特斯拉自适应智能空气悬架 (基于GPS定位自动升降)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Smart Adaptive Air Suspension with GPS Geo-Memory",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="全自动位置记忆车身高低调节悬架",
        aliases=[
            "特斯拉空气悬架",
            "gps记忆空悬",
            "自动升降悬架",
            "自适应空气悬架",
            "智能空悬",
        ],
        summary="具备GPS地理围栏自动记忆功能，一次手动升起后，下次行驶至该地库陡坡或坑洼路段时车身会自动提前举升避免托底。",
        description=(
            "空气悬架深度联动车机车载GPS高精定位系统。当车主在自家陡峭地库入口或家门口减速带手动将悬架升高后，"
            "系统会自动弹窗提示：‘记住该位置？’确认后，以后每一次开到这个固定位置，悬架都会提前数米无声自动升到最高，高速巡航时自动下沉贴地降低阻力。"
        ),
        technical_principles=[
            "车机地图经纬度地理围栏与悬架升降ECU总线关联",
            "连续可变阻尼阀与全铝封闭式空气弹簧自适应调节",
        ],
        advantages=[
            "彻底杜绝因一时疏忽忘记升底盘而在固定陡坡磕碰下巴的惨剧",
            "高速自动压低车身降低风阻提升稳定性，烂路自动举升兼顾通过性",
        ],
        limitations=[
            "主要配备于Model S、Model X及Cybertruck等高端旗舰车型",
        ],
        sub_variants={},
        representative_vehicles=["Model S", "Model X", "Cybertruck"],
        standard_labels=["自适应空气悬架", "GPS记忆升降", "地库防托底", "高速自动降车身"],
        equivalence_group_id=EquivalenceDomain.ACTIVE_BODY_CONTROL,
        sales_talking_points=[
            "向担心托底的客户演示位置记忆：‘家里的地下车库斜坡比较陡？只要在这儿升过一次，以后每次开回家车身都自动抬高，再也不用提心吊胆怕磕底！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 19. 特斯拉超高抗冲击装甲复合车窗玻璃 (Armor Glass)
    TechnologyEntity(
        id="tesla_armor_glass",
        name="特斯拉超强抗冲击装甲复合隔音玻璃 (Armor Glass)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Ultra-Strong Acoustic Armor Glass",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="高强防砸防飞石声学双层夹胶玻璃",
        aliases=[
            "装甲玻璃",
            "防弹玻璃",
            "armor glass",
            "特斯拉双层玻璃",
            "防砸玻璃",
        ],
        summary="采用超强聚合物复合夹胶技术打造的坚固车窗玻璃，能抵御高速飞石撞击甚至棒球猛力砸击，具备极强隔音防盗防破窗能力。",
        description=(
            "率先全面强化搭载于Cybertruck及新Model 3/Y。外层由超强高韧强化玻璃与多层吸能声学PVB热塑聚合物薄膜复合而成，"
            "不仅能承受四级冰雹猛烈敲击，在遭遇小偷拿砖头砸车窗盗窃时无法被轻易破开，同时大幅阻隔外界高速风噪，提升车内声学私密性。"
        ),
        technical_principles=[
            "化学强化高离子交换深度物理钢化工艺",
            "高分子聚合物声学夹胶减振薄膜三明治压合",
        ],
        advantages=[
            "防飞石防砸能力比普通汽车单层钢化玻璃强数倍，极大提升被动防盗安全",
            "全车双层夹胶玻璃大幅削减车内风噪与路噪",
        ],
        limitations=[
            "发生极端落水紧急救援时车内安全破窗需使用专业高能量钨钢破窗器",
        ],
        sub_variants={},
        representative_vehicles=["Cybertruck", "Model 3 Highland", "Model Y"],
        standard_labels=["装甲车窗", "Armor Glass", "双层声学夹胶", "防砸防盗", "超强抗冲击"],
        equivalence_group_id=None,
        sales_talking_points=[
            "敲击车窗展示厚实感：‘这可不是普通薄玻璃，而是双层装甲夹胶玻璃，高速上大石头蹦上来不碎裂，小偷砸玻璃偷东西砸不破，车里静悄悄！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 20. 特斯拉单踏板极致强动能回收系统
    TechnologyEntity(
        id="tesla_regenerative_braking",
        name="特斯拉高平顺单踏板强动能回收系统",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla One-Pedal Regenerative Braking & Energy Deceleration",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="大功率反拖制动与百公里极致能量回收",
        aliases=[
            "单踏板模式",
            "特斯拉动能回收",
            "强动能回收",
            "one pedal",
            "电门刹车",
        ],
        summary="松开加速踏板即可产生高达0.3G的反拖制动力平稳刹停并完全保持静止，将车辆滑行减速动能最大化回收充入电池。",
        description=(
            "特斯拉标志性的能量回收系统。通过电机反向做发电机运转，在市区90%以上的工况下仅凭右脚深浅控制电门踏板即可完成加减速和完全刹停。"
            "不仅使刹车片磨损几乎为零（十年免换刹车皮），更能将日常行驶能耗降低15-20%，形成极其平顺跟脚的操控一体感。"
        ),
        technical_principles=[
            "电控逆变器反向再生发电毫秒级磁场弱磁转矩控制",
            "低速电机制动与机械驻车EPB无缝渐进接管融合",
        ],
        advantages=[
            "长途开下坡山路完全不用踩机械刹车，刹车永不过热，还能白白多充几度电",
            "踩电门和抬电门精准控制车速，熟悉后脚部疲劳感大幅降低",
        ],
        limitations=[
            "长期习惯单踏板的司机在极端紧急时刻仍需养成瞬间大力踩下机械刹车踏板的肌肉记忆",
        ],
        sub_variants={},
        representative_vehicles=["Model 3", "Model Y", "Model S", "Model X"],
        standard_labels=["单踏板模式", "动能回收", "刹车皮不磨损", "减速充电", "下坡不发热"],
        equivalence_group_id=None,
        sales_talking_points=[
            "带客户体验松电门的减速质感：‘跑山下坡完全不用带刹车，车子自己稳稳减速，回收的电还充回电池里，刹车皮开十年都不用换！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 21. 特斯拉 Dojo 超算中心与 D1 自研芯片
    TechnologyEntity(
        id="tesla_dojo_d1",
        name="特斯拉 Dojo 自动驾驶超级计算机与 D1 芯片",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Dojo Supercomputing ExaPOD & Custom D1 AI Chip",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="端到端神经网络百万级视频集群训练底座",
        aliases=[
            "dojo",
            "dojo超算",
            "d1芯片",
            "特斯拉dojo",
            "ai训练集群",
        ],
        summary="特斯拉自研专为海量自动驾驶视频流训练设计的ExaFLOP级超级计算机系统，搭载定制D1高带宽神经网络芯片。",
        description=(
            "为了支撑FSD端到端大模型对全球上百万辆特斯拉回传海量行车视频的训练消化，特斯拉自研了D1芯片与Dojo机柜。"
            "单机柜算力达到百P级，通过极高互联带宽处理视频流时空三维对齐，使端到端模型迭代速度提升数倍，赋予FSD神速进化的智力底座。"
        ),
        technical_principles=[
            "7nm定制ASIC芯片D1，单芯片BF16/CFP8算力超362TFLOPS",
            "无服务器架构散热砖（Training Tile）与超高密度液冷垂直供电",
        ],
        advantages=[
            "完全摆脱第三方AI芯片算力垄断与短缺瓶颈，算法与算力软硬深度协同",
            "支持全球最大量产车队百亿公里真实道路视频数据自动清洗闭环",
        ],
        limitations=[
            "仅作为后台云端训练基础设施，不直接安装在单车车端",
        ],
        sub_variants={},
        representative_vehicles=["特斯拉全球云端训练底座", "FSD全系模型训练基石"],
        standard_labels=["Dojo超算", "D1芯片", "ExaFLOP算力", "自动驾驶大模型训练", "云端数据闭环"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向追求顶尖AI科技的客户解释技术护城河：‘别家车企买英伟达显卡训练，特斯拉直接自己造超算Dojo，每天有几百万辆车在给它跑数据，算法进化速度比谁都快！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 22. 特斯拉扁线发卡永磁同步电机 (Hairpin Motor)
    TechnologyEntity(
        id="tesla_hairpin_motor",
        name="特斯拉扁线发卡定子永磁同步电机总成",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Hairpin Stator High-Efficiency PMSM Drive Unit",
        category=TechCategory.POWERTRAIN_MOTOR,
        subcategory="高槽满率发卡扁线轻量化高效电驱",
        aliases=[
            "特斯拉发卡电机",
            "特斯拉扁线电机",
            "hairpin motor",
            "特斯拉驱动电机",
            "后驱电机",
        ],
        summary="采用Hairpin发卡式扁铜线绕组定子设计，槽满率提升至70%以上，铜损降低且散热极佳，赋予车辆超低百公里综合电耗。",
        description=(
            "从早期的圆铜线绕组全面切换至发卡扁铜线技术。扁平的铜条像发卡一样整齐插入定子铁芯槽内，"
            "大幅消除了导线之间的空隙，热阻下降，在极小的电机外壳尺寸内释放高达220kW以上峰值功率，整车电耗做到同级无法企及的11-13kWh/100km。"
        ),
        technical_principles=[
            "全自动精密波形发卡编组与端部激光自动激光焊接",
            "直接浸没式喷淋油冷定子铁芯与端部铜线换热",
        ],
        advantages=[
            "同尺寸电机功率提升25%，高转速满载电磁噪音显著降低",
            "电驱能耗极其克制，让Model 3成为全球最省电的中型纯电轿车之一",
        ],
        limitations=[
            "制造工装设备精密昂贵，维修需总成级专业作业",
        ],
        sub_variants={},
        representative_vehicles=["Model 3", "Model Y后轮驱动版/长续航版"],
        standard_labels=["扁线电机", "发卡绕组", "高槽满率", "超低电耗", "高功率密度"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向算家庭用车成本的客户算账：‘特斯拉扁线发卡电机能耗天下第一，百公里电耗才12度，一块钱能跑二十公里，比坐地铁公交还便宜！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 23. 特斯拉集中式中央行车电脑与区域控制器架构 (Zonal EEA)
    TechnologyEntity(
        id="tesla_centralized_eea",
        name="特斯拉中央集中式车载电脑与区域控制器架构",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Centralized Car Computer & Zonal Controller Architecture",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="高集成中央大脑与前后左区域控制器",
        aliases=[
            "集中式电子电气架构",
            "区域控制器",
            "zonal架构",
            "特斯拉eea",
            "中央计算电脑",
        ],
        summary="开创汽车行业中央集中式电子电气架构，仅用一个中央车载电脑（CCM）加左/右/前三个区域控制器掌控全车一切。",
        description=(
            "传统燃油车拥有多达70-100个分散杂乱的ECU盒子，线束长达几公里。特斯拉率先革新为‘中央大脑+三个就近区域控制器’，"
            "车窗、车锁、车灯电线就近插在对应的区域盒子上，软件通过千兆代码统一调度，线束总长从数公里砍到几百米，整车具备终生软件无限进化能力。"
        ),
        technical_principles=[
            "单板整合自研智驾SoC芯片与AMD Ryzen智能座舱平台",
            "以太网骨干连接与电子保险丝e-Fuse智能配电",
        ],
        advantages=[
            "全车代码统一掌握在自研软件团队手中，每次整车OTA可任意升级电机、车灯与空调",
            "彻底消灭容易烧坏的传统机械保险丝，短路自动电子恢复重启",
        ],
        limitations=[
            "中央电脑算力一旦损坏需更换高规格集成主板",
        ],
        sub_variants={},
        representative_vehicles=["Model 3", "Model Y", "Model S", "Model X", "Cybertruck"],
        standard_labels=["集中式架构", "区域控制器", "Zonal EEA", "线束缩短", "电子保险丝e-Fuse"],
        equivalence_group_id=None,
        sales_talking_points=[
            "讲清‘真智能车’与‘伪智能车’的区别：‘传统车有上百个互不理睬的小电脑，特斯拉全车就一个中央大脑，OTA不仅能换车机界面，连刹车踏板脚感和提速性能都能升级！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 24. 特斯拉 Yoke 赛车式多功能方向盘
    TechnologyEntity(
        id="tesla_yoke_steering",
        name="特斯拉 Yoke 赛车式半幅方向盘",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Yoke Racing-Style Steering Wheel",
        category=TechCategory.COCKPIT_OS,
        subcategory="无上半幅遮挡开阔视野运动方向盘",
        aliases=[
            "yoke方向盘",
            "半幅方向盘",
            "特斯拉yoke",
            "赛车方向盘",
            "去拨杆方向盘",
        ],
        summary="削去上半圆的赛车风半幅方向盘，取消转向灯与换挡物理拨杆，前方仪表盘视野零遮挡，如同驾驶科幻宇宙飞船。",
        description=(
            "为了呈现极致开阔的驾驶视野与未来感，特斯拉去掉了传统方向盘上部半圆，并将转向灯、大灯、喇叭与雨刮全部集成在左右拇指触控按键上。"
            "配合中控屏幕边缘上下滑动换挡（或自动根据前后障碍物Auto Shift智能切D/R挡），打造彻底去机械化的极简驾驶舱。"
        ),
        technical_principles=[
            "电容式轻触反馈触感按键与振动微马达",
            "基于Autopilot视觉障碍物自动感知预选挡位算法（Auto Shift）",
        ],
        advantages=[
            "前方视野一览无余，完全不遮挡正前方液晶仪表盘或路况视野",
            "犹如坐在战斗机或F1赛车驾驶舱内的极致科幻战斗感",
        ],
        limitations=[
            "在大角度急转弯揉库打轮时习惯双手抓上圆把位的驾驶员需要一定适应过程",
        ],
        sub_variants={},
        representative_vehicles=["Model S Plaid", "Model X Plaid", "Cybertruck"],
        standard_labels=["Yoke方向盘", "半幅方向盘", "无拨杆设计", "全视野无遮挡", "F1赛车操控感"],
        equivalence_group_id=None,
        sales_talking_points=[
            "让客户握住Yoke方向盘感受视野：‘双手搭在上面，正前方一点遮挡都没有，就像在开外星飞船，科技范儿十足！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 25. 特斯拉矩阵式动态自适应 LED 大灯
    TechnologyEntity(
        id="tesla_matrix_headlights",
        name="特斯拉自适应像素矩阵式 LED 大灯",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Adaptive Pixel Matrix LED Headlights",
        category=TechCategory.MANUFACTURING_SAFETY,
        subcategory="像素级动态避让与专属字符投射灯光",
        aliases=[
            "特斯拉矩阵大灯",
            "自适应大灯",
            "像素大灯",
            "tesla投影大灯",
            "灯光秀",
        ],
        summary="由上百颗微小独立LED像素构成的高分辨率大灯，不仅夜间长开远光自动避让对向来车，还能在白墙投射‘TESLA’字母与灯光秀。",
        description=(
            "配合全车环视视觉摄像头，夜间行驶时远光灯始终开启，当检测到前车尾灯或对向车辆前灯时，"
            "大灯会精准熄灭对应车辆轮廓的微小LED单体，其余路面保持极昼般明亮照亮；驻车时更可跟随音乐节奏开展华丽的‘Tesla Light Show’全车灯光秀。"
        ),
        technical_principles=[
            "高精度微阵列多晶LED光源独立驱动控制器",
            "车机视觉感知目标位置与大灯偏折角度坐标实时动态映射",
        ],
        advantages=[
            "大幅提升夜间走暗路、跑乡村国道的行车能见度，且绝不会晃花别人的眼睛",
            "自带节日全车灯光音乐秀，车友聚会时是活跃气氛的绝对顶流",
        ],
        limitations=[
            "在未开启自适应远光设置时默认处于普通远近光模式",
        ],
        sub_variants={},
        representative_vehicles=["Model 3 Highland", "Model Y", "Model S", "Model X"],
        standard_labels=["矩阵大灯", "自动避让远光", "像素投影", "特斯拉灯光秀", "夜视安全"],
        equivalence_group_id=None,
        sales_talking_points=[
            "过年过节给客户演示全车灯光秀：‘车灯跟随音乐节奏跳舞、投射字幕，车门车窗自动随着动感节拍开闭，超级酷炫好玩！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 26. 特斯拉主动后轮线控转向系统 (Cybertruck)
    TechnologyEntity(
        id="tesla_rear_wheel_steer",
        name="特斯拉主动后轮线控转向技术 (双向±10°)",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Active Rear-Wheel Steer-by-Wire Architecture",
        category=TechCategory.CHASSIS_SUSPENSION,
        subcategory="大角度电控后轮独立转向系统",
        aliases=[
            "特斯拉后轮转向",
            "cybertruck后轮转向",
            "特斯拉主动后轮转向",
            "±10度后转向",
            "大皮卡小转弯",
        ],
        summary="后轮支持最大双向±10度大角度电控偏转，让接近5.7米长的庞大Cybertruck皮卡转弯半径比紧凑型Model 3还小。",
        description=(
            "大型全尺寸皮卡传统上非常笨重难开，拐弯进出库极容易蹭轮。特斯拉在Cybertruck后轴安装了高刚性大功率转向电机，"
            "低速时后轮与前轮反向偏转多达10度，原地掉头转弯半径缩减至惊人的11.3米；高速变道时后轮同向偏转，车身如履平地无甩尾。"
        ),
        technical_principles=[
            "后轴双齿轮齿条高承载电驱动作动器",
            "整车车速与线控转向角动态复合控制算法",
        ],
        advantages=[
            "5.68米庞然大物在拥挤市区掉头一把过，完全颠覆大皮卡笨重难开的传统印象",
            "大幅改善越野狭窄岩石弯道通过能力",
        ],
        limitations=[
            "后轮转向拉杆机构在遭遇极限重度托底后需检查对中校准",
        ],
        sub_variants={},
        representative_vehicles=["Cybertruck"],
        standard_labels=["后轮转向", "±10度转向", "Cybertruck掉头", "灵动大车", "全轮转向"],
        equivalence_group_id=EquivalenceDomain.INTELLIGENT_CHASSIS_STEERING,
        sales_talking_points=[
            "向担心大车难停难开的客户演示：‘车长快5米7的大装甲皮卡，后轮能打10度大角，拐弯掉头比普通小轿车还灵活，窄路轻松一把过！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 27. 特斯拉全自研 FSD 芯片 (Hardware 3.0 / 4.0)
    TechnologyEntity(
        id="tesla_hw3_platform",
        name="特斯拉全自研 FSD 车载计算芯片平台",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla In-House FSD Silicon Computing Architecture",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="专用车规级高能效神经网络处理芯片 (NPU)",
        aliases=[
            "fsd芯片",
            "特斯拉自研芯片",
            "hw3芯片",
            "hw4芯片",
            "npu芯片",
            "双芯片冗余",
        ],
        summary="特斯拉完全自主研发的高能效车规级智驾专用芯片，单板配备两颗完全独立互为冗余的自研SoC，专为卷积神经网络硬件加速设计。",
        description=(
            "在传统车企依赖英伟达或Mobileye通用芯片时，特斯拉为了追求极致能效比从零开始自研硅片。芯片内部配备双NPU神经网络加速核心，"
            "单板集成双套独立电源、内存与通信总线。当其中一颗芯片出现极端意外宕机，另一颗芯片零时延接管确保自动驾驶不失控。"
        ),
        technical_principles=[
            "定制矩阵乘法器单元与SRAM本地超大高速缓存",
            "锁步双SoC独立计算互检安全冗余架构",
        ],
        advantages=[
            "硬件架构完全为自家神经网络量身定制，算力利用率高达90%以上",
            "双芯片冗余安全，为完全无人驾驶提供硬件级防失效保障",
        ],
        limitations=[
            "针对通用算法灵活性不如通用GPU，但对专用神经网络效率绝顶",
        ],
        sub_variants={},
        representative_vehicles=["Model 3", "Model Y", "Model S", "Model X", "Cybertruck"],
        standard_labels=["FSD芯片", "自研NPU", "双芯片冗余", "车规计算平台", "高能效计算"],
        equivalence_group_id=None,
        sales_talking_points=[
            "向追求底层核心技术的客户说明：‘很多车企只是买现成芯片攒车，特斯拉连核心智驾芯片都是自己从晶圆光刻开始正向设计，技术掌控力极强！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 28. 特斯拉 V3 超级充电桩体系 (250kW)
    TechnologyEntity(
        id="tesla_v3_supercharger",
        name="特斯拉 V3 250kW 超级充电网络",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Supercharger V3 250kW Liquid-Cooled Network",
        category=TechCategory.BATTERY_CHARGING,
        subcategory="全液冷细线缆高效超级补能站",
        aliases=[
            "v3超充",
            "250kw超充",
            "特斯拉v3",
            "特斯拉充电桩",
            "超充网络",
        ],
        summary="全球最普及的250kW峰值功率超充桩，采用液冷超细充电线，充电5分钟补充120公里续航，桩与桩之间不分流分流功率。",
        description=(
            "V3超充彻底终结了老款V2超充‘两辆车连在一个箱体功率减半’的痛点，每个车位独享高达250kW峰值输出。"
            "充电枪缆比普通快充桩细一半且极其柔软轻盈，女生单手轻松插拔；导航设置超充站后，车辆自动在行驶途中提前为电池加热至最理想充能温度。"
        ),
        technical_principles=[
            "直流母线架构与单桩独享大功率逆变整流模块",
            "车机导航目的地自动联动电池智能预热（Battery Preconditioning）",
        ],
        advantages=[
            "充电线极其轻巧，插枪即充毫无负担",
            "入站前电池提前预热，一插枪立刻飙上250kW峰值充电平台",
        ],
        limitations=[
            "充电末端（80%以上）为保护电池寿命充电功率会正常阶梯下降",
        ],
        sub_variants={},
        representative_vehicles=["Model 3", "Model Y", "Model S", "Model X"],
        standard_labels=["V3超充", "250kW功率", "电池预热", "液冷细枪线", "独享功率不分流"],
        equivalence_group_id=EquivalenceDomain.HIGH_VOLTAGE_800V_PLATFORM,
        sales_talking_points=[
            "向长途出行的客户展示导航：‘只要在车机导航里选好超充站，车子在路上就自己把电池加热到最佳温度，一到站插上枪就是最大功率，充15分钟就走！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 29. 特斯拉一体式低风阻封闭轮毂与空气动力轮盖
    TechnologyEntity(
        id="tesla_aero_wheels",
        name="特斯拉 Aero 动力学轮毂盖优化体系",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Aero Wheel Cover Aerodynamic System",
        category=TechCategory.PLATFORM_ARCHITECTURE,
        subcategory="低风阻车轮微气流导流与便携拆装",
        aliases=[
            "aero轮毂盖",
            "特斯拉轮毂盖",
            "低风阻轮毂",
            "动力学轮盖",
            "拆卸轮毂盖",
        ],
        summary="可随时徒手拆装的空气动力学导流轮毂盖，跑长途降低车轮风阻提升3-4%续航，拆下即变帅气铝合金运动轮毂。",
        description=(
            "车轮在高速旋转时产生的空气紊流占整车高速总风阻的三分之一。特斯拉自研Aero空气动力学导流盖，"
            "将车轮表面平整包裹引导侧方气流顺畅通过。跑长途多跑出几十公里续航；市区代步如果追求酷炫运动，卡扣徒手一掰就能取下露出里面的纯黑运动铝圈。"
        ),
        technical_principles=[
            "高强耐磨复合工程塑料卡扣机械自锁",
            "CFD轮端旋转湍流数值风洞模拟减阻设计",
        ],
        advantages=[
            "高速巡航增加近20-30公里续航，省电实打实",
            "兼顾‘想要省电’和‘想要帅气铝合金轮毂’的两面需求，随意切换",
        ],
        limitations=[
            "拆装时需注意顺着卡扣卡槽卡紧避免高速颠簸脱落",
        ],
        sub_variants={},
        representative_vehicles=["Model 3全系", "Model Y全系"],
        standard_labels=["Aero轮毂盖", "低风阻车轮", "长途省电", "两用轮毂", "徒手拆装"],
        equivalence_group_id=None,
        sales_talking_points=[
            "现场演示徒手拆装轮毂盖：‘跑长途装上轮毂盖更省电跑得更远，平时在市区拔下来就是纯黑运动铝合金轮毂，花一份钱拥有两种风格！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),

    # 30. 特斯拉全自研无雷达纯视觉倒车与 3D 环视高保真测距
    TechnologyEntity(
        id="tesla_vision_park_assist",
        name="特斯拉 Tesla Vision 高保真 3D 泊车辅助系统",
        brand="特斯拉 (Tesla)",
        brand_key="tesla",
        english_name="Tesla Vision High-Fidelity 3D Park Assist",
        category=TechCategory.AUTONOMOUS_DRIVING,
        subcategory="全纯视觉空间体素化高保真周围环境渲染",
        aliases=[
            "高保真泊车",
            "3d泊车辅助",
            "无超声波雷达倒车",
            "纯视觉倒车",
            "3d车周渲染",
        ],
        summary="彻底取消车身前后打孔超声波雷达，利用纯视觉算法实时重建车身四周厘米级3D高保真彩色立体点云模型。",
        description=(
            "在全面拥抱纯视觉后，特斯拉取消了保险杠上多余的雷达开孔。依靠车身摄像头在低速泊车时实时生成周围墙面、立柱、低矮马路牙子的高保真3D立体模型，"
            "中控屏幕上如同俯瞰真实三维微缩模型，距离障碍物多远以厘米级数字直观跳动，甚至能看清地上的停车线与凸起台阶。"
        ),
        technical_principles=[
            "多视角立体深度神经网络（MVS-Net）与隐式神经表面重建",
            "低速运动时空帧特征对齐推断前保险杠盲区不可见物体",
        ],
        advantages=[
            "车身保险杠完全纯平无任何雷达开孔，外观浑然一体更高级",
            "不仅能报警蜂鸣，更能真实还原障碍物三维立体形状和边界",
        ],
        limitations=[
            "遇到镜头被厚泥浆严重糊住时需先擦拭后视摄像头保证视线清晰",
        ],
        sub_variants={},
        representative_vehicles=["Model 3 Highland", "Model Y 2024款", "Cybertruck"],
        standard_labels=["高保真3D泊车", "Tesla Vision", "取消超声波雷达", "纯视觉测距", "厘米级渲染"],
        equivalence_group_id=EquivalenceDomain.URBAN_NOA_AUTONOMOUS_DRIVING,
        sales_talking_points=[
            "挂倒挡给客户展示中控大屏：‘看屏幕上，整个车周围的立柱、旁边的车甚至路牙子全部变成三维彩色模型，距离多少厘米清清楚楚，倒车再也不会刮蹭！’",
        ],
        maturity=TechMaturity.MASS_PRODUCTION,
    ),
]

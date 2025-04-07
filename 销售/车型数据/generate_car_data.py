import os
import json
from openai import OpenAI
from datetime import datetime

# Deepseek API配置
api_key = "sk-40f9ea6f41bd4cbbae8a9d4adb07fbf8"
client = OpenAI(
    api_key=api_key,
    base_url='https://api.deepseek.com/v1'  # 设置API基础URL
)

# 品牌和车型列表
BRANDS_AND_MODELS = {
    '奔驰': [
        {'car_series': 'C级', 'models': ['C200', 'C300', 'C43 AMG']},
        {'car_series': 'E级', 'models': ['E200', 'E300', 'E350']},
        {'car_series': 'S级', 'models': ['S400', 'S500', 'S580']},
        {'car_series': 'A级', 'models': ['A180', 'A200', 'AMG A35']},
        {'car_series': 'GLA', 'models': ['GLA200', 'GLA260', 'AMG GLA35']},
        {'car_series': 'GLB', 'models': ['GLB200', 'GLB260', 'AMG GLB35']},
        {'car_series': 'GLC', 'models': ['GLC260', 'GLC300', 'AMG GLC43']},
        {'car_series': 'GLE', 'models': ['GLE350', 'GLE450', 'AMG GLE53']},
        {'car_series': 'EQA', 'models': ['EQA250', 'EQA350']},
        {'car_series': 'EQB', 'models': ['EQB250', 'EQB350']},
        {'car_series': 'EQC', 'models': ['EQC400', 'AMG EQC']},
        {'car_series': 'EQE', 'models': ['EQE350', 'AMG EQE43']},
        {'car_series': 'EQS', 'models': ['EQS450', 'EQS580']}
    ],
    '宝马': [
        {'car_series': '3系', 'models': ['320i', '330i', 'M3']},
        {'car_series': '5系', 'models': ['520i', '530i', 'M5']},
        {'car_series': '7系', 'models': ['730i', '740i', '750i']},
        {'car_series': '1系', 'models': ['118i', '120i', 'M135i']},
        {'car_series': '2系', 'models': ['220i', '230i', 'M240i']},
        {'car_series': '4系', 'models': ['420i', '430i', 'M4']},
        {'car_series': '6系GT', 'models': ['630i', '640i']},
        {'car_series': '8系', 'models': ['840i', 'M850i', 'M8']},
        {'car_series': 'X1', 'models': ['sDrive20i', 'xDrive25i']},
        {'car_series': 'X3', 'models': ['xDrive30i', 'M40i', 'iX3']},
        {'car_series': 'X5', 'models': ['xDrive40i', 'M50i']},
        {'car_series': 'X7', 'models': ['xDrive40i', 'M50i']},
        {'car_series': 'iX', 'models': ['iX xDrive40', 'iX xDrive50']}
    ],
    '奥迪': [
        {'car_series': 'A4L', 'models': ['40 TFSI', '45 TFSI', '50 TFSI']},
        {'car_series': 'A6L', 'models': ['45 TFSI', '55 TFSI', '55 TFSI quattro']},
        {'car_series': 'Q5L', 'models': ['40 TFSI', '45 TFSI', '50 TFSI']},
        {'car_series': 'A3', 'models': ['35 TFSI', '40 TFSI']},
        {'car_series': 'A5', 'models': ['40 TFSI', '45 TFSI']},
        {'car_series': 'A7L', 'models': ['55 TFSI', '55 TFSI quattro']},
        {'car_series': 'A8L', 'models': ['55 TFSI', '60 TFSI']},
        {'car_series': 'Q2L', 'models': ['35 TFSI', '40 TFSI']},
        {'car_series': 'Q3', 'models': ['35 TFSI', '40 TFSI']},
        {'car_series': 'Q7', 'models': ['45 TFSI', '55 TFSI']},
        {'car_series': 'Q8', 'models': ['55 TFSI', 'RS Q8']},
        {'car_series': 'e-tron', 'models': ['50 quattro', '55 quattro']},
        {'car_series': 'RS e-tron GT', 'models': ['quattro']}
    ],
    '丰田': [
        {'car_series': '凯美瑞', 'models': ['2.0L', '2.5L', '双擎']},
        {'car_series': 'RAV4', 'models': ['2.0L', '2.5L', '双擎']},
        {'car_series': '汉兰达', 'models': ['2.0T', '2.5L', '双擎']},
        {'car_series': '卡罗拉', 'models': ['1.8L', '1.2T', '双擎']},
        {'car_series': '雷凌', 'models': ['1.8L', '1.2T', '双擎']},
        {'car_series': '亚洲龙', 'models': ['2.5L', '双擎']},
        {'car_series': '威兰达', 'models': ['2.0L', '双擎']},
        {'car_series': '奕泽', 'models': ['2.0L', '双擎']},
        {'car_series': '皇冠', 'models': ['2.5L', '双擎']},
        {'car_series': '普拉多', 'models': ['2.7L', '3.5L']},
        {'car_series': '兰德酷路泽', 'models': ['4.0L', '3.5T']},
        {'car_series': 'bZ4X', 'models': ['前驱', '四驱']},
        {'car_series': 'bZ3', 'models': ['标准续航', '长续航']}
    ],
    '本田': [
        {'car_series': '雅阁', 'models': ['锐·混动e+', '锐·混动e:PHEV']},
        {'car_series': 'CR-V', 'models': ['锐·混动', '锐·混动e+']},
        {'car_series': '思域', 'models': ['240TURBO', '锐·混动e+']},
        {'car_series': '冠道', 'models': ['370TURBO', '锐·混动e+']},
        {'car_series': '皓影', 'models': ['锐·混动', '锐·混动e+']},
        {'car_series': '奥德赛', 'models': ['锐·混动', '锐·混动e+']},
        {'car_series': '飞度', 'models': ['锐·混动', '锐·混动e+']},
        {'car_series': '竞瑞', 'models': ['锐·混动', '锐·混动e+']},
        {'car_series': 'e:NS1', 'models': ['标准续航', '长续航']},
        {'car_series': 'e:NP1', 'models': ['标准续航', '长续航']},
        {'car_series': 'e:N2', 'models': ['标准续航', '长续航']},
        {'car_series': 'e:N GT', 'models': ['标准续航', '长续航']},
        {'car_series': 'e:N SUV', 'models': ['标准续航', '长续航']}
    ],
    '比亚迪': [
        {'car_series': '汉', 'models': ['DM-i', 'DM-p', 'EV']},
        {'car_series': '宋', 'models': ['PLUS DM-i', 'PLUS EV', 'MAX']},
        {'car_series': '海豚', 'models': ['致臻版', '尊贵版', '智行版']},
        {'car_series': '秦', 'models': ['PLUS DM-i', 'PLUS EV']},
        {'car_series': '元', 'models': ['PLUS DM-i', 'PLUS EV']},
        {'car_series': '唐', 'models': ['DM-i', 'DM-p', 'EV']},
        {'car_series': '海豹', 'models': ['致臻版', '性能版']},
        {'car_series': '驱逐舰05', 'models': ['致臻版', '性能版']},
        {'car_series': '护卫舰07', 'models': ['致臻版', '性能版']},
        {'car_series': '海鸥', 'models': ['致臻版', '性能版']},
        {'car_series': '刀片电池版', 'models': ['标准续航', '长续航']},
        {'car_series': '仰望', 'models': ['U8', 'U9']},
        {'car_series': '腾势', 'models': ['D9', 'N7']}
    ],
    '特斯拉': [
        {'car_series': 'Model 3', 'models': ['标准续航', '长续航', '高性能版']},
        {'car_series': 'Model Y', 'models': ['标准续航', '长续航', '高性能版']},
        {'car_series': 'Model S', 'models': ['长续航', 'Plaid']},
        {'car_series': 'Model X', 'models': ['长续航', 'Plaid']},
        {'car_series': 'Cybertruck', 'models': ['单电机', '双电机', '三电机']},
        {'car_series': 'Roadster', 'models': ['标准版', 'Founders Series']},
        {'car_series': 'Semi', 'models': ['标准版', '长续航版']},
        {'car_series': 'Model 2', 'models': ['标准续航', '长续航']},
        {'car_series': 'Model C', 'models': ['标准续航', '长续航']},
        {'car_series': 'Model A', 'models': ['标准续航', '长续航']},
        {'car_series': 'Model E', 'models': ['标准续航', '长续航']},
        {'car_series': 'Model R', 'models': ['标准续航', '长续航']},
        {'car_series': 'Model V', 'models': ['标准续航', '长续航']}
    ],
    '蔚来': [
        {'car_series': 'ET7', 'models': ['75kWh', '100kWh']},
        {'car_series': 'ES6', 'models': ['75kWh', '100kWh']},
        {'car_series': 'ES8', 'models': ['75kWh', '100kWh']},
        {'car_series': 'EC6', 'models': ['75kWh', '100kWh']},
        {'car_series': 'ET5', 'models': ['75kWh', '100kWh']},
        {'car_series': 'ES7', 'models': ['75kWh', '100kWh']},
        {'car_series': 'EC7', 'models': ['75kWh', '100kWh']},
        {'car_series': 'EL6', 'models': ['75kWh', '100kWh']},
        {'car_series': 'EL7', 'models': ['75kWh', '100kWh']},
        {'car_series': 'ET9', 'models': ['75kWh', '100kWh']},
        {'car_series': 'EF9', 'models': ['75kWh', '100kWh']},
        {'car_series': 'EH9', 'models': ['75kWh', '100kWh']},
        {'car_series': 'EP9', 'models': ['标准版', '赛道版']}
    ],
    '小鹏': [
        {'car_series': 'P7', 'models': ['智驾版', '超长续航版']},
        {'car_series': 'G9', 'models': ['RWD', '4WD']},
        {'car_series': 'P5', 'models': ['标准续航', '长续航']},
        {'car_series': 'G3i', 'models': ['标准续航', '长续航']},
        {'car_series': 'G6', 'models': ['标准续航', '长续航']},
        {'car_series': 'G7', 'models': ['标准续航', '长续航']},
        {'car_series': 'X9', 'models': ['标准续航', '长续航']},
        {'car_series': 'P9', 'models': ['标准续航', '长续航']},
        {'car_series': 'E9', 'models': ['标准续航', '长续航']},
        {'car_series': 'S9', 'models': ['标准版', '性能版']},
        {'car_series': 'F9', 'models': ['标准续航', '长续航']},
        {'car_series': 'H9', 'models': ['标准续航', '长续航']},
        {'car_series': 'K9', 'models': ['标准续航', '长续航']}
    ],
    '理想': [
        {'car_series': 'L7', 'models': ['Pro', 'Max']},
        {'car_series': 'L9', 'models': ['Pro', 'Max']},
        {'car_series': 'L8', 'models': ['Pro', 'Max']},
        {'car_series': 'L6', 'models': ['Pro', 'Max']},
        {'car_series': 'L5', 'models': ['Pro', 'Max']},
        {'car_series': 'L4', 'models': ['Pro', 'Max']},
        {'car_series': 'L3', 'models': ['Pro', 'Max']},
        {'car_series': 'MEGA', 'models': ['Pro', 'Max']},
        {'car_series': 'X01', 'models': ['Pro', 'Max']},
        {'car_series': 'X02', 'models': ['Pro', 'Max']},
        {'car_series': 'X03', 'models': ['Pro', 'Max']},
        {'car_series': 'X04', 'models': ['Pro', 'Max']},
        {'car_series': 'X05', 'models': ['Pro', 'Max']}
    ]
}

# 数据模板
DATA_TEMPLATE = """
# {brand}{car_series} {model} {year}款
## 1. 车型基本信息
### 品牌信息
- 品牌名称：{brand}
- 品牌定位：德系豪华品牌
- 品牌历史：1926年创立，全球最古老的汽车品牌之一
- 品牌国别：德国

### 车型信息
- 车系名称：{car_series}
- 具体型号：{model}
- 年款信息：{year}款

{car_info}
"""

def create_brand_folders():
    """创建品牌文件夹结构"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    for brand in BRANDS_AND_MODELS.keys():
        brand_path = os.path.join(base_path, brand)
        os.makedirs(brand_path, exist_ok=True)

def generate_car_data(brand, car_series, model, year):
    """使用OpenAI API生成车型数据"""
    prompt = f"""请生成一个详细的{brand} {car_series} {model} {year}款车型信息，包括：
    1. 车身尺寸、轴距、整备质量等基本参数
    2. 外观配置（车身颜色、轮毂、大灯、天窗等）
    3. 动力系统（发动机/电机、变速箱、驱动方式等）
    4. 性能参数（最大功率、最大扭矩、百公里加速等）
    5. 内饰配置（座椅材质、方向盘、空调、储物等）
    6. 智能系统（中控屏、车机系统、手机互联等）
    7. 安全配置（安全气囊、辅助驾驶、胎压监测等）
    8. 价格信息（官方指导价、可选套餐、保养成本等）
    请确保信息准确、专业，并符合市场实际情况。"""

    try:
        response = client.chat.completions.create(
            model='deepseek-chat',
            messages=[
                {
                    'role': 'system',
                    'content': '你是一个专业的汽车行业分析师，熟悉各品牌车型的详细信息。'
                },
                {
                    'role': 'user',
                    'content': prompt
                }
            ],
            temperature=0.7
        )
        
        # 直接使用API返回的文本数据
        car_info = response.choices[0].message.content
        
        # 将数据填充到模板中
        formatted_data = DATA_TEMPLATE.format(
            brand=brand,
            car_series=car_series,
            model=model,
            year=year,
            car_info=car_info
        )
        
        return formatted_data
    except Exception as e:
        print(f"生成数据时出错：{str(e)}")
        return None

def save_car_data(brand, car_series, model, year, data):
    """保存车型数据到文件"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    filename = f"{car_series}-{model}-{year}.md"
    file_path = os.path.join(base_path, brand, filename)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(data)
        print(f"成功保存文件：{filename}")
    except Exception as e:
        print(f"保存文件时出错：{str(e)}")

def check_existing_file(brand, car_series, model, year):
    """检查车型文件是否已存在"""
    base_path = os.path.dirname(os.path.abspath(__file__))
    filename = f"{car_series}-{model}-{year}.md"
    file_path = os.path.join(base_path, brand, filename)
    return os.path.exists(file_path)

def main():
    """主函数"""
    create_brand_folders()
    year = "2024"
    
    for brand, car_series_list in BRANDS_AND_MODELS.items():
        print(f"正在处理{brand}品牌的车型数据...")
        for series_info in car_series_list:
            car_series = series_info['car_series']
            for model in series_info['models']:
                if not check_existing_file(brand, car_series, model, year):
                    print(f"生成{brand} {car_series} {model} {year}款数据...")
                    car_data = generate_car_data(brand, car_series, model, year)
                    if car_data:
                        save_car_data(brand, car_series, model, year, car_data)
                else:
                    print(f"跳过已存在的车型：{brand} {car_series} {model} {year}款")


if __name__ == "__main__":
    main()
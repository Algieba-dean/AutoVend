# 超轻量级隐式标签预测模型

本项目开发了一个极度优化的隐式标签预测模型，专为资源受限环境设计。它能够从车辆查询文本中预测隐式标签，模型体积仅为原始BERT模型的4%左右。

## 主要特点

- 超小模型体积：只有约17MB，比标准BERT小96%
- 超快推理速度：每次推理仅需几毫秒
- 低内存占用：适合边缘设备和嵌入式系统
- 多种优化技术：包括微型Transformer、剪枝、INT8量化等
- 支持ONNX导出：便于跨平台部署

## 目录结构

```
.
├── README.md                          # 主文档
├── README_ULTRA_LIGHT.md              # 超轻量级模型详细文档
├── QueryLabels.json                   # 标签定义
├── dataset.py                         # 数据集处理类
├── utils.py                           # 工具函数
├── example_dataset.json               # 示例训练数据
├── ultra_light_model.py               # 超轻量级模型实现
├── ultra_light_predictor.py           # 超轻量级预测器
├── train_ultra_light_model.py         # 训练脚本
├── ultra_light_predictor_example.py   # 使用示例
└── requirements.txt                   # 依赖项
```

## 安装

1. 安装依赖:

```bash
pip install -r requirements.txt
```

2. 确保您的项目目录中包含QueryLabels.json文件

## 使用方法

### 训练模型

使用默认参数训练模型:

```bash
python train_ultra_light_model.py
```

使用自定义参数:

```bash
python train_ultra_light_model.py --config QueryLabels.json --dataset example_dataset.json --model_name prajjwal1/bert-tiny --max_seq_length 32 --hidden_dim 128 --embedding_pruning 0.3 --epochs 15 --quantize --export_onnx
```

### 主要参数

- `--config`: 标签配置文件路径 (默认: 'QueryLabels.json')
- `--dataset`: 数据集文件路径 (默认: 'example_dataset.json')
- `--model_name`: 预训练模型名称 (默认: 'prajjwal1/bert-tiny')
- `--max_seq_length`: 最大序列长度 (默认: 32)
- `--hidden_dim`: 隐藏层维度 (默认: 128)
- `--embedding_pruning`: 嵌入层剪枝率 (默认: 0.3)
- `--quantize`: 训练后应用INT8量化
- `--export_onnx`: 训练后导出为ONNX格式

### 预测示例

训练完成后，您可以使用模型预测新查询的隐式标签:

```python
from ultra_light_predictor import UltraLightPredictor

# 初始化预测器
predictor = UltraLightPredictor(
    model_path='outputs/best_ultra_light_model.pt',
    config_path='QueryLabels.json',
    max_seq_length=32,
    hidden_dim=128,
    quantize=True  # 应用量化(仅CPU)
)

# 进行预测
query = "我需要一台经济实惠、油耗低的城市代步车"
predictions = predictor.predict(query)

# 打印结果
print(f"查询: {query}")
for label, value in predictions.items():
    print(f"  {label}: {value}")

# 批量处理
queries = ["我想要一辆豪华SUV", "我需要一款电动车"]
batch_results = predictor.predict_batch(queries)
```

## 性能指标

- **模型大小**: ~17MB (相比标准BERT的~400MB小约96%)
- **加载时间**: ~3秒
- **推理时间**: ~4.2ms/查询
- **内存占用**: 极低

## 应用场景

该超轻量级模型特别适用于:
- 边缘设备和嵌入式系统
- 移动应用
- 需要低延迟处理的场景
- 离线应用

## 延伸阅读

详细的模型说明、优化技术和使用指南请参考 [README_ULTRA_LIGHT.md](README_ULTRA_LIGHT.md) 
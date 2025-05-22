# 超轻量级隐式标签预测模型 (Ultra-Lightweight Implicit Label Predictor)

一个经过极度优化的隐式标签预测模型，专为资源受限环境设计，如边缘设备、移动应用和嵌入式系统。

## 主要特点

- **极小的模型体积**: 整个模型仅约16-17MB，相比标准BERT模型缩小了96%
- **极快的推理速度**: 每次推理只需几毫秒
- **低内存占用**: 运行时内存占用极低
- **支持多种优化**: 包括量化、剪枝、ONNX导出等
- **保持基本准确率**: 虽然体积极小，但仍保持基本的预测准确率

## 优化技术

该超轻量级模型采用了以下多种优化技术:

1. **微型基础模型**: 使用`prajjwal1/bert-tiny`作为基础模型，而非完整BERT
2. **极少层数**: 仅使用2层transformer层，标准BERT有12层，DistilBERT有6层
3. **减少注意力头**: 每层仅使用2个注意力头
4. **超短序列长度**: 输入序列限制为32个token，而不是通常的128或512
5. **嵌入层剪枝**: 30%的嵌入权重被剪枝为0
6. **降维投影**: 添加额外投影层减少特征维度
7. **共享表示层**: 所有标签分类器共享部分表示，减少参数数量
8. **INT8量化**: 将模型权重量化为8位整数，进一步减小体积
9. **ONNX导出**: 支持导出到ONNX格式，便于在各种平台高效部署

## 安装

```bash
pip install -r requirements.txt
```

## 训练超轻量级模型

```bash
python train_ultra_light_model.py --dataset example_dataset.json --config QueryLabels.json --epochs 15 --embedding_pruning 0.3
```

主要参数:
- `--model_name`: 预训练基础模型名称 (默认: 'prajjwal1/bert-tiny')
- `--max_seq_length`: 最大序列长度 (默认: 32)
- `--hidden_dim`: 隐藏层维度 (默认: 128)
- `--embedding_pruning`: 嵌入层剪枝率 (默认: 0.3)
- `--quantize`: 启用INT8量化 (仅CPU)
- `--export_onnx`: 训练后导出为ONNX格式
- `--distillation`: 启用知识蒸馏训练

## 使用方法

```python
from ultra_light_predictor import UltraLightPredictor

# 初始化超轻量级预测器
predictor = UltraLightPredictor(
    model_path='outputs/best_ultra_light_model.pt',
    config_path='QueryLabels.json',
    max_seq_length=32,
    hidden_dim=128,
    quantize=True  # 启用量化以进一步减小模型体积(仅CPU)
)

# 进行单条查询预测
query = "我需要一辆经济实惠、油耗低的城市代步车"
result = predictor.predict(query)  # 默认只返回非none值

# 打印结果
print(f"查询: {query}")
for label, value in result.items():
    print(f"  {label}: {value}")

# 批量处理查询
queries = [
    "我想要一辆豪华SUV，性能强劲，配置高端",
    "我需要一款电动车，续航里程长",
    "我想买一辆宽敞的家用车，安全性能好"
]
batch_results = predictor.predict_batch(queries)

# 导出到ONNX以获得更高性能
predictor.export_to_onnx("ultra_light_model.onnx")
```

## 性能对比

| 模型类型 | 模型大小 | 加载时间 | 推理时间 | 内存占用 |
|---------|---------|---------|---------|----------|
| 标准BERT | ~400MB  | ~3秒    | ~9ms    | 高       |
| 轻量级   | ~250MB  | ~1秒    | ~4.5ms  | 中       |
| 超轻量级 | ~17MB   | ~3秒    | ~4.2ms  | 极低     |

## 应用场景

- **移动应用**: 手机应用中需要本地进行语言理解的场景
- **嵌入式设备**: 资源受限的IoT设备和嵌入式系统
- **边缘计算**: 需要在边缘设备上进行实时语言处理
- **低延迟需求**: 对推理速度有极高要求的应用
- **离线应用**: 不依赖网络连接的离线应用

## 注意事项

- 与标准模型相比，超轻量级模型可能在某些特定场景下准确率略有下降
- INT8量化仅在CPU上有效，GPU上不支持此功能
- 更复杂的查询可能需要调整max_seq_length参数以获取更好结果

## 示例运行

```bash
python ultra_light_predictor_example.py
```

该示例将加载超轻量级模型，显示其性能统计信息，并进行演示预测。 
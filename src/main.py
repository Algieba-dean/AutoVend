"""
AutoVend RAG Agent 主程序

提供命令行接口用于构建索引和执行检索。
"""

import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 现在可以使用相对导入
from src.models.query import Query
from src.rag.embeddings import BGEEmbeddingModel
from src.rag.index_builder import IndexBuilder
from src.rag.retriever import VehicleRetriever
from src.rag.vector_store import ChromaVectorStore
from src.utils.config import config
from src.utils.logger import get_logger, setup_logging


def setup_cli_logging():
    """设置CLI日志"""
    log_level = config.log_level.upper()
    setup_logging(level=log_level, enable_rich=True)


def build_index_command(args) -> None:
    """构建索引命令"""
    logger = get_logger()

    try:
        logger.info("开始构建车辆向量索引...")

        builder = IndexBuilder(
            data_dir=args.data_dir,
            persist_directory=args.persist_dir,
            collection_name=args.collection_name,
            batch_size=args.batch_size,
        )

        result = builder.build_index(
            force_rebuild=args.force,
            validate_data=args.validate,
            parallel_loading=not args.sequential,
        )

        if result["status"] == "success":
            logger.info("✅ 索引构建成功!")
            logger.info(f"处理车辆数: {result['stats']['processed_vehicles']}")
            logger.info(f"构建耗时: {result['stats']['build_time']:.2f}秒")
            logger.info(f"集合信息: {result['collection_info']['count']} 个文档")
        else:
            logger.error(f"❌ 索引构建失败: {result['status']}")
            sys.exit(1)

    except Exception as e:
        logger.error(f"❌ 构建索引时发生错误: {e}")
        sys.exit(1)


def search_command(args) -> None:
    """搜索命令"""
    logger = get_logger()

    try:
        # 初始化组件
        embedding_model = BGEEmbeddingModel()
        vector_store = ChromaVectorStore()
        retriever = VehicleRetriever(
            embedding_model=embedding_model,
            vector_store=vector_store,
            similarity_threshold=0.3,  # 降低阈值
            price_tolerance=args.price_tolerance,
        )

        # 创建查询
        query = Query(text=args.query, top_k=args.top_k)

        logger.info(f"🔍 搜索: {args.query}")

        # 执行搜索
        response = retriever.search(query)

        # 显示结果
        if not response.results:
            logger.info("❌ 未找到匹配的车辆")
            return

        logger.info(
            f"✅ 找到 {len(response.results)} 个匹配结果，耗时 {response.search_time:.2f}秒"
        )
        logger.info(f"📊 {response.get_summary()}")

        # 显示详细结果
        for i, result in enumerate(response.results[: args.show], 1):
            logger.info(f"\n🚗 结果 {i}: {result.vehicle.car_model}")
            logger.info(f"   匹配度: {result.score.overall_score:.3f}")
            logger.info(f"   品牌: {result.vehicle.precise_labels.brand or '未知'}")
            logger.info(
                f"   车型: {result.vehicle.precise_labels.vehicle_category_bottom or '未知'}"
            )
            logger.info(f"   价格: {result.vehicle.precise_labels.prize or '未知'}")
            logger.info(f"   说明: {result.explanation}")

            if result.score.matched_features:
                logger.info(f"   匹配特征: {', '.join(result.score.matched_features)}")

    except Exception as e:
        logger.error(f"❌ 搜索时发生错误: {e}")
        sys.exit(1)


def status_command(args) -> None:
    """状态命令"""
    logger = get_logger()

    try:
        # 检查索引状态
        vector_store = ChromaVectorStore()
        collection_info = vector_store.get_collection_info()

        logger.info("📊 AutoVend RAG 系统状态")
        logger.info("=" * 50)
        logger.info(f"集合名称: {collection_info.get('name', '未知')}")
        logger.info(f"文档数量: {collection_info.get('count', 0)}")
        logger.info(f"距离度量: {collection_info.get('distance_metric', '未知')}")
        logger.info(f"存储目录: {collection_info.get('persist_directory', '未知')}")

        # 检查数据目录
        data_path = Path(config.vehicle_data_dir)
        if data_path.exists():
            toml_files = list(data_path.rglob("*.toml"))
            logger.info(f"数据文件: {len(toml_files)} 个TOML文件")
        else:
            logger.warning(f"数据目录不存在: {data_path}")

        # 检查嵌入模型
        try:
            embedding_model = BGEEmbeddingModel()
            logger.info(f"嵌入模型: {embedding_model.model_name}")
            logger.info(f"嵌入维度: {embedding_model.embed_dimension}")
            logger.info(f"使用设备: {embedding_model.device}")
        except Exception as e:
            logger.warning(f"嵌入模型初始化失败: {e}")

    except Exception as e:
        logger.error(f"❌ 获取状态时发生错误: {e}")
        sys.exit(1)


def test_command(args) -> None:
    """测试命令"""
    logger = get_logger()

    try:
        # 初始化组件
        embedding_model = BGEEmbeddingModel()
        vector_store = ChromaVectorStore()
        retriever = VehicleRetriever(
            embedding_model=embedding_model,
            vector_store=vector_store,
            similarity_threshold=0.3,  # 降低阈值
            price_tolerance=0.2,
        )

        # 测试查询
        test_queries = [
            "30万左右的家用SUV",
            "丰田轿车",
            "新能源车推荐",
            "商务MPV",
            "预算20万的家用车",
        ]

        logger.info("🧪 开始检索准确性测试")
        logger.info("=" * 50)

        total_score = 0.0
        successful_queries = 0

        for i, query_text in enumerate(test_queries, 1):
            logger.info(f"\n测试 {i}: {query_text}")

            try:
                query = Query(text=query_text, top_k=5)
                response = retriever.search(query)

                if response.results:
                    top_score = response.results[0].score.overall_score
                    total_score += top_score
                    successful_queries += 1

                    logger.info(f"   ✅ 找到 {len(response.results)} 个结果")
                    logger.info(f"   🎯 最佳匹配: {response.results[0].vehicle.car_model}")
                    logger.info(f"   📊 匹配度: {top_score:.3f}")
                    logger.info(f"   ⏱️  耗时: {response.search_time:.2f}秒")
                else:
                    logger.warning("   ❌ 未找到匹配结果")

            except Exception as e:
                logger.error(f"   ❌ 测试失败: {e}")

        # 计算平均分数
        if successful_queries > 0:
            avg_score = total_score / successful_queries
            logger.info("\n📈 测试总结:")
            logger.info(f"   成功查询: {successful_queries}/{len(test_queries)}")
            logger.info(f"   平均匹配度: {avg_score:.3f}")
            logger.info(f"   系统状态: {'良好' if avg_score > 0.7 else '需要优化'}")
        else:
            logger.error("\n❌ 所有测试查询都失败了")

    except Exception as e:
        logger.error(f"❌ 测试时发生错误: {e}")
        sys.exit(1)


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="AutoVend RAG Agent - 智能汽车销售助手",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  python src/main.py build                    # 构建索引
  python src/main.py search "30万左右家用SUV"  # 搜索车辆
  python src/main.py status                   # 查看系统状态
  python src/main.py test                     # 运行测试
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # 构建索引命令
    build_parser = subparsers.add_parser("build", help="构建向量索引")
    build_parser.add_argument("--data-dir", help="数据目录路径")
    build_parser.add_argument("--persist-dir", help="向量存储目录")
    build_parser.add_argument("--collection-name", help="集合名称")
    build_parser.add_argument("--batch-size", type=int, default=100, help="批处理大小")
    build_parser.add_argument("--force", action="store_true", help="强制重建索引")
    build_parser.add_argument("--validate", action="store_true", default=True, help="验证数据")
    build_parser.add_argument("--sequential", action="store_true", help="顺序加载数据")

    # 搜索命令
    search_parser = subparsers.add_parser("search", help="搜索车辆")
    search_parser.add_argument("query", help="搜索查询")
    search_parser.add_argument("--top-k", type=int, default=10, help="返回结果数量")
    search_parser.add_argument("--threshold", type=float, default=0.7, help="相似度阈值")
    search_parser.add_argument("--price-tolerance", type=float, default=0.2, help="价格容忍度")
    search_parser.add_argument("--show", type=int, default=5, help="显示结果数量")

    # 状态命令
    subparsers.add_parser("status", help="查看系统状态")

    # 测试命令
    subparsers.add_parser("test", help="运行检索测试")

    # 解析参数
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # 设置日志
    setup_cli_logging()

    # 执行命令
    if args.command == "build":
        build_index_command(args)
    elif args.command == "search":
        search_command(args)
    elif args.command == "status":
        status_command(args)
    elif args.command == "test":
        test_command(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

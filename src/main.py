"""
AutoVend RAG Agent 主程序

提供命令行接口用于构建索引和执行检索。
"""

import argparse
import sys
import time
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
    """
    构建全部三层索引：SQLite 结构化目录、ChromaDB 向量索引、BM25 稀疏索引。

    三者都显式构建，而不是留给首次查询懒加载 —— 否则 CI 里的构建步骤会通过，
    真正的失败要等到评估门禁才暴露，排查时得倒推一层。
    """
    logger = get_logger()

    try:
        # 1. SQLite 结构化目录（元数据预过滤的数据源，也是 BM25 的语料源）
        logger.info("开始构建 SQLite 结构化目录...")
        from src.filter.vehicle_db import VehicleDB

        db = VehicleDB()
        if args.force or db.count() == 0:
            db.import_from_toml_dir()
        logger.info(f"✅ SQLite 目录就绪: {db.count()} 辆车")

        # 2. ChromaDB 向量索引
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

        # 3. BM25 稀疏索引
        logger.info("开始构建 BM25 稀疏索引...")
        from src.retrieval.bm25_index import BM25Index

        bm25 = BM25Index.build(db=db)
        bm25.save()
        logger.info(f"✅ BM25 索引就绪: {len(bm25)} 条")

    except Exception as e:
        logger.error(f"❌ 构建索引时发生错误: {e}")
        sys.exit(1)


def search_command(args) -> None:
    """搜索命令 - 接入生产级 TieredRetrievalEngine, HybridPipeline 与 RankRefiner"""
    logger = get_logger()

    try:
        from src.core.compression import ContextCompressor
        from src.filter.vehicle_db import VehicleDB
        from src.rag_service.reranker import RankRefiner
        from src.rag_service.schemas import VehicleQueryRequest, VehicleSearchResult
        from src.retrieval.adapters import hybrid_result_to_cars
        from src.retrieval.hybrid_pipeline import build_hybrid_pipeline
        from src.retrieval.tiered_engine import TieredRetrievalEngine

        logger.info(f"🔍 启动分级检索引擎搜索: '{args.query}' (top_k={args.top_k})")
        start_time = time.time()

        db = VehicleDB()
        pipeline = None
        try:
            pipeline = build_hybrid_pipeline(
                similarity_threshold=getattr(args, "threshold", 0.3),
                price_tolerance=getattr(args, "price_tolerance", 0.2),
                enable_sparse=True,
            )
        except Exception as pipe_err:
            logger.warning(f"构建混合管道提示 ({pipe_err})，使用降级敏捷模式")

        tiered_engine = TieredRetrievalEngine.get_instance(
            db=db,
            hybrid_pipeline=pipeline,
        )

        request = VehicleQueryRequest(
            query_text=args.query,
            top_k=args.top_k,
            enable_rerank=getattr(args, "enable_rerank", True),
        )

        # 1. 优先经由 TieredRetrievalEngine 智能路由 (Tier 0 极速规格匹配 / Tier 1 敏捷混合召回)
        tiered_res = tiered_engine.search(request)
        elapsed = time.time() - start_time

        results: List[VehicleSearchResult] = []
        routing_tier = 1
        routing_reason = "Agile Hybrid Retrieval"

        if tiered_res and tiered_res.results:
            results = list(tiered_res.results)
            routing_tier = tiered_res.tier
            routing_reason = tiered_res.routing_reason
        elif pipeline is not None:
            # 回退调用 hybrid pipeline
            pipe_res = pipeline.search(args.query, top_k=args.top_k * 2)
            cars = hybrid_result_to_cars(pipe_res, limit=args.top_k * 2)
            for c in cars:
                meta = c.get("metadata", {})
                results.append(
                    VehicleSearchResult(
                        car_model=c.get("car_model", ""),
                        score=float(c.get("score", 0.0)),
                        brand=meta.get("brand", ""),
                        price=meta.get("price", ""),
                        category=meta.get("category", ""),
                        powertrain_type=meta.get("powertrain_type", ""),
                        metadata=meta,
                        text_snippet=c.get("text_snippet", ""),
                    )
                )
            routing_tier = 1
            routing_reason = "HybridPipeline Direct"
        else:
            # 兼容老版纯向量检索
            embedding_model = BGEEmbeddingModel()
            vector_store = ChromaVectorStore()
            retriever = VehicleRetriever(
                embedding_model=embedding_model,
                vector_store=vector_store,
                similarity_threshold=getattr(args, "threshold", 0.3),
                price_tolerance=getattr(args, "price_tolerance", 0.2),
            )
            old_resp = retriever.search(Query(text=args.query, top_k=args.top_k))
            for r in old_resp.results:
                results.append(
                    VehicleSearchResult(
                        car_model=r.vehicle.car_model,
                        score=r.score.overall_score,
                        brand=r.vehicle.precise_labels.brand or "",
                        price=r.vehicle.precise_labels.price or "",
                        category=r.vehicle.precise_labels.vehicle_category_bottom or "",
                        powertrain_type=r.vehicle.precise_labels.powertrain_type or "",
                        metadata={},
                        text_snippet=r.vehicle.get_search_text(),
                    )
                )
            routing_tier = 1
            routing_reason = "VehicleRetriever Fallback"

        # 2. 调用 RankRefiner 进行平滑预算高斯衰减与多属性凸组合精排
        if results and getattr(args, "enable_rerank", True):
            results = RankRefiner.refine(
                query_text=args.query,
                results=results,
                top_k=args.top_k,
            )

        if not results:
            logger.info("❌ 未找到匹配的车辆")
            return

        logger.info(
            f"✅ 找到 {len(results)} 个匹配结果，耗时 {elapsed:.2f}秒 (分级: Tier {routing_tier} - {routing_reason})"
        )

        # 显示详细结果
        show_count = getattr(args, "show", 5)
        for i, res in enumerate(results[:show_count], 1):
            logger.info(f"\n🚗 结果 {i}: {res.car_model}")
            logger.info(f"   综合匹配得分: {res.score:.4f}")
            if "spec_alignment_score" in res.metadata:
                logger.info(f"   规格契合得分: {res.metadata['spec_alignment_score']:.3f}")
            logger.info(f"   品牌: {res.brand or '未知'}")
            logger.info(f"   车型: {res.category or '未知'}")
            logger.info(f"   价格: {res.price or '未知'}")
            if res.powertrain_type:
                logger.info(f"   动力: {res.powertrain_type}")
            if res.text_snippet:
                snippet = ContextCompressor.clean_marketing_fluff(res.text_snippet, query_text=args.query)
                clean_snippet = snippet[:120] + "..." if len(snippet) > 120 else snippet
                logger.info(f"   亮点: {clean_snippet}")

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
    """测试命令 - 验证生产级分级检索与精排表现"""
    logger = get_logger()

    try:
        from src.filter.vehicle_db import VehicleDB
        from src.rag_service.reranker import RankRefiner
        from src.rag_service.schemas import VehicleQueryRequest
        from src.retrieval.hybrid_pipeline import build_default_pipeline
        from src.retrieval.tiered_engine import TieredRetrievalEngine

        db = VehicleDB()
        pipeline = None
        try:
            pipeline = build_default_pipeline(similarity_threshold=0.3, enable_sparse=True)
        except Exception as e:
            logger.warning(f"构建混合管道提示: {e}")

        tiered_engine = TieredRetrievalEngine.get_instance(db=db, hybrid_pipeline=pipeline)

        test_queries = [
            "30万左右的家用SUV",
            "丰田轿车",
            "新能源车推荐",
            "商务MPV",
            "预算20万的家用车",
            "极氪001 和 汉EV 对比续航",
        ]

        logger.info("🧪 开始分级检索与精排准确性测试")
        logger.info("=" * 50)

        total_score = 0.0
        successful_queries = 0

        for i, query_text in enumerate(test_queries, 1):
            logger.info(f"\n测试 {i}: {query_text}")

            try:
                req = VehicleQueryRequest(query_text=query_text, top_k=5, enable_rerank=True)
                tiered_res = tiered_engine.search(req)

                results = list(tiered_res.results) if tiered_res and tiered_res.results else []
                if results:
                    results = RankRefiner.refine(query_text, results, top_k=5)

                if results:
                    top_score = results[0].score
                    total_score += top_score
                    successful_queries += 1

                    tier_str = f"Tier {tiered_res.tier}" if tiered_res else "Tier 1"
                    reason_str = tiered_res.routing_reason if tiered_res else "Standard"
                    lat_str = f"{tiered_res.latency_ms:.2f}ms" if tiered_res else "N/A"

                    logger.info(f"   ✅ 找到 {len(results)} 个结果 ({tier_str}: {reason_str})")
                    logger.info(f"   🎯 最佳匹配: {results[0].car_model}")
                    logger.info(f"   📊 匹配度: {top_score:.3f}")
                    logger.info(f"   ⏱️  耗时: {lat_str}")
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
            logger.info(f"   系统状态: {'良好' if avg_score > 0.5 else '需要优化'}")
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
    search_parser.add_argument("--no-rerank", dest="enable_rerank", action="store_false", default=True, help="禁用RankRefiner精排")

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

"""
Unified CLI for Universal Automotive Web Crawler.
Usage:
  python -m src.crawler.cli crawl --brand "比亚迪"
  python -m src.crawler.cli crawl-multi --brands "比亚迪,特斯拉,理想,蔚来,小鹏"
  python -m src.crawler.cli list-brands
  python -m src.crawler.cli list-serials --brand "比亚迪"
  python -m src.crawler.cli stats
  python -m src.crawler.cli queue-stats
"""

import asyncio
import click
from rich.console import Console
from rich.table import Table

from src.crawler.adapters.yiche_adapter import CANONICAL_BRAND_SLUGS, YicheSiteAdapter
from src.crawler.engine import UniversalCrawlerEngine
from src.crawler.schemas import BrandMeta
from src.crawler.scheduler.task_queue import SQLiteTaskQueue
from src.crawler.storage import RawDataStorage

console = Console()


@click.group()
def cli():
    """Universal Automotive Web Crawler CLI."""
    pass


@cli.command("list-brands")
def list_brands():
    """List all supported and discoverable automotive brands."""
    table = Table(title="Discoverable Automotive Brands")
    table.add_column("Brand Name", style="cyan")
    table.add_column("Brand Slug", style="green")

    for name, slug in sorted(CANONICAL_BRAND_SLUGS.items()):
        table.add_row(name, slug)

    console.print(table)


@cli.command("list-serials")
@click.option("--brand", required=True, help="Brand name to inspect (e.g. 比亚迪, 特斯拉).")
def list_serials(brand: str):
    """Dynamically discover all vehicle series under a brand."""
    async def _run():
        adapter = YicheSiteAdapter(headless=True)
        try:
            await adapter.initialize()
            brand_meta = BrandMeta(name=brand, slug=CANONICAL_BRAND_SLUGS.get(brand, brand.lower()))
            serials = await adapter.discover_serials_by_brand(brand_meta)

            table = Table(title=f"Discovered Series for [{brand}] ({len(serials)} Total)")
            table.add_column("Serial Name", style="cyan")
            table.add_column("Slug", style="green")
            table.add_column("Config URL", style="dim")

            for s in serials:
                table.add_row(s.serial_name, s.serial_slug, f"https://car.yiche.com/{s.serial_slug}/peizhi/")

            console.print(table)
        finally:
            await adapter.close()

    asyncio.run(_run())


@cli.command("crawl")
@click.option("--brand", required=True, help="Brand name to crawl (e.g. 比亚迪, 特斯拉, 理想).")
@click.option("--delay", default=1.2, type=float, help="Request jitter delay in seconds.")
@click.option("--discontinued/--no-discontinued", default=True, help="Exhaustively capture discontinued/historical year models.")
def crawl(brand: str, delay: float, discontinued: bool):
    """Crawl full vehicle specifications for a brand."""
    async def _run():
        engine = UniversalCrawlerEngine(headless=True)
        try:
            console.print(f"[bold cyan]Starting exhaustive crawl for brand:[/] {brand} (Include Discontinued/Historical: {discontinued})")
            summary = await engine.crawl_brand(
                brand_name=brand, delay_seconds=delay, include_discontinued=discontinued
            )
            console.print(f"\n[bold green]✓ Crawl Completed for {brand}[/]")
            console.print(f"Total Series Succeeded: [green]{summary.total_serials}[/]")
            console.print(f"Total Trims Ingested: [bold green]{summary.total_trims}[/]")
            console.print(f"Failed Series: {summary.failed_serials}")
            console.print(f"Elapsed Time: {summary.elapsed_seconds}s")
        finally:
            await engine.close()

    asyncio.run(_run())


@cli.command("crawl-multi")
@click.option("--brands", required=True, help="Comma-separated brand names (e.g. 比亚迪,特斯拉,理想,蔚来).")
@click.option("--delay", default=1.2, type=float, help="Request jitter delay.")
@click.option("--discontinued/--no-discontinued", default=True, help="Exhaustively capture discontinued/historical year models.")
def crawl_multi(brands: str, delay: float, discontinued: bool):
    """Batch crawl multiple automotive brands."""
    async def _run():
        brand_list = [b.strip() for b in brands.split(",") if b.strip()]
        engine = UniversalCrawlerEngine(headless=True)
        try:
            console.print(f"[bold cyan]Starting batch crawl for brands:[/] {brand_list}")
            results = await engine.crawl_multi_brands(brands=brand_list, delay_seconds=delay)
            console.print("\n[bold green]=== Multi-Brand Crawl Summary ===[/]")
            for b_name, s in results.items():
                console.print(f"• [cyan]{b_name}[/]: {s.total_serials} series, [bold green]{s.total_trims}[/] trims ({s.elapsed_seconds}s)")
        finally:
            await engine.close()

    asyncio.run(_run())


@cli.command("stats")
def stats():
    """Display catalog database statistics."""
    storage = RawDataStorage()
    trims = storage.get_all_trims()

    console.print(f"\n[bold cyan]Indexed Catalog Database:[/] {storage.db_path}")
    console.print(f"Total Trim Models: [bold green]{len(trims)}[/]\n")

    if trims:
        table = Table(title="Crawled Vehicle Catalog (Recent Sample)")
        table.add_column("Car ID", style="cyan")
        table.add_column("Brand", style="magenta")
        table.add_column("Series", style="blue")
        table.add_column("Trim Model Name", style="white")
        table.add_column("Price Guide", style="green")
        table.add_column("Power Type", style="yellow")
        table.add_column("Body Type", style="dim")

        for row in trims[:15]:
            table.add_row(
                str(row["car_id"]),
                str(row["brand"]),
                str(row["serial"]),
                str(row["trim_name"]),
                str(row["price_guide"]),
                str(row["powertrain_type"]),
                str(row["category_bottom"]),
            )

        console.print(table)


@cli.command("queue-stats")
def queue_stats():
    """Display task queue and checkpoint statistics."""
    queue = SQLiteTaskQueue()
    stats_data = queue.get_stats()

    table = Table(title="Crawler Task Queue State")
    table.add_column("Task Status", style="cyan")
    table.add_column("Count", style="green")

    for status, count in stats_data.items():
        table.add_row(str(status), str(count))

    console.print(table)


@cli.command("brand-stats")
def brand_stats():
    """Display breakdown of series and trim count by brand."""
    storage = RawDataStorage()
    b_stats = storage.get_brand_stats()

    table = Table(title="Crawled Brand Summary (All Brands)")
    table.add_column("Brand", style="cyan")
    table.add_column("Series Count", style="magenta")
    table.add_column("Trims Count", style="green")

    total_s = 0
    total_t = 0
    for b, data in b_stats.items():
        table.add_row(b, str(data["series_count"]), str(data["trims_count"]))
        total_s += data["series_count"]
        total_t += data["trims_count"]

    table.add_section()
    table.add_row("Total", str(total_s), str(total_t), style="bold yellow")
    console.print(table)


@cli.command("show-brand")
@click.option("--brand", required=True, help="Brand name to inspect (e.g. 比亚迪, 零跑, 理想).")
def show_brand(brand: str):
    """Inspect all vehicle series and trim models under a brand."""
    storage = RawDataStorage()
    trims = storage.get_all_trims(brand=brand)

    if not trims:
        console.print(f"[yellow]No trims found for brand: {brand}[/]")
        return

    # Group by serial
    series_map = {}
    for t in trims:
        s = t["serial"]
        series_map.setdefault(s, []).append(t)

    table = Table(title=f"All Series & Models for [{brand}] ({len(series_map)} Series, {len(trims)} Trims)")
    table.add_column("Series Name", style="cyan")
    table.add_column("Slug", style="dim")
    table.add_column("Trims Count", style="green")
    table.add_column("Price Range", style="yellow")
    table.add_column("Powertrain Types", style="magenta")

    for sname, t_list in sorted(series_map.items(), key=lambda x: len(x[1]), reverse=True):
        sslug = t_list[0]["serial_slug"]
        prices = [t["price_guide"] for t in t_list if t["price_guide"] and t["price_guide"] != "暂无报价"]
        p_str = f"{min(prices)} ~ {max(prices)}" if prices else "暂无"
        p_types = set(t["powertrain_type"] for t in t_list if t["powertrain_type"])
        p_type_str = "/".join(p_types) if p_types else "-"
        table.add_row(sname, sslug, str(len(t_list)), p_str, p_type_str)

    console.print(table)


@cli.command("show-serial")
@click.option("--brand", default="", help="Brand name (optional).")
@click.option("--serial", required=True, help="Series name (e.g. 汉, 海豚, 零跑C16).")
def show_serial(brand: str, serial: str):
    """Inspect detailed trim models for a specific car series."""
    storage = RawDataStorage()
    all_trims = storage.get_all_trims(brand=brand if brand else None)
    matched = [t for t in all_trims if serial in t["serial"] or serial in t["trim_name"]]

    if not matched:
        console.print(f"[yellow]No trims found matching serial: {serial}[/]")
        return

    table = Table(title=f"Trim Breakdown for [{serial}] ({len(matched)} Trims Found)")
    table.add_column("Car ID", style="dim")
    table.add_column("Brand", style="cyan")
    table.add_column("Series", style="blue")
    table.add_column("Trim Model Name", style="white")
    table.add_column("Price Guide", style="green")
    table.add_column("Power Type", style="yellow")
    table.add_column("Year", style="magenta")

    for t in matched:
        table.add_row(
            str(t["car_id"]),
            str(t["brand"]),
            str(t["serial"]),
            str(t["trim_name"]),
            str(t["price_guide"]),
            str(t["powertrain_type"]),
            str(t["year"]),
        )

    console.print(table)


@cli.command("search")
@click.option("--keyword", required=True, help="Search keyword (e.g. 激光雷达, DM-i, 纯电, 630).")
def search(keyword: str):
    """Search vehicle models across the entire database by keyword."""
    storage = RawDataStorage()
    all_trims = storage.get_all_trims()
    keyword_lower = keyword.lower()
    matched = [
        t for t in all_trims 
        if (t.get("trim_name") and keyword_lower in t["trim_name"].lower())
        or (t.get("serial") and keyword_lower in t["serial"].lower())
        or (t.get("powertrain_type") and keyword_lower in t["powertrain_type"].lower())
        or (t.get("brand") and keyword_lower in t["brand"].lower())
    ]

    table = Table(title=f"Search Results for '{keyword}' ({len(matched)} Matches)")
    table.add_column("Brand", style="cyan")
    table.add_column("Series", style="blue")
    table.add_column("Trim Name", style="white")
    table.add_column("Price Guide", style="green")
    table.add_column("Power Type", style="yellow")

    for t in matched[:30]:
        table.add_row(
            str(t["brand"]),
            str(t["serial"]),
            str(t["trim_name"]),
            str(t["price_guide"]),
            str(t["powertrain_type"]),
        )

    console.print(table)
    if len(matched) > 30:
        console.print(f"[dim]... and {len(matched) - 30} more matches omitted[/]")


@cli.command("rebuild-index")
def rebuild_index():
    """Rebuild entire SQLite catalog from raw JSON data lake files."""
    storage = RawDataStorage()
    console.print("[bold cyan]Rebuilding SQLite index from raw JSON data lake...[/]")
    count = storage.rebuild_index_from_raw()
    console.print(f"[bold green]✓ Index Rebuilt Successfully! Total Trims Indexed:[/] {count}")


if __name__ == "__main__":
    cli()


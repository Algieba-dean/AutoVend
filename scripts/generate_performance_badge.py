#!/usr/bin/env python3
"""
生成性能徽标脚本

根据性能测试结果生成GitHub徽标。
"""

import json
import sys
import argparse
from pathlib import Path


def load_metrics(metrics_file: str) -> dict:
    """加载性能指标"""
    try:
        with open(metrics_file, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Metrics file {metrics_file} not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {metrics_file}")
        sys.exit(1)


def get_badge_color(value: float, thresholds: dict) -> str:
    """根据数值获取徽标颜色"""
    if value >= thresholds.get('excellent', float('inf')):
        return 'brightgreen'
    elif value >= thresholds.get('good', float('inf')):
        return 'green'
    elif value >= thresholds.get('warning', float('inf')):
        return 'yellow'
    elif value >= thresholds.get('poor', float('inf')):
        return 'orange'
    else:
        return 'red'


def format_value(value: float, unit: str = '', precision: int = 2) -> str:
    """格式化数值显示"""
    if unit == 'ms':
        return f"{value*1000:.{precision}f}ms"
    elif unit == 's':
        return f"{value:.{precision}f}s"
    elif unit == '%':
        return f"{value:.{precision}f}%"
    elif unit == 'qps':
        return f"{value:.{precision}f}"
    else:
        return f"{value:.{precision}f}{unit}"


def generate_badge_url(label: str, message: str, color: str) -> str:
    """生成徽标URL"""
    import urllib.parse
    
    encoded_label = urllib.parse.quote(label)
    encoded_message = urllib.parse.quote(message)
    
    return f"https://img.shields.io/badge/{encoded_label}-{encoded_message}-{color}"


def generate_performance_badges(metrics: dict) -> dict:
    """生成性能徽标"""
    badges = {}
    
    # 响应时间徽标
    if 'avg_retrieval_time' in metrics:
        response_time = metrics['avg_retrieval_time']
        color = get_badge_color(response_time, {
            'excellent': 0.02,
            'good': 0.05,
            'warning': 0.1,
            'poor': 0.2
        })
        message = format_value(response_time, 's', 3)
        badges['response-time'] = generate_badge_url('Response Time', message, color)
    
    # QPS徽标
    if 'qps' in metrics:
        qps = metrics['qps']
        color = get_badge_color(qps, {
            'excellent': 50,
            'good': 30,
            'warning': 20,
            'poor': 10
        })
        message = format_value(qps, '', 1)
        badges['qps'] = generate_badge_url('QPS', f"{message} req/s", color)
    
    # 准确率徽标
    if 'category_accuracy' in metrics:
        accuracy = metrics['category_accuracy']
        color = get_badge_color(accuracy, {
            'excellent': 90,
            'good': 80,
            'warning': 70,
            'poor': 60
        })
        message = format_value(accuracy, '%', 1)
        badges['accuracy'] = generate_badge_url('Accuracy', message, color)
    
    # 内存使用徽标
    if 'peak_memory_mb' in metrics:
        memory = metrics['peak_memory_mb']
        color = get_badge_color(memory, {
            'excellent': 1500,
            'good': 2000,
            'warning': 2500,
            'poor': 3000
        })
        message = format_value(memory, 'MB', 0)
        badges['memory'] = generate_badge_url('Memory', message, color)
    
    return badges


def generate_badge_markdown(badges: dict) -> str:
    """生成徽标Markdown"""
    markdown_lines = []
    
    # 主要性能指标
    main_badges = ['response-time', 'qps', 'accuracy', 'memory']
    
    for badge_name in main_badges:
        if badge_name in badges:
            badge_url = badges[badge_name]
            badge_label = badge_name.replace('-', ' ').title()
            markdown_lines.append(f"[![{badge_label}]({badge_url})]({badge_url})")
    
    return ' '.join(markdown_lines)


def save_badges_json(badges: dict, output_file: str):
    """保存徽标JSON"""
    badges_data = {
        'timestamp': str(Path(__file__).stat().st_mtime),
        'badges': badges
    }
    
    with open(output_file, 'w') as f:
        json.dump(badges_data, f, indent=2)


def update_readme(readme_file: str, badges_markdown: str):
    """更新README文件中的徽标"""
    try:
        with open(readme_file, 'r') as f:
            content = f.read()
        
        # 查找性能徽标部分
        start_marker = '<!-- PERFORMANCE_BADGES -->'
        end_marker = '<!-- /PERFORMANCE_BADGES -->'
        
        start_idx = content.find(start_marker)
        end_idx = content.find(end_marker)
        
        if start_idx != -1 and end_idx != -1:
            # 替换现有徽标
            new_content = (
                content[:start_idx + len(start_marker)] + '\n' +
                badges_markdown + '\n' +
                content[end_idx:]
            )
            
            with open(readme_file, 'w') as f:
                f.write(new_content)
            
            print(f"Updated {readme_file} with performance badges")
        else:
            print(f"Performance badge markers not found in {readme_file}")
            
    except FileNotFoundError:
        print(f"README file {readme_file} not found")


def main():
    parser = argparse.ArgumentParser(description='Generate performance badges')
    parser.add_argument('--metrics', default='metrics.json', help='Metrics JSON file')
    parser.add_argument('--output', default='performance_badges.json', help='Output badges JSON file')
    parser.add_argument('--readme', default='README.md', help='README file to update')
    parser.add_argument('--markdown-only', action='store_true', help='Only output markdown')
    
    args = parser.parse_args()
    
    # 加载性能指标
    metrics = load_metrics(args.metrics)
    
    # 生成徽标
    badges = generate_performance_badges(metrics)
    
    # 保存徽标JSON
    save_badges_json(badges, args.output)
    
    # 生成Markdown
    badges_markdown = generate_badge_markdown(badges)
    
    if args.markdown_only:
        print(badges_markdown)
    else:
        # 更新README
        update_readme(args.readme, badges_markdown)
        print(f"Performance badges generated and saved to {args.output}")
        print(f"Markdown: {badges_markdown}")


if __name__ == '__main__':
    main()

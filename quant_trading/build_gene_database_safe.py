#!/usr/bin/env python3
"""
安全的妖股基因库构建脚本
增强功能：
1. 超时控制
2. 重试机制
3. 断点续传
4. 进度保存
5. 详细日志
"""

import sys
import os
import time
import logging
from demon_stock_gene import DemonStockGene

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/build_gene_db.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def main():
    print("=" * 70)
    print("🧬 妖股基因库安全构建工具")
    print("=" * 70)
    print()
    
    # 检查当前时间
    current_hour = time.localtime().tm_hour
    if 9 <= current_hour <= 15:
        print("⚠️  警告：当前是交易时间（9:00-15:00）")
        print("建议：收盘后（15:30+）或周末运行，成功率更高")
        response = input("\n是否继续？(y/n): ")
        if response.lower() != 'y':
            print("已取消")
            return
    
    # 询问构建规模
    print("\n请选择构建规模：")
    print("1. 测试版（100只股票，10-20分钟）- 推荐首次使用")
    print("2. 完整版（5000只股票，30-60分钟）- 正式使用")
    print("3. 自定义数量")
    
    choice = input("\n请选择 (1/2/3): ").strip()
    
    if choice == '1':
        max_stocks = 100
    elif choice == '2':
        max_stocks = 5000
    elif choice == '3':
        try:
            max_stocks = int(input("请输入股票数量: "))
        except ValueError:
            print("❌ 无效输入")
            return
    else:
        print("❌ 无效选择")
        return
    
    print()
    print("=" * 70)
    print(f"?? 开始构建基因库（目标：{max_stocks}只）")
    print("=" * 70)
    print()
    print("💡 提示:")
    print("  - 支持中断恢复（Ctrl+C 后可重新运行继续）")
    print("  - 每50只自动保存，数据不会丢失")
    print("  - 网络失败会自动重试（最多3次）")
    print()
    
    try:
        # 初始化追踪器
        tracker = DemonStockGene()
        
        # 显示当前进度
        existing_count = len(tracker.gene_db)
        if existing_count > 0:
            print(f"✅ 检测到已有基因数据：{existing_count}只")
            print(f"将跳过已处理的股票，继续构建剩余部分")
            print()
        
        # 开始构建
        start_time = time.time()
        tracker.build_gene_database(max_stocks=max_stocks, batch_save_interval=50)
        elapsed = time.time() - start_time
        
        # 完成提示
        print()
        print("=" * 70)
        print("✅ 构建完成！")
        print("=" * 70)
        
        # 统计信息
        stats = tracker.get_statistics()
        print(f"\n📊 基因库统计:")
        print(f"  总股票数: {stats['total_stocks']}")
        print(f"  高分妖股 (≥60分): {stats['high_gene_count']}")
        print(f"  超级妖股 (≥80分): {stats['super_demon_count']}")
        print(f"  平均基因评分: {stats['avg_gene_score']}")
        print(f"  耗时: {elapsed/60:.1f} 分钟")
        
        if stats['max_gene_stock']:
            max_stock = stats['max_gene_stock']
            print(f"  最强妖股: {max_stock['name']} ({max_stock['symbol']}) - {max_stock['gene_score']}分")
        
        # 显示Top5
        print(f"\n🔥 Top 5 妖股:")
        high_gene = tracker.get_high_gene_stocks(min_score=0)
        for i, stock in enumerate(high_gene[:5], 1):
            print(f"  {i}. {stock['name']:8s} ({stock['symbol']}) 基因:{stock['gene_score']:3.0f}分")
        
        print()
        print("=" * 70)
        print("下一步操作:")
        print("  1. 配置自动更新: cd quant_trading && ./setup_cron.sh")
        print("  2. 启动交易机器人: python3 auto_trader.py")
        print("  3. 查看妖股排行: ./quick_start_demon_gene.sh")
        print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        print("💡 已处理的数据已保存，可随时重新运行继续构建")
    except Exception as e:
        print(f"\n❌ 构建失败: {e}")
        print("💡 已处理的数据已保存，可稍后重新运行")
        logging.error(f"构建失败: {e}", exc_info=True)

if __name__ == "__main__":
    main()
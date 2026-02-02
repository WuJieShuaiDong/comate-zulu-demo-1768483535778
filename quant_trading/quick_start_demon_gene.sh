#!/bin/bash
# 妖股基因系统快速启动脚本
# 用途：帮助用户快速构建基因库并启动增强版交易系统

echo "================================================"
echo "🧬 妖股基因系统 - 快速启动向导"
echo "================================================"
echo ""

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 python3，请先安装 Python 3.7+"
    exit 1
fi

echo "✅ Python 环境检测通过"
echo ""

# 菜单选项
echo "请选择操作："
echo "1. 首次构建基因库 (测试版，扫描100只股票，耗时10-20分钟)"
echo "2. 完整构建基因库 (全市场5000只，耗时30-60分钟)"
echo "3. 每日增量更新 (仅更新涨停股+高分妖股，耗时3-5分钟)"
echo "4. 查询妖股基因排行榜 (Top 20)"
echo "5. 启动增强版交易机器人"
echo "6. 退出"
echo ""

read -p "请输入选项 (1-6): " choice

case $choice in
    1)
        echo ""
        echo "🚀 开始构建测试版基因库 (100只股票)..."
        echo "预计耗时: 10-20分钟"
        echo ""
        python3 << EOF
from demon_stock_gene import DemonStockGene
tracker = DemonStockGene()
tracker.build_gene_database(max_stocks=100)
print("\n✅ 测试版基因库构建完成！")
print("💡 建议：收盘后运行完整构建 (选项2) 以获得最佳效果")
EOF
        ;;
    
    2)
        echo ""
        echo "🚀 开始构建完整基因库 (全市场5000只)..."
        echo "预计耗时: 30-60分钟"
        echo "⚠️  请保持网络连接稳定，建议收盘后运行"
        echo ""
        read -p "确认继续？(y/n): " confirm
        if [ "$confirm" = "y" ]; then
            python3 << EOF
from demon_stock_gene import DemonStockGene
tracker = DemonStockGene()
tracker.build_gene_database(max_stocks=5000)
print("\n✅ 完整基因库构建完成！")
print("📊 基因库位置: data/demon_gene_db.json")
EOF
        else
            echo "已取消"
        fi
        ;;
    
    3)
        echo ""
        echo "🔄 开始每日增量更新..."
        echo "预计耗时: 3-5分钟"
        echo ""
        python3 << EOF
from demon_stock_gene import DemonStockGene
tracker = DemonStockGene()
tracker.update_gene_database()
print("\n✅ 增量更新完成！")
EOF
        ;;
    
    4)
        echo ""
        echo "🏆 妖股基因排行榜 (Top 20)"
        echo "================================================"
        python3 << EOF
from demon_stock_gene import DemonStockGene
tracker = DemonStockGene()
stocks = tracker.get_high_gene_stocks(min_score=60)

if not stocks:
    print("⚠️  基因库为空或无高分妖股，请先构建基因库 (选项1或2)")
else:
    print(f"\n共 {len(stocks)} 只妖股 (基因评分≥60分)\n")
    for i, stock in enumerate(stocks[:20], 1):
        tag = ""
        if stock['gene_score'] >= 80:
            tag = " 🔥 [超级妖股]"
        elif stock['gene_score'] >= 70:
            tag = " ✨ [强妖股]"
        
        print(f"{i:2d}. {stock['name']:8s} ({stock['symbol']}) "
              f"基因:{stock['gene_score']:3.0f}分 "
              f"连板:{stock['max_continuous_board']:2d}板 "
              f"月涨幅:{stock['monthly_max_gain']:5.1f}%{tag}")
EOF
        ;;
    
    5)
        echo ""
        echo "🤖 启动增强版交易机器人..."
        echo "================================================"
        
        # 检查基因库是否存在
        if [ ! -f "data/demon_gene_db.json" ]; then
            echo "⚠️  警告：未检测到妖股基因库"
            echo "💡 建议先运行选项1构建基因库，否则将使用传统模式"
            echo ""
            read -p "继续启动？(y/n): " confirm
            if [ "$confirm" != "y" ]; then
                echo "已取消"
                exit 0
            fi
        fi
        
        echo ""
        echo "选择运行模式："
        echo "1. 前台运行 (实时查看日志，Ctrl+C 停止)"
        echo "2. 后台运行 (nohup 守护进程)"
        echo ""
        read -p "请选择 (1-2): " mode
        
        if [ "$mode" = "1" ]; then
            echo ""
            echo "🚀 启动中..."
            python3 auto_trader.py
        elif [ "$mode" = "2" ]; then
            echo ""
            echo "🚀 后台启动中..."
            nohup python3 auto_trader.py > logs/trader_$(date +%Y%m%d_%H%M%S).log 2>&1 &
            echo "✅ 机器人已在后台运行"
            echo "📊 查看日志: tail -f data/bot.log"
            echo "🛑 停止运行: pkill -f auto_trader.py"
        else
            echo "无效选项"
        fi
        ;;
    
    6)
        echo "再见！"
        exit 0
        ;;
    
    *)
        echo "❌ 无效选项，请输入 1-6"
        ;;
esac

echo ""
echo "================================================"
echo "操作完成！"
echo "================================================"
#!/bin/bash
# 系统状态检查脚本

echo "================================================"
echo "🔍 妖股基因系统状态检查"
echo "================================================"
echo ""

echo "1️⃣ 基因库文件:"
if [ -f "data/demon_gene_db.json" ]; then
    size=$(ls -lh data/demon_gene_db.json | awk '{print $5}')
    echo "   ✅ 已存在 (大小: $size)"
else
    echo "   ❌ 未构建 - 请先运行构建命令"
fi

echo ""
echo "2️⃣ 定时任务:"
if crontab -l 2>/dev/null | grep -q daily_maintenance; then
    echo "   ✅ 已配置"
    crontab -l | grep daily_maintenance
else
    echo "   ❌ 未配置 - 运行: ./setup_cron.sh"
fi

echo ""
echo "3️⃣ 脚本权限:"
for script in daily_maintenance.sh setup_cron.sh quick_start_demon_gene.sh; do
    if [ -x "$script" ]; then
        echo "   ✅ $script"
    else
        echo "   ❌ $script (运行: chmod +x $script)"
    fi
done

echo ""
echo "4️⃣ 日志目录:"
if [ -d "logs" ]; then
    count=$(ls -1 logs/*.log 2>/dev/null | wc -l | tr -d ' ')
    echo "   ✅ 已创建 ($count 个日志文件)"
else
    echo "   ⚠️  不存在 (首次运行时自动创建)"
fi

echo ""
echo "5️⃣ Python 模块:"
python3 << 'PYEOF'
try:
    from demon_stock_gene import DemonStockGene
    tracker = DemonStockGene()
    count = len(tracker.gene_db)
    if count > 0:
        super_count = sum(1 for s in tracker.gene_db.values() if s.get('gene_score', 0) >= 80)
        print(f"   ✅ 基因库: {count} 只 (超级妖股: {super_count} 只)")
    else:
        print("   ⚠️  基因库为空 - 请先构建")
except Exception as e:
    print(f"   ❌ 导入失败: {e}")
PYEOF

echo ""
echo "================================================"
echo "💡 快速操作指南:"
echo "================================================"
echo ""
echo "首次构建基因库（收盘后15:30+）:"
echo "  python3 -c \"from demon_stock_gene import DemonStockGene; DemonStockGene().build_gene_database(max_stocks=100)\""
echo ""
echo "配置自动维护:"
echo "  ./setup_cron.sh"
echo ""
echo "手动触发维护:"
echo "  ./daily_maintenance.sh"
echo ""
echo "查看妖股排行:"
echo "  ./quick_start_demon_gene.sh  # 选4"
echo ""

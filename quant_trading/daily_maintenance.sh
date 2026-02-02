#!/bin/bash
# 妖股基因系统每日自动维护脚本
# 功能：增量更新基因库 + 日志记录
# 建议执行时间：每个交易日收盘后 15:30-16:00

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/daily_maintenance_$(date +%Y%m%d).log"

# 确保日志目录存在
mkdir -p "$LOG_DIR"

# 开始维护
echo "================================================" | tee -a "$LOG_FILE"
echo "🔄 妖股基因库每日维护开始" | tee -a "$LOG_FILE"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# 切换到脚本目录
cd "$SCRIPT_DIR" || exit 1

# 检查基因库是否存在
if [ ! -f "data/demon_gene_db.json" ]; then
    echo "⚠️  警告：基因库不存在，执行首次构建（测试版100只）" | tee -a "$LOG_FILE"
    python3 -c "
from demon_stock_gene import DemonStockGene
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
tracker = DemonStockGene()
tracker.build_gene_database(max_stocks=100)
" 2>&1 | tee -a "$LOG_FILE"
else
    echo "✅ 基因库已存在，执行增量更新" | tee -a "$LOG_FILE"
    python3 -c "
from demon_stock_gene import DemonStockGene
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
tracker = DemonStockGene()
tracker.update_gene_database()
" 2>&1 | tee -a "$LOG_FILE"
fi

# 检查执行结果
if [ $? -eq 0 ]; then
    echo "" | tee -a "$LOG_FILE"
    echo "✅ 维护完成" | tee -a "$LOG_FILE"
    
    # 统计基因库信息
    python3 -c "
from demon_stock_gene import DemonStockGene
tracker = DemonStockGene()
total = len(tracker.gene_db)
super_demons = sum(1 for s in tracker.gene_db.values() if s.get('gene_score', 0) >= 80)
strong_demons = sum(1 for s in tracker.gene_db.values() if 60 <= s.get('gene_score', 0) < 80)
print(f'📊 基因库统计:')
print(f'   总数: {total}只')
print(f'   超级妖股(≥80分): {super_demons}只')
print(f'   强妖股(60-79分): {strong_demons}只')
" 2>&1 | tee -a "$LOG_FILE"
else
    echo "" | tee -a "$LOG_FILE"
    echo "❌ 维护失败，请检查日志" | tee -a "$LOG_FILE"
fi

echo "" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"
echo "维护结束时间: $(date '+%Y-%m-%d %H:%M:%S')" | tee -a "$LOG_FILE"
echo "================================================" | tee -a "$LOG_FILE"

# 清理7天前的日志
find "$LOG_DIR" -name "daily_maintenance_*.log" -mtime +7 -delete 2>/dev/null
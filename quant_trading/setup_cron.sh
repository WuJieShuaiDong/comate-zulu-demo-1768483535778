#!/bin/bash
# 自动配置 cron 定时任务脚本
# 功能：设置每个交易日 15:35 自动更新妖股基因库

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MAINTENANCE_SCRIPT="$SCRIPT_DIR/daily_maintenance.sh"

echo "================================================"
echo "🕐 配置妖股基因库自动维护定时任务"
echo "================================================"
echo ""

# 检查维护脚本是否存在
if [ ! -f "$MAINTENANCE_SCRIPT" ]; then
    echo "❌ 错误：找不到 daily_maintenance.sh"
    exit 1
fi

# 添加执行权限
chmod +x "$MAINTENANCE_SCRIPT"
echo "✅ 维护脚本权限已设置"

# 生成 cron 任务条目
CRON_JOB="35 15 * * 1-5 $MAINTENANCE_SCRIPT"

echo ""
echo "📋 将添加以下定时任务："
echo "   时间: 每个交易日 15:35 (周一到周五)"
echo "   命令: $MAINTENANCE_SCRIPT"
echo ""

# 检查是否已存在相同任务
if crontab -l 2>/dev/null | grep -q "$MAINTENANCE_SCRIPT"; then
    echo "⚠️  检测到已存在相同任务"
    read -p "是否替换？(y/n): " replace
    if [ "$replace" != "y" ]; then
        echo "已取消"
        exit 0
    fi
    # 删除旧任务
    crontab -l 2>/dev/null | grep -v "$MAINTENANCE_SCRIPT" | crontab -
    echo "✅ 已删除旧任务"
fi

# 添加新任务
(crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ 定时任务添加成功！"
    echo ""
    echo "📊 当前所有定时任务："
    echo "================================================"
    crontab -l
    echo "================================================"
    echo ""
    echo "💡 提示："
    echo "   1. 每个交易日 15:35 自动运行"
    echo "   2. 日志保存在: $SCRIPT_DIR/logs/"
    echo "   3. 查看最新日志: tail -f $SCRIPT_DIR/logs/daily_maintenance_\$(date +%Y%m%d).log"
    echo "   4. 删除定时任务: crontab -e (手动删除对应行)"
else
    echo "❌ 定时任务添加失败"
    exit 1
fi

echo ""
echo "🎉 配置完成！"
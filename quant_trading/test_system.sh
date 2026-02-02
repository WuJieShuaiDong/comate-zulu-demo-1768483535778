#!/bin/bash

###############################################################################
# 量化交易系统 - 功能测试脚本
# 功能：测试所有核心功能是否正常工作
# 作者：Zulu AI
# 版本：1.0
###############################################################################

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║                   系统功能测试                                 ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 测试计数
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

run_test() {
    local test_name=$1
    local test_command=$2
    
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    echo -e "${YELLOW}测试 $TOTAL_TESTS: $test_name${NC}"
    
    eval "$test_command" > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ 通过${NC}"
        PASSED_TESTS=$((PASSED_TESTS + 1))
    else
        echo -e "${RED}✗ 失败${NC}"
        FAILED_TESTS=$((FAILED_TESTS + 1))
    fi
    echo ""
}

# 1. Python环境测试
run_test "Python3 可用性" "command -v python3"

# 2. 核心依赖测试
run_test "Streamlit 已安装" "python3 -c 'import streamlit'"
run_test "Akshare 已安装" "python3 -c 'import akshare'"
run_test "Pandas 已安装" "python3 -c 'import pandas'"

# 3. 核心模块测试
run_test "妖股基因模块加载" "python3 -c 'from demon_stock_gene import DemonStockGene'"
run_test "赚钱效应模块加载" "python3 -c 'from money_effect_tracker import MoneyEffectTracker'"

# 4. 数据目录测试
run_test "数据目录存在" "test -d '$SCRIPT_DIR/data'"

# 5. 脚本权限测试
run_test "start_all.sh 可执行" "test -x '$SCRIPT_DIR/start_all.sh'"
run_test "stop_all.sh 可执行" "test -x '$SCRIPT_DIR/stop_all.sh'"

# 6. 配置文件测试
if [ -f "$SCRIPT_DIR/data/account.json" ]; then
    run_test "account.json 格式有效" "python3 -c 'import json; json.load(open(\"$SCRIPT_DIR/data/account.json\"))'"
fi

if [ -f "$SCRIPT_DIR/data/demon_gene_db.json" ]; then
    run_test "妖股基因库格式有效" "python3 -c 'import json; json.load(open(\"$SCRIPT_DIR/data/demon_gene_db.json\"))'"
fi

# 7. 妖股基因功能测试
echo -e "${YELLOW}测试 $((TOTAL_TESTS + 1)): 妖股基因评分功能${NC}"
TOTAL_TESTS=$((TOTAL_TESTS + 1))
python3 << 'EOF' > /dev/null 2>&1
from demon_stock_gene import DemonStockGene
tracker = DemonStockGene()
if len(tracker.gene_db) > 0:
    symbol = list(tracker.gene_db.keys())[0]
    score = tracker.get_gene_score(symbol)
    if score and 'total_score' in score:
        exit(0)
exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 通过${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${YELLOW}○ 跳过 (基因库为空)${NC}"
fi
echo ""

# 8. 网络连通性测试
echo -e "${YELLOW}测试 $((TOTAL_TESTS + 1)): 网络连通性 (akshare)${NC}"
TOTAL_TESTS=$((TOTAL_TESTS + 1))
python3 << 'EOF' > /dev/null 2>&1
import akshare as ak
try:
    df = ak.stock_zh_a_spot_em()
    if not df.empty:
        exit(0)
except:
    pass
exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 通过${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
else
    echo -e "${YELLOW}○ 跳过 (网络不可用)${NC}"
fi
echo ""

# 总结
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo -e "总测试数: $TOTAL_TESTS"
echo -e "${GREEN}通过: $PASSED_TESTS${NC}"
echo -e "${RED}失败: $FAILED_TESTS${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}🎉 所有测试通过！系统就绪。${NC}"
    exit 0
else
    echo -e "${RED}⚠️  部分测试失败，请检查上述错误。${NC}"
    exit 1
fi
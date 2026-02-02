#!/bin/bash
echo "🛑 正在执行紧急重置..."

# 1. 停止所有服务
pkill -9 -f "auto_trader.py"
pkill -9 -f "streamlit"
sleep 2

# 2. 强制重写账户文件 (保留 trades.csv)
# cat > data/trades.csv << 'EOF' ... (已手动重建，这里不覆盖)

cat > data/account.json << 'EOF'
{
  "cash": 45661.0,
  "positions": {
    "603633": {
      "cost": 9.21,
      "shares": 2100,
      "name": "徕木股份"
    },
    "300438": {
      "cost": 46.1,
      "shares": 400,
      "name": "鹏辉能源"
    },
    "301391": {
      "cost": 75.17,
      "shares": 200,
      "name": "卡莱特"
    }
  },
  "total_value": 101098.0,
  "initial_capital": 100000.0,
  "last_day_value": 101098.0,
  "yesterday_pnl": 0.0,
  "nav_history": [],
  "last_update_date": "2026-01-28",
  "update_time": "2026-01-28 11:30:00",
  "mode": "SIMULATION"
}
EOF

# 3. 重启服务
nohup python3 auto_trader.py > logs/trader.log 2>&1 &
echo $! > .bot.pid
nohup python3 -m streamlit run app.py --server.port 8503 --server.address 0.0.0.0 > logs/app.log 2>&1 &
echo $! > .app.pid

echo "✅ 重置完成！请访问 http://127.0.0.1:8503"
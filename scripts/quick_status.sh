#!/bin/bash
# PersonalNotebook — 服务状态检查脚本

CYAN='\033[0;36m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${CYAN}🔍 PersonalNotebook 服务状态${NC}"
echo "════════════════════════════════════════"

check_port() {
    local name=$1 port=$2
    if lsof -i :$port -sTCP:LISTEN &>/dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} $name (:$port) — ${GREEN}running${NC}"
    else
        echo -e "  ${RED}❌${NC} $name (:$port) — ${RED}stopped${NC}"
    fi
}

check_port "Frontend"      3000
check_port "Backend API"   8000
check_port "Model Gateway" 8900
check_port "MinIO API"     9000
check_port "MinIO Console" 9001
check_port "Qdrant"        6333
check_port "PostgreSQL"    5432
check_port "Redis"         6379

echo ""
echo "  日志目录: $HOME/PersonalNotebook-Data/logs"
echo ""

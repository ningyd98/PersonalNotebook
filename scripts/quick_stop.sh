#!/bin/bash
# PersonalNotebook — 快速停止脚本
set -euo pipefail

CYAN='\033[0;36m'
GREEN='\033[0;32m'
NC='\033[0m'

echo ""
echo -e "${CYAN}🛑 停止 PersonalNotebook...${NC}"
echo ""

# Frontend
pkill -f "next start" 2>/dev/null && echo -e "  ${GREEN}⏹${NC} Frontend" || true

# Celery
pkill -f "celery_app" 2>/dev/null && echo -e "  ${GREEN}⏹${NC} Celery Worker" || true

# Backend
pkill -f "app.main:app" 2>/dev/null && echo -e "  ${GREEN}⏹${NC} Backend API" || true

# Model Gateway
pkill -f "model-gateway/main.py" 2>/dev/null && echo -e "  ${GREEN}⏹${NC} Model Gateway" || true

# Qdrant
pkill -x qdrant 2>/dev/null && echo -e "  ${GREEN}⏹${NC} Qdrant" || true

# MinIO
pkill -x minio 2>/dev/null && echo -e "  ${GREEN}⏹${NC} MinIO" || true

# Redis (Homebrew)
if brew services list | grep -q "redis.*started" 2>/dev/null; then
    brew services stop redis 2>/dev/null && echo -e "  ${GREEN}⏹${NC} Redis" || true
fi

# PostgreSQL (Homebrew)
if brew services list | grep -q "postgresql.*started" 2>/dev/null; then
    brew services stop postgresql@16 2>/dev/null && echo -e "  ${GREEN}⏹${NC} PostgreSQL" || true
fi

# Docker (如果使用了 Docker 模式)
if command -v docker &>/dev/null && docker compose -f infra/docker-compose.yml ps 2>/dev/null | grep -q "running"; then
    docker compose -f infra/docker-compose.yml down 2>/dev/null && echo -e "  ${GREEN}⏹${NC} Docker 服务" || true
fi

echo ""
echo -e "${GREEN}✅ PersonalNotebook 已停止${NC}"

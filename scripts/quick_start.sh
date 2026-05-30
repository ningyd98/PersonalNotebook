#!/bin/bash
# ============================================================
# PersonalNotebook — 快速启动脚本
# 在项目根目录运行: bash scripts/quick_start.sh
# ============================================================
set -euo pipefail

VERSION="0.3.0"
APP_NAME="PersonalNotebook"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="$HOME/.personalnotebook"
DATA_DIR="$HOME/PersonalNotebook-Data"
LOG_DIR="$DATA_DIR/logs"
VENV_DIR="$INSTALL_DIR/venv"

# Banner
echo ""
echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║${NC}  📓 PersonalNotebook v${VERSION}                  ${CYAN}║${NC}"
echo -e "${CYAN}║${NC}  个人知识库 RAG 系统 — 快速启动              ${CYAN}║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
echo ""

# ============================================================
# 检查依赖
# ============================================================
check_deps() {
    echo -e "${BLUE}[1/4]${NC} 检查依赖..."

    local MISSING=()

    # Python3
    if ! command -v python3 &>/dev/null; then
        MISSING+=("python3")
    fi

    # Node.js
    if ! command -v node &>/dev/null; then
        MISSING+=("node")
    fi

    # Docker or Homebrew services
    USE_DOCKER=false
    if command -v docker &>/dev/null && docker info &>/dev/null 2>&1; then
        USE_DOCKER=true
        echo -e "  ${GREEN}✓${NC} Docker 可用，将使用 Docker 运行基础设施"
    else
        # 检查 Homebrew
        if ! command -v brew &>/dev/null; then
            MISSING+=("homebrew")
        fi
    fi

    if [[ ${#MISSING[@]} -gt 0 ]]; then
        echo -e "  ${RED}✗${NC} 缺少依赖: ${MISSING[*]}"
        echo ""
        read -p "是否自动安装缺少的依赖？[Y/n] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Nn]$ ]]; then
            install_deps "${MISSING[@]}"
        else
            echo -e "${RED}请先安装缺少的依赖后再运行${NC}"
            exit 1
        fi
    else
        echo -e "  ${GREEN}✓${NC} 核心依赖已满足"
    fi
}

install_deps() {
    local deps=("$@")

    for dep in "${deps[@]}"; do
        case $dep in
            python3)
                echo "  安装 Python3..."
                brew install python@3.13
                ;;
            node)
                echo "  安装 Node.js..."
                brew install node@22
                ;;
            homebrew)
                echo "  安装 Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
                if [[ "$(uname -m)" == "arm64" ]]; then
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                fi
                ;;
        esac
    done
}

# ============================================================
# 设置环境
# ============================================================
setup_env() {
    echo -e "${BLUE}[2/4]${NC} 设置环境..."

    mkdir -p "$INSTALL_DIR" "$DATA_DIR"/{uploads,storage,qdrant,minio,logs}

    # Python venv
    if [[ ! -d "$VENV_DIR" ]]; then
        echo "  创建 Python 虚拟环境..."
        python3 -m venv "$VENV_DIR"
    fi
    source "$VENV_DIR/bin/activate"

    # 安装 Python 依赖（检查是否已安装）
    if ! python3 -c "import fastapi" 2>/dev/null; then
        echo "  安装 Python 依赖（首次安装需要几分钟）..."
        pip install --upgrade pip -q
        pip install fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" asyncpg psycopg2-binary \
            alembic pydantic pydantic-settings "celery[redis]" redis minio qdrant-client \
            PyMuPDF python-docx python-pptx openpyxl pandas markdown-it-py python-frontmatter \
            Pillow httpx aiofiles "python-jose[cryptography]" "passlib[bcrypt]" python-dotenv \
            loguru tiktoken rich faster-whisper mutagen py7zr -q 2>/dev/null
    fi
    echo -e "  ${GREEN}✓${NC} Python 环境就绪"

    # 前端依赖
    if [[ ! -d "$PROJECT_DIR/frontend/node_modules" ]]; then
        echo "  安装前端依赖..."
        cd "$PROJECT_DIR/frontend"
        npm install --legacy-peer-deps
    fi

    # 前端构建
    if [[ ! -d "$PROJECT_DIR/frontend/.next" ]]; then
        echo "  构建前端..."
        cd "$PROJECT_DIR/frontend"
        npm run build
    fi
    echo -e "  ${GREEN}✓${NC} 前端就绪"

    # 配置文件
    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        # 生成安全密钥
        SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me")
        JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me")
        sed -i '' "s|SECRET_KEY=.*|SECRET_KEY=$SECRET|g" "$PROJECT_DIR/.env" 2>/dev/null || true
        sed -i '' "s|JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$JWT_SECRET|g" "$PROJECT_DIR/.env" 2>/dev/null || true
    fi
    echo -e "  ${GREEN}✓${NC} 配置就绪"
}

# ============================================================
# 启动基础设施
# ============================================================
start_infra() {
    echo -e "${BLUE}[3/4]${NC} 启动基础设施..."

    if [[ "$USE_DOCKER" == true ]]; then
        start_infra_docker
    else
        start_infra_native
    fi
}

start_infra_docker() {
    echo -e "  使用 ${CYAN}Docker${NC} 模式..."

    cd "$PROJECT_DIR/infra"

    # 启动 docker-compose
    if ! docker compose ps | grep -q "kb-postgres.*running" 2>/dev/null; then
        docker compose up -d postgres redis qdrant minio minio-create-bucket
        echo -e "  等待服务启动..."
        sleep 10
    fi

    echo -e "  ${GREEN}✓${NC} PostgreSQL (Docker)"
    echo -e "  ${GREEN}✓${NC} Redis (Docker)"
    echo -e "  ${GREEN}✓${NC} Qdrant (Docker)"
    echo -e "  ${GREEN}✓${NC} MinIO (Docker)"

    # 数据库迁移
    cd "$PROJECT_DIR/backend"
    DATABASE_URL="postgresql+asyncpg://kb_user:kb_password@localhost:5432/personal_kb" \
        alembic upgrade head 2>/dev/null || echo -e "  ${YELLOW}⚠${NC} 数据库迁移可能需要手动运行"
}

start_infra_native() {
    echo -e "  使用 ${CYAN}Homebrew 原生${NC} 模式..."

    # PostgreSQL
    if ! brew services list | grep -q "postgresql@16.*started"; then
        brew services start postgresql@16 2>/dev/null || {
            # 尝试其他版本
            brew services start postgresql 2>/dev/null || true
        }
        sleep 3
    fi

    # 创建数据库和用户
    if ! psql -U "$USER" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='kb_user'" 2>/dev/null | grep -q 1; then
        createuser kb_user 2>/dev/null || true
        psql -U "$USER" -d postgres -c "ALTER USER kb_user WITH PASSWORD 'kb_password';" 2>/dev/null || true
    fi
    if ! psql -U "$USER" -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "personal_kb"; then
        createdb -O kb_user personal_kb 2>/dev/null || true
    fi
    echo -e "  ${GREEN}✓${NC} PostgreSQL"

    # Redis
    if ! brew services list | grep -q "redis.*started"; then
        brew services start redis 2>/dev/null || true
        sleep 1
    fi
    echo -e "  ${GREEN}✓${NC} Redis"

    # MinIO
    if ! command -v minio &>/dev/null; then
        brew install minio
    fi
    if ! pgrep -x minio &>/dev/null; then
        nohup minio server "$DATA_DIR/minio" --console-address ":9001" > "$LOG_DIR/minio.log" 2>&1 &
        sleep 2
    fi
    echo -e "  ${GREEN}✓${NC} MinIO"

    # Qdrant
    local QDRANT_DIR="$INSTALL_DIR/qdrant"
    if [[ ! -x "$QDRANT_DIR/qdrant" ]]; then
        echo "  下载 Qdrant..."
        mkdir -p "$QDRANT_DIR"
        local ARCH="aarch64"
        [[ "$(uname -m)" == "x86_64" ]] && ARCH="x86_64"
        curl -fSL "https://github.com/qdrant/qdrant/releases/latest/download/qdrant-${ARCH}-apple-darwin.tar.gz" \
            -o /tmp/qdrant.tar.gz 2>/dev/null || \
        curl -fSL "https://github.com/qdrant/qdrant/releases/download/v1.13.4/qdrant-${ARCH}-apple-darwin.tar.gz" \
            -o /tmp/qdrant.tar.gz
        tar -xzf /tmp/qdrant.tar.gz -C "$QDRANT_DIR" --strip-components=1
        chmod +x "$QDRANT_DIR/qdrant"
        rm -f /tmp/qdrant.tar.gz
    fi
    if ! pgrep -x qdrant &>/dev/null; then
        nohup "$QDRANT_DIR/qdrant" --storage-path "$DATA_DIR/qdrant" > "$LOG_DIR/qdrant.log" 2>&1 &
        sleep 2
    fi
    echo -e "  ${GREEN}✓${NC} Qdrant"

    # 数据库迁移
    cd "$PROJECT_DIR/backend"
    DATABASE_URL="postgresql+asyncpg://kb_user:kb_password@localhost:5432/personal_kb" \
        alembic upgrade head 2>/dev/null || echo -e "  ${YELLOW}⚠${NC} 数据库迁移可能需要手动运行"
}

# ============================================================
# 启动应用服务
# ============================================================
start_app() {
    echo -e "${BLUE}[4/4]${NC} 启动应用服务..."
    mkdir -p "$LOG_DIR"

    # Model Gateway
    if ! lsof -i :8900 -sTCP:LISTEN &>/dev/null; then
        cd "$PROJECT_DIR/model-gateway"
        nohup python3 main.py > "$LOG_DIR/model-gateway.log" 2>&1 &
        sleep 2
    fi
    echo -e "  ${GREEN}✓${NC} Model Gateway (:8900)"

    # Backend API
    if ! lsof -i :8000 -sTCP:LISTEN &>/dev/null; then
        cd "$PROJECT_DIR/backend"
        nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
        sleep 3
    fi
    echo -e "  ${GREEN}✓${NC} Backend API (:8000)"

    # Celery Worker
    if ! pgrep -f "celery_app" &>/dev/null; then
        cd "$PROJECT_DIR/backend"
        nohup celery -A app.workers.celery_app worker --loglevel=info > "$LOG_DIR/celery.log" 2>&1 &
        sleep 2
    fi
    echo -e "  ${GREEN}✓${NC} Celery Worker"

    # Frontend
    if ! lsof -i :3000 -sTCP:LISTEN &>/dev/null; then
        cd "$PROJECT_DIR/frontend"
        nohup npx next start -p 3000 > "$LOG_DIR/frontend.log" 2>&1 &
        sleep 3
    fi
    echo -e "  ${GREEN}✓${NC} Frontend (:3000)"
}

# ============================================================
# 显示状态
# ============================================================
show_status() {
    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║${NC}  🎉 PersonalNotebook 已启动！                ${GREEN}║${NC}"
    echo -e "${GREEN}╠══════════════════════════════════════════════╣${NC}"
    echo -e "${GREEN}║${NC}                                              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  📱 前端界面:  ${CYAN}http://localhost:3000${NC}         ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  🔧 API 文档:  ${CYAN}http://localhost:8000/docs${NC}     ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  📊 MinIO:     ${CYAN}http://localhost:9001${NC}         ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  📝 日志:      $LOG_DIR   ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                              ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  🛑 停止: ${YELLOW}bash scripts/quick_stop.sh${NC}             ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}  🔍 状态: ${YELLOW}bash scripts/quick_status.sh${NC}            ${GREEN}║${NC}"
    echo -e "${GREEN}║${NC}                                              ${GREEN}║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════════════╝${NC}"
    echo ""

    # 自动打开浏览器
    sleep 2
    open "http://localhost:3000" 2>/dev/null || true
}

# ============================================================
# Main
# ============================================================
check_deps
setup_env
start_infra
start_app
show_status

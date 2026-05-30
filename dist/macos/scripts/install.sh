#!/bin/bash
# ============================================================
# PersonalNotebook macOS 一键安装脚本
# 自动检测并安装所有依赖，配置并启动所有服务
# ============================================================
set -euo pipefail

VERSION="0.3.0"
APP_NAME="PersonalNotebook"
INSTALL_DIR="$HOME/.personalnotebook"
DATA_DIR="$HOME/PersonalNotebook-Data"
LOG_FILE="$INSTALL_DIR/install.log"
PYTHON_VERSION="3.13.12"
NODE_VERSION="22.22.2"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN${NC} $1"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR${NC} $1"; }
info() { echo -e "${BLUE}[$(date '+%H:%M:%S')] INFO${NC} $1"; }

# ============================================================
# Step 0: 检查系统环境
# ============================================================
check_system() {
    log "检查系统环境..."

    if [[ "$(uname)" != "Darwin" ]]; then
        err "此安装脚本仅支持 macOS"
        exit 1
    fi

    ARCH=$(uname -m)
    if [[ "$ARCH" != "arm64" && "$ARCH" != "x86_64" ]]; then
        err "不支持的架构: $ARCH"
        exit 1
    fi

    log "系统检查通过: macOS $(sw_vers -productVersion) ($ARCH)"
}

# ============================================================
# Step 1: 安装 Homebrew（如果未安装）
# ============================================================
install_homebrew() {
    if command -v brew &>/dev/null; then
        log "Homebrew 已安装: $(brew --version | head -1)"
        return 0
    fi

    log "安装 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # 配置 PATH
    if [[ "$ARCH" == "arm64" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        if ! grep -q "/opt/homebrew/bin" "$HOME/.zprofile" 2>/dev/null; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
        fi
    else
        eval "$(/usr/local/bin/brew shellenv)"
    fi

    log "Homebrew 安装完成"
}

# ============================================================
# Step 2: 安装基础设施服务
# ============================================================
install_infra() {
    log "安装基础设施服务..."

    # PostgreSQL
    if ! brew list postgresql@16 &>/dev/null; then
        log "安装 PostgreSQL 16..."
        brew install postgresql@16
        brew link postgresql@16 --force
    fi
    log "PostgreSQL 已就绪"

    # Redis
    if ! brew list redis &>/dev/null; then
        log "安装 Redis..."
        brew install redis
    fi
    log "Redis 已就绪"

    # MinIO
    if ! brew list minio &>/dev/null; then
        log "安装 MinIO..."
        brew install minio
    fi
    log "MinIO 已就绪"

    # FFmpeg
    if ! command -v ffmpeg &>/dev/null; then
        log "安装 FFmpeg..."
        brew install ffmpeg
    fi
    log "FFmpeg 已就绪"

    # Qdrant - 下载预编译二进制
    install_qdrant
}

install_qdrant() {
    local QDRANT_DIR="$INSTALL_DIR/qdrant"
    if [[ -x "$QDRANT_DIR/qdrant" ]]; then
        log "Qdrant 已安装"
        return 0
    fi

    log "下载 Qdrant..."
    mkdir -p "$QDRANT_DIR"

    local ARCH_SUFFIX="aarch64"
    if [[ "$(uname -m)" == "x86_64" ]]; then
        ARCH_SUFFIX="x86_64"
    fi

    # 获取最新版本号
    local LATEST_URL="https://github.com/qdrant/qdrant/releases/latest/download/qdrant-${ARCH_SUFFIX}-apple-darwin.tar.gz"
    local TMP_FILE="/tmp/qdrant.tar.gz"

    curl -fSL -o "$TMP_FILE" "$LATEST_URL" 2>/dev/null || {
        # fallback to known version
        warn "Latest download failed, trying v1.13.4..."
        curl -fSL -o "$TMP_FILE" \
            "https://github.com/qdrant/qdrant/releases/download/v1.13.4/qdrant-${ARCH_SUFFIX}-apple-darwin.tar.gz"
    }

    tar -xzf "$TMP_FILE" -C "$QDRANT_DIR" --strip-components=1
    chmod +x "$QDRANT_DIR/qdrant"
    rm -f "$TMP_FILE"

    log "Qdrant 安装完成: $QDRANT_DIR/qdrant"
}

# ============================================================
# Step 3: 安装 Python 和 Node.js
# ============================================================
install_runtimes() {
    # Python
    if ! command -v python3 &>/dev/null; then
        log "安装 Python..."
        brew install python@3.13
    fi
    log "Python: $(python3 --version 2>/dev/null || echo 'installed')"

    # Node.js
    if ! command -v node &>/dev/null; then
        log "安装 Node.js..."
        brew install node@22
    fi
    log "Node.js: $(node --version 2>/dev/null || echo 'installed')"
}

# ============================================================
# Step 4: 设置 Python 虚拟环境和依赖
# ============================================================
setup_python_env() {
    log "设置 Python 虚拟环境..."

    local VENV_DIR="$INSTALL_DIR/venv"
    if [[ ! -d "$VENV_DIR" ]]; then
        python3 -m venv "$VENV_DIR"
    fi

    source "$VENV_DIR/bin/activate"

    log "安装后端 Python 依赖..."
    local PROJECT_DIR
    PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

    if [[ -f "$PROJECT_DIR/backend/pyproject.toml" ]]; then
        pip install --upgrade pip setuptools wheel
        pip install -e "$PROJECT_DIR/backend[dev]" 2>/dev/null || \
        pip install fastapi uvicorn[standard] sqlalchemy[asyncio] asyncpg psycopg2-binary \
            alembic pydantic pydantic-settings celery[redis] redis minio qdrant-client \
            PyMuPDF python-docx python-pptx openpyxl pandas markdown-it-py python-frontmatter \
            Pillow httpx aiofiles python-jose[cryptography] passlib[bcrypt] python-dotenv \
            loguru tiktoken rich faster-whisper mutagen py7zr
    fi

    log "安装 Model Gateway 依赖..."
    if [[ -f "$PROJECT_DIR/model-gateway/pyproject.toml" ]]; then
        pip install -e "$PROJECT_DIR/model-gateway" 2>/dev/null || \
        pip install fastapi uvicorn[standard] pydantic pydantic-settings httpx python-dotenv loguru
    fi

    deactivate
    log "Python 环境设置完成"
}

# ============================================================
# Step 5: 构建前端
# ============================================================
build_frontend() {
    log "构建前端..."
    local PROJECT_DIR
    PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

    cd "$PROJECT_DIR/frontend"

    if [[ ! -d "node_modules" ]]; then
        npm install
    fi

    npm run build
    log "前端构建完成"
}

# ============================================================
# Step 6: 初始化数据库
# ============================================================
init_database() {
    log "初始化 PostgreSQL 数据库..."

    # 确保 PostgreSQL 正在运行
    if ! brew services list | grep -q "postgresql@16.*started"; then
        brew services start postgresql@16
        sleep 3
    fi

    # 创建数据库和用户（如果不存在）
    local PG_USER="kb_user"
    local PG_DB="personal_kb"
    local PG_PASS="kb_password"

    if ! psql -U "$USER" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$PG_USER'" 2>/dev/null | grep -q 1; then
        createuser "$PG_USER" 2>/dev/null || true
        psql -U "$USER" -d postgres -c "ALTER USER $PG_USER WITH PASSWORD '$PG_PASS';" 2>/dev/null || true
    fi

    if ! psql -U "$USER" -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "$PG_DB"; then
        createdb -O "$PG_USER" "$PG_DB" 2>/dev/null || true
    fi

    # 运行 Alembic 迁移
    local PROJECT_DIR
    PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
    source "$INSTALL_DIR/venv/bin/activate"
    cd "$PROJECT_DIR/backend"
    DATABASE_URL="postgresql+asyncpg://$PG_USER:$PG_PASS@localhost:5432/$PG_DB" \
        alembic upgrade head 2>/dev/null || warn "Alembic migration failed (may need manual setup)"
    deactivate

    log "数据库初始化完成"
}

# ============================================================
# Step 7: 创建配置文件
# ============================================================
create_config() {
    log "创建配置文件..."

    local PROJECT_DIR
    PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        # 更新路径配置
        sed -i '' "s|UPLOAD_DIR=./uploads|UPLOAD_DIR=$DATA_DIR/uploads|g" "$PROJECT_DIR/.env"
        sed -i '' "s|LOCAL_STORAGE_PATH=./storage|LOCAL_STORAGE_PATH=$DATA_DIR/storage|g" "$PROJECT_DIR/.env"

        # 生成安全密钥
        SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        sed -i '' "s|SECRET_KEY=change-me-to-a-random-string-at-least-32-chars|SECRET_KEY=$SECRET|g" "$PROJECT_DIR/.env"
        sed -i '' "s|JWT_SECRET_KEY=change-me-jwt-secret|JWT_SECRET_KEY=$JWT_SECRET|g" "$PROJECT_DIR/.env"
    fi

    # 创建数据目录
    mkdir -p "$DATA_DIR/uploads"
    mkdir -p "$DATA_DIR/storage"
    mkdir -p "$DATA_DIR/qdrant"
    mkdir -p "$DATA_DIR/minio"
    mkdir -p "$DATA_DIR/redis"
    mkdir -p "$DATA_DIR/logs"

    log "配置文件创建完成"
}

# ============================================================
# Step 8: 创建启动/停止脚本
# ============================================================
create_scripts() {
    log "创建启动和停止脚本..."

    local PROJECT_DIR
    PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"

    cat > "$INSTALL_DIR/start.sh" << 'START_SCRIPT'
#!/bin/bash
# PersonalNotebook 启动脚本
set -euo pipefail

INSTALL_DIR="$HOME/.personalnotebook"
DATA_DIR="$HOME/PersonalNotebook-Data"
PROJECT_DIR="$(cd "$(dirname "$0")/../../.." && pwd)"
LOG_DIR="$DATA_DIR/logs"
source "$INSTALL_DIR/venv/bin/activate"

mkdir -p "$LOG_DIR"

echo "🚀 启动 PersonalNotebook..."

# 1. 启动 PostgreSQL
if ! brew services list | grep -q "postgresql@16.*started"; then
    brew services start postgresql@16
    sleep 3
fi
echo "  ✅ PostgreSQL"

# 2. 启动 Redis
if ! brew services list | grep -q "redis.*started"; then
    brew services start redis
    sleep 1
fi
echo "  ✅ Redis"

# 3. 启动 MinIO
if ! pgrep -x minio &>/dev/null; then
    nohup minio server "$DATA_DIR/minio" --console-address ":9001" > "$LOG_DIR/minio.log" 2>&1 &
    sleep 2
    # 创建 bucket
    if command -v mc &>/dev/null; then
        mc alias set local http://localhost:9000 minioadmin minioadmin 2>/dev/null || true
        mc mb local/kb-assets --ignore-existing 2>/dev/null || true
    fi
fi
echo "  ✅ MinIO (http://localhost:9000, Console: http://localhost:9001)"

# 4. 启动 Qdrant
if ! pgrep -x qdrant &>/dev/null; then
    nohup "$INSTALL_DIR/qdrant/qdrant" --storage-path "$DATA_DIR/qdrant" > "$LOG_DIR/qdrant.log" 2>&1 &
    sleep 2
fi
echo "  ✅ Qdrant (http://localhost:6333)"

# 5. 启动 Model Gateway
if ! pgrep -f "model-gateway/main.py" &>/dev/null; then
    cd "$PROJECT_DIR/model-gateway"
    nohup python3 main.py > "$LOG_DIR/model-gateway.log" 2>&1 &
    sleep 2
fi
echo "  ✅ Model Gateway (http://localhost:8900)"

# 6. 启动 Backend API
if ! pgrep -f "app.main:app" &>/dev/null; then
    cd "$PROJECT_DIR/backend"
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/backend.log" 2>&1 &
    sleep 3
fi
echo "  ✅ Backend API (http://localhost:8000)"

# 7. 启动 Celery Worker
if ! pgrep -f "celery_app" &>/dev/null; then
    cd "$PROJECT_DIR/backend"
    nohup celery -A app.workers.celery_app worker --loglevel=info > "$LOG_DIR/celery.log" 2>&1 &
    sleep 2
fi
echo "  ✅ Celery Worker"

# 8. 启动 Frontend
if ! pgrep -f "next start" &>/dev/null; then
    cd "$PROJECT_DIR/frontend"
    nohup npx next start -p 3000 > "$LOG_DIR/frontend.log" 2>&1 &
    sleep 3
fi
echo "  ✅ Frontend (http://localhost:3000)"

echo ""
echo "🎉 PersonalNotebook 已启动！"
echo ""
echo "   📱 前端界面: http://localhost:3000"
echo "   🔧 后端 API:  http://localhost:8000/docs"
echo "   📊 MinIO:      http://localhost:9001 (minioadmin/minioadmin)"
echo "   📝 日志目录:   $LOG_DIR"
echo ""
echo "   停止服务: $INSTALL_DIR/stop.sh"
echo ""
START_SCRIPT
    chmod +x "$INSTALL_DIR/start.sh"

    cat > "$INSTALL_DIR/stop.sh" << 'STOP_SCRIPT'
#!/bin/bash
# PersonalNotebook 停止脚本

echo "🛑 停止 PersonalNotebook..."

# 停止 Frontend
pkill -f "next start" 2>/dev/null && echo "  ⏹ Frontend" || echo "  ⏭ Frontend (not running)"

# 停止 Celery
pkill -f "celery_app" 2>/dev/null && echo "  ⏹ Celery Worker" || echo "  ⏭ Celery Worker (not running)"

# 停止 Backend
pkill -f "app.main:app" 2>/dev/null && echo "  ⏹ Backend API" || echo "  ⏭ Backend API (not running)"

# 停止 Model Gateway
pkill -f "model-gateway/main.py" 2>/dev/null && echo "  ⏹ Model Gateway" || echo "  ⏭ Model Gateway (not running)"

# 停止 Qdrant
pkill -x qdrant 2>/dev/null && echo "  ⏹ Qdrant" || echo "  ⏭ Qdrant (not running)"

# 停止 MinIO
pkill -x minio 2>/dev/null && echo "  ⏹ MinIO" || echo "  ⏭ MinIO (not running)"

# 停止 Redis
brew services stop redis 2>/dev/null && echo "  ⏹ Redis" || echo "  ⏭ Redis (not running)"

# 停止 PostgreSQL
brew services stop postgresql@16 2>/dev/null && echo "  ⏹ PostgreSQL" || echo "  ⏭ PostgreSQL (not running)"

echo ""
echo "✅ PersonalNotebook 已停止"
STOP_SCRIPT
    chmod +x "$INSTALL_DIR/stop.sh"

    # 创建状态检查脚本
    cat > "$INSTALL_DIR/status.sh" << 'STATUS_SCRIPT'
#!/bin/bash
# PersonalNotebook 服务状态检查

echo "🔍 PersonalNotebook 服务状态"
echo "================================"

check_port() {
    local name=$1 port=$2
    if lsof -i :$port -sTCP:LISTEN &>/dev/null; then
        echo "  ✅ $name (port $port) — running"
    else
        echo "  ❌ $name (port $port) — stopped"
    fi
}

check_port "Frontend"    3000
check_port "Backend API" 8000
check_port "Model Gateway" 8900
check_port "MinIO API"   9000
check_port "MinIO Console" 9001
check_port "Qdrant"      6333
check_port "PostgreSQL"  5432
check_port "Redis"       6379

echo ""
echo "  日志目录: $HOME/PersonalNotebook-Data/logs"
STATUS_SCRIPT
    chmod +x "$INSTALL_DIR/status.sh"

    log "启动/停止/状态脚本创建完成"
}

# ============================================================
# Main
# ============================================================
main() {
    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║    PersonalNotebook v$VERSION 安装向导     ║"
    echo "║    macOS 一键安装脚本                     ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""

    mkdir -p "$INSTALL_DIR"
    exec > >(tee -a "$LOG_FILE") 2>&1

    check_system
    install_homebrew
    install_infra
    install_runtimes
    setup_python_env
    build_frontend
    create_config
    init_database
    create_scripts

    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║    ✅ PersonalNotebook 安装完成！        ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""
    echo "  启动服务:  $INSTALL_DIR/start.sh"
    echo "  停止服务:  $INSTALL_DIR/stop.sh"
    echo "  查看状态:  $INSTALL_DIR/status.sh"
    echo "  前端界面:  http://localhost:3000"
    echo "  API 文档:  http://localhost:8000/docs"
    echo "  数据目录:  $DATA_DIR"
    echo "  日志目录:  $DATA_DIR/logs"
    echo ""

    # 询问是否立即启动
    read -p "是否立即启动 PersonalNotebook？[Y/n] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Nn]$ ]]; then
        "$INSTALL_DIR/start.sh"
    fi
}

main "$@"

#!/bin/bash
# ============================================================
# PersonalNotebook — macOS DMG 构建脚本
# 在项目根目录运行: bash dist/macos/build_dmg.sh
# ============================================================
set -euo pipefail

VERSION="0.3.0"
APP_NAME="PersonalNotebook"
PROJECT_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist/macos"
DMG_DIR="$DIST_DIR/dmg_staging"
DMG_OUTPUT="$DIST_DIR/${APP_NAME}-${VERSION}-macos.dmg"

echo "🛠  Building ${APP_NAME} v${VERSION} macOS DMG..."

# Step 1: 复制完整项目到 Resources
echo "  📦 打包项目文件..."
RESOURCES_DIR="$DIST_DIR/$APP_NAME.app/Contents/Resources/project"
rm -rf "$RESOURCES_DIR"
mkdir -p "$RESOURCES_DIR"

# 复制核心项目文件（排除 .git, node_modules, __pycache__, .next, build artifacts）
rsync -a \
    --exclude='.git' \
    --exclude='node_modules' \
    --exclude='__pycache__' \
    --exclude='.next' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='dist' \
    --exclude='*.egg-info' \
    --exclude='build/' \
    --exclude='.env' \
    --exclude='.workbuddy' \
    --exclude='.github' \
    --exclude='.pytest_cache' \
    --exclude='tmp' \
    "$PROJECT_DIR/" "$RESOURCES_DIR/"

# 重新生成 .env 从 .env.example
if [[ -f "$RESOURCES_DIR/.env.example" ]]; then
    cp "$RESOURCES_DIR/.env.example" "$RESOURCES_DIR/.env"
fi

# Step 2: 更新安装脚本中的项目路径引用
# 安装脚本需要知道项目文件在 Resources/project/ 中
cat > "$DIST_DIR/$APP_NAME.app/Contents/Resources/scripts/install.sh" << 'INSTALL_SCRIPT'
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

# 项目文件位置（在 .app 包内）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_RESOURCES="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$APP_RESOURCES/project"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${GREEN}[$(date '+%H:%M:%S')]${NC} $1"; }
warn() { echo -e "${YELLOW}[$(date '+%H:%M:%S')] WARN${NC} $1"; }
err()  { echo -e "${RED}[$(date '+%H:%M:%S')] ERROR${NC} $1"; }

# ============================================================
# Step 1: 安装 Homebrew
# ============================================================
install_homebrew() {
    if command -v brew &>/dev/null; then
        log "Homebrew 已安装: $(brew --version | head -1)"
        return 0
    fi
    log "安装 Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    if [[ "$(uname -m)" == "arm64" ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
        if ! grep -q "/opt/homebrew/bin" "$HOME/.zprofile" 2>/dev/null; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
        fi
    fi
    log "Homebrew 安装完成"
}

# ============================================================
# Step 2: 安装基础设施
# ============================================================
install_infra() {
    log "安装基础设施服务..."

    # PostgreSQL
    if ! brew list postgresql@16 &>/dev/null; then
        log "安装 PostgreSQL 16..."
        brew install postgresql@16
        brew link postgresql@16 --force 2>/dev/null || true
    fi

    # Redis
    if ! brew list redis &>/dev/null; then
        log "安装 Redis..."
        brew install redis
    fi

    # MinIO
    if ! brew list minio &>/dev/null; then
        log "安装 MinIO..."
        brew install minio
    fi

    # FFmpeg
    if ! command -v ffmpeg &>/dev/null; then
        log "安装 FFmpeg..."
        brew install ffmpeg
    fi

    # Qdrant
    local QDRANT_DIR="$INSTALL_DIR/qdrant"
    if [[ ! -x "$QDRANT_DIR/qdrant" ]]; then
        log "下载 Qdrant..."
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
    log "基础设施安装完成"
}

# ============================================================
# Step 3: Python 环境
# ============================================================
setup_python() {
    log "设置 Python 环境..."
    if ! command -v python3 &>/dev/null; then
        brew install python@3.13
    fi

    local VENV_DIR="$INSTALL_DIR/venv"
    [[ ! -d "$VENV_DIR" ]] && python3 -m venv "$VENV_DIR"
    source "$VENV_DIR/bin/activate"

    log "安装 Python 依赖（可能需要几分钟）..."
    pip install --upgrade pip setuptools wheel -q

    # 后端依赖
    pip install fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" asyncpg psycopg2-binary \
        alembic pydantic pydantic-settings "celery[redis]" redis minio qdrant-client \
        PyMuPDF python-docx python-pptx openpyxl pandas markdown-it-py python-frontmatter \
        Pillow httpx aiofiles "python-jose[cryptography]" "passlib[bcrypt]" python-dotenv \
        loguru tiktoken rich faster-whisper mutagen py7zr -q 2>/dev/null

    deactivate
    log "Python 环境就绪"
}

# ============================================================
# Step 4: 构建前端
# ============================================================
build_frontend() {
    log "构建前端..."
    if ! command -v node &>/dev/null; then
        brew install node@22
    fi

    cd "$PROJECT_DIR/frontend"
    [[ ! -d "node_modules" ]] && npm install --legacy-peer-deps
    npm run build
    log "前端构建完成"
}

# ============================================================
# Step 5: 初始化配置和数据库
# ============================================================
init_config() {
    log "初始化配置..."

    mkdir -p "$DATA_DIR"/{uploads,storage,qdrant,minio,redis,logs}

    # 创建 .env
    if [[ ! -f "$PROJECT_DIR/.env" ]]; then
        cp "$PROJECT_DIR/.env.example" "$PROJECT_DIR/.env"
        sed -i '' "s|UPLOAD_DIR=./uploads|UPLOAD_DIR=$DATA_DIR/uploads|g" "$PROJECT_DIR/.env"
        sed -i '' "s|LOCAL_STORAGE_PATH=./storage|LOCAL_STORAGE_PATH=$DATA_DIR/storage|g" "$PROJECT_DIR/.env"

        SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me-random-secret")
        JWT_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(32))" 2>/dev/null || echo "change-me-jwt-secret")
        sed -i '' "s|SECRET_KEY=change-me-to-a-random-string-at-least-32-chars|SECRET_KEY=$SECRET|g" "$PROJECT_DIR/.env"
        sed -i '' "s|JWT_SECRET_KEY=change-me-jwt-secret|JWT_SECRET_KEY=$JWT_SECRET|g" "$PROJECT_DIR/.env"
    fi

    # 初始化 PostgreSQL
    if ! brew services list | grep -q "postgresql@16.*started"; then
        brew services start postgresql@16
        sleep 3
    fi

    if ! psql -U "$USER" -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='kb_user'" 2>/dev/null | grep -q 1; then
        createuser kb_user 2>/dev/null || true
        psql -U "$USER" -d postgres -c "ALTER USER kb_user WITH PASSWORD 'kb_password';" 2>/dev/null || true
    fi
    if ! psql -U "$USER" -lqt 2>/dev/null | cut -d \| -f 1 | grep -qw "personal_kb"; then
        createdb -O kb_user personal_kb 2>/dev/null || true
    fi

    # 运行数据库迁移
    source "$INSTALL_DIR/venv/bin/activate"
    cd "$PROJECT_DIR/backend"
    DATABASE_URL="postgresql+asyncpg://kb_user:kb_password@localhost:5432/personal_kb" \
        alembic upgrade head 2>/dev/null || warn "数据库迁移需要手动运行"
    deactivate

    log "配置初始化完成"
}

# ============================================================
# Step 6: 创建启动/停止脚本
# ============================================================
create_scripts() {
    log "创建启动脚本..."

    cat > "$INSTALL_DIR/start.sh" << 'START_SH'
#!/bin/bash
set -euo pipefail

INSTALL_DIR="$HOME/.personalnotebook"
DATA_DIR="$HOME/PersonalNotebook-Data"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_RESOURCES="$(cd "$SCRIPT_DIR/.." && pwd)"
PROJECT_DIR="$APP_RESOURCES/project"
LOG_DIR="$DATA_DIR/logs"

source "$INSTALL_DIR/venv/bin/activate"
mkdir -p "$LOG_DIR"

echo "🚀 启动 PersonalNotebook..."

# PostgreSQL
if ! brew services list | grep -q "postgresql@16.*started"; then
    brew services start postgresql@16 && sleep 3
fi
echo "  ✅ PostgreSQL"

# Redis
if ! brew services list | grep -q "redis.*started"; then
    brew services start redis && sleep 1
fi
echo "  ✅ Redis"

# MinIO
if ! pgrep -x minio &>/dev/null; then
    nohup minio server "$DATA_DIR/minio" --console-address ":9001" > "$LOG_DIR/minio.log" 2>&1 &
    sleep 2
fi
echo "  ✅ MinIO"

# Qdrant
if ! pgrep -x qdrant &>/dev/null; then
    nohup "$INSTALL_DIR/qdrant/qdrant" --storage-path "$DATA_DIR/qdrant" > "$LOG_DIR/qdrant.log" 2>&1 &
    sleep 2
fi
echo "  ✅ Qdrant"

# Model Gateway
if ! pgrep -f "model-gateway/main.py" &>/dev/null; then
    cd "$PROJECT_DIR/model-gateway"
    nohup python3 main.py > "$LOG_DIR/model-gateway.log" 2>&1 &
    sleep 2
fi
echo "  ✅ Model Gateway"

# Backend
if ! pgrep -f "app.main:app" &>/dev/null; then
    cd "$PROJECT_DIR/backend"
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$LOG_DIR/backend.log" 2>&1 &
    sleep 3
fi
echo "  ✅ Backend API"

# Celery
if ! pgrep -f "celery_app" &>/dev/null; then
    cd "$PROJECT_DIR/backend"
    nohup celery -A app.workers.celery_app worker --loglevel=info > "$LOG_DIR/celery.log" 2>&1 &
    sleep 2
fi
echo "  ✅ Celery Worker"

# Frontend
if ! pgrep -f "next start" &>/dev/null; then
    cd "$PROJECT_DIR/frontend"
    nohup npx next start -p 3000 > "$LOG_DIR/frontend.log" 2>&1 &
    sleep 3
fi
echo "  ✅ Frontend"

echo ""
echo "🎉 PersonalNotebook 已启动！"
echo ""
echo "   📱 前端:     http://localhost:3000"
echo "   🔧 API:      http://localhost:8000/docs"
echo "   📊 MinIO:    http://localhost:9001"
echo "   📝 日志:     $LOG_DIR"
echo "   🛑 停止:     $INSTALL_DIR/stop.sh"
START_SH
    chmod +x "$INSTALL_DIR/start.sh"

    cat > "$INSTALL_DIR/stop.sh" << 'STOP_SH'
#!/bin/bash
echo "🛑 停止 PersonalNotebook..."
pkill -f "next start" 2>/dev/null && echo "  ⏹ Frontend" || true
pkill -f "celery_app" 2>/dev/null && echo "  ⏹ Celery" || true
pkill -f "app.main:app" 2>/dev/null && echo "  ⏹ Backend" || true
pkill -f "model-gateway/main.py" 2>/dev/null && echo "  ⏹ Model Gateway" || true
pkill -x qdrant 2>/dev/null && echo "  ⏹ Qdrant" || true
pkill -x minio 2>/dev/null && echo "  ⏹ MinIO" || true
brew services stop redis 2>/dev/null && echo "  ⏹ Redis" || true
brew services stop postgresql@16 2>/dev/null && echo "  ⏹ PostgreSQL" || true
echo "✅ 已停止"
STOP_SH
    chmod +x "$INSTALL_DIR/stop.sh"

    cat > "$INSTALL_DIR/status.sh" << 'STATUS_SH'
#!/bin/bash
echo "🔍 PersonalNotebook 服务状态"
echo "================================"
for svc in "Frontend:3000" "Backend:8000" "Model Gateway:8900" "MinIO:9000" "Qdrant:6333" "PostgreSQL:5432" "Redis:6379"; do
    name="${svc%:*}"; port="${svc#*:}"
    if lsof -i :$port -sTCP:LISTEN &>/dev/null; then
        echo "  ✅ $name (:$port)"
    else
        echo "  ❌ $name (:$port)"
    fi
done
STATUS_SH
    chmod +x "$INSTALL_DIR/status.sh"

    log "脚本创建完成"
}

# ============================================================
# Main
# ============================================================
main() {
    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║    PersonalNotebook v$VERSION 安装向导     ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""

    mkdir -p "$INSTALL_DIR"
    exec > >(tee -a "$LOG_FILE") 2>&1

    install_homebrew
    install_infra
    setup_python
    build_frontend
    init_config
    create_scripts

    echo ""
    echo "╔══════════════════════════════════════════╗"
    echo "║    ✅ 安装完成！                          ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""
    echo "  启动: $INSTALL_DIR/start.sh"
    echo "  停止: $INSTALL_DIR/stop.sh"
    echo "  状态: $INSTALL_DIR/status.sh"
    echo ""

    read -p "是否立即启动？[Y/n] " -n 1 -r
    echo
    [[ ! $REPLY =~ ^[Nn]$ ]] && "$INSTALL_DIR/start.sh"
}

main "$@"
INSTALL_SCRIPT
    chmod +x "$DIST_DIR/$APP_NAME.app/Contents/Resources/scripts/install.sh"

    # 更新 .app 启动器中的路径
    cat > "$DIST_DIR/$APP_NAME.app/Contents/MacOS/$APP_NAME" << 'APP_LAUNCHER'
#!/bin/bash
INSTALL_DIR="$HOME/.personalnotebook"
APP_RESOURCES="$(cd "$(dirname "$0")/../Resources" && pwd)"

if [[ ! -d "$INSTALL_DIR/venv" ]]; then
    osascript -e '
    tell application "Terminal"
        activate
        set shellScript to "bash \"'"$APP_RESOURCES"'/scripts/install.sh\"; exit"
        do script shellScript
    end tell
    '
else
    if lsof -i :3000 -sTCP:LISTEN &>/dev/null; then
        open "http://localhost:3000"
    else
        osascript -e '
        tell application "Terminal"
            activate
            set shellScript to "bash \"'"$INSTALL_DIR"'/start.sh\"; sleep 5; open \"http://localhost:3000\""
            do script shellScript
        end tell
        '
    fi
fi
APP_LAUNCHER
    chmod +x "$DIST_DIR/$APP_NAME.app/Contents/MacOS/$APP_NAME"

# Step 3: 创建 DMG staging 目录
echo "  📁 准备 DMG 内容..."
rm -rf "$DMG_DIR"
mkdir -p "$DMG_DIR"

cp -r "$DIST_DIR/$APP_NAME.app" "$DMG_DIR/"
ln -s /Applications "$DMG_DIR/Applications"

# 创建 README
cat > "$DMG_DIR/README.txt" << 'README'
═══════════════════════════════════════════
  PersonalNotebook — 个人知识库 RAG 系统
═══════════════════════════════════════════

安装方式:
  1. 将 PersonalNotebook.app 拖入 Applications 文件夹
  2. 双击 PersonalNotebook.app 启动
  3. 首次启动会自动安装所有依赖（需要网络连接）
  4. 安装完成后自动启动所有服务
  5. 浏览器打开 http://localhost:3000

手动操作:
  启动服务: ~/.personalnotebook/start.sh
  停止服务: ~/.personalnotebook/stop.sh
  查看状态: ~/.personalnotebook/status.sh

系统要求:
  - macOS 12.0 或更高版本
  - Apple Silicon (M1/M2/M3/M4) 或 Intel Mac
  - 至少 4GB 可用磁盘空间
  - 网络连接（首次安装需要下载依赖）

包含的服务:
  - PostgreSQL 16 (数据库)
  - Redis 7 (缓存/队列)
  - MinIO (对象存储)
  - Qdrant (向量数据库)
  - FastAPI Backend (API 服务)
  - Model Gateway (模型网关)
  - Next.js Frontend (Web 界面)
  - Celery Worker (异步任务)

数据存储位置:
  ~/PersonalNotebook-Data/
README

# Step 4: 创建 DMG
echo "  💿 创建 DMG 磁盘镜像..."
hdiutil create -volname "$APP_NAME" -srcfolder "$DMG_DIR" -ov -format UDZO "$DMG_OUTPUT"

# 清理
rm -rf "$DMG_DIR"

echo ""
echo "✅ DMG 构建完成: $DMG_OUTPUT"
echo "   大小: $(du -sh "$DMG_OUTPUT" | cut -f1)"

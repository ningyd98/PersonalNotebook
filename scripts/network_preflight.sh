#!/bin/bash
# PersonalNotebook Network Preflight — Phase 2D
# 检查 Core 局域网可达性，输出移动端配对地址
set -e

echo "=========================================="
echo " Network Preflight Check"
echo "=========================================="

# 1. Detect platform and local IPs
echo "--- 1. Local IPs ---"
if [[ "$OSTYPE" == "darwin"* ]]; then
  ifconfig | grep "inet " | grep -v 127.0.0.1 | awk '{printf "  macOS: %s\n", $2}'
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  ip -4 addr show | grep "inet " | grep -v 127.0.0.1 | awk '{printf "  Linux: %s\n", $2}' | cut -d/ -f1
elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" ]]; then
  ipconfig | grep "IPv4" | awk '{printf "  Windows: %s\n", $NF}'
else
  echo "  Unknown platform — check your local IP manually with ifconfig / ipconfig"
fi

# 2. Check local health
echo ""
echo "--- 2. Core health (localhost) ---"
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
  echo "  ✅ Core responding on localhost:8000"
else
  echo "  ❌ Core not responding — start with: docker compose up -d"
  echo "     or: uvicorn app.main:app --host 0.0.0.0 --port 8000"
fi

# 3. Check port 8000 listening
echo ""
echo "--- 3. Port 8000 ---"
if command -v lsof &>/dev/null; then
  lsof -i :8000 -sTCP:LISTEN 2>/dev/null | head -5 || echo "  (no listener detected)"
elif command -v netstat &>/dev/null; then
  netstat -an | grep "\.8000.*LISTEN" || echo "  (no listener detected)"
fi

# 4. Output pairing URL for mobile
echo ""
echo "--- 4. Mobile pairing URL ---"
MOBILE_IP=""
if [[ "$OSTYPE" == "darwin"* ]]; then
  MOBILE_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | awk 'NR==1{print $2}')
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  MOBILE_IP=$(ip -4 addr show | grep "inet " | grep -v 127.0.0.1 | awk 'NR==1{print $2}' | cut -d/ -f1)
fi
if [ -n "$MOBILE_IP" ]; then
  echo "  Mobile Core URL: http://$MOBILE_IP:8000"
  echo "  Verify in mobile browser: http://$MOBILE_IP:8000/health"
else
  echo "  Could not detect local IP — find it manually and use:"
  echo "  http://YOUR_IP:8000"
fi

echo ""
echo "--- 5. Check mobile reachability ---"
echo "  On your phone, open: http://$MOBILE_IP:8000/health"
echo "  Expected: { \"status\": \"ok\", ... }"
echo ""
echo "  If unreachable:"
echo "  - Ensure phone and computer are on same Wi-Fi"
echo "  - Check macOS firewall: System Settings → Network → Firewall"
echo "  - Ensure Core listens on 0.0.0.0, not 127.0.0.1"
echo ""
echo "✅ Preflight complete"

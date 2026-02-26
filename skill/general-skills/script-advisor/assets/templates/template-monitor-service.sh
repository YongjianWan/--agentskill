#!/bin/bash
# ============================================================================
# 脚本名称: monitor-{{SERVICE_NAME}}.sh
# 功能描述: 监控{{SERVICE_DESCRIPTION}}服务状态，自动重启失败的服务
# 创建日期: $(date +%Y-%m-%d)
# 版本: 1.0.0
# ============================================================================
# 半结构化任务模板 - 服务监控脚本
# 替换以下变量:
#   {{SERVICE_NAME}}        - 服务名称（英文，如gateway、wecom、memory等）
#   {{SERVICE_DESCRIPTION}} - 服务描述（中文，如Gateway网关、WeCom企业微信等）
#   {{CHECK_COMMAND}}       - 检查服务状态的命令
#   {{START_COMMAND}}       - 启动服务的命令
#   {{RESTART_COMMAND}}     - 重启服务的命令（可选，默认使用start）
#   {{CHECK_INTERVAL}}      - 检查间隔（秒，默认60）
#   {{MAX_RETRIES}}         - 最大重试次数（默认3）
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# 配置常量
# ----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_BASENAME="monitor-{{SERVICE_NAME}}"
LOG_FILE="/var/log/openclaw/${SCRIPT_BASENAME}.log"
STATUS_FILE="/tmp/${SCRIPT_BASENAME}.status"

# ----------------------------------------------------------------------------
# 颜色输出
# ----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE" >&2; }

# ----------------------------------------------------------------------------
# 配置变量 - 根据实际服务修改
# ----------------------------------------------------------------------------
SERVICE_NAME="{{SERVICE_NAME}}"
SERVICE_DESCRIPTION="{{SERVICE_DESCRIPTION}}"
CHECK_COMMAND="{{CHECK_COMMAND}}"
START_COMMAND="{{START_COMMAND}}"
RESTART_COMMAND="{{RESTART_COMMAND:-$START_COMMAND}}"
CHECK_INTERVAL={{CHECK_INTERVAL:-60}}
MAX_RETRIES={{MAX_RETRIES:-3}}

# ----------------------------------------------------------------------------
# 参数解析
# ----------------------------------------------------------------------------
parse_args() {
    local mode="daemon"  # daemon|check-once
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --once)
                mode="check-once"
                shift
                ;;
            --interval)
                CHECK_INTERVAL="$2"
                shift 2
                ;;
            --brief)
                export OUTPUT_MODE="brief"
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    echo "$mode"
}

# ----------------------------------------------------------------------------
# 检查服务状态
# ----------------------------------------------------------------------------
check_service() {
    log_info "检查{{SERVICE_DESCRIPTION}}服务状态..."
    
    if eval "$CHECK_COMMAND" &>/dev/null; then
        echo "running"
        log_success "{{SERVICE_DESCRIPTION}}服务运行正常"
        return 0
    else
        echo "stopped"
        log_error "{{SERVICE_DESCRIPTION}}服务已停止"
        return 1
    fi
}

# ----------------------------------------------------------------------------
# 启动服务
# ----------------------------------------------------------------------------
start_service() {
    log_info "启动{{SERVICE_DESCRIPTION}}服务..."
    
    if eval "$START_COMMAND" &>/dev/null; then
        log_success "{{SERVICE_DESCRIPTION}}服务启动成功"
        
        # 验证启动是否成功
        sleep 5
        if check_service | grep -q "running"; then
            return 0
        else
            return 1
        fi
    else
        log_error "{{SERVICE_DESCRIPTION}}服务启动失败"
        return 1
    fi
}

# ----------------------------------------------------------------------------
# 重启服务
# ----------------------------------------------------------------------------
restart_service() {
    log_info "重启{{SERVICE_DESCRIPTION}}服务..."
    
    if eval "$RESTART_COMMAND" &>/dev/null; then
        log_success "{{SERVICE_DESCRIPTION}}服务重启成功"
        
        # 验证重启是否成功
        sleep 5
        if check_service | grep -q "running"; then
            return 0
        else
            return 1
        fi
    else
        log_error "{{SERVICE_DESCRIPTION}}服务重启失败"
        return 1
    fi
}

# ----------------------------------------------------------------------------
# 单次检查模式
# ----------------------------------------------------------------------------
check_once() {
    local status
    status=$(check_service)
    
    if [[ "$OUTPUT_MODE" == "brief" ]]; then
        # 简洁输出（减少token消耗）
        if [[ "$status" == "running" ]]; then
            echo "✅ {{SERVICE_NAME}}: 运行正常"
        else
            echo "❌ {{SERVICE_NAME}}: 已停止"
        fi
    else
        # 详细输出
        log_info "服务状态: $status"
        
        if [[ "$status" == "stopped" ]]; then
            log_warning "尝试自动重启..."
            if start_service; then
                log_success "自动重启成功"
            else
                log_error "自动重启失败，需要手动干预"
                return 1
            fi
        fi
    fi
    
    return 0
}

# ----------------------------------------------------------------------------
# 守护进程模式
# ----------------------------------------------------------------------------
run_daemon() {
    log_info "启动{{SERVICE_DESCRIPTION}}监控守护进程"
    log_info "检查间隔: ${CHECK_INTERVAL}秒"
    log_info "最大重试次数: ${MAX_RETRIES}"
    
    local failure_count=0
    
    while true; do
        if check_service | grep -q "running"; then
            # 服务正常
            failure_count=0
            log_info "{{SERVICE_DESCRIPTION}}服务正常（连续失败次数: $failure_count）"
        else
            # 服务异常
            ((failure_count++))
            log_error "{{SERVICE_DESCRIPTION}}服务异常（失败次数: $failure_count/${MAX_RETRIES}）"
            
            if [[ $failure_count -ge $MAX_RETRIES ]]; then
                log_error "达到最大重试次数，尝试重启服务..."
                if restart_service; then
                    failure_count=0
                    log_success "重启成功，重置失败计数"
                else
                    log_error "重启失败，可能需要人工干预"
                    # 保持failure_count，下次继续尝试
                fi
            else
                log_warning "等待下次检查再决定是否重启"
            fi
        fi
        
        # 记录状态文件
        echo "last_check=$(date +%s)" > "$STATUS_FILE"
        echo "failure_count=$failure_count" >> "$STATUS_FILE"
        echo "status=$(check_service)" >> "$STATUS_FILE"
        
        sleep "$CHECK_INTERVAL"
    done
}

# ----------------------------------------------------------------------------
# 主逻辑
# ----------------------------------------------------------------------------
main() {
    log_info "=== {{SERVICE_DESCRIPTION}}服务监控 ==="
    
    local mode
    mode=$(parse_args "$@")
    
    # 确保日志目录存在
    mkdir -p "$(dirname "$LOG_FILE")"
    
    case "$mode" in
        "check-once")
            check_once
            ;;
        "daemon")
            run_daemon
            ;;
        *)
            log_error "未知模式: $mode"
            exit 1
            ;;
    esac
}

# ----------------------------------------------------------------------------
# 帮助信息
# ----------------------------------------------------------------------------
show_usage() {
    cat <<EOF
{{SERVICE_DESCRIPTION}}服务监控脚本

用法: $0 [选项]

选项:
  --once             单次检查模式（不进入守护进程）
  --interval <秒>    检查间隔（默认: 60）
  --brief            简洁输出模式（减少token消耗）
  -h, --help        显示此帮助信息

示例:
  $0                  # 守护进程模式监控服务
  $0 --once --brief   # 单次检查，简洁输出
  $0 --interval 30    # 30秒间隔监控

监控逻辑:
  1. 每${CHECK_INTERVAL}秒检查服务状态
  2. 连续失败${MAX_RETRIES}次后自动重启
  3. 记录日志到: $LOG_FILE
  4. 状态文件: $STATUS_FILE

服务配置:
  服务名称: {{SERVICE_NAME}}
  检查命令: {{CHECK_COMMAND}}
  启动命令: {{START_COMMAND}}
  重启命令: ${RESTART_COMMAND}
EOF
}

# ----------------------------------------------------------------------------
# 脚本入口
# ----------------------------------------------------------------------------
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
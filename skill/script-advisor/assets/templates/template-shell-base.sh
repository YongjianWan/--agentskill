#!/bin/bash
# ============================================================================
# 脚本名称: {{SCRIPT_NAME}}.sh
# 功能描述: {{SCRIPT_DESCRIPTION}}
# 创建日期: $(date +%Y-%m-%d)
# 版本: 1.0.0
# ============================================================================
# 半结构化任务模板 - 基础Shell脚本
# 替换以下变量:
#   {{SCRIPT_NAME}}     - 脚本名称（英文，无空格）
#   {{SCRIPT_DESCRIPTION}} - 功能描述（中文）
#   {{AUTHOR}}          - 作者（可选）
#   {{VARIABLES}}       - 自定义变量部分（如需）
#   {{MAIN_LOGIC}}      - 主逻辑实现
#   {{HELP_TEXT}}       - 帮助信息
# ============================================================================

set -euo pipefail  # 严格模式：错误退出、未定义变量退出、管道错误检测

# ----------------------------------------------------------------------------
# 配置常量
# ----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_BASENAME="$(basename "$0" .sh)"
LOG_FILE="/var/log/openclaw-${SCRIPT_BASENAME}.log"
CONFIG_FILE="/root/.openclaw/openclaw.json"  # 默认配置路径

# ----------------------------------------------------------------------------
# 颜色输出
# ----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'  # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE" >&2; }

# ----------------------------------------------------------------------------
# 自定义变量区 - 根据实际需求修改
# ----------------------------------------------------------------------------
{{VARIABLES}}

# ----------------------------------------------------------------------------
# 参数解析
# ----------------------------------------------------------------------------
parse_args() {
    local help_mode=false
    local verbose_mode=false
    local dry_run=false
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            -h|--help)
                help_mode=true
                shift
                ;;
            -v|--verbose)
                verbose_mode=true
                shift
                ;;
            --dry-run)
                dry_run=true
                shift
                ;;
            --brief)
                # 简洁输出模式（用于减少token消耗）
                export OUTPUT_MODE="brief"
                shift
                ;;
            *)
                log_error "未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    if [[ "$help_mode" == true ]]; then
        show_usage
        exit 0
    fi
    
    # 设置全局标志
    export VERBOSE="$verbose_mode"
    export DRY_RUN="$dry_run"
}

# ----------------------------------------------------------------------------
# 主逻辑
# ----------------------------------------------------------------------------
main() {
    log_info "=== 开始执行: {{SCRIPT_NAME}} ==="
    log_info "参数: $*"
    
    parse_args "$@"
    
    # 检查前置条件
    check_prerequisites
    
    # 执行主逻辑
    {{MAIN_LOGIC}}
    
    log_success "=== 执行完成 ==="
}

# ----------------------------------------------------------------------------
# 前置条件检查
# ----------------------------------------------------------------------------
check_prerequisites() {
    log_info "检查前置条件..."
    
    # 检查OpenClaw配置是否存在
    if [[ ! -f "$CONFIG_FILE" ]]; then
        log_error "OpenClaw配置文件不存在: $CONFIG_FILE"
        exit 1
    fi
    
    # 检查必要命令
    local required_commands=("jq" "curl" "openclaw")
    for cmd in "${required_commands[@]}"; do
        if ! command -v "$cmd" &>/dev/null; then
            log_warning "命令 '$cmd' 未安装，某些功能可能受限"
        fi
    done
    
    # 检查日志目录
    local log_dir="$(dirname "$LOG_FILE")"
    if [[ ! -d "$log_dir" ]]; then
        mkdir -p "$log_dir"
        log_info "创建日志目录: $log_dir"
    fi
}

# ----------------------------------------------------------------------------
# 帮助信息
# ----------------------------------------------------------------------------
show_usage() {
    cat <<EOF
{{HELP_TEXT}}
EOF
}

# ----------------------------------------------------------------------------
# 清理函数（如果需要）
# ----------------------------------------------------------------------------
cleanup() {
    if [[ -n "${TEMP_DIR:-}" && -d "$TEMP_DIR" ]]; then
        rm -rf "$TEMP_DIR"
        log_info "清理临时目录: $TEMP_DIR"
    fi
}

# ----------------------------------------------------------------------------
# 信号处理
# ----------------------------------------------------------------------------
trap cleanup EXIT INT TERM

# ----------------------------------------------------------------------------
# 脚本入口
# ----------------------------------------------------------------------------
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
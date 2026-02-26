#!/bin/bash
# ============================================================================
# 脚本名称: {{SCRIPT_NAME}}.sh
# 功能描述: {{SCRIPT_DESCRIPTION}}
# 创建日期: $(date +%Y-%m-%d)
# 版本: 1.0.0
# ============================================================================
# 半结构化任务模板 - 添加--brief参数优化脚本输出
# 替换以下变量:
#   {{SCRIPT_NAME}}        - 脚本名称（英文，无空格）
#   {{SCRIPT_DESCRIPTION}} - 功能描述（中文）
#   {{BASE_COMMAND}}       - 原始检查命令（如：openclaw status, jq '.channels.wecom'）
#   {{FILTER_PATTERN}}     - grep过滤正则（如：-i wecom, ERROR\|WARN）
#   {{OUTPUT_LINES}}       - 简洁模式保留几行（默认：3）
#   {{FALLBACK_COMMAND}}   - 备用检查命令（可选）
#   {{TIMEOUT_SECONDS}}    - 命令超时时间（默认：5）
# ============================================================================
# 适用场景：
#   1. 高频执行的状态检查脚本
#   2. 输出冗长但只需关键信息的命令
#   3. 需要快速查看结果的场景
# 
# 优化效果：
#   - 原始输出可能20-50行，简洁模式3-5行
#   - 减少60-80% token消耗
#   - 提升响应速度（避免解析冗长输出）
# 
# 真实填充示例：
#   示例1 - WeCom状态检查：
#     BASE_COMMAND="openclaw status"
#     FILTER_PATTERN="-i wecom"
#     OUTPUT_LINES="5"
#   
#   示例2 - 系统错误日志：
#     BASE_COMMAND="openclaw logs --tail 100"
#     FILTER_PATTERN="ERROR\|WARN"
#     OUTPUT_LINES="10"
#   
#   示例3 - 配置查看：
#     BASE_COMMAND="jq '.channels' /root/.openclaw/openclaw.json"
#     FILTER_PATTERN=""
#     OUTPUT_LINES="20"
# ============================================================================

set -euo pipefail  # 严格模式：错误退出、未定义变量退出、管道错误检测

# ----------------------------------------------------------------------------
# 配置常量
# ----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_BASENAME="$(basename "$0" .sh)"
LOG_FILE="/var/log/openclaw-${SCRIPT_BASENAME}.log"

# ----------------------------------------------------------------------------
# 模板变量 - 根据实际需求替换
# ----------------------------------------------------------------------------
BASE_COMMAND="{{BASE_COMMAND}}"
FILTER_PATTERN="{{FILTER_PATTERN}}"
OUTPUT_LINES="{{OUTPUT_LINES:-3}}"
FALLBACK_COMMAND="{{FALLBACK_COMMAND:-}}"
TIMEOUT_SECONDS="{{TIMEOUT_SECONDS:-5}}"

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
# 参数解析
# ----------------------------------------------------------------------------
brief_mode=false
verbose_mode=false
help_mode=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --brief|-b)
            brief_mode=true
            shift
            ;;
        --verbose|-v)
            verbose_mode=true
            shift
            ;;
        --help|-h)
            help_mode=true
            shift
            ;;
        *)
            echo "未知参数: $1"
            exit 1
            ;;
    esac
done

# ----------------------------------------------------------------------------
# 帮助信息
# ----------------------------------------------------------------------------
show_help() {
    cat <<EOF
{{SCRIPT_DESCRIPTION}}

用法:
  $SCRIPT_BASENAME [选项]

选项:
  -b, --brief     简洁模式：只显示关键信息（${OUTPUT_LINES}行）
  -v, --verbose   详细模式：显示完整输出
  -h, --help      显示此帮助信息

默认模式：
  显示常规输出，包含必要但不冗余的信息

示例:
  $SCRIPT_BASENAME               # 常规模式
  $SCRIPT_BASENAME --brief       # 简洁模式（节省token）
  $SCRIPT_BASENAME --verbose     # 详细模式（调试用）

优化效果：
  - 简洁模式减少60-80%输出
  - 提升响应速度
  - 降低token消耗
EOF
    exit 0
}

# ----------------------------------------------------------------------------
# 核心函数
# ----------------------------------------------------------------------------

# 执行命令（带超时）
execute_command() {
    local cmd="$1"
    local timeout_sec="${2:-$TIMEOUT_SECONDS}"
    
    log_info "执行命令: $cmd"
    
    if [ "$timeout_sec" -gt 0 ]; then
        timeout "$timeout_sec" bash -c "$cmd" 2>/dev/null
    else
        bash -c "$cmd" 2>/dev/null
    fi
}

# 完整模式：显示原始输出
full_mode() {
    log_info "=== 开始检查 ==="
    
    if [ -n "$FALLBACK_COMMAND" ]; then
        # 尝试主命令，失败则使用备用命令
        output=$(execute_command "$BASE_COMMAND")
        if [ $? -ne 0 ] || [ -z "$output" ]; then
            log_warning "主命令失败，尝试备用命令"
            output=$(execute_command "$FALLBACK_COMMAND")
        fi
    else
        output=$(execute_command "$BASE_COMMAND")
    fi
    
    if [ -z "$output" ]; then
        log_error "命令无输出"
        exit 1
    fi
    
    echo "$output"
    log_success "检查完成"
}

# 简洁模式：只显示关键信息
brief_mode_func() {
    log_info "=== 简洁模式检查 ==="
    
    if [ -n "$FALLBACK_COMMAND" ]; then
        output=$(execute_command "$BASE_COMMAND")
        if [ $? -ne 0 ] || [ -z "$output" ]; then
            output=$(execute_command "$FALLBACK_COMMAND")
        fi
    else
        output=$(execute_command "$BASE_COMMAND")
    fi
    
    if [ -z "$output" ]; then
        echo "✗ 无输出"
        exit 1
    fi
    
    # 应用过滤
    if [ -n "$FILTER_PATTERN" ]; then
        filtered_output=$(echo "$output" | grep -E "$FILTER_PATTERN" | head -n "$OUTPUT_LINES")
    else
        filtered_output=$(echo "$output" | head -n "$OUTPUT_LINES")
    fi
    
    if [ -z "$filtered_output" ]; then
        # 无匹配，显示摘要
        line_count=$(echo "$output" | wc -l)
        word_count=$(echo "$output" | wc -w)
        echo "✓ 检查完成（${line_count}行，${word_count}词）"
        echo "ℹ️  无匹配项，使用完整模式查看详情"
    else
        echo "$filtered_output"
        
        # 显示统计信息
        total_lines=$(echo "$output" | wc -l)
        filtered_lines=$(echo "$filtered_output" | wc -l)
        reduction=$((100 - (filtered_lines * 100 / total_lines)))
        
        if [ "$reduction" -gt 50 ]; then
            echo "✅ 输出精简完成（减少${reduction}%，${filtered_lines}/${total_lines}行）"
        else
            echo "ℹ️  输出精简（减少${reduction}%，${filtered_lines}/${total_lines}行）"
        fi
    fi
    
    log_success "简洁检查完成 $(date '+%H:%M:%S')"
}

# 详细模式：调试用
verbose_mode_func() {
    log_info "=== 详细模式检查 ==="
    echo "配置信息:"
    echo "  - 基础命令: $BASE_COMMAND"
    echo "  - 过滤模式: $FILTER_PATTERN"
    echo "  - 输出行数: $OUTPUT_LINES"
    echo "  - 备用命令: ${FALLBACK_COMMAND:-无}"
    echo "  - 超时时间: ${TIMEOUT_SECONDS}秒"
    echo ""
    
    full_mode
}

# ----------------------------------------------------------------------------
# 主函数
# ----------------------------------------------------------------------------
main() {
    if [ "$help_mode" = true ]; then
        show_help
    fi
    
    if [ "$verbose_mode" = true ]; then
        verbose_mode_func
    elif [ "$brief_mode" = true ]; then
        brief_mode_func
    else
        full_mode
    fi
}

# ----------------------------------------------------------------------------
# 错误处理
# ----------------------------------------------------------------------------
handle_error() {
    log_error "脚本执行失败: $?"
    exit 1
}

trap handle_error ERR

# ----------------------------------------------------------------------------
# 执行入口
# ----------------------------------------------------------------------------
main "$@"
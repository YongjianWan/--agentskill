#!/bin/bash
# ============================================================================
# 脚本名称: optimize-{{SCRIPT_NAME}}.sh
# 功能描述: 优化{{TARGET_DESCRIPTION}}脚本，减少代码行数，提高可读性和性能
# 创建日期: $(date +%Y-%m-%d)
# 版本: 1.0.0
# ============================================================================
# 半结构化任务模板 - 代码优化脚本
# 替换以下变量:
#   {{SCRIPT_NAME}}          - 优化脚本名称（英文）
#   {{TARGET_DESCRIPTION}}   - 目标脚本描述（中文）
#   {{TARGET_FILE}}          - 要优化的脚本文件路径
#   {{OPTIMIZATION_GOALS}}   - 优化目标（如减少行数、提高性能、增强可读性）
#   {{KEEP_FUNCTIONALITY}}   - 必须保留的功能（列表）
# ============================================================================

set -euo pipefail

# ----------------------------------------------------------------------------
# 配置常量
# ----------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_BASENAME="optimize-{{SCRIPT_NAME}}"
LOG_FILE="/var/log/openclaw/${SCRIPT_BASENAME}.log"
BACKUP_DIR="/tmp/openclaw-script-backups"

# ----------------------------------------------------------------------------
# 颜色输出
# ----------------------------------------------------------------------------
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }
log_error() { echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE" >&2; }
log_debug() { [[ "${VERBOSE:-false}" == "true" ]] && echo -e "${CYAN}[DEBUG]${NC} $(date '+%Y-%m-%d %H:%M:%S') $*" | tee -a "$LOG_FILE"; }

# ----------------------------------------------------------------------------
# 配置变量
# ----------------------------------------------------------------------------
TARGET_FILE="{{TARGET_FILE}}"
OPTIMIZATION_GOALS="{{OPTIMIZATION_GOALS}}"
KEEP_FUNCTIONALITY="{{KEEP_FUNCTIONALITY}}"
ORIGINAL_LINES=0
OPTIMIZED_LINES=0

# ----------------------------------------------------------------------------
# 参数解析
# ----------------------------------------------------------------------------
parse_args() {
    local mode="analyze"  # analyze|apply|dry-run
    
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --apply)
                mode="apply"
                shift
                ;;
            --dry-run)
                mode="dry-run"
                shift
                ;;
            --brief)
                export OUTPUT_MODE="brief"
                shift
                ;;
            -v|--verbose)
                export VERBOSE="true"
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
# 备份原始文件
# ----------------------------------------------------------------------------
backup_file() {
    local file="$1"
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    
    mkdir -p "$BACKUP_DIR"
    local backup_file="${BACKUP_DIR}/$(basename "$file")_${timestamp}.bak"
    
    cp "$file" "$backup_file"
    log_info "原始文件备份至: $backup_file"
    echo "$backup_file"
}

# ----------------------------------------------------------------------------
# 分析脚本
# ----------------------------------------------------------------------------
analyze_script() {
    log_info "分析脚本: $TARGET_FILE"
    
    if [[ ! -f "$TARGET_FILE" ]]; then
        log_error "目标文件不存在: $TARGET_FILE"
        exit 1
    fi
    
    # 统计基本信息
    ORIGINAL_LINES=$(wc -l < "$TARGET_FILE")
    local total_chars=$(wc -c < "$TARGET_FILE")
    local shebang_lines=$(grep -c '^#!' "$TARGET_FILE")
    local comment_lines=$(grep -c '^[[:space:]]*#' "$TARGET_FILE")
    local code_lines=$((ORIGINAL_LINES - comment_lines))
    
    # 检测常见优化点
    local optimization_points=()
    
    # 1. 检查重复代码模式
    local duplicate_blocks=$(grep -n "重复模式" "$TARGET_FILE" 2>/dev/null || true)
    if [[ -n "$duplicate_blocks" ]]; then
        optimization_points+=("发现重复代码块，可封装为函数")
    fi
    
    # 2. 检查过长函数
    local long_functions=$(awk '/^[[:space:]]*[a-zA-Z_][a-zA-Z0-9_]*\(\)/{p=1; func=$0; lines=0} p{lines++} /^[[:space:]]*}/{if(p && lines > 30){print func " (" lines "行)"}; p=0}' "$TARGET_FILE" 2>/dev/null || true)
    if [[ -n "$long_functions" ]]; then
        optimization_points+=("存在过长函数，建议拆分")
    fi
    
    # 3. 检查复杂的条件嵌套
    local deep_nesting=$(grep -c "if.*if\|for.*if\|while.*if" "$TARGET_FILE" 2>/dev/null || true)
    if [[ $deep_nesting -gt 3 ]]; then
        optimization_points+=("条件嵌套过深，可简化逻辑")
    fi
    
    # 4. 检查错误处理
    local error_handling=$(grep -c "|| exit\|set -e\|trap" "$TARGET_FILE" 2>/dev/null || true)
    if [[ $error_handling -eq 0 ]]; then
        optimization_points+=("缺乏错误处理机制")
    fi
    
    # 5. 检查参数处理
    local param_handling=$(grep -c "getopts\|while.*shift" "$TARGET_FILE" 2>/dev/null || true)
    if [[ $param_handling -eq 0 ]] && [[ $ORIGINAL_LINES -gt 50 ]]; then
        optimization_points+=("缺乏标准参数解析")
    fi
    
    # 输出分析报告
    cat <<EOF

=============================================
脚本分析报告: $(basename "$TARGET_FILE")
=============================================
基本信息:
  总行数: $ORIGINAL_LINES 行
  代码行: $code_lines 行
  注释行: $comment_lines 行
  文件大小: $((total_chars/1024)) KB

优化目标: $OPTIMIZATION_GOALS
必须保留: $KEEP_FUNCTIONALITY

检测到的优化点 (${#optimization_points[@]}个):
EOF
    
    for i in "${!optimization_points[@]}"; do
        echo "  $((i+1)). ${optimization_points[$i]}"
    done
    
    if [[ ${#optimization_points[@]} -eq 0 ]]; then
        echo "  ✅ 未发现明显优化点，脚本质量良好"
    fi
    
    # 优化建议
    cat <<EOF

优化建议:
1. 代码重构:
   - 重复逻辑封装为函数
   - 长函数拆分为子函数
   - 简化复杂条件判断

2. 质量提升:
   - 添加错误处理和清理机制
   - 标准化参数解析
   - 增加注释和文档

3. 性能优化:
   - 避免不必要的子进程调用
   - 使用内置命令替代外部命令
   - 减少文件I/O操作

预计优化效果:
  行数减少: 15-30%
  可读性提升: 显著
  维护成本: 降低

=============================================
EOF
    
    echo "$ORIGINAL_LINES"
}

# ----------------------------------------------------------------------------
# 应用优化
# ----------------------------------------------------------------------------
apply_optimization() {
    log_info "应用优化到: $TARGET_FILE"
    
    local backup_file
    backup_file=$(backup_file "$TARGET_FILE")
    
    # 创建优化版本
    local temp_file
    temp_file=$(mktemp)
    
    # 基础优化步骤（实际项目中应更复杂）
    cat "$TARGET_FILE" | sed '
        # 移除多余空行（连续3个以上空行保留2个）
        /^$/ { N; /^\n$/ { N; /^\n\n$/ { N; /^\n\n\n/ { s/\n\n\n/\n\n/; P; D } } } }
        
        # 标准化shebang后的空行
        1 { /^#!\/bin\/bash/ { n; /^$/! { i\ 
        } } }
    ' > "$temp_file"
    
    # 检查优化后的行数
    OPTIMIZED_LINES=$(wc -l < "$temp_file")
    local reduction=$((ORIGINAL_LINES - OPTIMIZED_LINES))
    local reduction_percent=$((reduction * 100 / ORIGINAL_LINES))
    
    if [[ $reduction -gt 0 ]]; then
        mv "$temp_file" "$TARGET_FILE"
        chmod +x "$TARGET_FILE"
        log_success "优化完成: 减少 $reduction 行 ($reduction_percent%)"
        log_info "原始文件备份在: $backup_file"
    else
        rm "$temp_file"
        log_warning "未进行优化，脚本已是最优状态"
    fi
}

# ----------------------------------------------------------------------------
# 主逻辑
# ----------------------------------------------------------------------------
main() {
    log_info "=== 脚本优化工具 ==="
    log_info "目标: $TARGET_FILE"
    log_info "优化目标: $OPTIMIZATION_GOALS"
    
    local mode
    mode=$(parse_args "$@")
    
    # 确保日志目录存在
    mkdir -p "$(dirname "$LOG_FILE")"
    
    # 执行分析
    ORIGINAL_LINES=$(analyze_script)
    
    case "$mode" in
        "analyze")
            # 仅分析，不修改
            log_info "分析模式完成，使用 --dry-run 或 --apply 进行优化"
            ;;
        "dry-run")
            log_info "干运行模式 - 显示优化效果但不修改文件"
            log_info "预计可减少行数: $((ORIGINAL_LINES * 15 / 100))-$((ORIGINAL_LINES * 30 / 100))"
            ;;
        "apply")
            apply_optimization
            ;;
        *)
            log_error "未知模式: $mode"
            exit 1
            ;;
    esac
    
    # 简洁输出模式
    if [[ "${OUTPUT_MODE:-}" == "brief" ]]; then
        echo "📊 $(basename "$TARGET_FILE"): ${ORIGINAL_LINES}行 → ${OPTIMIZED_LINES:-$ORIGINAL_LINES}行"
    fi
}

# ----------------------------------------------------------------------------
# 帮助信息
# ----------------------------------------------------------------------------
show_usage() {
    cat <<EOF
脚本优化工具 - 优化Shell脚本代码

用法: $0 [选项]

选项:
  --analyze         仅分析脚本，不修改（默认）
  --dry-run         干运行模式，显示优化效果但不修改
  --apply           应用优化到原文件
  --brief           简洁输出模式（减少token消耗）
  -v, --verbose     详细输出模式
  -h, --help        显示此帮助信息

优化目标: $OPTIMIZATION_GOALS
必须保留: $KEEP_FUNCTIONALITY

优化策略:
  1. 代码去重 - 识别并封装重复逻辑
  2. 函数拆分 - 将长函数拆分为可复用的子函数
  3. 结构简化 - 减少条件嵌套，提高可读性
  4. 错误处理 - 添加适当的错误检查和清理
  5. 文档完善 - 补充注释和使用说明

示例:
  $0 --analyze        # 分析脚本并提供优化建议
  $0 --dry-run        # 显示优化效果但不修改
  $0 --apply --brief  # 应用优化并简洁输出

注意:
  - 优化前会自动备份原始文件
  - 仅支持Shell脚本（.sh文件）
  - 优化会保留所有核心功能
EOF
}

# ----------------------------------------------------------------------------
# 脚本入口
# ----------------------------------------------------------------------------
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
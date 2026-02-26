#!/bin/bash
# 技能进化优化器 - 基于分析结果生成改进方案
# 三层架构：检测(analyzer) → 优化(evolver) → 验证(validator)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_DIR="/root/.openclaw/workspace"
SCRIPTS_DIR="$WORKSPACE_DIR/scripts"
REGISTRY_FILE="$SCRIPTS_DIR/registry.json"
EVOLUTION_DIR="$WORKSPACE_DIR/skills/skill-evolution"
REPORTS_DIR="$WORKSPACE_DIR/active/evolution-reports"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[skill-evolver]${NC} $*" >&2; }
success() { echo -e "${GREEN}[skill-evolver]${NC} $*" >&2; }
warn() { echo -e "${YELLOW}[skill-evolver]${NC} $*" >&2; }
error() { echo -e "${RED}[skill-evolver]${NC} $*" >&2; }

# 显示帮助
show_help() {
    cat <<EOF
技能进化优化器 - 基于分析结果生成改进方案

用法: $0 [选项]

选项:
  --dry-run      只显示改进建议，不实际修改（默认）
  --apply        应用改进（需要确认）
  --help         显示此帮助信息
  --brief        简洁输出模式

功能:
  1. 读取 registry.json，分析脚本状态
  2. 识别需要优化的脚本（缺少 --brief 支持等）
  3. 生成改进方案
  4. 可选：应用改进

三层进化架构:
  🔍 evolution-analyzer.py - 检测问题
  🔧 skill-evolver.sh     - 生成并应用改进
  ✅ evolution-validator.py - 验证兼容性

EOF
}

# 检查依赖
check_dependencies() {
    if [ ! -f "$REGISTRY_FILE" ]; then
        error "registry.json 不存在: $REGISTRY_FILE"
        return 1
    fi
    
    if [ ! -d "$SCRIPTS_DIR" ]; then
        error "scripts 目录不存在: $SCRIPTS_DIR"
        return 1
    fi
    
    # 检查 jq 是否可用（用于 JSON 解析）
    if ! command -v jq &> /dev/null; then
        warn "jq 未安装，使用简单的 grep 解析"
    fi
    
    return 0
}

# 分析脚本状态
analyze_scripts() {
    log "分析脚本状态..."
    
    local total_scripts=0
    local with_brief=0
    local without_brief=()
    
    # 使用 jq 解析（如果可用）
    if command -v jq &> /dev/null; then
        total_scripts=$(jq '.scripts | length' "$REGISTRY_FILE")
        
        # 提取需要优化的脚本
        without_brief=($(jq -r '.scripts[] | select(.briefMode != true) | .name' "$REGISTRY_FILE"))
        with_brief=$((total_scripts - ${#without_brief[@]}))
    else
        # 简单的 grep 解析
        total_scripts=$(grep -c '"name"' "$REGISTRY_FILE" || echo "0")
        
        # 粗略估计：查找没有 "briefMode": true 的脚本
        # 这里简化处理，实际可能需要更复杂的解析
        warn "使用简单解析，结果可能不准确"
        without_brief=("placeholder1" "placeholder2")  # 占位符
        with_brief=$((total_scripts - ${#without_brief[@]}))
    fi
    
    echo "total_scripts:$total_scripts"
    echo "with_brief:$with_brief"
    echo "without_brief:${without_brief[*]}"
}

# 为脚本生成改进建议
generate_improvement_for_script() {
    local script_name="$1"
    local script_path="$SCRIPTS_DIR/$script_name"
    
    log "为 $script_name 生成改进建议..."
    
    # 检查脚本是否存在
    if [ ! -f "$script_path" ]; then
        warn "脚本不存在: $script_path"
        return 1
    fi
    
    # 检查是否已经有 --brief 支持
    if grep -q "brief" "$script_path" && grep -q "\-\-brief" "$script_path"; then
        echo "✅ $script_name 已支持 --brief"
        return 0
    fi
    
    # 生成改进建议
    cat <<EOF

📋 脚本: $script_name
🔧 改进: 添加 --brief 支持
📝 建议修改:

1. 在参数解析部分添加:
   brief=false
   while [[ \$# -gt 0 ]]; do
     case \$1 in
       --brief) brief=true; shift ;;
       *) break ;;
     esac
   done

2. 在输出部分根据 brief 变量调整:
   if [ "\$brief" = true ]; then
     echo "✅ 简洁输出"
   else
     echo "详细输出..."
   fi

3. 更新 registry.json 中的 briefMode 为 true

EOF
    
    # 标记为需要改进
    return 2
}

# 生成改进报告
generate_improvement_report() {
    local analysis_output="$1"
    
    # 解析分析结果
    local total_scripts=$(echo "$analysis_output" | grep "total_scripts:" | cut -d: -f2)
    local with_brief=$(echo "$analysis_output" | grep "with_brief:" | cut -d: -f2)
    local without_brief_str=$(echo "$analysis_output" | grep "without_brief:" | cut -d: -f2)
    
    local without_brief=()
    IFS=' ' read -ra without_brief <<< "$without_brief_str"
    
    log "生成改进报告..."
    
    # 创建报告目录
    mkdir -p "$REPORTS_DIR"
    local report_file="$REPORTS_DIR/improvement-$(date '+%Y%m%d-%H%M%S').md"
    
    cat > "$report_file" <<EOF
# 技能进化改进报告

**生成时间**: $(date '+%Y-%m-%d %H:%M:%S')
**分析结果**: $with_brief/$total_scripts 个脚本已优化

## 📊 概览

| 指标 | 数值 |
|------|------|
| 脚本总数 | $total_scripts |
| 已优化脚本 | $with_brief |
| 需改进脚本 | ${#without_brief[@]} |
| 优化率 | $(awk "BEGIN {printf \"%.1f%%\", $with_brief/$total_scripts*100}") |

## 🔧 待改进脚本

EOF
    
    local improvement_count=0
    
    for script_name in "${without_brief[@]}"; do
        if [ -n "$script_name" ] && [ "$script_name" != "placeholder"* ]; then
            echo "### $script_name" >> "$report_file"
            echo "" >> "$report_file"
            
            # 生成具体改进建议
            local suggestion=$(generate_improvement_for_script "$script_name" 2>&1 | tail -20)
            echo "$suggestion" >> "$report_file"
            echo "" >> "$report_file"
            
            improvement_count=$((improvement_count + 1))
        fi
    done
    
    # 添加总结
    cat >> "$report_file" <<EOF

## 🎯 执行建议

### 立即执行（高价值）
1. **添加 --brief 支持**到上述 ${#without_brief[@]} 个脚本
2. **更新 registry.json** 中的 briefMode 字段
3. **运行验证器**: evolution-validator.py --brief

### 长期改进
1. **添加使用统计**：记录脚本调用次数、成功率
2. **实现 Token 节省率**计算
3. **建立自动进化触发器**：每周自动运行进化流程

### 半自动辅助原则
- 分析而非强制：提供建议，由用户确认执行
- 务实优先：只解决实际问题，不追求理论完美
- 用户中心：最终决策权在用户，系统是辅助工具

## 📁 相关文件

- **分析器**: $EVOLUTION_DIR/scripts/evolution-analyzer.py
- **验证器**: $EVOLUTION_DIR/scripts/evolution-validator.py
- **注册表**: $REGISTRY_FILE
- **报告目录**: $REPORTS_DIR

---
*由 skill-evolver.sh 自动生成*
EOF
    
    echo "report_file:$report_file"
    echo "improvement_count:$improvement_count"
}

# 应用改进（需要确认）
apply_improvements() {
    local report_file="$1"
    
    log "准备应用改进..."
    warn "⚠️  注意：此操作将修改脚本文件"
    echo "查看改进报告: $report_file"
    
    # 这里简化实现，实际应该解析报告并应用修改
    # 由于安全考虑，当前版本只生成建议，不自动修改
    
    cat <<EOF

🔒 安全限制：当前版本不自动修改脚本

手动应用步骤：
1. 查看报告: cat "$report_file"
2. 手动编辑需要改进的脚本
3. 更新 registry.json 中的 briefMode 字段
4. 运行验证器: evolution-validator.py

原因：
- 脚本修改需要谨慎，避免破坏现有功能
- 不同脚本结构不同，需要人工判断
- 保持用户最终决策权

EOF
}

# 主函数
main() {
    local dry_run=true
    local apply=false
    local brief=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run) dry_run=true; shift ;;
            --apply) apply=true; dry_run=false; shift ;;
            --brief) brief=true; shift ;;
            --help) show_help; exit 0 ;;
            *) error "未知参数: $1"; show_help; exit 1 ;;
        esac
    done
    
    # 检查依赖
    if ! check_dependencies; then
        error "依赖检查失败"
        exit 1
    fi
    
    log "开始技能进化优化..."
    log "模式: $([ "$dry_run" = true ] && echo "干跑（只生成建议）" || echo "应用改进")"
    
    # 分析脚本状态
    local analysis_output=$(analyze_scripts)
    
    if [ "$brief" = true ]; then
        local total_scripts=$(echo "$analysis_output" | grep "total_scripts:" | cut -d: -f2)
        local with_brief=$(echo "$analysis_output" | grep "with_brief:" | cut -d: -f2)
        local without_brief_count=$(echo "$analysis_output" | grep "without_brief:" | cut -d: -f2 | wc -w)
        
        if [ "$without_brief_count" -eq 0 ]; then
            echo "✅ evolution-ready: $with_brief/$total_scripts scripts optimized"
        else
            echo "⚠️ evolution-needed: $without_brief_count scripts need --brief support"
        fi
        exit 0
    fi
    
    # 生成改进报告
    local report_info=$(generate_improvement_report "$analysis_output")
    local report_file=$(echo "$report_info" | grep "report_file:" | cut -d: -f2)
    local improvement_count=$(echo "$report_info" | grep "improvement_count:" | cut -d: -f2)
    
    # 输出结果
    if [ "$improvement_count" -gt 0 ]; then
        success "生成改进报告: $report_file"
        success "发现 $improvement_count 个脚本需要改进"
        
        # 显示报告摘要
        echo ""
        echo "=== 改进报告摘要 ==="
        head -30 "$report_file"
        echo "..."
        echo "完整报告: $report_file"
        
        # 如果指定了 --apply，尝试应用改进
        if [ "$apply" = true ]; then
            apply_improvements "$report_file"
        else
            echo ""
            echo "💡 提示: 使用 --apply 参数应用改进（需谨慎）"
            echo "      或手动查看报告并实施建议"
        fi
    else
        success "🎉 所有脚本均已优化！"
        echo "✅ 无需改进"
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
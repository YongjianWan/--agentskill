#!/bin/bash

# Integrated Skill Manager - Called from skill-manager skill
# Provides unified interface for all skill management operations

set -e

SKILLS_DIR="/root/.openclaw/workspace/skills"
SCRIPTS_DIR="/root/.openclaw/workspace/scripts"
ACTION="$1"
ARG1="$2"
ARG2="$3"

# 颜色定义（终端输出用）
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# JSON输出（给skill用）
json_output() {
    local status="$1"
    local message="$2"
    local data="$3"
    
    if [ -z "$data" ]; then
        echo "{\"status\":\"$status\",\"message\":\"$message\"}"
    else
        echo "{\"status\":\"$status\",\"message\":\"$message\",\"data\":$data}"
    fi
}

# 列出技能
list_skills() {
    local filter="$1"
    
    skills_json="["
    first=true
    
    for skill_dir in "$SKILLS_DIR"/*/; do
        skill_name=$(basename "$skill_dir")
        
        # 跳过禁用技能（除非特别要求）
        if [[ "$skill_name" == _* ]] && [ "$filter" != "all" ]; then
            continue
        fi
        
        skill_file="$skill_dir/SKILL.md"
        
        if [ -f "$skill_file" ]; then
            # 提取信息
            description=$(grep -i "description:" "$skill_file" | head -1 | cut -d: -f2- | sed 's/^ *//;s/ *$//')
            if [ -z "$description" ]; then
                description=$(head -5 "$skill_file" | grep -v "^---" | head -1 | sed 's/^ *//;s/ *$//')
            fi
            
            enabled="true"
            if [[ "$skill_name" == _* ]]; then
                enabled="false"
                skill_name="${skill_name:1}"  # 去掉下划线
            fi
            
            size=$(du -sh "$skill_dir" 2>/dev/null | cut -f1)
            lines=$(wc -l < "$skill_file" 2>/dev/null || echo "0")
            
            if [ "$first" = true ]; then
                first=false
            else
                skills_json="$skills_json,"
            fi
            
            skills_json="$skills_json{\"name\":\"$skill_name\",\"enabled\":$enabled,\"description\":\"$description\",\"size\":\"$size\",\"lines\":$lines}"
        fi
    done
    
    skills_json="$skills_json]"
    json_output "success" "Skills listed" "$skills_json"
}

# 搜索技能
search_skills() {
    local query="$1"
    
    if [ -z "$query" ]; then
        json_output "error" "Search query required"
        return 1
    fi
    
    results_json="["
    first=true
    
    for skill_dir in "$SKILLS_DIR"/*/; do
        skill_name=$(basename "$skill_dir")
        skill_file="$skill_dir/SKILL.md"
        
        if [ -f "$skill_file" ] && grep -i "$query" "$skill_file" >/dev/null; then
            # 提取匹配行
            matches=$(grep -i "$query" "$skill_file" | head -2 | sed 's/"/\\"/g' | tr '\n' ';')
            
            enabled="true"
            if [[ "$skill_name" == _* ]]; then
                enabled="false"
                skill_name="${skill_name:1}"
            fi
            
            if [ "$first" = true ]; then
                first=false
            else
                results_json="$results_json,"
            fi
            
            results_json="$results_json{\"name\":\"$skill_name\",\"enabled\":$enabled,\"matches\":\"$matches\"}"
        fi
    done
    
    results_json="$results_json]"
    
    if [ "$first" = true ]; then
        json_output "info" "No skills found matching '$query'"
    else
        json_output "success" "Search results for '$query'" "$results_json"
    fi
}

# 启用/禁用技能
toggle_skill() {
    local skill_name="$1"
    local action="$2"  # enable or disable
    
    if [ -z "$skill_name" ]; then
        json_output "error" "Skill name required"
        return 1
    fi
    
    if [ "$action" = "enable" ]; then
        if [ -d "$SKILLS_DIR/_$skill_name" ]; then
            mv "$SKILLS_DIR/_$skill_name" "$SKILLS_DIR/$skill_name"
            json_output "success" "Skill '$skill_name' enabled"
        elif [ -d "$SKILLS_DIR/$skill_name" ]; then
            json_output "info" "Skill '$skill_name' is already enabled"
        else
            json_output "error" "Skill '$skill_name' not found"
        fi
    elif [ "$action" = "disable" ]; then
        if [ -d "$SKILLS_DIR/$skill_name" ]; then
            mv "$SKILLS_DIR/$skill_name" "$SKILLS_DIR/_$skill_name"
            json_output "success" "Skill '$skill_name' disabled"
        elif [ -d "$SKILLS_DIR/_$skill_name" ]; then
            json_output "info" "Skill '$skill_name' is already disabled"
        else
            json_output "error" "Skill '$skill_name' not found"
        fi
    else
        json_output "error" "Invalid action: $action (use enable or disable)"
    fi
}

# 获取技能信息
skill_info() {
    local skill_name="$1"
    
    if [ -z "$skill_name" ]; then
        json_output "error" "Skill name required"
        return 1
    fi
    
    # 检查启用和禁用版本
    if [ -d "$SKILLS_DIR/$skill_name" ]; then
        skill_dir="$SKILLS_DIR/$skill_name"
        enabled="true"
    elif [ -d "$SKILLS_DIR/_$skill_name" ]; then
        skill_dir="$SKILLS_DIR/_$skill_name"
        enabled="false"
    else
        json_output "error" "Skill '$skill_name' not found"
        return 1
    fi
    
    skill_file="$skill_dir/SKILL.md"
    
    if [ ! -f "$skill_file" ]; then
        json_output "error" "SKILL.md file not found for '$skill_name'"
        return 1
    fi
    
    # 提取元数据
    metadata="{}"
    while read -r line; do
        if [[ "$line" =~ ^[a-zA-Z-]+: ]]; then
            key=$(echo "$line" | cut -d: -f1)
            value=$(echo "$line" | cut -d: -f2- | sed 's/^ *//;s/ *$//')
            metadata=$(echo "$metadata" | jq --arg k "$key" --arg v "$value" '. + {($k): $v}')
        fi
    done < <(grep -E "^(name|description|source|license|trigger):" "$skill_file")
    
    # 文件信息
    size=$(du -sh "$skill_dir" 2>/dev/null | cut -f1)
    lines=$(wc -l < "$skill_file")
    modified=$(stat -c %y "$skill_file" 2>/dev/null | cut -d. -f1)
    
    info_json="{\"name\":\"$skill_name\",\"enabled\":$enabled,\"metadata\":$metadata,\"size\":\"$size\",\"lines\":$lines,\"modified\":\"$modified\"}"
    
    json_output "success" "Skill information for '$skill_name'" "$info_json"
}

# 统计分析
skill_stats() {
    total=$(ls -d "$SKILLS_DIR"/*/ 2>/dev/null | wc -l)
    enabled=$(ls -d "$SKILLS_DIR"/[^_]*/ 2>/dev/null | wc -l)
    disabled=$(ls -d "$SKILLS_DIR"/_*/ 2>/dev/null | wc -l)
    
    # 大小统计
    size_info=""
    if [ $total -gt 0 ]; then
        total_size=$(du -sh "$SKILLS_DIR" 2>/dev/null | cut -f1)
        
        # 最大的5个技能
        largest=$(du -sh "$SKILLS_DIR"/*/ 2>/dev/null | sort -hr | head -5 | while read size name; do
            echo "$(basename "$name"):$size"
        done | tr '\n' ';')
    fi
    
    stats_json="{\"total\":$total,\"enabled\":$enabled,\"disabled\":$disabled,\"total_size\":\"$total_size\",\"largest\":\"$largest\"}"
    
    json_output "success" "Skill statistics" "$stats_json"
}

# 运行外部脚本（兼容现有系统）
run_external() {
    local script="$1"
    local args="$2"
    
    if [ ! -f "$SCRIPTS_DIR/$script" ]; then
        json_output "error" "Script '$script' not found"
        return 1
    fi
    
    # 运行脚本并捕获输出
    output=$(cd /root/.openclaw/workspace && "$SCRIPTS_DIR/$script" $args 2>&1)
    
    json_output "success" "Script executed" "{\"script\":\"$script\",\"output\":\"$output\"}"
}

# 主逻辑
case "$ACTION" in
    list)
        list_skills "$ARG1"
        ;;
    search)
        search_skills "$ARG1"
        ;;
    enable)
        toggle_skill "$ARG1" "enable"
        ;;
    disable)
        toggle_skill "$ARG1" "disable"
        ;;
    info)
        skill_info "$ARG1"
        ;;
    stats)
        skill_stats
        ;;
    run)
        run_external "$ARG1" "$ARG2"
        ;;
    help)
        json_output "info" "Available commands: list [all], search <query>, enable <skill>, disable <skill>, info <skill>, stats, run <script> [args]"
        ;;
    *)
        json_output "error" "Unknown command: $ACTION. Use 'help' for available commands."
        ;;
esac
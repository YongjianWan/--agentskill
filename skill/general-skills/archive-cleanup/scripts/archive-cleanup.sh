#!/bin/bash
# 归档清理脚本
# 功能：将 active/daily/ 超过7天的文件归档到 archive/YYYY-MM/

cd /root/.openclaw/workspace

DAILY_DIR="active/daily"
ARCHIVE_DIR="archive"

# 查找超过7天的文件
find "$DAILY_DIR" -name "*.md" -type f -mtime +7 | while read file; do
    filename=$(basename "$file")
    # 从文件名提取日期
    if [[ $filename =~ ^([0-9]{4})-([0-9]{2}) ]]; then
        year=${BASH_REMATCH[1]}
        month=${BASH_REMATCH[2]}
        target_dir="$ARCHIVE_DIR/$year-$month"
        
        mkdir -p "$target_dir"
        mv "$file" "$target_dir/"
        echo "[归档] $filename → $target_dir/"
    fi
done

echo "$(date): archive-cleanup 完成"

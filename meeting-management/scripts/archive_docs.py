#!/usr/bin/env python3
"""归档文档脚本"""
import os
import shutil

def main():
    # 创建归档目录
    archive_dir = os.path.join('archive', 'docs', '2026-02-27')
    os.makedirs(archive_dir, exist_ok=True)
    print(f"归档目录: {archive_dir}")
    
    # 要移动的文件列表
    files_to_archive = [
        'FRONTEND_QUICKSTART.md',
        'UPDATE_SUMMARY_20260227.md',
        'SESSION_ARCHIVE.md',
    ]
    
    # 查找中文文件
    docs_files = os.listdir('docs')
    for f in docs_files:
        if f.endswith('.md'):
            try:
                f.encode('ascii')
            except UnicodeEncodeError:
                # 包含非ASCII字符（中文文件名）
                files_to_archive.append(f)
    
    print(f"\n将归档 {len(files_to_archive)} 个文件:")
    moved_count = 0
    
    for f in files_to_archive:
        src = os.path.join('docs', f)
        dst = os.path.join(archive_dir, f)
        
        if os.path.exists(src):
            shutil.move(src, dst)
            print(f"  [OK] {f}")
            moved_count += 1
        else:
            print(f"  [SKIP] {f} (不存在)")
    
    print(f"\n成功归档: {moved_count}/{len(files_to_archive)}")
    
    # 列出归档内容
    archived = os.listdir(archive_dir)
    print(f"\n归档目录内容 ({len(archived)} 个文件):")
    for f in archived:
        size = os.path.getsize(os.path.join(archive_dir, f))
        print(f"  - {f} ({size} bytes)")
    
    # 创建归档说明
    readme_path = os.path.join(archive_dir, 'README.md')
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write("""# 文档归档说明

**归档日期**: 2026-02-27

## 归档原因

本次归档是文档膨胀整理的第一步，将重复或不再活跃的文档移出活跃目录。

## 归档文件清单

| 文件名 | 归档原因 | 替代文档 |
|--------|----------|----------|
| FRONTEND_QUICKSTART.md | 与FRONTEND_CONTRACT.md重复 | 使用FRONTEND_CONTRACT.md |
| UPDATE_SUMMARY_20260227.md | 内容已合并至CHANGELOG.md | 查看CHANGELOG.md |
| SESSION_ARCHIVE.md | 历史归档副本，非当前活跃 | 查看SESSION_STATE.yaml |
| 业务流程.md (中文) | 中文命名不规范 | 重命名为BUSINESS_FLOW.md保留在docs/ |
| 测试清单.md (中文) | 中文命名不规范 | 重命名为TEST_CHECKLIST.md保留在docs/ |
| 未来方向.md (中文) | 内容价值低 | 删除或参考INTEGRATION_PLAN.md |

## 恢复说明

如需恢复某个文档，从此目录复制回docs/即可。
""")
    print(f"\n创建归档说明: {readme_path}")

if __name__ == '__main__':
    main()

#!/bin/bash
# Token 压缩功能测试脚本

echo "=== Token Optimizer Test ==="
echo ""

# 测试1: 直接测试压缩模块
echo "Test 1: Compressor module"
cd /root/.openclaw/workspace/skills/kimi-bridge
python3 src/compressor.py
echo ""

# 测试2: 环境变量开关测试
echo "Test 2: Environment toggle"
TOKEN_OPT_ENABLED=false python3 -c "
from src.compressor import compress_tool_result
data = 'x' * 5000
compressed, stats = compress_tool_result(data, 'test')
print(f'Enabled=false: Compressed={stats is not None}')  # Should be False
"

TOKEN_OPT_ENABLED=true python3 -c "
from src.compressor import compress_tool_result
data = 'x' * 5000
compressed, stats = compress_tool_result(data, 'test')
print(f'Enabled=true: Compressed={stats is not None}')  # Should be True
if stats:
    print(f'  Saved: {stats.saved_percent:.1f}%')
"

echo ""
echo "=== Test Complete ==="

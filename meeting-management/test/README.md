# 测试目录结构

```
test/
├── README.md                 # 本文件
├── unit/                     # 单元测试
│   ├── test_1_6_transcript_update.py  # 转写片段更新单元测试
│   └── api_test_report.py             # API测试报告生成
├── integration/              # 集成测试
│   ├── test_create_meeting.py         # 创建会议API测试
│   ├── test_template_style.py         # 模板风格测试
│   ├── test_state_machine.py          # 状态机流转测试
│   └── test_list_1_4.py               # 会议列表查询测试
├── e2e/                      # 端到端测试
│   ├── test_regenerate.py             # 纪要重新生成E2E测试
│   ├── test_regenerate_final.py       # 纪要生成最终测试
│   └── test_websocket.py              # WebSocket E2E测试
├── bug_fixes/                # Bug修复验证测试
│   ├── test_b001_bug.py               # B-001 format校验测试
│   ├── test_b002_b003.py              # B-002/B-003 minutes字段测试
│   ├── verify_case3.py                # 转写更新用例3验证
│   └── verify_case3_v2.py             # 转写更新用例3验证v2
├── db_connection/            # 数据库连接测试
│   ├── check_db.py                    # 数据库协议检测
│   ├── test_hgdb.py                   # 瀚高数据库连接测试
│   └── check_meeting.py               # 会议数据检查
└── real/                     # 真实环境测试
    ├── index.html                     # 浏览器测试页面
    └── README.md                      # 使用说明
```

## 测试分类说明

### 单元测试 (unit/)
测试单个函数/模块，不依赖外部服务。

### 集成测试 (integration/)
测试多个模块协作，需要启动服务但不需要完整流程。

### 端到端测试 (e2e/)
测试完整业务流程，从创建会议到生成纪要。

### Bug修复验证 (bug_fixes/)
针对特定Bug的回归测试，确保修复有效。

### 数据库连接测试 (db_connection/)
测试数据库连通性和兼容性。

## 运行测试

```bash
# 单元测试
python -m pytest test/unit/

# 集成测试（需先启动服务）
python test/integration/test_create_meeting.py

# E2E测试
python test/e2e/test_regenerate.py
```

import requests
import json
import time
import sys

BASE_URL = 'http://localhost:8765/api/v1'
results = []
passed = 0
failed = 0
existing_meeting_id = None
templates = []

def test_endpoint(name, method, url, **kwargs):
    global passed, failed
    try:
        if method == 'GET':
            resp = requests.get(url, timeout=30, **kwargs)
        elif method == 'POST':
            resp = requests.post(url, timeout=60, **kwargs)
        else:
            resp = requests.request(method, url, timeout=30, **kwargs)
        
        if resp.status_code < 400:
            results.append({'endpoint': f'{method} {name}', 'status': 'OK', 'status_code': resp.status_code, 'notes': ''})
            passed += 1
            return resp
        else:
            results.append({'endpoint': f'{method} {name}', 'status': 'FAIL', 'status_code': resp.status_code, 'notes': resp.text[:200]})
            failed += 1
            return None
    except Exception as e:
        results.append({'endpoint': f'{method} {name}', 'status': 'FAIL', 'status_code': None, 'notes': str(e)})
        failed += 1
        return None

print('='*60)
print('MEETING-MANAGEMENT API TEST')
print('='*60)

# 1. 测试健康检查
print('\n[1/7] Testing GET /health...')
resp = test_endpoint('/health', 'GET', f'{BASE_URL}/health')

# 2. 测试模板列表
print('[2/7] Testing GET /templates...')
resp = test_endpoint('/templates', 'GET', f'{BASE_URL}/templates')
if resp and resp.status_code == 200:
    try:
        data = resp.json()
        templates = data.get('templates', [])
        print(f'      Found {len(templates)} templates')
        for t in templates:
            print(f'      - {t.get("id")}: {t.get("name")}')
    except Exception as e:
        print(f'      Error parsing templates: {e}')

# 3. 测试会议列表并获取存在的ID
print('[3/7] Testing GET /meetings...')
resp = test_endpoint('/meetings', 'GET', f'{BASE_URL}/meetings')
if resp and resp.status_code == 200:
    try:
        data = resp.json()
        meetings = data.get('list', [])
        print(f'      Found {len(meetings)} meetings')
        if meetings:
            # 优先找 completed 状态的会议
            for m in meetings:
                if m.get('status') == 'completed':
                    existing_meeting_id = m.get('session_id')
                    break
            if not existing_meeting_id:
                existing_meeting_id = meetings[0].get('session_id')
            print(f'      Using meeting ID: {existing_meeting_id}')
    except Exception as e:
        print(f'      Error parsing meetings: {e}')

# 4. 测试会议详情
print('[4/7] Testing GET /meetings/{id}...')
if existing_meeting_id:
    resp = test_endpoint(f'/meetings/{existing_meeting_id}', 'GET', f'{BASE_URL}/meetings/{existing_meeting_id}')
else:
    results.append({'endpoint': 'GET /meetings/{id}', 'status': 'SKIP', 'status_code': None, 'notes': 'No meeting ID available'})
    print('      SKIPPED - No meeting ID available')

# 5. 测试重新生成纪要（如果有模板）
print('[5/7] Testing POST /meetings/{id}/regenerate...')
if existing_meeting_id and templates:
    # 测试第一个模板
    template_id = templates[0].get('id')
    print(f'      Using template: {template_id}')
    resp = test_endpoint(
        f'/meetings/{existing_meeting_id}/regenerate',
        'POST',
        f'{BASE_URL}/meetings/{existing_meeting_id}/regenerate',
        json={'template_id': template_id}
    )
    if resp and resp.status_code == 200:
        print('      Regeneration started successfully')
else:
    results.append({'endpoint': 'POST /meetings/{id}/regenerate', 'status': 'SKIP', 'status_code': None, 'notes': 'No meeting ID or templates available'})
    print('      SKIPPED - No meeting ID or templates available')

# 6. 测试下载纪要
print('[6/7] Testing GET /meetings/{id}/download...')
if existing_meeting_id:
    resp = test_endpoint(f'/meetings/{existing_meeting_id}/download', 'GET', f'{BASE_URL}/meetings/{existing_meeting_id}/download')
else:
    results.append({'endpoint': 'GET /meetings/{id}/download', 'status': 'SKIP', 'status_code': None, 'notes': 'No meeting ID available'})
    print('      SKIPPED - No meeting ID available')

# 7. 测试上传接口（只检查端点存在，不实际上传大文件）
print('[7/7] Testing POST /upload/audio...')
try:
    resp = requests.post(f'{BASE_URL}/upload/audio', timeout=10)
    if resp.status_code in [400, 422]:
        results.append({'endpoint': 'POST /upload/audio', 'status': 'OK', 'status_code': resp.status_code, 'notes': 'Endpoint exists (expects file)'})
        passed += 1
        print('      OK - Endpoint exists (expects file)')
    elif resp.status_code < 400:
        results.append({'endpoint': 'POST /upload/audio', 'status': 'OK', 'status_code': resp.status_code, 'notes': ''})
        passed += 1
        print('      OK')
    else:
        results.append({'endpoint': 'POST /upload/audio', 'status': 'FAIL', 'status_code': resp.status_code, 'notes': resp.text[:200]})
        failed += 1
        print(f'      FAIL - {resp.status_code}')
except Exception as e:
    results.append({'endpoint': 'POST /upload/audio', 'status': 'FAIL', 'status_code': None, 'notes': str(e)})
    failed += 1
    print(f'      FAIL - {e}')

# 输出最终报告
report = {
    'summary': {'total': len(results), 'passed': passed, 'failed': failed},
    'details': results
}

print()
print('='*60)
print('API TEST REPORT')
print('='*60)
print(json.dumps(report, indent=2, ensure_ascii=False))
print('='*60)
print(f'Result: {passed} passed, {failed} failed, {len(results) - passed - failed} skipped')

# 保存报告
with open('api_test_report.json', 'w', encoding='utf-8') as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print('Report saved to api_test_report.json')

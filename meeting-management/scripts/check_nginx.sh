#!/bin/bash
# Nginx 统一入口检查脚本
# 在 192.168.106.66 服务器上执行

echo "========== 1. Nginx 进程状态 =========="
ps aux | grep nginx | grep -v grep

echo ""
echo "========== 2. Nginx 配置语法 =========="
nginx -t

echo ""
echo "========== 3. 监听端口 =========="
netstat -tlnp | grep nginx

echo ""
echo "========== 4. 会议后端连通性 =========="
curl -s -o /dev/null -w "%{http_code}" http://172.20.3.70:8765/api/v1/health
echo " (期望: 200)"

echo ""
echo "========== 5. Django 连通性 =========="
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/api/health
echo " (期望: 200 或 404，只要不是 refused)"

echo ""
echo "========== 6. 测试统一入口 - 会议API =========="
curl -s -o /dev/null -w "%{http_code} %{http_location}" http://192.168.106.66/api/meetings/health
echo " (期望: 200)"

echo ""
echo "========== 7. 测试统一入口 - Django =========="  
curl -s -o /dev/null -w "%{http_code}" http://192.168.106.66/api/
echo " (期望: 200 或 404)"

echo ""
echo "========== 8. Nginx 错误日志（最近10行） =========="
tail -10 /var/log/nginx/error.log 2>/dev/null || echo "日志路径可能不同"

echo ""
echo "========== 9. Nginx 访问日志（最近5行） =========="
tail -5 /var/log/nginx/access.log 2>/dev/null || echo "日志路径可能不同"

echo ""
echo "========== 10. Nginx 配置内容（location部分） =========="
grep -A 10 "location /api/meetings" /etc/nginx/nginx.conf 2>/dev/null || \
grep -A 10 "location /api/meetings" /etc/nginx/conf.d/*.conf 2>/dev/null || \
echo "未找到会议管理location配置"

#!/usr/bin/env python3
import socket
import struct

def check_postgresql(host, port):
    """尝试识别 PostgreSQL 协议"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    try:
        s.connect((host, port))
        # PostgreSQL 启动包
        startup = b'\x00\x03\x00\x00'  # 协议版本 3.0
        startup += b'user\x00ai_gwy\x00'
        startup += b'database\x00meetings\x00\x00'
        length = struct.pack('>I', len(startup) + 4)
        s.send(length + startup)
        
        resp = s.recv(1024)
        print(f"响应类型: {hex(resp[0]) if resp else '无'}")
        print(f"响应内容: {resp[:100]}")
        
        # 'R' = 认证请求
        # 'E' = 错误
        if resp and resp[0] == 82:  # 'R'
            print("检测到 PostgreSQL 协议")
        elif resp and resp[0] == 69:  # 'E'
            print("PostgreSQL 错误响应")
            # 尝试解析错误信息
            try:
                err = resp[5:].decode('utf-8', errors='ignore')
                print(f"错误信息: {err}")
            except:
                pass
    except Exception as e:
        print(f"连接错误: {e}")
    finally:
        s.close()

check_postgresql('192.168.102.129', 9310)

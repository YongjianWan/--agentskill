#!/usr/bin/env python3
"""
SSP 平台认证模块

核心：双重 Base64 SM4 加密
"""

from gmssl.sm4 import CryptSM4, SM4_ENCRYPT
import base64
import requests
import time

# SSP 平台固定加密密钥
FIXED_KEY = "f0abc74a175329be"

# Token 获取端点（获取长期 Token）
TOKEN_URL = "https://www.ssfssp.com:8888/ssp/openApi/rSaWsmLo/NyYckwZA/SuoeqkoP/ssp-gateway-admin/api-user/createApiToken"
# 注意：此 Token 是长期的，不会过期，直接用于 Authorization 头


class SSPAuth:
    """SSP 平台认证管理器
    
    认证流程：
    1. SM4 ECB 加密 Credentials
    2. 双重 Base64 编码（SSP 平台要求）
    3. 获取 Token（有效期 5 分钟）
    4. 使用 Authorization: {token} 调用 API（直接传 Token，无 Bearer）
    """
    
    def __init__(self, access_key: str, secret_key: str):
        self.access_key = access_key
        self.secret_key = secret_key
        self._token = None
        self._token_expires = 0
    
    def _sm4_encrypt(self, key_str: str, data_str: str) -> str:
        """
        SM4 ECB 加密 + 双重 Base64
        
        注意：SSP 平台要求双重 Base64 编码
        1. SM4 加密原始数据 -> bytes
        2. Base64 编码 -> string  
        3. 再次 Base64 编码 -> final cipher
        """
        # SM4 加密
        crypt = CryptSM4()
        crypt.set_key(key_str.encode('utf-8'), SM4_ENCRYPT)
        encrypted_bytes = crypt.crypt_ecb(data_str.encode('utf-8'))
        
        # 第一次 Base64
        first_b64 = base64.b64encode(encrypted_bytes).decode('utf-8')
        
        # 第二次 Base64（SSP 平台特殊要求）
        final_cipher = base64.b64encode(first_b64.encode('utf-8')).decode('utf-8')
        
        return final_cipher
    
    def _get_cipher(self) -> str:
        """生成 cipher 密文"""
        data = f'{{"accessKey":"{self.access_key}","secretKey":"{self.secret_key}"}}'
        return self._sm4_encrypt(FIXED_KEY, data)
    
    def get_token(self, force_refresh: bool = False) -> str:
        """
        获取 SSP Token（带自动缓存和刷新）
        
        Args:
            force_refresh: 强制刷新 token
            
        Returns:
            Token 字符串
        """
        # 检查缓存（提前 60 秒刷新）
        if not force_refresh and time.time() < self._token_expires - 60:
            return self._token
        
        # 生成 cipher 并获取 token
        cipher = self._get_cipher()
        timestamp = str(int(time.time() * 1000))
        
        resp = requests.post(TOKEN_URL, json={
            "timestamp": timestamp,
            "cipher": cipher
        }, timeout=10)
        
        result = resp.json()
        if result.get("code") != "0":
            raise Exception(f"Token 获取失败: {result.get('msg')}")
        
        self._token = result["data"]["token"]
        self._token_expires = time.time() + 240  # 4 分钟缓存
        
        return self._token
    
    def get_auth_header(self) -> dict:
        """获取认证请求头"""
        return {
            "Authorization": self.get_token(),
            "Content-Type": "application/json"
        }


if __name__ == "__main__":
    # 测试
    import os
    
    access_key = os.getenv("SSP_ACCESS_KEY", "652cb30dd1")
    secret_key = os.getenv("SSP_SECRET_KEY", "24bf741821")
    
    auth = SSPAuth(access_key, secret_key)
    token = auth.get_token()
    
    print(f"Token: {token[:40]}...")
    print(f"Auth Header: {auth.get_auth_header()['Authorization'][:50]}...")

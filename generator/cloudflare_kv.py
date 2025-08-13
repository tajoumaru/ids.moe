# SPDX-License-Identifier: AGPL-3.0-only
# Copyright 2025 tajoumaru

"""
Cloudflare Workers KV client for Python
"""

import json
import requests
from typing import Any, Dict, List, Optional
from urllib.parse import quote


class CloudflareKV:
    """Client for Cloudflare Workers KV REST API"""
    
    def __init__(self, account_id: str, namespace_id: str, auth_token: str):
        """
        Initialize Cloudflare KV client
        
        :param account_id: Cloudflare account ID
        :param namespace_id: KV namespace ID
        :param auth_token: Cloudflare API token with Workers KV permissions
        """
        self.account_id = account_id
        self.namespace_id = namespace_id
        self.auth_token = auth_token
        self.base_url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/storage/kv/namespaces/{namespace_id}"
        self.headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }
        
    def get(self, key: str) -> Optional[str]:
        """Get a value by key"""
        url = f"{self.base_url}/values/{quote(key, safe='')}"
        response = requests.get(url, headers=self.headers)
        
        if response.status_code == 404:
            return None
        elif response.status_code == 200:
            return response.text
        else:
            response.raise_for_status()
            
    def set(self, key: str, value: str, expiration_ttl: Optional[int] = None) -> bool:
        """Set a key-value pair"""
        url = f"{self.base_url}/values/{quote(key, safe='')}"
        params = {}
        if expiration_ttl:
            params["expiration_ttl"] = expiration_ttl
            
        response = requests.put(
            url, 
            data=value,
            headers={**self.headers, "Content-Type": "text/plain"},
            params=params
        )
        return response.status_code == 200
    
    def delete(self, *keys: str) -> bool:
        """Delete one or more keys"""
        if len(keys) == 1:
            # Single key deletion
            url = f"{self.base_url}/values/{quote(keys[0], safe='')}"
            response = requests.delete(url, headers=self.headers)
            return response.status_code in (200, 404)
        else:
            # Bulk deletion
            url = f"{self.base_url}/bulk"
            data = json.dumps([{"key": key, "action": "delete"} for key in keys])
            response = requests.put(url, data=data, headers=self.headers)
            return response.status_code == 200
    
    def mset(self, mapping: Dict[str, str]) -> bool:
        """Set multiple key-value pairs at once"""
        if not mapping:
            return True
            
        url = f"{self.base_url}/bulk"
        
        # Cloudflare KV bulk API format
        operations = []
        for key, value in mapping.items():
            operations.append({
                "key": key,
                "value": value
            })
        
        # Split into batches of 10000 (Cloudflare limit)
        batch_size = 10000
        for i in range(0, len(operations), batch_size):
            batch = operations[i:i + batch_size]
            response = requests.put(
                url,
                json=batch,
                headers=self.headers
            )
            if response.status_code != 200:
                return False
                
        return True
    
    def list_keys(self, prefix: Optional[str] = None, limit: int = 1000) -> List[Dict[str, Any]]:
        """List keys in the namespace"""
        url = f"{self.base_url}/keys"
        params = {"limit": limit}
        if prefix:
            params["prefix"] = prefix
            
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            return response.json().get("result", [])
        return []
    
    
    def flushdb(self) -> bool:
        """Delete all keys in the namespace"""
        # List all keys and delete them
        all_keys = []
        cursor = None
        
        # First, collect all keys
        while True:
            url = f"{self.base_url}/keys"
            params = {"limit": 1000}
            if cursor:
                params["cursor"] = cursor
                
            response = requests.get(url, headers=self.headers, params=params)
            if response.status_code != 200:
                return False
                
            data = response.json()
            result = data.get("result", [])
            all_keys.extend([item["name"] for item in result])
            
            # Check if there are more pages
            result_info = data.get("result_info", {})
            if not result or len(result) < 1000 or not result_info.get("cursor"):
                break
                
            cursor = result_info.get("cursor")
        
        # Delete in batches
        if all_keys:
            batch_size = 10000
            for i in range(0, len(all_keys), batch_size):
                batch = all_keys[i:i + batch_size]
                if not self.delete(*batch):
                    return False
                    
        return True
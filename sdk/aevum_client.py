"""Aevum（薪火）OS - Python SDK.

供外部 Agent 接入的客户端库。
"""

import httpx
from typing import Optional


class AevumClient:
    """Aevum OS 客户端."""

    def __init__(self, base_url: str = "http://localhost:8000", api_key: str = None, token: str = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.token = token

    def _headers(self):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        elif self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def submit_task(self, intent: str, domain: str = "综合通用", task_type: str = "方案规划", constraints: dict = None) -> dict:
        """提交任务执行."""
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/api/v1/execution/tasks",
                json={"intent": intent, "context": {"domain": domain, "task_type": task_type, "constraints": constraints or {}}},
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def search_experiences(self, query: str, domain: str = None, limit: int = 10) -> list:
        """搜索经验."""
        params = {"query": query, "limit": limit}
        if domain:
            params["domain"] = domain
        with httpx.Client() as client:
            resp = client.post(
                f"{self.base_url}/api/v1/retrieval/search",
                json=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def get_experience(self, experience_id: str) -> dict:
        """获取经验详情."""
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base_url}/api/v1/experiences/{experience_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def list_experiences(self, page: int = 1, page_size: int = 20, domain: str = None) -> dict:
        """列出经验."""
        params = {"page": page, "page_size": page_size}
        if domain:
            params["domain"] = domain
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base_url}/api/v1/experiences",
                params=params,
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def get_dashboard(self) -> dict:
        """获取 Dashboard 数据."""
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base_url}/api/v1/evaluation/dashboard",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

    def get_metrics(self) -> dict:
        """获取系统指标."""
        with httpx.Client() as client:
            resp = client.get(
                f"{self.base_url}/api/v1/evaluation/metrics",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json()

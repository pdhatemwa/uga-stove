import os
from dataclasses import dataclass

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


@dataclass
class ApiError(Exception):
    status_code: int
    message: str

    def __str__(self) -> str:
        return self.message


class ApiClient:
    def __init__(self, token: str | None = None):
        self.base_url = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")
        self.token = token
        self.session = requests.Session()
        retries = Retry(
            total=3,
            connect=3,
            read=2,
            backoff_factor=0.4,
            status_forcelist=(502, 503, 504),
            allowed_methods=frozenset({"GET", "HEAD"}),
        )
        self.session.mount("http://", HTTPAdapter(max_retries=retries))
        self.session.mount("https://", HTTPAdapter(max_retries=retries))

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @staticmethod
    def _raise(response: requests.Response) -> None:
        if response.ok:
            return
        try:
            detail = response.json().get("detail", response.text)
            if isinstance(detail, list):
                detail = "; ".join(item.get("msg", str(item)) for item in detail)
        except ValueError:
            detail = response.text or "The service returned an unexpected error"
        raise ApiError(response.status_code, str(detail))

    def login(self, username: str, password: str) -> dict:
        response = self.session.post(
            f"{self.base_url}/api/v1/auth/login",
            data={"username": username, "password": password},
            timeout=15,
        )
        self._raise(response)
        return response.json()

    def get(self, path: str, *, params: dict | None = None, raw: bool = False):
        response = self.session.get(
            f"{self.base_url}{path}", headers=self._headers(), params=params, timeout=30
        )
        self._raise(response)
        return response.content if raw else response.json()

    def post(
        self,
        path: str,
        *,
        json: dict | None = None,
        data: dict | None = None,
        files: dict | None = None,
    ):
        response = self.session.post(
            f"{self.base_url}{path}",
            headers=self._headers(),
            json=json,
            data=data,
            files=files,
            timeout=120 if files else 30,
        )
        self._raise(response)
        return response.json()

    def patch(self, path: str, payload: dict):
        response = self.session.patch(
            f"{self.base_url}{path}", headers=self._headers(), json=payload, timeout=30
        )
        self._raise(response)
        return response.json()

"""Client gọi Nextcloud OCS Provisioning API (tạo user, đặt quota, bật/tắt tài khoản...).

Tài liệu: https://docs.nextcloud.com/server/stable/admin_manual/configuration_user/user_provisioning_api.html
Mọi lời gọi cần header "OCS-APIRequest: true" và xác thực Basic bằng tài khoản admin Nextcloud.
"""
import logging
from urllib.parse import quote

import httpx

from app.core.config import settings

log = logging.getLogger("portal.nextcloud")


class NextcloudError(Exception):
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


def quota_text(gb: int) -> str:
    return f"{gb} GB"


class NextcloudClient:
    def __init__(self, base_url: str, admin_user: str, admin_password: str):
        self.base = base_url.rstrip("/")
        self.auth = (admin_user, admin_password)

    def _call(self, method: str, path: str, data: dict | None = None):
        url = f"{self.base}/ocs/v1.php/cloud{path}"
        try:
            r = httpx.request(
                method,
                url,
                params={"format": "json"},
                data=data,
                auth=self.auth,
                headers={"OCS-APIRequest": "true", "Accept": "application/json"},
                timeout=20,
            )
        except httpx.HTTPError as exc:
            raise NextcloudError(f"Không kết nối được Nextcloud ({exc.__class__.__name__}).") from exc
        try:
            meta = r.json()["ocs"]["meta"]
        except (ValueError, KeyError, TypeError):
            raise NextcloudError(
                f"Nextcloud trả về phản hồi không hợp lệ (HTTP {r.status_code}). "
                "Kiểm tra Nextcloud đã khởi động xong, trusted_domains và tài khoản admin."
            )
        code = meta.get("statuscode")
        if code != 100:
            raise NextcloudError(meta.get("message") or f"Lỗi Nextcloud mã {code}", code=code)
        return r.json()["ocs"].get("data")

    # ---- Tài khoản ----
    def create_user(self, userid: str, password: str, email: str, display_name: str, quota_gb: int):
        self._call(
            "POST",
            "/users",
            {
                "userid": userid,
                "password": password,
                "email": email,
                "displayName": display_name,
                "quota": quota_text(quota_gb),
            },
        )

    def _edit(self, userid: str, key: str, value: str):
        self._call("PUT", f"/users/{quote(userid, safe='')}", {"key": key, "value": value})

    def set_quota(self, userid: str, quota_gb: int):
        self._edit(userid, "quota", quota_text(quota_gb))

    def set_password(self, userid: str, password: str):
        self._edit(userid, "password", password)

    def enable_user(self, userid: str):
        self._call("PUT", f"/users/{quote(userid, safe='')}/enable")

    def disable_user(self, userid: str):
        self._call("PUT", f"/users/{quote(userid, safe='')}/disable")

    def delete_user(self, userid: str):
        self._call("DELETE", f"/users/{quote(userid, safe='')}")

    def get_usage(self, userid: str) -> tuple[int, int | None]:
        """Trả về (bytes đã dùng, bytes tổng quota hoặc None nếu không giới hạn)."""
        data = self._call("GET", f"/users/{quote(userid, safe='')}") or {}
        q = data.get("quota") or {}
        used = int(q.get("used") or 0)
        total = q.get("total")
        return used, (int(total) if total not in (None, "") else None)


# Các module khác gọi qua `nextcloud.nc` để test có thể thay bằng bản giả.
nc = NextcloudClient(settings.nc_url, settings.nc_admin_user, settings.nc_admin_password)

import json
from typing import Any
from src.libs.custom_logger import get_custom_logger

from src.node.api_clients.base_client import BaseClient

logger = get_custom_logger(__name__)


class TrafficController(BaseClient):
    def __init__(self, host: str = "127.0.0.1", port: int = 8080):
        self._host = host
        self._port = port

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"http://{self._host}:{self._port}/{path.lstrip('/')}"
        headers = {"Content-Type": "application/json"}

        logger.info(f"TC request POST {url} payload={payload}")
        resp = self.make_request("post", url, headers=headers, data=json.dumps(payload))
        logger.info(f"TC response status={getattr(resp, 'status_code', None)}")

        return resp.json()

    def apply(self, *, node: str, command: str, value: Any = None) -> dict[str, Any]:
        return self._post("tc/apply", {"node": node, "command": command, "value": value})

    def add_latency(self, *, container_id: str, ms: int, jitter_ms: int | None = None) -> dict[str, Any]:
        value: dict[str, Any] = {"ms": ms}
        if jitter_ms is not None:
            value["jitter_ms"] = jitter_ms

        return self.apply(
            node=container_id,
            command="latency",
            value=value,
        )

    def add_packet_loss(self, *, container_id: str, percent: float) -> dict[str, Any]:
        return self.apply(
            node=container_id,
            command="loss",
            value={"percent": percent},
        )

    def add_bandwidth(self, *, container_id: str, rate: str) -> dict[str, Any]:
        return self.apply(
            node=container_id,
            command="bandwidth",
            value={"rate": rate},
        )

    def clear(self, *, container_id: str) -> dict[str, Any]:
        return self.apply(
            node=container_id,
            command="clear",
            value=None,
        )

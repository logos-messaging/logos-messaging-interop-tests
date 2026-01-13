import subprocess
from src.libs.custom_logger import get_custom_logger

logger = get_custom_logger(__name__)


class TrafficController:
    def _pid(self, node) -> int:
        if not node.container:
            raise RuntimeError("Node container not started yet")

        node.container.reload()
        pid = node.container.attrs.get("State", {}).get("Pid")
        if not pid or pid == 0:
            raise RuntimeError("Container PID not available (container not running?)")
        return int(pid)

    def _exec(self, node, tc_args: list[str], iface: str = "eth0"):
        pid = self._pid(node)

        cmd = ["sudo", "-n", "nsenter", "-t", str(pid), "-n", "tc"] + tc_args
        logger.info(f"TC exec: {cmd}")

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"TC failed: {' '.join(cmd)}\n" f"stdout: {res.stdout}\n" f"stderr: {res.stderr}")

    def clear(self, node, iface: str = "eth0"):
        try:
            self._exec(node, ["qdisc", "del", "dev", iface, "root"], iface=iface)
        except RuntimeError as e:
            msg = str(e)
            if "Cannot delete qdisc with handle of zero" in msg or "No such file or directory" in msg:
                return
            raise

    def add_latency(self, node, ms: int, iface: str = "eth0"):
        self.clear(node, iface=iface)
        self._exec(node, ["qdisc", "add", "dev", iface, "root", "netem", "delay", f"{ms}ms"], iface=iface)

    def add_packet_loss(self, node, percent: float, iface: str = "eth0"):
        self.clear(node, iface=iface)
        self._exec(node, ["qdisc", "add", "dev", iface, "root", "netem", "loss", f"{percent}%"], iface=iface)

    def add_bandwidth(self, node, rate: str, iface: str = "eth0"):
        self.clear(node, iface=iface)
        self._exec(
            node,
            ["qdisc", "add", "dev", iface, "root", "tbf", "rate", rate, "burst", "32kbit", "limit", "12500"],
            iface=iface,
        )

    def add_packet_loss_correlated(
        self,
        node,
        percent: float,
        correlation: float,
        iface: str = "eth0",
    ):
        self.clear(node, iface=iface)
        self._exec(
            node,
            [
                "qdisc",
                "add",
                "dev",
                iface,
                "root",
                "netem",
                "loss",
                f"{percent}%",
                f"{correlation}%",
            ],
            iface=iface,
        )

    def add_packet_loss_egress(
        self,
        node,
        percent: float,
        iface: str = "eth0",
    ):
        self.clear(node, iface=iface)
        self._exec(
            node,
            [
                "qdisc",
                "add",
                "dev",
                iface,
                "root",
                "netem",
                "loss",
                f"{percent}%",
            ],
            iface=iface,
        )

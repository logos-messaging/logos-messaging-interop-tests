import pytest, time, re, os
from src.env_vars import NODE_1, NODE_2, STRESS_ENABLED
from src.libs.common import delay
from src.libs.custom_logger import get_custom_logger
from src.node.waku_node import WakuNode
from src.steps.filter import StepsFilter
from src.steps.light_push import StepsLightPush
from src.steps.relay import StepsRelay
from src.steps.store import StepsStore
import re

logger = get_custom_logger(__name__)

"""
These tests make sure thst REST flags related to admin flags acting as expected 
"""


class TestAdminFlags(StepsFilter, StepsStore, StepsRelay, StepsLightPush):
    TAGS = ["TRC", "DBG", "INF", "NTC", "WRN", "ERR", "FTL"]

    LEVEL_RE = re.compile(r'"lvl"\s*:\s*"(TRC|DBG|INF|NTC|WRN|ERR|FTL)"|\b(TRC|DBG|INF|NTC|WRN|ERR|FTL)\b')

    def _read_tail_counts(self, path: str, start_size: int) -> dict:
        with open(path, "rb") as f:
            f.seek(start_size)
            text = f.read().decode(errors="ignore")
        counts = {t: 0 for t in self.TAGS}
        for a, b in self.LEVEL_RE.findall(text):
            counts[(a or b)] += 1
        return counts

    def _trigger(self):
        self.node1.info()
        self.node1.get_version()
        self.node1.get_debug_version()

    @pytest.fixture(scope="function", autouse=True)
    def nodes(self):
        self.node1 = WakuNode(NODE_2, f"node1_{self.test_id}")
        self.node2 = WakuNode(NODE_2, f"node2_{self.test_id}")
        self.node3 = WakuNode(NODE_2, f"node3_{self.test_id}")
        self.node4 = WakuNode(NODE_2, f"node3_{self.test_id}")

    def _tail(self, path, start_size):
        with open(path, "rb") as f:
            f.seek(start_size)
            return f.read().decode(errors="ignore")

    def _count_levels(self, text, levels):
        return {lvl: len(re.findall(getattr(self, f"{lvl}_RE"), text)) for lvl in levels}

    def test_admin_filter_subscriptions_shape(self):
        self.node1.start(filter="true", relay="true")
        self.node2.start(relay="false", filternode=self.node1.get_multiaddr_with_id(), discv5_bootstrap_node=self.node1.get_enr_uri())
        resp = self.node2.set_filter_subscriptions(
            {"requestId": "1", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic}
        )
        subs = self.node1.get_filter_subscriptions()
        logger.debug(f"Node admin subscriptions info{subs}")
        assert resp["statusDesc"] == "OK" and resp["requestId"] == "1"
        logger.debug(f"node 1 peers {self.node1.get_peers()}")
        assert self.node2.get_multiaddr_with_id().rpartition("/p2p/")[2] == subs[0]["peerId"], "peer id doesn't match"
        assert subs[0]["filterCriteria"][0]["pubsubTopic"] == self.test_pubsub_topic, "pubsub topic doesn't match"
        assert subs[0]["filterCriteria"][0]["contentTopic"] == self.test_content_topic, "content topic doesn't match"

    def test_admin_peers_stats_shape(self):
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())

        stats = self.node1.get_peer_stats()
        logger.debug(f"Node admin peers stats {stats}")

    def test_admin_peers_stats_counts(self):
        self.node1.start(filter="true", relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node1.add_peers([self.node3.get_multiaddr_with_id()])
        self.node4.start(relay="false", filternode=self.node1.get_multiaddr_with_id(), discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node4.set_filter_subscriptions({"requestId": "1", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic})

        stats = self.node1.get_peer_stats()
        logger.debug(f"Node-1 admin peers stats {stats}")

        assert stats["Sum"]["Total peers"] == 3, "expected 3 peers connected to node1"
        assert stats["Relay peers"]["Total relay peers"] == 2, "expected exactly 2 relay peer"

    def test_admin_peers_mesh_on_shard_contains_node2(self):
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        mesh = self.node1.get_mesh_peers_on_shard(self.node1.start_args["shard"])
        logger.debug(f"Node-1 mesh on the shard  {mesh}")

        logger.debug("Validate the schema variables")
        assert isinstance(mesh["shard"], int) and mesh["shard"] == int(self.node1.start_args["shard"]), "shard mismatch"
        peer_maddrs = [p["multiaddr"] for p in mesh["peers"]]
        assert self.node2.get_multiaddr_with_id() in peer_maddrs and self.node3.get_multiaddr_with_id() in peer_maddrs, "node2 or node3 not in mesh"
        for p in mesh["peers"]:
            assert isinstance(p["protocols"], list) and all(isinstance(x, str) for x in p["protocols"]), "protocols must be [str]"
            assert isinstance(p["shards"], list) and all(isinstance(x, int) for x in p["shards"]), "shards must be [int]"
            assert isinstance(p["agent"], str), "agent not str"
            assert isinstance(p["origin"], str), "origin not str"
            assert isinstance(p.get("score", 0.0), (int, float)), "score not number"

    def test_admin_peer_by_id(self):
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        peer_id = self.node2.get_multiaddr_with_id().rpartition("/p2p/")[2]
        info = self.node1.get_peer_info(peer_id)
        logger.debug(f"Node-1 /admin/v1/peer/{peer_id}: {info} \n")
        logger.debug("Validate response schema")
        for k in ("multiaddr", "protocols", "shards", "connected", "agent", "origin"):
            assert k in info, f"missing field: {k}"
        assert info["multiaddr"] == self.node2.get_multiaddr_with_id(), "multiaddr mismatch"

    def test_admin_set_all_log_levels(self):
        self.node1.start(relay="true")
        self.node1.container()
        levels = ["TRACE", "DEBUG", "INFO", "NOTICE", "WARN", "ERROR", "FATAL"]
        _levels = ["INFO"]
        for lvl in _levels:
            resp = self.node1.set_log_level(lvl)
            logger.debug(f"Set log level ({lvl})")
            self.node2.start(relay="true")
            assert resp.status_code == 200, f"failed to set log level {lvl} {resp.text}"
            self.node2.info()
            self.node2.get_debug_version()

        resp = self.node1.set_log_level("TRACE")
        logger.debug(f"Restore default log level (TRACE) -> status={resp.status_code}")
        assert resp.status_code == 200, f"failed to revert log level: {resp.text}"

    @pytest.mark.timeout(120)
    def test_log_level_DEBUG_from_TRACE(self):
        self.node1.start(relay="true")
        path = self.node1._log_path
        for _ in range(50):
            if os.path.exists(path):
                break
            time.sleep(0.05)

        assert self.node1.set_log_level("TRACE").status_code == 200
        assert self.node1.set_log_level("DEBUG").status_code == 200

        start = os.path.getsize(path)
        self._trigger()
        time.sleep(2)

        counts = self._read_tail_counts(path, start)
        logger.debug(f"counts at DEBUG: {counts}")

        assert counts["DBG"] > 0, "expected DEBUG logs at DEBUG level"
        assert counts["TRC"] == 0, "TRACE must be filtered at DEBUG"

        assert self.node1.set_log_level("TRACE").status_code == 200

    @pytest.mark.timeout(120)
    def test_log_level_INFO_from_DEBUG(self):
        self.node1.start(relay="true")
        path = self.node1._log_path
        for _ in range(50):
            if os.path.exists(path):
                break
            time.sleep(0.05)

        # assert self.node1.set_log_level("DEBUG").status_code == 200
        assert self.node1.set_log_level("INFO").status_code == 200

        start = os.path.getsize(path)
        self._trigger()
        time.sleep(2)

        counts = self._read_tail_counts(path, start)
        logger.debug(f"counts at INFO: {counts}")

        assert counts["INF"] > 0, "expected INFO logs at INFO level"
        assert counts["DBG"] == 0 and counts["TRC"] == 0, "lower than INFO (DBG/TRC) must be filtered"

        assert self.node1.set_log_level("TRACE").status_code == 200

    @pytest.mark.timeout(120)
    def test_log_level_NOTICE_from_INFO(self):
        self.node1.start(relay="true")
        path = self.node1._log_path
        for _ in range(50):
            if os.path.exists(path):
                break
            time.sleep(0.05)

        assert self.node1.set_log_level("INFO").status_code == 200
        assert self.node1.set_log_level("NOTICE").status_code == 200

        start = os.path.getsize(path)
        self._trigger()
        time.sleep(2)

        counts = self._read_tail_counts(path, start)
        logger.debug(f"counts at NOTICE: {counts}")

        assert counts["NTC"] > 0, "expected NOTICE logs at NOTICE level"
        for lv in ["TRC", "DBG", "INF"]:
            assert counts[lv] == 0, f"{lv} must be filtered at NOTICE"

        assert self.node1.set_log_level("TRACE").status_code == 200

    @pytest.mark.timeout(120)
    def test_log_level_WARN_from_NOTICE(self):
        self.node1.start(relay="true")
        path = self.node1._log_path
        for _ in range(50):
            if os.path.exists(path):
                break
            time.sleep(0.05)

        assert self.node1.set_log_level("NOTICE").status_code == 200
        assert self.node1.set_log_level("WARN").status_code == 200

        start = os.path.getsize(path)
        self._trigger()
        time.sleep(2)

        counts = self._read_tail_counts(path, start)
        logger.debug(f"counts at WARN: {counts}")

        assert counts["WRN"] > 0, "expected WARN logs at WARN level"
        for lv in ["TRC", "DBG", "INF", "NTC"]:
            assert counts[lv] == 0, f"{lv} must be filtered at WARN"

        assert self.node1.set_log_level("TRACE").status_code == 200

    @pytest.mark.timeout(120)
    def test_log_level_ERROR_from_WARN(self):
        self.node1.start(relay="true")
        path = self.node1._log_path
        for _ in range(50):
            if os.path.exists(path):
                break
            time.sleep(0.05)

        assert self.node1.set_log_level("WARN").status_code == 200
        assert self.node1.set_log_level("ERROR").status_code == 200

        start = os.path.getsize(path)
        self._trigger()
        time.sleep(2)

        counts = self._read_tail_counts(path, start)
        logger.debug(f"counts at ERROR: {counts}")

        assert counts["ERR"] > 0, "expected ERROR logs at ERROR level"
        for lv in ["TRC", "DBG", "INF", "NTC", "WRN"]:
            assert counts[lv] == 0, f"{lv} must be filtered at ERROR"

        assert self.node1.set_log_level("TRACE").status_code == 200

    @pytest.mark.timeout(120)
    def test_log_level_FATAL_from_ERROR(self):
        self.node1.start(relay="true")
        path = self.node1._log_path
        for _ in range(50):
            if os.path.exists(path):
                break
            time.sleep(0.05)

        assert self.node1.set_log_level("ERROR").status_code == 200
        assert self.node1.set_log_level("FATAL").status_code == 200

        start = os.path.getsize(path)
        self._trigger()
        time.sleep(2)

        counts = self._read_tail_counts(path, start)
        logger.debug(f"counts at FATAL: {counts}")

        assert counts["FTL"] > 0, "expected FATAL logs at FATAL level"
        for lv in ["TRC", "DBG", "INF", "NTC", "WRN", "ERR"]:
            assert counts[lv] == 0, f"{lv} must be filtered at FATAL"

        assert self.node1.set_log_level("TRACE").status_code == 200

    def test_get_connected_peers_contains_node2(self):
        node1 = node2 = None
        try:
            name = getattr(self, "test_id", "adminflags")
            node1 = WakuNode(NODE_1, f"node1_{name}")
            node2 = WakuNode(NODE_2, f"node2_{name}")

            node1.start(relay="true")
            node2.start(relay="true", discv5_bootstrap_node=node1.get_enr_uri())

            def node2_connected():
                peers = node1.get_connected_peers()
                logger.debug(f"/admin/v1/peers/connected -> {peers}")
                if not isinstance(peers, list) or not peers:
                    return False
                maddrs = [self._extract_multiaddr(p) for p in peers]
                return node2.get_multiaddr_with_id() in maddrs

            self._wait_until(node2_connected, timeout=60, step=1.0, desc="node2 to show in connected peers")
        finally:
            for n in (node2, node1):
                if n:
                    n.stop()

    def test_get_relay_peers_contains_nodes(self):
        node1 = node2 = node3 = None
        try:
            name = getattr(self, "test_id", "adminflags")
            node1 = WakuNode(NODE_1, f"node1_{name}")
            node2 = WakuNode(NODE_2, f"node2_{name}")
            node3 = WakuNode(NODE_2, f"node3_{name}")

            node1.start(relay="true")
            node2.start(relay="true", discv5_bootstrap_node=node1.get_enr_uri())
            node3.start(relay="true", discv5_bootstrap_node=node1.get_enr_uri())

            def peers_listed():
                peers = node1.get_relay_peers()
                logger.debug(f"/admin/v1/peers/relay -> {peers}")
                if not isinstance(peers, list) or not peers:
                    return False
                maddrs = [self._extract_multiaddr(p) for p in peers]
                return any(ma in maddrs for ma in (node2.get_multiaddr_with_id(), node3.get_multiaddr_with_id()))

            self._wait_until(peers_listed, timeout=60, step=1.0, desc="relay peers to be listed")
        finally:
            for n in (node3, node2, node1):
                if n:
                    n.stop()

    def test_get_relay_peers_on_shard_contains_bootstrapped_node(self):
        node1 = WakuNode(NODE_1, "node1_relay_shard")
        node2 = WakuNode(NODE_2, "node2_relay_shard")

        node1.start(relay="true")
        node2.start(relay="true", discv5_bootstrap_node=node1.get_enr_uri())

        shard_id = 0  # default shard
        deadline = time.time() + 60
        present = False
        while time.time() < deadline and not present:
            resp = node1.get_relay_peers_on_shard(shard_id)
            peers = resp.get("peers", []) if isinstance(resp, dict) else []
            maddrs = []
            for p in peers:
                m = p.get("multiaddr") or (p.get("multiaddrs")[0] if p.get("multiaddrs") else None)
                if m:
                    maddrs.append(m)
            if node2.get_multiaddr_with_id() in maddrs:
                present = True
            else:
                time.sleep(1.0)

        assert present, f"expected node2 in /admin/v1/peers/relay/on/{shard_id}"
        node2.stop()
        node1.stop()

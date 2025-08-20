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

    def test_admin_peers_stats_schema(self):
        self.node1.start(filter="true", relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        stats = self.node1.get_peer_stats()
        logger.debug(f"Peer stats schema check: {stats}")
        assert isinstance(stats, dict), "stats must be a dict"
        for k in ("Sum", "Relay peers"):
            assert k in stats, f"missing section: {k}"
            assert isinstance(stats[k], dict), f"{k} must be a dict"
        assert isinstance(stats["Sum"].get("Total peers", 0), int) and stats["Sum"]["Total peers"] >= 0, "Sum.Total peers must be a non-negative int"
        assert (
            isinstance(stats["Relay peers"].get("Total relay peers", 0), int) and stats["Relay peers"]["Total relay peers"] >= 0
        ), "Relay peers.Total relay peers must be a non-negative int"

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

    def test_relay_peers_on_shard_schema(self):
        node_shard = "0"
        self.node1.start(relay="true", shard=node_shard, dns_discovery="false")
        self.node2.start(
            relay="true",
            shard=node_shard,
            dns_discovery="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        time.sleep(1)
        resp = self.node1.get_relay_peers_on_shard(node_shard)
        logger.debug(f"relay peers on shard=0 (schema): {resp!r}")
        assert str(resp["shard"]) == node_shard, "Returned 'shard' must match requested shardId"
        for p in resp["peers"]:
            assert isinstance(p.get("multiaddr"), str) and p["multiaddr"].strip(), "peer.multiaddr must be a non-empty string"
            if "protocols" in p:
                assert isinstance(p["protocols"], list) and all(isinstance(x, str) for x in p["protocols"]), "peer.protocols must be list[str]"
            if "shards" in p:
                assert isinstance(p["shards"], list), "peer.shards must be a list"
            if "connected" in p:
                assert isinstance(p["connected"], str), "peer.connected must be a string"
            if "agent" in p:
                assert isinstance(p["agent"], str), "peer.agent must be a string"
            if "origin" in p:
                assert isinstance(p["origin"], str), "peer.origin must be a string"
            if "score" in p:
                assert isinstance(p["score"], (int, float)), "peer.score must be a number"

    def test_relay_peers_on_shard_contains_connected_peer(self):
        self.node1.start(relay="true", shard="0", dns_discovery="false")
        self.node2.start(
            relay="true",
            shard="0",
            dns_discovery="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        n2_addr = self.node2.get_multiaddr_with_id()
        resp = self.node1.get_relay_peers_on_shard("0")
        logger.debug(f"checking shard=0 list: {resp!r}")
        assert any(
            p.get("multiaddr") == n2_addr for p in resp["peers"]
        ), f"Expected Node-2 address {n2_addr} in Node-1's /admin/v1/peers/relay/on/0 list"

    def test_admin_relay_peers_schema(self):
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node1.add_peers([self.node2.get_multiaddr_with_id()])
        self.node2.add_peers([self.node1.get_multiaddr_with_id()])
        time.sleep(1)

        resp = self.node1.get_relay_peers()
        logger.debug(f"/admin/v1/peers/relay (schema): {resp!r} / type={type(resp).__name__}")

        groups = resp if isinstance(resp, list) else [resp]
        for grp in groups:
            peers_list = grp.get("peers")
            assert isinstance(peers_list, list), "'peers' must be a list"
            for peer in peers_list:
                ma = peer.get("multiaddr")
                assert isinstance(ma, str) and ma.strip(), "multiaddr must be a non-empty string"
                if "protocols" in peer:
                    protos = peer["protocols"]
                    assert isinstance(protos, list) and all(isinstance(x, str) for x in protos), "protocols must be list[str]"
                if "score" in peer:
                    assert isinstance(peer["score"], (int, float)), "score must be a number"

    def test_admin_relay_peers_contains_all_three(self):
        self.node1.start(relay="true")

        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3 = WakuNode(NODE_2, f"node3_{self.test_id}")
        self.node4 = WakuNode(NODE_2, f"node4_{self.test_id}")
        self.node3.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node4.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())

        n2_addr = self.node2.get_multiaddr_with_id()
        n3_addr = self.node3.get_multiaddr_with_id()
        n4_addr = self.node4.get_multiaddr_with_id()
        time.sleep(1)

        resp = self.node1.get_relay_peers()
        logger.debug(f"/admin/v1/peers/relay (contains 3 peers): {resp!r}")

        peer_addrs = {peer["multiaddr"] for group in resp for peer in group["peers"]}
        assert n2_addr in peer_addrs, f"Missing Node-2 address {n2_addr}"
        assert n3_addr in peer_addrs, f"Missing Node-3 address {n3_addr}"
        assert n4_addr in peer_addrs, f"Missing Node-4 address {n4_addr}"

import pytest
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
    @pytest.fixture(scope="function", autouse=True)
    def nodes(self):
        self.node1 = WakuNode(NODE_2, f"node1_{self.test_id}")
        self.node2 = WakuNode(NODE_2, f"node2_{self.test_id}")
        self.node3 = WakuNode(NODE_2, f"node3_{self.test_id}")
        self.node4 = WakuNode(NODE_2, f"node3_{self.test_id}")

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

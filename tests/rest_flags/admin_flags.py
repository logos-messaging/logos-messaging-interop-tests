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


class TestE2E(StepsFilter, StepsStore, StepsRelay, StepsLightPush):
    @pytest.fixture(scope="function", autouse=True)
    def nodes(self):
        self.node1 = WakuNode(NODE_2, f"node1_{self.test_id}")
        self.node2 = WakuNode(NODE_2, f"node2_{self.test_id}")

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

import pytest
import logging
from time import time
from src.libs.custom_logger import get_custom_logger
from src.env_vars import NODE_1, NODE_2
from src.node.waku_node import WakuNode
from src.steps.relay import StepsRelay
from src.libs.common import delay
from src.steps.common import StepsCommon
from src.steps.network_conditions import TrafficController

logger = get_custom_logger(__name__)


class TestNetworkConditions(StepsRelay):
    @pytest.fixture(scope="function", autouse=True)
    def setup_nodes(self, request):
        self.node1 = WakuNode(NODE_1, f"node1_{request.cls.test_id}")
        self.node2 = WakuNode(NODE_2, f"node2_{request.cls.test_id}")
        self.tc = TrafficController(host="127.0.0.1", port=8080)

    def test_relay_with_latency_between_two_nodes(self):
        logger.info("Starting node1 and node2 with relay enabled")
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())

        logger.info("Subscribing both nodes to relay topic")
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])

        logger.info("Waiting for autoconnection")
        self.wait_for_autoconnection([self.node1, self.node2], hard_wait=10)

        logger.info("Applying 500ms latency to node2")
        self.tc.add_latency(container_id=self.node2.container_id, ms=500)

        message = self.create_message()

        logger.info("Publishing message from node1")
        start = time()
        self.node1.send_relay_message(message, self.test_pubsub_topic)

        delay(1)

        logger.info("Fetching relay messages on node2")
        messages = self.node2.get_relay_messages(self.test_pubsub_topic)
        end = time()

        logger.info("Clearing network conditions on node2")
        self.tc.clear(container_id=self.node2.container_id)

        assert messages, "Message was not received under latency"
        assert (end - start) >= 0.5

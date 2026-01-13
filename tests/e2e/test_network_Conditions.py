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
        self.tc = TrafficController()

    def test_relay_with_latency_between_two_nodes(self):
        logger.info("Starting node1 and node2 with relay enabled")
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())

        logger.info("Subscribing both nodes to relay topic")
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])

        logger.info("Waiting for autoconnection")
        self.wait_for_autoconnection([self.node1, self.node2], hard_wait=10)

        logger.debug("Applying 500ms latency to node2")
        self.tc.add_latency(self.node2, ms=5000)
        message = self.create_message()

        logger.debug("Publishing message from node1")

        self.node1.send_relay_message(message, self.test_pubsub_topic)
        logger.debug("Fetching relay messages on node2")
        t0 = time()
        messages = self.node2.get_relay_messages(self.test_pubsub_topic)
        dt = time() - t0
        assert messages, "Message arrived too early; latency may not be applied"
        assert dt >= 4.5, f"Expected slow GET due to latency, got {dt}"
        assert dt <= 5.5, "msg took too long"
        self.tc.clear(self.node2)

    @pytest.mark.timeout(60 * 8)
    def test_relay_7_nodes_3sec_latency(self):
        self.node1 = WakuNode(NODE_1, f"node1_{self.test_id}")
        self.node2 = WakuNode(NODE_2, f"node2_{self.test_id}")
        self.node3 = WakuNode(NODE_2, f"node3_{self.test_id}")
        self.node4 = WakuNode(NODE_2, f"node4_{self.test_id}")
        self.node5 = WakuNode(NODE_2, f"node5_{self.test_id}")
        self.node6 = WakuNode(NODE_2, f"node6_{self.test_id}")
        self.node7 = WakuNode(NODE_2, f"node7_{self.test_id}")

        nodes = [self.node1, self.node2, self.node3, self.node4, self.node5, self.node6, self.node7]

        logger.info("Starting nodes with chain bootstrap")
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="true", discv5_bootstrap_node=self.node2.get_enr_uri())
        self.node4.start(relay="true", discv5_bootstrap_node=self.node3.get_enr_uri())
        self.node5.start(relay="true", discv5_bootstrap_node=self.node4.get_enr_uri())
        self.node6.start(relay="true", discv5_bootstrap_node=self.node5.get_enr_uri())
        self.node7.start(relay="true", discv5_bootstrap_node=self.node6.get_enr_uri())

        logger.info("Subscribing all nodes to relay topic")
        for node in nodes:
            node.set_relay_subscriptions([self.test_pubsub_topic])

        logger.info("Waiting for autoconnection")
        self.wait_for_autoconnection(nodes, hard_wait=60)

        logger.info("Applying 3s latency to node3")
        self.tc.add_latency(self.node3, ms=3000)

        t_start = time()
        _ = self.node3.get_relay_messages(self.test_pubsub_topic)
        elapsed = time() - t_start

        logger.info(f"Observed GET latency on node3: {elapsed:.2f}s")
        assert elapsed >= 2.8, f"Expected ~3s latency on node3 GET, got {elapsed:.2f}s"

    @pytest.mark.timeout(60 * 6)
    def test_relay_4_nodes_sender_latency(self):
        self.node3 = WakuNode(NODE_2, f"node3_{self.test_id}")
        self.node4 = WakuNode(NODE_2, f"node4_{self.test_id}")

        logger.info("Starting 4 nodes with relay enabled (bootstrap chain)")
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="true", discv5_bootstrap_node=self.node2.get_enr_uri())
        self.node4.start(relay="true", discv5_bootstrap_node=self.node3.get_enr_uri())

        nodes = [self.node1, self.node2, self.node3, self.node4]

        for n in nodes:
            n.set_relay_subscriptions([self.test_pubsub_topic])

        self.wait_for_autoconnection(nodes, hard_wait=40)

        latency_ms = 3000
        logger.info(f"Applying {latency_ms}ms latency on sender node1")
        self.tc.add_latency(self.node1, ms=latency_ms)

        t_pub0 = time()
        self.node1.send_relay_message(self.create_message(), self.test_pubsub_topic)
        publish_dt = time() - t_pub0

        # assert publish_dt > (latency_ms / 1000.0) - 0.4, f"Expected publish call to be slowed by sender latency. "
        # assert publish_dt <= (latency_ms / 1000.0) + 0.4, f"Publish call took too long"

        deadline = t_pub0 + 10.0
        received = False

        while time() < deadline:
            msgs = self.node4.get_relay_messages(self.test_pubsub_topic) or []
            if msgs:
                received = True
                break
            delay(0.2)

        assert received, f"node4 did not receive any relay message within {deadline}"

        self.tc.clear(self.node1)

    @pytest.mark.timeout(60 * 8)
    def test_relay_4_nodes_two_publishers_compare_latency(self):
        self.node3 = WakuNode(NODE_2, f"node3_{self.test_id}")
        self.node4 = WakuNode(NODE_2, f"node4_{self.test_id}")

        logger.info("Starting 4 nodes ")
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="true", discv5_bootstrap_node=self.node2.get_enr_uri())
        self.node4.start(relay="true", discv5_bootstrap_node=self.node3.get_enr_uri())

        nodes = [self.node1, self.node2, self.node3, self.node4]

        for n in nodes:
            n.set_relay_subscriptions([self.test_pubsub_topic])

        self.wait_for_autoconnection(nodes, hard_wait=60)

        latency_ms = 3000
        logger.debug(f"Applying {latency_ms}ms latency on node1 only")
        self.tc.add_latency(self.node1, ms=latency_ms)

        node1_dts = []
        node2_dts = []
        _ = self.node4.get_relay_messages(self.test_pubsub_topic)

        for i in range(5):
            t0 = time()
            self.node1.send_relay_message(self.create_message(), self.test_pubsub_topic)
            node1_dts.append(time() - t0)

            t0 = time()
            self.node2.send_relay_message(
                self.create_message(),
                self.test_pubsub_topic,
            )
            node2_dts.append(time() - t0)

            delay(0.2)

        # for dt in node1_dts:
        # assert dt > (latency_ms / 1000.0) - 0.4, "Expected node1 publish to be slowed by latency"
        # assert dt <= (latency_ms / 1000.0) + 0.4, "node1 publish took too long"

        for dt in node2_dts:
            assert dt < 1.0, f"Expected node2 publish to be fast"

        deadline = time() + 10.0
        received = False
        while time() < deadline:
            msgs = self.node4.get_relay_messages(self.test_pubsub_topic) or []
            if msgs:
                received = True
                break
            delay(0.2)

        assert received, f"node4 did not receive any relay message within time"

        self.tc.clear(self.node1)

    @pytest.mark.timeout(60 * 6)
    @pytest.mark.parametrize(
        "latency_ms",
        [
            200,
            500,
            1000,
            5000,
            7000,
        ],
    )
    def test_relay_different_latency_between_two_nodes(self, latency_ms):
        logger.info("Starting node1 and node2 with relay enabled")
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())

        logger.info("Subscribing both nodes to relay topic")
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])

        logger.info("Waiting for autoconnection")
        self.wait_for_autoconnection([self.node1, self.node2], hard_wait=10)

        logger.info(f"Applying {latency_ms}ms latency to node2")
        self.tc.clear(self.node2)
        if latency_ms > 0:
            self.tc.add_latency(self.node2, ms=latency_ms)

        message = self.create_message()
        self.node1.send_relay_message(message, self.test_pubsub_topic)
        t0 = time()
        messages = self.node2.get_relay_messages(self.test_pubsub_topic)
        dt = time() - t0

        assert messages, "No relay messages returned (publish/relay may have failed)"
        expected_s = (latency_ms / 1000.0) * 2
        tolerance_s = 0.5
        assert dt >= expected_s - tolerance_s, f"Expected >= {expected_s - tolerance_s}s, got {dt}s"
        assert dt <= expected_s + tolerance_s, f"Expected <= {expected_s + tolerance_s}s, got {dt}s"
        self.tc.clear(self.node2)

    @pytest.mark.timeout(60 * 10)
    def test_relay_sustained_latency_under_load_sender_burst(self):
        latency_ms = 3000
        total_messages = 50
        wait_time = 40.0
        acceptable_msgs = total_messages / 2
        self.node3 = WakuNode(NODE_2, f"node3_{self.test_id}")
        self.node4 = WakuNode(NODE_2, f"node4_{self.test_id}")
        logger.info("Starting 4 nodes with relay enabled")
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node4.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())

        logger.info("Subscribing all nodes to relay topic")
        for n in [self.node1, self.node2, self.node3, self.node4]:
            n.set_relay_subscriptions([self.test_pubsub_topic])

        self.wait_for_autoconnection([self.node1, self.node2, self.node3, self.node4], hard_wait=30)

        _ = self.node4.get_relay_messages(self.test_pubsub_topic)

        logger.info(f"Applying {latency_ms}ms latency on sender node1")
        self.tc.clear(self.node1)
        self.tc.add_latency(self.node1, ms=latency_ms)

        logger.info(f"Sending {total_messages} messages from node1")
        for i in range(total_messages):
            self.node1.send_relay_message(self.create_message(), self.test_pubsub_topic)

        received_count = 0
        last_count = 0
        ticks = 0

        deadline = time() + wait_time
        while time() < deadline:
            msgs = self.node4.get_relay_messages(self.test_pubsub_topic) or []
            if len(msgs) > last_count:
                ticks += 1
                last_count = len(msgs)
            received_count = max(received_count, len(msgs))
            if received_count >= acceptable_msgs:
                break
            delay(1)

        logger.info(f"Node4 received {received_count} messages " f"(min_expected={acceptable_msgs}, total_sent={total_messages})")

        assert received_count >= acceptable_msgs, "relay stalled or dropped all traffic; "
        self.tc.clear(self.node1)

    def test_relay_4_nodes_sender_packet_loss_simple(self):
        self.node3 = WakuNode(NODE_2, f"node3_{self.test_id}")
        self.node4 = WakuNode(NODE_2, f"node4_{self.test_id}")

        logger.info("Starting 4 nodes with relay enabled (bootstrap chain)")
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="true", discv5_bootstrap_node=self.node2.get_enr_uri())
        self.node4.start(relay="true", discv5_bootstrap_node=self.node3.get_enr_uri())

        nodes = [self.node1, self.node2, self.node3, self.node4]
        for n in nodes:
            n.set_relay_subscriptions([self.test_pubsub_topic])

        self.wait_for_autoconnection(nodes, hard_wait=60)

        loss_percent = 30.0
        logger.info(f"Applying {loss_percent}% packet loss on sender node1")
        self.tc.add_packet_loss(self.node1, percent=loss_percent)

        _ = self.node4.get_relay_messages(self.test_pubsub_topic)

        self.node1.send_relay_message(self.create_message(), self.test_pubsub_topic)

        deadline = time() + 10.0
        received = False

        while time() < deadline:
            msgs = self.node4.get_relay_messages(self.test_pubsub_topic) or []
            if msgs:
                received = True
                break
            delay(0.2)

        assert received, f"node4 did not receive any relay message"

        self.tc.clear(self.node1)

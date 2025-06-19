import pytest
from src.env_vars import NODE_1, NODE_2, STRESS_ENABLED
from src.libs.common import delay
from src.libs.custom_logger import get_custom_logger
from src.node.waku_node import WakuNode
from src.steps.filter import StepsFilter
from src.steps.light_push import StepsLightPush
from src.steps.relay import StepsRelay
from src.steps.store import StepsStore

logger = get_custom_logger(__name__)

"""
In those tests we aim to combine multiple protocols/node types and create a more end-to-end scenario
"""


class TestE2E(StepsFilter, StepsStore, StepsRelay, StepsLightPush):
    @pytest.fixture(scope="function", autouse=True)
    def nodes(self):
        self.node1 = WakuNode(NODE_2, f"node1_{self.test_id}")
        self.node2 = WakuNode(NODE_1, f"node2_{self.test_id}")
        self.node3 = WakuNode(NODE_2, f"node3_{self.test_id}")

    def test_relay_receiving_node_not_connected_directly_to_relaying_node(self):
        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="true", discv5_bootstrap_node=self.node2.get_enr_uri())

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        # for e2e scenarios I think waiting for autoconnection is important instead of forcing connection via API calls
        # that's why the bellow code is commented to showcase this difference. In case we uncomment it, the connection will be faster
        # self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        # self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])
        self.wait_for_autoconnection([self.node1, self.node2, self.node3], hard_wait=30)

        # self.node1 relays and we check that self.node3 receives the message
        self.check_published_message_reaches_relay_peer(sender=self.node1, peer_list=[self.node3], message_propagation_delay=1)

    def test_filter_node_not_connected_directly_to_relaying_node(self):
        self.node1.start(filter="true", relay="true")
        self.node2.start(filter="true", relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="false", filternode=self.node2.get_multiaddr_with_id(), discv5_bootstrap_node=self.node2.get_enr_uri())

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_filter_subscriptions({"requestId": "1", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic})

        # for e2e scenarios I think waiting for autoconnection is important instead of forcing connection via API calls
        # that's why the bellow code is commented to showcase this difference. In case we uncomment it, the connection will be faster
        # self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        # self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])
        self.wait_for_autoconnection([self.node1, self.node2, self.node3], hard_wait=30)

        # self.node1 relays and we check that self.node3 receives the message
        self.check_published_message_reaches_filter_peer(sender=self.node1, peer_list=[self.node3], message_propagation_delay=1)

    def test_store_node_not_connected_directly_to_relaying_node(self):
        self.node1.start(relay="true")
        self.node2.start(store="true", relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="false", storenode=self.node2.get_multiaddr_with_id(), discv5_bootstrap_node=self.node2.get_enr_uri())

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        # self.node1 relays and we check that self.node3 receives the message

        # for e2e scenarios I think waiting for autoconnection is important instead of forcing connection via API calls
        # that's why the bellow code is commented to showcase this difference. In case we uncomment it, the connection will be faster
        # self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        # self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])
        self.wait_for_autoconnection([self.node1, self.node2], hard_wait=30)

        self.publish_message(sender=self.node1)
        self.check_published_message_is_stored(page_size=50, ascending="true", store_node=self.node3)

    def test_relay_receiving_node_not_connected_directly_to_lightpushing_node(self):
        self.node1.start(lightpush="true", relay="true")
        self.node2.start(
            lightpush="true", relay="true", discv5_bootstrap_node=self.node1.get_enr_uri(), lightpushnode=self.node1.get_multiaddr_with_id()
        )
        self.node3.start(relay="true", discv5_bootstrap_node=self.node2.get_enr_uri())

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        # for e2e scenarios I think waiting for autoconnection is important instead of forcing connection via API calls
        # that's why the bellow code is commented to showcase this difference. In case we uncomment it, the connection will be faster
        # self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        # self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])
        self.wait_for_autoconnection([self.node1, self.node2, self.node3], hard_wait=30)

        # self.node1 light pushed and we check that self.node3 receives the message
        self.check_light_pushed_message_reaches_receiving_peer(sender=self.node1, peer_list=[self.node3])

    def test_filter_node_not_connected_directly_to_lightpushing_node(self):
        self.node1.start(lightpush="true")
        self.node2.start(
            lightpush="true",
            filter="true",
            relay="true",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
            lightpushnode=self.node1.get_multiaddr_with_id(),
        )
        self.node3.start(relay="false", filternode=self.node2.get_multiaddr_with_id(), discv5_bootstrap_node=self.node2.get_enr_uri())

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_filter_subscriptions({"requestId": "1", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic})

        # for e2e scenarios I think waiting for autoconnection is important instead of forcing connection via API calls
        # that's why the bellow code is commented to showcase this difference. In case we uncomment it, the connection will be faster
        # self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        # self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])
        self.wait_for_autoconnection([self.node1, self.node2, self.node3], hard_wait=30)

        # self.node1 light pushed and we check that self.node3 receives the message
        self.node1.send_light_push_message(self.create_payload())
        delay(1)
        get_messages_response = self.get_filter_messages(self.test_content_topic, pubsub_topic=self.test_pubsub_topic, node=self.node3)
        assert len(get_messages_response) == 1, f"Expected 1 message but got {len(get_messages_response)}"

    def test_store_node_not_connected_directly_to_lightpushing_node(self):
        self.node1.start(lightpush="true")
        self.node2.start(
            lightpush="true",
            store="true",
            relay="true",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
            lightpushnode=self.node1.get_multiaddr_with_id(),
        )
        self.node3.start(relay="false", storenode=self.node2.get_multiaddr_with_id(), discv5_bootstrap_node=self.node2.get_enr_uri())

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])

        # for e2e scenarios I think waiting for autoconnection is important instead of forcing connection via API calls
        # that's why the bellow code is commented to showcase this difference. In case we uncomment it, the connection will be faster
        # self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        # self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])
        self.wait_for_autoconnection([self.node1, self.node2], hard_wait=30)

        # self.node1 light pushed and we check that self.node3 receives the message
        message = self.create_message()
        self.node1.send_light_push_message(self.create_payload(message=message))
        delay(1)
        self.check_published_message_is_stored(page_size=50, ascending="true", store_node=self.node3, messages_to_check=[message])

    def test_chain_of_relay_nodes(self):
        self.node4 = WakuNode(NODE_2, f"node4_{self.test_id}")
        self.node5 = WakuNode(NODE_2, f"node5_{self.test_id}")
        self.node6 = WakuNode(NODE_2, f"node6_{self.test_id}")
        self.node7 = WakuNode(NODE_2, f"node7_{self.test_id}")
        self.node8 = WakuNode(NODE_2, f"node8_{self.test_id}")
        self.node9 = WakuNode(NODE_2, f"node9_{self.test_id}")
        self.node10 = WakuNode(NODE_2, f"node10_{self.test_id}")

        self.node1.start(relay="true")
        self.node2.start(relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="true", discv5_bootstrap_node=self.node2.get_enr_uri())
        self.node4.start(relay="true", discv5_bootstrap_node=self.node3.get_enr_uri())
        self.node5.start(relay="true", discv5_bootstrap_node=self.node4.get_enr_uri())
        self.node6.start(relay="true", discv5_bootstrap_node=self.node5.get_enr_uri())
        self.node7.start(relay="true", discv5_bootstrap_node=self.node6.get_enr_uri())
        self.node8.start(relay="true", discv5_bootstrap_node=self.node7.get_enr_uri())
        self.node9.start(relay="true", discv5_bootstrap_node=self.node8.get_enr_uri())
        self.node10.start(relay="true", discv5_bootstrap_node=self.node9.get_enr_uri())

        node_list = [self.node1, self.node2, self.node3, self.node4, self.node5, self.node6, self.node7, self.node8, self.node9, self.node10]
        for node in node_list:
            node.set_relay_subscriptions([self.test_pubsub_topic])

        self.wait_for_autoconnection(node_list, hard_wait=30)

        # self.node1 relays and we check that self.node10 receives the message
        self.check_published_message_reaches_relay_peer(sender=self.node1, peer_list=[self.node10], message_propagation_delay=1)

    @pytest.mark.timeout(60 * 7)
    def test_filter_20_senders_1_receiver(self):
        total_senders = 20
        node_list = []

        logger.debug(f"Start {total_senders} nodes to publish messages ")
        self.node1.start(relay="true")
        node_list.append(self.node1)
        for i in range(total_senders - 1):
            node_list.append(WakuNode(NODE_2, f"node{i + 1}_{self.test_id}"))
            delay(0.1)
            node_list[i + 1].start(relay="true", discv5_bootstrap_node=node_list[i].get_enr_uri())
            delay(3)

        logger.debug(f"Start filter node and subscribed filter node ")
        self.node21 = WakuNode(NODE_1, f"node21_{self.test_id}")
        self.node22 = WakuNode(NODE_1, f"node22_{self.test_id}")
        self.node21.start(relay="true", filter="true", store="false", discv5_bootstrap_node=node_list[total_senders - 1].get_enr_uri())
        self.node22.start(
            relay="false", filter="true", filternode=self.node21.get_multiaddr_with_id(), store="false", discv5_bootstrap_node=self.node21
        )

        node_list.append(self.node21)

        logger.debug(f"Subscribe nodes to relay  pubsub topic {self.test_pubsub_topic}")
        for node in node_list:
            node.set_relay_subscriptions([self.test_pubsub_topic])
        logger.debug(f"Node22 make filter request to pubsubtopic {self.test_pubsub_topic} and content topic  {self.test_content_topic}")
        self.node22.set_filter_subscriptions({"requestId": "1", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic})
        self.wait_for_autoconnection(node_list, hard_wait=80)

        logger.debug(f"{total_senders} Nodes publish {total_senders} messages")
        for node in node_list[:-1]:
            self.publish_message(sender=node, pubsub_topic=self.test_pubsub_topic, message=self.create_message())
            delay(1)

        logger.debug("Node 22 requests messages of subscribed filter topic")
        messages_response = self.get_filter_messages(self.test_content_topic, pubsub_topic=self.test_pubsub_topic, node=self.node22)

        logger.debug(f"Total number received messages for node 22 is {len(messages_response)}")
        assert len(messages_response) == total_senders, f"Received messages != published which is {total_senders} !!"

    @pytest.mark.timeout(60 * 7)
    def test_filter_3_senders_multiple_msg_1_receiver(self):
        messages_num = 12
        total_senders = 3
        self.node4 = WakuNode(NODE_1, f"node4_{self.test_id}")
        self.node5 = WakuNode(NODE_1, f"node5_{self.test_id}")
        node_list = []

        logger.debug("Start 5 nodes")
        self.node1.start(relay="true", store="false")
        self.node2.start(relay="true", store="false", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="true", store="false", filter="true", discv5_bootstrap_node=self.node2.get_enr_uri())
        self.node4.start(relay="true", filter="true", store="false", discv5_bootstrap_node=self.node3.get_enr_uri())
        self.node5.start(relay="false", filternode=self.node4.get_multiaddr_with_id(), store="false", discv5_bootstrap_node=self.node3.get_enr_uri())

        logger.debug(f"Subscribe nodes to relay  pubsub topic {self.test_pubsub_topic}")
        node_list = [self.node1, self.node2, self.node3, self.node4]
        for node in node_list:
            node.set_relay_subscriptions([self.test_pubsub_topic])

        logger.debug(f"Node5 makes filter request pubsubtopic {self.test_pubsub_topic} and content topic {self.test_content_topic}")
        self.node5.set_filter_subscriptions({"requestId": "1", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic})
        node_list.append(self.node5)
        self.wait_for_autoconnection(node_list, hard_wait=60)

        logger.debug(f" {total_senders} Nodes publish {messages_num} message")
        for node in node_list[:-2]:
            for i in range(messages_num // total_senders):
                self.publish_message(sender=node, pubsub_topic=self.test_pubsub_topic, message=self.create_message())
                delay(2)

        logger.debug(f"Node5 requests messages of subscribed filter topic {self.test_pubsub_topic}")
        messages_response = self.get_filter_messages(self.test_content_topic, pubsub_topic=self.test_pubsub_topic, node=self.node5)
        logger.debug(f"Response for node 5 is {messages_response}")
        assert len(messages_response) == messages_num, f"Received messages != published which is{messages_num} !!"

    @pytest.mark.timeout(60 * 5)
    def test_filter_many_subscribed_nodes(self):
        max_subscribed_nodes = 15
        if STRESS_ENABLED:
            max_subscribed_nodes = 50
        node_list = []
        response_list = []
        logger.debug("Start 2 nodes")
        self.node1.start(relay="true", store="false")
        self.node2.start(relay="true", filter="true", store="false", discv5_bootstrap_node=self.node1.get_enr_uri())

        logger.debug(f"Subscribe nodes to relay  pubsub topic {self.test_pubsub_topic}")
        node_list_relay = [self.node1, self.node2]
        for node in node_list_relay:
            node.set_relay_subscriptions([self.test_pubsub_topic])

        node_list.append(self.node2)
        logger.debug(f"{max_subscribed_nodes} Node start and making filter requests to node2")
        for i in range(max_subscribed_nodes):
            node_list.append(WakuNode(NODE_2, f"node{i+2}_{self.test_id}"))
            delay(0.1)
            node_list[i + 1].start(
                relay="false",
                filternode=self.node2.get_multiaddr_with_id(),
                discv5_bootstrap_node=node_list[i].get_enr_uri(),
                store="false",
            )
            delay(1)
            node_list[i + 1].set_filter_subscriptions(
                {"requestId": "1", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic}
            )
        self.wait_for_autoconnection(node_list_relay, hard_wait=100)

        logger.debug("Node1 publish message")
        self.publish_message(sender=self.node1, pubsub_topic=self.test_pubsub_topic, message=self.create_message())
        delay(4)

        logger.debug(f"{max_subscribed_nodes} Node requests the published message of subscribed filter topic")
        for i in range(max_subscribed_nodes):
            messages_response = self.get_filter_messages(self.test_content_topic, pubsub_topic=self.test_pubsub_topic, node=node_list[i + 1])
            logger.debug(f"Response for node {i+1} is {messages_response}")
            response_list.append(messages_response)

        assert len(response_list) == max_subscribed_nodes, "Received message count doesn't match sent "

    @pytest.mark.smoke
    def test_store_filter_interaction_with_six_nodes(self):
        logger.debug("Create  6 nodes")
        self.node4 = WakuNode(NODE_2, f"node4_{self.test_id}")
        self.node5 = WakuNode(NODE_2, f"node5_{self.test_id}")
        self.node6 = WakuNode(NODE_2, f"node6_{self.test_id}")

        logger.debug("Start 5 nodes with their corresponding config")
        self.node1.start(relay="true", store="true")
        self.node2.start(relay="true", store="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="true", store="true", discv5_bootstrap_node=self.node2.get_enr_uri())
        self.node4.start(relay="true", filter="true", store="true", discv5_bootstrap_node=self.node3.get_enr_uri())
        self.node6.start(relay="false", filternode=self.node4.get_multiaddr_with_id(), discv5_bootstrap_node=self.node4.get_enr_uri())

        logger.debug("Subscribe nodes to relay  pubsub topics")
        node_list = [self.node1, self.node2, self.node3, self.node4]
        for node in node_list:
            node.set_relay_subscriptions([self.test_pubsub_topic])

        logger.debug(f"Node6 subscribe to filter for pubsubtopic {self.test_pubsub_topic}")
        node_list.append(self.node6)
        self.node6.set_filter_subscriptions({"requestId": "1", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic})
        self.wait_for_autoconnection(node_list, hard_wait=50)

        logger.debug(f"Node1 publish message for topic {self.test_pubsub_topic}")
        message = self.create_message()
        self.publish_message(sender=self.node1, pubsub_topic=self.test_pubsub_topic, message=message)
        delay(4)

        logger.debug(f"Node6 inquery for filter messages on pubsubtopic {self.test_pubsub_topic} & contenttopic{self.test_content_topic}")
        messages_response = self.get_filter_messages(self.test_content_topic, pubsub_topic=self.test_pubsub_topic, node=self.node6)
        logger.debug(f"Filter inquiry response is {messages_response}")
        assert len(messages_response) == 1, f"filtered messages count doesn't match published messages"

        logger.debug("Node5 goes live !!")
        self.node5.start(relay="false", storenode=self.node4.get_multiaddr_with_id(), discv5_bootstrap_node=self.node4.get_enr_uri())
        delay(2)
        logger.debug("Node5 makes request to get stored messages ")
        self.check_published_message_is_stored(page_size=50, ascending="true", store_node=self.node5, messages_to_check=[message])

    def test_repeated_filter_requestID(self):
        logger.debug("Create 3 nodes")
        logger.debug("Start 3 nodes with their corresponding config")
        self.node1.start(relay="true", store="true")
        self.node2.start(relay="true", store="true", filter="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(
            relay="true",
            filternode=self.node2.get_multiaddr_with_id(),
            store="false",
            pubsub_topic=self.test_pubsub_topic,
            discv5_bootstrap_node=self.node2.get_enr_uri(),
        )

        logger.debug("Subscribe nodes to relay  pubsub topics")
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])

        logger.debug("Wait for all nodes auto connection")
        node_list = [self.node1, self.node2]
        self.wait_for_autoconnection(node_list, hard_wait=30)

        logger.debug(f"Node3 subscribe to filter for pubsubtopic  {self.test_pubsub_topic} 2 times with same request id")
        self.node3.set_filter_subscriptions({"requestId": "1", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic})
        try:
            self.node3.set_filter_subscriptions(
                {"requestId": "1", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic}
            )
        except Exception as e:
            logger.debug(f"Request ID not unique cause error str{e}")

        logger.debug(f"Node1 publish message for topic {self.test_pubsub_topic}")
        self.publish_message(sender=self.node1, pubsub_topic=self.test_pubsub_topic, message=self.create_message())
        delay(5)
        messages_response = self.get_filter_messages(self.test_content_topic, pubsub_topic=self.test_pubsub_topic, node=self.node3)
        logger.debug(f"Response for node 3 is {messages_response}")
        # This assert will be uncommented once know what is the expected behavior
        # assert len(messages_response) == 1, f"filtered messages count doesn't match published messages"
        messages_response = self.get_filter_messages(self.test_content_topic, pubsub_topic=self.test_pubsub_topic, node=self.node3)
        logger.debug(f"Response for node3 using same request ID is {messages_response}")
        # note: additional steps will be added to test the correct expected response on sending 2 requests with same ID

    def test_msg_not_stored_when_ephemeral_true(self):
        logger.debug("Start 3 nodes ")
        self.node1.start(relay="true", store="true")
        self.node2.start(store="true", relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="false", storenode=self.node2.get_multiaddr_with_id(), discv5_bootstrap_node=self.node2.get_enr_uri())

        logger.debug(f"Subscribe node1 ,2 to pubtopic {self.test_pubsub_topic}")
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.wait_for_autoconnection([self.node1, self.node2], hard_wait=30)

        logger.debug("Node1 publish message with flag ephemeral = True")
        message = self.create_message(ephemeral=True)
        self.publish_message(sender=self.node1, pubsub_topic=self.test_pubsub_topic, message=message)
        delay(3)
        try:
            logger.debug("Node3 makes store request to get messages")
            self.check_published_message_is_stored(page_size=50, ascending="true", store_node=self.node3, messages_to_check=[message])
            raise Exception("Messages shouldn't be stores when ephemeral = true")
        except Exception as e:
            logger.debug(f"Response for store when ephemeral = true is str{e}")
            assert e.args[0].find("'messages': []"), "response for store shouldn't contain messages"
            logger.debug("Message isn't stored as ephemeral = True")

    def test_msg_stored_when_ephemeral_false(self):
        logger.debug("Start 3 nodes")
        self.node1.start(relay="true", store="true")
        self.node2.start(store="true", relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="false", storenode=self.node2.get_multiaddr_with_id(), discv5_bootstrap_node=self.node2.get_enr_uri())

        logger.debug(f"Subscribe node1 ,2 to pubtopic {self.test_pubsub_topic}")
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.wait_for_autoconnection([self.node1, self.node2], hard_wait=30)

        logger.debug("Node1 publish message with ephemeral = false")
        message = self.create_message(ephemeral=False)
        self.publish_message(sender=self.node1, pubsub_topic=self.test_pubsub_topic, message=message)
        delay(3)
        logger.debug("Check if message is stored ")
        self.check_published_message_is_stored(page_size=50, ascending="true", store_node=self.node3, messages_to_check=[message])

    def test_multiple_edge_service_nodes_communication(self):
        self.edge_node1 = WakuNode(NODE_1, f"node4_{self.test_id}")
        self.edge_node2 = WakuNode(NODE_1, f"node5_{self.test_id}")
        self.service_node1 = WakuNode(NODE_2, f"node6_{self.test_id}")
        self.service_node2 = WakuNode(NODE_1, f"node7_{self.test_id}")
        self.service_node3 = WakuNode(NODE_2, f"node8_{self.test_id}")

        logger.debug("Start 2 edges nodes and 3 service nodes ")
        self.service_node1.start(relay="true", store="true", lightpush="true")
        self.edge_node1.start(
            relay="false", lightpushnode=self.service_node1.get_multiaddr_with_id(), discv5_bootstrap_node=self.service_node1.get_enr_uri()
        )
        self.service_node2.start(relay="true", store="true", discv5_bootstrap_node=self.service_node1.get_enr_uri())  # service node2
        self.service_node3.start(
            relay="true", filter="true", storenode=self.service_node2.get_multiaddr_with_id(), discv5_bootstrap_node=self.service_node2.get_enr_uri()
        )
        self.edge_node2.start(
            relay="false",
            filternode=self.service_node3.get_multiaddr_with_id(),
            storenode=self.service_node2.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.service_node2.get_enr_uri(),
        )  # edge node2

        logger.debug("Connect 3 service nodes to relay subscriptions")
        self.service_node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.service_node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.service_node3.set_relay_subscriptions([self.test_pubsub_topic])
        self.wait_for_autoconnection([self.service_node1, self.service_node2, self.service_node3], hard_wait=30)

        logger.debug(f"Edge node2 makes filter subscription to pubsubtopic {self.test_pubsub_topic} and content topic {self.test_content_topic}")
        self.edge_node2.set_filter_subscriptions(
            {"requestId": "1", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic}
        )

        logger.debug("Check if service node1 receives message sent by edge node1")
        message = self.create_message()
        self.check_light_pushed_message_reaches_receiving_peer(sender=self.edge_node1, peer_list=[self.service_node1], message=message)

        logger.debug("Check if edge node2 can query stored message")
        self.check_published_message_is_stored(page_size=50, ascending="true", store_node=self.edge_node2, messages_to_check=[message])

        logger.debug("Check if service node3 can query stored message")
        self.check_published_message_is_stored(page_size=50, ascending="true", store_node=self.service_node3, messages_to_check=[message])

        logger.debug("Check if edge node2 can get sent message using filter get request ")
        messages_response = self.get_filter_messages(self.test_content_topic, pubsub_topic=self.test_pubsub_topic, node=self.edge_node2)
        assert len(messages_response) == 1, "message counter isn't as expected "

    def test_store_no_peer_selected(self):
        store_version = "v3"
        logger.debug("Start 5 nodes")
        self.node4 = WakuNode(NODE_2, f"node3_{self.test_id}")
        self.node5 = WakuNode(NODE_2, f"node4_{self.test_id}")
        self.node6 = WakuNode(NODE_2, f"node5_{self.test_id}")
        self.node1.start(relay="true", store="true")
        self.node2.start(store="false", relay="false", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(relay="false", discv5_bootstrap_node=self.node2.get_enr_uri())
        self.node4.start(relay="true", store="false", discv5_bootstrap_node=self.node3.get_enr_uri())
        self.node5.start(relay="false", store="false", discv5_bootstrap_node=self.node4.get_enr_uri())

        logger.debug("Add 3 peer nodes to node3")
        self.multiaddr_with_id = self.node1.get_multiaddr_with_id()
        self.add_node_peer(self.node3, [self.multiaddr_with_id])
        self.multiaddr_with_id = self.node2.get_multiaddr_with_id()
        self.add_node_peer(self.node3, [self.multiaddr_with_id])
        self.multiaddr_with_id = self.node4.get_multiaddr_with_id()
        self.add_node_peer(self.node3, [self.node4.get_multiaddr_with_id()])

        logger.debug(f"Subscribe nodes 1,2 to relay on pubsubtopic {self.test_pubsub_topic}")
        self.node4.set_relay_subscriptions([self.test_pubsub_topic])
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.wait_for_autoconnection([self.node1, self.node4], hard_wait=30)

        logger.debug("Node1 publish message")
        self.publish_message(sender=self.node4)
        logger.debug("Check if node3 can inquiry stored message without stor peer specified")
        store_response = self.node3.get_store_messages(
            pubsub_topic=self.test_pubsub_topic, content_topics=self.test_content_topic, page_size=5, ascending="true", store_v=store_version
        )
        assert len(store_response["messages"]) == 1, "Can't find stored message!!"

        logger.debug("Repeat publish and store inquiry but using store v1")
        store_version = "v1"
        self.publish_message(sender=self.node4)

        logger.debug("Check if node3 can inquiry stored message without stor peer specified")
        store_response = self.node3.get_store_messages(pubsub_topic=self.test_pubsub_topic, page_size=5, ascending="true", store_v=store_version)
        assert len(store_response["messages"]) == 2, "Can't find stored message!!"

    def test_sync_trail(self):
        self.node1.start(store="true", relay="true", sync="true")
        self.node2.start(store="true", relay="false", discv5_bootstrap_node=self.node1.get_enr_uri())
        # ogger.debug(f"publish mesage via store { self.publish_message(sender=self.node1,via ="sync")} ")

        # logger.debug(f"return of sync request {self.node2.request_sync(self)}")

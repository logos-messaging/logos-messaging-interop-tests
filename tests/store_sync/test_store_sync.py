import pytest
from src.env_vars import NODE_1, NODE_2
from src.libs.common import delay, to_base64
from src.libs.custom_logger import get_custom_logger
from src.node.store_response import StoreResponse
from src.node.waku_node import WakuNode
from src.steps.store import StepsStore

logger = get_custom_logger(__name__)

"""
In those tests we aim to combine multiple protocols/node types and create a more end-to-end scenario
"""


class TestStoreSync(StepsStore):
    @pytest.fixture(scope="function", autouse=True)
    def nodes(self):
        self.node1 = WakuNode(NODE_1, f"node1_{self.test_id}")
        self.node2 = WakuNode(NODE_1, f"node2_{self.test_id}")
        self.node3 = WakuNode(NODE_1, f"node3_{self.test_id}")
        self.num_messages = 10

    def test_sync_nodes_are_relay(self):
        self.node1.start(store="true", relay="true")
        self.node2.start(store="false", store_sync="true", relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(store="false", store_sync="true", relay="true", discv5_bootstrap_node=self.node2.get_enr_uri())

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        message_list = [self.publish_message(sender=self.node1, via="relay") for _ in range(self.num_messages)]

        delay(2)  # wait for the sync to finish

        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node1, messages_to_check=message_list)
        node1_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=message_list)
        node2_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=message_list)
        node3_message = len(self.store_response.messages)

        assert (
            node1_message == node2_message == node3_message == self.num_messages
        ), f"Store messages are not equal to each other or not equal to {self.num_messages}"

    def test_sync_nodes_have_store_true(self):
        self.node1.start(store="true", relay="true")
        self.node2.start(store="true", store_sync="true", relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(store="true", store_sync="true", relay="true", discv5_bootstrap_node=self.node2.get_enr_uri())

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        message_list = [self.publish_message(sender=self.node1, via="relay") for _ in range(self.num_messages)]

        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node1, messages_to_check=message_list)
        node1_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=message_list)
        node2_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=message_list)
        node3_message = len(self.store_response.messages)

        assert (
            node1_message == node2_message == node3_message == self.num_messages
        ), f"Store messages are not equal to each other or not equal to {self.num_messages}"

    def test_sync_nodes_are_not_relay_and_have_storenode_set(self):
        self.node1.start(store="true", relay="true")
        self.node2.start(
            store="false",
            store_sync="true",
            relay="false",
            storenode=self.node1.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.node3.start(
            store="false",
            store_sync="true",
            relay="false",
            storenode=self.node1.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node2.get_enr_uri(),
        )

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])

        message_list = [self.publish_message(sender=self.node1, via="relay") for _ in range(self.num_messages)]

        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node1, messages_to_check=message_list)
        node1_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=message_list)
        node2_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=message_list)
        node3_message = len(self.store_response.messages)

        assert (
            node1_message == node2_message == node3_message == self.num_messages
        ), f"Store messages are not equal to each other or not equal to {self.num_messages}"

    def test_sync_messages_received_via_lightpush(self):
        self.node1.start(store="true", store_sync="true", relay="true", lightpush="true")
        self.node2.start(
            store="true",
            store_sync="true",
            relay="true",
            lightpush="true",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
            lightpushnode=self.node1.get_multiaddr_with_id(),
        )
        self.node3.start(
            store="true",
            store_sync="true",
            relay="true",
            storenode=self.node2.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node2.get_enr_uri(),
        )

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        message_list = [self.publish_message(sender=self.node1, via="lightpush") for _ in range(self.num_messages)]

        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node1, messages_to_check=message_list)
        node1_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=message_list)
        node2_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=message_list)
        node3_message = len(self.store_response.messages)

        assert (
            node1_message == node2_message == node3_message == self.num_messages
        ), f"Store messages are not equal to each other or not equal to {self.num_messages}"

    def test_check_sync_when_2_nodes_publish(self):
        self.node1.start(store="true", store_sync="true", relay="true")
        self.node2.start(
            store="true",
            store_sync="true",
            relay="true",
            storenode=self.node1.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.node3.start(
            store="false",
            store_sync="true",
            relay="false",
            storenode=self.node2.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node2.get_enr_uri(),
        )

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])

        ml1 = [self.publish_message(sender=self.node1, via="relay", message_propagation_delay=0.01) for _ in range(self.num_messages)]
        ml2 = [self.publish_message(sender=self.node2, via="relay", message_propagation_delay=0.01) for _ in range(self.num_messages)]

        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node1, messages_to_check=ml1 + ml2)
        node1_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=ml1 + ml2)
        node2_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=ml1 + ml2)
        node3_message = len(self.store_response.messages)

        assert (
            node1_message == node2_message == node3_message == self.num_messages * 2
        ), f"Store messages are not equal to each other or not equal to {self.num_messages * 2}"

    def test_check_sync_when_all_3_nodes_publish(self):
        self.node1.start(store="true", store_sync="true", relay="true")
        self.node2.start(
            store="true",
            store_sync="true",
            relay="true",
            storenode=self.node1.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.node3.start(
            store="false",
            store_sync="true",
            relay="true",
            storenode=self.node2.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node2.get_enr_uri(),
        )

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        ml1 = [self.publish_message(sender=self.node1, via="relay", message_propagation_delay=0.01) for _ in range(self.num_messages)]
        ml2 = [self.publish_message(sender=self.node2, via="relay", message_propagation_delay=0.01) for _ in range(self.num_messages)]
        ml3 = [self.publish_message(sender=self.node3, via="relay", message_propagation_delay=0.01) for _ in range(self.num_messages)]

        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node1, messages_to_check=ml1 + ml2 + ml3)
        node1_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=ml1 + ml2 + ml3)
        node2_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=ml1 + ml2 + ml3)
        node3_message = len(self.store_response.messages)

        assert (
            node1_message == node2_message == node3_message == self.num_messages * 3
        ), f"Store messages are not equal to each other or not equal to {self.num_messages * 3}"

    #########################################################

    def test_sync_with_one_node_with_delayed_start(self):
        self.node1.start(store="true", store_sync="true", relay="true")
        self.node2.start(
            store="true",
            store_sync="true",
            relay="true",
            storenode=self.node1.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])

        message_list = [self.publish_message(sender=self.node1, via="relay") for _ in range(self.num_messages)]

        # start the 3rd node
        self.node3.start(
            store="false",
            store_sync="true",
            relay="true",
            storenode=self.node2.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node2.get_enr_uri(),
        )
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        delay(1)  # wait for the sync to finish

        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node1, messages_to_check=message_list)
        node1_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=message_list)
        node2_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=message_list)
        node3_message = len(self.store_response.messages)

        assert (
            node1_message == node2_message == node3_message == self.num_messages
        ), f"Store messages are not equal to each other or not equal to {self.num_messages}"

    def test_sync_with_nodes_restart__case1(self):
        self.node1.start(store="true", store_sync="true", relay="true")
        self.node2.start(
            store="true",
            store_sync="true",
            relay="true",
            storenode=self.node1.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.node3.start(
            store="false",
            store_sync="true",
            relay="true",
            storenode=self.node2.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node2.get_enr_uri(),
        )

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        ml1 = [self.publish_message(sender=self.node1, via="relay", message_propagation_delay=0.01) for _ in range(self.num_messages)]
        ml2 = [self.publish_message(sender=self.node2, via="relay", message_propagation_delay=0.01) for _ in range(self.num_messages)]
        ml3 = [self.publish_message(sender=self.node3, via="relay", message_propagation_delay=0.01) for _ in range(self.num_messages)]

        self.node1.restart()
        self.node2.restart()
        self.node3.restart()

        delay(2)  # wait for the sync to finish

        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node1, messages_to_check=ml1 + ml2 + ml3)
        node1_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=ml1 + ml2 + ml3)
        node2_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=ml1 + ml2 + ml3)
        node3_message = len(self.store_response.messages)

        assert (
            node1_message == node2_message == node3_message == self.num_messages * 3
        ), f"Store messages are not equal to each other or not equal to {self.num_messages * 3}"

    def test_sync_with_nodes_restart__case2(self):
        self.node1.start(store="true", relay="true")
        self.node2.start(store="false", store_sync="true", relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(store="false", store_sync="true", relay="true", discv5_bootstrap_node=self.node2.get_enr_uri())

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        ml1 = [self.publish_message(sender=self.node1, via="relay", message_propagation_delay=0.01) for _ in range(self.num_messages)]
        ml2 = [self.publish_message(sender=self.node2, via="relay", message_propagation_delay=0.01) for _ in range(self.num_messages)]
        ml3 = [self.publish_message(sender=self.node3, via="relay", message_propagation_delay=0.01) for _ in range(self.num_messages)]

        self.node2.restart()

        delay(5)  # wait for the sync to finish

        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node1, messages_to_check=ml1 + ml2 + ml3)
        node1_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=ml1 + ml2 + ml3)
        node2_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=ml1 + ml2 + ml3)
        node3_message = len(self.store_response.messages)

        assert (
            node1_message == node2_message == node3_message == self.num_messages * 3
        ), f"Store messages are not equal to each other or not equal to {self.num_messages * 3}"

    def test_high_message_volume_sync(self):
        self.node1.start(store="true", store_sync="true", relay="true")
        self.node2.start(
            store="true",
            store_sync="true",
            relay="true",
            storenode=self.node1.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.node3.start(
            store="false",
            store_sync="true",
            relay="true",
            storenode=self.node2.get_multiaddr_with_id(),
            discv5_bootstrap_node=self.node2.get_enr_uri(),
        )

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        expected_message_hash_list = {"nwaku": []}

        for _ in range(500):  # total 1500 messages
            messages = [self.create_message() for _ in range(3)]

            for i, node in enumerate([self.node1, self.node2, self.node3]):
                self.publish_message(sender=node, via="relay", message=messages[i], message_propagation_delay=0.01)

            expected_message_hash_list["nwaku"].extend([self.compute_message_hash(self.test_pubsub_topic, msg, hash_type="hex") for msg in messages])

        delay(5)  # wait for the sync to finish

        for node in [self.node1, self.node2, self.node3]:
            store_response = StoreResponse({"paginationCursor": "", "pagination_cursor": ""}, node)
            response_message_hash_list = []
            while store_response.pagination_cursor is not None:
                cursor = store_response.pagination_cursor
                store_response = self.get_messages_from_store(node, page_size=100, cursor=cursor)
                for index in range(len(store_response.messages)):
                    response_message_hash_list.append(store_response.message_hash(index))
            assert len(expected_message_hash_list[node.type()]) == len(response_message_hash_list), "Message count mismatch"
            assert expected_message_hash_list[node.type()] == response_message_hash_list, "Message hash mismatch"

    def test_large_message_payload_sync(self):
        self.node1.start(store="true", relay="true")
        self.node2.start(store="false", store_sync="true", relay="true", discv5_bootstrap_node=self.node1.get_enr_uri())
        self.node3.start(store="false", store_sync="true", relay="true", discv5_bootstrap_node=self.node2.get_enr_uri())

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        payload_length = 1024 * 100  # after encoding to base64 this will be close to 150KB

        ml1 = [
            self.publish_message(
                sender=self.node1, via="relay", message=self.create_message(payload=to_base64("a" * (payload_length))), message_propagation_delay=0.01
            )
            for _ in range(self.num_messages)
        ]
        ml2 = [
            self.publish_message(
                sender=self.node2, via="relay", message=self.create_message(payload=to_base64("a" * (payload_length))), message_propagation_delay=0.01
            )
            for _ in range(self.num_messages)
        ]
        ml3 = [
            self.publish_message(
                sender=self.node3, via="relay", message=self.create_message(payload=to_base64("a" * (payload_length))), message_propagation_delay=0.01
            )
            for _ in range(self.num_messages)
        ]

        delay(10)  # wait for the sync to finish

        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node1, messages_to_check=ml1 + ml2 + ml3)
        node1_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=ml1 + ml2 + ml3)
        node2_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=ml1 + ml2 + ml3)
        node3_message = len(self.store_response.messages)

        assert (
            node1_message == node2_message == node3_message == self.num_messages * 3
        ), f"Store messages are not equal to each other or not equal to {self.num_messages * 3}"

    def test_sync_flags(self):
        self.node1.start(
            store="true",
            store_sync="true",
            store_sync_interval=1,
            store_sync_range=10,
            store_sync_relay_jitter=1,
            relay="true",
        )
        self.node2.start(
            store="false",
            store_sync="true",
            store_sync_interval=1,
            store_sync_range=10,
            store_sync_relay_jitter=1,
            relay="true",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.node3.start(
            store="false",
            store_sync="true",
            store_sync_interval=1,
            store_sync_range=10,
            store_sync_relay_jitter=1,
            relay="true",
            discv5_bootstrap_node=self.node2.get_enr_uri(),
        )

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.add_node_peer(self.node3, [self.node2.get_multiaddr_with_id()])

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])
        self.node2.set_relay_subscriptions([self.test_pubsub_topic])
        self.node3.set_relay_subscriptions([self.test_pubsub_topic])

        message_list = [self.publish_message(sender=self.node1, via="relay") for _ in range(self.num_messages)]

        delay(2)  # wait for the sync to finish

        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node1, messages_to_check=message_list)
        node1_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=message_list)
        node2_message = len(self.store_response.messages)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=message_list)
        node3_message = len(self.store_response.messages)

        assert (
            node1_message == node2_message == node3_message == self.num_messages
        ), f"Store messages are not equal to each other or not equal to {self.num_messages}"

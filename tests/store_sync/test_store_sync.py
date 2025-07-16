import pytest
from src.env_vars import NODE_1, NODE_2
from src.libs.common import delay, to_base64
from src.libs.custom_logger import get_custom_logger
from src.node.store_response import StoreResponse
from src.node.waku_node import WakuNode
from src.steps.store import StepsStore
import time

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

    @pytest.mark.skip("This test doesn not work as expected, will be fixed by @aya")
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

    def test_sync_flags_no_relay_2nodes(self):
        self.node1.start(
            store="true",
            store_sync="true",
            store_sync_interval=10,
            store_sync_range=45,
            store_sync_relay_jitter=0,
            relay="true",
        )
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])

        self.node2.start(
            store="true",
            store_sync="true",
            store_sync_interval=10,
            store_sync_range=45,
            store_sync_relay_jitter=0,
            relay="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        delay(1)

        message_list = [self.publish_message(sender=self.node1, via="relay") for _ in range(self.num_messages)]

        delay(20)  # wait for the sync to finish
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=message_list)

    def test_sync_flags_node2_start_later(self):
        self.node1.start(
            store="true",
            store_sync="true",
            store_sync_interval=10,
            store_sync_range=45,
            store_sync_relay_jitter=0,
            relay="true",
        )
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])

        message_list = [self.publish_message(sender=self.node1, via="relay") for _ in range(self.num_messages)]
        delay(1)
        self.node2.start(
            store="true",
            store_sync="true",
            store_sync_interval=10,
            store_sync_range=45,
            store_sync_relay_jitter=0,
            relay="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])

        delay(65)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node2, messages_to_check=message_list)

    def test_store_sync_indirect_node(self):
        self.node1.start(
            store="true",
            store_sync="true",
            store_sync_interval=10,
            store_sync_range=45,
            store_sync_relay_jitter=0,
            relay="true",
        )
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])

        self.node2.start(
            store="true",
            store_sync="true",
            store_sync_interval=10,
            store_sync_range=45,
            store_sync_relay_jitter=0,
            relay="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )

        self.node3.start(
            store="true",
            store_sync="true",
            store_sync_interval=10,
            store_sync_range=45,
            store_sync_relay_jitter=0,
            relay="false",
            dns_discovery="false",
            discv5_bootstrap_node=self.node2.get_enr_uri(),
        )
        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        message_list = [self.publish_message(sender=self.node1, via="relay") for _ in range(self.num_messages)]
        delay(65)
        self.check_published_message_is_stored(page_size=100, ascending="true", store_node=self.node3, messages_to_check=message_list)

    def test_store_sync_long_chain(self):
        sync_interval = 10
        sync_range = 120
        self.node1.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=0,
            relay="true",
            dns_discovery="false",
        )

        self.node1.set_relay_subscriptions([self.test_pubsub_topic])

        self.node4 = WakuNode(NODE_2, f"node4_{self.test_id}")
        self.node5 = WakuNode(NODE_2, f"node5_{self.test_id}")
        self.node6 = WakuNode(NODE_2, f"node6_{self.test_id}")
        self.node7 = WakuNode(NODE_2, f"node7_{self.test_id}")
        self.node8 = WakuNode(NODE_2, f"node8_{self.test_id}")

        extra_nodes = [
            self.node2,
            self.node3,
            self.node4,
            self.node5,
            self.node6,
            self.node7,
            self.node8,
        ]
        prev = self.node1
        for node in extra_nodes:
            node.start(
                store="true",
                store_sync="true",
                store_sync_interval=sync_interval,
                store_sync_range=sync_range,
                store_sync_relay_jitter=0,
                relay="false",
                dns_discovery="false",
            )

            self.add_node_peer(node, [prev.get_multiaddr_with_id()])
            prev = node

        published = [self.publish_message(sender=self.node1, via="relay") for _ in range(self.num_messages)]
        delay(sync_interval * 7 + 20)
        self.check_published_message_is_stored(
            page_size=100,
            ascending="true",
            store_node=self.node8,
            messages_to_check=published,
        )

    def test_store_sync_overlap_sync_window(self):
        sync_interval = 15
        sync_range = 45
        intervals = 6
        publish_secs = sync_interval * intervals

        self.node1.start(relay="true", store="true", store_sync="true", dns_discovery="false")

        self.node2.start(
            relay="false",
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=0,
            dns_discovery="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])

        logger.debug(f"Publishing {publish_secs} messages at 1 msg/s")
        published_hashes = []
        for i in range(publish_secs):
            msg = self.publish_message(sender=self.node1, via="relay")
            published_hashes.append(self.compute_message_hash(self.test_pubsub_topic, msg, hash_type="hex"))
            delay(0.8)

        logger.debug(f"Waiting {sync_interval * 2} seconds to allow at least two sync rounds")
        delay(sync_interval * 2)

        logger.debug("Querying node2 store for all messages")
        resp = self.get_messages_from_store(self.node2, page_size=2000, ascending="true")
        store_hashes = [resp.message_hash(i) for i in range(len(resp.messages))]

        logger.debug(f"Store returned {len(store_hashes)} messages, published publish_secs" f" messages")

        assert len(set(store_hashes)) == publish_secs
        assert set(store_hashes) == set(published_hashes)

    @pytest.mark.timeout(60 * 20)
    def test_query_after_long_time(self):
        sync_range = 150
        backlog_secs = 10 * 60
        publish_delay = 0.8
        sync_interval = 10

        self.node1.start(store="true", relay="true", store_sync="true", dns_discovery="false")
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])

        logger.debug(f"Publishing {backlog_secs} messages at 1 msg/s to build backlog")
        published_hashes = []
        for _ in range(backlog_secs):
            msg = self.publish_message(sender=self.node1, via="relay")
            published_hashes.append(self.compute_message_hash(self.test_pubsub_topic, msg, hash_type="hex"))
            delay(publish_delay)

        expected_hashes = published_hashes[-sync_range:]

        self.node2.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=0,
            relay="false",
            dns_discovery="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])

        logger.debug(f"Waiting {sync_interval * 2} s to let Node B finish its first sync")
        delay(sync_interval * 4)

        store_response = StoreResponse({"paginationCursor": "", "pagination_cursor": ""}, self.node2)
        store_hashes = []
        while store_response.pagination_cursor is not None:
            cursor = store_response.pagination_cursor
            store_response = self.get_messages_from_store(self.node2, page_size=100, cursor=cursor, ascending="true")
            for idx in range(len(store_response.messages)):
                store_hashes.append(store_response.message_hash(idx))

        logger.debug(f"Store returned {len(store_hashes)} messages; expected range {len(expected_hashes) - 20} : {len(expected_hashes)}")
        assert len(expected_hashes) >= len(store_hashes) > len(expected_hashes) - 20, "Incorrect number of messages synced"

    @pytest.mark.timeout(60 * 3)
    def test_store_sync_after_partition_under_100_msgs(self):
        sync_interval = 10
        sync_range = 180
        node2up_secs = 20
        node2down_secs = 60
        publish_delay = 0.8
        total_expected = node2up_secs + node2down_secs

        self.node1.start(store="true", relay="true", store_sync="true", dns_discovery="false")
        self.node2.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=0,
            relay="false",
            dns_discovery="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])

        published_hashes = []
        for _ in range(node2up_secs):
            m = self.publish_message(sender=self.node1, via="relay")
            published_hashes.append(self.compute_message_hash(self.test_pubsub_topic, m, hash_type="hex"))
            delay(publish_delay)

        logger.debug("Pausing Node2 container ")
        self.node2.pause()

        logger.debug("Publishing while node2 paused ")
        for _ in range(node2down_secs):
            m = self.publish_message(sender=self.node1, via="relay")
            published_hashes.append(self.compute_message_hash(self.test_pubsub_topic, m, hash_type="hex"))
            delay(publish_delay)

        logger.debug("Unpausing Node2")
        self.node2.unpause()
        delay(sync_interval * 2)

        resp = self.get_messages_from_store(self.node2, ascending="true", page_size=100)
        store_hashes = [resp.message_hash(i) for i in range(len(resp.messages))]

        logger.debug(f"Node2 store has {len(store_hashes)} messages; expected {total_expected}")
        assert len(store_hashes) == total_expected, "Message count mismatch after partition"
        assert set(store_hashes) == set(published_hashes), "Missing or extra messages after sync"

    def test_store_sync_small_sync_range(self):
        sync_interval = 10
        sync_range = 20
        jitter = 0
        backlog_wait = 60
        publish_count = 3

        self.node1.start(
            store="true",
            store_sync="true",
            relay="true",
            dns_discovery="false",
        )
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])

        for _ in range(publish_count):
            self.publish_message(sender=self.node1, via="relay")

        time.sleep(backlog_wait)

        self.node2.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=jitter,
            relay="false",  # ensure no gossip path
            dns_discovery="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])

        time.sleep(sync_interval * 2)

        resp = self.get_messages_from_store(
            self.node2,
            page_size=100,
            cursor="",
            ascending="true",
        )
        logger.debug("Node-2 local store returned %d messages; expected 0", len(resp.messages))
        assert len(resp.messages) == 0, "Store-Sync unexpectedly fetched messages older than the configured window"

    def test_store_sync_range_with_jitter_catches_old_messages(self):
        sync_interval = 5
        sync_range = 20
        jitter = 25
        backlog_wait = 25
        publish_count = 3

        self.node1.start(store="true", store_sync="true", relay="true", dns_discovery="false")
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])

        for _ in range(publish_count):
            self.publish_message(sender=self.node1, via="relay")

        time.sleep(backlog_wait)
        self.node2.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=jitter,
            relay="false",
            dns_discovery="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])

        time.sleep(sync_interval * 2)

        resp = self.get_messages_from_store(self.node2, page_size=100, cursor="", ascending="true")

        assert len(resp.messages) == publish_count

    def test_store_sync_range_with_zero_jitter(self):
        sync_interval = 5
        sync_range = 20
        jitter = 0
        backlog_wait = 25
        publish_count = 3

        self.node1.start(store="true", store_sync="true", relay="true", dns_discovery="false")
        self.node1.set_relay_subscriptions([self.test_pubsub_topic])

        for _ in range(publish_count):
            self.publish_message(sender=self.node1, via="relay")

        time.sleep(backlog_wait)
        self.node2.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=jitter,
            relay="false",
            dns_discovery="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])

        time.sleep(sync_interval * 2)

        resp = self.get_messages_from_store(self.node2, page_size=100, cursor="", ascending="true")

        assert len(resp.messages) == 0

    def test_three_store_sync_exchange(self):
        msgs_per_node = 20
        total_expected = msgs_per_node * 3
        sync_interval = 6
        sync_range = 600
        jitter = 0
        publish_delay = 0.01
        wait_cycles = 3

        self.node1.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=jitter,
            relay="true",
            dns_discovery="false",
        )

        for _ in range(msgs_per_node):
            self.publish_message(sender=self.node1, via="relay")
            time.sleep(publish_delay)

        self.node2.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=jitter,
            relay="true",
            dns_discovery="false",
        )

        for _ in range(msgs_per_node):
            self.publish_message(sender=self.node2, via="relay")
            time.sleep(publish_delay)

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])
        self.node3.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=jitter,
            relay="true",
            dns_discovery="false",
        )
        for _ in range(msgs_per_node):
            self.publish_message(sender=self.node3, via="relay")
            time.sleep(publish_delay)

        self.add_node_peer(
            self.node3,
            [self.node1.get_multiaddr_with_id(), self.node2.get_multiaddr_with_id()],
        )

        time.sleep(sync_interval * wait_cycles)
        resp_A = self.get_messages_from_store(self.node1, page_size=200, cursor="", ascending="true", peer_id="")
        logger.debug("Node-A store has %d messages", len(resp_A.messages))
        assert len(resp_A.messages) == total_expected, f" For Node A expected {total_expected}, got {len(resp_A.messages)}"

        resp_B = self.get_messages_from_store(self.node2, page_size=200, cursor="", ascending="true", peer_id="")
        logger.debug("Node-B store has %d messages", len(resp_B.messages))
        assert len(resp_B.messages) == total_expected, f"expected {total_expected}, got {len(resp_B.messages)}"
        resp_C = self.get_messages_from_store(self.node3, page_size=200, cursor="", ascending="true", peer_id="")
        logger.debug("Node-C store has %d messages", len(resp_C.messages))
        assert len(resp_C.messages) == total_expected, f"expected {total_expected}, got {len(resp_C.messages)}"

    @pytest.mark.timeout(240)
    def test_node_without_sync_or_relay_stays_empty(self):
        msgs_to_publish = 30
        sync_interval = 6
        sync_range = 300
        jitter = 0
        publish_delay = 0.01
        wait_cycles = 3
        topic = self.test_pubsub_topic

        self.node1.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=jitter,
            relay="true",
            dns_discovery="false",
        )
        for _ in range(msgs_to_publish):
            self.publish_message(sender=self.node1, via="relay")
            time.sleep(publish_delay)

        self.node2.start(
            # store="false",
            store_sync="false",
            relay="false",
            dns_discovery="false",
            # discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        # self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])

        self.node3.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=jitter,
            relay="false",
            dns_discovery="false",
            discv5_bootstrap_node=self.node1.get_enr_uri(),
        )
        self.add_node_peer(self.node3, [self.node1.get_multiaddr_with_id()])

        time.sleep(sync_interval * wait_cycles)

        resp2 = self.get_messages_from_store(self.node2, page_size=200, cursor="", ascending="true", peer_id="")
        logger.debug("Node2 store has %d messages expected 0", len(resp2.messages))
        assert len(resp2.messages) == 0, "Node2 unexpectedly received messages"

        resp3 = self.get_messages_from_store(self.node3, page_size=200, cursor="", ascending="true", peer_id="")
        logger.debug("Node3 store has %d messages expected %d", len(resp3.messages), msgs_to_publish)
        assert len(resp3.messages) == msgs_to_publish, f"Node3 store mismatch: expected {msgs_to_publish}, " f"got {len(resp3.messages)}"

    def test_continuous_store_sync(self):
        msgs_per_round = 30
        rounds = 3
        sleep_between_rounds = 30
        publish_delay = 0.01
        sync_interval = 6
        sync_range = 600
        jitter = 0

        self.node1.start(
            store="true",
            store_sync="true",
            relay="true",
            dns_discovery="false",
        )

        self.node2.start(
            store="true",
            store_sync="true",
            store_sync_interval=sync_interval,
            store_sync_range=sync_range,
            store_sync_relay_jitter=jitter,
            relay="false",
            dns_discovery="false",
        )

        self.add_node_peer(self.node2, [self.node1.get_multiaddr_with_id()])

        total_published = 0
        for _ in range(rounds):
            for _ in range(msgs_per_round):
                self.publish_message(sender=self.node1, via="relay")
                total_published += 1
                time.sleep(publish_delay)

            time.sleep(sync_interval * 2)

            resp = self.get_messages_from_store(
                self.node2,
                page_size=100,
                cursor="",
                ascending="true",
                peer_id="",
            )
            logger.debug(f"Node-2 store has {len(resp.messages)}/{total_published} messages")
            assert len(resp.messages) == total_published, f"expected {total_published}, got {len(resp.messages)}"

            time.sleep(sleep_between_rounds)

    def test_store_sync_high_jitter_stress(self):
        sync_interval = 10
        sync_range = 120
        jitter = 90
        msgs_per_node = 50
        message_delay = 0.0
        page_size = 100

        nodes = [self.node1, self.node2, self.node3]

        for n in nodes:
            n.start(
                store="true",
                store_sync="true",
                store_sync_interval=sync_interval,
                store_sync_range=sync_range,
                store_sync_relay_jitter=jitter,
                relay="true",
                dns_discovery="false",
            )
            n.set_relay_subscriptions([self.test_pubsub_topic])

        for i, a in enumerate(nodes):
            for b in nodes[i + 1 :]:
                self.add_node_peer(a, [b.get_multiaddr_with_id()])
                self.add_node_peer(b, [a.get_multiaddr_with_id()])

        expected_hashes = []
        for _ in range(msgs_per_node):
            msgs = [self.create_message() for _ in nodes]
            for node, msg in zip(nodes, msgs):
                self.publish_message(
                    sender=node,
                    via="relay",
                    message=msg,
                    message_propagation_delay=message_delay,
                )
                expected_hashes.append(self.compute_message_hash(self.test_pubsub_topic, msg, hash_type="hex"))

        delay(120)

        for node in nodes:
            store_resp = self.get_messages_from_store(node, page_size=page_size, ascending="true")
            retrieved_hashes = [store_resp.message_hash(i) for i in range(len(store_resp.messages))]
            assert len(retrieved_hashes) == len(expected_hashes), " message count mismatch"
            assert retrieved_hashes == expected_hashes, "{ message hash mismatch"

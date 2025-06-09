import pytest
from src.libs.custom_logger import get_custom_logger
from src.libs.common import delay
from src.steps.store import StepsStore

logger = get_custom_logger(__name__)


class TestReliability(StepsStore):
    def test_publishing_node_is_stopped(self, node_setup):
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        self.publishing_node1.stop()
        try:
            store_response = self.get_messages_from_store(self.store_node1, page_size=5)
            assert len(store_response.messages) == 1
        except Exception as ex:
            raise AssertionError(f"Nwaku failed with {ex}")

    def test_publishing_node_restarts(self, node_setup):
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        self.publishing_node1.restart()
        self.publishing_node1.ensure_ready()
        self.add_node_peer(self.store_node1, self.multiaddr_list)
        self.subscribe_to_pubsub_topics_via_relay(node=self.publishing_node1)
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=5)
            assert len(store_response.messages) == 2

    def test_store_node_restarts(self, node_setup):
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        self.store_node1.restart()
        self.store_node1.ensure_ready()
        self.subscribe_to_pubsub_topics_via_relay(node=self.store_node1)
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=5)
            assert len(store_response.messages) == 2

    def test_publishing_node_paused_and_unpaused(self, node_setup):
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        self.publishing_node1.pause()
        delay(1)
        self.publishing_node1.unpause()
        self.publishing_node1.ensure_ready()
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=5)
            assert len(store_response.messages) == 2

    def test_store_node_paused_and_unpaused(self, node_setup):
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        self.store_node1.pause()
        delay(1)
        self.store_node1.unpause()
        self.store_node1.ensure_ready()
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=5)
            assert len(store_response.messages) == 2

    def test_message_relayed_while_store_node_is_paused(self, node_setup):
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        self.store_node1.pause()
        self.publish_message()
        self.store_node1.unpause()
        self.store_node1.ensure_ready()
        self.check_published_message_is_stored(page_size=5)
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=5)
            assert len(store_response.messages) == 2

    def test_message_relayed_while_store_node_is_stopped_without_removing(self):
        self.setup_first_publishing_node(store="true", relay="true")
        self.setup_first_store_node(store="false", relay="false", remove_container=False)
        self.subscribe_to_pubsub_topics_via_relay()
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        self.store_node1.container.stop()
        self.publish_message()
        self.store_node1.container.start()
        self.store_node1.ensure_ready()
        for node in self.store_nodes:
            store_response = self.get_messages_from_store_with_retry(node)
            assert len(store_response.messages) == 2

    def test_message_relayed_while_store_node_is_stopped_and_removed(self, node_setup):
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        self.store_node1.stop()
        self.store_nodes.remove(self.store_node1)
        self.publish_message()
        self.setup_first_store_node(store="false", relay="true")
        self.store_node1.ensure_ready()
        self.add_node_peer(self.store_node1, self.multiaddr_list)
        self.subscribe_to_pubsub_topics_via_relay(node=self.store_node1)
        delay(1)
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=5)
            assert len(store_response.messages) == 2

    def test_message_relayed_before_store_node_is_started(self, node_setup):
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)
        self.setup_second_store_node(store="false", relay="true")
        self.subscribe_to_pubsub_topics_via_relay()
        store_response = self.get_messages_from_store(self.store_node2, page_size=5)
        assert len(store_response.messages) == 1
        self.publish_message()
        self.check_published_message_is_stored(page_size=5)

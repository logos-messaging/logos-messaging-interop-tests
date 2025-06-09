from uuid import uuid4
import pytest
from src.steps.filter import StepsFilter


@pytest.mark.usefixtures("setup_main_relay_node", "setup_main_filter_node")
class TestFilterPing(StepsFilter):
    @pytest.mark.smoke
    def test_filter_ping_on_subscribed_peer(self, subscribe_main_nodes):
        self.ping_filter_subscriptions(str(uuid4()))

    def test_filter_ping_on_peer_without_subscription(self):
        self.ping_without_filter_subscription()

    def test_filter_ping_on_unsubscribed_peer(self, subscribe_main_nodes):
        self.ping_filter_subscriptions(str(uuid4()))
        self.delete_filter_subscription({"requestId": "12345", "contentFilters": [self.test_content_topic], "pubsubTopic": self.test_pubsub_topic})
        self.ping_without_filter_subscription()

    def test_filter_ping_without_request_id(self, subscribe_main_nodes):
        try:
            self.ping_filter_subscriptions("")
            if self.node2.is_nwaku():
                pass
            else:
                raise NotImplementedError("Not implemented for this node type")
        except Exception as ex:
            assert "bad request id" in str(ex)

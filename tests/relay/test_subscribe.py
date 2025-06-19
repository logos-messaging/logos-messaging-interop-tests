import pytest
from src.env_vars import NODE_2
from src.libs.custom_logger import get_custom_logger
from src.steps.relay import StepsRelay
from src.test_data import INVALID_PUBSUB_TOPICS, VALID_PUBSUB_TOPICS

logger = get_custom_logger(__name__)


@pytest.mark.usefixtures("setup_main_relay_nodes")
class TestRelaySubscribe(StepsRelay):
    @pytest.mark.smoke
    def test_relay_no_subscription(self):
        self.check_publish_without_relay_subscription(self.test_pubsub_topic)

    @pytest.mark.smoke
    def test_relay_subscribe_to_single_pubsub_topic(self):
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, [self.test_pubsub_topic])
        self.wait_for_published_message_to_reach_relay_peer()

    def test_relay_subscribe_to_already_existing_pubsub_topic(self):
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, [self.test_pubsub_topic])
        self.wait_for_published_message_to_reach_relay_peer()
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, [self.test_pubsub_topic])
        self.check_published_message_reaches_relay_peer()

    def test_relay_subscribe_with_multiple_overlapping_pubsub_topics(self):
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, VALID_PUBSUB_TOPICS[:3])
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, VALID_PUBSUB_TOPICS[1:4])
        for pubsub_topic in VALID_PUBSUB_TOPICS[:4]:
            self.wait_for_published_message_to_reach_relay_peer(pubsub_topic=pubsub_topic)

    def test_relay_subscribe_with_empty_pubsub_topic_list(self):
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, [])

    def test_relay_subscribe_with_invalid_pubsub_topic_format(self):
        success_pubsub_topics = []
        for pubsub_topic in INVALID_PUBSUB_TOPICS:
            logger.debug(f"Running test with payload {pubsub_topic}")
            try:
                self.ensure_relay_subscriptions_on_nodes(self.main_nodes, pubsub_topic)
                success_pubsub_topics.append(pubsub_topic)
            except Exception as ex:
                assert "Bad Request" in str(ex)
        assert not success_pubsub_topics, f"Invalid Pubsub Topics that didn't failed: {success_pubsub_topics}"

    def test_relay_unsubscribe_from_single_pubsub_topic(self):
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, [self.test_pubsub_topic])
        self.wait_for_published_message_to_reach_relay_peer()
        self.delete_relay_subscriptions_on_nodes(self.main_nodes, [self.test_pubsub_topic])
        self.check_publish_without_relay_subscription(self.test_pubsub_topic)

    def test_relay_unsubscribe_from_all_pubsub_topics(self):
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, VALID_PUBSUB_TOPICS)
        for pubsub_topic in VALID_PUBSUB_TOPICS:
            self.wait_for_published_message_to_reach_relay_peer(pubsub_topic=pubsub_topic)
        self.delete_relay_subscriptions_on_nodes(self.main_nodes, VALID_PUBSUB_TOPICS)
        for pubsub_topic in VALID_PUBSUB_TOPICS:
            self.check_publish_without_relay_subscription(pubsub_topic)

    def test_relay_unsubscribe_from_some_pubsub_topics(self):
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, VALID_PUBSUB_TOPICS)
        for pubsub_topic in VALID_PUBSUB_TOPICS:
            self.wait_for_published_message_to_reach_relay_peer(pubsub_topic=pubsub_topic)
        self.delete_relay_subscriptions_on_nodes(self.main_nodes, VALID_PUBSUB_TOPICS[:3])
        for pubsub_topic in VALID_PUBSUB_TOPICS[:3]:
            self.check_publish_without_relay_subscription(pubsub_topic)
        for pubsub_topic in VALID_PUBSUB_TOPICS[3:]:
            self.check_published_message_reaches_relay_peer(pubsub_topic=pubsub_topic)

    def test_relay_unsubscribe_from_non_existing_pubsub_topic(self):
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, [self.test_pubsub_topic])
        self.wait_for_published_message_to_reach_relay_peer()
        try:
            self.delete_relay_subscriptions_on_nodes(self.main_nodes, VALID_PUBSUB_TOPICS[4:5])
            if self.node1.is_nwaku():
                pass  # nwaku doesn't fail in this case
            else:
                raise NotImplementedError("Not implemented for this node type")
        except Exception as ex:
            assert "Bad Request" in str(ex) or "Internal Server Error" in str(ex)
        self.check_published_message_reaches_relay_peer()

    def test_relay_unsubscribe_with_invalid_pubsub_topic_format(self):
        success_pubsub_topics = []
        for pubsub_topic in INVALID_PUBSUB_TOPICS:
            logger.debug(f"Running test with payload {pubsub_topic}")
            try:
                self.delete_relay_subscriptions_on_nodes(self.main_nodes, pubsub_topic)
                success_pubsub_topics.append(pubsub_topic)
            except Exception as ex:
                assert "Bad Request" in str(ex)
        assert not success_pubsub_topics, f"Invalid Pubsub Topics that didn't failed: {success_pubsub_topics}"

    def test_relay_resubscribe_to_unsubscribed_pubsub_topic(self):
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, [self.test_pubsub_topic])
        self.wait_for_published_message_to_reach_relay_peer()
        self.delete_relay_subscriptions_on_nodes(self.main_nodes, [self.test_pubsub_topic])
        self.check_publish_without_relay_subscription(self.test_pubsub_topic)
        self.ensure_relay_subscriptions_on_nodes(self.main_nodes, [self.test_pubsub_topic])
        self.check_published_message_reaches_relay_peer()

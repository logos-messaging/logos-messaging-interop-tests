import pytest
from src.env_vars import NODE_1, NODE_2
from src.libs.custom_logger import get_custom_logger
from src.libs.common import to_base64
from src.node.waku_message import WakuMessage
from src.node.store_response import StoreResponse
from src.steps.store import StepsStore
from src.test_data import SAMPLE_INPUTS
from src.test_data import PUBSUB_TOPICS_STORE

logger = get_custom_logger(__name__)


@pytest.mark.usefixtures("node_setup")
class TestApiFlags(StepsStore):
    def test_store_with_peerAddr(self):
        self.publish_message()
        self.check_published_message_is_stored(store_node=self.store_node1, peer_addr=self.multiaddr_list[0])

    def test_store_with_wrongPeerAddr(self):
        self.publish_message()
        wrong_peer_addr = self.multiaddr_list[0][1:]
        logger.debug(f"Running test with wrong_peer_addr: {wrong_peer_addr}")
        try:
            self.check_published_message_is_stored(store_node=self.store_node1, peer_addr=wrong_peer_addr)
            raise Exception("Message stored with wrong peer address")
        except Exception as ex:
            logger.debug(f" Response with wrong peer address is { ex.args[0]}")
            assert ex.args[0].find("Invalid MultiAddress") != -1
        # try to send wrong peer id
        wrong_peer_id = self.multiaddr_list[0][:-1]
        logger.debug(f"Running test with wrong_peer_addr {wrong_peer_id}")
        try:
            self.check_published_message_is_stored(store_node=self.store_node1, peer_addr=wrong_peer_id)
            raise Exception("Message restored with wrong peer id")
        except Exception as ex:
            logger.debug(f" Response with wrong peer id is { ex.args[0]}")
            assert ex.args[0].find("Failed parsing remote peer info") != -1

        # send address without /tcp number
        wrong_peer_addr = self.multiaddr_list[0].replace("/tcp", "")
        logger.debug(f"logger is {wrong_peer_addr}")
        try:
            self.check_published_message_is_stored(store_node=self.store_node1, peer_addr=wrong_peer_addr)
            raise Exception("Message stored with wrong peer address")
        except Exception as ex:
            logger.debug(f" Response with wrong peer address is { ex.args[0]}")
            assert ex.args[0].find("Unsupported protocol") != -1

    def test_store_include_data(self):
        message_list = []
        for payload in SAMPLE_INPUTS:
            message = self.create_message(payload=to_base64(payload["value"]))
            self.publish_message(message=message)
            message_list.append(message)
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, include_data="true", page_size=50)
            assert len(store_response.messages) == len(SAMPLE_INPUTS)
            for index in range(len(store_response.messages)):
                assert store_response.message_payload(index) == message_list[index]["payload"]
                assert store_response.message_pubsub_topic(index) == self.test_pubsub_topic
                waku_message = WakuMessage([store_response.message_at(index)])
                waku_message.assert_received_message(message_list[index])

    def test_store_not_include_data(self):
        self.publish_message(message=self.create_message())
        store_response = self.get_messages_from_store(self.store_node1, include_data="false")
        logger.debug(f" Message restored with hash only is {store_response.messages} ")
        assert "message" not in store_response.messages

    def test_get_store_messages_with_wrong_typo_content_topic(self):
        # positive scenario
        content_topic = "/myapp/1/latest/protoo"
        logger.debug(f"Trying to publish msg with content topic {content_topic}")
        msg = self.publish_message(message=self.create_message(contentTopic=content_topic))
        store_response = self.get_messages_from_store(self.store_node1, include_data="true", content_topics=content_topic)
        try:
            if store_response.messages is not None:
                stored_contentTopic = store_response.message_content(0)
                logger.debug(f"stored content topic is {stored_contentTopic}")
                assert stored_contentTopic == content_topic, "content topics don't match"

        except Exception as e:
            raise Exception(f"can't get message with content topic {content_topic}")

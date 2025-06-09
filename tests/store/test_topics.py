import pytest
from src.env_vars import NODE_2
from src.steps.store import StepsStore
from src.test_data import CONTENT_TOPICS_DIFFERENT_SHARDS
from src.libs.custom_logger import get_custom_logger
from src.test_data import PUBSUB_TOPICS_STORE

logger = get_custom_logger(__name__)


class TestTopics(StepsStore):
    @pytest.fixture(scope="function", autouse=True)
    def topics_setup(self, node_setup):
        self.message_hash_list = {"nwaku": []}
        for content_topic in CONTENT_TOPICS_DIFFERENT_SHARDS:
            message = self.create_message(contentTopic=content_topic)
            self.publish_message(message=message)
            self.message_hash_list["nwaku"].append(self.compute_message_hash(self.test_pubsub_topic, message, hash_type="hex"))

    def test_store_with_one_content_topic(self):
        for node in self.store_nodes:
            for index, content_topic in enumerate(CONTENT_TOPICS_DIFFERENT_SHARDS):
                store_response = node.get_store_messages(content_topics=content_topic, page_size=20, ascending="true")
                assert len(store_response["messages"]) == 1, "Message count mismatch"
                assert (
                    store_response["messages"][0]["messageHash"] == self.message_hash_list[node.type()][index]
                ), "Incorrect messaged filtered based on content topic"

    def test_store_with_multiple_content_topics(self):
        for node in self.store_nodes:
            store_response = node.get_store_messages(
                content_topics=f"{CONTENT_TOPICS_DIFFERENT_SHARDS[0]},{CONTENT_TOPICS_DIFFERENT_SHARDS[4]}", page_size=20, ascending="true"
            )
            assert len(store_response["messages"]) == 2, "Message count mismatch"
            assert (
                store_response["messages"][0]["messageHash"] == self.message_hash_list[node.type()][0]
            ), "Incorrect messaged filtered based on multiple content topics"
            assert (
                store_response["messages"][1]["messageHash"] == self.message_hash_list[node.type()][4]
            ), "Incorrect messaged filtered based on multiple content topics"

    def test_store_with_unknown_content_topic(self):
        for node in self.store_nodes:
            store_response = node.get_store_messages(content_topics="test", page_size=20, ascending="true")
            assert len(store_response["messages"]) == 0, "Message count mismatch"

    def test_store_with_unknown_pubsub_topic(self):
        for node in self.store_nodes:
            store_response = node.get_store_messages(pubsub_topic="test", page_size=20, ascending="true")
            assert len(store_response["messages"]) == 0, "Message count mismatch"

    def test_store_with_both_pubsub_topic_and_content_topic(self):
        for node in self.store_nodes:
            for index, content_topic in enumerate(CONTENT_TOPICS_DIFFERENT_SHARDS):
                store_response = node.get_store_messages(
                    pubsub_topic=self.test_pubsub_topic, content_topics=content_topic, page_size=20, ascending="true"
                )
                assert len(store_response["messages"]) == 1, "Message count mismatch"
                assert (
                    store_response["messages"][0]["messageHash"] == self.message_hash_list[node.type()][index]
                ), "Incorrect messaged filtered based on content topic"

    def test_store_with_unknown_pubsub_topic_but_known_content_topic(self):
        for node in self.store_nodes:
            store_response = node.get_store_messages(
                pubsub_topic="test", content_topics=CONTENT_TOPICS_DIFFERENT_SHARDS[0], page_size=20, ascending="true"
            )
            assert len(store_response["messages"]) == 0, "Message count mismatch"

    @pytest.mark.smoke
    def test_store_with_both_pubsub_topic_and_content_topic(self):
        for node in self.store_nodes:
            for index, content_topic in enumerate(CONTENT_TOPICS_DIFFERENT_SHARDS):
                store_response = node.get_store_messages(
                    pubsub_topic=self.test_pubsub_topic, content_topics=content_topic, page_size=20, ascending="true"
                )
                assert len(store_response["messages"]) == 1, "Message count mismatch"
                assert (
                    store_response["messages"][0]["messageHash"] == self.message_hash_list[node.type()][index]
                ), "Incorrect messaged filtered based on content topic"

    def test_store_without_pubsub_topic_and_content_topic(self):
        for node in self.store_nodes:
            store_response = node.get_store_messages(page_size=20, ascending="true")
            assert len(store_response["messages"]) == len(CONTENT_TOPICS_DIFFERENT_SHARDS), "Message count mismatch"

    def test_store_with_not_valid_content_topic(self):
        empty_content_topic = "##"
        logger.debug(f"trying to find stored messages with wrong content_topic ={empty_content_topic}")
        for node in self.store_nodes:
            store_response = node.get_store_messages(page_size=20, include_data="true", ascending="true", content_topics=empty_content_topic)
            assert len(store_response["messages"]) == 0, "Messages shouldn't ne retrieved with invalid content_topic"
        # test with space string content topic
        space_content_topic = " "
        try:
            store_response = self.store_nodes[0].get_store_messages(
                page_size=20, include_data="true", ascending="true", content_topics=space_content_topic
            )
            logger.debug(f" response for invalid content_topic {store_response}")
            assert store_response["messages"] == [], "message stored with wrong topic "
        except Exception as e:
            raise Exception("couldn't get stored message with invalid content_topic")

    def test_store_with_wrong_url_content_topic(self):
        # test with wrong url
        wrong_content_topic = "myapp/1/latest/proto"
        logger.debug(f"trying to find stored messages with wrong content_topic ={wrong_content_topic}")
        try:
            store_response = self.store_nodes[0].get_store_messages(
                page_size=20, include_data="true", ascending="true", content_topics=wrong_content_topic
            )
            logger.debug(f" response for wrong url content topic is {store_response}")
            assert store_response["messages"] == [], "message stored with wrong topic "
        except Exception as e:
            raise Exception(f"couldn't get stored message with wrong url {wrong_content_topic}")

    def test_store_with_empty_pubsub_topics(self):
        # empty pubsub topic
        empty_topic = ""
        index = iter(self.store_nodes)
        logger.debug(f"Trying to get stored msg with empty pubsub topic")
        store_response = self.store_nodes[0].get_store_messages(pubsub_topic=empty_topic, include_data="true", page_size=20, ascending="true")
        logger.debug(f"getting the following response when sending empty pubsub_topic {store_response}")
        for msg in store_response["messages"]:
            assert msg["pubsubTopic"] == self.test_pubsub_topic, "wrong pubsub topic"
        logger.debug(f"messages successfully queried with empty pubsub topic ")

    def test_store_with_wrong_url_pubsub_topic(self):
        # wrong url pubsub topic
        wrong_url_topic = PUBSUB_TOPICS_STORE[0][1:]
        logger.debug(f"Trying to get stored msg with wrong url topic {wrong_url_topic}")
        try:
            self.publish_message(pubsub_topic=PUBSUB_TOPICS_STORE[0])
            self.check_published_message_is_stored(pubsub_topic=wrong_url_topic)
            raise Exception("getting  stored message  with wrong url pubsub topic")
        except Exception as e:
            logger.error(f"Topic {wrong_url_topic} is wrong ''n: {str(e)}")
            assert e.args[0].find("messages': []") != -1, "Message shall not be stored for wrong topic"

    def test_store_with_long_string_pubsub_topic(self):
        # long topic string
        long_url_topic = PUBSUB_TOPICS_STORE[0][:-1]
        million = 1000000
        for i in range(million):
            long_url_topic += str(i)
        logger.debug(f"Trying to get stored msg with url topic size million ")
        self.publish_message(pubsub_topic=PUBSUB_TOPICS_STORE[0])
        try:
            self.check_published_message_is_stored(pubsub_topic=long_url_topic)
            raise Exception("request stored message with very long topic string shouldn't be accepted")
        except Exception as e:
            logger.error(f"store request with very long pubsub topic wasn't accepted ")
            assert e.args[0].find("Client Error: Request Header Fields Too Large for url") != -1, "error isn't for large url"

    def test_store_with_wrong_encoding_pubsubtopic(self):
        wrong_encoidng_topic = "%23waku%2F2%2Frs%2F3%2F0"
        empty_response = []
        logger.debug(f"trying get message with  wrong encoded pubsub topic {wrong_encoidng_topic}")
        store_response = self.store_nodes[0].get_store_messages(
            pubsub_topic=wrong_encoidng_topic, encode_pubsubtopic=False, include_data="true", page_size=20, ascending="true"
        )
        logger.debug(f"response for getting message with wrong encoded pubsub topic {store_response}")
        assert store_response["messages"] == empty_response, "Error !! message retrieved with wrong encoding pubsub_topic"

    def test_store_without_encoding_pubsubtopic(self):
        topic = PUBSUB_TOPICS_STORE[0]
        logger.debug(f"trying get message with  wrong encoded pubsub topic {topic}")
        store_response = self.store_nodes[0].get_store_messages(
            pubsub_topic=topic, encode_pubsubtopic=False, include_data="true", page_size=20, ascending="true"
        )
        logger.debug(f"response for getting message without encoding pubsub topic {store_response}")
        assert store_response["messages"][0]["pubsubTopic"] == PUBSUB_TOPICS_STORE[0], "topics Don't match !!"

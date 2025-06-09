import time
from src.env_vars import NODE_1, NODE_2
import pytest
from datetime import timedelta, datetime
from src.libs.custom_logger import get_custom_logger
from src.steps.store import StepsStore

logger = get_custom_logger(__name__)


@pytest.mark.usefixtures("node_setup")
class TestTimeFilter(StepsStore):
    def test_messages_with_timestamps_close_to_now(self):
        failed_timestamps = []
        ts_pass = self.get_time_list_pass()
        for timestamp in ts_pass:
            logger.debug(f'Running test with payload {timestamp["description"]}')
            message = self.create_message(timestamp=timestamp["value"])
            try:
                self.publish_message(message=message)
                self.check_published_message_is_stored(page_size=20, ascending="true")
            except Exception as ex:
                logger.error(f'Payload {timestamp["description"]} failed: {str(ex)}')
                failed_timestamps.append(timestamp["description"])
        assert not failed_timestamps, f"Timestamps failed: {failed_timestamps}"

    def test_messages_with_timestamps_far_from_now(self):
        success_timestamps = []
        ts_fail = self.get_time_list_fail()
        for timestamp in ts_fail:
            logger.debug(f'Running test with payload {timestamp["description"]}')
            message = self.create_message(timestamp=timestamp["value"])
            try:
                self.publish_message(message=message)
                self.check_store_returns_empty_response()
            except Exception as ex:
                logger.error(f'Payload {timestamp["description"]} succeeded where it should have failed: {str(ex)}')
                success_timestamps.append(timestamp["description"])
        assert not success_timestamps, f"Timestamps succeeded: {success_timestamps}"

    def test_time_filter_matches_one_message(self):
        message_hash_list = {"nwaku": []}
        ts_pass = self.get_time_list_pass()
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
            message_hash_list["nwaku"].append(self.compute_message_hash(self.test_pubsub_topic, message, hash_type="hex"))
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(
                node,
                page_size=20,
                start_time=ts_pass[0]["value"] - 100000,
                end_time=ts_pass[0]["value"] + 100000,
            )
            assert len(store_response.messages) == 1, "Message count mismatch"
            assert store_response.message_hash(0) == message_hash_list[node.type()][0], "Incorrect messaged filtered based on time"

    def test_time_filter_matches_multiple_messages(self):
        message_hash_list = {"nwaku": []}
        ts_pass = self.get_time_list_pass()
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
            message_hash_list["nwaku"].append(self.compute_message_hash(self.test_pubsub_topic, message, hash_type="hex"))
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(
                node,
                page_size=20,
                start_time=ts_pass[0]["value"] - 100000,
                end_time=ts_pass[4]["value"] + 100000,
            )
            assert len(store_response.messages) == 5, "Message count mismatch"
            for i in range(5):
                assert store_response.message_hash(i) == message_hash_list[node.type()][i], f"Incorrect messaged filtered based on time at index {i}"

    def test_time_filter_matches_no_message(self):
        ts_pass = self.get_time_list_pass()
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(
                node,
                page_size=20,
                start_time=ts_pass[0]["value"] - 100000,
                end_time=ts_pass[0]["value"] - 100,
            )
            assert not store_response.messages, "Message count mismatch"

    def test_time_filter_start_time_equals_end_time(self):
        message_hash_list = {"nwaku": []}
        ts_pass = self.get_time_list_pass()
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
            message_hash_list["nwaku"].append(self.compute_message_hash(self.test_pubsub_topic, message, hash_type="hex"))
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(
                node,
                page_size=20,
                start_time=ts_pass[0]["value"],
                end_time=ts_pass[0]["value"],
            )
            assert len(store_response.messages) == 1, "Message count mismatch"
            assert store_response.message_hash(0) == message_hash_list[node.type()][0], "Incorrect messaged filtered based on time"

    def test_time_filter_start_time_after_end_time(self):
        ts_pass = self.get_time_list_pass()
        start_time = ts_pass[4]["value"]  # 2 sec Future
        end_time = ts_pass[0]["value"]  # 3 sec past
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
        logger.debug(f"inquering stored messages with start time {start_time} after end time {end_time}")
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(
                node,
                page_size=20,
                start_time=start_time,
                end_time=end_time,
            )
            logger.debug(f"response for wrong time message is {store_response.response}")
            assert len(store_response.messages) == 0, "got messages with start time after end time !"

    def test_time_filter_negative_start_time(self):
        ts_pass = self.get_time_list_pass()
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
        start_time = -10000
        logger.debug(f"inquering stored messages with start time {start_time}")
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=20, start_time=start_time, include_data=True)
            logger.debug(f"number of messages stored for  " f"start time = {start_time} is  {len(store_response.messages)}")
            assert len(store_response.messages) == 6, "number of messages retrieved doesn't match time filter "

    def test_time_filter_zero_start_time(self):
        ts_pass = self.get_time_list_pass()
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
        start_time = 0
        logger.debug(f"inquering stored messages with start time {start_time}")
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=20, start_time=start_time, include_data=True)
            logger.debug(f"number of messages stored for  " f"start time = {start_time} is  {len(store_response.messages)}")
            assert len(store_response.messages) == 6, "number of messages retrieved doesn't match time filter "

    def test_time_filter_zero_start_end_time(self):
        ts_pass = self.get_time_list_pass()
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
        start_time = 0
        end_time = 0
        logger.debug(f"inquering stored messages with start time {start_time}")
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=20, start_time=start_time, end_time=end_time, include_data=True)
            logger.debug(f"number of messages stored for  " f"start time = {start_time} is  {len(store_response.messages)}")

            assert len(store_response.messages) == 6, "number of messages retrieved doesn't match time filter "

    def test_time_filter_invalid_start_time(self):
        ts_pass = self.get_time_list_pass()
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
        start_time = "abc"
        logger.debug(f"inquering stored messages with start time {start_time}")
        try:
            for node in self.store_nodes:
                store_response = self.get_messages_from_store(node, page_size=20, start_time=start_time, include_data=True)
            raise Exception(f"Request for stored messages with invalid start time {start_time} is successful")
        except Exception as e:
            logger.debug(f"invalid start_time cause error {e}")
            assert e.args[0].find("Bad Request for url"), "url with wrong start_time is accepted"

    def test_time_filter_end_time_now(self):
        ts_pass = self.get_time_list_pass()
        ts_pass[3]["value"] = int((datetime.now() + timedelta(seconds=4)).timestamp() * 1e9)
        start_time = ts_pass[0]["value"]
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
        end_time = int(datetime.now().timestamp() * 1e9)
        logger.debug(f"inquering stored messages with start time {start_time} after end time {end_time}")
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=20, start_time=start_time, end_time=end_time, include_data=True)
            logger.debug(f"number of messages stored for start time {start_time} and " f"end time = {end_time} is  {len(store_response.messages)}")
            assert len(store_response.messages) == 3, "number of messages retrieved doesn't match time filter "

    def test_time_filter_big_timestamp(self):
        ts_pass = self.get_time_list_pass()
        start_time = ts_pass[0]["value"]
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
        end_time = int((datetime.now() + timedelta(days=8000)).timestamp() * 1e9)
        logger.debug(f"inquering stored messages with start time {start_time} after end time {end_time}")
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=20, start_time=start_time, end_time=end_time, include_data=True)
            logger.debug(f"number of messages stored for start time {start_time} and " f"end time = {end_time} is  {len(store_response.messages)}")
            assert len(store_response.messages) == 6, "number of messages retrieved doesn't match time filter "

    def test_time_filter_small_timestamp(self):
        ts_pass = self.get_time_list_pass()
        start_time = ts_pass[0]["value"]
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
        end_time = ts_pass[5]["value"] + 1
        logger.debug(f"inquering stored messages with start time {start_time} after end time {end_time}")
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=20, start_time=start_time, end_time=end_time, include_data=True)
            logger.debug(f"number of messages stored for start time {start_time} and " f"end time = {end_time} is  {len(store_response.messages)}")

            assert len(store_response.messages) == 6, "number of messages retrieved doesn't match time filter "

    def test_time_filter_negative_end_time(self):
        ts_pass = self.get_time_list_pass()
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
        end_time = -10000
        logger.debug(f"inquering stored messages with end time {end_time}")
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=20, end_time=end_time, include_data=True)
            logger.debug(f"number of messages stored for  " f"end time = {end_time} is  {len(store_response.messages)}")

            assert len(store_response.messages) == 6, "number of messages retrieved doesn't match time filter "

    def test_time_filter_zero_end_time(self):
        ts_pass = self.get_time_list_pass()
        for timestamp in ts_pass:
            message = self.create_message(timestamp=timestamp["value"])
            self.publish_message(message=message)
        end_time = 0
        logger.debug(f"inquering stored messages with end time {end_time}")
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=20, end_time=end_time, include_data=True)
            logger.debug(f"number of messages stored for  " f"end time = {end_time} is  {len(store_response.messages)}")
            assert len(store_response.messages) == 6, "number of messages retrieved doesn't match time filter "

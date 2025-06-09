import pytest
from src.env_vars import NODE_1, NODE_2
from src.libs.common import to_base64
from src.node.store_response import StoreResponse
from src.steps.store import StepsStore


@pytest.mark.usefixtures("node_setup")
class TestCursorManyMessages(StepsStore):
    # we implicitly test the reusabilty of the cursor for multiple nodes

    @pytest.mark.timeout(540)
    @pytest.mark.store2000
    def test_get_multiple_2000_store_messages(self):
        expected_message_hash_list = {"nwaku": []}
        for i in range(2000):
            message = self.create_message(payload=to_base64(f"Message_{i}"))
            self.publish_message(message=message)
            expected_message_hash_list["nwaku"].append(self.compute_message_hash(self.test_pubsub_topic, message, hash_type="hex"))
        store_response = StoreResponse({"paginationCursor": "", "pagination_cursor": ""}, self.store_node1)
        response_message_hash_list = []
        while store_response.pagination_cursor is not None:
            cursor = store_response.pagination_cursor
            store_response = self.get_messages_from_store(self.store_node1, page_size=100, cursor=cursor)
            for index in range(len(store_response.messages)):
                response_message_hash_list.append(store_response.message_hash(index))
        assert len(expected_message_hash_list[self.store_node1.type()]) == len(response_message_hash_list), "Message count mismatch"
        assert expected_message_hash_list[self.store_node1.type()] == response_message_hash_list, "Message hash mismatch"

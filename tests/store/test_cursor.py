import pytest
from src.env_vars import NODE_1, NODE_2
from src.libs.common import to_base64, to_hex
from src.node.store_response import StoreResponse
from src.steps.store import StepsStore


@pytest.mark.usefixtures("node_setup")
class TestCursor(StepsStore):
    # we implicitly test the reusabilty of the cursor for multiple nodes

    @pytest.mark.parametrize("cursor_index, message_count", [[2, 4], [3, 20], [10, 40], [19, 20], [19, 50], [110, 120]])
    def test_different_cursor_and_indexes(self, cursor_index, message_count):
        message_hash_list = {"nwaku": []}
        cursor = ""
        cursor_index = cursor_index if cursor_index < 100 else 100
        for i in range(message_count):
            message = self.create_message(payload=to_base64(f"Message_{i}"))
            self.publish_message(message=message)
            message_hash_list["nwaku"].append(self.compute_message_hash(self.test_pubsub_topic, message, hash_type="hex"))
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=cursor_index)
            assert len(store_response.messages) == cursor_index
            cursor = store_response.pagination_cursor
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=100, ascending="true", cursor=cursor)
            assert len(store_response.messages) == message_count - cursor_index
            for index in range(len(store_response.messages)):
                assert (
                    store_response.message_hash(index) == message_hash_list[node.type()][cursor_index + index]
                ), f"Message hash at index {index} doesn't match"

    def test_passing_cursor_not_returned_in_paginationCursor(self):
        cursor = ""
        for i in range(10):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=5)
            # retrieving the cursor with the message hash of the 3rd message stored
            cursor = store_response.message_hash(2)
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=100, cursor=cursor)
            assert len(store_response.messages) == 7, "Message count mismatch"

    def test_passing_cursor_of_the_last_message_from_the_store(self):
        cursor = ""
        for i in range(10):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=10)
            # retrieving the cursor with the message hash of the last message stored
            cursor = store_response.message_hash(9)
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=100, cursor=cursor)
            assert not store_response.messages, "Messages found"

    def test_passing_cursor_of_non_existing_message_from_the_store(self):
        for i in range(4):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))
        # creating a cursor to a message that doesn't exist
        wrong_message = self.create_message(payload=to_base64("test"))
        cursor = {}
        cursor["nwaku"] = self.compute_message_hash(self.test_pubsub_topic, wrong_message, hash_type="hex")
        for node in self.store_nodes:
            try:
                self.get_messages_from_store(node, page_size=100, cursor=cursor[node.type()])
                raise AssertionError("Store fetch with wrong cursor worked!!!")
            except Exception as ex:
                assert "cursor not found" in str(ex) or "Internal Server Error" in str(ex)

    def test_passing_invalid_cursor(self):
        for i in range(4):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))
        # creating a invalid hex cursor
        cursor = to_hex("test")
        for node in self.store_nodes:
            try:
                self.get_messages_from_store(node, page_size=100, cursor=cursor)
                raise AssertionError("Store fetch with wrong cursor worked!!!")
            except Exception as ex:
                assert "invalid hash length" in str(ex) or "Bad Request" in str(ex)

    def test_passing_non_base64_cursor(self):
        for i in range(4):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))
        # creating a non base64 cursor
        cursor = "test"
        for node in self.store_nodes:
            try:
                self.get_messages_from_store(node, page_size=100, cursor=cursor)
                raise AssertionError("Store fetch with wrong cursor worked!!!")
            except Exception as ex:
                assert "cursor not found" in str(ex) or "Exception converting hex string to bytes" in str(ex) or "Bad Request" in str(ex)

    # Ensure that when the cursor is an empty string (""), the API returns the first page of data.
    def test_empty_cursor(self):
        for i in range(10):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=5, cursor="")
            assert store_response.status_code == 200, f"Expected status code 200, got {store_response.status_code}"
            assert len(store_response.messages) == 5, "Message count mismatch with empty cursor"

    # Test the scenario where the cursor points near the last few messages, ensuring proper pagination.
    def test_cursor_near_end(self):
        for i in range(10):
            message = self.create_message(payload=to_base64(f"Message_{i}"))
            self.publish_message(message=message)

        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, page_size=5)
            cursor = store_response.pagination_cursor
            store_response = self.get_messages_from_store(node, page_size=5, cursor=cursor)
            assert len(store_response.messages) == 5, "Message count mismatch near the end"

    # Test how the API handles a cursor that points to a message that no longer exists.
    def test_cursor_pointing_to_deleted_message(self):
        # Publish some messages
        for i in range(10):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))

        # Create a deleted message and compute its hash as the cursor
        deleted_message = self.create_message(payload=to_base64("Deleted_Message"))
        cursor = {}
        cursor["nwaku"] = self.compute_message_hash(self.test_pubsub_topic, deleted_message, hash_type="hex")

        # Test the store response
        for node in self.store_nodes:
            store_response = self.get_store_messages_with_errors(
                node=node, pubsub_topic=self.test_pubsub_topic, content_topics=self.test_content_topic, page_size=100, cursor=cursor[node.type()]
            )
            assert store_response["status_code"] == 500, f"Expected status code 500, got {store_response['status_code']}"
            actual_error_message = store_response["error_message"]
            assert "cursor not found" in actual_error_message

    # Test if the API returns the expected messages when the cursor points to the first message in the store.
    def test_cursor_equal_to_first_message(self):
        message_hash_list = {"nwaku": []}
        for i in range(10):
            message = self.create_message(payload=to_base64(f"Message_{i}"))
            self.publish_message(message=message)
            message_hash_list["nwaku"].append(self.compute_message_hash(self.test_pubsub_topic, message, hash_type="hex"))

        for node in self.store_nodes:
            cursor = message_hash_list[node.type()][0]  # Cursor points to the first message
            store_response = self.get_messages_from_store(node, page_size=100, cursor=cursor)
            assert len(store_response.messages) == 9, "Message count mismatch from the first cursor"

    # Test behavior when the cursor points exactly at the page size boundary.
    def test_cursor_at_page_size_boundary(self):
        for i in range(10):
            message = self.create_message(payload=to_base64(f"Message_{i}"))
            self.publish_message(message=message)

        # Set page size to 5, checking paginationCursor after both fetches
        for node in self.store_nodes:
            # Fetch the first page of messages
            store_response = self.get_messages_from_store(node, page_size=5)

            # Check if we received exactly 5 messages
            assert len(store_response.messages) == 5, "Message count mismatch on first page"

            # Validate that paginationCursor exists because we are not at the boundary
            assert store_response.pagination_cursor is not None, "paginationCursor should be present when not at the boundary"
            cursor = store_response.pagination_cursor

            # Fetch the next page using the cursor
            store_response = self.get_messages_from_store(node, page_size=5, cursor=cursor)

            # Check if we received exactly 5 more messages
            assert len(store_response.messages) == 5, "Message count mismatch at page size boundary"

            # Validate that paginationCursor is **not** present when we reach the boundary (end of pagination)
            assert store_response.pagination_cursor is None, "paginationCursor should be absent when at the boundary"

    #   This test publishes 5 messages and retrieves them using the store API with a page size of 3.
    #   It attempts to use an invalid 'paginationCursor' query parameter instead of the correct 'cursor'.
    #   The test then validates that the incorrect parameter doesn't affect pagination and that the correct
    #   'cursor' parameter successfully retrieves the remaining messages.
    def test_invalid_pagination_cursor_param(self):
        # Store the timestamps used when creating messages
        timestamps = []

        # Publish 5 messages
        for i in range(5):
            message = self.create_message(payload=to_base64(f"Message_{i}"))
            timestamps.append(message["timestamp"])  # Save the timestamp
            self.publish_message(message=message)

        for node in self.store_nodes:
            # Step 1: Request first page with pageSize = 3
            store_response = self.get_messages_from_store(node, page_size=3)
            assert len(store_response.messages) == 3, "Message count mismatch on first page"
            pagination_cursor = store_response.pagination_cursor

            # Step 2: Attempt to use invalid paginationCursor param (expect 200 but no page change)
            invalid_cursor = pagination_cursor
            store_response_invalid = self.get_messages_from_store(node, page_size=3, paginationCursor=invalid_cursor)
            assert store_response_invalid.status_code == 200, "Expected 200 response with invalid paginationCursor param"
            assert len(store_response_invalid.messages) == 3, "Expected the same page content since paginationCursor is ignored"
            assert store_response_invalid.messages == store_response.messages, "Messages should be the same as the first page"

            # Step 3: Use correct cursor to get the remaining messages
            store_response_valid = self.get_messages_from_store(node, page_size=3, cursor=pagination_cursor)
            assert len(store_response_valid.messages) == 2, "Message count mismatch on second page"
            assert store_response_valid.pagination_cursor is None, "There should be no pagination cursor for the last page"

            # Validate the message content using the correct timestamp
            hash_type = "hex" if node.is_nwaku() else "base64"
            expected_message_hashes = [
                self.compute_message_hash(
                    self.test_pubsub_topic,
                    {
                        "payload": to_base64(f"Message_3"),
                        "contentTopic": "/myapp/1/latest/proto",
                        "timestamp": timestamps[3],  # Use the stored timestamp for Message_3
                    },
                    hash_type=hash_type,
                ),
                self.compute_message_hash(
                    self.test_pubsub_topic,
                    {
                        "payload": to_base64(f"Message_4"),
                        "contentTopic": "/myapp/1/latest/proto",
                        "timestamp": timestamps[4],  # Use the stored timestamp for Message_4
                    },
                    hash_type=hash_type,
                ),
            ]
            for i, message in enumerate(store_response_valid.messages):
                assert message["messageHash"] == expected_message_hashes[i], f"Message hash mismatch for message {i}"

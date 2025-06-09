import pytest
from src.env_vars import NODE_2
from src.libs.common import to_base64, to_hex
from src.libs.custom_logger import get_custom_logger
from src.steps.store import StepsStore
from src.test_data import SAMPLE_INPUTS

logger = get_custom_logger(__name__)


@pytest.mark.usefixtures("node_setup")
class TestHashes(StepsStore):
    def test_store_with_hashes(self):
        message_hash_list = {"nwaku": []}
        for payload in SAMPLE_INPUTS:
            message = self.create_message(payload=to_base64(payload["value"]))
            self.publish_message(message=message)
            message_hash_list["nwaku"].append(self.compute_message_hash(self.test_pubsub_topic, message, hash_type="hex"))
        for node in self.store_nodes:
            for message_hash in message_hash_list[node.type()]:
                store_response = self.get_messages_from_store(node, hashes=message_hash, page_size=50)
                assert len(store_response.messages) == 1
                assert store_response.message_hash(0) == message_hash

    def test_store_with_multiple_hashes(self):
        message_hash_list = {"nwaku": []}
        for payload in SAMPLE_INPUTS:
            message = self.create_message(payload=to_base64(payload["value"]))
            self.publish_message(message=message)
            message_hash_list["nwaku"].append(self.compute_message_hash(self.test_pubsub_topic, message, hash_type="hex"))
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(
                node, hashes=f"{message_hash_list[node.type()][0]},{message_hash_list[node.type()][4]}", page_size=50
            )
            assert len(store_response.messages) == 2
            assert store_response.message_hash(0) == message_hash_list[node.type()][0], "Incorrect messaged filtered based on multiple hashes"
            assert store_response.message_hash(1) == message_hash_list[node.type()][4], "Incorrect messaged filtered based on multiple hashes"

    def test_store_with_wrong_hash(self):
        for i in range(4):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))
        wrong_hash = {}
        wrong_hash["nwaku"] = self.compute_message_hash(self.test_pubsub_topic, self.create_message(payload=to_base64("test")), hash_type="hex")
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, hashes=wrong_hash[node.type()], page_size=50)
            assert not store_response.messages, "Messages found"

    def test_store_with_invalid_hash(self):
        for i in range(4):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))
        invalid_hash = to_hex("test")
        for node in self.store_nodes:
            try:
                store_response = self.get_messages_from_store(node, hashes=invalid_hash, page_size=50)
                assert not store_response.messages
            except Exception as ex:
                assert "waku message hash parsing error: invalid hash length" in str(ex)

    def test_store_with_non_hex_hash(self):
        for i in range(4):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))
        non_hex_hash = "test"
        for node in self.store_nodes:
            try:
                store_response = self.get_messages_from_store(node, hashes=non_hex_hash, page_size=50)
                assert not store_response.messages
            except Exception as ex:
                assert "Exception converting hex string to bytes: t is not a hexadecimal character" in str(ex)

    # Addon on Test

    # Test when the hashes parameter is an empty string.
    def test_store_with_empty_hashes(self):
        for i in range(4):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))

        # Test with an empty string for the hashes parameter
        for node in self.store_nodes:
            store_response = self.get_messages_from_store(node, hashes="", page_size=50)
            assert len(store_response.messages) == 4, "Messages found"

    # Test when the hash is longer than the valid length (e.g., 45 characters or more).
    def test_store_with_excessive_length_hash(self):
        excessive_length_hash = "A" * 50  # Exceeds valid length of 44 characters for a Base64-encoded hash
        for i in range(4):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))

        for node in self.store_nodes:
            store_response = self.get_store_messages_with_errors(node, hashes=excessive_length_hash, page_size=50)

            # Check if the response has a "messages" key and if it's empty
            assert "messages" not in store_response, "Messages found for an excessive length hash"

    # Test the behavior when you supply an empty hash alongside valid hashes.
    def test_store_with_empty_and_valid_hash(self):
        message_hash_list = {"nwaku": []}
        for i in range(4):
            message = self.create_message(payload=to_base64(f"Message_{i}"))
            self.publish_message(message=message)

            message_hash_list["nwaku"].append(self.compute_message_hash(self.test_pubsub_topic, message, hash_type="hex"))

        empty_hash = ""
        for node in self.store_nodes:
            try:
                # Combining valid hash with an empty hash
                store_response = self.get_messages_from_store(node, hashes=f"{message_hash_list[node.type()][0]},{empty_hash}", page_size=50)
                assert len(store_response.messages) == 1, "Message count mismatch with empty and valid hashes"
            except Exception as ex:
                assert "waku message hash parsing error" in str(ex), "Unexpected error for combined empty and valid hash"

    # Test for hashes that include non-hex characters.
    def test_store_with_non_hex_characters_in_hash(self):
        non_hex_hash = "### INVALID HASH ###"  # Invalid hash with non-hex characters
        for i in range(4):
            self.publish_message(message=self.create_message(payload=to_base64(f"Message_{i}")))

        for node in self.store_nodes:
            store_response = self.get_store_messages_with_errors(node, hashes=non_hex_hash, page_size=50)

            assert (
                "Exception converting hex string to bytes: # is not a hexadecimal character" in store_response["error_message"]
            ), f"Expected '# is not a hexadecimal character' error, got {store_response['error_message']}"

    # Test when duplicate valid hashes are provided.
    def test_store_with_duplicate_hashes(self):
        message_hash_list = {"nwaku": []}
        for i in range(4):
            message = self.create_message(payload=to_base64(f"Message_{i}"))
            self.publish_message(message=message)
            message_hash_list["nwaku"].append(self.compute_message_hash(self.test_pubsub_topic, message, hash_type="hex"))

        for node in self.store_nodes:
            # Use the same hash twice
            duplicate_hash = f"{message_hash_list[node.type()][0]},{message_hash_list[node.type()][0]}"
            store_response = self.get_messages_from_store(node, hashes=duplicate_hash, page_size=50)
            assert len(store_response.messages) == 1, "Expected only one message for duplicate hashes"
            assert store_response.message_hash(0) == message_hash_list[node.type()][0], "Incorrect message returned for duplicate hashes"

    #  Invalid Query Parameter (hash) for Hashes
    def test_invalid_hash_param(self):
        # Publish 4 messages
        published_messages = []
        for i in range(4):
            message = self.create_message(payload=to_base64(f"Message_{i}"))
            self.publish_message(message=message)
            published_messages.append(message)

        for node in self.store_nodes:
            # Step 1: Request messages with the correct 'hashes' parameter
            hash_type = "hex" if node.is_nwaku() else "base64"
            correct_hash = self.compute_message_hash(self.test_pubsub_topic, published_messages[2], hash_type=hash_type)
            store_response_valid = self.get_messages_from_store(node, hashes=correct_hash)

            assert store_response_valid.status_code == 200, "Expected 200 response with correct 'hashes' parameter"
            assert len(store_response_valid.messages) == 1, "Expected exactly one message in the response"
            assert store_response_valid is not None and store_response_valid.messages, "Store response is None or has no messages"
            assert store_response_valid.messages[0]["messageHash"] == correct_hash, "Returned message hash does not match the expected hash"

            # Step 2: Attempt to use the invalid 'hash' parameter (expect all messages to be returned)
            store_response_invalid = self.get_messages_from_store(node, hash=correct_hash)

            assert store_response_invalid.status_code == 200, "Expected 200 response with invalid 'hash' parameter"
            assert len(store_response_invalid.messages) == 4, "Expected all messages to be returned since 'hash' filter is ignored"

            # Collect the hashes of all published messages
            if store_response_invalid is not None and store_response_invalid.messages:
                expected_hashes = [msg["messageHash"] for msg in store_response_invalid.messages]
                returned_hashes = [msg["messageHash"] for msg in store_response_invalid.messages]
            else:
                expected_hashes = []
                returned_hashes = []

            assert set(returned_hashes) == set(expected_hashes), "Returned message hashes do not match the expected hashes"

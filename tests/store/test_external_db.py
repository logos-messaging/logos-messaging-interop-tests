import pytest
from src.libs.custom_logger import get_custom_logger
from src.steps.store import StepsStore
from src.env_vars import PG_PASS, PG_USER

logger = get_custom_logger(__name__)


class TestExternalDb(StepsStore):
    postgress_url = f"postgres://{PG_USER}:{PG_PASS}@postgres:5432/postgres"

    @pytest.fixture(scope="function", autouse=True)
    def node_postgres_setup(self, store_setup, start_postgres_container):
        self.setup_first_publishing_node(store="true", relay="true", store_message_db_url=self.postgress_url)
        self.setup_first_store_node(store="false", relay="true")
        self.subscribe_to_pubsub_topics_via_relay()

    @pytest.mark.timeout(60)
    def test_on_empty_postgress_db(self):
        message = self.create_message()
        self.publish_message(message=message)
        self.check_published_message_is_stored(page_size=5, ascending="true")
        assert len(self.store_response.messages) >= 1

    @pytest.mark.flaky(reruns=6)
    def test_on_postgress_db_with_one_message(self):
        self.test_on_empty_postgress_db()
        self.setup_first_publishing_node(store="true", relay="true", store_message_db_url=self.postgress_url)
        self.setup_first_store_node(store="false", relay="true")
        self.subscribe_to_pubsub_topics_via_relay()
        message = self.create_message()
        self.publish_message(message=message)
        self.check_published_message_is_stored(page_size=5, ascending="true")
        assert len(self.store_response.messages) >= 2

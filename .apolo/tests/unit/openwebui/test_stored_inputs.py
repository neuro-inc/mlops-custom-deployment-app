import pytest
from apolo_app_types_fixtures.constants import APP_ID, APP_SECRETS_NAME
from apolo_apps_openwebui.inputs_processor import OpenWebUIInputsProcessor
from apolo_apps_openwebui.types import OpenWebUIAppInputs


pytest_plugins = ["apolo_app_types_fixtures"]


STORED_INPUTS = {
    "preset": {"name": "cpu-small", "__type__": "Preset"},
    "networking_config": {
        "ingress_http": {
            "auth": {"type": "apolo_auth", "__type__": "ApoloAuth"},
            "__type__": "IngressHttp",
        },
        "__type__": "BasicNetworkingConfig",
    },
    "database_config": {
        "database": {"database_type": "sqlite", "__type__": "SQLiteDatabase"},
        "__type__": "DataBaseConfig",
    },
    "llm_chat_api": {
        "host": "llm-inference.platform--org--project",
        "port": 80,
        "protocol": "http",
        "timeout": 30.0,
        "base_path": "/",
        "api_type": "rest",
        "api_base_path": "/v1",
        "openai_api_type": "chat",
        "endpoint_url": "/v1/chat",
        "hf_model": {
            "model_hf_name": "meta-llama/Llama-3.1-8B-Instruct",
            "hf_token": None,
            "hf_cache": None,
            "__type__": "HuggingFaceModel",
        },
        "__type__": "OpenAICompatChatAPI",
    },
    "embeddings_api": {
        "host": "tei.platform--org--project",
        "port": 3000,
        "protocol": "http",
        "timeout": 30.0,
        "base_path": "/",
        "api_type": "rest",
        "api_base_path": "/v1",
        "openai_api_type": "embeddings",
        "endpoint_url": "/v1/embeddings",
        "hf_model": {
            "model_hf_name": "BAAI/bge-small-en-v1.5",
            "hf_token": None,
            "hf_cache": None,
            "__type__": "HuggingFaceModel",
        },
        "__type__": "OpenAICompatEmbeddingsAPI",
    },
    "openwebui_specific": {"env": [], "__type__": "OpenWebUISpecific"},
}


async def generate_env(setup_clients, stored: dict) -> dict:
    processor = OpenWebUIInputsProcessor(client=setup_clients)
    values = await processor.gen_extra_values(
        input_=OpenWebUIAppInputs.model_validate(stored),
        app_name="openwebui-app",
        namespace="default-namespace",
        app_secrets_name=APP_SECRETS_NAME,
        app_id=APP_ID,
    )
    return {env["name"]: env["value"] for env in values["container"]["env"]}


@pytest.mark.asyncio
async def test_stored_inputs_keep_their_env(setup_clients):
    assert await generate_env(setup_clients, STORED_INPUTS) == {
        "OPENAI_API_BASE_URL": "http://llm-inference.platform--org--project/v1",
        "RAG_EMBEDDING_ENGINE": "openai",
        "RAG_OPENAI_API_BASE_URL": "http://tei.platform--org--project:3000/v1",
        "RAG_EMBEDDING_MODEL": "BAAI/bge-small-en-v1.5",
    }


@pytest.mark.asyncio
async def test_custom_env_overrides_the_embedding_model(setup_clients):
    stored = {
        **STORED_INPUTS,
        "openwebui_specific": {
            "env": [{"name": "RAG_EMBEDDING_MODEL", "value": "custom-model"}]
        },
    }

    env = await generate_env(setup_clients, stored)

    assert env["RAG_EMBEDDING_MODEL"] == "custom-model"

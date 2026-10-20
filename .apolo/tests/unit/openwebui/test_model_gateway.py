import pytest
from apolo_apps_openwebui.types import OpenWebUIAppInputs
from pydantic import ValidationError

from .test_stored_inputs import STORED_INPUTS, generate_env


pytest_plugins = ["apolo_app_types_fixtures"]


GATEWAY_API = {
    "host": "bifrost-0a1b2c3d.platform--org--project",
    "port": 8080,
    "protocol": "http",
    "timeout": 30.0,
    "base_path": "/",
    "api_type": "rest",
    "api_base_path": "/v1",
    "models": [
        {
            "name": "vllm/meta-llama/Llama-3.1-8B-Instruct",
            "capabilities": ["chat", "completions", "responses"],
            "__type__": "OpenAICompatModel",
        },
        {
            "name": "vllm/BAAI/bge-small-en-v1.5",
            "capabilities": ["embeddings"],
            "__type__": "OpenAICompatModel",
        },
        {
            "name": "openai/text-embedding-3-small",
            "capabilities": ["embeddings"],
            "__type__": "OpenAICompatModel",
        },
    ],
    "model_prefixes": ["openai/"],
    "__type__": "OpenAICompatAPI",
}

GATEWAY_URL = "http://bifrost-0a1b2c3d.platform--org--project:8080/v1"

GATEWAY_EMBEDDINGS_API = {
    "host": "bifrost-0a1b2c3d.platform--org--project",
    "port": 8080,
    "protocol": "http",
    "timeout": 30.0,
    "base_path": "/",
    "api_type": "rest",
    "api_base_path": "/v1",
    "openai_api_type": "embeddings",
    "endpoint_url": "/v1/embeddings",
    "hf_model": {
        "model_hf_name": "vllm/BAAI/bge-small-en-v1.5",
        "hf_token": None,
        "hf_cache": None,
        "__type__": "HuggingFaceModel",
    },
    "__type__": "OpenAICompatEmbeddingsAPI",
}


def gateway_inputs(**changes) -> dict:
    inputs = dict(STORED_INPUTS)
    del inputs["llm_chat_api"]
    return {**inputs, "openai_api": GATEWAY_API, **changes}


@pytest.mark.asyncio
async def test_gateway_serves_chat(setup_clients):
    assert await generate_env(setup_clients, gateway_inputs()) == {
        "OPENAI_API_BASE_URL": GATEWAY_URL,
        "RAG_EMBEDDING_ENGINE": "openai",
        "RAG_OPENAI_API_BASE_URL": "http://tei.platform--org--project:3000/v1",
        "RAG_EMBEDDING_MODEL": "BAAI/bge-small-en-v1.5",
    }


@pytest.mark.asyncio
async def test_embeddings_api_of_the_same_gateway(setup_clients):
    inputs = gateway_inputs(embeddings_api=GATEWAY_EMBEDDINGS_API)

    assert await generate_env(setup_clients, inputs) == {
        "OPENAI_API_BASE_URL": GATEWAY_URL,
        "RAG_EMBEDDING_ENGINE": "openai",
        "RAG_OPENAI_API_BASE_URL": GATEWAY_URL,
        "RAG_EMBEDDING_MODEL": "vllm/BAAI/bge-small-en-v1.5",
    }


def test_gateway_embeddings_models_are_not_picked_implicitly():
    inputs = gateway_inputs()
    del inputs["embeddings_api"]

    with pytest.raises(ValidationError, match="embeddings_api"):
        OpenWebUIAppInputs.model_validate(inputs)


@pytest.mark.asyncio
async def test_gateway_needs_a_chat_model_or_a_provider(setup_clients):
    embeddings_only = {
        **GATEWAY_API,
        "models": GATEWAY_API["models"][1:],
        "model_prefixes": [],
    }

    with pytest.raises(ValidationError, match="serves no chat model"):
        OpenWebUIAppInputs.model_validate(gateway_inputs(openai_api=embeddings_only))

    providers_only = {**embeddings_only, "model_prefixes": ["openai/"]}
    env = await generate_env(setup_clients, gateway_inputs(openai_api=providers_only))
    assert env["OPENAI_API_BASE_URL"] == GATEWAY_URL


@pytest.mark.asyncio
async def test_unknown_capability_from_the_gateway_is_accepted(setup_clients):
    gateway = {
        **GATEWAY_API,
        "models": [
            *GATEWAY_API["models"],
            {
                "name": "vllm/BAAI/bge-reranker-base",
                "capabilities": ["rerank"],
                "__type__": "OpenAICompatModel",
            },
        ],
    }

    env = await generate_env(setup_clients, gateway_inputs(openai_api=gateway))

    assert env["OPENAI_API_BASE_URL"] == GATEWAY_URL


def test_gateway_and_chat_api_are_exclusive():
    with pytest.raises(ValidationError, match="either the model gateway API"):
        OpenWebUIAppInputs.model_validate(
            gateway_inputs(llm_chat_api=STORED_INPUTS["llm_chat_api"])
        )


def test_a_chat_source_is_required():
    inputs = gateway_inputs()
    del inputs["openai_api"]

    with pytest.raises(ValidationError, match="either the model gateway API"):
        OpenWebUIAppInputs.model_validate(inputs)


def test_chat_api_without_embeddings_is_rejected():
    inputs = dict(STORED_INPUTS)
    del inputs["embeddings_api"]

    with pytest.raises(ValidationError, match="embeddings_api"):
        OpenWebUIAppInputs.model_validate(inputs)

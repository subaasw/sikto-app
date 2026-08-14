import pytest
from httpx import ASGITransport, AsyncClient

from api.agent.catalog import (
    available_providers,
    lead_with_choice,
    model_choices,
    resolve_model,
)
from api.agent.providers import agent_llm_chain
from api.config import Settings
from api.main import app


def _settings(**overrides: object) -> Settings:
    base = {
        "postgres_user": "u",
        "postgres_db": "d",
        "jwt_secret": "s",
        "nvidia_api_key": "",
        "deepseek_api_key": "",
        "openai_api_key": "",
    }
    return Settings(**{**base, **overrides})  # type: ignore[arg-type]


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def test_no_keys_means_no_providers():
    assert available_providers(_settings()) == []


def test_only_keyed_providers_are_listed():
    providers = available_providers(_settings(deepseek_api_key="k"))
    assert [p.id for p in providers] == ["deepseek"]


def test_all_keyed_providers_listed_with_models():
    providers = available_providers(
        _settings(nvidia_api_key="k", deepseek_api_key="k", openai_api_key="k")
    )
    assert [p.id for p in providers] == ["nvidia", "deepseek", "openai"]
    for provider in providers:
        assert provider.models
        assert provider.default in provider.models


def test_resolve_model_accepts_a_listed_choice():
    settings = _settings(deepseek_api_key="secret")
    choice = next(iter(model_choices(settings)))
    config = resolve_model(settings, choice)
    assert config is not None
    assert config.model == settings.deepseek_model


@pytest.mark.parametrize(
    "choice",
    ["", None, "openai:gpt-4o", "nvidia:anything", "bogus", "deepseek:../../evil"],
)
def test_resolve_model_rejects_unconfigured_or_unknown(choice):
    assert resolve_model(_settings(deepseek_api_key="k"), choice) is None


def test_chosen_model_leads_the_chain_over_the_default():
    settings = _settings(nvidia_api_key="k", deepseek_api_key="k")
    default = agent_llm_chain(settings)
    assert "nvidia" in default[0].base_url

    chain = lead_with_choice(default, settings, "deepseek:deepseek-chat")
    assert chain[0].model == "deepseek-chat"
    assert "deepseek.com" in chain[0].base_url
    assert [c.model for c in chain[1:]] == [c.model for c in default if c.model != "deepseek-chat"]


def test_unknown_choice_leaves_the_default_chain_untouched():
    settings = _settings(nvidia_api_key="k", deepseek_api_key="k")
    default = agent_llm_chain(settings)
    assert lead_with_choice(default, settings, "bogus:model") == default
    assert lead_with_choice(default, settings, None) == default


async def test_providers_endpoint_never_leaks_key_values():
    async with await _client() as client:
        resp = await client.get("/providers")
        assert resp.status_code == 200
        body = resp.text
        for provider in resp.json():
            assert set(provider) == {"id", "label", "models", "default"}
        assert "api_key" not in body

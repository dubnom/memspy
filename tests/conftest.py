from __future__ import annotations

import pathlib
from typing import Any
from unittest.mock import patch

import pytest
from homeassistant import components, loader
from homeassistant.helpers import translation as translation_helper


@pytest.fixture(autouse=True, scope="module")
def evict_faked_translations(translations_once):
    """Clear translation cache entries without crashing on shorter mock call signatures."""
    real_component_strings = translation_helper._async_get_component_strings
    with patch(
        "homeassistant.helpers.translation._async_get_component_strings",
        wraps=real_component_strings,
    ) as mock_component_strings:
        yield

    cache = translations_once.kwargs["return_value"]
    component_paths = components.__path__

    for call in mock_component_strings.mock_calls:
        if len(call.args) < 4:
            continue

        integrations: dict[str, loader.Integration] = call.args[3]
        if not isinstance(integrations, dict):
            continue

        for domain, integration in integrations.items():
            if any(
                pathlib.Path(f"{component_path}/{domain}") == integration.file_path
                for component_path in component_paths
            ):
                continue
            for loaded_for_lang in cache.loaded.values():
                loaded_for_lang.discard(domain)

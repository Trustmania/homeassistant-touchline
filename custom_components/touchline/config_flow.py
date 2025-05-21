"""Config flow for Roth Touchline floor heating controller."""
from __future__ import annotations

import re
from typing import Any

from pytouchline import PyTouchline
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import _LOGGER, DOMAIN

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
    }
)

RESULT_SUCCESS = "success"
RESULT_CANNOT_CONNECT = "cannot_connect"


def _try_connect_and_fetch_basic_info(host):
    """Attempt to connect and, if successful, fetch number of devices."""
    py_touchline = PyTouchline()
    result = {"type": None, "data": {}}
    number_of_devices = None
    device = PyTouchline(id=0)
    try:
        number_of_devices = int(py_touchline.get_number_of_devices(host))
        if number_of_devices:
            device.update()
            result["data"] = device.get_controller_id()
            if result["data"]:
                result["type"] = RESULT_SUCCESS
            return result
    except ConnectionRefusedError:
        _LOGGER.debug(
            "Failed to connect to device %s. Check the IP address "
            "as well as whether the device is connected to power and network",
            host,
        )
        result["type"] = RESULT_CANNOT_CONNECT
    _LOGGER.debug(
        "Number of devices found: %s",
        number_of_devices,
    )
    return result


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Roth Touchline."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=DATA_SCHEMA)

        # Abort if an entry with same host is present.
        self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})

        errors = {}
        host = user_input[CONF_HOST]
        # Remove HTTPS and HTTP schema from URL.
        pattern = "https?://"
        host = re.sub(pattern, "", host)
        host = "http://" + host
        user_input[CONF_HOST] = host
        if not cv.url(host):
            errors["base"] = "invalid_input"
        else:
            self._async_abort_entries_match({CONF_HOST: user_input[CONF_HOST]})
            result = await self.hass.async_add_executor_job(
                _try_connect_and_fetch_basic_info, user_input[CONF_HOST]
            )

            if result["type"] != RESULT_SUCCESS:
                errors["base"] = "cannot_connect"

        if errors:
            return self.async_show_form(
                step_id="user", data_schema=DATA_SCHEMA, errors=errors
            )

        await self.async_set_unique_id(result["data"])
        self._abort_if_unique_id_configured()
        _LOGGER.debug(
            "Host: %s",
            user_input[CONF_HOST],
        )
        return self.async_create_entry(title=host, data=user_input)

    async def async_step_import(self, conf: dict[str, Any]) -> FlowResult:
        """Import a configuration from yaml configuration."""
        return await self.async_step_user(user_input=conf)
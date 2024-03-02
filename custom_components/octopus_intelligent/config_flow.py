"""Config flow for Octopus Intelligent integration."""
from collections import OrderedDict
import logging
from .graphql_client import OctopusEnergyGraphQLClient 

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.const import (
    CONF_ID,
    CONF_API_KEY,
)

import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_ACCOUNT_ID,
    CONF_OFFPEAK_START,
    CONF_OFFPEAK_START_DEFAULT,
    CONF_OFFPEAK_END,
    CONF_OFFPEAK_END_DEFAULT,
    INTELLIGENT_24HR_TIMES
)
from .graphql_util import InvalidAuthError, validate_octopus_account

_LOGGER = logging.getLogger(__name__)

class OctopusIntelligentConfigFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_CLOUD_PUSH

    async def _show_setup_form(self, errors=None):
        """Show the setup form to the user."""
        errors = errors or {}

        fields = OrderedDict()
        fields[vol.Required(CONF_API_KEY)] = str
        fields[vol.Required(CONF_ACCOUNT_ID)] = str
        fields[vol.Required(
                CONF_OFFPEAK_START,
                default=CONF_OFFPEAK_START_DEFAULT,
            )] = vol.In(INTELLIGENT_24HR_TIMES)
        fields[vol.Required(
                CONF_OFFPEAK_END,
                default=CONF_OFFPEAK_END_DEFAULT,
            )] = vol.In(INTELLIGENT_24HR_TIMES)
            

        return self.async_show_form(
            step_id="user", data_schema=vol.Schema(fields), errors=errors
        )

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is None:
            return await self._show_setup_form()

        errors = {}
        try:
            await try_connection(user_input[CONF_API_KEY], user_input[CONF_ACCOUNT_ID])
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.error(ex)
            if isinstance(ex, InvalidAuthError):
                errors["base"] = "invalid_auth"
            else:
                errors["base"] = "unknown"
            return await self._show_setup_form(errors)

        unique_id = user_input[CONF_ACCOUNT_ID]

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title="",
            data={
                CONF_ID: unique_id,
                CONF_API_KEY: user_input[CONF_API_KEY],
                CONF_ACCOUNT_ID: user_input[CONF_ACCOUNT_ID],
                CONF_OFFPEAK_START: user_input[CONF_OFFPEAK_START],
                CONF_OFFPEAK_END: user_input[CONF_OFFPEAK_END],
            })

    # @staticmethod
    # @callback
    # def async_get_options_flow(config_entry):
    #     return GardenaSmartSystemOptionsFlowHandler(config_entry)


# class GardenaSmartSystemOptionsFlowHandler(config_entries.OptionsFlow):
#     def __init__(self, config_entry):
#         """Initialize Gardena Smart Sytem options flow."""
#         self.config_entry = config_entry

#     async def async_step_init(self, user_input=None):
#         """Manage the options."""
#         return await self.async_step_user()

#     async def async_step_user(self, user_input=None):
#         """Handle a flow initialized by the user."""
#         errors = {}
#         if user_input is not None:
#             # TODO: Validate options (min, max values)
#             return self.async_create_entry(title="", data=user_input)

#         fields = OrderedDict()
#         fields[vol.Optional(
#             CONF_MOWER_DURATION,
#             default=self.config_entry.options.get(
#                 CONF_MOWER_DURATION, DEFAULT_MOWER_DURATION))] = cv.positive_int
#         fields[vol.Optional(
#             CONF_SMART_IRRIGATION_DURATION,
#             default=self.config_entry.options.get(
#                 CONF_SMART_IRRIGATION_DURATION, DEFAULT_SMART_IRRIGATION_DURATION))] = cv.positive_int
#         fields[vol.Optional(
#             CONF_SMART_WATERING_DURATION,
#             default=self.config_entry.options.get(
#                 CONF_SMART_WATERING_DURATION, DEFAULT_SMART_WATERING_DURATION))] = cv.positive_int

#         return self.async_show_form(step_id="user", data_schema=vol.Schema(fields), errors=errors)


async def try_connection(api_key: str, account_id: str):
    """Try connecting to the Octopus API and validating the given account_id."""
    _LOGGER.debug("Trying to connect to Octopus during setup")
    client = OctopusEnergyGraphQLClient(api_key)
    await validate_octopus_account(client, account_id)
    _LOGGER.debug("Successfully connected to Octopus during setup")

"""Persistent data storage for the integration, based on the HASS helpers.storage.Store class."""
import logging
from dataclasses import asdict, dataclass
from typing import Any

from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.core import CALLBACK_TYPE, Event, HomeAssistant
from homeassistant.exceptions import IntegrationError
from homeassistant.helpers.storage import Store

from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)


@dataclass
class PersistentData:
    """JSON-serialisable persistent data."""

    last_seen_planned_dispatch_source: str = "smart-charge"

    def set_values(self, data: dict[str, Any]):
        """Assign values from the given dict to this dataclass."""
        # Explicitly assign each field separately instead of using some '**data'
        # unpacking syntax in order to be future-proof against schema changes.
        self.last_seen_planned_dispatch_source = data.get(
            "last_seen_planned_dispatch_source",
            self.last_seen_planned_dispatch_source,
        )


class PersistentDataStore:
    """Wrapper around hass.helpers.storage.Store, with a lazy saving feature.

    Home Assistant may be hosted on an edge device like the Raspberry Pi, with data
    stored on an SD Card that physically "wears" when data is written. To mitigate this
    issue, the lazy save feature delays writting data to "disk" until the HASS STOP event
    is fired, indicating that Home Assistant is about to quit or restart. This includes
    the frontend web UI 'Restart' command, the "docker container stop" command, CTRL-C on
    the command line, and generally when the HASS process receives the SIGTERM signal.
    """

    def __init__(
        self,
        data: PersistentData,
        hass: HomeAssistant,
        account_id: str,
        lazy_save=True,
    ):
        self.data = data
        self._hass = hass
        self._store = Store[dict[str, Any]](
            hass=hass,
            key=f"{DOMAIN}.{account_id}",
            version=1,
            minor_version=1,
        )
        self._stop_event_listener: CALLBACK_TYPE | None = None
        self.lazy_save = lazy_save

    @property
    def lazy_save(self) -> bool:
        """Return whether lazy data saving is enabled."""
        return bool(self._stop_event_listener)

    @lazy_save.setter
    def lazy_save(self, enable: bool):
        """Enable/disable automatically calling self.save() on the HASS STOP event."""

        async def _on_hass_stop(_: Event):
            await self.save(raise_on_error=False)

        if enable:
            self._stop_event_listener = self._hass.bus.async_listen(
                EVENT_HOMEASSISTANT_STOP, _on_hass_stop
            )
        elif self._stop_event_listener:
            self._stop_event_listener()
            self._stop_event_listener = None

    async def load(self):
        """Load the data from persistent storage."""
        data = None
        try:
            data = await self._store.async_load()
        except Exception as ex:  # pylint: disable=broad-exception-caught
            _LOGGER.error(ex)
        if isinstance(data, dict):
            self.data.set_values(data)

    async def save(self, raise_on_error=False):
        """Save the data to persistent storage."""
        try:
            await self._store.async_save(asdict(self.data))
        except Exception as ex:  # pylint: disable=broad-exception-caught
            msg = f"Error saving persistent data: {ex}"
            if raise_on_error:
                raise IntegrationError(msg) from ex
            _LOGGER.error(msg)

    async def remove(self, disable_lazy_save=True):
        """Remove the data from persistent storage (delete the JSON file on disk)."""
        if disable_lazy_save:
            self.lazy_save = False
        try:
            await self._store.async_remove()
        except Exception as ex:  # pylint: disable=broad-exception-caught
            _LOGGER.error("Error removing persistent data: %s", ex)

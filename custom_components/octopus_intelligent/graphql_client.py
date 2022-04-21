import logging
import json
import math
import aiohttp

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from datetime import (timedelta)

_LOGGER = logging.getLogger(__name__)

class OctopusEnergyGraphQLClient:

  def __init__(self, api_key: str):
    if (api_key == None):
      raise Exception('API KEY is not set')

    self._api_key = api_key
    self._base_url = "https://api.octopus.energy/v1/graphql/"

  async def __async_get_token(self):
    """Gets a new token from the API TODO: cache and use refresh token for better API behaviour"""

    transport = AIOHTTPTransport(url=self._base_url)

    # Using `async with` on the client will start a connection on the transport
    # and provide a `session` variable to execute queries on this connection
    async with Client(
      transport=transport,
      fetch_schema_from_transport=True,
    ) as session:

      # Execute single query
      query = gql(
      '''
        mutation krakenTokenAuthentication($apiKey: String!) {
          obtainKrakenToken(input: { APIKey: $apiKey })
          {
            token
          }
        }
      ''')

      params = {"apiKey": self._api_key}

      result = await session.execute(query, variable_values=params, operation_name="krakenTokenAuthentication")
      token = result['obtainKrakenToken']['token']
      return token
      
  async def async_create_session(self):
    """Creates a new session, use with `async with`"""
    token = await self.__async_get_token()
    headers = {"Authorization": token}
    transport = AIOHTTPTransport(url=self._base_url, headers=headers)

    # Using `async with` on the client will start a connection on the transport
    # and provide a `session` variable to execute queries on this connection
    return Client(
      transport=transport,
      fetch_schema_from_transport=True,
    )


  async def async_get_accounts(session):

    # Execute single query
    query = gql(
    '''
        query viewer {
          viewer {
            fullName
            accounts {
              number
            }
          }
        }
    ''')

    params = {}
    result = await session.execute(query, variable_values=params, operation_name="viewer")

    return list(map(lambda x: x['number'], result['viewer']['accounts']))

  async def async_get_charge_preferences(self, session, account_id: str):
    """Gets the charging preferences for the given account"""
    # Execute single query
    query = gql(
    '''
      query vehicleChargingPreferences($accountNumber: String!) {
        vehicleChargingPreferences(accountNumber: $accountNumber) {
          weekdayTargetTime,
          weekdayTargetSoc,
          weekendTargetTime,
          weekendTargetSoc
        }
      }
    ''')

    params = {"accountNumber": account_id}
    result = await session.execute(query, variable_values=params, operation_name="vehicleChargingPreferences")
    return result['vehicleChargingPreferences']

  async def async_set_charge_preferences(self, session, account_id: str, readyByHoursAfterMidnight: float, targetSocPercent: int):
    """Sets the charging preferences for the given account"""
    # Execute single query
    query = gql(
    '''
      mutation setVehicleChargePreferences($accountNumber: String!, $targetTime: String!, $targetSocPercent: Int!) {
        setVehicleChargePreferences(input: { accountNumber: $accountNumber, weekdayTargetTime: $targetTime, weekendTargetTime: $targetTime, weekdayTargetSoc: $targetSocPercent, weekendTargetSoc: $targetSocPercent }) {
          krakenflexDevice {
            krakenflexDeviceId
          }
        }
      }
    ''')

    # round up to nearest 5
    targetSocPercent = 5 * math.ceil(round(targetSocPercent) / 5)
    # round up to nearest 0.5
    readyByHoursAfterMidnight = 0.5 * round(readyByHoursAfterMidnight / 0.5)

    if readyByHoursAfterMidnight < 4 or readyByHoursAfterMidnight > 11:
        raise ValueError("Target time must be between 4AM and 11AM")
    if targetSocPercent < 10 or targetSocPercent > 100:
        raise ValueError("Target SOC percent must be between 10 and 100")

    # get hours
    readyByHoursAfterMidnightHours = int(readyByHoursAfterMidnight)
    # get mins - rounded to nearest 30 mins
    readyByHoursAfterMidnightMinutes = round(30 * (readyByHoursAfterMidnight % 0.5))

    targetTime = f"{readyByHoursAfterMidnightHours:02}:{readyByHoursAfterMidnightMinutes:02}"

    params = {"accountNumber": account_id, "targetTime": targetTime, "targetSocPercent": targetSocPercent}
    result = await session.execute(query, variable_values=params, operation_name="setVehicleChargePreferences")
    return result['setVehicleChargePreferences']
    
  async def async_trigger_boost_charge(self, session, account_id: str):
    """Triggers a boost charge for the given account"""
    # Execute single query
    query = gql(
    '''
      mutation triggerBoostCharge($accountNumber: String!) {
        triggerBoostCharge(input: { accountNumber: $accountNumber }) {
          krakenflexDevice {
            krakenflexDeviceId
          }
        }
      }
    ''')

    params = {"accountNumber": account_id}
    result = await session.execute(query, variable_values=params, operation_name="triggerBoostCharge")
    return result['triggerBoostCharge']
        
  async def async_cancel_boost_charge(self, session, account_id: str):
    """Cancels any boost charge currently in progress for the given account"""
    # Execute single query
    query = gql(
    '''
      mutation deleteBoostCharge($accountNumber: String!) {
        deleteBoostCharge(input: { accountNumber: $accountNumber }) {
          krakenflexDevice {
            krakenflexDeviceId
          }
        }
      }
    ''')

    params = {"accountNumber": account_id}
    result = await session.execute(query, variable_values=params, operation_name="deleteBoostCharge")
    return result['deleteBoostCharge']

  async def async_get_device_info(session, account_id: str):
    """Get the user's device info (e.g. vehicle make, battery size, state etc.)"""
    # Execute single query
    query = gql(
    '''
      query registeredKrakenflexDevice($accountNumber: String!) {
        registeredKrakenflexDevice(accountNumber: $accountNumber) {
          krakenflexDeviceId
          provider
          vehicleMake
          vehicleModel
          vehicleBatterySizeInKwh
          chargePointMake
          chargePointModel
          chargePointPowerInKw
          status
          suspended
          hasToken
          createdAt
        }
      }
    ''')

    params = {"accountNumber": account_id}
    result = await session.execute(query, variable_values=params, operation_name="registeredKrakenflexDevice")
    return result['registeredKrakenflexDevice']


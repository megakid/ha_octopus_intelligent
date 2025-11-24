import logging
import math

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

_LOGGER = logging.getLogger(__name__)

class OctopusEnergyGraphQLClient:

  def __init__(self, api_key: str):
    if (api_key == None):
      raise Exception('API KEY is not set')

    self._api_key = api_key
    self._base_url = "https://api.octopus.energy/v1/graphql/"
    self._login_attempt = 0
    self._session = None

  async def async_get_accounts(self) -> list[str]:
    """Gets the accounts for the given API key"""
    return await self.__async_execute_with_session(self.__async_get_accounts)

  async def async_get_devices(self, account_id: str):
    """Gets the devices for the given account"""
    return await self.__async_execute_with_session(lambda session: self.__async_get_devices(session, account_id))

  async def async_get_combined_state(self, account_id: str, device_id: str = None):
    """Gets the state for the given account"""
    return await self.__async_execute_with_session(lambda session: self.__async_get_combined_state(session, account_id, device_id))

  async def async_get_charge_preferences(self, account_id: str):
    """Gets the charging preferences for the given account"""
    return await self.__async_execute_with_session(lambda session: self.__async_get_charge_preferences(session, account_id))

  async def async_set_charge_preferences(self, account_id: str, readyByHoursAfterMidnight: float, targetSocPercent: int, device_id: str = None):
    """Sets the charging preferences for the given account"""
    return await self.__async_execute_with_session(
      lambda session: self.__async_set_charge_preferences(session, 
        account_id, 
        readyByHoursAfterMidnight, 
        targetSocPercent,
        device_id))
    
  async def async_trigger_boost_charge(self, account_id: str):
    """Triggers a boost charge for the given account"""
    return await self.__async_execute_with_session(lambda session: self.__async_trigger_boost_charge(session, account_id))
    
  async def async_cancel_boost_charge(self, account_id: str):
    """Cancels the boost charge for the given account"""
    return await self.__async_execute_with_session(lambda session: self.__async_cancel_boost_charge(session, account_id))


  async def async_suspend_smart_charging(self, account_id: str, device_id: str = None):
    """Suspends smart charging for the given account"""
    return await self.__async_execute_with_session(lambda session: self.__async_suspend_smart_charging(session, account_id, device_id))

  async def async_resume_smart_charging(self, account_id: str, device_id: str = None):
    """Resumes smart charging for the given account"""
    return await self.__async_execute_with_session(lambda session: self.__async_resume_smart_charging(session, account_id, device_id))

  async def async_get_device_info(self, account_id: str):
    """Gets the device info for the given account"""
    return await self.__async_execute_with_session(lambda session: self.__async_get_device_info(session, account_id))
    

  async def __async_get_token(self):
    """Gets a new token from the API"""
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
      
  async def __async_get_session(self, reset = False):
    """Creates a new session, use with `async with`"""
    if (reset):
      self._session = None

    if (self._session != None):
      return self._session

    token = await self.__async_get_token()
    headers = {"Authorization": token}
    transport = AIOHTTPTransport(url=self._base_url, headers=headers)

    # Using `async with` on the client will start a connection on the transport
    # and provide a `session` variable to execute queries on this connection
    session = Client(
      transport=transport,
      fetch_schema_from_transport=True,
    )
    self._session = session
    return session

  async def __async_execute_with_session(self, func):
    """Executes the given function with a session, auto retrying with a new session if it fails."""
    try:
      async with await self.__async_get_session() as session:
        return await func(session)
    except Exception as e:
      try:
        async with await self.__async_get_session(reset = True) as session:
          return await func(session)
      except Exception as e:
        raise e

  async def __async_set_charge_preferences(self, session, account_id: str, readyByHoursAfterMidnight: float, targetSocPercent: int, device_id: str = None):
    """Sets the charging preferences for the given account"""
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
    readyByHoursAfterMidnightMinutes = round(60 * (readyByHoursAfterMidnight % 1))

    targetTime = f"{readyByHoursAfterMidnightHours:02}:{readyByHoursAfterMidnightMinutes:02}"

    # Retrieve device id for the account if not provided
    if device_id is None:
      device_id = await self.__async_get_device_id(session, account_id)

    if device_id is None:
      raise Exception('Failed to find intelligent device id for account')

    # Build schedules for all days using provided time and percentage
    days_of_week = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY"]
    schedules = ", ".join(list(map(lambda day: f"{{\n  dayOfWeek: {day}\n  time: \"{targetTime}\"\n  max: {targetSocPercent}\n}}", days_of_week)))

    # Execute single query using new mutation
    query_str = f'''
      mutation setDevicePreferences($deviceId: ID!) {{
        setDevicePreferences(input: {{
          deviceId: $deviceId
          mode: CHARGE
          unit: PERCENTAGE
          schedules: [{schedules}]
        }}) {{
          id
        }}
      }}
    '''
    query = gql(query_str)

    params = {"deviceId": device_id}
    result = await session.execute(query, variable_values=params, operation_name="setDevicePreferences")
    return result['setDevicePreferences']
    
  async def __async_trigger_boost_charge(self, session, account_id: str):
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
        
  async def __async_cancel_boost_charge(self, session, account_id: str):
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

  async def __async_get_accounts(self, session):
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

  async def __async_get_charge_preferences(self, session, account_id: str):
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

  async def __async_get_device_info(self, session, account_id: str):
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

  async def __async_get_combined_state(self, session, account_id: str, device_id: str = None):
    """Get the user's account state"""
    
    if device_id:
        # Use new device-specific query
        query = gql(
        '''
        query getDeviceSpecificData($accountNumber: String!, $deviceId: ID!) {
            devices(accountNumber: $accountNumber, deviceId: $deviceId) {
                id
                provider
                deviceType
                status { 
                    current 
                    isSuspended
                    suspended
                }
                ... on SmartFlexVehicle {
                    vehicleMake: make
                    vehicleModel: model
                    vehicleBatterySizeInKwh: batterySize
                    chargingPreferences {
                        weekdayTargetTime
                        weekdayTargetSoc
                        weekendTargetTime
                        weekendTargetSoc
                    }
                }
                ... on SmartFlexChargePoint {
                    chargePointMake: make
                    chargePointModel: model
                    chargePointPowerInKw: powerInKw
                    chargingPreferences {
                        weekdayTargetTime
                        weekdayTargetSoc
                        weekendTargetTime
                        weekendTargetSoc
                    }
                }
            }
            flexPlannedDispatches(deviceId: $deviceId) {
                startDtUtc: start
                endDtUtc: end
                chargeKwh: energyAddedKwh
                source: type
            }
            completedDispatches(accountNumber: $accountNumber) {
                startDtUtc: start
                endDtUtc: end
                chargeKwh: delta
                meta { 
                    source
                    location
                }
            }
        }
        ''')
        
        params = {"accountNumber": account_id, "deviceId": device_id}
        result = await session.execute(query, variable_values=params, operation_name="getDeviceSpecificData")
        
        # Transform to match old structure
        devices = result.get('devices', [])
        device = devices[0] if devices else {}
        
        # Try to find charging preferences in fragments
        charging_preferences = device.get('chargingPreferences', {})

        # Map to registeredKrakenflexDevice format
        registered_device = {
            "krakenflexDeviceId": device.get('id'),
            "provider": device.get('provider'),
            "vehicleMake": device.get('vehicleMake'),
            "vehicleModel": device.get('vehicleModel'),
            "vehicleBatterySizeInKwh": device.get('vehicleBatterySizeInKwh'),
            "chargePointMake": device.get('chargePointMake'),
            "chargePointModel": device.get('chargePointModel'),
            "chargePointPowerInKw": device.get('chargePointPowerInKw'),
            "status": device.get('status', {}).get('current'),
            "suspended": device.get('status', {}).get('isSuspended', device.get('status', {}).get('suspended')),
            "hasToken": True, # Assumption
            "createdAt": None # Not available in this query
        }

        # Map flexPlannedDispatches to plannedDispatches format
        planned_dispatches = []
        for disp in result.get('flexPlannedDispatches', []):
            planned_dispatches.append({
                "startDtUtc": disp.get('startDtUtc'),
                "endDtUtc": disp.get('endDtUtc'),
                "chargeKwh": disp.get('chargeKwh'),
                "meta": {
                    "source": disp.get('source'),
                    "location": None 
                }
            })

        return {
            "vehicleChargingPreferences": charging_preferences,
            "registeredKrakenflexDevice": registered_device,
            "plannedDispatches": planned_dispatches,
            "completedDispatches": result.get('completedDispatches', [])
        }

    # Fallback to old query if no device_id
    query = gql(
    '''
        query getCombinedData($accountNumber: String!) {
            vehicleChargingPreferences(accountNumber: $accountNumber) {
                weekdayTargetTime,
                weekdayTargetSoc,
                weekendTargetTime,
                weekendTargetSoc
            }
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
            plannedDispatches(accountNumber: $accountNumber) {
                startDtUtc: startDt
                endDtUtc: endDt
                chargeKwh: delta
                meta { 
                    source
                    location
                }
            }
            completedDispatches(accountNumber: $accountNumber) {
                startDtUtc: startDt
                endDtUtc: endDt
                chargeKwh: delta
                meta { 
                    source
                    location
                }
            }
        }
    ''')

    params = {"accountNumber": account_id}
    result = await session.execute(query, variable_values=params, operation_name="getCombinedData")
    return result


  async def __async_get_devices(self, session, account_id: str):
    """Retrieve all intelligent devices for account."""
    query = gql(
    '''
      query getDevices($accountNumber: String!) {
        devices(accountNumber: $accountNumber) {
          id
          deviceType
          status { current }
          
          ... on SmartFlexVehicle {
            vehicleMake: make
            vehicleModel: model
          }
          ... on SmartFlexChargePoint {
            chargePointMake: make
            chargePointModel: model
          }
        }
      }
    ''')

    params = {"accountNumber": account_id}
    result = await session.execute(query, variable_values=params, operation_name="getDevices")
    devices = result['devices'] if result is not None and 'devices' in result else []
    
    valid_devices = []
    for device in devices:
        if device is not None and device.get('deviceType') == 'ELECTRIC_VEHICLES' and device.get('status', {}).get('current') == 'LIVE':
             # Normalize make/model
             make = device.get('vehicleMake') or device.get('chargePointMake') or 'Unknown'
             model = device.get('vehicleModel') or device.get('chargePointModel') or 'Vehicle'
             device['vehicleMake'] = make
             device['vehicleModel'] = model
             valid_devices.append(device)
             
    return valid_devices

  async def __async_get_device_id(self, session, account_id: str):
    """Retrieve the new device id for intelligent device for use with mutations."""
    # Prefer new devices query, fallback to krakenflexDeviceId
    try:
      query = gql(
      '''
        query getDevices($accountNumber: String!) {
          devices(accountNumber: $accountNumber) {
            id
            deviceType
            status { current }
            __typename
          }
        }
      ''')

      params = {"accountNumber": account_id}
      result = await session.execute(query, variable_values=params, operation_name="getDevices")
      devices = result['devices'] if result is not None and 'devices' in result else []
      for device in devices:
        if device is not None and device.get('deviceType') == 'ELECTRIC_VEHICLES' and device.get('status', {}).get('current') == 'LIVE':
          return device.get('id')
    except Exception:
      pass

    # Fallback to legacy device id if available (may not work with new mutations)
    info = await self.__async_get_device_info(session, account_id)
    return info['krakenflexDeviceId'] if info is not None and 'krakenflexDeviceId' in info else None



  async def __async_suspend_smart_charging(self, session, account_id: str, device_id: str = None):
    """Suspends smart charging for the given account"""
    # Retrieve device id for the account if not provided
    if device_id is None:
        device_id = await self.__async_get_device_id(session, account_id)
        
    if device_id is None:
      raise Exception('Failed to find intelligent device id for account')

    # Execute single query using new mutation
    query = gql(
    '''      
      mutation updateDeviceSmartControl($deviceId: ID!) {
        updateDeviceSmartControl(input: { deviceId: $deviceId, action: SUSPEND }) {
          id
        }
      }
    ''')

    params = {"deviceId": device_id}
    result = await session.execute(query, variable_values=params, operation_name="updateDeviceSmartControl")
    return result['updateDeviceSmartControl']


  async def __async_resume_smart_charging(self, session, account_id: str, device_id: str = None):
    """Resumes smart charging for the given account"""
    # Retrieve device id for the account if not provided
    if device_id is None:
        device_id = await self.__async_get_device_id(session, account_id)
        
    if device_id is None:
      raise Exception('Failed to find intelligent device id for account')

    # Execute single query using new mutation
    query = gql(
    '''      
      mutation updateDeviceSmartControl($deviceId: ID!) {
        updateDeviceSmartControl(input: { deviceId: $deviceId, action: UNSUSPEND }) {
          id
        }
      }
    ''')

    params = {"deviceId": device_id}
    result = await session.execute(query, variable_values=params, operation_name="updateDeviceSmartControl")
    return result['updateDeviceSmartControl']



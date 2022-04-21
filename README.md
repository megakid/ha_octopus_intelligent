# octopus_intelligent
Octopus Intelligent Home Assistant integration

# TODO

It provides detailed live train departures and journey stats:

```yaml
station_code: WAT
calling_at: WAL
next_trains:
  - origin_name: London Waterloo
    destination_name: Basingstoke
    service_uid: Q46478
    scheduled: 21-01-2022 20:12
    estimated: 21-01-2022 20:12
    minutes: 3
    platform: '10'
    operator_name: South Western Railway
    stops_of_interest: []
    scheduled_arrival: 21-01-2022 20:37
    estimate_arrival: 21-01-2022 20:36
    journey_time_mins: 24
    stops: 2
  - origin_name: London Waterloo
    destination_name: Woking
    service_uid: Q46174
    scheduled: 21-01-2022 20:20
    estimated: 21-01-2022 20:20
    minutes: 11
    platform: '4'
    operator_name: South Western Railway
    stops_of_interest:
      - stop: VXH
        name: Vauxhall
        scheduled_stop: 21-01-2022 20:23
        estimate_stop: 21-01-2022 20:23
        journey_time_mins: 3
        stops: 0
    scheduled_arrival: 21-01-2022 20:54
    estimate_arrival: 21-01-2022 20:53
    journey_time_mins: 33
    stops: 7
unit_of_measurement: min
icon: mdi:train
friendly_name: Next Waterloo train data
```

This Home Assistant integration is only made possible by the brilliant Realtime Trains API (https://api.rtt.io also see https://www.realtimetrains.co.uk) which is maintained by Tom Cairns under swlines Ltd (https://twitter.com/swlines).

Alternatively, you can use the built-in `uk_transport` integration (see https://www.home-assistant.io/integrations/uk_transport/).  NOTE: Unlike this `realtime_trains_api` integration, `uk_transport` cannot provide additional journey details such as stops, journey durations and arrival times.

# Guide

## Installation & Usage

1. Signup to https://api.rtt.io
2. Add repository to HACS (see https://hacs.xyz/docs/faq/custom_repositories) - use "https://github.com/megakid/ha_realtime_trains_api" as the repository URL.
3. Install the `realtime_trains_api` integration inside HACS
5. To your HA `configuration.yaml`, add the following:
```yaml
sensor:
  - platform: realtime_trains_api
    username: '[Your RTT API Auth Credentials username]'
    password: '[Your RTT API Auth Credentials password]' # (recommended to use '!secret my_rtt_password' and add to secrets.yaml)
    scan_interval:
      seconds: 90 # this defaults to 60 seconds (in HA) so you can change this.  Dont set it too frequent or you might get blocked for abuse of the RTT API.
    queries:
      - origin: WAL
        destination: WAT
        # journey_data_for_next_X_trains is optional but highly recommended, 
        # Defaults to 0. 
        # Entering 5 here means the first 5 departures from the origin 
        # (WAL in this case) to destination (WAT in this case) will hit 
        # the API to lookup the number of stops, journey time and estimated
        # arrival time to the destination (WAT in this case).
        journey_data_for_next_X_trains: 5 
        auto_adjust_scans: true # If no depatures are retrieved, back off polling interval to 30 mins (until there are some trains)
        stops_of_interest:
          - VXH # a stop_of_interest will add data about this stop to each train's data (only if journey_data is gathered for that journey).  Means you can add more context to the train journey (e.g. my commute can start at two stops for some trains, only one for others meaning it might change my choice of train if I can get on at VXH instead of WAT)
      - origin: WAT
        destination: WAL
        sensor_name: My Custom Journey # this will appear as 'sensor.my_custom_journey'
        time_offset:
          minutes: 20 # This will display departures from now+20 minutes - useful if the station is 20 minutes travel/walk away.
```
6. Restart HA
7. Your `sensor` will be named something like `sensor.next_train_from_wal_to_wat` (unless you specified a `sensor_name`) for each query you defined in your configuration.# ha_octopus_intelligent

# octopus_intelligent
Octopus Intelligent Home Assistant integration

* `binary_sensor.octopus_intelligent_slot` - will be `on` when your electricity is cheap. This includes when your car is charging outside of the normal Octopus Intelligent offpeak times but NOT when bump charging (unless within off peak hours)

NOTE: It has come to my attention that, when outside core offpeak hours (2330 -> 0530), if your car does not successfully charge during the planned slots then your usage will be billed at peak pricing.  This means that if charging is unreliable then the sensor won't reflect your billing accurately.

* `switch.octopus_intelligent_bump_charge` and `switch.octopus_intelligent_smart_charging` - controls your Octopus Intelligent bump charge and smart charge settings

* `select.octopus_intelligent_target_time` and `select.octopus_intelligent_target_soc` - controls your Octopus Intelligent target ready time and SoC %.

<img width="850" alt="image" src="https://user-images.githubusercontent.com/1478003/166564194-c7d9f4a6-31af-42d6-9ccc-a8b81324385d.png">

# Guide

## Installation & Usage

1. Add repository to HACS (see https://hacs.xyz/docs/faq/custom_repositories) - use "https://github.com/megakid/ha_octopus_intelligent" as the repository URL.
2. Install the `octopus_intelligent` integration inside HACS (You do NOT need to restart despite HACS saying so)
3. Goto Integrations page and add "Octopus Intelligent Tariff" integration as with any other integration
4. Follow config steps (Your octopus api key and account id can be found here: https://octopus.energy/dashboard/developer/)

NOTE: Your api_key and account_id is stored strictly within your Home Assistant and does not get stored elsewhere.  It is only sent directly to the official Octopus API to exchange it for a authentication token necessary to use the API.

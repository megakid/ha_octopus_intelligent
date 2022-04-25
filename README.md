# octopus_intelligent
Octopus Intelligent Home Assistant integration

`binary_sensor.octopus_intelligent_slot` - will be `on` when your electricity is cheap (this includes when your car is charging outside of the normal Octopus Intelligent offpeak times)
`button.start_bump_charge` and `button.cancel_bump_charge` - controls your Octopus Intelligent bump charge settings
`select.target_ready_by_time` and `select.target_state_of_charge` - controls your Octopus Intelligent target ready time and SoC %.

# Guide

## Installation & Usage

1. Add repository to HACS (see https://hacs.xyz/docs/faq/custom_repositories) - use "https://github.com/megakid/ha_octopus_intelligent" as the repository URL.
2. Install the `octopus_intelligent` integration inside HACS
3. Goto Integrations page and add "Octopus Intelligent Tariff" integration as with any other integration
4. Follow config steps (Your octopus api key and account id can be found here: https://octopus.energy/dashboard/developer/)

NOTE: Your api_key and account_id is stored strictly within your Home Assistant and does not get stored elsewhere.  It is only sent directly to the official Octopus API to exchange it for a authentication token necessary to use the API.
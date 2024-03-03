#!/usr/bin/env bash

# Use this script to start Home Assistant in a VS Code devcontainer.

REPO_DIR="$( cd -- "$(dirname "$0")/.." >/dev/null 2>&1 ; pwd -P )"
HASS='hass'
CONFIG_DIR='/config'
CONFIG_FILE="${CONFIG_DIR}/configuration.yaml"
LOGGER_CONFIG='
logger:
  logs:
    custom_components.octopus_intelligent: debug'

function log_cmd {
	set -x
	"$@"
	{ set +x; } 2>/dev/null
}

# Ensure that 'configuration.yaml' has a 'logger:' section to set log levels.
function edit_hass_config {
	if ! [ -f "${CONFIG_FILE}" ]; then
		log_cmd "${HASS}" --config "${CONFIG_DIR}" --script ensure_config
	fi
	# Add a `logger:` section to configuration.yaml if one is missing.
	if [ "$(yq '.logger' "${CONFIG_FILE}")" = null ]; then
		cat >>"${CONFIG_FILE}" <<<"${LOGGER_CONFIG}"
	fi
}

function main {
	edit_hass_config
	# Add the 'custom_components' folder to PYTHONPATH so that HASS can find
	# the integration without the need for soft links in the config folder.
	export PYTHONPATH="${PYTHONPATH}:${REPO_DIR}/custom_components"
	echo '
=================================================================================
Starting Home Assistant... Visit http://localhost:8123 in a browser on the host.
=================================================================================
'
	# Start Home Assistant. See 'hass --help' for options like '--debug'.
	log_cmd "${HASS}" --config "${CONFIG_DIR}"
}

main

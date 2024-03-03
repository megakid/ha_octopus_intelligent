# VS Code devcontainer development

The goal is to make it easier and reproducible to test this integration with a Home
Assistant instance running in a Docker container. The use of a VS Code devcontainer also
allows developers to share some aspects of the development environment configuration, such
as relevant VS Code extensions and settings.

About VS Code devcontainers: 
https://code.visualstudio.com/docs/devcontainers/containers

# Base image: HASS vs generic Python devcontainer

Typical VS Code devcontainers would use a generic Microsoft VS Code devcontainer image
such as `mcr.microsoft.com/vscode/devcontainers/python:1-3`. Indeed, the Home Assistant
core project itself uses such a base image
([Dockerfile.dev](https://github.com/home-assistant/core/blob/2024.2.5/Dockerfile.dev#L1)).

However, using a generic Python base image means having to install Home Assistant and its
dependencies, and there are many of them as can be seen in the Home Assistant core
[Dockerfile.dev](https://github.com/home-assistant/core/blob/2024.2.5/Dockerfile.dev)
file. On a laptop, building that image can take a discouraging 10+ minutes. Subsequent
container rebuilds are faster due to caching, but it's still not a great experience. (The
most time consuming part being the `pip install` steps, especially where some dependencies
require building Python wheels from source.)

To save time and improve the experience, the Dockerfile on this folder uses the official
production HASS image (`ghcr.io/home-assistant/home-assistant`) as the devcontainer base
image. Testing so far was limited but encouraging: VS Code detects if some devcontainer
dependencies (needed by VS Code itself) are missing in the base image and installs them
automatically. This is a lot faster than installing Home Assistant on a generic Python
devcontainer image — from 10+ minutes to under a minute.

# Run Home Assistant in the devcontainer

The usual VS Code palette command _"Dev Containers: Rebuild and Reopen in Container"_ can
be used to build the container image. Once VS Code opens a terminal prompt on the
container, start Home Assistant by running the `start_ha.sh` script (located in the same
folder as this README file):

```
7e4fa12090b1:/workspaces/ha_octopus_intelligent# .devcontainer/start_ha.sh 
+ hass --config /config --script ensure_config
Unable to find configuration. Creating default one in /config
Configuration file: True

=================================================================================
Starting Home Assistant... Visit http://localhost:8123 in a browser on the host.
=================================================================================

+ hass --config /config
2024-03-03 15:58:34.589 WARNING (SyncWorker_2) [homeassistant.loader] We found a custom integration octopus_intelligent which has not been tested by Home Assistant. This component might cause stability problems, be sure to disable it if you experience issues with Home Assistant
```

TCP port 8123 is exported to the host. On the host (outside the container), point a web
browser to http://localhost:8123. You should see the HASS onboarding web UI to create a
user account. The integration should be visible to HASS as explained below, so simply
search for it in Settings > Integrations > Add Integration.

# configuration.yaml and custom_components

When executed for the first time, the `start_ha.sh` script will create a default
`/config/configuration.yaml` file and will add a `logger:` section to it in order to set
the Octopus Intelligent integration log level to `'debug'`. The script also sets the
`PYTHONPATH` environment variable to point to the the `custom_components` folder in this
repo, so that it is visible to Home Assistant for installation without the need of soft
links, bind mounts, HACS store, or manual installation steps.

# Home Assistant source and intellisense

The Home Assistant source code can be found in the devcontainer at `/usr/src/homeassistant`
and you can browse and edit it directly from VS Code (for example, in order to add extra
debug logging). Any such changes are lost when the devcontainer is rebuilt.

Pylance "intellisense" is available. If it does not seem to work right after the
devcontainer is built for the first time, try closing and reopening the VS Code window.
It should take less than a minute for intellisense to index the dependencies.

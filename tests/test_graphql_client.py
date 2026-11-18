"""GraphQL client tests against a local fake Octopus API."""
import pytest
from aiohttp import web

from custom_components.octopus_intelligent.graphql_client import (
    OctopusEnergyGraphQLClient,
)

# What the schema introspection looks like after Octopus adds a directive
# location that graphql-core does not know about (issue #77).
_UNPARSEABLE_INTROSPECTION = {
    "data": {
        "__schema": {
            "queryType": {"name": "Query"},
            "mutationType": None,
            "subscriptionType": None,
            "types": [
                {
                    "kind": "OBJECT",
                    "name": "Query",
                    "fields": [
                        {
                            "name": "viewer",
                            "args": [],
                            "type": {"kind": "SCALAR", "name": "String", "ofType": None},
                            "isDeprecated": False,
                        }
                    ],
                    "interfaces": [],
                },
                {"kind": "SCALAR", "name": "String"},
            ],
            "directives": [
                {
                    "name": "deprecated",
                    "args": [],
                    "locations": ["A_LOCATION_GRAPHQL_CORE_DOES_NOT_KNOW"],
                }
            ],
        }
    }
}


async def _handle(request: web.Request) -> web.Response:
    body = await request.json()
    query = body["query"]
    if "__schema" in query:
        return web.json_response(_UNPARSEABLE_INTROSPECTION)
    if "obtainKrakenToken" in query:
        return web.json_response({"data": {"obtainKrakenToken": {"token": "tok"}}})
    return web.json_response(
        {"data": {"viewer": {"fullName": "Test", "accounts": [{"number": "A-1234"}]}}}
    )


@pytest.fixture
async def fake_octopus_url(socket_enabled):
    app = web.Application()
    app.router.add_post("/graphql/", _handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = site._server.sockets[0].getsockname()[1]
    try:
        yield f"http://127.0.0.1:{port}/graphql/"
    finally:
        await runner.cleanup()


async def test_client_does_not_depend_on_schema_introspection(fake_octopus_url):
    """A schema graphql-core cannot parse must not break login or queries."""
    client = OctopusEnergyGraphQLClient("api-key")
    client._base_url = fake_octopus_url

    assert await client.async_get_accounts() == ["A-1234"]

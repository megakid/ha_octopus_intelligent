"""Validation and parsing for the Octopus GraphQL API."""
from ast import literal_eval
from pprint import pformat

from gql.transport.exceptions import TransportQueryError

from .graphql_client import OctopusEnergyGraphQLClient


class InvalidAuthError(Exception):
    """Invalid Octopus API key or account number."""


async def validate_octopus_account(client: OctopusEnergyGraphQLClient, account_id: str):
    """Check that the Octopus account_id matches the authenticated API."""
    try:
        accounts = await client.async_get_accounts()
    except TransportQueryError as ex:
        msg = parse_gql_query_error(ex, "Authentication failed")
        raise InvalidAuthError(msg) from ex
    if account_id not in accounts:
        raise InvalidAuthError(
            f"Account '{account_id}' not found in accounts {accounts}"
        )


def parse_gql_query_error(error: TransportQueryError, default_title: str) -> str:
    """Format a GQL JSON-like error response into something arguably readable for logging.

    Sample formatted return value:

    Authentication failed:
    {'message': 'Invalid data.',
     'path': ['obtainKrakenToken'],
     'extensions': {'errorType': 'VALIDATION',
                    'errorCode': 'KT-CT-1139',
                    'errorDescription': 'Authentication failed.',
                    'errorClass': 'VALIDATION',
                    'validationErrors': [{'message': 'Authentication failed.',
                                          'inputPath': ['input', 'apiKey']}]}}
    """
    err_str = str(error)
    if len(err_str) > 500:  # Some protection against wild inputs
        return err_str
    try:
        # Using ast.literal_eval() instead of json.loads() because the GQL
        # response uses single quotes in object notation, and quote replacement
        # may go wrong if the error messages include quotes.
        obj = literal_eval(err_str)
        if not isinstance(obj, dict):
            return err_str
        if "locations" in obj:
            del obj["locations"]  # Noise
        exts = obj.get("extensions", {})
        title = exts.get("errorDescription", "") if isinstance(exts, dict) else ""
        if isinstance(title, str) and len(title) > 1:
            title = title.rstrip(".") or default_title
        else:
            title = default_title
        body = pformat(obj, sort_dicts=False)
        return f"{title}:\n{body}"
    except Exception:  # pylint: disable=broad-except
        return err_str

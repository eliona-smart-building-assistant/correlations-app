import logging
import os
from eliona.api_client2 import (
    AppsApi,
    ApiClient,
    Configuration,
)


host = os.getenv("API_ENDPOINT")
api_key = os.getenv("API_TOKEN")


configuration = Configuration(host=host)
configuration.api_key["ApiKeyAuth"] = api_key
api_client = ApiClient(configuration)


apps_api = AppsApi(api_client)


# Initialize the logger
logger = logging.getLogger(__name__)


def Initialize():

    app = apps_api.get_app_by_name("correlations")

    if not app.registered:
        apps_api.patch_app_by_name("correlations", True)
        logger.info("App 'correlations' registered.")

    else:
        logger.info("App 'correlations' already active.")

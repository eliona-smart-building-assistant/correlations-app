
import eliona.api_client2

from eliona.api_client2.api.assets_api import AssetsApi


from eliona.api_client2 import ApiClient,AssetsApi
from eliona.api_client2.models import Asset
import os


# Set up configuration for the Eliona API
configuration = eliona.api_client2.Configuration(host=os.getenv("API_ENDPOINT"))
configuration.api_key["ApiKeyAuth"] = os.getenv("API_TOKEN")

# Create an instance of the API client
api_client = eliona.api_client2.ApiClient(configuration)
assets_api = AssetsApi(api_client)



def create_asset_to_save_reports(project_id, correlation_id):

    with ApiClient(configuration) as api_client:
        assets_api = AssetsApi(api_client)
        gai_name = f"correlation_reports_{correlation_id}"
        project_id=str(project_id),
        asset = Asset(
            global_asset_identifier=gai_name,
            project_id=project_id,
            asset_type="Space",
            name=gai_name,
            description="This asset is used to store the Reports of the correlation",
        )

        asset = assets_api.put_asset(asset)
        print(asset)
        return asset


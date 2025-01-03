import os
import uvicorn
from register_app import Initialize


def start_api():
    port = int(os.getenv("API_SERVER_PORT", 3000))
    uvicorn.run("api.openapi:app", host="0.0.0.0", port=port)


Initialize()
start_api()

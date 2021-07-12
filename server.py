import aiohttp.web
import aiohttp
from aiohttp.web_request import Request  # the joy of typings
import json
import datetime
from typing import Callable

responses: dict[str, Callable[[dict], str]] = {
    "GetTime": lambda body: f"The time is {datetime.datetime.utcnow().strftime('%-H %-M')}"
}

async def handler(request: Request):
    body = await request.json()
    intent = body["intent"]["name"]
    
    return_text = responses[intent](body)
    print(return_text)
    resp = json.dumps({
        "speech": {
            "text": return_text
        }
    })

    return aiohttp.web.Response(body=resp, headers={"Content-Type": "application/json"})

app = aiohttp.web.Application()
app.add_routes([aiohttp.web.post('/', handler)])
aiohttp.web.run_app(app, port=8080)

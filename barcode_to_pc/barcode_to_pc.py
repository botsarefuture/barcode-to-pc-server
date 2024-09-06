import logging
import asyncio
from aiohttp import web, WSMsgType
import json
from zeroconf import ServiceInfo, Zeroconf
import socket


async def websocket_handler(request):
    ws = web.WebSocketResponse(autoping=True)
    await ws.prepare(request)

    queue: asyncio.Queue = request.app["queue"]

    async for msg in ws:
        if msg.type == WSMsgType.TEXT:
            data = json.loads(msg.data)
            action = data.get("action")

            request.app.logger.debug(f"Received action: {action}")

            response = {}

            if action == "helo":
                request.app.logger.debug(
                    f"helo {data.get('version')} {data.get('deviceName')} {data.get('deviceId')}"
                )
                response = {
                    "action": "helo",
                    "version": "0.9",
                    # 'outputProfiles': [ ... ]
                }
            elif action == "ping":
                request.app.logger.debug("ping")
                response = {"action": "pong"}
            elif action == "getVersion":
                request.app.logger.debug("getVersion")
            elif action == "deleteScan":
                request.app.logger.debug(
                    f"deleteScan {data.get('scanSessionId')} {data.get('scan')}"
                )
            elif action == "deleteScanSessions":
                request.app.logger.debug(
                    f"deleteScanSessions {data.get('scanSessionIds')}"
                )
            elif action == "putScanSessions":
                request.app.logger.debug(
                    f"putScanSessions {data.get('sendKeystrokes')} {data.get('deviceId')}"
                )
                for session in data.get("scanSessions", []):
                    request.app.logger.debug(
                        f"{session['id']} {session['name']} {session['date']} {session['selected']}"
                    )
                    for scanning in session.get("scannings", []):
                        request.app.logger.debug(
                            f"{scanning['id']} {scanning['repeated']} {scanning['date']} {scanning['text']} {scanning['displayValue']}"
                        )
                        queue.put_nowait(scanning["text"])
            elif action == "updateScanSession":
                request.app.logger.debug(f"updateScanSession {data}")
            elif action == "clearScanSessions":
                request.app.logger.debug(f"clearScanSessions {data}")
            else:
                request.app.logger.debug(f"Unknown action: {data}")
                await ws.close()
                continue

            await ws.send_str(json.dumps(response))

        elif msg.type == WSMsgType.ERROR:
            request.app.logger.info(
                f"WebSocket connection closed with exception: {ws.exception()}"
            )

    request.app.logger.info("WebSocket connection closed")

    return ws


class Server:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # self.logger.setLevel(logging.DEBUG)

        self.TYPE = "_http._tcp.local."
        self.info = ServiceInfo(
            type_=self.TYPE,
            name=f"barcode-to-pc-server.{self.TYPE}",
            server=socket.gethostname(),
            port=57891,
            properties={"path": "/"},
        )
        self.zeroconf = Zeroconf()

    async def start(self, queue: asyncio.Queue, loop=None):
        self.logger.debug("Starting server")
        app = web.Application(logger=self.logger, loop=loop)
        app["queue"] = queue
        app.add_routes([web.get("/", websocket_handler)])

        self.runner = web.AppRunner(app)
        self.logger.info("Registering service...")
        self.zeroconf.register_service(self.info)

        await self.runner.setup()
        self.site = web.TCPSite(self.runner, port=57891, reuse_address=True)
        self.logger.debug("Starting site...")
        await self.site.start()

    async def stop(self):
        self.logger.debug("Stopping server")
        await self.runner.cleanup()
        self.logger.info("Unregistering service...")
        self.zeroconf.unregister_service(self.info)
        self.zeroconf.close()

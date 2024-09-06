#!/usr/bin/env python3.7
# Install dependencies with: python3.7 -m pip install zeroconf aiohttp

import logging
import asyncio
from barcode_to_pc.barcode_to_pc import Server


async def main(server: Server):
    queue = asyncio.Queue()

    async def print_codes():
        while True:
            code = await queue.get()
            print(code)

    await server.start(queue)
    await print_codes()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    server = Server()

    try:
        asyncio.run(main(server))
    except KeyboardInterrupt:
        logging.info("Shutting down server due to KeyboardInterrupt")
    finally:
        # Ensure the server stops gracefully
        asyncio.run(server.stop())

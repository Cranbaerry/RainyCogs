import sys
import discord
import logging
import asyncio
from redbot.core import commands
from TikTokApi import TikTokApi

from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
driver = webdriver.Chrome(ChromeDriverManager().install())


class tiktok(commands.Cog):
    # init method or constructor
    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.bot = bot
        self.log = logging.getLogger("red")
        self.api = TikTokApi.get_instance(use_test_endpoints=True, custom_verifyFp="verify_adjaksdjakwj", use_selenium=True)

        if __name__ != "__main__":
            self.socket_task = self.bot.loop.create_task(self.wsrun())

    async def run(self):
        data = self.api.trending()
        self.log.debug(data[0]['author']['uniqueId'])

    def cog_unload(self):
        self.log.debug("[TikTok] Shutting down websocket server..")
        self.socket_task.cancel()


if __name__ == "__main__":
    main = tiktok(None)

    log_format = logging.Formatter('[%(asctime)s] [%(levelname)s]: %(message)s')
    main.log.setLevel(logging.DEBUG)

    # writing to stdout
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    handler.setFormatter(log_format)
    main.log.addHandler(handler)

    #loop = asyncio.get_event_loop()
    #loop.run_until_complete(main.main2())
    asyncio.run(main.run())


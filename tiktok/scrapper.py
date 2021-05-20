from TikTokApi import TikTokApi
import websockets
import asyncio
import platform
import logging
import sys
import os
import atexit


#from selenium import webdriver
#from webdriver_manager.chrome import ChromeDriverManager
#driver = webdriver.Chrome(ChromeDriverManager().install())


async def echo(websocket, path):
    try:
        log.debug("Client connection established")
        while True:
            await websocket.send("Hello")
            get_tiktok_by_name("discord")
            asyncio.sleep(1)
    except (websockets.exceptions.ConnectionClosedError, websockets.exceptions.ConnectionClosed):
        log.debug("Client connection closed")


async def echo_server(stop):
    async with websockets.serve(echo, "localhost", 8765):
        log.debug("Serving websocket on port 8765")
        log.debug("File: " + os.getcwd() + r'\driver\chromedriver')
        get_tiktok_by_name("discord", 1)
        # api.browser.browser.quit()
        await stop


def get_tiktok_by_name(username, count):
    for tiktok in api.byUsername(username, count=count):
        log.debug(tiktok)


def exit_handler():
    api.browser.browser.quit()


log = logging.getLogger("scrapper")
log_format = logging.Formatter('[%(asctime)s] [%(levelname)s]: %(message)s')
log.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)
handler.setFormatter(log_format)
#log.addHandler(handler)

loop = asyncio.get_event_loop()
atexit.register(exit_handler)

log.debug("System platform: %s" % platform.system())
if platform.system() == 'Windows':
    import threading

    stop_event = threading.Event()
    stop = asyncio.get_event_loop().run_in_executor(None, stop_event.wait)
    #driver = os.getcwd() + r'\driver\chromedriver_win'
    # stop_event.set()
elif platform.system() == "Linux":
    # The stop condition is set when receiving SIGTERM.
    # https://stackoverflow.com/questions/56663152/how-to-stop-websocket-server-created-with-websockets-serve
    import signal

    stop = loop.create_future()
    loop.add_signal_handler(signal.SIGTERM, stop.set_result, None)
    #driver = os.getcwd() + r'\driver\chromedriver_linux'
    # loop.close()

api = TikTokApi.get_instance(use_test_endpoints=True, custom_verifyFp="verify_adjaksdjakwj", use_selenium=True,
                             logging_level=logging.DEBUG, executablePath=ChromeDriverManager().install())


# Run the server until the stop condition is met.
loop.run_until_complete(echo_server(stop))
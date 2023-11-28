import json, logging, pickle, asyncio

# updatable settings
class ConfigLoader:
    def __init__(self, config_path):
        self.config_path = config_path
        self.load_config()

    def load_config(self):
        with open(self.config_path, "r") as file:
            self.config = json.load(file)

        # Webull login
        self.email = self.config['config']['login']['email']
        self.password = self.config['config']['login']['password']
        self.did = self.config['config']['login']['did']
        self.pin = self.config['config']['login']['trading_pin']

        # order settings
        self.auto_cancel_order = self.config['config']['auto_cancel_order']
        self.frequency = self.config['config']['frequency']
        self.api_type = self.config['config']['api_type']
        self.bto_offset = self.config['config']['bto_offset']
        self.stc_offset = self.config['config']['stc_offset']
        self.max_per_trade = self.config['config']['max_per_trade']

        # Paths
        self.csv_path = self.config['config']['csv_path']
        self.variable_path = self.config['config']['variable_path']

        # debug/logger
        self.debug = self.config['config']['debug']
        self.format = self.config['config']['log_format']
        self.log_path = self.config['config']['log_path']

        # info
        self.tickers = self.config['tickers']
        self.keywords = self.config['triggers']

    def reload_config(self):
        self.load_config()

        from modules.handler import Handler
        from modules.manager import Manager

        Handler().update_vars()
        Manager().update_vars()
        
        return True

config_path = ""
config = ConfigLoader(config_path)
wb = None
with open(config.variable_path, 'rb') as file:
    current_positions = pickle.load(file)

# logger
logger = logging.getLogger(__name__)
formatter = logging.Formatter(config.format, datefmt="%m-%d %H:%M:%S")
file_handler = logging.FileHandler(config.log_path, encoding='utf-8')
file_handler.setFormatter(formatter)
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.DEBUG if config.debug is True else logging.INFO)
logger.addHandler(stream_handler)
logger.setLevel(logging.DEBUG)

# api login
def login(refresh_session=None):
    global wb
    from api import paper_webull, webull
    if not wb or refresh_session is not None: 
        if config.api_type == 'paper':
            wb = paper_webull(username=config.email, password=config.password, did=config.did)
        elif config.api_type == 'live':
            wb = webull(username=config.email, password=config.password, did=config.did, pin=config.pin)
    return wb

async def ask_entry():
    from modules.handler import Handler
    entry = input('> ').lower()
    if entry:
        await Handler().handle_message(entry)

if __name__ == '__main__':
    while True:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(ask_entry())
        loop.close()
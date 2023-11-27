import unittest, pytest, asyncio
from modules.handler import Handler

handler = Handler()

class TestPositionFunctions(unittest.TestCase):
    def test_input(self):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        normal_input = 'buy SPX 4490p @ 0.01'
        loop.run_until_complete(handler.handle_message(normal_input))

        missing_entry_keyword = 'SPX 4490p @ 0.01'
        loop.run_until_complete(handler.handle_message(missing_entry_keyword))

        missing_ticker_keyword = 'buy 4490p @ 0.01'
        loop.run_until_complete(handler.handle_message(missing_ticker_keyword))

        missing_strike_keyword = 'buy SPX @ 0.01'
        loop.run_until_complete(handler.handle_message(missing_strike_keyword))

        missing_lmt_price = 'buy SPX 4490p'
        loop.run_until_complete(handler.handle_message(missing_lmt_price))
        loop.close()

    def test_command(self):
        pass

if __name__ == '__main__':
    unittest.main()

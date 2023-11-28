import traceback, pickle, asyncio

import main
from . import error

class Manager:

    def __init__(self) -> None:
        self.update_vars()

    def update_vars(self):
        self.config = main.config
        self.logger = main.logger
        self.variable_path = main.config.variable_path
        self.frequency = main.config.frequency
        self.wb = main.login()
        self.auto_cancel_order = main.config.auto_cancel_order
        with open(self.variable_path, 'rb') as file:
            self.current_positions: list = pickle.load(file)

    async def mkt_order(self, ticker_id, action, quant, contract):
        await self.wb.place_order_option(
            optionId=ticker_id, 
            action=action, 
            orderType='MKT', 
            quant=quant,
            contract=contract
        )

    async def lmt_order(self, ticker_id, lmt_price, action, quant, contract):
        await self.wb.place_order_option(
            optionId=ticker_id, 
            lmtPrice=lmt_price, 
            action=action, 
            orderType='LMT',
            quant=quant,
            contract=contract
        )

    def new_position(self, ticker_id):
        self.current_positions.append(ticker_id)
        with open(self.variable_path, 'wb') as file:
            pickle.dump(self.current_positions, file)

        self.logger.debug(f'New position appended to monitor: {ticker_id}')
        self.logger.debug(f'New current positions list: {self.current_positions}')

    def remove_position(self, ticker: int):
        if ticker in self.current_positions:
            self.current_positions.remove(ticker)
            with open(self.variable_path, 'wb') as file:
                pickle.dump(self.current_positions, file)

            self.logger.debug(f'Position removed from monitor: {ticker}')
            self.logger.debug(f'New current positions list: {self.current_positions}')

        else:   
            self.logger.warning(f'Position not found in monitor: {ticker}')
            self.logger.warning(f'Current positions list: {self.current_positions}')

    async def check_order(self, orderID, action, contract, tickerID):
        try:
            for i in range(self.frequency[1]):
                await asyncio.sleep(self.frequency[0])
                past = self.wb.get_history_orders(status='Filled', count=10, action=action)
                for order in [o for o in past if o['orderId'] == int(orderID) and self.auto_cancel_order is True]:
                    self.logger.info(f'''{action} order {orderID} filled
    ----------------
    Contract: {contract}
    Total value: {order['filledValue']}
    Average fill: {round(float(order['avgFilledPrice']), 2)}
    ----------------''')
                    
                    if orderID not in self.current_positions:
                        self.new_position(tickerID)
                    else:
                        self.remove_position(tickerID)
                    return

            if action == 'BUY' and self.wb.cancel_order(orderID) is True:
                raise error.OrderFailedError(f'Cancelling order {orderID} as it was not filled.')
            
        except error.OrderFailedError as e:
            line_number = (traceback.extract_tb(e.__traceback__))[-1][1]
            self.logger.error(f'Order failed: {e}')
            return None, None
        except Exception as e:
            line_number = (traceback.extract_tb(e.__traceback__))[-1][1]
            self.logger.error(f'{type(e).__name__} occurred on line {line_number}: {e}')
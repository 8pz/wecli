import re, traceback, math
from datetime import datetime

import main
from . import utils as error
from .manager import Manager

manager = Manager()

class Handler:
        
    def __init__(self) -> None:
        self.update_vars()

    def update_vars(self):
        self.email = main.config.email
        self.password = main.config.password
        self.wb = main.login()
        self.offset = main.config.bto_offset
        self.logger = main.logger
        self.max_per_trade = main.config.max_per_trade
        self.ticker_list = main.config.tickers
        self.keywords: dict = main.config.keywords

    async def handle_message(self, content: str):
        try:
            ticker = ''
            direction = ''
            exp_date = ''
            strike_price = ''
            lmt_price = ''
            ticker_id = ''

            msgs = content.split(" ")

            for ticker in [t for t in self.ticker_list if t.lower() in content]:
                self.logger.debug(f"Ticker found: {ticker}")
                break

            for msg in msgs:
                try:
                    if "/" in msg and bool(re.search(r"\d", msg)):
                        exp_date = (datetime.strptime(msg, "%m/%d")).strftime("2023-%m-%d")                          
                        self.logger.debug(f"Expiration date found: {exp_date}")

                    elif ("c" in msg or "p" in msg) and bool(re.search(r"\d", msg)) and not strike_price:
                        strike_price = str(re.sub(r"[a-zA-Z]", "", msg)).rstrip('0').rstrip('.') if '.' in str(re.sub(r"[a-zA-Z]", "", msg)) else str(re.sub(r"[a-zA-Z]", "", msg))
                        direction = "call" if "c" in msg else "put"
                        self.logger.debug(f"Strike and direction found: {strike_price}, {direction}")

                    elif "." in msg and bool(re.search(r"\d", msg)) and not lmt_price:
                        lmt_price = round(float(msg) + self.offset, 2)
                        self.logger.debug(f"Limit price found: {lmt_price}")

                    elif msg.isdigit() and not ticker_id:
                        ticker_id = int(msg)
                        self.logger.debug(f"Ticker ID found: {ticker_id}")
                except Exception as e:
                    line_number = (traceback.extract_tb(e.__traceback__))[-1][1]
                    self.logger.warning(f'{type(e).__name__} occured on line {line_number}: {e}')

            for trigger, value in self.keywords.items():
                for value in value:
                    if value not in content:
                        continue
                    if trigger == 'trim':
                        if not ticker_id and manager.current_positions:
                            ticker_id = manager.current_positions[-1]
                            self.logger.info(f'Ticker ID not found. Fetching from last placed position: {ticker_id}')
                        return await self.sell(ticker_id, True)
                    elif trigger == 'exit':
                        if not ticker_id and manager.current_positions:
                            ticker_id = manager.current_positions[-1]
                            self.logger.info(f'Ticker ID not found. Fetching from last placed position: {ticker_id}')
                        return await self.sell(ticker_id)
                    elif trigger == 'entry':
                        if ticker_id and ticker:
                            quote = self.wb.get_option_quote(
                                stock=ticker,
                                optionId=ticker_id
                            )

                        elif ticker and strike_price and direction:
                            quote = self.wb.get_options_by_strike_and_expire_date(
                                ticker,
                                exp_date,
                                strike_price, 
                                direction
                            )

                        else:
                            missing_values = []
                            if not ticker:
                                missing_values.append("ticker")
                            if not strike_price:
                                missing_values.append("strike_price")
                            if not direction:
                                missing_values.append("direction")
                            
                            raise error.MissingValueError(f"Missing values: {', '.join(missing_values)}")

                        if not quote:
                            raise error.MissingValueError(f"Quote not found: {ticker}, {strike_price}, {direction}")
                        quote = quote[0][direction] if isinstance(quote, list) else quote['data'][0] 
                        self.logger.debug(f"Quote found: {quote}")
                        ticker_id = quote['tickerId']
                        
                        if not lmt_price:
                            lmt_price = round((float(quote["askList"][0]['price']) + float(quote["bidList"][0]['price'])) / 2, 2)

                        contract = f'{ticker} {"/".join((quote["expireDate"].split("-"))[1:])} {strike_price}{direction[0]}'
                        return await self.entry(ticker_id, lmt_price, contract)
            
            return self.logger.warning(f'None of the criteria were met.')
                
        except Exception as e:
            line_number = (traceback.extract_tb(e.__traceback__))[-1][1]
            self.logger.error(f'{type(e).__name__} occured on line {line_number}: {e}')

    async def entry(self, ticker_id, lmt_price, contract='Unknown'):
        try:
            quantity = math.floor(self.max_per_trade / (lmt_price * 100))

            if quantity <= 0:
                raise error.LimitExceededError(f'Cannot use auto quantity. One contract ({round(lmt_price * 100, 2)}) exceeds your limit ({self.max_per_trade})')
            
            contract = f'{quantity}x {contract}'
            
            await manager.lmt_order(
                ticker_id, 
                lmt_price, 
                'BUY', 
                quantity,
                contract
            )
            
        except Exception as e:
            line_number = (traceback.extract_tb(e.__traceback__))[-1][1]
            self.logger.error(f'{type(e).__name__} occured on line {line_number}: {e}')

    async def sell(self, ticker_id: int, partial=False):
        positions = self.wb.get_positions()
        if len(positions) == 0:
            self.logger.warning(f"No positions found")
            return
        
        for each in positions:
            try:
                symbol = re.match(r'^[A-Z]+', each['ticker']['symbol']).group(0) if re.match(r'^[A-Z]+', each['ticker']['symbol']) else None
                strike = str(round(each['optionExercisePrice']))
                tickerID = each['ticker']['tickerId']
                amt = 0

                if int(ticker_id) != int(tickerID):
                    continue

                optionType = each['optionType'][:1]
                positionAmt = int(each['position'])
                expiration = "/".join((each['optionExpireDate'].split("-"))[1:])
                contract = f'{symbol} {expiration} {strike}{optionType}'

                if partial is True:
                    amt = round(positionAmt/2) if round(positionAmt/2) > 0 else 1

                if amt >= positionAmt:
                    positionAmt = amt

                await manager.mkt_order(
                    ticker_id=ticker_id,
                    action='SELL',
                    quant=positionAmt,
                    contract=contract
                )

            except KeyError as e:
                line_number = (traceback.extract_tb(e.__traceback__))[-1][1]
                self.logger.warning(f'KeyError: {e} not found')
            except Exception as e:
                line_number = (traceback.extract_tb(e.__traceback__))[-1][1]
                self.logger.error(f'{type(e).__name__} occurred on line {line_number}: {e}')
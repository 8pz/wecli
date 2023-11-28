
import requests, uuid

from datetime import datetime
from pytz import timezone

from main import logger, config

from ..utils.account import account
from ..utils.endpoints import urls
from .utils import utils as u

endpoint = urls()
utils = u()

class paper_webull(u):
    def __init__(self, **kwargs) -> None:
        self.wb = account(paper=True, **kwargs)
        super().login(self.wb)

    async def place_order_option(self, optionId, quant, lmtPrice=None, stpPrice=None, action=None, orderType='LMT', enforce='DAY', contract='Unknown', tp_order=False):
        '''
        create buy / sell order
        stock: string
        lmtPrice: float
        action: string BUY / SELL
        optionId: string
        orderType: MKT / LMT
        enforce: GTC / DAY
        quant: int
        '''

        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)
        data = {
            'orderType': orderType,
            'serialId': str(uuid.uuid4()),
            'paperId': 1,
            'outsideRegularTradingHour': True,
            'accountId': self.wb._account_id,
            'tickerId': int(optionId),
            'quantity': int(quant),
            'action': "BUY",
            'timeInForce': enforce,
            'orders': [{'quantity': int(quant), 'action': action, 'tickerId': int(optionId), 'tickerType': 'OPTION'}],
        }
        
        if orderType == 'LMT' and isinstance(lmtPrice, float):
            data['lmtPrice'] = float(lmtPrice)
            
        response = requests.post(endpoint.paper_place_option_orders(), json=data, headers=headers, timeout=self.wb.timeout)
        if response.status_code != 200:
            raise Exception('place_option_order failed', response.status_code, response.reason)
        
        logger.info(f'{orderType} {action} order sent: {contract} @ ~{lmtPrice}')
        response = response.json()

        if config.auto_cancel_order is True and tp_order is False:
            from modules.manager import Manager
            await Manager().check_order(response['orderId'], action, contract, optionId)
            return response
        
        return response

    def place_order(self, stock=None, tId=None, price=0, action='BUY', orderType='LMT', enforce='GTC', quant=0, outsideRegularTradingHour=True):
        ''' Place a paper account order. '''
        if not tId is None:
            pass
        elif not stock is None:
            tId = utils.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')

        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)

        data = {
            'action': action, #  BUY or SELL
            'lmtPrice': float(price),
            'orderType': orderType, # 'LMT','MKT'
            'outsideRegularTradingHour': outsideRegularTradingHour,
            'quantity': int(quant),
            'serialId': str(uuid.uuid4()),
            'tickerId': tId,
            'timeInForce': enforce  # GTC or DAY
        }

        #Market orders do not support extended hours trading.
        if orderType == 'MKT':
            data['outsideRegularTradingHour'] = False

        response = requests.post(endpoint.paper_place_order(self.wb._account_id, tId), json=data, headers=headers, timeout=self.wb.timeout)
        return response.json()

    def modify_order(self, order, price=0, action='BUY', orderType='LMT', enforce='GTC', quant=0, outsideRegularTradingHour=True):
        ''' Modify a paper account order. '''
        headers = self.wb.build_req_headers()

        data = {
            'action': action, #  BUY or SELL
            'lmtPrice': float(price),
            'orderType':orderType,
            'comboType': 'NORMAL', # 'LMT','MKT'
            'outsideRegularTradingHour': outsideRegularTradingHour,
            'serialId': str(uuid.uuid4()),
            'tickerId': order['ticker']['tickerId'],
            'timeInForce': enforce # GTC or DAY
        }

        if quant == 0 or quant == order['totalQuantity']:
            data['quantity'] = order['totalQuantity']
        else:
            data['quantity'] = int(quant)

        response = requests.post(endpoint.paper_modify_order(self.wb._account_id, order['orderId']), json=data, headers=headers, timeout=self.wb.timeout)
        if response:
            return True
        else:
            print("Modify failed. {} {}".format(response, response.json()))
            return False
        
    def cancel_order(self, order_id):
        ''' Cancel a paper account order. '''
        headers = self.wb.build_req_headers()
        response = requests.post(endpoint.paper_cancel_order(self.wb._account_id, order_id), headers=headers, timeout=self.wb.timeout)
        return bool(response)

    def get_current_orders(self):
        ''' Open paper trading orders '''
        return self.get_account()['openOrders']

    def get_history_orders(self, status='All', count=20, action=''):
        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)
        response = requests.get(endpoint.paper_orders(self.wb._account_id, count, status, action), headers=headers, timeout=self.wb.timeout)
        return response.json()

    def get_positions(self):
        ''' Current positions in paper trading account. '''

        return self.get_account()['positions']
    
    def get_account(self):
        ''' Get important details of paper account '''
        headers = self.wb.build_req_headers()
        response = requests.get(endpoint.paper_account(self.wb._account_id), headers=headers, timeout=self.wb.timeout)
        return response.json()

    def get_account_id(self):
        ''' Get paper account id: call this before paper account actions'''
        headers = self.wb.build_req_headers()
        response = requests.get(endpoint.paper_account_id(), headers=headers, timeout=self.wb.timeout)
        result = response.json()
        if result is not None and len(result) > 0 and 'id' in result[0]:
            id = result[0]['id']
            self.wb._account_id = id
            return id
        else:
            return None

    def get_social_posts(self, topic, num=100):
        headers = self.wb.build_req_headers()

        response = requests.get(endpoint.social_posts(topic, num), headers=headers, timeout=self.wb.timeout)
        result = response.json()
        return result

    def get_social_home(self, topic, num=100):
        headers = self.wb.build_req_headers()

        response = requests.get(endpoint.social_home(topic, num), headers=headers, timeout=self.wb.timeout)
        result = response.json()
        return result


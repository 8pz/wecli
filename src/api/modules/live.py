import uuid, requests
from datetime import datetime
from pytz import timezone

from ..utils.account import account
from ..utils.endpoints import urls
from .utils import utils as u

endpoint = urls()
utils = u()

class webull(u):
    def __init__(self, **kwargs) -> None:
        self.wb = account(**kwargs)
        super().login(self.wb)
        
    def place_order(self, stock=None, tId=None, price=0, action='BUY', orderType='LMT', enforce='GTC', quant=0, outsideRegularTradingHour=True, stpPrice=None, trial_value=0, trial_type='DOLLAR'):
        '''
        Place an order

        price: float (LMT / STP LMT Only)
        action: BUY / SELL / SHORT
        ordertype : LMT / MKT / STP / STP LMT / STP TRAIL
        timeinforce:  GTC / DAY / IOC
        outsideRegularTradingHour: True / False
        stpPrice: float (STP / STP LMT Only)
        trial_value: float (STP TRIAL Only)
        trial_type: DOLLAR / PERCENTAGE (STP TRIAL Only)
        '''
        if not tId is None:
            pass
        elif not stock is None:
            tId = utils.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')

        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)
        data = {
            'action': action,
            'comboType': 'NORMAL',
            'orderType': orderType,
            'outsideRegularTradingHour': outsideRegularTradingHour,
            'quantity': int(quant),
            'serialId': str(uuid.uuid4()),
            'tickerId': tId,
            'timeInForce': enforce
        }

        # Market orders do not support extended hours trading.
        if orderType == 'MKT' :
            data['outsideRegularTradingHour'] = False
        elif orderType == 'LMT':
            data['lmtPrice'] = float(price)
        elif orderType == 'STP' :
            data['auxPrice'] = float(stpPrice)
        elif orderType == 'STP LMT' :
            data['lmtPrice'] = float(price)
            data['auxPrice'] = float(stpPrice)
        elif orderType == 'STP TRAIL' :
            data['trailingStopStep'] = float(trial_value)
            data['trailingType'] = str(trial_type)

        response = requests.post(endpoint.place_orders(self.wb._account_id), json=data, headers=headers, timeout=self.wb.timeout)
        return response.json()

    def modify_order(self, order=None, order_id=0, stock=None, tId=None, price=0, action=None, orderType=None, enforce=None, quant=0, outsideRegularTradingHour=None):
        '''
        Modify an order
        order_id: order_id
        action: BUY / SELL
        ordertype : LMT / MKT / STP / STP LMT / STP TRAIL
        timeinforce:  GTC / DAY / IOC
        outsideRegularTradingHour: True / False
        '''
        if not order and not order_id:
            raise ValueError('Must provide an order or order_id')

        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)

        modifiedAction = action or order['action']
        modifiedLmtPrice = float(price or order['lmtPrice'])
        modifiedOrderType = orderType or order['orderType']
        modifiedOutsideRegularTradingHour = outsideRegularTradingHour if type(outsideRegularTradingHour) == bool else order['outsideRegularTradingHour']
        modifiedEnforce = enforce or order['timeInForce']
        modifiedQuant = int(quant or order['quantity'])
        if not tId is None:
            pass
        elif not stock is None:
            tId = utils.get_ticker(stock)
        else :
            tId = order['ticker']['tickerId']
        order_id = order_id or order['orderId']

        data = {
            'action': modifiedAction,
            'lmtPrice': modifiedLmtPrice,
            'orderType': modifiedOrderType,
            'quantity': modifiedQuant,
            'comboType': 'NORMAL',
            'outsideRegularTradingHour': modifiedOutsideRegularTradingHour,
            'serialId': str(uuid.uuid4()),
            'orderId': order_id,
            'tickerId': tId,
            'timeInForce': modifiedEnforce
        }
        #Market orders do not support extended hours trading.
        if data['orderType'] == 'MKT':
            data['outsideRegularTradingHour'] = False

        response = requests.post(endpoint.modify_order(self.wb._account_id, order_id), json=data, headers=headers, timeout=self.wb.timeout)

        return response.json()

    def cancel_order(self, order_id=''):
        '''
        Cancel an order
        '''
        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)
        data = {}
        response = requests.post(endpoint.cancel_order(self.wb._account_id) + str(order_id) + '/' + str(uuid.uuid4()), json=data, headers=headers, timeout=self.wb.timeout)
        result = response.json()
        return result['success']

    def place_order_otoco(self, stock='', price='', stop_loss_price='', limit_profit_price='', time_in_force='DAY', quant=0) :
        '''
        OTOCO: One-triggers-a-one-cancels-the-others, aka Bracket Ordering
        Submit a buy order, its fill will trigger sell order placement. If one sell fills, it will cancel the other
         sell
        '''
        headers = self.wb.build_req_headers(include_trade_token=False, include_time=True)
        data1 = {
            'newOrders': [
                {'orderType': 'LMT', 'timeInForce': time_in_force, 'quantity': int(quant),
                 'outsideRegularTradingHour': False, 'action': 'BUY', 'tickerId': utils.get_ticker(stock),
                 'lmtPrice': float(price), 'comboType': 'MASTER'},
                {'orderType': 'STP', 'timeInForce': time_in_force, 'quantity': int(quant),
                 'outsideRegularTradingHour': False, 'action': 'SELL', 'tickerId': utils.get_ticker(stock),
                 'auxPrice': float(stop_loss_price), 'comboType': 'STOP_LOSS'},
                {'orderType': 'LMT', 'timeInForce': time_in_force, 'quantity': int(quant),
                 'outsideRegularTradingHour': False, 'action': 'SELL', 'tickerId': utils.get_ticker(stock),
                 'lmtPrice': float(limit_profit_price), 'comboType': 'STOP_PROFIT'}
            ]
        }

        response1 = requests.post(endpoint.check_otoco_orders(self.wb._account_id), json=data1, headers=headers, timeout=self.wb.timeout)
        result1 = response1.json()

        if result1['forward'] :
            data2 = {'newOrders': [
                {'orderType': 'LMT', 'timeInForce': time_in_force, 'quantity': int(quant),
                 'outsideRegularTradingHour': False, 'action': 'BUY', 'tickerId': utils.get_ticker(stock),
                 'lmtPrice': float(price), 'comboType': 'MASTER', 'serialId': str(uuid.uuid4())},
                {'orderType': 'STP', 'timeInForce': time_in_force, 'quantity': int(quant),
                 'outsideRegularTradingHour': False, 'action': 'SELL', 'tickerId': utils.get_ticker(stock),
                 'auxPrice': float(stop_loss_price), 'comboType': 'STOP_LOSS', 'serialId': str(uuid.uuid4())},
                {'orderType': 'LMT', 'timeInForce': time_in_force, 'quantity': int(quant),
                 'outsideRegularTradingHour': False, 'action': 'SELL', 'tickerId': utils.get_ticker(stock),
                 'lmtPrice': float(limit_profit_price), 'comboType': 'STOP_PROFIT', 'serialId': str(uuid.uuid4())}],
                'serialId': str(uuid.uuid4())
            }

            response2 = requests.post(endpoint.place_otoco_orders(self.wb._account_id), json=data2, headers=headers, timeout=self.wb.timeout)

            # print('Resp 2: {}'.format(response2))
            return response2.json()
        else:
            print(result1['checkResultList'][0]['code'])
            print(result1['checkResultList'][0]['msg'])
            return False

    def modify_order_otoco(self, order_id1='', order_id2='', order_id3='', stock='', price='', stop_loss_price='', limit_profit_price='', time_in_force='DAY', quant=0) :
        '''
        OTOCO: One-triggers-a-one-cancels-the-others, aka Bracket Ordering
        Submit a buy order, its fill will trigger sell order placement. If one sell fills, it will cancel the other
         sell
        '''
        headers = self.wb.build_req_headers(include_trade_token=False, include_time=True)

        data = {'modifyOrders': [
            {'orderType': 'LMT', 'timeInForce': time_in_force, 'quantity': int(quant), 'orderId': str(order_id1),
             'outsideRegularTradingHour': False, 'action': 'BUY', 'tickerId': utils.get_ticker(stock),
             'lmtPrice': float(price), 'comboType': 'MASTER', 'serialId': str(uuid.uuid4())},
            {'orderType': 'STP', 'timeInForce': time_in_force, 'quantity': int(quant), 'orderId': str(order_id2),
             'outsideRegularTradingHour': False, 'action': 'SELL', 'tickerId': utils.get_ticker(stock),
             'auxPrice': float(stop_loss_price), 'comboType': 'STOP_LOSS', 'serialId': str(uuid.uuid4())},
            {'orderType': 'LMT', 'timeInForce': time_in_force, 'quantity': int(quant), 'orderId': str(order_id3),
             'outsideRegularTradingHour': False, 'action': 'SELL', 'tickerId': utils.get_ticker(stock),
             'lmtPrice': float(limit_profit_price), 'comboType': 'STOP_PROFIT', 'serialId': str(uuid.uuid4())}],
            'serialId': str(uuid.uuid4())
        }

        response = requests.post(endpoint.modify_otoco_orders(self.wb._account_id), json=data, headers=headers, timeout=self.wb.timeout)

        return response.json()

    def cancel_order_otoco(self, combo_id=''):
        '''
        Retract an otoco order. Cancelling the MASTER order_id cancels the sub orders.
        '''
        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)
        # data = { 'serialId': str(uuid.uuid4()), 'cancelOrders': [str(order_id)]}
        data = {}
        response = requests.post(endpoint.cancel_otoco_orders(self.wb._account_id, combo_id), json=data, headers=headers, timeout=self.wb.timeout)
        return response.json()

    def place_order_crypto(self, stock=None, tId=None, price=0, action='BUY', orderType='LMT', enforce='DAY', entrust_type='QTY', quant=0, outsideRegularTradingHour=False) :
        '''
        Place Crypto order
        price: Limit order entry price
        quant: dollar amount to buy/sell when entrust_type is CASH else the decimal or fractional amount of shares to buy
        action: BUY / SELL
        entrust_type: CASH / QTY
        ordertype : LMT / MKT
        timeinforce:  DAY
        outsideRegularTradingHour: True / False
        '''
        if not tId is None:
            pass
        elif not stock is None:
            tId = utils.get_ticker(stock)
        else:
            raise ValueError('Must provide a stock symbol or a stock id')

        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)
        data = {
            'action': action,
            'assetType': 'crypto',
            'comboType': 'NORMAL',
            'entrustType': entrust_type,
            'lmtPrice': str(price),
            'orderType': orderType,
            'outsideRegularTradingHour': outsideRegularTradingHour,
            'quantity': str(quant),
            'serialId': str(uuid.uuid4()),
            'tickerId': tId,
            'timeInForce': enforce
        }

        response = requests.post(endpoint.place_orders(self.wb._account_id), json=data, headers=headers, timeout=self.wb.timeout)
        return response.json()

    async def place_order_option(self, optionId=None, lmtPrice='MKT', stpPrice=None, action=None, orderType='LMT', enforce='DAY', quant=0, contract='Unknown', tp_order=False):
        '''
        create buy / sell order
        stock: string
        lmtPrice: float
        stpPrice: float
        action: string BUY / SELL
        optionId: string
        orderType: MKT / LMT / STP / STP LMT
        enforce: GTC / DAY
        quant: int
        '''
        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)
        data = {
            'orderType': orderType,
            'serialId': str(uuid.uuid4()),
            'timeInForce': enforce,
            'orders': [{'quantity': int(quant), 'action': action, 'tickerId': int(optionId), 'tickerType': 'OPTION'}],
        }

        if orderType == 'LMT' and isinstance(lmtPrice, int):
            data['lmtPrice'] = float(lmtPrice)

        response = requests.post(endpoint.place_option_orders(self.wb._account_id), json=data, headers=headers, timeout=self.wb.timeout)
        if response.status_code != 200 :
            raise Exception('place_option_order failed', response.status_code, response.reason)
        
        self.wb.logger.info(f'{orderType} {action} order sent: {contract}')
        
        if stpPrice:
            data_stp = {
                'orderType': orderType,
                'serialId': str(uuid.uuid4()),
                'timeInForce': enforce,
                'orders': [{'quantity': int(quant), 'action': 'SELL', 'tickerId': int(optionId), 'tickerType': 'OPTION'}],
            }
            data_stp['auxPrice'] = float(stpPrice)
            response_stop = requests.post(endpoint.place_option_orders(self.wb._account_id), json=data, headers=headers, timeout=self.wb.timeout)
            if response_stop.status_code != 200:
                raise Exception('place_option_order (stop loss order) failed', response_stop.status_code, response_stop.reason)
            self.wb.logger.info(f'STOP order sent @ {stpPrice}')

        return response.json(), response_stop.json()

    def modify_order_option(self, order=None, lmtPrice=None, stpPrice=None, enforce=None, quant=0):
        '''
        order: dict from get_current_orders
        stpPrice: float
        lmtPrice: float
        enforce: GTC / DAY
        quant: int
        '''
        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)
        data = {
            'comboId': order['comboId'],
            'orderType': order['orderType'],
            'timeInForce': enforce or order['timeInForce'],
            'serialId': str(uuid.uuid4()),
            'orders': [{'quantity': quant or order['totalQuantity'],
                        'action': order['action'],
                        'tickerId': order['ticker']['tickerId'],
                        'tickerType': 'OPTION',
                        'orderId': order['orderId']}]
        }

        if order['orderType'] == 'LMT' and (lmtPrice or order.get('lmtPrice')):
            data['lmtPrice'] = lmtPrice or order['lmtPrice']
        elif order['orderType'] == 'STP' and (stpPrice or order.get('auxPrice')):
            data['auxPrice'] = stpPrice or order['auxPrice']
        elif order['orderType'] == 'STP LMT' and (stpPrice or order.get('auxPrice')) and (lmtPrice or order.get('lmtPrice')):
            data['auxPrice'] = stpPrice or order['auxPrice']
            data['lmtPrice'] = lmtPrice or order['lmtPrice']

        response = requests.post(endpoint.replace_option_orders(self.wb._account_id), json=data, headers=headers, timeout=self.wb.timeout)
        if response.status_code != 200:
            raise Exception('replace_option_order failed', response.status_code, response.reason)
        return True

    def get_account(self):
        '''
        get important details of account, positions, portfolio stance...etc
        '''
        headers = self.wb.build_req_headers()
        response = requests.get(endpoint.account(self.wb._account_id), headers=headers, timeout=self.wb.timeout)
        result = response.json()

        return result

    def get_positions(self):
        '''
        output standing positions of stocks
        '''

        return self.get_account()['positions']

    def get_portfolio(self):
        '''
        output numbers of portfolio
        '''
        data = self.get_account()
        output = {}
        for item in data['accountMembers']:
            output[item['key']] = item['value']
        return output

    def get_activities(self, index=1, size=500) :
        '''
        Activities including transfers, trades and dividends
        '''
        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)
        data = {'pageIndex': index,
                'pageSize': size}
        response = requests.post(endpoint.account_activities(self.wb._account_id), json=data, headers=headers, timeout=self.wb.timeout)
        return response.json()

    def get_current_orders(self) :
        '''
        Get open/standing orders
        '''
        data = self.get_account()['openOrders']
        self.wb.logger.debug(f'Standing orders: {data}')
        return data
    
    def get_history_orders(self, status='All', count=20, action=''):
        '''
        Historical orders, can be cancelled or filled
        status = Cancelled / Filled / Working / Partially Filled / Pending / Failed / All
        '''
        headers = self.wb.build_req_headers(include_trade_token=True, include_time=True)
        response = requests.get(endpoint.orders(self.wb._account_id, count, status, action), headers=headers, timeout=self.wb.timeout)
        return response.json()

    def cancel_all_orders(self):
        '''
        Cancels all open (aka 'working') orders
        '''
        open_orders = self.get_current_orders()
        for order in open_orders:
            self.cancel_order(order['orderId'])
            self.wb.logger.info(f'Order cancelled: {order["orderId"]}')

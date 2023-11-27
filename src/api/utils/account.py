import getpass, hashlib, os, pickle, requests, time, uuid, urllib.parse
from datetime import datetime
from email_validator import validate_email, EmailNotValidError

from . import endpoints

class account:
    def __init__(self, paper=False, **kwargs):
        username = kwargs.get('username', '')
        password = kwargs.get('password', '')
        pin = kwargs.get('pin', '')
        device_name = kwargs.get('device_name', '')
        mfa = kwargs.get('mfa', '')
        question_id = kwargs.get('question_id', '')
        question_answer = kwargs.get('question_answer', '')
        did = kwargs.get('did', '')
        save_token = kwargs.get('save_token', False)
        token_path = kwargs.get('token_path', None)
        region_code = kwargs.get('region_code', None)
        self.paper = paper

        if did: self._set_did(did)
        if pin: self.get_trade_token(pin)
        
        # session
        self._session = requests.session()
        self._headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:99.0) Gecko/20100101 Firefox/99.0',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'en-US,en;q=0.5',
            'Content-Type': 'application/json',
            'platform': 'web',
            'hl': 'en',
            'os': 'web',
            'osv': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:99.0) Gecko/20100101 Firefox/99.0',
            'app': 'global',
            'appid': 'webull-webapp',
            'ver': '3.39.18',
            'lzone': 'dc_core_r001',
            'ph': 'MacOS Firefox',
            'locale': 'eng',
            'device-type': 'Web',
            'did': self._get_did()
        }

        # endpoints
        self._urls = endpoints.urls()

        # account info
        self._account_id = ''
        self._trade_token = ''
        self._access_token = ''
        self._refresh_token = ''
        self._token_expire = ''
        self._uuid = ''

        # misc
        self._did = self._get_did()
        self._region_code = region_code or 6
        self.zone_var = 'dc_core_r001'
        self.timeout = 15

        # with webull md5 hash salted
        password = ('wl_app-a&b@!423^' + password).encode('utf-8')
        md5_hash = hashlib.md5(password)

        account_type = self.get_account_type(username)

        if device_name == '' :
            device_name = 'default_string'

        data = {
            'account': username,
            'accountType': str(account_type),
            'deviceId': self._did,
            'deviceName': device_name,
            'grade': 1,
            'pwd': md5_hash.hexdigest(),
            'regionId': self._region_code
        }

        if mfa != '' :
            data['extInfo'] = {
                'codeAccountType': account_type,
                'verificationCode': mfa
            }
            headers = self.build_req_headers()
        else :
            headers = self._headers

        if question_id != '' and question_answer != '' :
            data['accessQuestions'] = '[{"questionId":"' + str(question_id) + '", "answer":"' + str(question_answer) + '"}]'

        response = requests.post(self._urls.login(), json=data, headers=headers, timeout=self.timeout)
        result = response.json()
        if 'accessToken' in result and result['accessToken']:
            self._access_token = result['accessToken']
            self._refresh_token = result['refreshToken']
            self._token_expire = result['tokenExpireTime']
            self._uuid = result['uuid']
            self._account_id = self.get_account_id()
            if save_token:
                self._save_token(result, token_path)

    def _get_did(self, path=''):
        '''
        Makes a unique device id from a random uuid (uuid.uuid4).
        if the pickle file doesn't exist, this func will generate a random 32 character hex string
        uuid and save it in a pickle file for future use. if the file already exists it will
        load the pickle file to reuse the did. Having a unique did appears to be very important
        for the MQTT web socket protocol

        path: path to did.bin. For example _get_did('cache') will search for cache/did.bin instead.

        :return: hex string of a 32 digit uuid
        '''
        filename = 'did.bin'
        if path:
            filename = os.path.join(path, filename)
        if os.path.exists(filename):
            with open(filename,'rb') as file:
                did = pickle.load(file)
        else:
            did = uuid.uuid4().hex
            with open(filename, 'wb') as file:
                pickle.dump(did, file)
        return did

    def _set_did(self, did, path=''):
        '''
        If your starting to use this package after webull's new image verification for login, you'll
        need to login from a browser to get your did file in order to login through this api. You can
        find your did file by using this link:

        https://github.com/tedchou12/webull/wiki/Workaround-for-Login

        and then headers tab instead of response head, and finally look for the did value from the
        request headers.

        Then, you can run this program to save your did into did.bin so that it can be accessed in the
        future without the did explicitly being in your code.

        path: path to did.bin. For example _get_did('cache') will search for cache/did.bin instead.
        '''
        filename = 'did.bin'
        if path:
            filename = os.path.join(path, filename)
        with open(filename, 'wb') as file:
            pickle.dump(did, file)
        return True

    def build_req_headers(self, include_trade_token=False, include_time=False, include_zone_var=True):
        '''
        Build default set of header params
        '''
        headers = self._headers
        req_id = str(uuid.uuid4().hex)
        headers['reqid'] = req_id
        headers['did'] = self._did
        headers['access_token'] = self._access_token
        if include_trade_token :
            headers['t_token'] = self._trade_token
        if include_time :
            headers['t_time'] = str(round(time.time() * 1000))
        if include_zone_var :
            headers['lzone'] = self.zone_var
        return headers

    def get_mfa(self, username='') :
        account_type = self.get_account_type(username)

        data = {'account': str(username),
                'accountType': str(account_type),
                'codeType': int(5)}

        response = requests.post(self._urls.get_mfa(), json=data, headers=self._headers, timeout=self.timeout)
        # data = response.json()

        if response.status_code == 200 :
            return True
        else :
            return False

    def check_mfa(self, username='', mfa='') :
        account_type = self.get_account_type(username)

        data = {'account': str(username),
                'accountType': str(account_type),
                'code': str(mfa),
                'codeType': int(5)}

        response = requests.post(self._urls.check_mfa(), json=data, headers=self._headers, timeout=self.timeout)
        data = response.json()

        return data

    def get_security(self, username='') :
        account_type = self.get_account_type(username)
        username = urllib.parse.quote(username)

        # seems like webull has a bug/stability issue here:
        time = datetime.now().timestamp() * 1000
        response = requests.get(self._urls.get_security(username, account_type, self._region_code, 'PRODUCT_LOGIN', time, 0), headers=self._headers, timeout=self.timeout)
        data = response.json()
        if len(data) == 0 :
            response = requests.get(self._urls.get_security(username, account_type, self._region_code, 'PRODUCT_LOGIN', time, 1), headers=self._headers, timeout=self.timeout)
            data = response.json()

        return data

    def next_security(self, username='') :
        account_type = self.get_account_type(username)
        username = urllib.parse.quote(username)

        # seems like webull has a bug/stability issue here:
        time = datetime.now().timestamp() * 1000
        response = requests.get(self._urls.next_security(username, account_type, self._region_code, 'PRODUCT_LOGIN', time, 0), headers=self._headers, timeout=self.timeout)
        data = response.json()
        if len(data) == 0 :
            response = requests.get(self._urls.next_security(username, account_type, self._region_code, 'PRODUCT_LOGIN', time, 1), headers=self._headers, timeout=self.timeout)
            data = response.json()

        return data

    def check_security(self, username='', question_id='', question_answer='') :
        account_type = self.get_account_type(username)

        data = {'account': str(username),
                'accountType': str(account_type),
                'answerList': [{'questionId': str(question_id), 'answer': str(question_answer)}],
                'event': 'PRODUCT_LOGIN'}

        response = requests.post(self._urls.check_security(), json=data, headers=self._headers, timeout=self.timeout)
        data = response.json()

        return data

    def login_prompt(self):
        '''
        End login session
        '''
        uname = input('Enter Webull Username:')
        pwd = getpass.getpass('Enter Webull Password:')
        self.trade_pin = getpass.getpass('Enter 6 digit Webull Trade PIN:')
        self.login(uname, pwd)
        return self.get_trade_token(self.trade_pin)

    def logout(self):
        '''
        End login session
        '''
        headers = self.build_req_headers()
        response = requests.get(self._urls.logout(), headers=headers, timeout=self.timeout)
        return response.status_code

    def api_login(self, access_token='', refresh_token='', token_expire='', uuid='', mfa=''):
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expire = token_expire
        self._uuid = uuid
        self._account_id = self.get_account_id()

    def refresh_login(self, save_token=False, token_path=None):
        '''
        Refresh login token
        '''
        headers = self.build_req_headers()
        data = {'refreshToken': self._refresh_token}

        response = requests.post(self._urls.refresh_login(self._refresh_token), json=data, headers=headers, timeout=self.timeout)
        result = response.json()
        if 'accessToken' in result and result['accessToken'] != '' and result['refreshToken'] != '' and result['tokenExpireTime'] != '':
            self._access_token = result['accessToken']
            self._refresh_token = result['refreshToken']
            self._token_expire = result['tokenExpireTime']
            self._account_id = self.get_account_id()
            if save_token:
                result['uuid'] = self._uuid
                self._save_token(result, token_path)
        return result

    def _save_token(self, token=None, path=None):
        '''
        save login token to webull_credentials.json
        '''
        filename = 'webull_credentials.json'
        if path:
            filename = os.path.join(path, filename)
        with open(filename, 'wb') as f:
            pickle.dump(token, f)
            return True
        return False

    def get_detail(self):
        '''
        get some contact details of your account name, email/phone, region, avatar...etc
        '''
        headers = self.build_req_headers()

        response = requests.get(self._urls.user(), headers=headers, timeout=self.timeout)
        result = response.json()

        return result

    def get_account_id(self, id=0):
        '''
        get account id
        call account id before trade actions
        '''
        if self.paper is True:
            headers = self.build_req_headers()
            response = requests.get(self._urls.paper_account_id(), headers=headers, timeout=self.timeout)
            result = response.json()
            if result is not None and len(result) > 0 and 'id' in result[0]:
                id = result[0]['id']
                self._account_id = id
                return id
            else:
                return None
        else:
            headers = self.build_req_headers()
            response = requests.get(self._urls.account_id(), headers=headers, timeout=self.timeout)
            result = response.json()
            if result['success'] and len(result['data']) > 0 :
                self.zone_var = str(result['data'][int(id)]['rzone'])
                self._account_id = str(result['data'][int(id)]['secAccountId'])
                return self._account_id
            else:
                return None

    def get_trade_token(self, password=''):
        '''
        Trading related
        authorize trade, must be done before trade action
        '''
        headers = self.build_req_headers()

        # with webull md5 hash salted
        password = ('wl_app-a&b@!423^' + password).encode('utf-8')
        md5_hash = hashlib.md5(password)
        data = {'pwd': md5_hash.hexdigest()}

        response = requests.post(self._urls.trade_token(), json=data, headers=headers, timeout=self.timeout)
        result = response.json()
        if 'tradeToken' in result :
            self._trade_token = result['tradeToken']
            return True
        else:
            return False

    def get_account_type(self, username='') :
        try:
            validate_email(username)
            account_type = 2 # email
        except EmailNotValidError as _e:
            account_type = 1 # phone

        return account_type

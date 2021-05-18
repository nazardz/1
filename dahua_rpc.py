#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import hashlib
import requests

if sys.version_info > (3, 0):
    unicode = str


class DahuaRpc(object):
    def __init__(self, host, username, password):
        self.host = host
        self.username = username
        self.password = password
        self.s = requests.Session()
        self.session_id = None
        self.id = 0

    # Raw request #
    def request(self, method, params=None, object_id=None, extra=None, url=None):
        """Make a RPC request"""
        self.id += 1
        data = {'method': method, 'id': self.id}
        if params is not None:
            data['params'] = params
        if object_id:
            data['object'] = object_id
        if extra is not None:
            data.update(extra)
        if self.session_id:
            data['session'] = self.session_id
        if not url:
            url = "http://{}/RPC2".format(self.host)
        r = self.s.post(url, json=data)
        return r.json()

    # Login #
    def login(self):
        """Dahua RPC login"""
        # login1: get session, realm & random for real login
        url = 'http://{}/RPC2_Login'.format(self.host)
        method = "global.login"
        params = {'userName': self.username,
                  'password': "",
                  'clientType': "Dahua3.0-Web3.0"}
        r = self.request(method=method, params=params, url=url)
        if r is None:
            raise LoginError(str(r))
        self.session_id = r['session']
        realm = r['params']['realm']
        random = r['params']['random']
        # Password encryption algorithm
        # Reversed from rpcCore.getAuthByType
        pwd_phrase = self.username + ":" + realm + ":" + self.password
        if isinstance(pwd_phrase, unicode):
            pwd_phrase = pwd_phrase.encode('utf-8')
        pwd_hash = hashlib.md5(pwd_phrase).hexdigest().upper()
        pass_phrase = self.username + ':' + random + ':' + pwd_hash
        if isinstance(pass_phrase, unicode):
            pass_phrase = pass_phrase.encode('utf-8')
        pass_hash = hashlib.md5(pass_phrase).hexdigest().upper()
        # login2: the real login
        params = {'userName': self.username,
                  'password': pass_hash,
                  'clientType': 'Dahua3.0-Web3.0',
                  'authorityType': "Default",
                  'passwordType': "Default"}
        r = self.request(method=method, params=params, url=url)
        if r['result'] is False:
            # print('Component error: User or password not valid.')
            return False
        return True

    # Logout
    def logout(self):
        """Dahua RPC logout"""
        method = 'global.logout'
        r = self.request(method=method)
        if r['result'] is False:
            raise LoginError(str(r))
        else:
            return r

    # Current Time #
    def current_time(self):
        """Get current time on the device"""
        method = "global.getCurrentTime"
        r = self.request(method=method)
        if r['result'] is False:
            raise RequestError(str(r))
        else:
            return r

    # Reboot device #
    def reboot(self):
        """Reboot the device"""
        # Get object id
        method = "magicBox.factory.instance"
        r = self.request(method=method)
        object_id = r['result']
        # Reboot
        method = "magicBox.reboot"
        r = self.request(method=method, object_id=object_id)
        if r['result'] is False:
            raise RequestError(str(r))
        else:
            return r

    # Media File Find ---------------#
    # Find media files = create finder + conditions + find files #

    def get_media_file_info(self):
        """Create a media file finder"""
        method = "mediaFileFind.factory.create"
        r = self.request(method=method)
        if r['result'] is False:
            raise RequestError(str(r))
        else:
            return r

    def start_find_media_file(self, object_id, start, end, channel, types):
        """Start to find file wth the condition"""
        method = "mediaFileFind.findFile"
        params = {
            "condition": {"StartTime": start, "EndTime": end,
                          "Channel": channel,
                          "Types": ['==', types]
                          }}
        r = self.request(method=method, params=params, object_id=object_id)
        if r['result'] is False:
            return r
            # raise RequestError(str(r))
        else:
            return r

    def find_next_media_file(self, object_id, count):
        """Find next 'count' files"""
        method = "mediaFileFind.findNextFile"
        params = {
            "count": count}
        r = self.request(method=method, params=params, object_id=object_id)
        if r['result'] is False:
            raise RequestError(str(r))
        else:
            return r

    def stop_find_media_file(self, object_id):
        """Stop find media file"""
        method = "mediaFileFind.close"
        r = self.request(method=method, object_id=object_id)
        if r['result'] is False:
            raise RequestError(str(r))
        else:
            return r

    def destroy_find_media_file(self, object_id):
        """Destroy a media file finder"""
        method = "mediaFileFind.destroy"
        r = self.request(method=method, object_id=object_id)
        if r['result'] is False:
            raise RequestError(str(r))
        else:
            return r
# -----------------------------------------------------------------------------------------#


class LoginError(Exception):
    pass


class RequestError(Exception):
    pass

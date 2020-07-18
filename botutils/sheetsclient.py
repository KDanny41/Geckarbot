import logging
import urllib.parse

from conf import Config
from botutils import restclient


class NoApiKey(Exception):
    """Raisen if no Google API Key is defined"""
    pass


class Client(restclient.Client):
    """
    REST Client for Google Sheets API.
    Further infos: https://developers.google.com/sheets/api
    """

    def __init__(self, spreadsheet_id):
        """
        Creates a new REST Client for Google Sheets API using the API Key given in Geckarbot.json.
        If no API Key is given, the Client can't set up.

        :param spreadsheet_id: The ID of the spreadsheet
        """

        if not Config().GOOGLE_API_KEY:
            raise NoApiKey()

        super(Client, self).__init__("https://sheets.googleapis.com/v4/spreadsheets/")

        self.spreadsheet_id = spreadsheet_id

        self.logger = logging.getLogger(__name__)
        self.logger.debug("Building Sheets API Client for spreadsheet {}".format(self.spreadsheet_id))

    def _params_add_api_key(self, params=None):
        """
        Adds the API key to the params dictionary
        """
        if params is None:
            params = {}
        params['key'] = Config().GOOGLE_API_KEY
        return params

    def _make_request(self, route, params=None):
        """
        Makes a Sheets Request
        """
        route = urllib.parse.quote(route)
        params = self._params_add_api_key(params)
        # self.logger.debug("Making Sheets request {}, params: {}".format(route, params))
        response = self.make_request(route, params=params)
        # self.logger.debug("Response: {}".format(response))
        return response

    def get(self, range):
        route = "{}/values/{}".format(self.spreadsheet_id, range)
        values = self._make_request(route)['values']
        return values

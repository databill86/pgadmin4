# -*- coding: utf-8 -*-
##########################################################################
#
# pgAdmin 4 - PostgreSQL Tools
#
# Copyright (C) 2013 - 2019, The pgAdmin Development Team
# This software is released under the PostgreSQL Licence
#
##########################################################################

from pgadmin.utils.route import BaseTestGenerator
from pgadmin.browser.server_groups.servers.databases.tests import utils as \
    database_utils
from regression import parent_node_dict
from regression.python_test_utils import test_utils
import json
from pgadmin.utils import server_utils, IS_PY2
import random


class TestDownloadCSV(BaseTestGenerator):
    """
    This class validates download csv
    """
    scenarios = [
        (
            'Download csv URL with valid query',
            dict(
                sql='SELECT 1 as "A",2 as "B",3 as "C"',
                init_url='/datagrid/initialize/query_tool/{0}/{1}/{2}',
                donwload_url="/sqleditor/query_tool/download/{0}",
                output_columns='"A","B","C"',
                output_values='1,2,3',
                is_valid_tx=True,
                is_valid=True
            )
        ),
        (
            'Download csv URL with wrong TX id',
            dict(
                sql='SELECT 1 as "A",2 as "B",3 as "C"',
                init_url='/datagrid/initialize/query_tool/{0}/{1}/{2}',
                donwload_url="/sqleditor/query_tool/download/{0}",
                output_columns=None,
                output_values=None,
                is_valid_tx=False,
                is_valid=False
            )
        ),
        (
            'Download csv URL with wrong query',
            dict(
                sql='SELECT * FROM this_table_does_not_exist',
                init_url='/datagrid/initialize/query_tool/{0}/{1}/{2}',
                donwload_url="/sqleditor/query_tool/download/{0}",
                output_columns=None,
                output_values=None,
                is_valid_tx=True,
                is_valid=False
            )
        ),
    ]

    def setUp(self):
        self._db_name = 'download_csv_' + str(random.randint(10000, 65535))
        self._sid = self.server_information['server_id']

        server_con = server_utils.connect_server(self, self._sid)

        self._did = test_utils.create_database(
            self.server, self._db_name
        )

    def runTest(self):

        db_con = database_utils.connect_database(self,
                                                 test_utils.SERVER_GROUP,
                                                 self._sid,
                                                 self._did)
        if not db_con["info"] == "Database connected.":
            raise Exception("Could not connect to the database.")

        # Initialize query tool
        url = self.init_url.format(
            test_utils.SERVER_GROUP, self._sid, self._did)
        response = self.tester.post(url)
        self.assertEquals(response.status_code, 200)

        response_data = json.loads(response.data.decode('utf-8'))
        self.trans_id = response_data['data']['gridTransId']
        # If invalid tx test then make the Tx id invalid so that tests fails
        if not self.is_valid_tx:
            self.trans_id = self.trans_id + '007'

        # Check character
        url = self.donwload_url.format(self.trans_id)
        # Disable the console logging from Flask logger
        self.app.logger.disabled = True
        response = self.tester.post(
            url,
            data={"query": self.sql, "filename": 'test.csv'}
        )
        # Enable the console logging from Flask logger
        self.app.logger.disabled = False
        if self.is_valid:
            # when valid query
            self.assertEquals(response.status_code, 200)
            csv_data = response.data.decode()
            self.assertTrue(self.output_columns in csv_data)
            self.assertTrue(self.output_values in csv_data)
        elif not self.is_valid and self.is_valid_tx:
            # When user enters wrong query
            self.assertEquals(response.status_code, 200)
            response_data = json.loads(response.data.decode('utf-8'))
            self.assertFalse(response_data['data']['status'])
            self.assertTrue(
                'relation "this_table_does_not_exist" does not exist' in
                response_data['data']['result']
            )
        else:
            # when TX id is invalid
            self.assertEquals(response.status_code, 500)

        database_utils.disconnect_database(self, self._sid, self._did)

    def tearDown(self):
        main_conn = test_utils.get_db_connection(
            self.server['db'],
            self.server['username'],
            self.server['db_password'],
            self.server['host'],
            self.server['port'],
            self.server['sslmode']
        )
        test_utils.drop_database(main_conn, self._db_name)

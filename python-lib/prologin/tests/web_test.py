import prologin.web

import multiprocessing
import requests
import time
import unittest
import wsgiref.simple_server

def test_ping_handler():
    """/__ping handler code returns pong"""
    headers, text = prologin.web.ping_handler()
    assert text == "pong"

def test_threads_handler():
    """/__threads handler code returns threads info"""
    headers, text = prologin.web.threads_handler()
    assert ' threads found' in text

class WebAppTest:
    """Abstract test which black-box tests all known handlers to check if the
    mapping works and if the output is kind of what we expect.
    
    Inherit from unittest.TestCase and this class, then implement the following
    *class* methods:
        - make_web_server
            Returns a function which, when run, runs forever listening for
            requests (server.serve_forever usually).
        - get_server_url
            Returns the base URL of the server without trailing /. Usually,
            something like http://localhost:12345
        - expected_normal_output
            Returns a string that should be in the normal application output -
            to test if requests are forwarded properly.

    Also define setUpClass and tearDownClass like this:
        @classmethod
        def setUpClass(cls):
            WebAppTest.setup_web_server(cls)

        @classmethod
        def tearDownClass(self):
            WebAppTest.tear_down_web_server(cls)
    """

    def setup_web_server(cls):
        server = cls.make_web_server()
        cls.process = multiprocessing.Process(target=server)
        cls.process.start()

    def tear_down_web_server(cls):
        cls.process.terminate()

    def testPingHandler(self):
        text = requests.get(self.get_server_url() + '/__ping').text
        self.assertEqual(text, "pong")

    def testThreadsHandler(self):
        text = requests.get(self.get_server_url() + '/__threads').text
        self.assertIn(' threads found', text)

class WsgiAppTest(unittest.TestCase, WebAppTest):
    @classmethod
    def setUpClass(cls):
        WebAppTest.setup_web_server(cls)

    @classmethod
    def tearDownClass(cls):
        WebAppTest.tear_down_web_server(cls)

    @classmethod
    def make_web_server(cls):
        def application(environ, start_response):
            start_response('200 OK', [])
            return [b'Normal output']
        application = prologin.web.WsgiApp(application, 'test-app')
        server = wsgiref.simple_server.make_server('127.0.0.1', 42543,
                                                   application)
        return server.serve_forever

    @classmethod
    def get_server_url(cls):
        return 'http://localhost:42543'

    @classmethod
    def expected_normal_output(cls):
        return 'Normal output'

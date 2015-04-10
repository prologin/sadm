import asyncio
import unittest

from prologin.workernode.operations import communicate as coro_comm

def communicate(*args, **kwargs):
    return asyncio.get_event_loop().run_until_complete(coro_comm(*args, **kwargs))

class WorkerNodeCommunicate(unittest.TestCase):
    def test_simple_echo(self):
        arg = 'Votai Test.'
        code, out = communicate(['/bin/echo', '-n', arg])
        self.assertEqual(out, arg)
        self.assertEqual(code, 0)

    def test_stdin_cat(self):
        data = 'Test. La seule liste BDE doublement chaînée.'
        code, out = communicate(['/bin/cat'], data=data)
        self.assertEqual(out, data)
        self.assertEqual(code, 0)

    def test_errcode(self):
        self.assertEqual(communicate(['/bin/true'])[0], 0)
        self.assertEqual(communicate(['/bin/false'])[0], 1)

    def test_truncate_output(self):
        out = communicate(['echo', 'Test.' * 99], max_len=21)[1]
        self.assertTrue(len(out) == 21)

        out = communicate(['echo', 'Test.' * 99], max_len=0)[1]
        self.assertTrue(len(out) == 0)

        out = communicate(['echo', 'Test.' * 99], max_len=10,
                truncate_message='log truncated')[1]
        self.assertTrue(len(out) == 10 + len('log truncated'))

    def test_timeout(self):
        with self.assertRaises(asyncio.TimeoutError):
            out = communicate(['/bin/sleep', '10'], timeout=1)

import unittest

from devices.little_lucy.platforms.nebula.native import client
from devices.little_lucy.platforms.nebula.native.action_schema import batch_digest
from devices.little_lucy.platforms.nebula.native.authorization import AuthorizationStore
from devices.little_lucy.platforms.nebula.native.hid import MockTransport
from devices.little_lucy.platforms.nebula.native.ui import render


def make_request(text='hello'):
    batch = {'actions': [
        {'kind': 'key', 'keys': ['a'], 'modifiers': [], 'hold_ms': 0},
        {'kind': 'move', 'dx': 1, 'dy': 2},
        {'kind': 'text', 'text': text},
        {'kind': 'release_all'},
    ]}
    return {
        'request_id': 'req-1',
        'revision': 'rev-1',
        'digest': batch_digest(batch),
        'batch': batch,
    }


class FakeAuthorizer:
    """Minimal stand-in for the real store, including one-use consumption."""

    def __init__(self, allowed=True):
        self.allowed = allowed
        self.calls = []
        self.consumed = []

    def authorize(self, token, req):
        self.calls.append((token, req))
        return self.allowed

    def consume(self, token):
        self.consumed.append(token)

    def save(self):
        pass


class RecordingQueue:
    def __init__(self):
        self.items = []

    def put(self, item):
        self.items.append(item)


class NativeExecuteTests(unittest.TestCase):
    def setUp(self):
        self.original = (client.EXECUTOR, client.AUTHORIZER, client.TRANSPORT)

    def tearDown(self):
        client.EXECUTOR, client.AUTHORIZER, client.TRANSPORT = self.original

    # --- rendering -------------------------------------------------------
    def test_pages_render_and_hits_are_tuples(self):
        model = {'page': 'execute_review', 'online': False, 'execute_request': make_request()}
        for page in ('execute_review', 'execute_confirm', 'executing', 'execute_result'):
            model['page'] = page
            image, hits = render(model, 0)
            self.assertEqual(image.size, (480, 272))
            for box, action in hits:
                self.assertEqual(len(box), 4)
                self.assertIsInstance(action, str)

    # --- navigation ------------------------------------------------------
    def test_execute_page_navigation_actions(self):
        model = {'page': 'home', 'online': False, 'execute_request': make_request(),
                 'execute_status': 'idle'}
        client.apply_action(model, 'execute_review')
        self.assertEqual(model['page'], 'execute_review')
        client.apply_action(model, 'execute_confirm')
        self.assertEqual(model['page'], 'execute_confirm')
        command = client.apply_action(model, 'execute_stop')
        self.assertEqual(model['page'], 'execute_result')
        self.assertEqual(model['execute_status'], 'stopped')
        self.assertTrue(command['release_inputs'])

    def test_execute_returns_request_and_token_separately(self):
        model = {'page': 'execute_confirm', 'online': False,
                 'execute_request': make_request(), 'execute_token': 'tok-1',
                 'execute_status': 'idle'}
        command = client.apply_action(model, 'execute')
        self.assertEqual(command['execute']['request'], make_request())
        self.assertEqual(command['execute']['token'], 'tok-1')
        self.assertEqual(model['page'], 'executing')

    # --- refusal paths ---------------------------------------------------
    def test_run_execute_without_executor_refuses(self):
        client.EXECUTOR = None
        client.AUTHORIZER = FakeAuthorizer()
        result = client.run_execute(make_request(), token='tok-1')
        self.assertFalse(result['ok'])
        self.assertEqual(result['message'], 'No PC executor configured.')

    def test_run_execute_without_authorizer_refuses(self):
        called = []
        client.EXECUTOR = lambda req: called.append(req)
        client.AUTHORIZER = None
        result = client.run_execute(make_request(), token='tok-1')
        self.assertFalse(result['ok'])
        self.assertEqual(result['message'], 'No authorizer configured.')
        self.assertEqual(called, [])

    def test_run_execute_without_token_refuses(self):
        called = []
        client.EXECUTOR = lambda req: called.append(req) or {'ok': True}
        client.AUTHORIZER = FakeAuthorizer(allowed=True)
        result = client.run_execute(make_request())
        self.assertFalse(result['ok'])
        self.assertEqual(called, [])

    def test_run_execute_with_rejecting_authorizer_refuses(self):
        called = []
        client.EXECUTOR = lambda req: called.append(req)
        client.AUTHORIZER = FakeAuthorizer(allowed=False)
        result = client.run_execute(make_request(), token='tok-1')
        self.assertFalse(result['ok'])
        self.assertEqual(called, [])
        self.assertEqual(client.AUTHORIZER.calls[0][0], 'tok-1')

    # --- happy path against the REAL authorizer --------------------------
    def test_real_authorizer_happy_path_executes_exactly_once(self):
        # Regression: the request document cannot carry the token, because
        # parse_request rejects unknown keys. The token must be separate.
        store = AuthorizationStore(ttl_seconds=60)
        client.AUTHORIZER = store
        request = make_request()
        token = client.stage_execution({'page': 'home'}, request)
        called = []
        client.EXECUTOR = lambda req: called.append(req) or {'ok': True, 'message': 'done'}
        result = client.run_execute(request, token=token)
        self.assertTrue(result['ok'], result)
        self.assertEqual(called, [request])

    def test_real_authorizer_blocks_replay_after_execution(self):
        store = AuthorizationStore(ttl_seconds=60)
        client.AUTHORIZER = store
        request = make_request()
        token = client.stage_execution({'page': 'home'}, request)
        called = []
        client.EXECUTOR = lambda req: called.append(req) or {'ok': True}
        self.assertTrue(client.run_execute(request, token=token)['ok'])
        second = client.run_execute(request, token=token)
        self.assertFalse(second['ok'])
        self.assertEqual(len(called), 1)

    def test_real_authorizer_blocks_wrong_revision(self):
        store = AuthorizationStore(ttl_seconds=60)
        client.AUTHORIZER = store
        request = make_request()
        token = client.stage_execution({'page': 'home'}, request)
        called = []
        client.EXECUTOR = lambda req: called.append(req) or {'ok': True}
        other = dict(request, revision='rev-2')
        self.assertFalse(client.run_execute(other, token=token)['ok'])
        self.assertEqual(called, [])

    # --- failure handling ------------------------------------------------
    def test_run_execute_exception_releases_transport(self):
        transport = MockTransport()
        client.EXECUTOR = lambda req: (_ for _ in ()).throw(RuntimeError('boom'))
        client.AUTHORIZER = FakeAuthorizer(allowed=True)
        result = client.run_execute(make_request(), transport=transport, token='tok-1')
        self.assertFalse(result['ok'])
        self.assertGreaterEqual(len(transport.reports), 2)
        self.assertEqual(transport.reports[-2], b'\x00' * 8)
        self.assertEqual(transport.reports[-1], b'\x00' * 4)

    def test_release_inputs_uses_configured_transport(self):
        transport = MockTransport()
        client.TRANSPORT = transport
        client.release_inputs()
        self.assertEqual(transport.reports[-2], b'\x00' * 8)
        self.assertEqual(transport.reports[-1], b'\x00' * 4)

    def test_release_inputs_without_transport_is_safe(self):
        client.TRANSPORT = None
        client.release_inputs()  # must not raise

    # --- routing ---------------------------------------------------------
    def test_execute_command_is_handled_locally_not_sent_to_bridge(self):
        # Regression: an execute command previously went to the decision
        # queue, so it was POSTed to LucyOS as if it were an approval.
        store = AuthorizationStore(ttl_seconds=60)
        client.AUTHORIZER = store
        request = make_request()
        token = store.stage(request)
        client.EXECUTOR = lambda req: {'ok': True, 'message': 'sent'}
        model = {'page': 'executing', 'execute_request': request, 'execute_token': token}
        queue = RecordingQueue()
        client.dispatch_command({'execute': {'request': request, 'token': token}}, model, queue)
        self.assertEqual(queue.items, [])
        self.assertEqual(model['page'], 'execute_result')
        self.assertEqual(model['execute_status'], 'done')

    def test_decision_command_still_goes_to_bridge_queue(self):
        model = {'page': 'sending'}
        queue = RecordingQueue()
        decision = {'approval_id': 'A-1', 'revision': 3, 'decision': 'APPROVED'}
        client.dispatch_command(decision, model, queue)
        self.assertEqual(queue.items, [decision])


if __name__ == '__main__':
    unittest.main()

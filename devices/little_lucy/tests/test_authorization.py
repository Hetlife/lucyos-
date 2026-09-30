import tempfile
import unittest

from devices.little_lucy.platforms.nebula.native.action_schema import batch_digest
from devices.little_lucy.platforms.nebula.native.authorization import AuthorizationStore


class AuthorizationTests(unittest.TestCase):
    def _clock(self, now=None):
        return now if now is not None else 0.0

    def _request(self, revision='rev1', text='hello'):
        batch = {'actions': [{'kind': 'text', 'text': text}]}
        return {
            'request_id': 'req-1',
            'revision': revision,
            'batch': batch,
            'digest': batch_digest(batch),
        }

    def test_fresh_token_authorizes_and_revision_and_digest_checks(self):
        store = AuthorizationStore(ttl_seconds=60)
        request = self._request()
        token = store.stage(request)
        self.assertTrue(store.authorize(token, request, now=0.0))
        self.assertFalse(store.authorize(token, self._request(revision='rev2'), now=0.0))
        self.assertFalse(store.authorize(token, self._request(text='other'), now=0.0))

    def test_expired_and_replay_and_unknown_token(self):
        store = AuthorizationStore(ttl_seconds=1)
        store._now = self._clock
        request = self._request()
        token = store.stage(request)
        self.assertFalse(store.authorize(token, request, now=2.0))
        self.assertFalse(store.authorize('missing', request, now=0.0))
        store.consume(token)
        self.assertTrue(store.is_consumed(token))
        self.assertFalse(store.authorize(token, request, now=0.0))

    def test_persistence_keeps_consumed_state_and_purge_counts_dropped(self):
        request = self._request()
        with tempfile.NamedTemporaryFile() as tmp:
            store = AuthorizationStore(ttl_seconds=1, path=tmp.name)
            store._now = self._clock
            token = store.stage(request)
            store.consume(token)
            store.save()
            reloaded = AuthorizationStore(ttl_seconds=1, path=tmp.name)
            reloaded.load()
            self.assertTrue(reloaded.is_consumed(token))
            self.assertFalse(reloaded.authorize(token, request, now=0.0))

        store = AuthorizationStore(ttl_seconds=1)
        store._now = self._clock
        t1 = store.stage(self._request(revision='a'))
        t2 = store.stage(self._request(revision='b', text='world'))
        self.assertEqual(store.purge(now=100.0), 2)
        self.assertFalse(store.authorize(t1, self._request(revision='a'), now=100.0))
        self.assertFalse(store.authorize(t2, self._request(revision='b', text='world'), now=100.0))

    def test_restaging_same_batch_does_not_revive_consumed_approval(self):
        # Regression: stage() previously overwrote the entry and reset the
        # consumed flag, so re-staging an identical batch made a spent
        # approval authorize again.
        store = AuthorizationStore(ttl_seconds=60)
        request = self._request()
        first = store.stage(request)
        store.consume(first)
        second = store.stage(request)
        self.assertNotEqual(first, second)
        self.assertTrue(store.is_consumed(first))
        self.assertFalse(store.authorize(first, request, now=0.0))
        self.assertTrue(store.authorize(second, request, now=0.0))

    def test_token_is_bound_to_request_id_not_only_batch(self):
        # Regression: a token issued for one request must not authorize a
        # different request that happens to carry the same batch and revision.
        store = AuthorizationStore(ttl_seconds=60)
        batch = {'actions': [{'kind': 'release_all'}]}
        digest = batch_digest(batch)
        original = {'request_id': 'req-1', 'revision': 'rev1', 'batch': batch, 'digest': digest}
        impostor = {'request_id': 'req-2', 'revision': 'rev1', 'batch': batch, 'digest': digest}
        token = store.stage(original)
        self.assertFalse(store.authorize(token, impostor, now=0.0))
        self.assertTrue(store.authorize(token, original, now=0.0))

    def test_stage_rejects_non_positive_ttl(self):
        with self.assertRaises(ValueError):
            AuthorizationStore(ttl_seconds=0)


if __name__ == '__main__':
    unittest.main()

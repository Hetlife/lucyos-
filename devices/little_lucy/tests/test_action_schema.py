import unittest

from devices.little_lucy.platforms.nebula.native.action_schema import (
    MAX_ACTIONS,
    MAX_MOVE_DELTA,
    MAX_SCROLL,
    MAX_TEXT_CHARS,
    MAX_TOTAL_MS,
    batch_digest,
    canonical_json,
    parse_request,
    validate_action,
    validate_batch,
)


class ActionSchemaTests(unittest.TestCase):
    def test_valid_batch_normalizes_and_digest_is_stable(self):
        batch = {
            'actions': [
                {'kind': 'key', 'modifiers': ['ctrl'], 'keys': ['a'], 'hold_ms': 10},
                {'kind': 'text', 'text': 'hello'},
                {'kind': 'move', 'dx': 1, 'dy': -1},
                {'kind': 'button', 'button': 'left', 'action': 'click'},
                {'kind': 'scroll', 'amount': 5},
                {'kind': 'wait', 'ms': 20},
                {'kind': 'release_all'},
            ]
        }
        normalized = validate_batch(batch)
        self.assertEqual(normalized['actions'][0], {'kind': 'key', 'keys': ['a'], 'modifiers': ['ctrl'], 'hold_ms': 10})
        self.assertEqual(canonical_json({'b': 2, 'a': 1}), '{"a":1,"b":2}')
        self.assertEqual(batch_digest(batch), batch_digest({'actions': list(batch['actions'])}))

    def test_bounds_raise(self):
        cases = [
            {'actions': []},
            {'actions': [{'kind': 'text', 'text': 'x' * (MAX_TEXT_CHARS + 1)}]},
            {'actions': [{'kind': 'move', 'dx': MAX_MOVE_DELTA + 1, 'dy': 0}]},
            {'actions': [{'kind': 'scroll', 'amount': MAX_SCROLL + 1}]},
            {'actions': [{'kind': 'wait', 'ms': 5001}]},
            {'actions': [{'kind': 'key', 'keys': ['a'], 'modifiers': ['meta']}]},
            {'actions': [{'kind': 'button', 'button': 'side', 'action': 'click'}]},
            {'actions': [{'kind': 'key', 'keys': ['a'], 'hold_ms': MAX_TOTAL_MS + 1}]},
        ]
        for batch in cases:
            with self.subTest(batch=batch):
                with self.assertRaises(ValueError):
                    validate_batch(batch)

    def test_digest_changes_when_action_changes(self):
        a = {'actions': [{'kind': 'text', 'text': 'hi'}]}
        b = {'actions': [{'kind': 'text', 'text': 'ho'}]}
        self.assertNotEqual(batch_digest(a), batch_digest(b))

    def test_parse_request_rejects_bad_digest_and_oversize_ids(self):
        batch = {'actions': [{'kind': 'release_all'}]}
        digest = batch_digest(batch)
        request = {'request_id': 'r1', 'revision': 'rev1', 'batch': batch, 'digest': digest}
        parsed = parse_request(request)
        self.assertEqual(parsed['digest'], digest)
        with self.assertRaises(ValueError):
            parse_request(dict(request, digest='0' * 64))
        with self.assertRaises(ValueError):
            parse_request(dict(request, request_id='x' * 65))
        with self.assertRaises(ValueError):
            parse_request(dict(request, revision='y' * 129))
        with self.assertRaises(ValueError):
            validate_action({'kind': 'unknown'})

    def test_unencodable_key_names_are_rejected(self):
        # Regression: the schema previously accepted any short string as a key,
        # so an owner could approve a batch the HID encoder cannot emit.
        for bad in ('notakey', 'f13', 'ctrl'):
            with self.subTest(key=bad):
                with self.assertRaises(ValueError):
                    validate_batch({'actions': [{'kind': 'key', 'keys': [bad]}]})

    def test_key_names_normalize_to_lower_case(self):
        normalized = validate_batch({'actions': [{'kind': 'key', 'keys': ['A'], 'modifiers': ['CTRL']}]})
        self.assertEqual(normalized['actions'][0]['keys'], ['a'])
        self.assertEqual(normalized['actions'][0]['modifiers'], ['ctrl'])


if __name__ == '__main__':
    unittest.main()

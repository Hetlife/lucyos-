import json
import os
import time
import uuid

try:  # package import in the LucyOS repo
    from .action_schema import parse_request
except ImportError:  # flat deployment on the Nebula
    from action_schema import parse_request


class AuthorizationStore:
    """Owner-approval authorization bound to one exact request.

    A token is created only by ``stage`` (an owner approval event). Each token
    is unique even when two approvals carry an identical batch, so consuming
    one approval can never be revived by staging the same batch again.
    Authorization additionally binds the request id, the revision, and the
    batch digest, so a token issued for one request cannot authorize another.
    """

    def __init__(self, ttl_seconds=120, path=None):
        if ttl_seconds <= 0:
            raise ValueError('ttl_seconds must be positive')
        self.ttl_seconds = ttl_seconds
        self.path = path
        self._entries = {}

    def _now(self, now=None):
        return time.time() if now is None else now

    def stage(self, request):
        parsed = parse_request(request)
        token = parsed['digest'] + '-' + uuid.uuid4().hex
        now = self._now()
        self._entries[token] = {
            'digest': parsed['digest'],
            'revision': parsed['revision'],
            'request_id': parsed['request_id'],
            'expires_at': now + self.ttl_seconds,
            'consumed': False,
        }
        return token

    def authorize(self, token, request, now=None):
        entry = self._entries.get(token)
        if entry is None or entry.get('consumed'):
            return False
        current = self._now(now)
        if current >= entry.get('expires_at', 0):
            return False
        try:
            parsed = parse_request(request)
        except ValueError:
            return False
        return (
            parsed['digest'] == entry.get('digest')
            and parsed['revision'] == entry.get('revision')
            and parsed['request_id'] == entry.get('request_id')
        )

    def consume(self, token):
        entry = self._entries.get(token)
        if entry is not None:
            entry['consumed'] = True

    def is_consumed(self, token):
        entry = self._entries.get(token)
        return bool(entry and entry.get('consumed'))

    def purge(self, now=None):
        current = self._now(now)
        dropped = 0
        for token in list(self._entries.keys()):
            entry = self._entries[token]
            if current >= entry.get('expires_at', 0):
                del self._entries[token]
                dropped += 1
        return dropped

    def save(self):
        if not self.path:
            return
        data = {'entries': self._entries}
        tmp = self.path + '.tmp'
        with open(tmp, 'w') as handle:
            json.dump(data, handle, sort_keys=True, separators=(',', ':'))
        os.replace(tmp, self.path)

    def load(self):
        if not self.path or not os.path.exists(self.path):
            return
        with open(self.path, 'r') as handle:
            data = json.load(handle)
        entries = data.get('entries', {})
        if not isinstance(entries, dict):
            raise ValueError('invalid authorization store')
        self._entries = entries

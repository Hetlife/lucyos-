import hashlib
import json

try:  # package import in the LucyOS repo
    from .hid import KEYCODES
except ImportError:  # flat deployment on the Nebula
    from hid import KEYCODES

MAX_ACTIONS = 64
MAX_TEXT_CHARS = 256
MAX_MOVE_DELTA = 2000
MAX_SCROLL = 50
MAX_TOTAL_MS = 30000
ACTION_KINDS = frozenset({'key', 'text', 'move', 'button', 'scroll', 'wait', 'release_all'})

_MODIFIERS = frozenset({'ctrl', 'alt', 'shift', 'super'})
_BUTTONS = frozenset({'left', 'right', 'middle'})
_BUTTON_ACTIONS = frozenset({'down', 'up', 'click'})


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def _require_dict(value, name):
    if not isinstance(value, dict):
        raise ValueError(name + ' must be an object')


def _require_int(value, name, minimum=None, maximum=None):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(name + ' must be an integer')
    if minimum is not None and value < minimum:
        raise ValueError(name + ' is too small')
    if maximum is not None and value > maximum:
        raise ValueError(name + ' is too large')
    return value


def _require_str(value, name, minimum_len=1, maximum_len=None):
    if not isinstance(value, str):
        raise ValueError(name + ' must be a string')
    if len(value) < minimum_len:
        raise ValueError(name + ' must not be empty')
    if maximum_len is not None and len(value) > maximum_len:
        raise ValueError(name + ' is too long')
    return value


def _require_str_list(value, name, allow_empty=False):
    if not isinstance(value, list):
        raise ValueError(name + ' must be a list')
    if not value and not allow_empty:
        raise ValueError(name + ' must not be empty')
    result = []
    for item in value:
        if not isinstance(item, str) or not item or len(item) > 32:
            raise ValueError(name + ' has an invalid item')
        result.append(item)
    return result


def validate_action(action):
    _require_dict(action, 'action')
    kind = action.get('kind')
    if kind not in ACTION_KINDS:
        raise ValueError('unknown action kind')

    if kind == 'release_all':
        if set(action.keys()) != {'kind'}:
            raise ValueError('release_all takes no extra keys')
        return {'kind': 'release_all'}

    if kind == 'text':
        if set(action.keys()) != {'kind', 'text'}:
            raise ValueError('text action has unknown keys')
        text = _require_str(action.get('text'), 'text', 1, MAX_TEXT_CHARS)
        return {'kind': 'text', 'text': text}

    if kind == 'move':
        if set(action.keys()) != {'kind', 'dx', 'dy'}:
            raise ValueError('move action has unknown keys')
        dx = _require_int(action.get('dx'), 'dx')
        dy = _require_int(action.get('dy'), 'dy')
        if abs(dx) > MAX_MOVE_DELTA or abs(dy) > MAX_MOVE_DELTA:
            raise ValueError('move delta exceeds limit')
        return {'kind': 'move', 'dx': dx, 'dy': dy}

    if kind == 'button':
        if set(action.keys()) != {'kind', 'button', 'action'}:
            raise ValueError('button action has unknown keys')
        button = _require_str(action.get('button'), 'button')
        if button not in _BUTTONS:
            raise ValueError('invalid button')
        button_action = _require_str(action.get('action'), 'action')
        if button_action not in _BUTTON_ACTIONS:
            raise ValueError('invalid button action')
        return {'kind': 'button', 'button': button, 'action': button_action}

    if kind == 'scroll':
        if set(action.keys()) != {'kind', 'amount'}:
            raise ValueError('scroll action has unknown keys')
        amount = _require_int(action.get('amount'), 'amount')
        if abs(amount) > MAX_SCROLL:
            raise ValueError('scroll amount exceeds limit')
        return {'kind': 'scroll', 'amount': amount}

    if kind == 'wait':
        if set(action.keys()) != {'kind', 'ms'}:
            raise ValueError('wait action has unknown keys')
        ms = _require_int(action.get('ms'), 'ms', 0, 5000)
        return {'kind': 'wait', 'ms': ms}

    if kind == 'key':
        allowed = {'kind', 'keys', 'modifiers', 'hold_ms'}
        if not set(action.keys()).issubset(allowed):
            raise ValueError('key action has unknown keys')
        keys = [key.lower() for key in _require_str_list(action.get('keys'), 'keys')]
        for key in keys:
            # Reject names the HID encoder cannot turn into a report. Without
            # this, an owner could approve a batch that fails halfway through
            # execution, leaving keys held.
            if key not in KEYCODES:
                raise ValueError('unknown key name: ' + key)
        modifiers = _require_str_list(action.get('modifiers', []), 'modifiers', allow_empty=True)
        modifiers = [modifier.lower() for modifier in modifiers]
        for modifier in modifiers:
            if modifier not in _MODIFIERS:
                raise ValueError('invalid modifier')
        hold_ms = _require_int(action.get('hold_ms', 0), 'hold_ms', 0, 2000)
        return {'kind': 'key', 'keys': keys, 'modifiers': modifiers, 'hold_ms': hold_ms}

    raise ValueError('unknown action kind')


def validate_batch(batch):
    _require_dict(batch, 'batch')
    if set(batch.keys()) != {'actions'}:
        raise ValueError('batch has unknown keys')
    actions = batch.get('actions')
    if not isinstance(actions, list) or not actions:
        raise ValueError('batch actions must be a non-empty list')
    if len(actions) > MAX_ACTIONS:
        raise ValueError('batch is too large')
    normalized = []
    total = 0
    for action in actions:
        item = validate_action(action)
        normalized.append(item)
        if item['kind'] == 'wait':
            total += item['ms']
        elif item['kind'] == 'key':
            total += item['hold_ms']
    if total > MAX_TOTAL_MS:
        raise ValueError('batch exceeds total time limit')
    return {'actions': normalized}


def batch_digest(batch):
    payload = canonical_json(validate_batch(batch))
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def parse_request(payload):
    _require_dict(payload, 'payload')
    if set(payload.keys()) != {'request_id', 'revision', 'batch', 'digest'}:
        raise ValueError('request has unknown keys')
    request_id = _require_str(payload.get('request_id'), 'request_id', 1, 64)
    revision = _require_str(payload.get('revision'), 'revision', 1, 128)
    batch = validate_batch(payload.get('batch'))
    digest = _require_str(payload.get('digest'), 'digest', 1)
    expected = hashlib.sha256(canonical_json(batch).encode('utf-8')).hexdigest()
    if digest != expected:
        raise ValueError('digest mismatch')
    return {'request_id': request_id, 'revision': revision, 'batch': batch, 'digest': digest}

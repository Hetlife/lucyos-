"""S-44 metadata contracts; stdlib validation of the schema's small vocabulary."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from scripts.verify_authority import git

ROOT = Path(__file__).resolve().parents[1]
ARCHITECTURE = ROOT / '.lucy/architecture'
EVIDENCE = ROOT / '.lucy/planning/codebase-reduction-20260918/evidence'
MODULES = {'kernel.state', 'kernel.tasks', 'execution', 'memory', 'skills',
           'interfaces', 'governance', 'business'}
SOURCE_ROOTS = {'aion_core', 'bridges', 'scripts', 'integrations'}


def file_matches(root, pattern):
    if Path(pattern).is_absolute() or '..' in Path(pattern).parts:
        raise AssertionError(f'Unsafe path: {pattern}')
    files = {p.relative_to(root).as_posix() for p in root.glob(pattern) if p.is_file()}
    if not files:
        raise AssertionError(f'No files match: {pattern}')
    return files


def ownership(root, manifests, tracked):
    owners = {}
    for manifest in manifests:
        for pattern in manifest['owned_files']:
            for path in file_matches(root, pattern):
                owners.setdefault(path, set()).add(manifest['module'])
    for path in tracked:
        if Path(path).suffix == '.py' and Path(path).parts[0] in SOURCE_ROOTS:
            if len(owners.get(path, set())) != 1:
                raise AssertionError(f'Expected exactly one owner: {path}')
    return owners


def validate_shape(value, rule):
    # This is deliberately not a general JSON Schema implementation. Fail closed
    # if the checked schema grows beyond the vocabulary implemented here.
    supported = {'type', 'enum', 'minLength', 'items', 'uniqueItems', 'minItems'}
    if set(rule) - supported:
        raise AssertionError(f'Unsupported schema rule: {set(rule) - supported}')
    if 'enum' in rule and value not in rule['enum']:
        raise AssertionError(f'Invalid enum value: {value}')
    if rule.get('type') == 'string':
        if not isinstance(value, str) or len(value) < rule.get('minLength', 0):
            raise AssertionError('Expected nonempty string')
    elif rule.get('type') == 'array':
        if not isinstance(value, list) or len(value) < rule.get('minItems', 0):
            raise AssertionError('Expected array with required items')
        for item in value:
            validate_shape(item, rule['items'])
        if rule.get('uniqueItems') and len(value) != len(set(value)):
            raise AssertionError('Duplicate array items')
    elif 'type' in rule:
        raise AssertionError(f'Unsupported schema type: {rule["type"]}')


class ModuleManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((ARCHITECTURE / 'module.schema.json').read_text())
        cls.paths = sorted((ARCHITECTURE / 'modules').glob('*.json'))
        cls.manifests = [json.loads(p.read_text()) for p in cls.paths]
        cls.tracked = git('-C', str(ROOT), 'ls-files', '-z').rstrip('\0').split('\0')
        cls.graph = json.loads((EVIDENCE / 'dependency_graph.json').read_text())
        cls.metrics = json.loads((EVIDENCE / 'complexity_map.json').read_text())['modules']

    def check_schema(self, manifests):
        self.assertEqual(self.schema['type'], 'object')
        self.assertFalse(self.schema['additionalProperties'])
        for manifest in manifests:
            self.assertIsInstance(manifest, dict)
            self.assertEqual(set(manifest), set(self.schema['required']))
            self.assertEqual(set(manifest), set(self.schema['properties']))
            for field, value in manifest.items():
                validate_shape(value, self.schema['properties'][field])

    def check_dependencies(self, manifests):
        owners = ownership(ROOT, manifests, self.tracked)
        module_owners = {}
        for name, metric in self.metrics.items():
            self.assertEqual(len(owners.get(metric['path'], set())), 1)
            module_owners[name] = next(iter(owners[metric['path']]))
        actual = {(module_owners[a], module_owners[b]) for a, b in self.graph['edges']
                  if module_owners[a] != module_owners[b]}
        for manifest in manifests:
            name = manifest['module']
            allowed = set(manifest['allowed_dependencies'])
            forbidden = set(manifest['forbidden_dependencies'])
            self.assertLessEqual(allowed | forbidden, MODULES - {name})
            self.assertFalse(allowed & forbidden)
            self.assertLessEqual({(name, target) for target in allowed}, actual,
                                 'Allowed dependency lacks S-41 evidence')

    def test_repository_contracts(self):
        self.assertEqual(len(self.paths), 8)
        self.assertEqual({m['module'] for m in self.manifests}, MODULES)
        self.check_schema(self.manifests)
        owners = ownership(ROOT, self.manifests, self.tracked)
        baseline = json.loads((ROOT / '.lucy/authority/HIGH_MODEL_BASELINE.json').read_text())
        protected = set()
        for pattern in baseline['protected_paths']:
            protected.update(p for p in self.tracked if Path(p).match(pattern))
        for path, manifest in zip(self.paths, self.manifests):
            self.assertEqual(path.stem, manifest['module'])
            self.assertLessEqual(len(path.read_text().splitlines()), 60)
            for field in ('tests', 'adrs', 'protected_paths'):
                for pattern in manifest[field]:
                    file_matches(ROOT, pattern)
            expected = {p for p in protected if manifest['module'] in owners.get(p, set())}
            listed = set()
            for pattern in manifest['protected_paths']:
                listed.update(file_matches(ROOT, pattern))
            self.assertEqual(listed, expected)
        self.check_dependencies(self.manifests)

    def test_unowned_and_multiply_owned_fixture_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'aion_core').mkdir()
            (root / 'aion_core/owned.py').touch()
            manifests = [{'module': 'kernel.state', 'owned_files': ['aion_core/owned.py']}]
            tracked = ['aion_core/owned.py']
            ownership(root, manifests, tracked)  # Positive control.
            (root / 'aion_core/unowned.py').touch()
            with self.assertRaisesRegex(AssertionError, 'one owner: aion_core/unowned.py'):
                ownership(root, manifests, tracked + ['aion_core/unowned.py'])
            manifests.append({'module': 'kernel.tasks', 'owned_files': ['aion_core/owned.py']})
            with self.assertRaisesRegex(AssertionError, 'one owner: aion_core/owned.py'):
                ownership(root, manifests, tracked)

    def test_missing_file_and_unsafe_pattern_fail(self):
        for pattern in ('aion_core/does_not_exist.py', '../outside.py', '/outside.py'):
            with self.subTest(pattern=pattern), self.assertRaises(AssertionError):
                file_matches(ROOT, pattern)

    def test_invalid_schema_values_fail(self):
        for field, value in (('module', 'ninth'), ('risk_level', 'unknown'),
                             ('purpose', ''), ('tests', 'tests/test_tasks.py'),
                             ('owned_files', []), ('allowed_dependencies', ['ninth']),
                             ('tests', ['tests/test_tasks.py'] * 2)):
            manifests = copy.deepcopy(self.manifests)
            manifests[0][field] = value
            with self.subTest(field=field), self.assertRaises(AssertionError):
                self.check_schema(manifests)
        for missing in (True, False):
            manifests = copy.deepcopy(self.manifests)
            if missing:
                del manifests[0]['purpose']
            else:
                manifests[0]['extra'] = 'not allowed'
            with self.assertRaises(AssertionError):
                self.check_schema(manifests)

    def test_unsupported_dependency_fails(self):
        manifests = copy.deepcopy(self.manifests)
        # Business does not import interfaces in the recorded S-41 graph.
        business = next(m for m in manifests if m['module'] == 'business')
        self.assertNotIn('interfaces', business['allowed_dependencies'])
        business['allowed_dependencies'].append('interfaces')
        with self.assertRaisesRegex(AssertionError, 'lacks S-41 evidence'):
            self.check_dependencies(manifests)

    def test_conflicting_dependency_fails(self):
        manifests = copy.deepcopy(self.manifests)
        manifests[0]['forbidden_dependencies'] = manifests[0]['allowed_dependencies'][:1]
        self.assertTrue(manifests[0]['forbidden_dependencies'])
        with self.assertRaises(AssertionError):
            self.check_dependencies(manifests)


if __name__ == '__main__':
    unittest.main()

from base64 import b64encode

import pytest

from probirka import MASK, mask_url, redact_value
from probirka._redact import redact_secrets, redact_string, secrets_from_headers, secrets_from_url


@pytest.mark.parametrize(
    ('url', 'expected'),
    [
        ('postgresql://app:hunter2@db:5432/app', 'postgresql://app:***@db:5432/app'),
        ('redis://:hunter2@cache:6379/0', 'redis://:***@cache:6379/0'),
        ('amqp://guest:guest@mq:5672/', 'amqp://guest:***@mq:5672/'),
        (
            'mongodb://app:hunter2@h1:27017,h2:27017/db?replicaSet=rs',
            'mongodb://app:***@h1:27017,h2:27017/db?replicaSet=rs',
        ),
        ('postgresql://app:p%40ss%2Fword@db/app', 'postgresql://app:***@db/app'),
        ('https://user:pass@example.com/health?x=1#frag', 'https://user:***@example.com/health?x=1#frag'),
        # nothing to mask
        ('postgresql://app@db:5432/app', 'postgresql://app@db:5432/app'),
        ('redis://localhost:6379/0', 'redis://localhost:6379/0'),
        ('http://host:8080/path?q=a@b', 'http://host:8080/path?q=a@b'),
        ('localhost:9092', 'localhost:9092'),
        ('', ''),
    ],
)
def test_mask_url(url: str, expected: str) -> None:
    assert mask_url(url) == expected


def test_mask_url_custom_mask() -> None:
    assert mask_url('redis://:hunter2@cache/0', mask='[secure]') == 'redis://:[secure]@cache/0'


def test_mask_url_survives_unparsable_url() -> None:
    # an unbalanced IPv6 bracket makes urlsplit raise; fall back to the regex
    assert mask_url('postgresql://app:hunter2@[::1/app') == 'postgresql://app:***@[::1/app'


@pytest.mark.parametrize(
    ('url', 'expected'),
    [
        ('postgresql://app:hunter2@db/app', ('hunter2', 'YXBwOmh1bnRlcjI=')),
        ('postgresql://app:p%40ss@db/app', ('p%40ss', 'p@ss', 'YXBwOnBAc3M=')),
        ('redis://:hunter2@cache/0', ('hunter2', 'Omh1bnRlcjI=')),
        ('postgresql://app@db/app', ()),
        ('redis://localhost/0', ()),
        ('postgresql://app:abc@db/app', ('YXBwOmFiYw==',)),  # too short to be masked safely, its base64 is not
        (None, ()),
        ('', ()),
    ],
)
def test_secrets_from_url(url: str | None, expected: tuple[str, ...]) -> None:
    assert secrets_from_url(url) == expected


def test_secrets_from_url_survives_unparsable_url() -> None:
    assert secrets_from_url('postgresql://app:hunter2@[::1/app') == ('hunter2', 'YXBwOmh1bnRlcjI=')
    assert secrets_from_url('postgresql://[::1/app') == ()


def test_secrets_from_url_basic_auth_matches_what_http_clients_send() -> None:
    assert b64encode(b'app:hunter2').decode() in secrets_from_url('https://app:hunter2@svc/health')


def test_secrets_from_headers_include_the_token_without_the_scheme() -> None:
    secrets = secrets_from_headers({'Authorization': 'Bearer abc.def', 'X-Token': 'hunter2', 'Accept': 'json'})

    assert secrets == ('Bearer abc.def', 'abc.def', 'hunter2', 'json')
    assert secrets_from_headers(None) == ()
    assert secrets_from_headers({}) == ()


def test_redact_secrets_replaces_every_known_value() -> None:
    text = 'connect to postgresql://app:hunter2@db failed, password "hunter2" rejected'

    assert (
        redact_secrets(text, ('hunter2',))
        == f'connect to postgresql://app:{MASK}@db failed, password "{MASK}" rejected'
    )


def test_redact_secrets_longest_first() -> None:
    assert redact_secrets('token=abcdef', ('abc', 'abcdef')) == f'token={MASK}'


def test_redact_secrets_ignores_short_and_empty_values() -> None:
    assert redact_secrets('a message', ('', 'a', 'age')) == 'a message'
    assert redact_secrets('a message', ()) == 'a message'


@pytest.mark.parametrize(
    ('text', 'expected'),
    [
        ('InvalidURL: amqp://guest:guest@mq/', f'InvalidURL: amqp://guest:{MASK}@mq/'),
        ('GET https://api/health?token=abc&x=1 failed', f'GET https://api/health?token={MASK}&x=1 failed'),
        ('https://api/health?x=1&api_key=abc', f'https://api/health?x=1&api_key={MASK}'),
        ('https://api/health?Signature=abc#frag', f'https://api/health?Signature={MASK}#frag'),
        (
            'ConnectionRefusedError: [Errno 61] Connect call failed',
            'ConnectionRefusedError: [Errno 61] Connect call failed',
        ),
        ('redis://localhost:6379/0 is down', 'redis://localhost:6379/0 is down'),
    ],
)
def test_redact_string(text: str, expected: str) -> None:
    assert redact_string(text) == expected


def test_redact_value_masks_sensitive_keys_whole() -> None:
    info = {
        'version': '1.0',
        'password': 'hunter2',
        'API_KEY': 'abc',
        'Authorization': 'Bearer abc',
        'db': {'dsn': 'postgresql://app:hunter2@db/app', 'pool_size': 10, 'secret_ttl': 30},
        'urls': ['https://user:pass@a/', 'https://b/'],
        'pairs': ('x', {'token': 1}),
        'count': 3,
        'none': None,
        1: 'not a string key',
    }

    assert redact_value(info) == {
        'version': '1.0',
        'password': MASK,
        'API_KEY': MASK,
        'Authorization': MASK,
        'db': {'dsn': f'postgresql://app:{MASK}@db/app', 'pool_size': 10, 'secret_ttl': MASK},
        'urls': [f'https://user:{MASK}@a/', 'https://b/'],
        'pairs': ('x', {'token': MASK}),
        'count': 3,
        'none': None,
        1: 'not a string key',
    }


def test_redact_value_leaves_other_objects_alone() -> None:
    obj = object()

    assert redact_value(obj) is obj
    assert redact_value(None) is None
    assert redact_value(True) is True

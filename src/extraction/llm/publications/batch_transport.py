"""Small researcher-terminal Batch/Files HTTP client; never retries mutating submissions."""
from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .request_builder import canonical_json
from .resumable_production_journal import require, replace_atomic


def unique(pairs: list) -> dict:
    """Reject ambiguous duplicate JSON keys in provider artifacts."""
    result = {}
    for key, value in pairs:
        require(key not in result, 'DUPLICATE_JSON_KEY')
        result[key] = value
    return result


def decode(data: bytes) -> Any:
    """Parse provider JSON without silently choosing duplicate fields."""
    return json.loads(data, object_pairs_hook=unique)


class BatchAPI:
    """Use existing credentials; retries are limited to read-only/token-count operations."""

    def __init__(self, key: str) -> None:
        """Keep credentials in memory only."""
        self.key = key

    def request(self, method: str, path: str, data: bytes | None = None,
                content_type: str = 'application/json', safe: bool = False) -> bytes:
        """Persisted intents precede POST; an ambiguous POST is never repeated here."""
        for attempt in range(5 if safe else 1):
            try:
                req = Request('https://api.openai.com/v1' + path, data=data, method=method,
                              headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': content_type})
                with urlopen(req, timeout=120) as response:
                    return response.read()
            except HTTPError as exc:
                if not safe or exc.code not in (429, 500, 502, 503, 504) or attempt == 4:
                    raise ValueError('BATCH_HTTP_%s; durable intent requires reconciliation for POST' % exc.code) from None
                delay = exc.headers.get('Retry-After', '')
                time.sleep(min(60, float(delay) if delay.isdigit() else 2 ** attempt))
            except (URLError, TimeoutError, OSError):
                if not safe or attempt == 4:
                    raise ValueError('BATCH_TRANSPORT_UNCERTAIN; restart to reconcile, never blind resubmit') from None
                time.sleep(2 ** attempt)
        raise ValueError('BATCH_READ_RETRIES_EXHAUSTED')

    def listing(self, resource: str) -> list[dict]:
        """Fully paginate; recovery must not infer absence from the first page."""
        result, after = [], None
        while True:
            query = {'limit': 100}
            if resource == 'files':
                query['purpose'] = 'batch'
            if after:
                query['after'] = after
            page = decode(self.request('GET', '/' + resource + '?' + urlencode(query), safe=True))
            result.extend(page['data'])
            if not page.get('has_more'):
                return result
            next_id = page['data'][-1]['id']
            require(next_id != after, 'PAGINATION_DID_NOT_ADVANCE')
            after = next_id

    def count(self, body: dict) -> dict:
        """Obtain exact schema-aware input tokens without generating model output."""
        count_body = {k: body[k] for k in ('model', 'input', 'reasoning', 'text')}
        value = decode(self.request('POST', '/responses/input_tokens', canonical_json(count_body), safe=True))
        require(value.get('object') == 'response.input_tokens' and type(value.get('input_tokens')) is int
                and value['input_tokens'] > 0, 'INVALID_INPUT_TOKEN_COUNT')
        return value

    def upload(self, path: Path) -> dict:
        """Upload one sealed JSONL with a content-addressed filename, without POST retry."""
        boundary = 'publication-' + uuid.uuid4().hex
        data = (('--' + boundary + '\r\nContent-Disposition: form-data; name="purpose"\r\n\r\nbatch\r\n'
                 '--' + boundary + '\r\nContent-Disposition: form-data; name="file"; filename="' + path.name +
                 '"\r\nContent-Type: application/jsonl\r\n\r\n').encode() + path.read_bytes() +
                ('\r\n--' + boundary + '--\r\n').encode())
        return decode(self.request('POST', '/files', data, 'multipart/form-data; boundary=' + boundary))

    def create(self, file_id: str, metadata: dict) -> dict:
        """Submit once; metadata enables exact recovery of a lost acknowledgement."""
        return decode(self.request('POST', '/batches', canonical_json(dict(input_file_id=file_id,
            endpoint='/v1/responses', completion_window='24h', metadata=metadata))))

    def retrieve(self, batch_id: str) -> dict:
        """Poll an existing batch without dispatching any new requests."""
        return decode(self.request('GET', '/batches/' + batch_id, safe=True))

    def content(self, file_id: str) -> bytes:
        """Retrieve exact output/error/input bytes for durable local processing."""
        return self.request('GET', '/files/' + file_id + '/content', safe=True)

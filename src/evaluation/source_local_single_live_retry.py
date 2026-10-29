"""One explicitly authorized supplemental response; never edit or integrate frozen v6."""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path

from src.evaluation import source_local_file_upload_recovery as files
from src.extraction.llm import source_family_batch as adapter
from src.extraction.llm import source_local_specialized as specialized

ROOT, QUEUE, QUEUE_SHA = files.ROOT, files.QUEUE, files.QUEUE_SHA
REQUEST_ID = 'github:v042:software_roles_and_use:c44ac5e4d5b28b6caf8d856e04057b61ab5d82ef050d80e016cff636f5f945a5'
RESPONSE_ID = 'resp_0525409134371023016ae2d8b56d8c87d19ee005501a8545fc'
BUNDLE_SHA = '338d6436000e79fc0bb63cf067d6ad85c0643c9b83461e3d651f02569d80168b'
OUTPUT = Path('var/study2_step13/source-local-single-live-retry/v1')
require, digest, canonical = files.require, files.digest, files.canonical


def load_original(repo=ROOT):
    """Verify exact frozen bytes and all original implementation pins, without rewriting."""
    raw = (repo / QUEUE / 'queue-manifest.json').read_bytes()
    require(digest(raw) == QUEUE_SHA, 'QUEUE_DRIFT')
    require(digest((repo / QUEUE / 'execution/batch/run-manifest.json').read_bytes()) == files.RUN_SHA,
            'RUN_MANIFEST_DRIFT')
    queue = files.transport.decode(raw)
    matches = [e for e in queue['requests'] if e['identity']['requestID'] == REQUEST_ID]
    require(len(matches) == 1, 'REQUEST_ASSOCIATION_DRIFT')
    entry = matches[0]
    require(entry['ownerID'] == 'github:repo:807667447' and
            entry['groupID'] == 'software_roles_and_use' and
            entry['bundleSha256'] == BUNDLE_SHA and entry['bundleFile'] == BUNDLE_SHA + '.json', 'ENTRY_DRIFT')
    for path, sha in queue['implementationPins'].items():
        require(digest((repo / path).read_bytes()) == sha, 'IMPLEMENTATION_PIN_DRIFT:' + path)
    raw = (repo / QUEUE / 'queue' / entry['bundleFile']).read_bytes()
    require(digest(raw) == BUNDLE_SHA, 'BUNDLE_DRIFT')
    prepared = files.transport.decode(raw)
    require(adapter.fingerprint(prepared) == entry['identity'], 'IDENTITY_DRIFT')
    require(prepared['body']['max_output_tokens'] == 32768 and prepared['body']['store'] is False,
            'ENVELOPE_DRIFT')
    return prepared


def validate_response(prepared, response):
    """Require complete output and replay authentic text through the original group validator."""
    require(response.get('status') == 'completed' and not response.get('incomplete_details') and
            response.get('model') == prepared['body']['model'] and response.get('id') and
            isinstance(response.get('usage'), dict), 'RESPONSE_NOT_USABLE')
    texts = []
    for item in response.get('output', []):
        if item.get('type') == 'message':
            require(item.get('status') == 'completed', 'MESSAGE_INCOMPLETE')
            for content in item.get('content', []):
                require(content.get('type') == 'output_text', 'REFUSAL_OR_UNEXPECTED_CONTENT')
                texts.append(content['text'])
    require(len(texts) == 1, 'AMBIGUOUS_MODEL_OUTPUT')
    return specialized.replay(prepared, texts[0].encode(),
        expected_request_sha256=prepared['semanticRequest']['requestSha256'])


def execute(prepared, output, client, *, authorized=False):
    """One durable intent permits one SDK POST; every later invocation fails closed."""
    require(authorized, 'EXPLICIT_ONE_POST_AUTHORIZATION_REQUIRED')
    files.durable_directory(output)
    with (output / 'recovery.lock').open('a+b') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        require(not (output / 'intent.json').exists(), 'PRIOR_INTENT_STOP_NO_REDISPATCH')
        provenance = dict(requestID=REQUEST_ID, originalResponseID=RESPONSE_ID,
            originalJobID='job-000003', queueSha256=QUEUE_SHA, runManifestSha256=files.RUN_SHA,
            bundleSha256=BUNDLE_SHA,
            providerBodySha256=digest(canonical(prepared['body'])), providerParameterChanges={},
            timeoutSeconds=600, maxRetries=0, authorizedPosts=1, sdkVersion='1.109.1')
        files.seal(output / 'intent.json', provenance)
        try:
            response = client.responses.create(**prepared['body']).model_dump(mode='json')
            files.seal(output / 'response.json', response)
        except BaseException as exc:
            files.seal(output / 'outcome.json', dict(status='uncertain', usable=False,
                        diagnostic=files.safe_diagnostic(exc)))
            raise ValueError('UNCERTAIN_OUTCOME_STOP_NO_REDISPATCH') from None
        try:
            report = validate_response(prepared, response)
            files.seal(output / 'semantic-replay.json', report)
        except Exception as exc:
            files.seal(output / 'outcome.json', dict(status='recorded_not_usable', usable=False,
                responseID=response.get('id'), usage=response.get('usage'),
                incomplete_details=response.get('incomplete_details'), diagnostic=files.safe_diagnostic(exc)))
            raise ValueError('RESPONSE_RECORDED_NOT_USABLE_NO_REDISPATCH') from None
        result = dict(status='validated_supplemental_response', usable=True, responseID=response['id'],
            usage=response['usage'], responseSha256=digest(canonical(response)),
            integrated=False, kgAuthorization=False)
        files.seal(output / 'outcome.json', result)
        return result


def main():
    """Researcher-only live execution; no automatic retries or Batch operations."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--authorize-one-post', action='store_true')
    args = parser.parse_args()
    require(args.authorize_one_post, 'EXPLICIT_ONE_POST_AUTHORIZATION_REQUIRED')
    prepared = load_original()
    import openai
    require(openai.__version__ == '1.109.1', 'SDK_VERSION_DRIFT')
    with openai.OpenAI(api_key=files.openai_provider.load_openai_api_key(),
            base_url='https://api.openai.com/v1', timeout=600, max_retries=0) as client:
        result = execute(prepared, ROOT / OUTPUT, client, authorized=True)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

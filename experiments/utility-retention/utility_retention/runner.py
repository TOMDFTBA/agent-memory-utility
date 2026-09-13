"""Stage 1 runner with strict identity checks and per-response durable resume."""
import argparse
import random
import time
from pathlib import Path

from longmem.config import load_config
from longmem.experiment_contracts import SCHEMA_VERSION
from longmem.experiment_io import (append_jsonl, public_model_config, read_json, read_jsonl,
                                   runtime_metadata, sha256_file, source_hashes, write_json)
from .dataset import pilot_dataset, validate
from .engine import Engine, historical_features, score
from .labeling import evaluate, expected_keys, key

HERE = Path(__file__).resolve().parents[1]
ROOT = HERE.parents[1]


def model_identity(config, backend):
    result = {k: public_model_config(config[k]) for k in ('embedding', 'generation')}
    result['name'] = 'test-only' if backend == 'test' else Path(config['generation']['model_path']).name
    result['revision'] = config['generation'].get('revision', 'local')
    result['metadata_sha256'] = {}
    if backend == 'model':
        for section in ('embedding', 'generation'):
            folder = Path(config[section]['model_path'])
            result['metadata_sha256'][section] = {
                p.relative_to(folder).as_posix(): sha256_file(p) for p in sorted(folder.rglob('*'))
                if p.is_file() and p.suffix in {'.json', '.py', '.model', '.safetensors', '.bin', '.txt'}
            }
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dataset', type=Path)
    parser.add_argument('--protocol', type=Path, default=HERE / 'protocol.md')
    parser.add_argument('--config', type=Path, default=HERE / 'configs/pilot.json')
    parser.add_argument('--model-config', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--backend', choices=['test', 'model'], default='test')
    parser.add_argument('--seed', type=int, default=20260912)
    args = parser.parse_args()
    settings = read_json(args.config)
    for name in ('read_budget', 'top_k', 'repeats', 'context_samples_per_stratum'):
        if type(settings[name]) is not int or settings[name] < 1:
            raise ValueError(f'{name} must be a positive integer')
    for name in ('minimum_effect', 'max_label_std', 'minimum_sign_stability', 'minimum_memory_dependency'):
        if not 0 <= settings[name] <= 1:
            raise ValueError(f'{name} must be in [0, 1]')
    args.output.mkdir(parents=True, exist_ok=True)
    manifest_path = args.output / 'manifest.json'
    if not manifest_path.exists() and any(args.output.iterdir()):
        raise ValueError('Output directory is nonempty and has no manifest')
    dataset_path = args.dataset
    if dataset_path is None:
        dataset_path = args.output / 'pilot-dataset.json'
        if not dataset_path.exists():
            write_json(dataset_path, pilot_dataset())
    dataset = read_json(dataset_path)
    validate(dataset)
    model_config = load_config(args.model_config or (ROOT / 'configs/test.yaml' if args.backend == 'test' else None))
    if args.backend == 'test':
        model_config['embedding'] = {'backend': 'hash-test'}
        model_config['generation'] = {'backend': 'evidence-test'}
    sources = list(HERE.glob('*.py')) + list((HERE / 'utility_retention').glob('*.py')) + list((ROOT / 'src/longmem').glob('*.py'))
    identity = dict(protocol_sha256=sha256_file(args.protocol), dataset_sha256=sha256_file(dataset_path),
                    source_hashes=source_hashes(sources, root=ROOT),
                    model=model_identity(model_config, args.backend),
                    parameters=dict(settings=settings, seed=args.seed, backend=args.backend),
                    tokenizer='utf8-byte-test-v1' if args.backend == 'test' else 'generation-tokenizer; add_special_tokens=False')
    manifest = dict(schema_version=SCHEMA_VERSION, experiment_id='utility-retention-v0.2-e1',
                    **identity, runtime=runtime_metadata(), status='RUNNING')
    if manifest_path.exists():
        previous = read_json(manifest_path)
        if any(previous.get(k) != v for k, v in identity.items()):
            raise ValueError('Resume identity mismatch; use a new output directory')
    write_json(manifest_path, manifest)
    try:
        run(args, dataset, model_config, settings, manifest, manifest_path)
    except Exception as error:
        manifest.update(status='FAILED', error_type=type(error).__name__)
        write_json(manifest_path, manifest)
        raise


def run(args, dataset, model_config, settings, manifest, manifest_path):
    engine = Engine(model_config, args.backend, settings['read_budget'], settings['top_k'])
    seeds = [args.seed + i for i in range(settings['repeats'])]
    context_ids, features = {}, []
    for s in dataset:
        past = historical_features(s['memories'], s['history_queries'], s['event_order'], engine)
        features.extend(dict(snapshot_id=s['snapshot_id'], **r) for r in past)
        # Sample past-only retrieved / not-retrieved strata; selection never sees future answers.
        rng = random.Random(f'{args.seed}:{s["snapshot_id"]}')
        selected = []
        for observed in (False, True):
            candidates = sorted(r['memory_id'] for r in past if bool(r['retrieval_frequency']) == observed)
            selected.extend(rng.sample(candidates, min(len(candidates), settings['context_samples_per_stratum'])))
        context_ids[s['snapshot_id']] = sorted(selected)
    write_json(args.output / 'history-features.json', features)
    write_json(args.output / 'dataset-manifest.json', dict(snapshots=dataset,
               splits={split: sorted({s['trajectory_id'] for s in dataset if s['split'] == split})
                       for split in ('train', 'validation', 'test')}, context_ids=context_ids, seeds=seeds))
    response_path = args.output / 'responses.jsonl'
    responses = read_jsonl(response_path) if response_path.exists() else []
    done = {key(r): r for r in responses}
    expected = expected_keys(dataset, seeds, context_ids)
    if len(expected) > settings.get('max_generations', len(expected)):
        raise ValueError('Planned generation count exceeds frozen ceiling')
    spent = sum(r['duration_seconds'] for r in responses)
    if len(done) != len(responses) or not set(done) <= expected:
        raise ValueError('Duplicate or unexpected saved responses')
    for s in dataset:
        for seed in seeds:
            for q in s['future_queries']:
                full_context = None
                conditions = [('full', None), ('no_memory', None)]
                conditions += [('storage_deletion', m['memory_id']) for m in s['memories']]
                conditions += [('context_deletion', mid) for mid in context_ids[s['snapshot_id']]]
                for condition, mid in conditions:
                    identity = dict(snapshot_id=s['snapshot_id'], query_id=q['query_id'], seed=seed,
                                    condition=condition, deleted_memory_id=mid)
                    if key(identity) in done:
                        if condition == 'full':
                            full_context = done[key(identity)]['context']
                        continue
                    if spent >= settings.get('max_duration_seconds', float('inf')):
                        raise RuntimeError('Frozen cumulative runtime ceiling reached')
                    start = time.perf_counter()
                    storage = [] if condition == 'no_memory' else [m for m in s['memories']
                               if condition != 'storage_deletion' or m['memory_id'] != mid]
                    if condition == 'context_deletion':
                        context = [m for m in full_context if m['memory_id'] != mid]
                        ranking = done[(s['snapshot_id'], q['query_id'], seed, 'full', None)]['ranking']
                    else:
                        context, ranking = engine.retrieve(storage, q['text'])
                    generated = engine.answer(q['text'], context, seed)
                    record = dict(**identity, trajectory_id=s['trajectory_id'], split=s['split'],
                                  backend=args.backend, status='OK', query=q['text'], gold_answer=q['gold_answer'],
                                  storage_ids=[m['memory_id'] for m in storage], context=context, ranking=ranking,
                                  **generated, metrics=score(generated['generated_answer'], q['gold_answer']),
                                  duration_seconds=time.perf_counter() - start)
                    spent += record['duration_seconds']
                    append_jsonl(response_path, record)
                    responses.append(record)
                    done[key(record)] = record
                    if condition == 'full':
                        full_context = context
    utilities, labels, report = evaluate(dataset, responses, seeds, context_ids, settings, args.backend)
    write_json(args.output / 'query-utility.json', utilities)
    write_json(args.output / 'future-value-labels.json', labels)
    write_json(args.output / 'reliability-report.json', report)
    manifest.update(status='COMPLETE', response_count=len(responses), ready_for_stage2=report['ready_for_stage2'])
    write_json(manifest_path, manifest)
    print(f'COMPLETE: {len(responses)} responses; ready_for_stage2={report["ready_for_stage2"]}')

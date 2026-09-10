"""Recompute all rankings and prove full text-token coverage without loading models."""
import argparse
import importlib.util
import json
import os
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
os.environ.setdefault('HF_HOME', str(PROJECT / 'cache/huggingface'))
os.environ.setdefault('HF_HUB_OFFLINE', '1')


def verify(output):
    import hashlib
    from transformers import AutoTokenizer
    spec = importlib.util.spec_from_file_location('pilot', HERE / 'run_demo.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = json.loads((output / 'results.json').read_text())
    manifest = json.loads((output / 'manifest.json').read_text())
    records = json.loads((output / 'chunks.json').read_text())
    config = json.loads((output / 'config.json').read_text())
    assert result['config'] == config
    pages, queries = manifest['pages'], manifest['queries']
    assert len(set(p['page_id'] for p in pages)) == len(pages)
    assert len(set(q['query_id'] for q in queries)) == len(queries)
    arrays = np.load(output / 'index.npz', allow_pickle=False)
    assert arrays['page_ids'].tolist() == [p['page_id'] for p in pages]
    for page in pages:
        for key, digest in page['artifact_sha256'].items():
            assert hashlib.sha256((output / page[key]).read_bytes()).hexdigest() == digest
    tokenizer = AutoTokenizer.from_pretrained(PROJECT.parent / 'MiniCPM-Embedding/model',
                                             trust_remote_code=True, local_files_only=True)
    for source, key in [('native_text', 'native_text_path'), ('ocr_text', 'ocr_text_path')]:
        chunks = records[source]['chunks']
        assert len(chunks) == len(arrays[source + '_vectors']) == len(arrays[source + '_owners'])
        for page_index, page in enumerate(pages):
            ids = tokenizer.encode((output / page[key]).read_text(), add_special_tokens=False)
            assert ids == records[source]['page_token_ids'][page_index]
            selected = [(i, c) for i, c in enumerate(chunks) if c['page_id'] == page['page_id']]
            expected = list(module.chunk_ranges(len(ids), config['chunk_tokens'], config['overlap_tokens']))
            assert [(c['start'], c['end']) for _, c in selected] == expected
            covered = np.zeros(len(ids), dtype=bool)
            for index, chunk in selected:
                assert arrays[source + '_owners'][index] == page_index
                assert chunk['token_ids'] == ids[chunk['start']:chunk['end']]
                assert len(tokenizer.build_inputs_with_special_tokens(chunk['token_ids'])) <= config['model_max_tokens']
                covered[chunk['start']:chunk['end']] = True
            assert covered.all(), 'Missing text tokens'
    matrices = {'visual': arrays['visual_queries'] @ arrays['visual_vectors'].T}
    for source in ['native_text', 'ocr_text']:
        matrices[source] = module.aggregate(arrays['text_queries'] @ arrays[source + '_vectors'].T,
                                            arrays[source + '_owners'], len(pages))
    assert len(result['results']) == len(queries)
    for i, (row, query) in enumerate(zip(result['results'], queries)):
        assert all(row[k] == v for k, v in query.items())
        for source, matrix in matrices.items():
            order = np.argsort(-matrix[i], kind='stable')
            expected = [pages[j]['page_id'] for j in order]
            assert expected == [r['page_id'] for r in row[source]]
            assert np.allclose(matrix[i, order], [r['score'] for r in row[source]], atol=1e-6)
            assert row[source + '_rank'] == expected.index(query['target_page_id']) + 1
    for key, values in arrays.items():
        if key.endswith(('vectors', 'queries')):
            assert np.isfinite(values).all()
            assert np.allclose(np.linalg.norm(values, axis=1), 1, atol=1e-3)
    summary = {'status': 'PASS', 'page_count': len(pages), 'query_count': len(queries),
               'page_scores_recomputed': len(pages) * len(queries) * 3,
               'text_token_coverage': '100% for both native PDF and OCR text',
               'native_text_chunks': len(records['native_text']['chunks']),
               'ocr_text_chunks': len(records['ocr_text']['chunks']),
               'checks': ['input hashes', 'full tokenizer coverage', 'chunk size and ownership',
                          'normalized finite vectors', 'all scores and rankings', 'target ranks']}
    (output / 'verification.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path, nargs='?', default=HERE / 'results/v0.1')
    verify(parser.parse_args().output.resolve())

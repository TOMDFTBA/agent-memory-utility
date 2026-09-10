"""Three-way local page retrieval: VisRAG, native PDF text, real Tesseract OCR."""
import argparse
import gc
import importlib.util
import os
import sys
from pathlib import Path
import shutil
import subprocess
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
WORKSPACE = PROJECT.parent
sys.path.insert(0, str(PROJECT / 'src'))
sys.path.insert(0, str(HERE))

from longmem.experiment_io import sha256_file, write_json
from page_dataset import prepare_pages
os.environ.setdefault('HF_HOME', str(PROJECT / 'cache/huggingface'))
os.environ.setdefault('HF_HUB_OFFLINE', '1')


def chunk_ranges(length, size, overlap):
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError('Require size > 0 and 0 <= overlap < size')
    if length <= 0:
        raise ValueError('Empty text is an explicit OCR/input failure')
    start = 0
    while start < length:
        end = min(start + size, length)
        yield start, end
        if end == length:
            break
        start = end - overlap


def aggregate(chunk_scores, owners, page_count):
    import numpy as np
    if len(owners) != chunk_scores.shape[1] or set(owners) != set(range(page_count)):
        raise ValueError('Every page must own at least one scored chunk')
    owners = np.asarray(owners)
    return np.stack([chunk_scores[:, owners == i].max(axis=1) for i in range(page_count)], axis=1)


def ocr_runtime():
    env = os.environ.copy()
    local = PROJECT / 'cache/tesseract/root'
    binary = local / 'usr/bin/tesseract'
    if binary.exists():
        env['LD_LIBRARY_PATH'] = str(local / 'usr/lib/x86_64-linux-gnu') + (':' + env['LD_LIBRARY_PATH'] if env.get('LD_LIBRARY_PATH') else '')
        env['TESSDATA_PREFIX'] = str(local / 'usr/share/tesseract-ocr/5/tessdata')
    else:
        found = shutil.which('tesseract')
        if not found:
            raise RuntimeError('Tesseract missing. Run setup_ocr.py or install tesseract-ocr and tesseract-ocr-eng.')
        binary = Path(found)
    env['OMP_THREAD_LIMIT'] = '4'
    version = subprocess.run([str(binary), '--version'], env=env, check=True, capture_output=True, text=True).stdout
    languages = subprocess.run([str(binary), '--list-langs'], env=env, check=True, capture_output=True, text=True).stdout
    if 'eng' not in languages.splitlines():
        raise RuntimeError('Tesseract English language data missing')
    return str(binary), env, version


def prepare(output):
    return prepare_pages(paper_directory=WORKSPACE / 'VisRAG/papers', output=output)


def encode_visual(pages, queries, output):
    import numpy as np
    import torch
    import torch.nn.functional as F
    from PIL import Image
    from transformers import AutoModel, AutoTokenizer
    path = WORKSPACE / 'VisRAG/model-VisRAG-Ret'
    tok = AutoTokenizer.from_pretrained(path, trust_remote_code=True, local_files_only=True)
    model = AutoModel.from_pretrained(path, trust_remote_code=True, local_files_only=True,
                                     torch_dtype=torch.bfloat16).to('cuda').eval()
    def encode(text='', image=None):
        with torch.inference_mode():
            out = model(text=[text], image=[image], tokenizer=tok)
            weights = out.attention_mask * out.attention_mask.cumsum(dim=1)
            pooled = (out.last_hidden_state.float() * weights.unsqueeze(-1)).sum(1) / weights.sum(1, keepdim=True)
            return F.normalize(pooled, dim=1).cpu().numpy()
    vectors = []
    for page in pages:
        print('Visual:', page['page_id'], flush=True)
        with Image.open(output / page['image_path']) as im:
            vectors.append(encode(image=im.convert('RGB')))
    qvectors = np.concatenate([encode('Represent this query for retrieving relevant documents: ' + q['query']) for q in queries])
    vectors = np.concatenate(vectors)
    del model, tok
    gc.collect()
    torch.cuda.empty_cache()
    return vectors, qvectors


def encode_texts(pages, queries, output, config):
    import numpy as np
    import torch
    import torch.nn.functional as F
    spec = importlib.util.spec_from_file_location('shared_embedder', PROJECT / 'src/longmem/embedder.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    embedder = module.MiniCPMEmbedder(WORKSPACE / 'MiniCPM-Embedding/model', device='cuda', max_length=2048, batch_size=1)
    embedder._load()
    tokenizer = embedder.tokenizer
    def encode_ids(ids):
        # Never decode/re-tokenize chunks or truncate. Preserve the original token sequence.
        ids = tokenizer.build_inputs_with_special_tokens(ids)
        if len(ids) > 2048:
            raise ValueError('Chunk including special tokens exceeds model limit')
        batch = {'input_ids': torch.tensor([ids], device='cuda'),
                 'attention_mask': torch.ones((1, len(ids)), device='cuda', dtype=torch.long)}
        with torch.inference_mode():
            hidden = embedder.model(**batch).last_hidden_state.float()
            # Shared model applies position weights internally: plain masked mean here.
            mask = batch['attention_mask'].unsqueeze(-1)
            pooled = (hidden * mask).sum(1) / mask.sum(1)
            return F.normalize(pooled, dim=1).cpu().numpy()
    qvectors = np.concatenate([encode_ids(tokenizer.encode('Query: ' + q['query'], add_special_tokens=False)) for q in queries])
    artifacts = {}
    records = {}
    for source, key in [('native_text', 'native_text_path'), ('ocr_text', 'ocr_text_path')]:
        chunks, owners, vectors, full_tokens = [], [], [], []
        for page_index, page in enumerate(pages):
            text = (output / page[key]).read_text()
            ids = tokenizer.encode(text, add_special_tokens=False)
            full_tokens.append(ids)
            for start, end in chunk_ranges(len(ids), config['chunk_tokens'], config['overlap_tokens']):
                token_ids = ids[start:end]
                chunks.append({'page_id': page['page_id'], 'start': start, 'end': end,
                               'token_ids': token_ids, 'text_preview': tokenizer.decode(token_ids)})
                owners.append(page_index)
                vectors.append(encode_ids(token_ids))
            print(source, page['page_id'], len(ids), 'tokens; no truncation', flush=True)
        artifacts[source + '_vectors'] = np.concatenate(vectors)
        artifacts[source + '_owners'] = np.array(owners)
        records[source] = {'chunks': chunks, 'page_token_ids': full_tokens}
    artifacts['text_queries'] = qvectors
    write_json(output / 'chunks.json', records)
    return artifacts, embedder.version


def report(result, output):
    lines = ['# 三路页面检索对照', '', '真实 VisRAG-Ret 与 MiniCPM-Embedding；Tesseract 从同一批 PNG 识别文字。', '',
             '| 问题 | 指定页 | 视觉名次 | 原生文本名次 | OCR名次 |', '|---|---|---:|---:|---:|']
    for row in result['results']:
        lines.append(f"| {row['query']} | {row['target_page_id']} | {row['visual_rank']} | {row['native_text_rank']} | {row['ocr_text_rank']} |")
    lines += ['', '## 运行口径', '',
              '文本按 512 个内容 tokens 分块，相邻块重叠 64 tokens，再加模型特殊 token；直接编码原始 token ID，无截断。页面得分为其所有块的最高余弦相似度，两条文本路径使用同一模型、问题和聚合规则。', '',
              'OCR 固定英文、PSM 3、OEM 1；保存识别文本、TSV 坐标/置信度及日志。未对 OCR 手工修正。页面最长边沿用 1400 px，避免把分辨率改变混入本次对照。', '',
              '## 边界', '',
              '这是固定 8 页、5 个手工问题上的描述性结果，目标不是穷尽相关性标注。原生文本不是完美 OCR 标准答案；两者的阅读顺序可能不同，不能直接把文本差异当字符错误率。页面得分取最大值会使块数更多的页面获得更多匹配机会。视觉与文本使用不同编码器；不能把差异全部归因于模态。没有运行生成器，没有证明答案正确或长期记忆有效。', '',
              '逐问题的三路 top-3、最高分文本块和源图像链接见 cases.md；所有原始结果与向量保存在本目录。']
    (output / 'report.md').write_text('\n'.join(lines) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=HERE / 'results/v0.1')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('Output already exists; select a new --output directory to preserve prior runs')
    binary, env, version = ocr_runtime()
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('GPU unavailable; enable device access. No silent fallback.')
    output.mkdir(parents=True)
    config = {'chunk_tokens': 512, 'overlap_tokens': 64, 'model_max_tokens': 2048,
              'page_aggregation': 'max_chunk_cosine', 'ocr_language': 'eng', 'ocr_psm': 3,
              'ocr_oem': 1, 'image_max_side': 1400}
    write_json(output / 'config.json', config)
    pages, queries = prepare(output)
    for page in pages:
        print('OCR:', page['page_id'], flush=True)
        prefix = output / 'examples' / (page['page_id'] + '.ocr')
        proc = subprocess.run([binary, str(output / page['image_path']), str(prefix), '-l', 'eng',
                               '--psm', '3', '--oem', '1', 'txt', 'tsv'],
                              env=env, check=True, capture_output=True, text=True)
        (prefix.parent / (prefix.name + '.log')).write_text(proc.stderr)
        page['ocr_text_path'] = 'examples/' + prefix.name + '.txt'
        page['ocr_tsv_path'] = 'examples/' + prefix.name + '.tsv'
        if not (output / page['ocr_text_path']).read_text().strip():
            raise ValueError('Empty OCR for ' + page['page_id'])
        page['artifact_sha256'] = {key: sha256_file(output / page[key]) for key in
            ['image_path', 'native_text_path', 'ocr_text_path', 'ocr_tsv_path']}
    write_json(output / 'manifest.json', {'pages': pages, 'queries': queries})
    start = time.perf_counter()
    visual, visual_queries = encode_visual(pages, queries, output)
    visual_seconds = time.perf_counter() - start
    start = time.perf_counter()
    arrays, text_version = encode_texts(pages, queries, output, config)
    import numpy as np
    arrays.update(visual_vectors=visual, visual_queries=visual_queries, page_ids=np.array([p['page_id'] for p in pages]))
    for key, value in arrays.items():
        if key.endswith(('vectors', 'queries')):
            if not np.isfinite(value).all() or not np.allclose(np.linalg.norm(value, axis=1), 1, atol=1e-3):
                raise ValueError('Invalid normalized vectors: ' + key)
    matrices = {'visual': visual_queries @ visual.T}
    for source in ['native_text', 'ocr_text']:
        matrices[source] = aggregate(arrays['text_queries'] @ arrays[source + '_vectors'].T,
                                     arrays[source + '_owners'], len(pages))
    rows = []
    for i, q in enumerate(queries):
        row = dict(q)
        for source, matrix in matrices.items():
            order = np.argsort(-matrix[i], kind='stable')
            row[source] = [{'page_id': pages[j]['page_id'], 'score': float(matrix[i, j])} for j in order]
            row[source + '_rank'] = next(k + 1 for k, j in enumerate(order) if pages[j]['page_id'] == q['target_page_id'])
        rows.append(row)
    np.savez(output / 'index.npz', **arrays)
    result = {'status': 'completed', 'config': config, 'device': torch.cuda.get_device_name(0),
              'torch': torch.__version__, 'rocm': torch.version.hip, 'ocr_version': version,
              'text_model_version': text_version, 'script_sha256': sha256_file(Path(__file__)),
              'shared_encoder_sha256': sha256_file(PROJECT / 'src/longmem/embedder.py'),
              'visual_model_files': {p.name: sha256_file(p) for p in (WORKSPACE / 'VisRAG/model-VisRAG-Ret').iterdir() if p.suffix in {'.json', '.py'}},
              'visual_seconds_including_load': visual_seconds,
              'text_seconds_including_load': time.perf_counter() - start, 'results': rows}
    write_json(output / 'results.json', result)
    report(result, output)
    print('Completed:', output, flush=True)


if __name__ == '__main__':
    main()

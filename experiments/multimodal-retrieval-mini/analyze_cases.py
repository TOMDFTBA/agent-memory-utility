"""Export all five cases, including top-3 and source chunks, without selecting wins."""
import argparse
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent


def main(output):
    result = json.loads((output / 'results.json').read_text())
    chunks = json.loads((output / 'chunks.json').read_text())
    manifest = json.loads((output / 'manifest.json').read_text())
    arrays = np.load(output / 'index.npz', allow_pickle=False)
    pages = {p['page_id']: p for p in manifest['pages']}
    lines = ['# 五个可回查案例', '', '以下保留全部预设问题。分数仅用于同一路径内排序，不跨模型比较绝对值。文本片段来自每个指定目标页得分最高的块；完整原文、OCR 与 TSV 均保留。']
    records = []
    for i, row in enumerate(result['results']):
        target = row['target_page_id']
        lines += ['', '## ' + row['query_id'], '', row['query'], '',
                  f"指定证据页：[{target}]({pages[target]['image_path']})", '',
                  '| 路径 | 第一名 | 第二名 | 第三名 | 指定页名次 |', '|---|---|---|---|---:|']
        record = {'query_id': row['query_id'], 'target_page_id': target, 'top3': {}, 'target_chunks': {}}
        for source, label in [('visual', '视觉'), ('native_text', '原生文本'), ('ocr_text', 'OCR')]:
            entries = [f"{x['page_id']} ({x['score']:.4f})" for x in row[source][:3]]
            lines += [f"| {label} | " + ' | '.join(entries) + f" | {row[source + '_rank']} |"]
            record['top3'][source] = row[source][:3]
        for source, key, label in [('native_text', 'native_text_path', '原生文本'),
                                   ('ocr_text', 'ocr_text_path', 'OCR')]:
            scores = arrays['text_queries'][i] @ arrays[source + '_vectors'].T
            candidates = [j for j,c in enumerate(chunks[source]['chunks']) if c['page_id'] == target]
            best = max(candidates, key=lambda j: float(scores[j]))
            chunk = chunks[source]['chunks'][best]
            preview = ' '.join(chunk['text_preview'].split())[:350]
            record['target_chunks'][source] = {'chunk_index': best, 'start': chunk['start'], 'end': chunk['end'], 'score': float(scores[best])}
            lines += ['', f"{label}目标页最高分块：tokens [{chunk['start']}, {chunk['end']})，分数 {scores[best]:.4f}。[完整文本]({pages[target][key]})", '', '> ' + preview]
        records.append(record)
    (output / 'cases.md').write_text('\n'.join(lines) + '\n')
    (output / 'cases.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', nargs='?', type=Path, default=HERE / 'results/v0.1')
    main(parser.parse_args().output.resolve())

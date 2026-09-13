"""No-model probes of pinned upstream functions; no training or platform launch."""
import ast
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace


def deepnote(checkout):
    path = checkout / 'src/main.py'
    tree = ast.parse(path.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'retrieve_note')
    # Execute only the reviewed control function; never import upstream CLI/API setup.
    module = ast.Module(body=[function], type_ignores=[])
    probes = []
    for probe_id, votes, expected in [('cumulative_failures', [False, True, False], 'note-2'),
                                      ('keep_initial_on_failure', [False, False], 'note-0')]:
        calls, round_no = [], [0]
        def retrieve(*args, **kwargs):
            calls.append(kwargs['query'])
            return [f'evidence-{len(calls)}']
        def refine(*args):
            round_no[0] += 1
            return f'note-{round_no[0]}'
        outcomes = iter(votes)
        env = dict(args=SimpleNamespace(dataset='fixture', max_step=9, max_top_k=99, max_fail_step=2),
                   retrieve=retrieve, retrieve_method='emb', get_context=lambda refs: '\n'.join(refs),
                   init_note=lambda *a: 'note-0', gen_new_query=lambda *a: 'followup',
                   refine_note=refine, compare_note=lambda *a: next(outcomes), gen_answer=lambda q, note: note)
        exec(compile(module, str(path), 'exec'), env)
        result = env['retrieve_note']('fixture', 'question', 'unused-reference', top_k=1)
        if result['deepnote'] != expected or len(result['query_log']) != len(votes):
            raise ValueError('Unexpected upstream control behavior')
        probes.append(dict(probe_id=probe_id, comparison_results=votes, final_note=result['deepnote'],
                           refinement_rounds=len(result['query_log']), retrieval_calls=len(calls), passed=True))
    return dict(probes=probes, execution='upstream AST control function with deterministic stub retrieval/model calls',
                model_calls=0, interpretation='Control-flow checks only; no note quality or QA claim')


def pilotdeck(checkout):
    script = Path(__file__).with_name('pilotdeck_probe.mjs')
    process = subprocess.run(['node', str(script), str(checkout)], check=True, text=True, capture_output=True)
    return json.loads(process.stdout)

"""Version 2 synthetic corpus; subject-separated development/test queries."""
import random

RELATIONS = [
 ('editor', ['Neovim','Emacs','VS Code','Sublime Text'], 'uses {v} for editing code', ['Which code editor does {s} use now?', 'What is {s}\'s current editor?', 'Find the latest code-editing tool for {s}.', 'Which application does {s} currently edit code with?']),
 ('city', ['Oslo','Kyoto','Lisbon','Perth'], 'lives in {v}', ['Where does {s} live now?', 'What is {s}\'s current city?', 'Find the latest residence city for {s}.', 'In which city is {s} currently living?']),
 ('language', ['Python','Rust','Java','Julia'], 'uses {v} for programming', ['Which programming language does {s} use now?', 'What is {s}\'s current coding language?', 'Find the latest programming language for {s}.', 'Which language does {s} currently write software in?']),
 ('transport', ['a bicycle','a train','a bus','a scooter'], 'commutes using {v}', ['How does {s} commute now?', 'What is {s}\'s current mode of transport to work?', 'Find the latest commuting method for {s}.', 'How does {s} currently travel to work?']),
 ('drink', ['green tea','coffee','orange juice','sparkling water'], 'prefers {v} as a drink', ['What does {s} prefer to drink now?', 'What is {s}\'s current favorite beverage?', 'Find the latest drink preference for {s}.', 'Which beverage does {s} currently favor?']),
 ('project', ['Atlas','Beacon','Cedar','Delta'], 'works on project {v}', ['Which project does {s} work on now?', 'What is {s}\'s current project?', 'Find the latest project assignment for {s}.', 'Which project is {s} currently assigned to?']),
]


def generate(size, seed, scenario):
    if size < 100 or scenario not in ('old','balanced'):
        raise ValueError('size >= 100 and scenario old/balanced required')
    rng = random.Random(seed)
    records, queries = [], []
    for i in range(24):
        relation, values, statement, templates = RELATIONS[i % 6]
        subject = f'Person{i:03d}'
        current, previous = rng.sample(values,2)
        # Stratify target ages; all scenario variants share document text/vectors.
        event_order = (i+1)/26 if scenario=='balanced' else .02+(i/24)*.08
        family = f'{subject}:{relation}'
        split = 'dev' if i in {0, 7, 14, 21, 4, 11} else 'test'
        base = dict(subject=subject,relation=relation,importance=rng.random(),source='synthetic',split=split)
        records.append(dict(base,memory_id=f'old-{i}',canonical_id=f'old-{i}',content=f'Previously, {subject} '+statement.format(v=previous)+'.',event_order=event_order-.015,supersedes_id=None))
        records.append(dict(base,memory_id=f'current-{i}',canonical_id=f'current-{i}',content=f'Currently, {subject} '+statement.format(v=current)+'.',event_order=event_order,supersedes_id=f'old-{i}'))
        if i%2==0:
            records.append(dict(base,memory_id=f'duplicate-{i}',canonical_id=f'current-{i}',content=f'Currently, {subject} '+statement.format(v=current)+'.',event_order=event_order+.001,supersedes_id=None))
        for variant, template in enumerate(templates):
            queries.append(dict(query_id=f'{family}:{variant}',family=family,split=split,query=template.format(s=subject),
                                target_memory_id=f'current-{i}',target_canonical_id=f'current-{i}',superseded_memory_id=f'old-{i}'))
    for i in range(size-len(records)):
        relation, values, statement, _ = RELATIONS[i%6]
        subject = f'Person{i+24:05d}'
        value=rng.choice(values)
        content = (f'Currently, {subject} '+statement.format(v=value)+'.' if i%4 else f'{subject} saw birds in a garden on a sunny afternoon.')
        records.append(dict(memory_id=f'distractor-{i}',canonical_id=f'distractor-{i}',content=content,subject=subject,relation=relation,event_order=rng.random(),importance=rng.random(),supersedes_id=None,source='synthetic',split='distractor'))
    return records, queries

"""Query-independent whole-record storage. No query/truth input is accepted."""
import hashlib
import re
RECORD = re.compile(r'Record ([A-Z]{10}): ([1-9][0-9]{6})\Z')
HEADER = 'Records (key=number):\n'

def parse_record(record):
    match = RECORD.fullmatch(record)
    if not match: raise ValueError('Unexpected source record grammar')
    return match.groups()

def serialize(records, indices, compact=False):
    selected = sorted(indices)
    if len(selected) != len(set(selected)): raise ValueError('Duplicate indices')
    if any(i < 0 or i >= len(records) for i in selected): raise ValueError('Invalid index')
    if compact: return HEADER + '\n'.join('='.join(parse_record(records[i])) for i in selected)
    return '\n'.join(records[i] for i in selected)

def decode_compact(memory):
    if not memory.startswith(HEADER): raise ValueError('Missing schema header')
    records=[]
    for line in memory[len(HEADER):].splitlines():
        if not re.fullmatch(r'[A-Z]{10}=[1-9][0-9]{6}',line): raise ValueError('Invalid compact record')
        key,value=line.split('=');records.append(f'Record {key}: {value}')
    return records

def rank_records(records, source_id, seed):
    for record in records: parse_record(record)
    return sorted(range(len(records)),key=lambda i:hashlib.sha256(f'{seed}|{source_id}|{records[i]}'.encode()).hexdigest())

def pack(records, source_id, count_empty_template, budget, query_reserve, retention_seed, compact=False):
    """Callback receives storage text only; caller ALWAYS uses an empty question."""
    if budget<=query_reserve or query_reserve<0: raise ValueError('Invalid budget')
    selected=[]
    for index in rank_records(records,source_id,retention_seed):
        trial=selected+[index]
        if count_empty_template(serialize(records,trial,compact))+query_reserve<=budget: selected=trial
    selected.sort();memory=serialize(records,selected,compact)
    if count_empty_template(memory)+query_reserve>budget: raise ValueError('Header does not fit')
    return memory,selected

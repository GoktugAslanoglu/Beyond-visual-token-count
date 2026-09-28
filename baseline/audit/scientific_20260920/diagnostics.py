"""Post-unblinding scientific diagnostics; no new confirmatory hypotheses."""
import collections,hashlib,io,json,pathlib,sys,zipfile
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from tokenizers import Tokenizer
from scipy.stats import binomtest
ROOT=pathlib.Path(__file__).resolve().parents[3];OUT=pathlib.Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))
from iclr.stage04c_identifier_amended_20260913.identifier import validate
from iclr.ruler_cpu5_20260917.upstream.eval.synthetic.constants import string_match_all
from preflight import read

def digest(b):return hashlib.sha256(b).hexdigest()
def put(n,v):(OUT/n).write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def meta_check(memory,geometry):
    pages=geometry['source_partition'];cursor=0
    for p in pages:
        assert p['source_start']==cursor
        for l in p['lines']:
            assert l['start']==cursor and memory[l['start']:l['end']].removesuffix('\n')==l['text']
            b=l['bbox'];assert b[0]>=24 and b[1]>=24 and b[2]<=p['width']-24 and b[3]<=p['height']-24
            cursor=l['end']
        assert p['source_end']==cursor
    assert cursor==len(memory)
    # Bounding rectangle is geometry, not percentage of dark ink pixels.
    widths=[(max(l['bbox'][2] for l in p['lines'])-min(l['bbox'][0] for l in p['lines']))/p['width'] for p in pages]
    return widths
def rerender(p,base_side,final_side,font,actual):
    im=Image.new('RGB',(base_side,base_side),'white');draw=ImageDraw.Draw(im)
    for l in p['lines']:draw.text((l['x'],l['baseline_y']),l['text'],fill='black',font=font,anchor='ls')
    im=im.resize((final_side,final_side),Image.Resampling.LANCZOS)
    with Image.open(io.BytesIO(actual)) as old: equal=im.tobytes()==old.convert('RGB').tobytes()
    return equal

if __name__=='__main__':
    stats=read(OUT/'ANALYSIS.json');rows=[json.loads(s) for s in (OUT/'scored_rows.jsonl').read_text(encoding='utf-8').splitlines()]
    for h in stats['hypotheses']:
        if h['name']=='H3':assert abs(binomtest(h['positive'],h['positive']+h['negative'],.5,alternative='greater').pvalue-h['p_value'])<1e-35
    for reader in ['Qwen2B','Qwen9B','GLM']:
        for arm,a in stats['RULER'][reader]['arms'].items():
            for task,v in a['tasks'].items():
                subset=[r for r in rows if r['study']=='RULER' and r['reader']==reader and r['condition']==arm and r['task_id']==task]
                assert string_match_all([r['prediction'] for r in subset],[r['reference']['answers'] for r in subset])==v['native_score_percent']
    tokenizer=Tokenizer.from_file(str(ROOT/'iclr/stage04c_identifier_amended_20260913/tokenizer/tokenizer.json'))
    cases={}
    for p in (ROOT/'iclr/pre_gpu_cpu_20260913/identifier_checkpoint/inputs/cases').glob('*.candidate.json'):
        c=read(p);validate(c,lambda text:len(tokenizer.encode(text,add_special_tokens=False).ids));cases[c['id']]=c
    font=ImageFont.truetype(str(ROOT/'iclr/ruler_cpu5_20260917/assets/DejaVuSansMono.ttf'),12)
    layouts=[];image_samples=[];failures=[]
    for label,folder in [('Qwen2B','identifier_gpu_20260916'),('Qwen9B','identifier_qwen9b_20260917'),('GLM','identifier_glm_20260917')]:
        m=read(ROOT/'iclr'/folder/'RUN_MANIFEST.json')
        for r in m['rows']:
            req=read(ROOT/r['request']['path']);c=cases[r['item_id']]
            assert (req['reader'],req['item_id'],req['arm'])==(r['model_id'],r['item_id'],r['condition'])
            if r['condition']=='full_raw':continue
            g=req['geometry'];widths=meta_check(c['memory'],g)
            layouts.append(dict(study='Identifier',reader=label,condition=r['condition'],item=r['item_id'],glyph_min=min(p['g_eff_processor_y'] for p in g['pages']),glyph_max=max(p['g_eff_processor_y'] for p in g['pages']),max_text_width_fraction=max(widths)))
            if r['item_id'] in ['identifier-000','identifier-048','identifier-095']:
                pi=next(i for i,p in enumerate(g['source_partition']) if p['source_start']<=c['target_char_offset']<p['source_end'])
                p=g['source_partition'][pi];actual=(ROOT/r['request']['path']).parent/req['images'][pi]
                equal=rerender(p,g['base_side'],g['final_side'],font,actual.read_bytes())
                image_samples.append(dict(study='Identifier',reader=label,item=r['item_id'],condition=r['condition'],page=pi,pixels_equal=equal))
    print('Identifier geometry checked; deterministic target-page rerenders done',flush=True)
    with zipfile.ZipFile(ROOT/'iclr/ruler_cpu5_20260917/ICLR-RULER-Merged-Checkpoint-A-E.zip') as z:
        rc={}
        for name in z.namelist():
            if name.startswith('generation/') and name.endswith('/CASES.jsonl'):
                for c in map(json.loads,z.read(name).decode().splitlines()):rc[c['item_id']]=c
        for label,mkey in [('Qwen2B','qwen2b'),('Qwen9B','qwen9b'),('GLM','glm')]:
            m=read(ROOT/f'iclr/ruler_gpu_20260919/RUN_MANIFEST_{mkey}.json')
            for r in m['rows']:
                req=json.loads(z.read(r['request']['path']));c=rc[r['item_id']]
                assert (req['reader'],req['item_id'],req['arm'])==(r['model_id'],r['item_id'],r['condition'])
                assert req['source_sha256']==c['memory_sha256'] and req['native_prompt_sha256']==c['native_prompt_sha256']
                prefix=str(pathlib.PurePosixPath(r['request']['path']).parent)
                messages=json.loads(z.read(prefix+'/'+req['messages']));content=messages[0]['content']
                if r['condition']=='full_raw':assert content==[dict(type='text',text=c['prompt_prefix']+c['memory']+c['prompt_suffix'])];continue
                assert content[0]==dict(type='text',text=c['prompt_prefix']) and content[-1]==dict(type='text',text=c['prompt_suffix'])
                assert [v['image'] for v in content[1:-1]]==req['images']
                g=req['geometry'];widths=meta_check(c['memory'],g)
                layouts.append(dict(study='RULER',reader=label,condition=r['condition'],item=r['item_id'],glyph_min=min(p['g_eff_processor_y'] for p in g['pages']),glyph_max=max(p['g_eff_processor_y'] for p in g['pages']),max_text_width_fraction=max(widths)))
                if r['item_id'].endswith('-000'):
                    p=g['source_partition'][0];equal=rerender(p,g['base_side'],g['final_side'],font,z.read(prefix+'/'+req['images'][0]))
                    image_samples.append(dict(study='RULER',reader=label,item=r['item_id'],condition=r['condition'],page=0,pixels_equal=equal))
    summary=[]
    for study,reader,arm in sorted({(r['study'],r['reader'],r['condition']) for r in layouts}):
        rr=[r for r in layouts if (r['study'],r['reader'],r['condition'])==(study,reader,arm)]
        summary.append(dict(study=study,reader=reader,condition=arm,n=len(rr),glyph_range=[min(r['glyph_min'] for r in rr),max(r['glyph_max'] for r in rr)],median_max_text_width_fraction=float(np.median([r['max_text_width_fraction'] for r in rr]))))
    put('GEOMETRY_AND_METHOD_DIAGNOSTICS.json',dict(status='passed' if all(r['pixels_equal'] for r in image_samples) else 'review_required',
        complete_source_coverage_and_bbox_checks=len(layouts),identifier_source_cases_revalidated=96,
        independent_ruler_metric_cells=72,independent_identifier_sign_tests=3,
        layout_summary=summary,image_samples=image_samples,pixel_exact_rerenders=sum(r['pixels_equal'] for r in image_samples),
        interpretation='Post-unblinding diagnostics, not new confirmatory tests. Max text width is a bounding-box ratio, not ink coverage. Tiny glyphs and narrow-column square rendering limit generalization of identifier floor effects.'))
    print('Geometry rows',len(layouts),'pixel-exact rerenders',sum(r['pixels_equal'] for r in image_samples),'/',len(image_samples),flush=True)

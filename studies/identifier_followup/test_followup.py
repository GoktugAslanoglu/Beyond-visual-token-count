"""Local CPU tests; synthetic fixtures never count as experiment outcomes."""
import importlib,json,pathlib,sys,types
import pytest
import core

@pytest.mark.parametrize('split,n',[('dev',12),('eval',48)])
def test_schedule_balance(split,n):
 rows=core.schedule(split);assert len(rows)==n
 for key in ['length','alphabet','entropy']:
  vals={r[key] for r in rows};assert len(vals)==2
  assert all(sum(r[key]==v for r in rows)==n//2 for v in vals)
 assert all(sum(r['position']==v for r in rows)==n//3 for v in ['early','middle','late'])
 assert all(r['distractors']==4 for r in rows)

@pytest.mark.parametrize('layout',['original','L1_fullwidth_charwrap','L2_twocolumn_wordwrap','L3_fullwidth_wordwrap'])
@pytest.mark.parametrize('case_id',['followup-dev-000','followup-dev-007','followup-eval-047'])
def test_fresh_source_coverage_and_bounds(layout,case_id):
 split='dev' if '-dev-' in case_id else 'eval';case=core.read(core.D/'cases'/split/(case_id+'.json'));p=core.plan(case['memory'],layout)
 lines=[l for page in p['pages'] for l in page['lines']];assert len(p['pages'])==4
 assert ''.join(case['memory'][l['start']:l['end']] for l in lines)==case['memory']
 assert p['source_sha256']==core.digest(case['memory'].encode())
 for l in lines:assert l['bbox'][0]>=24 and l['bbox'][1]>=24 and l['bbox'][2]<=p['base_side']-24+1e-6 and l['bbox'][3]<=p['base_side']-24
 if layout!='original':assert ''.join(l['text'] for l in lines)==case['memory'].replace('\n',' ')

def test_renderer_does_not_accept_answer_metadata():
 import inspect
 assert list(inspect.signature(core.plan).parameters)==['text','layout_id']
 text='Record ABCDEFGHIJ: 12345678\n'+'Neutral line stays here.\n'*100
 p=core.plan(text,'L3_fullwidth_wordwrap');a=core.render(p,1008);b=core.render(p,1008)
 assert all(x.tobytes()==y.tobytes() for x,y in zip(a,b))
 for im in a+b:im.close()

def test_hash_tampering_and_path_escape_rejected(tmp_path):
 (tmp_path/'x').write_bytes(b'one');refs=core.package_files(tmp_path);core.verify_files(tmp_path,refs);(tmp_path/'x').write_bytes(b'two')
 with pytest.raises(ValueError):core.verify_files(tmp_path,refs)
 with pytest.raises((ValueError,FileNotFoundError)):core.verify_files(tmp_path,[{'path':'../escape','bytes':0,'sha256':'0'}])

def test_canonical_scorer_agreement():
 from audit_results import canonical
 from vendor.scoring import score
 for answer,pred in [('abc','abc'),('abc',' abc\n'),('abc','**abc**'),('abc','<|begin_of_box|>abc<|end_of_box|>'),('a b','a\n b')]:
  assert (canonical(pred)==' '.join(answer.split()))==bool(score(pred,answer,'controlled')['canonical']['exact_match'])

def test_full_dev_preparation_with_explicitly_synthetic_processor(tmp_path,monkeypatch):
 import torch
 import prepare
 from PIL import Image
 # Exercise request-count, tensor accounting, geometry and freeze plumbing only.
 # This is not a native model-processor or GPU readiness test.
 class Tokenizer:
  model_max_length=262144
  def encode(self,text,**kw):return [7]*8192
 class IP:
  merge_size=2;patch_size=16
  def __call__(self,images,**kw):
   grids=[[1,2*max(1,round(im.height/32)),2*max(1,round(im.width/32))] for im in images]
   return {'image_grid_thw':torch.tensor(grids,dtype=torch.int64)}
 class Processor:
  tokenizer=Tokenizer();image_processor=IP()
  def apply_chat_template(self,messages,**kw):return 'Synthetic test chat'
  def __call__(self,text,images,**kw):
   g=self.image_processor(images)['image_grid_thw'];n=sum(int(x.prod())//4 for x in g);ids=torch.tensor([[1]+[99]*n+[2]],dtype=torch.int64)
   return {'input_ids':ids,'attention_mask':torch.ones_like(ids),'image_grid_thw':g,'pixel_values':torch.tensor([[float(im.getpixel((24,24))[0])] for im in images])}
 fake=types.SimpleNamespace(__version__='5.3.0',AutoProcessor=types.SimpleNamespace(from_pretrained=lambda *a,**k:Processor()))
 monkeypatch.setitem(sys.modules,'transformers',fake);monkeypatch.setattr(prepare,'D',tmp_path)
 for n in ['environment','cases/dev']:(tmp_path/n).mkdir(parents=True)
 protocol=core.read(core.D/'PROTOCOL.json');(tmp_path/'PROTOCOL.json').write_text(json.dumps(protocol));(tmp_path/'DEV_FREEZE.json').write_text(json.dumps({'files':[]}));(tmp_path/'environment/ASSET_PINS.json').write_text('[]')
 asset=tmp_path/'assets/Qwen--Qwen3.5-2B';asset.mkdir(parents=True);(asset/'config.json').write_text(json.dumps({'image_token_id':99,'text_config':{'max_position_embeddings':262144}}))
 for i in range(12):(tmp_path/'cases/dev'/f'{i:03}.json').write_text(json.dumps({'id':f'synthetic-{i:03}','memory':'Record ABCDEFGHIJ: 12345678\n'+'Neutral line.\n'*100,'question':'Return the identifier.'}))
 prepare.main('dev',tmp_path/'assets',tmp_path/'output');f=core.read(tmp_path/'output/INPUT_FREEZE.json');assert f['expected_calls']==36 and len(f['rows'])==36;core.verify_files(tmp_path/'output',f['files'])
 import release_inputs
 monkeypatch.setattr(release_inputs,'D',tmp_path)
 release_inputs.validate(tmp_path/'output')
 (tmp_path/'output'/f['rows'][0]['path']/'REQUEST.json').write_text('{}')
 with pytest.raises(ValueError):core.verify_files(tmp_path/'output',f['files'])


def test_cap_reconstruction_keeps_uncapped_rows_and_reports_prefix_mismatch(tmp_path,monkeypatch):
 import analyze_cap
 baseline=[];rows=[]
 for reader,n in [('Qwen2B',126),('Qwen9B',121)]:
  for i in range(500):
   baseline.append(dict(reader=reader,item_id=f'c{i}',reference='alpha',cluster=f'conv-{i%10}',category=1,prediction='wrong',score={'canonical':{'f1':0.0}}))
  for i in range(n):
   folder=tmp_path/reader/f'c{i}';folder.mkdir(parents=True);core.put(folder/'ORIGINAL.json',{'generated_token_ids':[1]*96})
   rows.append(dict(reader=reader,case_id=f'c{i}',path=folder.relative_to(tmp_path).as_posix(),prediction='alpha',generated_token_ids=[2]*97,cap_hit=False))
 core.put(tmp_path/'BASELINE.json',baseline);monkeypatch.setattr(analyze_cap,'verify',lambda *a:rows)
 analyze_cap.analyze(tmp_path,[],tmp_path/'result');r=core.read(tmp_path/'result/cap_analysis.json')['readers']
 assert r['Qwen2B']['full_500_conversation_macro_sensitivity']==pytest.approx(126/500)
 assert r['Qwen9B']['full_500_conversation_macro_sensitivity']==pytest.approx(121/500)
 assert r['Qwen2B']['prefix96_mismatches']==126

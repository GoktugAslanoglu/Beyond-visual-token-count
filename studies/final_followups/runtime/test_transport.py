import pathlib,sys,zipfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import pytest
from transport import extract_new
def test_transport_rejects_escape_and_duplicates(tmp_path):
 for index,names in enumerate([['../outside'],['a','a'],['C:/bad'],['folder\\evil']]):
  path=tmp_path/f'{index}.zip'
  with zipfile.ZipFile(path,'w') as z:
   for n in names:
    info=zipfile.ZipInfo('fixture');info.filename=n;z.writestr(info,'fixture')
  with pytest.raises(ValueError):extract_new(path,tmp_path/f'out{index}')
def test_transport_valid_archive(tmp_path):
 path=tmp_path/'good.zip'
 with zipfile.ZipFile(path,'w') as z:z.writestr('prepared/data.json','{}')
 extract_new(path,tmp_path/'out')
 assert (tmp_path/'out/prepared/data.json').read_text()=='{}'

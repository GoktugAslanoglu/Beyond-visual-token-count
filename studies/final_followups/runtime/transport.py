"""Strict archive transport for the new final round."""
import pathlib,zipfile,stat
def extract_new(archive,destination):
 destination=pathlib.Path(destination);destination.mkdir(parents=True,exist_ok=False);root=destination.resolve()
 with zipfile.ZipFile(archive) as z:
  names=z.namelist()
  if len(names)!=len(set(names)) or len(names)>50000 or sum(i.file_size for i in z.infolist())>8*1024**3:raise ValueError('Invalid archive inventory')
  for i in z.infolist():
   rel=pathlib.PurePosixPath(i.filename)
   if rel.is_absolute() or '..' in rel.parts or ':' in i.filename or '\\' in i.orig_filename or stat.S_ISLNK(i.external_attr>>16):raise ValueError('Unsafe archive path')
   p=(root/pathlib.Path(*rel.parts)).resolve()
   if not p.is_relative_to(root):raise ValueError('Archive escaped destination')
  z.extractall(root)

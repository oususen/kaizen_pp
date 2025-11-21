from pathlib import Path 
import re 
p=Path('proposals/models.py') 
text=p.read_text(encoding='utf-8') 
''' 
''' 
if needle not in text: 
    raise SystemExit('needle not found') 
text=text.replace(needle, insert) 
p.write_text(text, encoding='utf-8') 

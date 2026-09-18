"""Recover the verified completed attempt whose supervising tool timed out."""
from pathlib import Path
import hashlib, json, shutil
from launch import ROOT, validate

def main():
    stage = ROOT/"product"
    attempt = stage/"attempts/1788696670313304330"
    inp = stage/"product.inp"; out = stage/"product.out"
    assert inp.read_bytes() == (attempt/inp.name).read_bytes()
    energy = validate(out.read_text(),inp.read_text())
    for name,suffix in [("PUNCH",".dat"),("IRCDATA",".irc")]:
        source = attempt/name
        if source.exists(): shutil.copy2(source,inp.with_suffix(suffix))
    status = dict(sha256=hashlib.sha256(inp.read_bytes()).hexdigest(),output_sha256=hashlib.sha256(out.read_bytes()).hexdigest(),success=True,energy_hartree=energy,np=8,threads_per_rank=1,attempt=str(attempt.relative_to(ROOT)),recovered=True)
    inp.with_suffix(".json").write_text(json.dumps(status,indent=2)+"\n")
    (attempt/"status.json").write_text(json.dumps(status,indent=2)+"\n")
    shutil.copy2(out,attempt/out.name)
    print(status)

if __name__ == "__main__": main()

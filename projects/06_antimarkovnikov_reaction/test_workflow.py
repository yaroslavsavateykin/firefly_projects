"""Run with python3 test_workflow.py; no external test framework."""
import hashlib, importlib, tempfile
from pathlib import Path
import generate
from launch import validate
from workflow import hess_test, hess_parse, hess_format, output_geometry, parse_energy
import re

def main():
    paths = list(generate.ROOT.glob("*/*.inp"))
    before = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    importlib.reload(generate)
    assert before == {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    geometry = generate.reference_geometry()
    text = generate.replace_geometry(generate.REF.read_text(),geometry,"test","ENERGY")
    again = generate.replace_geometry(text,geometry,"test","ENERGY")
    assert text == again
    assert "\n $DATA\n" in text
    assert all(len(line) <= 80 for line in text.splitlines())
    for option in ["UNITS=ANGS","D5=.T.","ICUT=13","ITOL=30"]:
        assert option in text
    data = text.split("$DATA")[1].split("$END")[0]
    assert len(data.strip().split("\n\n")) == 11
    good = "TOTAL ENERGY = -2.5\nEXECUTION OF FIREFLY TERMINATED NORMALLY"
    assert validate(good,text) == -2.5
    for bad,inp in [(good+"\nTERMINATED ABNORMALLY",text),(good,text.replace("RUNTYP=ENERGY","RUNTYP=OPTIMIZE")),("TOTAL ENERGY = -2.5",text)]:
        try: validate(bad,inp)
        except ValueError: pass
        else: raise AssertionError("false success")
    for name in ["product","mark_product"]:
        path = generate.ROOT/name/(name+".out")
        assert parse_energy(path) < -218
        assert len(output_geometry(path)) == 11
    hess_test()
    native = (generate.ROOT/"ts_hessian/ts_hessian.dat").read_text(errors="replace")
    matrix = hess_parse(re.findall(r"\$HESS\b(.*?)\$END",native,re.S)[-1],33)
    assert hess_parse(hess_format(matrix),33) == matrix
    try: hess_parse(hess_format(matrix).splitlines()[0],33)
    except ValueError: pass
    else: raise AssertionError("truncated Hessian accepted")
    assert validate(good+"\nSADDLE POINT LOCATED",text.replace("RUNTYP=ENERGY","RUNTYP=SADPOINT")) == -2.5
    for name in ["irc_forward","irc_reverse"]:
        assert parse_energy(generate.ROOT/name/(name+".out")) < -218
    try: parse_energy(generate.ROOT/"mark_saddle/mark_saddle.out")
    except ValueError: pass
    else: raise AssertionError("unconverged Markovnikov saddle accepted")
    print("generation, import safety, convergence, geometry and Hessian checks passed")

if __name__ == "__main__": main()

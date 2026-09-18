#!/usr/bin/env python3
"""Fresh scan-peak Hessians and saddle searches; never reuse the old 05 saddle."""
import argparse, re, subprocess
from generate import ROOT, write_input
from workflow import xyz_read, parse_energy, output_geometry

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("stage",choices=["hessian","saddle","ts-hessian","irc-forward","irc-reverse","endpoint-forward","endpoint-reverse"])
    parser.add_argument("--mark",action="store_true")
    args = parser.parse_args()
    prefix = "mark_" if args.mark else ""
    peak = (ROOT/(prefix+"scan_peak.txt")).read_text().split()[0]
    parse_energy(ROOT/peak/(peak+".out"))
    geometry = xyz_read(ROOT/peak/(peak+".xyz"))
    if args.stage == "hessian":
        name = prefix+"peak_hessian"
        write_input(ROOT/name,name,geometry,"HESSIAN"," $FORCE NVIB=2 $END\n")
    elif args.stage == "saddle":
        source = prefix+"peak_hessian"
        parse_energy(ROOT/source/(source+".out"))
        punch = (ROOT/source/(source+".dat")).read_text(errors="replace")
        hess = re.findall(r"\$HESS\b.*?\$END",punch,re.S)
        if not hess: raise ValueError("missing native punch Hessian")
        name = prefix+"saddle"
        write_input(ROOT/name,name,geometry,"SADPOINT",
                    " $STATPT METHOD=QA OPTTOL=1D-5 NSTEP=200 HESS=READ\n  UPHESS=POWELL IFOLOW=1 $END\n")
        path = ROOT/name/(name+".inp")
        path.write_text(path.read_text()+"\n "+hess[-1]+"\n")
    elif args.stage == "ts-hessian":
        source = prefix+"saddle"
        parse_energy(ROOT/source/(source+".out"))
        name = prefix+"ts_hessian"
        write_input(ROOT/name,name,output_geometry(ROOT/source/(source+".out")),"HESSIAN"," $FORCE NVIB=2 $END\n")
    elif args.stage.startswith("endpoint-"):
        source = prefix+args.stage.replace("endpoint-","irc_")
        parse_energy(ROOT/source/(source+".out"))
        name = prefix+args.stage.replace("-","_")
        write_input(ROOT/name,name,output_geometry(ROOT/source/(source+".out")),"OPTIMIZE"," $STATPT METHOD=QA OPTTOL=1D-5 NSTEP=200 $END\n")
    else:
        source = prefix+"ts_hessian"
        parse_energy(ROOT/source/(source+".out"))
        text = (ROOT/source/(source+".out")).read_text()
        imaginary = re.findall(r"(\d+\.\d+)\s+I\b", "\n".join(line for line in text.splitlines() if "FREQUENCY:" in line))
        if len(imaginary) != 1: raise ValueError("IRC requires exactly one imaginary mode")
        saddle = prefix+"saddle"
        geometry = output_geometry(ROOT/saddle/(saddle+".out"))
        hess = re.findall(r"\$HESS\b.*?\$END",(ROOT/source/(source+".dat")).read_text(errors="replace"),re.S)[-1]
        name = prefix+args.stage.replace("-","_")
        direction = ".T." if args.stage == "irc-forward" else ".F."
        write_input(ROOT/name,name,geometry,"IRC",f" $IRC FORWRD={direction} MXOPT=100 NPOINT=10\n  PACE=GS2 SADDLE=.T. $END\n")
        path = ROOT/name/(name+".inp")
        path.write_text(path.read_text()+"\n "+hess+"\n")
    subprocess.run(["python3",str(ROOT/"launch.py"),str(ROOT/name/(name+".inp"))],check=True)

if __name__ == "__main__": main()

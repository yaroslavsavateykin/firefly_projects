#!/usr/bin/env python3
"""Isolated, serial, content-addressed Firefly attempts with retained punch files."""
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import signal

ROOT = Path(__file__).resolve().parent

def validate(text, inp):
    if "EXECUTION OF FIREFLY TERMINATED NORMALLY" not in text or re.search(
        r"TERMINATED ABNORMALLY|SCF IS UNCONVERGED|SCF HAS NOT CONVERGED|FAILURE TO LOCATE|TOO MANY STEPS|FATAL ERROR", text):
        raise ValueError("abnormal, incomplete, or unconverged output")
    energies = re.findall(r"TOTAL ENERGY\s*=\s*(-?\d+\.\d+(?:[DE][+-]?\d+)?)", text)
    if not energies:
        raise ValueError("missing converged energy")
    runtyp = re.search(r"RUNTYP=(\w+)", inp).group(1)
    marker = {"OPTIMIZE":"EQUILIBRIUM GEOMETRY LOCATED","SADPOINT":"SADDLE POINT LOCATED"}.get(runtyp)
    if marker and marker not in text:
        raise ValueError("stationary point not converged")
    if runtyp == "HESSIAN" and "FREQUENCY:" not in text:
        raise ValueError("missing vibrational analysis")
    if runtyp == "IRC":
        requested = int(re.search(r"NPOINT=(\d+)",inp).group(1))
        points = [int(x) for x in re.findall(r"POINT\s+(\d+) ON THE REACTION PATH",text)]
        if points != list(range(1,requested+1)):
            raise ValueError("IRC did not complete all requested path points")
    return float(energies[-1].replace("D","E"))

def main():
    np = int(os.environ.get("NP", "8"))
    if not 1 <= np <= 8:
        raise ValueError("NP must be 1..8")
    inp = Path(sys.argv[1]).resolve(strict=True)
    if inp.suffix != ".inp" or not inp.is_relative_to(ROOT):
        raise ValueError("input must be an .inp inside project 06")
    ff = Path(os.environ.get("FF", ROOT.parent.parent/"shared/firefly/8.2.0/firefly820")).resolve()
    ext = Path(os.environ.get("EX", ff.parent)).resolve()
    if not os.access(ff, os.X_OK) or not ext.is_dir():
        raise ValueError("Firefly executable/extensions unavailable")
    with (ROOT/".calculation.lock").open("w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        source = inp.read_bytes(); text = source.decode()
        if not re.search(r"^ +\$DATA", text, re.M) or "$SMP NP=1 MKLNP=1 TPOOL=1 $END" not in text:
            raise ValueError("missing safe DATA/SMP controls; regenerate input")
        digest = hashlib.sha256(source).hexdigest()
        out = inp.with_suffix(".out"); state = inp.with_suffix(".json")
        if out.exists() and state.exists():
            prior = json.loads(state.read_text())
            if prior.get("sha256") == digest and (prior.get("success") or prior.get("returncode") == 0) and prior.get("output_sha256") == hashlib.sha256(out.read_bytes()).hexdigest():
                try:
                    energy = validate(out.read_text(errors="replace"), text)
                except ValueError:
                    pass
                else:
                    prior.update(success=True,energy_hartree=energy)
                    state.write_text(json.dumps(prior,indent=2)+"\n")
                    print("RESUME", inp.name, flush=True); return
        attempts = inp.parent/"attempts"; attempts.mkdir(exist_ok=True)
        attempt = attempts/str(time.time_ns()); attempt.mkdir()
        for suffix in (".out", ".dat", ".irc", ".json"):
            old = inp.with_suffix(suffix)
            if old.exists():
                shutil.copy2(old, attempt/("previous"+suffix))
                old.unlink()
        (attempt/inp.name).write_bytes(source)
        env = dict(os.environ, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", OMPXNUM_THREADS="1")
        status = {"sha256":digest,"np":np,"threads_per_rank":1,"success":False,"attempt":str(attempt.relative_to(ROOT))}
        state.write_text(json.dumps(status,indent=2)+"\n")
        print("RUN", inp.name, "ranks", np, flush=True)
        try:
            with tempfile.TemporaryDirectory(prefix="firefly06_") as tmp:
                scratch = Path(tmp)
                procgrp = attempt/"procgrp"; procgrp.write_text(f"local {np-1}\n")
                env.update(PUNCH=str(attempt/"PUNCH"), IRCDATA=str(attempt/"IRCDATA"))
                cpus = sorted(os.sched_getaffinity(0))[:np]
                command = ["taskset","-c",",".join(map(str,cpus)),str(ff),"-r","-f","-i",str(attempt/inp.name),"-o",str(out),"-p","-stdext","-ex",str(ext),"-t",str(scratch),"-p4pg",str(procgrp),"-nthreads","1"]
                with (attempt/"launch.log").open("w") as log:
                    process = subprocess.Popen(command,cwd=attempt,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    def stop(signum, frame):
                        os.killpg(process.pid, signal.SIGTERM)
                        process.wait()
                        raise RuntimeError("calculation interrupted")
                    signal.signal(signal.SIGTERM, stop)
                    signal.signal(signal.SIGINT, stop)
                    process.wait()
                    result = process
                for filename,suffix in [("PUNCH",".dat"),("IRCDATA",".irc")]:
                    candidates = [attempt/filename, scratch/filename]
                    for candidate in candidates:
                        if candidate.exists():
                            shutil.copy2(candidate,inp.with_suffix(suffix)); break
                status["returncode"] = result.returncode
                if result.returncode:
                    raise ValueError(f"process exit {result.returncode}")
                status["energy_hartree"] = validate(out.read_text(errors="replace"),text)
                status["success"] = True
        finally:
            if out.exists():
                shutil.copy2(out,attempt/out.name)
                status["output_sha256"] = hashlib.sha256(out.read_bytes()).hexdigest()
            state.write_text(json.dumps(status,indent=2)+"\n")
            (attempt/"status.json").write_text(json.dumps(status,indent=2)+"\n")
        print("COMPLETED" if "RUNTYP=IRC" in text else "CONVERGED", inp.name, status["energy_hartree"],flush=True)

if __name__ == "__main__":
    main()

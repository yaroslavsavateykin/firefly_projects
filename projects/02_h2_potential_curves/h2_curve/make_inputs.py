POINTS = [0.40, 0.50, 0.60, 0.70, 0.80, 1.00, 1.20, 1.50, 2.00, 3.00, 5.00]


def tag(r):
    return f"{r:.2f}".replace(".", "_")


def data(title, r):
    z = r / 2
    return f""" $DATA
{title}, R={r:.2f} Angstrom
C1
H     1.0     0.0000000000     0.0000000000    {-z: .10f}
H     1.0     0.0000000000     0.0000000000     {z: .10f}
 $END
"""


def generate_rhf():
    for r in POINTS:
        name = f"h2_rhf_R_{tag(r)}"
        with open(f"{name}.inp", "w") as f:
            f.write(
                " $CONTRL D5=.T. EXETYP=RUN FSTINT=.T. GENCON=.F. ICHARG=0 ICUT=13 INTTYP=HONDO\n"
                "      ITOL=30 MAXIT=100 MULT=1 RUNTYP=ENERGY SCFTYP=RHF WIDE=1 $END\n"
                " $MOORTH NOSTF=.T. NOZERO=.T. SYMDEN=.T. SYMS=.T. SYMVEC=.T. SYMVX=.T.\n"
                "      TOLE=0.0D0 TOLZ=0.0D0 $END\n"
                " $GUESS GUESS=HUCKEL $END\n"
                " $BASIS GBASIS=STO NGAUSS=3 $END\n"
                " $SYSTEM KDIAG=0 MASMEM=200000000 MWORDS=200 MXBCST=-1 NOJAC=1 TIMLIM=60000 $END\n"
                " $SCF DAMP=.T. DIIS=.T. DIRSCF=.T. FDIFF=.F. SHIFT=.T. SOSCF=.F. $END\n"
                + data("H2 RHF/STO-3G potential-energy point", r)
            )


def generate_fullci():
    for r in POINTS:
        name = f"h2_fci_R_{tag(r)}"
        with open(f"{name}.inp", "w") as f:
            f.write(
                " $CONTRL CITYP=ALDET D5=.T. EXETYP=RUN FSTINT=.T. GENCON=.F. ICHARG=0 ICUT=13\n"
                "      INTTYP=HONDO ITOL=30 MAXIT=100 MULT=1 RUNTYP=ENERGY SCFTYP=RHF WIDE=1 $END\n"
                " $MOORTH NOSTF=.T. NOZERO=.T. SYMDEN=.T. SYMS=.T. SYMVEC=.T. SYMVX=.T.\n"
                "      TOLE=0.0D0 TOLZ=0.0D0 $END\n"
                " $GUESS GUESS=HUCKEL $END\n"
                " $BASIS GBASIS=STO NGAUSS=3 $END\n"
                " $SYSTEM KDIAG=0 MASMEM=200000000 MWORDS=200 MXBCST=-1 NOJAC=1 TIMLIM=60000 $END\n"
                " $SCF DAMP=.T. DIIS=.T. DIRSCF=.T. FDIFF=.F. SHIFT=.T. SOSCF=.F. $END\n"
                " $CIDET NACT=2 NCORE=0 NELS=2 NSTATE=4 $END\n"
                + data("H2 full CI/STO-3G potential-energy point", r)
            )


def main():
    generate_rhf()
    generate_fullci()


main()

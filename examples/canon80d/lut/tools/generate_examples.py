#!/usr/bin/env python3
"""Generate original synthetic looks. No manufacturer/film matching claimed."""
from pathlib import Path

def generate(output, size=5):
    output.mkdir(parents=True,exist_ok=True)
    examples=[
        ("identity", "Identity calibration test",lambda r,g,b:(r,g,b)),
        ("warm_soft", "Original synthetic warm soft look",lambda r,g,b:
            (min(1,.02+.98*r**.92),min(1,.01+.98*g),.015+.925*b)),
    ]
    for name,description,function in examples:
        lines=["# "+description+"; no film or camera match claimed.",f'TITLE "{name}"',
               f"LUT_3D_SIZE {size}","DOMAIN_MIN 0 0 0","DOMAIN_MAX 1 1 1"]
        for b in range(size):
            for g in range(size):
                for r in range(size):
                    lines.append(" ".join(f"{v:.9f}" for v in function(r/(size-1),g/(size-1),b/(size-1))))
        (output/(name+".cube")).write_text("\n".join(lines)+"\n")

if __name__=="__main__":
    generate(Path(__file__).resolve().parents[1]/"examples")

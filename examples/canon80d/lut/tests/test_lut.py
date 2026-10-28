"""Exercise .cube parsing -> binary compiler -> actual C host against a float oracle."""
import importlib.util
import itertools
import math
from pathlib import Path
import random
import struct
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("compiler",ROOT/"tools/compile_cube.py")
compiler=importlib.util.module_from_spec(spec)
spec.loader.exec_module(compiler)

def cube(n, function, low=(0,0,0), high=(1,1,1)):
    rows=[]
    text=[f'LUT_3D_SIZE {n}', 'DOMAIN_MIN '+' '.join(map(str,low)),
          'DOMAIN_MAX '+' '.join(map(str,high))]
    for b,g,r in itertools.product(range(n),repeat=3):
        row=function(r/(n-1),g/(n-1),b/(n-1))
        rows.append(row)
        text.append(' '.join(f'{v:.12g}' for v in row))
    return '\n'.join(text),rows

def reference(rgb,n,rows,low,high):
    coordinates=[min(n-1,max(0,(v/65535-lo)/(hi-lo)*(n-1)))
                 for v,lo,hi in zip(rgb,low,high)]
    base=[min(n-2,math.floor(c)) for c in coordinates]
    fractions=[c-i for c,i in zip(coordinates,base)]
    out=[0.,0.,0.]
    for dr,dg,db in itertools.product((0,1),repeat=3):
        weight=math.prod(f if d else 1-f for d,f in zip((dr,dg,db),fractions))
        row=rows[base[0]+dr+n*(base[1]+dg+n*(base[2]+db))]
        for channel in range(3):
            out[channel]+=weight*row[channel]*65535
    return out

class LutTest(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
    def tearDown(self):
        self.tmp.cleanup()
    def run_host(self,blob,pixels,maximum=65535,expect_success=True):
        (self.root/'look.c80lut').write_bytes(blob)
        raster=(struct.pack('>'+str(len(pixels)*3)+'H',*(v for row in pixels for v in row))
                if maximum==65535 else bytes(v for row in pixels for v in row))
        (self.root/'in.ppm').write_bytes(f'P6\n{len(pixels)} 1\n{maximum}\n'.encode()+raster)
        output=self.root/'out.ppm'
        output.unlink(missing_ok=True)
        result=subprocess.run([str(ROOT/'build/c80-grade'),str(self.root/'look.c80lut'),
                               str(self.root/'in.ppm'),str(output)],capture_output=True)
        if not expect_success:
            self.assertNotEqual(result.returncode,0)
            return result.stderr.decode()
        self.assertEqual(result.returncode,0,result.stderr)
        payload=output.read_bytes().split(b'\n',3)[3]
        values=struct.unpack('>'+str(len(pixels)*3)+'H',payload) if maximum==65535 else list(payload)
        return list(zip(*(iter(values),)*3))
    def test_identity_all_8bit_values_and_primary_boundaries(self):
        text,_=cube(17,lambda r,g,b:(r,g,b))
        blob,_=compiler.compile_cube(text)
        pixels=[(i,255-i,(i*73)%256) for i in range(256)]
        pixels+=list(itertools.product((0,255),repeat=3))
        self.assertEqual(self.run_host(blob,pixels,255),pixels)
    def test_channel_order_red_fastest(self):
        text,_=cube(2,lambda r,g,b:(b,r,g))
        blob,_=compiler.compile_cube(text)
        pixels=list(itertools.product((0,12345,65535),repeat=3))
        actual=self.run_host(blob,pixels)
        for source,output in zip(pixels,actual):
            self.assertLessEqual(max(abs(a-b) for a,b in zip(output,(source[2],source[0],source[1]))),1)
    def test_nonlinear_random_offgrid_against_independent_float_oracle(self):
        n=9
        low=(-.25,.125,0.)
        high=(1.25,.875,1.)
        text,rows=cube(n,lambda r,g,b:(r*r*(.8+.2*g),math.sqrt(g)*(.75+.25*b),b*(1-.3*r)),low,high)
        blob,_=compiler.compile_cube(text)
        rng=random.Random(80)
        pixels=[tuple(rng.randrange(65536) for _ in range(3)) for _ in range(2000)]
        pixels+=list(itertools.product((0,65535),repeat=3))
        actual=self.run_host(blob,pixels)
        errors=[abs(a-b) for pixel,output in zip(pixels,actual)
                for a,b in zip(output,reference(pixel,n,rows,low,high))]
        self.assertLessEqual(max(errors),4.)
    def test_maximum_dimension_compiles_and_runs(self):
        text,_=cube(65,lambda r,g,b:(r,g,b))
        blob,info=compiler.compile_cube(text)
        self.assertEqual(info['table_bytes'],1647750)
        actual=self.run_host(blob,[(0,65535,32768)])[0]
        self.assertLessEqual(max(abs(a-b) for a,b in zip(actual,(0,65535,32768))),1)
    def test_parser_rejects_malformed_sources(self):
        valid,_=cube(2,lambda r,g,b:(r,g,b))
        malformed=[valid+'\n0 0 0',valid.rsplit('\n',1)[0],valid.replace('LUT_3D_SIZE 2','LUT_3D_SIZE 66'),
                   valid.replace('DOMAIN_MAX 1 1 1','DOMAIN_MAX 0 1 1'),
                   valid+'\nDOMAIN_MIN 0 0 0',valid.replace('0 0 0\n','nan 0 0\n',1),
                   valid.replace('LUT_3D_SIZE 2','LUT_1D_SIZE 2'),valid.replace('DOMAIN_MIN 0 0 0','DOMAIN_MIN -inf 0 0'),
                   valid.replace('DOMAIN_MAX 1 1 1','DOMAIN_MAX 0.000001 1 1')]
        for text in malformed:
            with self.subTest(text=text[:80]), self.assertRaises(ValueError):
                compiler.compile_cube(text)
    def test_out_of_range_output_requires_explicit_clip(self):
        text,_=cube(2,lambda r,g,b:(r*2,g,b))
        with self.assertRaisesRegex(ValueError,'clip-output'):
            compiler.compile_cube(text)
        blob,info=compiler.compile_cube(text,clip_output=True)
        self.assertEqual(info['clipped_components'],4)
        self.assertEqual(self.run_host(blob,[(65535,0,0)]),[(65535,0,0)])
    def test_binary_rejects_corruption_truncation_and_bad_fields(self):
        text,_=cube(2,lambda r,g,b:(r,g,b))
        blob,_=compiler.compile_cube(text)
        mutations=[]
        for index in (0,8,10,12,40,44,49):
            changed=bytearray(blob); changed[index]^=255; mutations.append(changed)
        mutations.extend((blob[:20],blob[:-1],blob+b'X'))
        for changed in mutations:
            with self.subTest(size=len(changed)):
                self.run_host(changed,[(0,0,0)],expect_success=False)
    def test_compiler_cli_no_overwrite(self):
        text,_=cube(2,lambda r,g,b:(r,g,b))
        source=self.root/'look.cube'; source.write_text(text)
        target=self.root/'look.c80lut'
        command=['python3',str(ROOT/'tools/compile_cube.py'),str(source),str(target)]
        first=subprocess.run(command,capture_output=True)
        self.assertEqual(first.returncode,0,first.stderr)
        original=target.read_bytes()
        self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
        self.assertEqual(target.read_bytes(),original)

if __name__=='__main__':
    unittest.main()

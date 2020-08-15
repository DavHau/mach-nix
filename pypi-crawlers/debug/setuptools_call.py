import sys, setuptools, tokenize

sys.argv[0] = 'setup.py'
sys.argv[1] = 'install'
__file__='setup.py'
f=getattr(tokenize, 'open', open)(__file__)
code=f.read().replace('\r\n', '\n')
f.close()
exec(compile(code, __file__, 'exec'))
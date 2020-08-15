### Debugging dependency extraction for a single package
- Extraction uses a modified python interpreter which must also be used for debugging. It is available from ./src/extractor/default.nix as attributes (py27, py35, py36, ...). Either build it via `nix-build ./src/extractor -A py37` for example or use `nix-shell`.
- Find the sdist release of the package you want to debug on pypi.org, download and unpack it.
- Copy the `./debug/setuptools_call.py` of this project to the unpacked source to the same directory the setup.py is in. Execute `setuptools_call.py` from there.
- You can use a debugger and set breakpoints in `setup.py`.

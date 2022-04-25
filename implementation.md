## File resolution

`mach-nix` uses [nix-pypi-fetcher](https://github.com/DavHau/nix-pypi-fetcher) to translate package versions to URLs and hashes.

For example, the declaration "package pillow + version 9.1.0 + python 3.9 + linux" resolves to

```json
  "Pillow-9.1.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl": [
    "gig6+ZwcOluh2kTGcpbVqtGfEcU1tVGlrlUyijF84zE=",
    "cp39"
  ],
```

The wheel URL is constructed in [pypi-crawlers/src/crawl_wheel_deps.py](pypi-crawlers/src/crawl_wheel_deps.py)

```py
def construct_url(name, pyver, filename: str):
    base_url = "https://files.pythonhosted.org/packages/"
    return f"{base_url}{pyver}/{name[0]}/{name}/{filename}"
```

So in this example, the full URL would be

```
https://files.pythonhosted.org/packages/cp39/p/pillow/Pillow-9.1.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
```

Now `mach-nix` can call Nix's `fetchurl` like

```nix
builtins.fetchurl {
  url = "https://files.pythonhosted.org/packages/cp39/p/pillow/Pillow-9.1.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl";
  sha256 = "gig6+ZwcOluh2kTGcpbVqtGfEcU1tVGlrlUyijF84zE=";
}
```

... and Nix will download the wheel file to `/nix/store`

```console
$ unzip -l /nix/store/7gbbbrsqkw7f69axyh818abh9yw45fnb-Pillow-9.1.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl | head
Archive:  /nix/store/7gbbbrsqkw7f69axyh818abh9yw45fnb-Pillow-9.1.0-cp39-cp39-manylinux_2_17_x86_64.manylinux2014_x86_64.whl
  Length      Date    Time    Name
---------  ---------- -----   ----
        0  04-01-2022 10:08   PIL/
        0  04-01-2022 10:08   Pillow.libs/
        0  04-01-2022 10:08   Pillow-9.1.0.dist-info/
     7311  04-01-2022 10:08   PIL/PdfImagePlugin.py
   141328  04-01-2022 10:08   PIL/_imagingcms.cpython-39-x86_64-linux-gnu.so
    46872  04-01-2022 10:08   PIL/_imagingtk.cpython-39-x86_64-linux-gnu.so
     1513  04-01-2022 10:08   PIL/GribStubImagePlugin.py
```

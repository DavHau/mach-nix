{

    description = "Create highly reproducible python environments";

    inputs.flake-utils.url = "github:numtide/flake-utils";

    outputs = { self, nixpkgs, flake-utils }: {

        packages.mach-nix = import ./default.nix;

        defaultPackage = self.packages.mach-nix.mach-nix;

        apps.mach-nix = flake-utils.lib.mkApp { drv = self.packages.mach-nix.mach-nix; };
        defaultApp = self.apps.mach-nix;

        mkPython = self.packages.mach-nix.mkPython;
        mkPythonShell = self.packages.mach-nix.mkPythonShell;
        
    };
}


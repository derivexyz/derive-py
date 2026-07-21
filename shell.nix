with import (fetchTarball {
  url = "https://github.com/NixOS/nixpkgs/archive/nixos-25.11.tar.gz";
  # get with: nix-prefetch-url --unpack https://github.com/NixOS/nixpkgs/archive/nixos-25.11.tar.gz
  sha256 = "0ln4yw7z3g9lb0x081hc0pd2j1wsx2qqf6bgmwwvdbkcl4bcy1dp"; 
}) {};

let
  python = pkgs.python311;
  poetry = pkgs.poetry;
  userShell = builtins.getEnv "SHELL";

in

mkShell {
  NIX_LD_LIBRARY_PATH = lib.makeLibraryPath [
    nss
    sane-backends
    nspr
    zlib
    libglvnd
    gcc
    openssl
    openssl_legacy
    bzip2
    libffi
    readline
    libgcc
    ncurses
    stdenv.cc
    stdenv.cc.libc stdenv.cc.libc_dev
  ];

  buildInputs = [
    pkgs.cowsay
    pkgs.gum
    pkgs.asciinema
    pkgs.asciinema-agg
    pkgs.poetry
    pkgs.python311
    pkgs.python311Packages.pip
    pkgs.python311Packages.virtualenv
    pkgs.python311Packages.unicurses
    pkgs.python311Packages.gnureadline
    pkgs.python311Packages.pyopenssl
    pkgs.python311Packages.cython
    pkgs.python311Packages.cytoolz
    pkgs.pythonManylinuxPackages.manylinux2014Package
    pkgs.cmake
  ];

  NIX_LD = builtins.readFile "${stdenv.cc}/nix-support/dynamic-linker";
  PYRIGHT_PYTHON_FORCE_VERSION ="1.1.407";

  shellHook = ''
    set -e
    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib.outPath}/lib:$LD_LIBRARY_PATH";
    echo 'Spinning up Python Virtual Environment in .nix-venv directory 🐍'
    ${pkgs.python311.interpreter} -m venv .nix-venv
    export PATH=$PWD/.nix-venv/bin:$PATH
    if [ -z "''${POETRY_RUN_SHELL_ACTIVE:-}" ]; then
      export POETRY_RUN_SHELL_ACTIVE=1
      echo "Dropping into pyenv"
      exec poetry run ${userShell}
    fi
  '';
}


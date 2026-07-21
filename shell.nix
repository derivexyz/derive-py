let
  pkgs = import (builtins.fetchTarball {
    url = "https://github.com/NixOS/nixpkgs/archive/nixos-25.11.tar.gz";
    sha256 = "0ln4yw7z3g9lb0x081hc0pd2j1wsx2qqf6bgmwwvdbkcl4bcy1dp";
  }) {};

  inherit (pkgs) lib;

  python = pkgs.python311;
  poetry = pkgs.poetry;
  userShell = builtins.getEnv "SHELL";

  

  runtimeLibraries = with pkgs; [
    nss
    sane-backends
    nspr
    zlib
    libglvnd
    openssl
    openssl_legacy
    bzip2
    libffi
    readline
    ncurses
    stdenv.cc.cc.lib
    stdenv.cc.libc
  ];

  pythonPackages = with python.pkgs; [
    pip
    virtualenv
    unicurses
    gnureadline
    pyopenssl
    cython
    cytoolz
  ];
in
pkgs.mkShell {
  packages =
    with pkgs;
    [
      cowsay
      gum
      asciinema
      asciinema-agg
      poetry
      python
      pythonManylinuxPackages.manylinux2014Package
      cmake
    ]
    ++ pythonPackages;

  NIX_LD = lib.fileContents "${pkgs.stdenv.cc}/nix-support/dynamic-linker";
  NIX_LD_LIBRARY_PATH = lib.makeLibraryPath runtimeLibraries;

  PYRIGHT_PYTHON_FORCE_VERSION = "1.1.407";

  shellHook = ''
    venv="$PWD/.nix-venv"

    export LD_LIBRARY_PATH="${pkgs.stdenv.cc.cc.lib}/lib:''${LD_LIBRARY_PATH:-}"

    if [ ! -d "$venv" ]; then
      echo "Creating Python virtual environment in .nix-venv"
      ${python.interpreter} -m venv "$venv"
    fi

    export VIRTUAL_ENV="$venv"
    export PATH="$venv/bin:$PATH"

    if [ -z "''${POETRY_RUN_SHELL_ACTIVE:-}" ]; then
      export POETRY_RUN_SHELL_ACTIVE=1

      user_shell="''${SHELL:-${pkgs.bashInteractive}/bin/bash}"

      echo "Starting Poetry environment with $user_shell"
      exec ${poetry}/bin/poetry run ${userShell}
    fi
  '';
}


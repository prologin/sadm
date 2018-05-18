#!/usr/bin/env bash

set -e

cd $(dirname -- "$0")
trap "exit 1" 1 2 3 15

PYTHON_VERSION=$( python3 --version | cut -d' ' -f2)
OCAML_VERSION=$( ocaml -vnum | cut -f1-2 -d. )

# Download doc
wget -c http://www.acm.uiuc.edu/webmonkeys/book/c_guide.tar.gz -O c.tar.gz
wget -c http://upload.cppreference.com/mwiki/images/6/6c/html_book_20141118.tar.gz -O cpp.tar.gz
wget -c http://caml.inria.fr/distrib/ocaml-${OCAML_VERSION}/ocaml-${OCAML_VERSION}-refman-html.tar.gz -O ocaml.tar.gz
wget -c https://docs.python.org/3/archives/python-${PYTHON_VERSION}-docs-html.tar.bz2 -O python.tar.bz2
wget -c http://fr.php.net/get/php_manual_fr.tar.gz/from/this/mirror -O php.tar.gz
wget -c https://downloads.haskell.org/~ghc/latest/docs/libraries.html.tar.xz -O haskell.tar.gz
wget -c https://static.rust-lang.org/dist/rust-docs-nightly-x86_64-unknown-linux-gnu.tar.gz -O rust.tar.gz
wget -c --header "Cookie: oraclelicense=accept-securebackup-cookie" "http://download.oracle.com/otn-pub/java/jdk/10.0.1+10/fb4372174a714e6b8c52526dc134031e/jdk-10.0.1_doc-all.zip" -O java.zip

# C
if [ -f c.tar.gz ]; then
    echo "Installing C doc"
    tar xf c.tar.gz
    mv c_guide c
else
    echo "** No C doc installed"
fi

# C++
if [ -f cpp.tar.gz ]; then
    echo "Installing C++ doc"
    tar xvf cpp.tar.gz
    mv reference/en cpp
    mv reference/common common
    rm -rf reference
else
    echo "** No C++ doc installed"
fi

# OCaml
if [ -f ocaml.tar.gz ]; then
    echo "Installing OCaml doc"
    tar xf ocaml.tar.gz
    mv htmlman ocaml
else
    echo "** No OCaml doc installed"
fi

# Python3
if [ -f python.tar.bz2 ]; then
    echo "Installing Python3 doc"
    tar xf python.tar.bz2
    mv python-${PYTHON_VERSION}-docs-html python
else
    echo "** No Python doc installed"
fi

# PHP
if [ -f php.tar.gz ]; then
    echo "Installing PHP doc"
    tar xf php.tar.gz
    mv php-chunked-xhtml php
else
    echo "** No PHP doc installed"
fi

# Java
if [ -f java.zip ]; then
    echo "Installing Java doc"
    unzip java.zip
    mv docs java
else
    echo "** No Java doc installed"
fi

# Haskell
if [ -f haskell.tar.gz ]; then
    echo "Installing Haskell doc"
    tar xf haskell.tar.gz
    mv libraries haskell
else
    echo "** No Haskell doc installed"
fi

# Rust
if [ -f rust.tar.gz ]; then
    echo "Installing Rust doc"
    tar xf rust.tar.gz
    mv rust-docs-nightly-*/rust-docs/share/doc/rust/html/ rust
    rm -rf rust-docs-nightly-*
else
    echo "** No Rust doc installed"
fi

# Clean
find . -name '*~' -exec rm '{}' \;
find . -name '#*#' -exec rm '{}' \;
mkdir sources
mv *.zip *.tar.gz *.tar.bz2 sources

# vim:set tw=0:

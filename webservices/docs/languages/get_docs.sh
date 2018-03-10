#!/usr/bin/env bash

set -e

cd $(dirname -- "$0")
trap "exit 1" 1 2 3 15

PYTHON_VERSION=$( python3 --version | cut -d' ' -f2)
OCAML_VERSION=$( ocaml -vnum | cut -f1-2 -d. )

# Download doc
wget -c -nv http://www.acm.uiuc.edu/webmonkeys/book/c_guide.tar.gz -O c.tar.gz
wget -c -nv http://upload.cppreference.com/mwiki/images/6/6c/html_book_20141118.tar.gz -O cpp.tar.gz
wget -c -nv http://caml.inria.fr/distrib/ocaml-${OCAML_VERSION}/ocaml-${OCAML_VERSION}-refman-html.tar.gz -O ocaml.tar.gz
wget -c -nv https://docs.python.org/3/archives/python-${PYTHON_VERSION}-docs-html.tar.bz2 -O python.tar.bz2
wget -c -nv http://fr.php.net/get/php_manual_fr.tar.gz/from/this/mirror -O php.tar.gz
wget -c -nv https://downloads.haskell.org/~ghc/latest/docs/libraries.html.tar.xz -O haskell.tar.gz
wget -c -nv --header "Cookie: oraclelicense=accept-securebackup-cookie" "http://download.oracle.com/otn-pub/java/jdk/9.0.4+11/c2514751926b4512b076cc82f959763f/jdk-9.0.4_doc-all.zip" -O java.zip

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
    tar xf haskell.tar.gz
    mv libraries haskell
else
    echo "** No Haskell doc installed"
fi

# Clean
find . -name '*~' -exec rm '{}' \;
find . -name '#*#' -exec rm '{}' \;
mkdir sources
mv *.zip *.tar.gz *.tar.bz2 sources

# vim:set tw=0:

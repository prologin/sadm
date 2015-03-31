#!/usr/bin/env bash

set -e

cd $(dirname -- "$0")
trap "exit 1" 1 2 3 15

PYTHON3_VERSION=3.4.3
PYTHON2_VERSION=2.7.9
OCAML_VERSION=4.02

# Oracle sux
if [ ! -f java.zip ]; then
    echo 'For the java documentation:'
    echo '- Go to http://www.oracle.com/technetwork/java/javase/downloads/index.html'
    echo '- Go to the download page of "Java SE 8 Documentation"'
    echo '- Accept the license'
    echo '- Download the doc to "java.zip"'
    exit 0
fi

# Download doc
wget -nv http://www.acm.uiuc.edu/webmonkeys/book/c_guide.tar.gz -O c.tar.gz
wget -nv http://upload.cppreference.com/mwiki/images/6/6c/html_book_20141118.tar.gz -O cpp.tar.gz
wget -nv http://caml.inria.fr/distrib/ocaml-${OCAML_VERSION}/ocaml-${OCAML_VERSION}-refman-html.tar.gz -O ocaml.tar.gz
wget -nv https://docs.python.org/3/archives/python-${PYTHON3_VERSION}-docs-html.tar.bz2 -O python3.tar.bz2
wget -nv https://docs.python.org/2/archives/python-${PYTHON2_VERSION}-docs-html.tar.bz2 -O python2.tar.bz2
wget -nv http://fr.php.net/get/php_manual_fr.tar.gz/from/this/mirror -O php.tar.gz

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
if [ -f python3.tar.bz2 ]; then
    echo "Installing Python3 doc"
    tar xf python3.tar.bz2
    mv python-${PYTHON3_VERSION}-docs-html python3
else
    echo "** No Python3 doc installed"
fi

# Python2
if [ -f python2.tar.bz2 ]; then
    echo "Installing Python2 doc"
    tar xf python2.tar.bz2
    mv python-${PYTHON2_VERSION}-docs-html python2
else
    echo "** No Python2 doc installed"
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

# Clean
find . -name '*~' -exec rm '{}' \;
find . -name '#*#' -exec rm '{}' \;
mkdir sources
mv *.zip *.tar.gz *.tar.bz2 sources

# vim:set tw=0:

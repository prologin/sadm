#!/usr/bin/env bash

set -e

cd $(dirname -- "$0")
trap "exit 1" 1 2 3 15

# Download doc
wget -nv http://www.acm.uiuc.edu/webmonkeys/book/c_guide.tar.gz -O c.tar.gz
wget -nv http://upload.cppreference.com/mwiki/images/5/5f/html_book_20140323.tar.gz -O cpp.tar.gz
wget -nv http://caml.inria.fr/distrib/ocaml-4.01/ocaml-4.01-refman-html.tar.gz -O ocaml.tar.gz
wget -nv https://docs.python.org/3/archives/python-3.4.0-docs-html.tar.bz2 -O python3.tar.bz2
wget -nv https://docs.python.org/2/archives/python-2.7.6-docs-html.tar.bz2 -O python2.tar.bz2
wget -nv http://fr.php.net/get/php_manual_fr.tar.gz/from/this/mirror -O php.tar.gz
wget -nv --no-check-certificate http://download.oracle.com/otn-pub/java/jdk/7u55-b13/jdk-7u55-apidocs.zip -O java.zip

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
    tar xf cpp.tar.gz
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
    mv python-3.4.0-docs-html python3
else
    echo "** No Python3 doc installed"
fi

# Python2
if [ -f python2.tar.bz2 ]; then
    echo "Installing Python2 doc"
    tar xf python2.tar.bz2
    mv python-2.7.6-docs-html python2
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

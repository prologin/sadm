#!/usr/bin/env bash

cd $(dirname -- "$0")
trap "exit 1" 1 2 3 15

# Download doc
wget http://www.acm.uiuc.edu/webmonkeys/book/c_guide.tar.gz -O c.tar.gz
wget http://upload.cppreference.com/mwiki/images/a/af/html_book_20120620.tar.gz -O cpp.tar.gz
wget http://caml.inria.fr/pub/distrib/ocaml-3.12/ocaml-3.12-refman.html.tar.gz -O ocaml.tar.gz
wget http://docs.python.org/archives/python-2.7.4-docs-html.tar.bz2 -O python.tar.bz2
wget http://fr.php.net/get/php_manual_fr.tar.gz/from/this/mirror -O php.tar.gz
wget --no-check-certificate http://download.oracle.com/otn-pub/java/jdk/7u21-b11/jdk-7u21-apidocs.zip -O java.zip

# C
if [ -f c.tar.gz ]; then
    tar xf c.tar.gz
    mv c_guide c
else
    echo "** No C doc installed"
fi

# C++
if [ -f cpp.tar.gz ]; then
    tar xf cpp.tar.gz
    mv output/en cpp
    rm -rf output
else
    echo "** No C++ doc installed"
fi

# OCaml
if [ -f ocaml.tar.gz ]; then
    tar xf ocaml.tar.gz
    mv htmlman ocaml
else
    echo "** No OCaml doc installed"
fi

# Python
if [ -f python.tar.bz2 ]; then
    tar xf python.tar.bz2
    mv python-2.7.4-docs-html python
else
    echo "** No Python doc installed"
fi

# PHP
if [ -f php.tar.gz ]; then
    tar xf php.tar.gz
    mv php-chunked-xhtml php
else
    echo "** No PHP doc installed"
fi

# Java
if [ -f java.zip ]; then
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

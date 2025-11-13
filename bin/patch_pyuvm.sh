#!/bin/bash

# Replace PyUVM file for sequences (adding pre_body and post_body)
echo "Replacing PyUVM sequence file"
echo "PWD is: $PWD"

pythondir=`find $1/lib -maxdepth 1 -type d -name 'python3.1*'`
echo "Found Python in: $pythondir"
echo "Replacing: $pythondir/site-packages/pyuvm/s14_15_python_sequences.py"
echo "With: bin/s14_15_python_sequences.py"
rm $pythondir/site-packages/pyuvm/s14_15_python_sequences.py
cp bin/s14_15_python_sequences.py $pythondir/site-packages/pyuvm/

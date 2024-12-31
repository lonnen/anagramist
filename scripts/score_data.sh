#!/bin/sh

# Check if a file path was provided as an argument
if [ $# -ne 2 ]; then
    echo "Usage: $0 <file_path> <start_line>"
    exit 1
fi

file_path="$1"
start_line="$2"
l_c=0

# Check if the file exists
if [ ! -f "$file_path" ]; then
    echo "Error: File '$file_path' does not exist"
    exit 1
fi

# Check if anagramist exists and is executable
if [ ! -x "$(command -v anagramist)" ]; then
    echo "Error: anagramist not found in PATH"
    exit 1
fi

while IFS= read -r line || [ -n "$line" ]; do
    # Skip empty lines
    if [ -z "$line" ]; then
        continue
    fi

    ((l_c+=1))
    if [ $l_c -lt $start_line ]; then
        continue
    fi
    
    # Remove trailing whitespace
    line="${line%"${line##*[![:space:]]}"}"
    
    # Process the line through anagramist.py
    anagramist check --auto-letters --candidate-only --json "$line"
    if [ $? -ne 0 ]; then
        echo "Error checking $1 line: $l_c"
        exit
    fi
    
    # Check if anagramist.py execution was successful
    if [ $? -ne 0 ]; then
        echo "Error: anagramist failed processing line: $line"
    fi
done < "$file_path"
#!/usr/bin/env python3
"""
Log forwarder with ANSI code handling and debugging.
"""

import sys
import re
import argparse
from typing import TextIO

def strip_ansi_codes(text: str) -> str:
    """Strip ANSI escape sequences from text."""
    # Pattern to match ANSI escape sequences
    ansi_pattern = re.compile(r'\x1b\[[0-9;]*[a-zA-Z]')
    return ansi_pattern.sub('', text)

def convert_escape_sequences(text: str) -> str:
    """Convert literal escape sequences like \\033 to actual escape characters."""
    # Convert \\033 to \x1b (actual escape character)
    text = text.replace('\\033', '\x1b')
    # Convert \\x1b to \x1b (in case it's already in hex format)
    text = text.replace('\\x1b', '\x1b')
    return text

def forward_logs(input_stream: TextIO, prefix: str, debug: bool = False):
    """Forward logs from input stream with prefix and ANSI handling."""
    # Convert the prefix to use actual escape characters
    prefix = convert_escape_sequences(prefix)
    
    for line in input_stream:
        # Check if this is a BROWSER/VITE message BEFORE stripping ANSI codes
        if '[BROWSER/VITE]' in line:
            # Keep the BROWSER/VITE prefix and add cyan color
            browser_prefix = "\033[0;36m[BROWSER/VITE]\033[0m"  # Cyan
            # Extract the message part after [BROWSER/VITE]
            parts = line.split('[BROWSER/VITE]', 1)
            if len(parts) > 1:
                message = parts[1].lstrip()
                output_line = f"{browser_prefix} {message}"
            else:
                output_line = f"{browser_prefix} {line}"
        else:
            # Strip ANSI codes for regular messages
            cleaned_line = strip_ansi_codes(line)
            
            # Remove existing prefixes (like [FRONTEND], [BACKEND], etc.)
            # Look for patterns like [WORD] at the start of the line
            prefix_pattern = re.compile(r'^\[[A-Z]+\]\s*')
            cleaned_line = prefix_pattern.sub('', cleaned_line)
            
            # Add our prefix and output
            output_line = f"{prefix} {cleaned_line}"
        
        print(output_line, end='')
        sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description='Forward logs with prefix and ANSI handling')
    parser.add_argument('--prefix', required=True, help='Prefix to add to each line')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    
    args = parser.parse_args()
    
    if args.debug:
        print(f"[DEBUG] Log forwarder started with prefix: '{args.prefix}'", file=sys.stderr)
        print(f"[DEBUG] Reading from stdin...", file=sys.stderr)
    
    try:
        forward_logs(sys.stdin, args.prefix, args.debug)
    except KeyboardInterrupt:
        if args.debug:
            print(f"[DEBUG] Interrupted by user", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        if args.debug:
            print(f"[DEBUG] Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()

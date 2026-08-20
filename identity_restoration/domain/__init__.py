"""Domain layer — pure. No I/O, no HTTP, no disk reads, no wall-clock reads.

Receives bytes and numbers. Returns bytes and numbers. If a function here
needs to open a file, call a network, or read the system clock, it belongs
in infrastructure/ instead (PHẦN 3.1 of the v2.0 plan).
"""

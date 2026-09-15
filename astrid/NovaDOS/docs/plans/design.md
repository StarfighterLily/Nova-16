# NovaDOS — A TI-OS / DOS / Plan-9 Hybrid for the Nova-16
Check the parent files at [NovaDOS](NovaDOS\docs\plans\design.md) first.

This document exists to refer to the same NovaDOS project, but implemented purely in Astrid.
This mostly applies to the kernel, which the parent project calls to be written in assembly.
This is valid - assembly is faster than a higher-level language, but is also difficult and
tedious. Astrid provides plenty of systems programming features, and is a perfect fit for
writing a true OS for the Nova-16. 
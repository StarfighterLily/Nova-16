#!/usr/bin/env python3
"""
Astrid 2.0 Module System
Provides package and module support for code organization.
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass

from ..lexer.lexer import Lexer
from ..parser.parser import Parser
from ..semantic.analyzer import SemanticAnalyzer
from ..ir.builder import IRBuilder

@dataclass
class Module:
    """Represents a compiled module."""
    name: str
    path: str
    functions: List[str]
    globals: List[str]
    dependencies: List[str]
    ir_module: Optional[Any] = None

@dataclass
class Package:
    """Represents a package containing multiple modules."""
    name: str
    path: str
    modules: Dict[str, Module]
    dependencies: List[str]

class ModuleSystem:
    """Astrid 2.0 module and package system."""

    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.modules: Dict[str, Module] = {}
        self.packages: Dict[str, Package] = {}
        self.lexer = Lexer()
        self.parser = Parser()
        self.semantic_analyzer = SemanticAnalyzer()
        self.ir_builder = IRBuilder()

    def load_module(self, module_path: str) -> Optional[Module]:
        """Load a module from file path."""
        if not os.path.exists(module_path):
            return None

        with open(module_path, 'r', encoding='utf-8') as f:
            source_code = f.read()

        # Parse module
        tokens = self.lexer.tokenize(source_code, module_path)
        ast = self.parser.parse(tokens, module_path)

        # Analyze semantics
        self.semantic_analyzer.analyze(ast)

        # Build IR
        ir_module = self.ir_builder.build(ast)

        # Extract module information
        module_name = Path(module_path).stem
        functions = [func.name for func in ast.functions]
        globals = []  # Would need to extract from AST
        dependencies = []  # Would need to parse import statements

        module = Module(
            name=module_name,
            path=module_path,
            functions=functions,
            globals=globals,
            dependencies=dependencies,
            ir_module=ir_module
        )

        self.modules[module_name] = module
        return module

    def load_package(self, package_path: str) -> Optional[Package]:
        """Load a package from directory path."""
        if not os.path.isdir(package_path):
            return None

        package_name = Path(package_path).name
        modules = {}

        # Load all .ast files in the package
        for file_path in Path(package_path).glob("*.ast"):
            module = self.load_module(str(file_path))
            if module:
                modules[module.name] = module

        # Load subpackages
        for dir_path in Path(package_path).iterdir():
            if dir_path.is_dir() and not dir_path.name.startswith('.'):
                subpackage = self.load_package(str(dir_path))
                if subpackage:
                    # Merge subpackage modules
                    modules.update(subpackage.modules)

        package = Package(
            name=package_name,
            path=package_path,
            modules=modules,
            dependencies=[]
        )

        self.packages[package_name] = package
        return package

    def resolve_dependency(self, module_name: str, package_name: Optional[str] = None) -> Optional[Module]:
        """Resolve a module dependency."""
        # First try direct module lookup
        if module_name in self.modules:
            return self.modules[module_name]

        # Try package.module lookup
        if package_name and package_name in self.packages:
            package = self.packages[package_name]
            if module_name in package.modules:
                return package.modules[module_name]

        # Try to load from file system
        search_paths = [
            self.base_path / f"{module_name}.ast",
            self.base_path / module_name / f"{module_name}.ast"
        ]

        for path in search_paths:
            if path.exists():
                return self.load_module(str(path))

        return None

    def get_module_functions(self, module_name: str) -> List[str]:
        """Get list of functions in a module."""
        module = self.modules.get(module_name)
        return module.functions if module else []

    def get_module_globals(self, module_name: str) -> List[str]:
        """Get list of global variables in a module."""
        module = self.modules.get(module_name)
        return module.globals if module else []

    def link_modules(self, main_module: Module, dependencies: List[Module]) -> Any:
        """Link multiple modules together."""
        # In a full implementation, this would merge IR modules
        # For now, return the main module
        return main_module.ir_module

    def create_module_from_source(self, source_code: str, module_name: str) -> Module:
        """Create a module from source code string."""
        # Parse and analyze
        tokens = self.lexer.tokenize(source_code, f"<{module_name}>")
        ast = self.parser.parse(tokens, f"<{module_name}>")
        self.semantic_analyzer.analyze(ast)
        ir_module = self.ir_builder.build(ast)

        # Extract information
        functions = [func.name for func in ast.functions]
        globals = []
        dependencies = []

        module = Module(
            name=module_name,
            path=f"<{module_name}>",
            functions=functions,
            globals=globals,
            dependencies=dependencies,
            ir_module=ir_module
        )

        self.modules[module_name] = module
        return module

    def export_module(self, module: Module, output_path: str):
        """Export a module to a file."""
        # In a full implementation, this would serialize the module
        # For now, just write the source if available
        if os.path.exists(module.path) and not module.path.startswith('<'):
            import shutil
            shutil.copy2(module.path, output_path)

    def get_module_dependencies(self, module: Module) -> Set[str]:
        """Get all transitive dependencies of a module."""
        visited = set()
        to_visit = [module.name]

        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue

            visited.add(current)
            mod = self.modules.get(current)
            if mod:
                to_visit.extend(mod.dependencies)

        return visited - {module.name}

    def validate_module_structure(self, module: Module) -> List[str]:
        """Validate module structure and return any issues."""
        issues = []

        # Check for missing dependencies
        for dep in module.dependencies:
            if not self.resolve_dependency(dep):
                issues.append(f"Missing dependency: {dep}")

        # Check for circular dependencies
        deps = self.get_module_dependencies(module)
        if module.name in deps:
            issues.append("Circular dependency detected")

        return issues

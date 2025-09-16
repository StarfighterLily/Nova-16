"""
Astrid Scope Management
Proper symbol table implementation with scope hierarchy.
"""

from typing import Dict, Any, Optional, List
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Symbol:
    """Represents a symbol in the symbol table."""
    
    def __init__(self, name: str, symbol_type: str, data_type: Any = None, line: int = 0, column: int = 0):
        self.name = name
        self.symbol_type = symbol_type  # 'variable', 'function', 'struct', etc.
        self.data_type = data_type
        self.line = line
        self.column = column
        self.is_used = False
    
    def __repr__(self):
        return f"Symbol({self.name}, {self.symbol_type}, {self.data_type})"


class Scope:
    """Represents a lexical scope with symbol management."""
    
    def __init__(self, name: str = "global", parent: Optional['Scope'] = None):
        self.name = name
        self.parent = parent
        self.symbols: Dict[str, Symbol] = {}
        self.children: List['Scope'] = []
        
        if parent:
            parent.children.append(self)
    
    def define(self, name: str, symbol: Symbol) -> bool:
        """Define a symbol in this scope. Returns False if already defined."""
        if name in self.symbols:
            return False
        
        self.symbols[name] = symbol
        logger.debug(f"Defined symbol '{name}' in scope '{self.name}'")
        return True
    
    def lookup(self, name: str) -> Optional[Symbol]:
        """Look up a symbol in this scope or parent scopes."""
        if name in self.symbols:
            symbol = self.symbols[name]
            symbol.is_used = True
            return symbol
        
        if self.parent:
            return self.parent.lookup(name)
        
        return None
    
    def lookup_local(self, name: str) -> Optional[Symbol]:
        """Look up a symbol only in this scope (not parent scopes)."""
        return self.symbols.get(name)
    
    def get_unused_symbols(self) -> List[Symbol]:
        """Get all unused symbols in this scope."""
        return [symbol for symbol in self.symbols.values() if not symbol.is_used]
    
    def __repr__(self):
        return f"Scope({self.name}, {len(self.symbols)} symbols)"


class ScopeManager:
    """Manages scope hierarchy during semantic analysis."""
    
    def __init__(self):
        self.global_scope = Scope("global")
        self.current_scope = self.global_scope
        self.scope_stack = [self.global_scope]
    
    def enter_scope(self, name: str = "block") -> Scope:
        """Enter a new scope."""
        new_scope = Scope(name, self.current_scope)
        self.current_scope = new_scope
        self.scope_stack.append(new_scope)
        logger.debug(f"Entered scope '{name}'")
        return new_scope
    
    def exit_scope(self) -> Optional[Scope]:
        """Exit the current scope and return to parent."""
        if len(self.scope_stack) <= 1:
            logger.warning("Attempted to exit global scope")
            return None
        
        old_scope = self.scope_stack.pop()
        self.current_scope = self.scope_stack[-1]
        logger.debug(f"Exited scope '{old_scope.name}'")
        return old_scope
    
    def define_symbol(self, name: str, symbol_type: str, data_type: Any = None, line: int = 0, column: int = 0) -> bool:
        """Define a symbol in the current scope."""
        symbol = Symbol(name, symbol_type, data_type, line, column)
        return self.current_scope.define(name, symbol)
    
    def lookup_symbol(self, name: str) -> Optional[Symbol]:
        """Look up a symbol starting from current scope."""
        return self.current_scope.lookup(name)
    
    def reset(self):
        """Reset scope manager to initial state."""
        self.global_scope = Scope("global")
        self.current_scope = self.global_scope
        self.scope_stack = [self.global_scope]
        logger.debug("Scope manager reset")

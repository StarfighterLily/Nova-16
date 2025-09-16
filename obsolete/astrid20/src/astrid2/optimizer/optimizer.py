"""
Astrid 2.0 Optimizer
"""

from ..utils.logger import get_logger
from .register_allocator import GraphColoringRegisterAllocator

logger = get_logger(__name__)


class Optimizer:
    """Optimizer for Astrid 2.0 IR."""

    def __init__(self):
        self.register_allocator = GraphColoringRegisterAllocator()

    def optimize(self, ir_module):
        """Optimize the IR module."""
        logger.debug("Starting optimization")

        # Perform graph coloring register allocation
        allocation = self.register_allocator.allocate_registers(ir_module)

        # Store allocation in the IR module for use by code generator
        ir_module.register_allocation = allocation
        ir_module.spilled_variables = self.register_allocator.get_spilled_variables()

        logger.debug("Optimization completed")
        return ir_module

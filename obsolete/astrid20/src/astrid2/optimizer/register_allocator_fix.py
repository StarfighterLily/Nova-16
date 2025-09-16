    def _analyze_function_signatures(self, ir_module: IRModule):
        """Analyze function signatures to understand parameter requirements."""
        for function in ir_module.functions:
            param_count = len(function.parameters) if function.parameters else 0
            self.function_signatures[function.name] = param_count
            logger.debug(f"Function {function.name} has {param_count} parameters")
            
    def _analyze_function_calls(self, ir_module: IRModule):
        """Identify which functions make calls to other functions."""
        for function in ir_module.functions:
            has_calls = False
            for block in function.blocks:
                for instruction in block.instructions:
                    if instruction.opcode == 'call':
                        has_calls = True
                        break
                if has_calls:
                    break
            
            if has_calls:
                self.functions_with_calls.add(function.name)
                logger.debug(f"Function {function.name} makes function calls")
                
    def _allocate_function_parameters(self, function: IRFunction, graph: InterferenceGraph):
        """Allocate specific registers for function parameters."""
        if not function.parameters:
            return
            
        for i, param in enumerate(function.parameters):
            if i < len(self.parameter_registers):
                param_reg = self.parameter_registers[i]
                param_name = param['name']
                
                # Map parameter directly to its designated register
                self.allocation[param_name] = param_reg
                logger.debug(f"Allocated parameter {param_name} to {param_reg}")
                
                # Add this parameter to the graph if it's not already there
                param_type = self._map_type_to_register_class(param['type'])
                if param_name not in graph.nodes:
                    graph.add_variable(param_name, param_type)

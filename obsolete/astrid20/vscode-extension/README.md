# Astrid 2.0 VS Code Extension

This extension provides comprehensive language support for Astrid 2.0, the hardware-optimized C-like programming language for the Nova-16 CPU emulator.

## Features

### Language Support
- **Syntax Highlighting**: Full syntax highlighting for Astrid 2.0 code
- **Error Diagnostics**: Real-time error detection and reporting
- **Auto-completion**: Intelligent code completion for keywords and builtin functions
- **Hover Information**: Detailed information on hover for types, functions, and keywords

### IDE Integration
- **Language Server Protocol**: Full LSP support for advanced IDE features
- **Compilation Commands**: Built-in commands to compile Astrid code
- **File Watching**: Automatic recompilation on file changes

## Installation

1. **Install Dependencies**:
   ```bash
   cd astrid2.0
   pip install -r requirements.txt
   ```

2. **Install the Extension**:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X)
   - Click the "..." menu and select "Install from VSIX" or
   - Use the VS Code Extension Development tools to package and install

3. **Package the Extension** (if developing):
   ```bash
   cd vscode-extension
   npm install -g vsce
   vsce package
   ```

## Configuration

### LSP Server Path
Set the path to the Astrid 2.0 LSP server in your VS Code settings:

```json
{
    "astrid2.lsp.server.path": "lsp_server.py"
}
```

## Usage

### Creating Astrid Files
- Create files with `.ast` extension
- VS Code will automatically recognize them as Astrid 2.0 files

### Compilation
- Use the command palette: `Ctrl+Shift+P`
- Search for "Astrid 2.0: Compile"
- Or use the keyboard shortcut (configurable)

### Language Features

#### Syntax Highlighting
```c
// Comments
void main() {
    int8 counter = 0;        // 8-bit integer
    int16 address = 0x1000;  // 16-bit integer
    pixel x = 128;           // Screen coordinate
    color red = 0x1F;        // Color value

    if (counter > 10) {
        set_pixel(x, 100, red);  // Builtin function
    }
}
```

#### Auto-completion
- Type keywords: `void`, `int8`, `if`, `while`, etc.
- Type builtin functions: `set_pixel`, `play_sound`, etc.
- Get parameter hints and documentation

#### Error Detection
- Missing semicolons
- Unmatched braces
- Type mismatches
- Undefined variables

## Supported Features

### Data Types
- `int8` - 8-bit integers (R registers)
- `int16` - 16-bit integers (P registers)
- `pixel` - Screen coordinates (0-255)
- `color` - Color values (0-31)
- `sound` - Audio samples
- `layer` - Graphics layers (0-7)
- `sprite` - Sprite objects (0-15)
- `interrupt` - Interrupt handlers

### Control Flow
- `if`/`else` statements
- `while` loops
- `for` loops
- `return` statements

### Builtin Functions
- **Graphics**: `set_pixel`, `get_pixel`, `clear_screen`, `set_layer`
- **Sound**: `play_sound`, `stop_sound`, `set_volume`, `set_frequency`
- **System**: `delay`, `get_time`, `set_interrupt`, `clear_interrupt`

## Development

### Project Structure
```
vscode-extension/
├── package.json              # Extension manifest
├── language-configuration.json  # Language configuration
├── syntaxes/
│   └── astrid.tmLanguage.json   # Syntax highlighting grammar
├── src/
│   └── extension.js            # Extension implementation
└── out/
    └── extension.js            # Compiled extension
```

### Building
```bash
cd vscode-extension
npm install
npm run compile  # If using TypeScript
vsce package     # Package for distribution
```

## Troubleshooting

### LSP Server Not Starting
1. Check that Python is in your PATH
2. Verify the LSP server path in settings
3. Check the VS Code output panel for error messages

### Compilation Errors
1. Ensure the Astrid 2.0 compiler is properly installed
2. Check that all dependencies are installed
3. Verify file paths in the terminal output

### Syntax Highlighting Issues
1. Restart VS Code
2. Reload the window (Ctrl+Shift+P → "Developer: Reload Window")
3. Check that the .ast file is associated with the Astrid language

## Contributing

Contributions are welcome! Please see the main Astrid 2.0 project for contribution guidelines.

## License

This extension is part of the Astrid 2.0 project and follows the same license terms.

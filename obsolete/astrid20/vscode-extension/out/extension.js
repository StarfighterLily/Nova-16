const vscode = require('vscode');
const path = require('path');
const { LanguageClient, LanguageClientOptions, ServerOptions, TransportKind } = require('vscode-languageclient');

/**
 * @param {vscode.ExtensionContext} context
 */
function activate(context) {
    // Get the server path from configuration
    const config = vscode.workspace.getConfiguration('astrid2');
    let serverPath = config.get('lsp.server.path', 'lsp_server.py');

    // If relative path, resolve relative to workspace
    if (!path.isAbsolute(serverPath)) {
        const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
        if (workspaceFolder) {
            serverPath = path.join(workspaceFolder.uri.fsPath, serverPath);
        }
    }

    // Server options
    const serverOptions = {
        command: 'python',
        args: [serverPath],
        options: {
            cwd: vscode.workspace.workspaceFolders?.[0]?.uri?.fsPath
        }
    };

    // Client options
    const clientOptions = {
        documentSelector: [{ scheme: 'file', language: 'astrid' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.ast')
        }
    };

    // Create and start the language client
    const client = new LanguageClient(
        'astrid2LanguageServer',
        'Astrid 2.0 Language Server',
        serverOptions,
        clientOptions
    );

    // Start the client
    client.start();

    // Register debug adapter
    const factory = new AstridDebugAdapterDescriptorFactory();
    context.subscriptions.push(
        vscode.debug.registerDebugAdapterDescriptorFactory('astrid', factory)
    );

    // Register commands
    context.subscriptions.push(
        vscode.commands.registerCommand('astrid2.compile', async () => {
            const activeEditor = vscode.window.activeTextEditor;
            if (activeEditor && activeEditor.document.languageId === 'astrid') {
                const fileName = activeEditor.document.fileName;
                const outputFile = fileName.replace('.ast', '.asm');

                const terminal = vscode.window.createTerminal('Astrid 2.0');
                terminal.show();
                terminal.sendText(`python run_astrid.py "${fileName}" -o "${outputFile}"`);
            }
        })
    );

    context.subscriptions.push(client);
}

class AstridDebugAdapterDescriptorFactory {
    createDebugAdapterDescriptor(session) {
        const config = vscode.workspace.getConfiguration('astrid2');
        let adapterPath = config.get('debug.adapter.path', 'debug_adapter.py');

        // If relative path, resolve relative to workspace
        if (!path.isAbsolute(adapterPath)) {
            const workspaceFolder = vscode.workspace.workspaceFolders?.[0];
            if (workspaceFolder) {
                adapterPath = path.join(workspaceFolder.uri.fsPath, adapterPath);
            }
        }

        return new vscode.DebugAdapterExecutable('python', [adapterPath]);
    }
}

function deactivate() {
    // Clean up
}

module.exports = {
    activate,
    deactivate
};

Do not overwrite existing documentation unless explicitly requested.
Run the test suite before and after changes to the emulator system.
Use Windows Powershell commands.
Pay attention to tool call requirements and tool call errors to ensure proper tool usage.
This environment is a Windows 10 desktop running VSCodium, using the Cline VSCode plugin.
If an edit tool call fails, ensure you supply the 'diff' and 'path' parameters.
If a search tool call fails, ensure you supply the 'regex' parameter.
If an execute_command tool call fails, ensure you supply the 'command' parameter.
If a read_file tool call fails, ensure you supply the 'path' parameter.
If a list_files tool call fails, ensure you supply the 'path' parameter.
Create new high-coverage tests to verify correct behavior.
Test against the emulator's '--headless' option and verify correct register data and visible pixel reports for graphical programs.
Write new tools as needed (i.e., to test operand encoding) or fix existing tools without losing focus of the task at hand.
$data = $input | ConvertFrom-Json
$tool = if ($data.tool_name) { $data.tool_name } else { 'ツール' }
Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.MessageBox]::Show($tool + ' の実行許可を求めています', 'Claude Code - 許可要求', 'OK', 'Warning')
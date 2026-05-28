<?php
function esc($command, $args) {
    $cmdString = escapeshellcmd($command);
    foreach ($args as $arg) { $cmdString .= ' ' . escapeshellarg($arg); }
    return "sudo bash -c " . escapeshellarg("export PATH=foo; " . $cmdString);
}
$inputs = "3\nuser\n30\n0\n1\n";
$scriptContent = "export TERM=xterm; printf '$inputs' | addws";
echo esc('bash', ['-c', $scriptContent]) . "\n";

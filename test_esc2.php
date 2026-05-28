<?php
function esc($command, $args) {
    $cmdString = escapeshellcmd($command);
    foreach ($args as $arg) { $cmdString .= ' ' . escapeshellarg($arg); }
    return "sudo bash -c " . escapeshellarg("export PATH=foo; " . $cmdString);
}
$script = <<<PYTHON
import os
path = '/etc/xray/config.json'
marker = '###'
username = 'test'
print(username)
PYTHON;
echo esc('/usr/bin/python', ['-c', $script]) . "\n";

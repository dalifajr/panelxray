<?php
echo "<pre>";
echo "Current User: " . shell_exec("whoami") . "\n";
echo "Bot status:\n";
echo shell_exec("systemctl status kyt 2>&1");
echo "\nBot logs:\n";
echo shell_exec("journalctl -u kyt -n 100 --no-pager 2>&1");
echo "</pre>";

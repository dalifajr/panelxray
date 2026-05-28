<?php

namespace App\Services;

class XrayConfigModifier
{
    public static function deleteAccount($configPath, $marker, $username)
    {
        if (!file_exists($configPath)) return false;
        
        $lines = file($configPath);
        $nextLines = [];
        $changed = false;
        $skipNextClient = false;
        
        foreach ($lines as $line) {
            if ($skipNextClient) {
                if (strpos(ltrim($line), '},{') === 0) {
                    $changed = true;
                    $skipNextClient = false;
                    continue;
                }
                $skipNextClient = false;
            }
            
            $parts = preg_split('/\s+/', trim($line));
            if (count($parts) >= 3 && $parts[0] === $marker && strtolower($parts[1]) === strtolower($username)) {
                $changed = true;
                $skipNextClient = true;
                continue;
            }
            
            $nextLines[] = $line;
        }
        
        if ($changed) {
            file_put_contents($configPath, implode("", $nextLines));
            return true;
        }
        return false;
    }

    public static function updateExpiry($configPath, $marker, $username, $newExpiry)
    {
        if (!file_exists($configPath)) return false;
        
        $lines = file($configPath);
        $nextLines = [];
        $changed = false;
        
        foreach ($lines as $line) {
            $parts = preg_split('/\s+/', trim($line));
            if (count($parts) >= 3 && $parts[0] === $marker && strtolower($parts[1]) === strtolower($username)) {
                $nextLines[] = "$marker $username $newExpiry\n";
                $changed = true;
            } else {
                $nextLines[] = $line;
            }
        }
        
        if ($changed) {
            file_put_contents($configPath, implode("", $nextLines));
            return true;
        }
        return false;
    }
}

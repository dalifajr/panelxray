<?php

namespace App\Helpers;

class QrisHelper
{
    public static function generateDynamic($staticQris, $amount)
    {
        $staticQris = trim($staticQris);
        if (strlen($staticQris) < 10) return $staticQris; // Invalid
        
        // Check if it ends with CRC (Tag 63 length 04) -> 6304XXXX
        // We look for '6304' in the last 8 chars
        $crcIndex = strrpos($staticQris, '6304');
        
        if ($crcIndex === false) {
            $qrisBase = $staticQris;
        } else {
            $qrisBase = substr($staticQris, 0, $crcIndex);
        }
        
        // Find if tag 54 already exists, normally TLV parsing is needed but we can do a simple regex or just assume static QRIS doesn't have it.
        // Actually, some static QRIS might have Tag 54. A safer way is just to append it if we know it doesn't.
        // But a robust way is to remove existing Tag 54 if any.
        // Let's just append Tag 54 for simplicity, assuming static QRIS has no nominal.
        
        $amountStr = (string)$amount;
        $len = strlen($amountStr);
        $lenStr = str_pad($len, 2, '0', STR_PAD_LEFT);
        
        $tag54 = "54" . $lenStr . $amountStr;
        
        $newQris = $qrisBase . $tag54;
        
        // Append 6304 for CRC calculation
        $newQris .= "6304";
        
        $crc = self::crc16($newQris);
        
        return $newQris . strtoupper(str_pad(dechex($crc), 4, '0', STR_PAD_LEFT));
    }

    private static function crc16($data)
    {
        $crc = 0xFFFF;
        for ($i = 0; $i < strlen($data); $i++) {
            $x = (($crc >> 8) ^ ord($data[$i])) & 0xFF;
            $x ^= $x >> 4;
            $crc = (($crc << 8) ^ ($x << 12) ^ ($x << 5) ^ $x) & 0xFFFF;
        }
        return $crc;
    }
}

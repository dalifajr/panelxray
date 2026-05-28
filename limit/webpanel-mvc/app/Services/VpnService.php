<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class VpnService
{
    protected $apiUrl;
    protected $secret;

    public function __construct()
    {
        $this->apiUrl = env('PYTHON_API_URL', 'http://127.0.0.1:1014/api/execute');
        $this->secret = env('INTERNAL_API_SECRET', 'secret123'); // Adjust if needed
    }

    /**
     * Executes a command via the Python API
     *
     * @param string $command The main command (e.g., 'addws')
     * @param array $args Arguments for the command
     * @return array ['success' => bool, 'output' => string, 'error' => string]
     */
    public function execute($command, $args = [])
    {
        try {
            $response = Http::timeout(10)->post($this->apiUrl, [
                'command' => $command,
                'args' => $args
            ]);

            if ($response->successful()) {
                $data = $response->json();
                if (isset($data['ok']) && $data['ok'] && $data['code'] === 0) {
                    return [
                        'success' => true,
                        'output' => $data['stdout'],
                        'error' => $data['stderr']
                    ];
                }
                return [
                    'success' => false,
                    'output' => $data['stdout'] ?? '',
                    'error' => $data['stderr'] ?? ($data['error'] ?? 'Unknown error')
                ];
            }

            return [
                'success' => false,
                'output' => '',
                'error' => 'HTTP Error: ' . $response->status()
            ];
        } catch (\Exception $e) {
            Log::error("VpnService Execution Failed: " . $e->getMessage());
            return [
                'success' => false,
                'output' => '',
                'error' => 'Connection to Python API failed.'
            ];
        }
    }

    /**
     * Helper to run awk or grep commands for counting
     */
    public function count($command, $divisor = 1)
    {
        // For simple commands like `awk ... /etc/passwd`, we need to run them in a shell wrapper
        // because subprocess.run takes raw commands, not shell strings by default in our python api unless shell=True
        // Actually, the python API does `subprocess.run([command] + args)`.
        // So we can pass `bash` as command, and `-c` and `$command` as args.
        $res = $this->execute('bash', ['-c', $command]);
        
        if ($res['success']) {
            $val = intval(trim($res['output']));
            if ($divisor > 1) {
                $val = floor($val / $divisor);
            }
            return max(0, $val);
        }
        
        return 0;
    }
}

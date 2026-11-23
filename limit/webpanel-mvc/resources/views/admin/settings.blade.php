@extends('layouts.app')

@section('content')
<div class="container-fluid px-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="mb-0 text-dark fw-bold">Pengaturan Sistem</h2>
    </div>

    <div class="row">
        <!-- Harga Layanan -->
        <div class="col-md-6 mb-4">
            <div class="card border-0 shadow-sm lift-hover">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h5 class="mb-0 fw-bold"><i class="fas fa-tags me-2 text-primary"></i>Harga Layanan (Per 30 Hari)</h5>
                </div>
                <div class="card-body p-4">
                    <form action="{{ route('admin.settings.prices') }}" method="POST">
                        @csrf
                        @php
                            $protocols = ['vmess', 'vless', 'trojan', 'shadowsocks', 'ssh'];
                        @endphp
                        
                        @foreach($protocols as $proto)
                        <div class="mb-3">
                            <label class="form-label text-capitalize fw-bold">Harga {{ $proto }}</label>
                            <div class="input-group">
                                <span class="input-group-text bg-light border">Rp</span>
                                <input type="number" class="form-control border" name="prices[{{ $proto }}][price]" value="{{ $prices[$proto]->price ?? 0 }}" required>
                            </div>
                        </div>
                        @endforeach
                        
                        <hr class="border-secondary opacity-25">
                        <div class="mb-3">
                            <label class="form-label fw-bold">Harga Tambah Limit IP (Per IP)</label>
                            <div class="input-group">
                                <span class="input-group-text bg-light border">Rp</span>
                                <input type="number" class="form-control border" name="extra_ip_price" value="{{ $prices['add_ip']->price ?? 0 }}" required>
                            </div>
                        </div>

                        <div class="mb-3">
                            <label class="form-label fw-bold">Limit IP Maksimal (Customer)</label>
                            <div class="input-group">
                                <span class="input-group-text bg-light border">IP</span>
                                <input type="number" class="form-control border" name="max_ip_limit" value="{{ $settings['max_ip_limit'] ?? 0 }}" min="0" required>
                            </div>
                            <small class="text-muted">Isi 0 untuk tanpa batas. Berlaku untuk user customer.</small>
                        </div>

                        <button type="submit" class="btn btn-primary w-100">Simpan Harga</button>
                    </form>
                </div>
            </div>
        </div>

        <!-- Pengaturan Payment -->
        <div class="col-md-6 mb-4">
            <div class="card border-0 shadow-sm lift-hover mb-4">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h5 class="mb-0 fw-bold"><i class="fas fa-qrcode me-2 text-primary"></i>Pengaturan Payment Gateway</h5>
                </div>
                <div class="card-body p-4">
                    <form action="{{ route('admin.settings.payment') }}" method="POST">
                        @csrf
                        <div class="mb-3">
                            <label class="form-label fw-bold">Payload QRIS Statis</label>
                            <textarea class="form-control border" name="qris_payload" rows="4" required placeholder="000201010211...">{{ $settings['qris_payload'] ?? '' }}</textarea>
                            <small class="text-muted">Scan QRIS toko Anda menggunakan aplikasi scanner dan paste teks hasil scannya di sini.</small>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold">API Secret Key (Notification Listener)</label>
                            <input type="text" class="form-control border" name="payment_secret_key" value="{{ $settings['payment_secret_key'] ?? Str::random(32) }}" required>
                            <small class="text-muted">Gunakan key ini pada aplikasi Notification Listener untuk autentikasi endpoint /api/listener/payment.</small>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Simpan Payment</button>
                    </form>
                </div>
            </div>

            <!-- Pengumuman Login -->
            <div class="card border-0 shadow-sm lift-hover mb-4">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h5 class="mb-0 fw-bold"><i class="fas fa-bullhorn me-2 text-primary"></i>Pengumuman Halaman Login</h5>
                </div>
                <div class="card-body p-4">
                    <form action="{{ route('admin.settings.announcement') }}" method="POST">
                        @csrf
                        <div class="mb-3">
                            <label class="form-label fw-bold">Teks Pengumuman</label>
                            <textarea class="form-control border" name="login_announcement" rows="4" required>{{ $settings['login_announcement'] ?? "Keamanan Terjamin\nLogin diotomatisasi melalui integrasi bot Telegram untuk memastikan hanya admin berwenang yang dapat mengakses kontrol panel server." }}</textarea>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Simpan Pengumuman</button>
                    </form>
                </div>
            </div>

            <!-- Pengaturan Bot Telegram -->
            <div class="card border-0 shadow-sm lift-hover">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h5 class="mb-0 fw-bold"><i class="fab fa-telegram-plane me-2 text-primary"></i>Pengaturan Bot Telegram</h5>
                </div>
                <div class="card-body p-4">
                    <form action="{{ route('admin.settings.bot') }}" method="POST">
                        @csrf
                        <div class="mb-3">
                            <label class="form-label fw-bold">Mode Operasi Bot</label>
                            <select class="form-select border" name="bot_mode" required>
                                <option value="admin_only" {{ ($settings['bot_mode'] ?? 'admin_only') === 'admin_only' ? 'selected' : '' }}>Admin Only (Khusus Admin / Kelola Server)</option>
                                <option value="sales" {{ ($settings['bot_mode'] ?? 'admin_only') === 'sales' ? 'selected' : '' }}>Sales Mode (Jualan VPN / Customer Self-Service)</option>
                            </select>
                            <small class="text-muted">Dalam mode Sales, bot akan menampilkan menu pembelian VPN, cek saldo, dan riwayat transaksi untuk customer non-admin.</small>
                        </div>
                        <div class="mb-3">
                            <div class="form-check form-switch mb-2">
                                <input class="form-check-input" type="checkbox" role="switch" id="botTrialSwitch" name="bot_trial_enabled" value="true" {{ ($settings['bot_trial_enabled'] ?? 'false') === 'true' ? 'checked' : '' }}>
                                <label class="form-check-label fw-bold" for="botTrialSwitch">Aktifkan Akun Trial di Bot</label>
                            </div>
                            <small class="text-muted d-block mb-2">Mengizinkan customer membuat akun trial gratis langsung dari bot.</small>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold">Durasi Akun Trial (Hari)</label>
                            <div class="input-group">
                                <input type="number" class="form-control border" name="bot_trial_days" value="{{ $settings['bot_trial_days'] ?? 1 }}" min="1" required>
                                <span class="input-group-text bg-light border">Hari</span>
                            </div>
                        </div>
                        <div class="row mb-3">
                            <div class="col-6">
                                <label class="form-label fw-bold">Default Limit SSH Baru</label>
                                <input type="number" class="form-control border" name="bot_default_ssh_limit" value="{{ $settings['bot_default_ssh_limit'] ?? 0 }}" min="0" required>
                                <small class="text-muted">Untuk customer yang baru di-acc.</small>
                            </div>
                            <div class="col-6">
                                <label class="form-label fw-bold">Default Limit Xray Baru</label>
                                <input type="number" class="form-control border" name="bot_default_xray_limit" value="{{ $settings['bot_default_xray_limit'] ?? 0 }}" min="0" required>
                                <small class="text-muted">Untuk customer yang baru di-acc.</small>
                            </div>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Simpan Pengaturan Bot</button>
                    </form>
                </div>
            </div>

            <!-- External REST API Integration -->
            <div class="card border-0 shadow-sm lift-hover mt-4">
                <div class="card-header bg-white border-0 pt-4 pb-0 d-flex justify-content-between align-items-center">
                    <h5 class="mb-0 fw-bold"><i class="fas fa-plug me-2 text-primary"></i>External REST API (Website Jualan)</h5>
                    @if(($settings['external_api_enabled'] ?? 'false') === 'true')
                        <span class="badge bg-success">Aktif</span>
                    @else
                        <span class="badge bg-secondary">Nonaktif</span>
                    @endif
                </div>
                <div class="card-body p-4">
                    @if(session('generated_external_api_token') || session('generated_external_api_hmac'))
                        <div class="alert alert-warning border mb-3">
                            <div class="fw-bold mb-2"><i class="fas fa-key me-1"></i>Kredensial Baru (Tampil Sekali — Segera Salin!)</div>
                            <div class="mb-2">
                                <label class="form-label small fw-bold mb-1">Bearer API Token</label>
                                <input type="text" class="form-control form-control-sm font-monospace" readonly value="{{ session('generated_external_api_token') }}" onclick="this.select()">
                            </div>
                            <div class="mb-0">
                                <label class="form-label small fw-bold mb-1">HMAC-SHA256 Secret</label>
                                <input type="text" class="form-control form-control-sm font-monospace" readonly value="{{ session('generated_external_api_hmac') }}" onclick="this.select()">
                            </div>
                        </div>
                    @endif

                    <div class="mb-3">
                        <label class="form-label small fw-bold text-secondary mb-1">Base URL Endpoint</label>
                        <input type="text" class="form-control form-control-sm font-monospace bg-light" readonly value="{{ url('/api/v1/vpn') }}" onclick="this.select()">
                        <small class="text-muted">Token aktif: <code>{{ $settings['external_api_token_prefix'] ?? 'Belum digenerate' }}</code></small>
                    </div>

                    <form action="{{ route('admin.settings.external-api') }}" method="POST" class="mb-3">
                        @csrf
                        <div class="form-check form-switch mb-3">
                            <input class="form-check-input" type="checkbox" role="switch" id="externalApiSwitch" name="external_api_enabled" value="true" {{ ($settings['external_api_enabled'] ?? 'false') === 'true' ? 'checked' : '' }}>
                            <label class="form-check-label fw-bold" for="externalApiSwitch">Aktifkan External REST API v1</label>
                        </div>
                        <div class="mb-3">
                            <label class="form-label fw-bold">IP Allowlist (Opsional)</label>
                            <textarea class="form-control border font-monospace" name="external_api_ip_allowlist" rows="2" placeholder="103.10.20.30, 10.0.0.0/24 (kosongkan untuk semua IP)">{{ $settings['external_api_ip_allowlist'] ?? '' }}</textarea>
                            <small class="text-muted">Pisahkan beberapa IP/CIDR dengan koma atau baris baru.</small>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Simpan Pengaturan API</button>
                    </form>

                    <form action="{{ route('admin.settings.external-api.regenerate') }}" method="POST" onsubmit="return confirm('Generate ulang API Token & HMAC Secret? Kredensial lama akan langsung tidak berlaku.')">
                        @csrf
                        <button type="submit" class="btn btn-outline-danger w-100">
                            <i class="fas fa-sync-alt me-1"></i> Generate / Rotate API Token & HMAC Secret
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>

    <!-- Backup & Restore Server -->
    <div class="row mt-4">
        <div class="col-12 mb-4">
            <div class="card border-0 shadow-sm lift-hover">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h5 class="mb-0 fw-bold"><i class="fas fa-database me-2 text-primary"></i>Backup & Restore VPS</h5>
                </div>
                <div class="card-body p-4">
                    <div class="row">
                        <!-- Backup Section -->
                        <div class="col-md-6 border-end">
                            <h6 class="fw-bold mb-3 text-secondary"><i class="fas fa-download me-2 text-success"></i>Backup Data Server</h6>
                            <p class="text-muted">Unduh arsip cadangan data VPS lengkap (termasuk sertifikat SSL, database akun VPN, quota, limit, database web panel, dan konfigurasi bot).</p>
                            <form action="{{ route('admin.settings.backup') }}" method="POST">
                                @csrf
                                <button type="submit" class="btn btn-success w-100 py-2 fw-bold"><i class="fas fa-file-archive me-2"></i>Buat & Unduh Backup (.zip)</button>
                            </form>
                            
                            @if(file_exists('/etc/kyt/restore_conflicts.json'))
                            <div class="mt-4 p-3 bg-light rounded border border-warning">
                                <h6 class="fw-bold text-warning mb-2"><i class="fas fa-exclamation-circle me-2"></i>Resolusi Konflik Tertunda</h6>
                                <p class="small text-muted mb-3">Terdapat sisa konflik user duplikat dari proses restore gabungan sebelumnya yang belum diselesaikan.</p>
                                <a href="{{ route('admin.settings.restore.conflicts') }}" class="btn btn-warning w-100 fw-bold btn-sm"><i class="fas fa-users-cog me-2"></i>Buka Resolusi Konflik</a>
                            </div>
                            @endif
                        </div>
                        
                        <!-- Restore Section -->
                        <div class="col-md-6 ps-md-4">
                            <h6 class="fw-bold mb-3 text-secondary"><i class="fas fa-upload me-2 text-primary"></i>Restore Data Server</h6>
                            <form id="restore-form" enctype="multipart/form-data">
                                @csrf
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Unggah File Backup (.zip)</label>
                                    <input type="file" class="form-control border" name="backup_file" id="backup_file" accept=".zip">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Atau Masukkan Link Backup</label>
                                    <input type="url" class="form-control border" name="backup_url" id="backup_url" placeholder="https://drive.google.com/...">
                                </div>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Opsi Penggabungan Data</label>
                                    <select class="form-select border" name="restore_mode" id="restore-mode-select">
                                        <option value="merge">Gabungkan Data (Merge & Skip Duplikat)</option>
                                        <option value="clean">Hapus Data Lama (Clean Overwrite)</option>
                                    </select>
                                    <small class="text-muted d-block mt-1">Mode gabung akan mengimpor pengguna baru secara aman tanpa menghapus akun aktif Anda saat ini.</small>
                                </div>
                                <button type="button" onclick="performRestoreAnalysis()" class="btn btn-primary w-100 py-2 fw-bold"><i class="fas fa-upload me-2"></i>Mulai Proses Restore</button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<script>
function performRestoreAnalysis() {
    const form = document.getElementById('restore-form');
    const formData = new FormData(form);
    
    const backupFile = document.getElementById('backup_file').files[0];
    const backupUrl = document.getElementById('backup_url').value;
    
    if (!backupFile && !backupUrl) {
        Swal.fire('Error', 'Silakan pilih file backup atau masukkan link backup.', 'error');
        return;
    }
    
    Swal.fire({
        title: 'Menganalisis Backup...',
        text: 'Mengunduh dan memeriksa file cadangan Anda...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    fetch("{{ route('admin.settings.restore.analyze') }}", {
        method: 'POST',
        headers: {
            'X-CSRF-TOKEN': '{{ csrf_token() }}'
        },
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            Swal.fire('Gagal', data.error || 'Terjadi kesalahan saat menganalisis backup.', 'error');
            return;
        }
        
        let warningHtml = "";
        let showWarning = false;
        
        if (data.domain_mismatch) {
            showWarning = true;
            warningHtml += `<div class="alert alert-warning text-start mb-3" style="font-size: 0.9rem;">
                <i class="fas fa-exclamation-triangle me-2"></i><strong>Peringatan Domain Berbeda:</strong><br>
                Domain backup: <code>${data.backup_domain}</code><br>
                Domain saat ini: <code>${data.current_domain}</code><br><br>
                Jika dilanjutkan, domain server akan diperbarui secara otomatis dan sertifikat SSL Let's Encrypt serta HAProxy akan diregenerasi.
            </div>`;
        }
        
        const mode = document.getElementById('restore-mode-select').value;
        if (mode === 'merge' && data.duplicate_users.length > 0) {
            showWarning = true;
            warningHtml += `<div class="alert alert-info text-start mb-0" style="font-size: 0.9rem;">
                <i class="fas fa-users-cog me-2"></i><strong>User Duplikat Terdeteksi (${data.duplicate_users.length} user):</strong><br>
                User tersebut akan dilewati (skip) agar tidak menimpa data aktif saat ini. Anda dapat menyelesaikannya secara manual di menu Resolusi Konflik setelah restore.
            </div>`;
        } else if (mode === 'clean') {
            showWarning = true;
            warningHtml += `<div class="alert alert-danger text-start mb-0" style="font-size: 0.9rem;">
                <i class="fas fa-trash-alt me-2"></i><strong>Perhatian (Clean Overwrite):</strong><br>
                Seluruh data pengguna, akun VPN, transaksi, dan voucher saat ini akan <strong>DIPOS / DIHAPUS</strong> dan digantikan sepenuhnya oleh data backup.
            </div>`;
        }
        
        if (showWarning) {
            Swal.fire({
                title: 'Konfirmasi Restorasi',
                html: warningHtml,
                icon: 'warning',
                showCancelButton: true,
                confirmButtonColor: '#3085d6',
                cancelButtonColor: '#d33',
                confirmButtonText: 'Ya, Lanjutkan Restore',
                cancelButtonText: 'Batal'
            }).then((result) => {
                if (result.isConfirmed) {
                    executeRestore(formData);
                }
            });
        } else {
            executeRestore(formData);
        }
    })
    .catch(error => {
        Swal.fire('Error', 'Gagal menghubungi server untuk menganalisis backup.', 'error');
        console.error(error);
    });
}

function executeRestore(formData) {
    Swal.fire({
        title: 'Memproses Restore...',
        text: 'Mengimpor data ke server baru. Jangan tutup halaman ini...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
    
    fetch("{{ route('admin.settings.restore') }}", {
        method: 'POST',
        headers: {
            'X-CSRF-TOKEN': '{{ csrf_token() }}'
        },
        body: formData
    })
    .then(response => {
        if (response.redirected) {
            window.location.href = response.url;
        } else {
            return response.json().then(data => {
                if (data.success) {
                    Swal.fire('Berhasil', 'Server berhasil direstore!', 'success').then(() => {
                        window.location.reload();
                    });
                } else {
                    Swal.fire('Gagal', data.error || 'Terjadi kesalahan saat restore.', 'error');
                }
            });
        }
    })
    .catch(error => {
        Swal.fire('Error', 'Gagal memproses restorasi.', 'error');
        console.error(error);
    });
}
</script>
@endsection

@extends('layouts.app')

@section('content')
<div class="container-fluid px-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <h2 class="mb-0 text-white">Pengaturan Sistem</h2>
    </div>

    <div class="row">
        <!-- Harga Layanan -->
        <div class="col-md-6 mb-4">
            <div class="card border-0 shadow-sm lift-hover">
                <div class="card-header bg-dark text-white border-bottom border-secondary">
                    <h5 class="mb-0"><i class="fas fa-tags me-2 text-primary"></i>Harga Layanan (Per 30 Hari)</h5>
                </div>
                <div class="card-body bg-dark text-white">
                    <form action="{{ route('admin.settings.prices') }}" method="POST">
                        @csrf
                        @php
                            $protocols = ['vmess', 'vless', 'trojan', 'ssh'];
                        @endphp
                        
                        @foreach($protocols as $proto)
                        <div class="mb-3">
                            <label class="form-label text-capitalize">Harga {{ $proto }}</label>
                            <div class="input-group">
                                <span class="input-group-text bg-secondary border-0 text-white">Rp</span>
                                <input type="number" class="form-control bg-dark text-white border-secondary" name="prices[{{ $proto }}][price]" value="{{ $prices[$proto]->price ?? 0 }}" required>
                            </div>
                        </div>
                        @endforeach
                        
                        <hr class="border-secondary">
                        <div class="mb-3">
                            <label class="form-label">Harga Tambah Limit IP (Per IP)</label>
                            <div class="input-group">
                                <span class="input-group-text bg-secondary border-0 text-white">Rp</span>
                                <input type="number" class="form-control bg-dark text-white border-secondary" name="extra_ip_price" value="{{ $prices['add_ip']->price ?? 0 }}" required>
                            </div>
                        </div>

                        <button type="submit" class="btn btn-primary w-100">Simpan Harga</button>
                    </form>
                </div>
            </div>
        </div>

        <!-- Pengaturan Payment -->
        <div class="col-md-6 mb-4">
            <div class="card border-0 shadow-sm lift-hover mb-4">
                <div class="card-header bg-dark text-white border-bottom border-secondary">
                    <h5 class="mb-0"><i class="fas fa-qrcode me-2 text-primary"></i>Pengaturan Payment Gateway</h5>
                </div>
                <div class="card-body bg-dark text-white">
                    <form action="{{ route('admin.settings.payment') }}" method="POST">
                        @csrf
                        <div class="mb-3">
                            <label class="form-label">Payload QRIS Statis</label>
                            <textarea class="form-control bg-dark text-white border-secondary" name="qris_payload" rows="4" required placeholder="000201010211...">{{ $settings['qris_payload'] ?? '' }}</textarea>
                            <small class="text-muted">Scan QRIS toko Anda menggunakan aplikasi scanner dan paste teks hasil scannya di sini.</small>
                        </div>
                        <div class="mb-3">
                            <label class="form-label">API Secret Key (Notification Listener)</label>
                            <input type="text" class="form-control bg-dark text-white border-secondary" name="payment_secret_key" value="{{ $settings['payment_secret_key'] ?? Str::random(32) }}" required>
                            <small class="text-muted">Gunakan key ini pada aplikasi Notification Listener untuk autentikasi endpoint /api/listener/payment.</small>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Simpan Payment</button>
                    </form>
                </div>
            </div>

            <!-- Pengumuman Login -->
            <div class="card border-0 shadow-sm lift-hover">
                <div class="card-header bg-dark text-white border-bottom border-secondary">
                    <h5 class="mb-0"><i class="fas fa-bullhorn me-2 text-primary"></i>Pengumuman Halaman Login</h5>
                </div>
                <div class="card-body bg-dark text-white">
                    <form action="{{ route('admin.settings.announcement') }}" method="POST">
                        @csrf
                        <div class="mb-3">
                            <label class="form-label">Teks Pengumuman</label>
                            <textarea class="form-control bg-dark text-white border-secondary" name="login_announcement" rows="4" required>{{ $settings['login_announcement'] ?? "Keamanan Terjamin\nLogin diotomatisasi melalui integrasi bot Telegram untuk memastikan hanya admin berwenang yang dapat mengakses kontrol panel server." }}</textarea>
                        </div>
                        <button type="submit" class="btn btn-primary w-100">Simpan Pengumuman</button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection

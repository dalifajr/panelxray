@extends('layouts.app')

@section('content')
<div class="container py-4">
    <div class="row justify-content-center">
        <div class="col-md-8">
            <h3 class="mb-4 text-dark fw-bold"><i class="fas fa-user-circle text-primary me-2"></i> Profil Pengguna</h3>
            
            <div class="row g-4">
                <!-- Info Section -->
                <div class="col-md-5">
                    <div class="card shadow-sm border-0 h-100">
                        <div class="card-body p-4 text-center">
                            <div class="user-avatar rounded-circle d-flex align-items-center justify-content-center text-white bg-primary mx-auto mb-3 shadow" style="width: 80px; height: 80px; font-size: 2rem; font-weight: bold; text-transform: uppercase;">
                                {{ substr($user->name, 0, 1) }}
                            </div>
                            <h4 class="fw-bold mb-1">{{ $user->name }}</h4>
                            <p class="text-secondary mb-3">{{ $user->username }}</p>
                            
                            <span class="badge {{ $user->role === 'admin' ? 'bg-danger' : 'bg-primary' }} rounded-pill px-3 py-2 mb-4 fs-6">
                                {{ ucfirst($user->role) }}
                            </span>

                            <hr class="text-muted">

                            <div class="text-start mt-4">
                                <p class="mb-2 text-muted fw-bold small text-uppercase">Informasi Akun</p>
                                <ul class="list-unstyled">
                                    <li class="mb-2 d-flex justify-content-between">
                                        <span class="text-secondary">Status</span>
                                        @if($user->status === 'active')
                                            <span class="text-success fw-bold"><i class="fas fa-check-circle"></i> Active</span>
                                        @else
                                            <span class="text-danger fw-bold"><i class="fas fa-ban"></i> Suspended</span>
                                        @endif
                                    </li>
                                    <li class="mb-2 d-flex justify-content-between">
                                        <span class="text-secondary">Limit VPN</span>
                                        <span class="fw-bold text-dark">{{ $user->vpn_account_limit }} Akun Aktif</span>
                                    </li>
                                    <li class="mb-2 d-flex justify-content-between">
                                        <span class="text-secondary">Limit IP VPN</span>
                                        <span class="fw-bold text-dark">{{ $user->role === 'customer' ? '1 (Locked)' : 'Unlimited' }}</span>
                                    </li>
                                </ul>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Form Section -->
                <div class="col-md-7">
                    <div class="card shadow-sm border-0 mb-4">
                        <div class="card-header bg-white border-0 pt-4 pb-0">
                            <h5 class="fw-bold mb-0">Ubah Profil & Password</h5>
                        </div>
                        <div class="card-body p-4">
                            @if($errors->any())
                            <div class="alert alert-danger mb-4">
                                <ul class="mb-0">
                                    @foreach($errors->all() as $error)
                                        <li>{{ $error }}</li>
                                    @endforeach
                                </ul>
                            </div>
                            @endif

                            <form action="{{ route('profile.update') }}" method="POST">
                                @csrf
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Username</label>
                                    <input type="text" class="form-control bg-light" value="{{ $user->username }}" disabled>
                                    <div class="form-text">Username tidak dapat diubah.</div>
                                </div>
                                <div class="mb-3">
                                    <label class="form-label fw-bold">Nama Tampilan</label>
                                    <input type="text" name="name" class="form-control" value="{{ old('name', $user->name) }}" required>
                                </div>
                                <div class="mb-4">
                                    <label class="form-label fw-bold">Password Baru</label>
                                    <input type="password" name="password" class="form-control" placeholder="Biarkan kosong jika tidak ingin mengubah">
                                    <div class="form-text">Minimal 6 karakter.</div>
                                </div>

                                <button type="submit" class="btn btn-primary w-100">Simpan Perubahan</button>
                            </form>
                        </div>
                    </div>

                    <!-- Telegram Section -->
                    <div class="card shadow-sm border-0">
                        <div class="card-body p-4">
                            <h5 class="fw-bold mb-3"><i class="fab fa-telegram text-info"></i> Integrasi Telegram</h5>
                            
                            @if($user->telegram_id)
                                <div class="alert alert-success d-flex align-items-center mb-3">
                                    <i class="fas fa-check-circle fs-4 me-3"></i>
                                    <div>
                                        <strong>Terhubung!</strong><br>
                                        ID Telegram Anda: {{ $user->telegram_id }}
                                    </div>
                                </div>
                                <p class="text-secondary small mb-3">Anda dapat login ke panel ini menggunakan tombol "Login via Telegram" di halaman depan.</p>
                                <form action="{{ route('profile.unlink') }}" method="POST" onsubmit="return confirm('Yakin ingin melepas tautan Telegram? Anda tidak akan bisa login via Telegram lagi hingga menautkan ulang.');">
                                    @csrf
                                    <button type="submit" class="btn btn-outline-danger w-100">Lepaskan Tautan Telegram</button>
                                </form>
                            @else
                                <div class="alert alert-secondary d-flex align-items-center mb-3">
                                    <i class="fas fa-info-circle fs-4 me-3"></i>
                                    <div>
                                        <strong>Belum Terhubung</strong><br>
                                        Tautkan akun Telegram Anda untuk kemudahan login 1 klik.
                                    </div>
                                </div>
                                <a href="{{ route('auth.telegram') }}" class="btn btn-info text-white w-100"><i class="fab fa-telegram-plane"></i> Tautkan Telegram Sekarang</a>
                            @endif
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection

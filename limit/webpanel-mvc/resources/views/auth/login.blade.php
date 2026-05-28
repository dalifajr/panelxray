@extends('layouts.app')

@section('content')
<style>
    .login-container {
        min-height: 100vh;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--bg-color);
    }
    .login-card {
        background: var(--bs-body-bg);
        border-radius: 16px;
        box-shadow: 0 1rem 3rem rgba(0,0,0,.1);
        overflow: hidden;
        width: 100%;
        max-width: 900px;
        display: flex;
    }
    .login-left {
        padding: 3rem;
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .login-right {
        flex: 1;
        background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%);
        padding: 3rem;
        color: white;
        display: flex;
        flex-direction: column;
        justify-content: center;
        position: relative;
    }
    .login-right::after {
        content: '';
        position: absolute;
        top: 0; right: 0; bottom: 0; left: 0;
        opacity: 0.1;
        background-image: radial-gradient(#fff 1px, transparent 1px);
        background-size: 20px 20px;
    }
    @media (max-width: 768px) {
        .login-card {
            flex-direction: column;
        }
        .login-right {
            display: none;
        }
    }
</style>

<div class="login-container">
    <div class="login-card">
        <div class="login-left">
            <div class="d-flex align-items-center gap-2 text-primary fw-bold mb-4 fs-3">
                <i class="fas fa-shield-alt"></i> 
                <span>VPN XRAY <span class="fw-light text-secondary fs-5">| Panel Admin</span></span>
            </div>
            
            <h4 class="fw-bold mb-2">Selamat Datang</h4>
            <p class="text-muted mb-4">Silakan login menggunakan akun Telegram Admin Anda.</p>

            @if(session('error'))
            <div class="alert alert-danger">{{ session('error') }}</div>
            @endif

            <a href="{{ route('auth.telegram') }}" class="btn btn-primary w-100 py-3 mb-3 d-flex align-items-center justify-content-center gap-2">
                <i class="fab fa-telegram-plane fs-5"></i> 
                <span class="fw-bold">Login via Telegram</span>
            </a>
            
            <div class="text-center mt-3 text-muted small">
                &copy; {{ date('Y') }} VPN Xray Panel. All rights reserved.
            </div>
        </div>
        <div class="login-right">
            <div class="position-relative z-1">
                <h2 class="fw-bold mb-3 text-white">Keamanan Terjamin</h2>
                <p class="opacity-75 fs-6 fw-light text-white">
                    Login diotomatisasi melalui integrasi bot Telegram untuk memastikan hanya admin berwenang yang dapat mengakses kontrol panel server.
                </p>
                <div class="mt-4 p-3 bg-white bg-opacity-10 rounded-3">
                    <i class="fas fa-info-circle mb-2 fs-4 text-warning"></i>
                    <p class="small mb-0 opacity-100">Klik tombol login, lalu mulai bot untuk mendapatkan link akses masuk langsung ke dashboard.</p>
                </div>
            </div>
        </div>
    </div>
</div>
@endsection

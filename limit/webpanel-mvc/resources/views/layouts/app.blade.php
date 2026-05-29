<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN XRAY - Web Panel</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <link href="{{ asset('assets/css/bootstrap.min.css') }}" rel="stylesheet">
    <link href="{{ asset('assets/css/student-app.css') }}" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script src="https://cdn.jsdelivr.net/npm/sweetalert2@11"></script>
    <style>
        body {
            font-family: 'Outfit', sans-serif;
        }
        /* Container Utama Loader */
        .page-loader {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(255, 255, 255, 0.8);
            z-index: 9999;
            display: flex;
            align-items: center;
            justify-content: center;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.3s;
        }

        /* Status Aktif */
        .page-loader.active {
            opacity: 1;
            pointer-events: all;
        }

        /* Animasi Spinner (Lingkaran Berputar) */
        .spinner {
            width: 50px;
            height: 50px;
            border: 5px solid #e0e0e0;
            border-top: 5px solid var(--bs-primary);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        /* Tema Gelap */
        [data-bs-theme="dark"] .page-loader {
            background: rgba(0, 0, 0, 0.8);
        }

        /* Tema SweetAlert2 Minimalis & Modern */
        .swal2-popup {
            border-radius: 16px !important;
            padding: 1.25rem !important; /* Dikurangi dari 2rem agar lebih lega di layar kecil */
            font-family: 'Outfit', sans-serif !important;
            width: 95% !important;
            max-width: 500px !important;
        }

        .swal2-title {
            color: #1e293b !important;
            font-size: 1.25rem !important;
            font-weight: 700 !important;
            padding: 0 !important;
            margin: 0 0 10px 0 !important;
        }

        .swal2-html-container {
            color: #64748b !important;
            line-height: 1.6 !important;
            margin: 10px 0 15px 0 !important;
            padding: 0 !important;
            text-align: center !important;
        }

        .swal2-actions {
            margin-top: 15px !important;
            gap: 10px !important;
            width: 100% !important;
            display: flex !important;
            flex-direction: row !important; /* Mencegah tombol bertumpuk (column-reverse) */
            justify-content: center !important;
        }

        .swal2-confirm, .swal2-cancel {
            border-radius: 10px !important;
            padding: 0.6rem 1.5rem !important;
            font-weight: 600 !important;
            flex: 1 !important; /* Membuat lebar tombol seimbang */
            margin: 0 !important;
        }

        .swal2-confirm {
            box-shadow: 0 4px 6px -1px rgba(13, 110, 253, 0.2) !important;
        }

        .swal2-cancel {
            background-color: #f1f5f9 !important;
            color: #475569 !important;
        }

        .swal2-html-container .bg-light table td,
        .swal2-html-container .mt-3 {
            font-size: 0.875rem !important; /* Setara 14px */
            line-height: 1.5 !important;
        }

        /* Gaya Bootstrap Modal Minimalis (selaras dengan SweetAlert) */
        .modal-content {
            border-radius: 16px !important;
            border: none !important;
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1) !important;
        }
        .modal-header {
            background: transparent !important;
            border-bottom: none !important;
            padding: 2rem 2rem 0.5rem 2rem !important;
        }
        .modal-title {
            color: #1e293b !important;
            font-size: 1.5rem !important;
            font-weight: 700 !important;
        }
        .modal-body {
            padding: 1.5rem 2rem !important;
            color: #64748b !important;
        }
        .modal-body label {
            color: #475569 !important;
        }
        .modal-footer {
            border-top: none !important;
            padding: 0.5rem 2rem 2rem 2rem !important;
        }
        .modal-content .btn-primary {
            border-radius: 10px !important;
            padding: 0.625rem 1.5rem !important;
            font-weight: 600 !important;
            background-color: #0d6efd !important;
            border: none !important;
            box-shadow: 0 4px 6px -1px rgba(13, 110, 253, 0.2) !important;
            transition: all 0.2s ease !important;
        }
        .modal-content .btn-primary:hover {
            transform: translateY(-1px);
            box-shadow: 0 6px 10px -1px rgba(13, 110, 253, 0.3) !important;
        }
        .modal-content .btn-light, .modal-content .btn-secondary {
            border-radius: 10px !important;
            padding: 0.625rem 1.5rem !important;
            font-weight: 600 !important;
            background-color: #f1f5f9 !important;
            color: #475569 !important;
            border: none !important;
        }
        .modal-content .btn-light:hover, .modal-content .btn-secondary:hover {
            background-color: #e2e8f0 !important;
        }
        .modal-header .btn-close {
            margin-right: -0.5rem;
            margin-top: -0.5rem;
        }

        /* Transformasi Tabel Menjadi Kartu pada Mobile */
        @media (max-width: 768px) {
            .table, 
            .table tbody, 
            .table tr, 
            .table td {
                display: block;
                width: 100%;
            }

            .table thead {
                display: none; /* Sembunyikan header kolom */
            }

            .account-row {
                background: #ffffff;
                border: 1px solid #e2e8f0 !important;
                border-radius: 12px;
                margin-bottom: 1.25rem;
                padding: 1rem;
                box-shadow: 0 2px 10px rgba(0, 0, 0, 0.03);
                position: relative;
            }

            .account-row td {
                display: flex;
                justify-content: space-between;
                align-items: center;
                border: none !important;
                padding: 0.6rem 0 !important;
                text-align: right;
                font-size: 0.9rem;
            }

            /* Membuat label otomatis jika ada atribut data-label di HTML */
            .account-row td::before {
                content: attr(data-label);
                font-weight: 600;
                color: #64748b;
                text-align: left;
                font-size: 0.8rem;
                text-transform: uppercase;
                margin-right: 1rem;
            }

            /* Baris terakhir (biasanya tombol aksi) */
            .account-row td:last-child {
                margin-top: 0.8rem;
                padding-top: 1rem !important;
                border-top: 1px dashed #e2e8f0 !important;
                justify-content: center;
            }
        }

        /* Optimalisasi Jarak pada Layar Sangat Kecil (Smartphone < 576px) */
        @media (max-width: 576px) {
            .main-content {
                padding: 60px 10px 10px 10px !important; /* Kurangi padding kiri/kanan menjadi 10px */
            }
            .container {
                padding-left: 0 !important;
                padding-right: 0 !important;
            }
            .card {
                border-radius: 12px !important;
            }
            .card-body {
                padding: 1rem 0.75rem !important;
            }
        }
    </style>
</head>
<body class="bg-body-tertiary">
<div class="page-loader active" id="pageLoader">
    <div class="spinner"></div>
</div>

@if(Auth::check())
<nav class="navbar navbar-expand fixed-top shadow-sm px-4 bg-body border-bottom" style="z-index: 1030; top: 0;">
    <div class="d-flex align-items-center gap-3">
        <button class="btn btn-link link-body-emphasis d-md-none text-decoration-none p-0" id="sidebarToggle">
            <i class="fas fa-bars fs-4"></i>
        </button>
        <div class="navbar-brand d-flex align-items-center gap-2 text-primary fw-bold m-0">
            <i class="fas fa-shield-alt"></i> 
            <span>VPN XRAY <span class="fw-light text-secondary fs-6 d-none d-sm-inline">| Panel Admin</span></span>
        </div>
    </div>
        <div class="ms-auto d-flex align-items-center gap-3">
            @php
                $unreadCount = Auth::user()->notifications()->where('is_read', false)->count();
            @endphp
            <a href="{{ route('notifications.index') }}" class="btn btn-link text-decoration-none text-dark position-relative p-0" style="margin-right: 15px;">
                <i class="fas fa-bell fs-5"></i>
                @if($unreadCount > 0)
              <span class="position-absolute top-0 start-100 translate-middle badge rounded-pill bg-danger" style="font-size: 0.65rem;">
                  {{ $unreadCount > 99 ? '99+' : $unreadCount }}
              </span>
              @endif
          </a>
          <form action="{{ route('logout') }}" method="POST" class="m-0">
            @csrf
            <button type="submit" class="btn btn-sm btn-outline-danger d-flex align-items-center gap-2">
                <i class="fas fa-sign-out-alt"></i> <span class="d-none d-sm-inline">Logout</span>
            </button>
        </form>
    </div>
</nav>

<div class="app-container" style="padding-top: 0;">
    <div class="sidebar" id="sidebar">
            <div class="sidebar-header d-flex align-items-center gap-3">
                <div class="user-avatar rounded-circle d-flex align-items-center justify-content-center fw-bold text-white bg-primary" style="width: 40px; height: 40px; text-transform: uppercase;">
                  {{ substr(Auth::user()->name, 0, 1) }}
                </div>
                <div class="user-info d-none d-md-block">
                    <div class="fw-bold text-white">{{ Auth::user()->name }}</div>
                    <div class="text-white-50 small">{{ Auth::user()->role === 'admin' ? 'Administrator' : 'Customer' }}</div>
                </div>
            </div>
            <div class="px-3 mb-3 d-none d-md-block">
                <div class="bg-light p-2 rounded border text-center">
                    <div class="text-secondary small mb-1">Saldo Akun</div>
                    <div class="fw-bold text-dark mb-2">Rp {{ number_format(Auth::user()->balance, 0, ',', '.') }}</div>
                    <a href="{{ route('wallet.index') }}" class="btn btn-sm btn-primary w-100"><i class="fas fa-plus-circle me-1"></i>Top Up</a>
                </div>
            </div>
          <div class="menu-list">
              <div class="menu-group">
                <a href="{{ route('dashboard') }}" class="menu-item {{ request()->routeIs('dashboard') ? 'active' : '' }}">
                    <i class="fas fa-home"></i> <span>Dashboard</span>
                </a>
                @if(Auth::user()->role === 'admin')
                <a href="{{ route('vpn.master') }}" class="menu-item {{ request()->routeIs('vpn.master') ? 'active' : '' }}">
                    <i class="fas fa-database text-info"></i> <span>Master Data VPN</span>
                </a>
                  <a href="{{ route('admin.users') }}" class="menu-item {{ request()->routeIs('admin.users') ? 'active' : '' }}">
                      <i class="fas fa-users text-warning"></i> <span>Manajemen User</span>
                  </a>
                  <a href="{{ route('admin.finance') }}" class="menu-item {{ request()->routeIs('admin.finance') ? 'active' : '' }}">
                      <i class="fas fa-chart-line text-success"></i> <span>Keuangan & Topup</span>
                  </a>
                  <a href="{{ route('admin.orders') }}" class="menu-item {{ request()->routeIs('admin.orders') ? 'active' : '' }}">
                      <i class="fas fa-shopping-cart text-info"></i> <span>Daftar Pesanan</span>
                  </a>
                  <a href="{{ route('admin.settings') }}" class="menu-item {{ request()->routeIs('admin.settings') ? 'active' : '' }}">
                      <i class="fas fa-cog text-secondary"></i> <span>Pengaturan Sistem</span>
                  </a>
                  @endif
                  <a href="{{ route('wallet.index') }}" class="menu-item {{ request()->routeIs('wallet.index') ? 'active' : '' }}">
                      <i class="fas fa-wallet text-success"></i> <span>Keuangan (Wallet)</span>
                  </a>
                  <a href="{{ route('profile') }}" class="menu-item {{ request()->routeIs('profile') ? 'active' : '' }}">
                      <i class="fas fa-user-circle text-primary"></i> <span>Profil Pengguna</span>
                  </a>
            </div>

            <div class="menu-group">
                <div class="menu-header">Kelola VPN</div>
                <a href="{{ route('vpn.index', 'vmess') }}" class="menu-item {{ request()->is('vpn/vmess*') ? 'active' : '' }}"><i class="fas fa-satellite-dish"></i> VMess</a>
                <a href="{{ route('vpn.index', 'vless') }}" class="menu-item {{ request()->is('vpn/vless*') ? 'active' : '' }}"><i class="fas fa-shield-alt"></i> VLESS</a>
                <a href="{{ route('vpn.index', 'trojan') }}" class="menu-item {{ request()->is('vpn/trojan*') ? 'active' : '' }}"><i class="fas fa-horse"></i> Trojan</a>
                <a href="{{ route('vpn.index', 'shadowsocks') }}" class="menu-item {{ request()->is('vpn/shadowsocks*') ? 'active' : '' }}"><i class="fas fa-moon"></i> Shadowsocks</a>
                <a href="{{ route('vpn.index', 'ssh') }}" class="menu-item {{ request()->is('vpn/ssh*') ? 'active' : '' }}"><i class="fas fa-terminal"></i> SSH</a>
            </div>
        </div>
    </div>
@endif

    <!-- Main Content -->
    <div class="{{ Auth::check() ? 'main-content position-relative' : '' }}">
        @if(Auth::check())<div class="main-background"></div>@endif
        <div class="container-fluid position-relative px-4 py-4">
            @yield('content')
        </div>
    </div>
    
    @if(Auth::check())
    <div class="sidebar-overlay" id="sidebarOverlay"></div>
    @endif
    
</div>

@stack('modals')

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    window.addEventListener('load', function() {
        const loader = document.getElementById('pageLoader');
        if (loader) {
            loader.classList.remove('active');
        }
    });

    document.addEventListener('DOMContentLoaded', function() {
        const loader = document.getElementById('pageLoader');
        const links = document.querySelectorAll('a:not([target="_blank"]):not([href^="#"]):not([href^="javascript:"])');
        
        links.forEach(link => {
            link.addEventListener('click', function(e) {
                if(e.ctrlKey || e.metaKey || e.shiftKey) return; // Allow open in new tab
                if (loader) {
                    loader.classList.add('active');
                }
            });
        });

        // Keep form submission loader as well
        const forms = document.querySelectorAll('form');
        forms.forEach(form => {
            form.addEventListener('submit', function() {
                if (loader && !form.classList.contains('no-loader')) {
                    loader.classList.add('active');
                }
            });
        });

        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');

        if(sidebarToggle && sidebar && overlay) {
            sidebarToggle.addEventListener('click', function() {
                sidebar.classList.toggle('active');
                overlay.classList.toggle('active');
            });
            overlay.addEventListener('click', function() {
                sidebar.classList.remove('active');
                overlay.classList.remove('active');
            });
        }
    });
</script>

@if(session('sweet_success'))
<script>
    Swal.fire({
        icon: 'success',
        title: 'Berhasil',
        text: {!! json_encode(session('sweet_success')) !!},
        timer: 3000,
        showConfirmButton: false
    });
</script>
@endif

@if(session('sweet_error'))
<script>
    Swal.fire({
        icon: 'error',
        title: 'Gagal',
        text: {!! json_encode(session('sweet_error')) !!}
    });
</script>
@endif

@stack('scripts')
</body>
</html>

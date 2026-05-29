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
            padding: 2rem !important;
            font-family: 'Outfit', sans-serif !important;
        }

        .swal2-title {
            color: #1e293b !important;
            font-size: 1.5rem !important;
            font-weight: 700 !important;
        }

        .swal2-html-container {
            color: #64748b !important;
            line-height: 1.6 !important;
        }

        .swal2-confirm {
            border-radius: 10px !important;
            padding: 0.625rem 1.5rem !important;
            font-weight: 600 !important;
            box-shadow: 0 4px 6px -1px rgba(13, 110, 253, 0.2) !important;
        }

        .swal2-cancel {
            border-radius: 10px !important;
            background-color: #f1f5f9 !important;
            color: #475569 !important;
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
            <div class="d-flex flex-column">
                <span class="fw-bold text-body" style="font-size: 0.9rem;">{{ Auth::user()->name }}</span>
                <small class="text-secondary" style="font-size: 0.75rem;">ID: {{ explode('@', Auth::user()->email)[0] }}</small>
            </div>
        </div>

        <div class="py-3">
            <div class="menu-group">
                <a href="{{ route('dashboard') }}" class="menu-item {{ request()->routeIs('dashboard') ? 'active' : '' }}">
                    <i class="fas fa-home"></i> <span>Dashboard</span>
                </a>
                <a href="{{ route('vpn.master') }}" class="menu-item {{ request()->routeIs('vpn.master') ? 'active' : '' }}">
                    <i class="fas fa-database text-info"></i> <span>Master Data VPN</span>
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

</body>
</html>

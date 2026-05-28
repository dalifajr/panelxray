<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VPN XRAY - Web Panel</title>
    <link href="{{ asset('assets/css/outfit.css') }}" rel="stylesheet">
    <link href="{{ asset('assets/css/bootstrap.min.css') }}" rel="stylesheet">
    <link href="{{ asset('assets/css/student-app.css') }}" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        body {
            font-family: 'Outfit', sans-serif;
        }
    </style>
</head>
<body class="bg-body-tertiary">

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
            <div class="user-avatar rounded-circle d-flex align-items-center justify-content-center fw-bold text-white bg-primary" style="width: 40px; height: 40px;">
                A
            </div>
            <div class="d-flex flex-column">
                <span class="fw-bold text-body" style="font-size: 0.9rem;">Admin Panel</span>
                <small class="text-secondary" style="font-size: 0.75rem;">ID: {{ Auth::user()->tg_id }}</small>
            </div>
        </div>

        <div class="py-3">
            <div class="menu-group">
                <a href="{{ route('dashboard') }}" class="menu-item {{ request()->routeIs('dashboard') ? 'active' : '' }}">
                    <i class="fas fa-home"></i> <span>Dashboard</span>
                </a>
            </div>

            <div class="menu-group">
                <div class="menu-header">Kelola VPN</div>
                <a href="#" class="menu-item"><i class="fas fa-circle" style="font-size: 0.4rem; opacity: 0.6;"></i> VMess</a>
                <a href="#" class="menu-item"><i class="fas fa-circle" style="font-size: 0.4rem; opacity: 0.6;"></i> VLESS</a>
                <a href="#" class="menu-item"><i class="fas fa-circle" style="font-size: 0.4rem; opacity: 0.6;"></i> Trojan</a>
                <a href="#" class="menu-item"><i class="fas fa-circle" style="font-size: 0.4rem; opacity: 0.6;"></i> Shadowsocks</a>
                <a href="#" class="menu-item"><i class="fas fa-circle" style="font-size: 0.4rem; opacity: 0.6;"></i> SSH</a>
            </div>
        </div>
    </div>
@endif

    <!-- Main Content -->
    <div class="{{ Auth::check() ? 'main-content position-relative' : '' }}">
        @if(Auth::check())<div class="main-background"></div>@endif
        <div class="container-fluid position-relative px-4 py-4" style="z-index: 1;">
            @yield('content')
        </div>
    </div>
    
    @if(Auth::check())
    <div class="sidebar-overlay" id="sidebarOverlay"></div>
    @endif
    
</div>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>
    document.addEventListener('DOMContentLoaded', function() {
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
</body>
</html>

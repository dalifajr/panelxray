@extends('layouts.app')

@section('content')
<!-- Hero Section -->
<div class="position-relative mb-5">
    <!-- Background Banner -->
    <div class="rounded-4 p-5 text-white shadow-sm overflow-hidden position-relative" 
         style="background: linear-gradient(135deg, var(--primary-color) 0%, var(--primary-light) 100%); min-height: 220px;">
        <!-- Abstract Pattern -->
        <div style="position: absolute; top: 0; right: 0; bottom: 0; left: 0; opacity: 0.1; background-image: radial-gradient(#fff 1px, transparent 1px); background-size: 20px 20px;"></div>
        <div style="position: absolute; bottom: -50px; left: -50px; width: 300px; height: 300px; background: rgba(255,255,255,0.1); border-radius: 50%;"></div>
        
        <div class="position-relative z-1">
            <h1 class="fw-bold mb-2 text-white">Selamat Datang, {{ Auth::user()->name }}</h1>
            <p class="mb-0 fs-5 opacity-75 fw-light text-white">Telegram ID: {{ Auth::user()->tg_id }} | Akses Administrator</p>
        </div>
    </div>

    <!-- Floating Stats Cards -->
    <div class="container-fluid px-4" style="margin-top: -60px;">
        <div class="row g-4">
            <!-- Card 1 -->
            <div class="col-md-3">
                <div class="card border-0 shadow-sm h-100 overflow-hidden lift-hover">
                    <div class="card-body p-4 position-relative">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <h2 class="display-5 fw-bold text-dark mb-0">{{ $vmsCount }}</h2>
                                <div class="text-muted small text-uppercase fw-bold">Akun VMess</div>
                            </div>
                            <div class="bg-primary-subtle rounded-3 p-3 text-primary">
                                <i class="fas fa-satellite-dish fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Card 2 -->
            <div class="col-md-3">
                <div class="card border-0 shadow-sm h-100 overflow-hidden lift-hover">
                    <div class="card-body p-4 position-relative">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <h2 class="display-5 fw-bold text-dark mb-0">{{ $vlsCount }}</h2>
                                <div class="text-muted small text-uppercase fw-bold">Akun VLESS</div>
                            </div>
                            <div class="bg-warning-subtle rounded-3 p-3 text-warning-emphasis">
                                <i class="fas fa-shield-alt fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Card 3 -->
            <div class="col-md-3">
                <div class="card border-0 shadow-sm h-100 overflow-hidden lift-hover">
                    <div class="card-body p-4 position-relative">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <h2 class="display-5 fw-bold text-dark mb-0">{{ $trjCount }}</h2>
                                <div class="text-muted small text-uppercase fw-bold">Akun Trojan</div>
                            </div>
                            <div class="bg-success-subtle rounded-3 p-3 text-success">
                                <i class="fas fa-horse fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Card 4 -->
            <div class="col-md-3">
                <div class="card border-0 shadow-sm h-100 overflow-hidden lift-hover">
                    <div class="card-body p-4 position-relative">
                        <div class="d-flex justify-content-between align-items-start mb-2">
                            <div>
                                <h2 class="display-5 fw-bold text-dark mb-0">{{ $sshCount }}</h2>
                                <div class="text-muted small text-uppercase fw-bold">Akun SSH</div>
                            </div>
                            <div class="bg-info-subtle rounded-3 p-3 text-info-emphasis">
                                <i class="fas fa-terminal fa-2x"></i>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</div>

<div class="row g-4 mb-5">
    <div class="col-lg-12">
        <h4 class="fw-bold mb-3"><i class="fas fa-cogs text-primary me-2"></i> Manajemen Layanan</h4>
        <div class="row g-3">
            <div class="col-6 col-md-3">
                <a href="#" onclick="handleQuickLinkClick(event)" class="card border-0 shadow-sm text-center text-decoration-none h-100 lift-hover text-dark bg-white">
                    <div class="card-body py-4">
                        <div class="bg-primary-subtle rounded-circle d-inline-flex p-3 mb-3 text-primary">
                            <i class="fas fa-plus-circle fa-2x"></i>
                        </div>
                        <div class="fw-bold">Buat Akun</div>
                        <div class="small text-muted">Vmess / Vless / Trojan</div>
                    </div>
                </a>
            </div>
            <div class="col-6 col-md-3">
                <a href="#" onclick="handleQuickLinkClick(event)" class="card border-0 shadow-sm text-center text-decoration-none h-100 lift-hover text-dark bg-white">
                    <div class="card-body py-4">
                        <div class="bg-warning-subtle rounded-circle d-inline-flex p-3 mb-3 text-warning-emphasis">
                            <i class="fas fa-list fa-2x"></i>
                        </div>
                        <div class="fw-bold">Daftar Akun</div>
                        <div class="small text-muted">Lihat semua akun</div>
                    </div>
                </a>
            </div>
            <div class="col-6 col-md-3">
                <a href="#" onclick="handleQuickLinkClick(event)" class="card border-0 shadow-sm text-center text-decoration-none h-100 lift-hover text-dark bg-white">
                    <div class="card-body py-4">
                        <div class="bg-success-subtle rounded-circle d-inline-flex p-3 mb-3 text-success">
                            <i class="fas fa-sync-alt fa-2x"></i>
                        </div>
                        <div class="fw-bold">Perpanjang</div>
                        <div class="small text-muted">Tambah masa aktif</div>
                    </div>
                </a>
            </div>
            <div class="col-6 col-md-3">
                <a href="#" onclick="handleQuickLinkClick(event)" class="card border-0 shadow-sm text-center text-decoration-none h-100 lift-hover text-dark bg-white">
                    <div class="card-body py-4">
                        <div class="bg-info-subtle rounded-circle d-inline-flex p-3 mb-3 text-info-emphasis">
                            <i class="fas fa-chart-bar fa-2x"></i>
                        </div>
                        <div class="fw-bold">Statistik</div>
                        <div class="small text-muted">Penggunaan Bandwidth</div>
                    </div>
                </a>
            </div>
        </div>
    </div>
</div>

<script>
    function handleQuickLinkClick(e) {
        e.preventDefault();
        const sidebar = document.getElementById('sidebar');
        const overlay = document.getElementById('sidebarOverlay');
        
        if (window.innerWidth < 968) {
            // Mobile: Tampilkan sidebar
            if (sidebar && overlay) {
                sidebar.classList.add('active');
                overlay.classList.add('active');
            }
        } else {
            // PC/Desktop: Highlight menu sidebar
            if (sidebar) {
                // Hapus class lama dan picu reflow untuk me-restart animasi
                sidebar.classList.remove('sidebar-highlight');
                void sidebar.offsetWidth; 
                sidebar.classList.add('sidebar-highlight');
                
                // Highlight header menu 'Kelola VPN'
                const menuHeaders = document.querySelectorAll('.menu-header');
                let vpnHeader = null;
                menuHeaders.forEach(el => {
                    if (el.textContent.trim().toLowerCase().includes('kelola vpn')) {
                        vpnHeader = el;
                    }
                });
                
                if (vpnHeader) {
                    vpnHeader.style.transition = 'color 0.3s ease';
                    vpnHeader.style.color = 'var(--accent-color)';
                    setTimeout(() => {
                        vpnHeader.style.color = '';
                    }, 3000);
                }
            }
        }
    }
</script>
@endsection

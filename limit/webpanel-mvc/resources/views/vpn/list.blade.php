@extends('layouts.app')

@section('content')
<style>
/* Menghilangkan radius sudut pada tombol di dalam form di tengah grup */
.btn-group > form:not(:last-child) > .btn {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
}

.btn-group > form:not(:first-child) > .btn {
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    border-left: 0; /* Menghilangkan border ganda */
}

/* Jika tombol pertama bukan form tapi setelahnya ada form */
.btn-group > .btn:first-child:not(:last-child) {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
}

/* Merapikan tabel detail di dalam SweetAlert */
#swal2-html-container table td {
    padding-top: 5px !important;
    padding-bottom: 5px !important;
    padding-left: 0 !important;
    vertical-align: top;
}

#swal2-html-container table td:first-child {
    width: 130px !important;
    font-weight: 600;
    color: #495057;
    white-space: nowrap;
}

/* Gaya Tombol Tabel Minimalis */
.btn-group-sm > .btn, 
.btn-group-sm > form > .btn {
    background: #f8f9fa !important;
    border: 1px solid #e2e8f0 !important;
    color: #4a5568 !important;
    font-size: 0.75rem !important;
}

/* Efek Hover Lembut */
.btn-group-sm > .btn:hover, 
.btn-group-sm > form > .btn:hover {
    background: #edf2f7 !important;
    color: #2d3748 !important;
}

/* Khusus Tombol Hapus saat Hover */
.btn-group-sm .btn-delete:hover {
    color: #e53e3e !important;
    background: #fff5f5 !important;
    border-color: #feb2b2 !important;
}
</style>

<div class="container py-4">
    <div class="row mb-4 align-items-center">
        <div class="col-md-6">
            <h2 class="fw-bold mb-0 text-uppercase">Daftar Akun {{ strtoupper($protocol) }}</h2>
        </div>
        <div class="col-md-6 text-end">
            <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#createModal">
                <i class="fas fa-plus me-1"></i> Buat Akun
            </button>
        </div>
    </div>

    <div class="row mb-4">
        <div class="col-md-5 mb-2 mb-md-0">
            <input type="text" id="searchInput" class="form-control" placeholder="Cari username...">
        </div>
        <div class="col-md-3 mb-2 mb-md-0">
            <select id="statusFilter" class="form-select">
                <option value="all">Semua Status</option>
                <option value="active">Aktif</option>
                <option value="pending">Menunggu Pembayaran</option>
                <option value="almost_expired">Hampir Expired</option>
                <option value="expired">Expired</option>
                <option value="suspended">Disuspend</option>
            </select>
        </div>
    </div>

    <div class="card shadow-sm border-0">
        <div class="card-body p-0">
            @if(count($parsedUsers) > 0)
            <div class="table-responsive">
                <table class="table table-hover table-sm table-borderless align-middle mb-0" id="accountsTable">
                    <thead class="table-light">
                        <tr>
                            <th class="ps-3 py-2">No.</th>
                            <th class="py-2">Username</th>
                            @if(auth()->user()->role === 'admin')
                            <th class="py-2">Pembuat</th>
                            @endif
                            <th class="py-2">Limit IP</th>
                            <th class="py-2">Dibuat</th>
                            <th class="py-2">Kedaluwarsa</th>
                            <th class="py-2">Status</th>
                            <th class="text-end pe-3 py-2">Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach($parsedUsers as $index => $user)
                        @php
                            $createdStr = $user['created_at'] ?? '';
                            $formattedCreated = !empty($createdStr) ? \Carbon\Carbon::parse($createdStr)->format('d M Y') : '-';
                            $expStr = $user['expires_at'] ?? '';
                            $formattedExp = !empty($expStr) ? \Carbon\Carbon::parse($expStr)->format('d M Y') : '-';
                            
                            $daysLeft = 0;
                            if(!empty($expStr)) {
                                $daysLeft = \Carbon\Carbon::now()->diffInDays(\Carbon\Carbon::parse($expStr), false);
                            }
                            
                            $status = 'active';
                            if ($user['is_pending_payment'] ?? false) {
                                $status = 'pending';
                            } elseif ($user['active'] == 0) {
                                $status = 'suspended';
                            } elseif ($daysLeft <= 3 && $daysLeft >= 0) {
                                $status = 'almost_expired';
                            } elseif ($daysLeft < 0) {
                                $status = 'expired';
                            }
                        @endphp
                        <tr class="account-row border-bottom" data-username="{{ strtolower($user['username']) }}" data-status="{{ $status }}" data-limit-ip="{{ $user['ip_limit'] ?? 1 }}">
                            <td class="ps-3 text-muted py-2" data-label="No.">{{ $index + 1 }}</td>
                            <td class="fw-bold text-primary py-2" data-label="Username">{{ $user['username'] }}</td>
                            @if(auth()->user()->role === 'admin')
                            <td class="py-2 text-secondary" data-label="Pembuat">{{ $user['creator_name'] ?? 'Sistem' }}</td>
                            @endif
                            <td class="py-2 fw-medium text-secondary" data-label="Limit IP">{{ $user['ip_limit'] ?? 1 }}</td>
                            <td class="py-2 text-secondary" data-label="Dibuat">{{ $formattedCreated }}</td>
                            <td class="py-2 text-secondary" data-label="Kedaluwarsa">{{ $formattedExp }}</td>
                            <td class="py-2" data-label="Status">
                                @if($status === 'pending')
                                    <span class="badge bg-warning text-dark">Menunggu Pembayaran</span>
                                @elseif($status === 'suspended')
                                    <span class="badge bg-danger">Disuspend</span>
                                @elseif($status === 'almost_expired')
                                    <span class="badge bg-warning text-dark">Hampir Expired</span>
                                @elseif($status === 'expired')
                                    <span class="badge bg-secondary">Expired</span>
                                @else
                                    <span class="badge bg-success">Aktif</span>
                                @endif
                            </td>
                            <td class="text-end pe-3 py-2" data-label="Aksi">
                                @if($user['is_pending_payment'] ?? false)
                                    <a href="{{ route('checkout.show', $user['transaction_id']) }}" class="btn btn-sm btn-warning fw-bold text-dark w-100">
                                        <i class="fas fa-wallet me-1"></i> Bayar
                                    </a>
                                @else
                                    <div class="btn-group btn-group-sm">
                                        <button class="btn btn-outline-info" onclick="viewConfig('{{ $protocol }}', '{{ $user['username'] }}')" title="Lihat Konfigurasi">
                                            <i class="fas fa-qrcode"></i>
                                        </button>
                                        <button class="btn btn-outline-primary" onclick="openRenewModal('{{ $user['username'] }}')" title="Perpanjang">
                                            <i class="fas fa-sync"></i>
                                        </button>
                                    @if($user['active'] == 1)
                                        <form action="{{ route('vpn.suspend', [$protocol, $user['username']]) }}" method="POST" class="d-inline mb-0">
                                            @csrf
                                            <button type="submit" class="btn btn-outline-warning" title="Suspend Akun">
                                                <i class="fas fa-ban"></i>
                                            </button>
                                        </form>
                                    @else
                                        <form action="{{ route('vpn.unsuspend', [$protocol, $user['username']]) }}" method="POST" class="d-inline mb-0">
                                            @csrf
                                            <button type="submit" class="btn btn-outline-success" title="Aktifkan Kembali">
                                                <i class="fas fa-play"></i>
                                            </button>
                                        </form>
                                    @endif
                                        <form action="{{ route('vpn.delete', [$protocol, $user['username']]) }}" method="POST" class="d-inline mb-0">
                                            @csrf
                                            <button type="button" class="btn btn-outline-danger btn-delete" data-user="{{ $user['username'] }}" title="Hapus">
                                                <i class="fas fa-trash"></i>
                                            </button>
                                        </form>
                                    </div>
                                @endif
                            </td>
                        </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
            @else
                @if(session('show_vpn_setup_tip'))
                    @php session()->forget('show_vpn_setup_tip'); @endphp
                    <div class="p-4 text-center mx-auto" style="max-width: 600px; background: linear-gradient(135deg, rgba(13, 71, 161, 0.05) 0%, rgba(25, 118, 210, 0.05) 100%); border: 1px solid rgba(13, 71, 161, 0.15); border-radius: var(--radius-lg); margin: 2rem auto;">
                        <div style="background: rgba(13, 71, 161, 0.1); width: 60px; height: 60px; border-radius: 50%; display: flex; align-items: center; justify-content: center; color: var(--primary-color); margin: 0 auto 1.5rem;">
                            <i class="fas fa-magic fa-2x"></i>
                        </div>
                        <h4 class="fw-bold text-dark mb-3">Selamat Bergabung! 🎉</h4>
                        <p class="text-secondary mb-4" style="font-size: 0.95rem; line-height: 1.6;">Anda belum memiliki akun VPN {{ strtoupper($protocol) }}. Mari buat akun pertama Anda dengan mengikuti langkah mudah berikut:</p>
                        
                        <div class="text-start mb-4" style="background: #white; background-color: #fff; padding: 1.5rem; border-radius: var(--radius-md); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);">
                            <div class="d-flex align-items-start gap-3 mb-3">
                                <span style="background: var(--primary-color); color: #fff; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: bold; flex-shrink: 0; margin-top: 0.1rem;">1</span>
                                <div>
                                    <strong class="text-dark">Klik Tombol "Buat Akun"</strong>
                                    <p class="text-muted small mb-0">Klik tombol biru di pojok kanan atas halaman ini untuk membuka form pembuatan akun.</p>
                                </div>
                            </div>
                            <div class="d-flex align-items-start gap-3 mb-3">
                                <span style="background: var(--primary-color); color: #fff; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: bold; flex-shrink: 0; margin-top: 0.1rem;">2</span>
                                <div>
                                    <strong class="text-dark">Isi Detail Akun & Tentukan Limit</strong>
                                    <p class="text-muted small mb-0">Masukkan username pilihan Anda, durasi aktif, serta limit IP (maksimal {{ \App\Models\Setting::where('key', 'max_ip_limit')->value('value') ?: 1 }} IP untuk customer).</p>
                                </div>
                            </div>
                            <div class="d-flex align-items-start gap-3">
                                <span style="background: var(--primary-color); color: #fff; width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.85rem; font-weight: bold; flex-shrink: 0; margin-top: 0.1rem;">3</span>
                                <div>
                                    <strong class="text-dark">Pilih Metode Pembayaran & Aktifkan</strong>
                                    <p class="text-muted small mb-0">Gunakan saldo akun Anda atau pilih metode QRIS untuk pembayaran otomatis instan. Akun Anda langsung aktif seketika!</p>
                                </div>
                            </div>
                        </div>

                        <button class="btn btn-primary px-4 py-2" data-bs-toggle="modal" data-bs-target="#createModal">
                            <i class="fas fa-plus-circle me-1"></i> Mulai Buat Akun Sekarang
                        </button>
                    </div>
                @else
                    <div class="p-5 text-center">
                        <i class="fas fa-box-open fa-3x text-muted mb-3"></i>
                        <h5 class="text-muted">Tidak ada akun yang ditemukan.</h5>
                    </div>
                @endif
            @endif
        </div>
    </div>
</div>

<script>
    document.addEventListener('DOMContentLoaded', function () {
        // Handle Search and Filter
        const searchInput = document.getElementById('searchInput');
        const statusFilter = document.getElementById('statusFilter');
        const rows = document.querySelectorAll('.account-row');

        function filterTable() {
            const searchTerm = searchInput.value.toLowerCase();
            const filterValue = statusFilter.value;

            rows.forEach(row => {
                const username = row.getAttribute('data-username');
                const status = row.getAttribute('data-status');

                const matchesSearch = username.includes(searchTerm);
                const matchesStatus = filterValue === 'all' || status === filterValue;

                if (matchesSearch && matchesStatus) {
                    row.style.display = '';
                } else {
                    row.style.display = 'none';
                }
            });
        }

        if (searchInput) searchInput.addEventListener('input', filterTable);
        if (statusFilter) statusFilter.addEventListener('change', filterTable);

        // Handle Delete Confirmation
        const deleteButtons = document.querySelectorAll('.btn-delete');
        deleteButtons.forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                const form = this.closest('form');
                const username = this.getAttribute('data-user');
                
                Swal.fire({
                    title: 'Hapus Akun?',
                    text: `Akun ${username} akan dihapus permanen!`,
                    icon: 'warning',
                    showCancelButton: true,
                    confirmButtonColor: '#d33',
                    cancelButtonColor: '#3085d6',
                    confirmButtonText: 'Ya, Hapus!',
                    cancelButtonText: 'Batal'
                }).then((result) => {
                    if (result.isConfirmed) {
                        form.submit();
                    }
                });
            });
        });
    });

    function viewConfig(protocol, username) {
        Swal.fire({
            title: 'Memuat...',
            text: 'Sedang mengambil konfigurasi akun',
            allowOutsideClick: false,
            didOpen: () => {
                Swal.showLoading();
            }
        });

        fetch(`/vpn/${protocol}/config/${username}`)
            .then(response => response.json())
            .then(data => {
                if(data.error) {
                    Swal.fire('Error', data.error, 'error');
                } else if (data.config && typeof data.config === 'object') {
                    const info = data.config;
                    
                    window.generateVpnLink = function(sniType) {
                        let addr = info.domain;
                        let host = info.domain;
                        let sni = info.domain;
                        let label = info.username;
                        
                        if (sniType === '1') {
                            addr = "support.zoom.us";
                            host = "support.zoom.us." + info.domain;
                            sni = "support.zoom.us." + info.domain;
                            label = info.username + " (Zoom)";
                        } else if (sniType === '2') {
                            addr = info.domain;
                            host = info.domain;
                            sni = "live.iflix.com";
                            label = info.username + " (Iflix)";
                        }
                        
                        let genLink = '';
                        if (protocol === 'vmess') {
                            const vmessObj = {
                                "v": "2",
                                "ps": label,
                                "add": addr,
                                "port": "443",
                                "id": info.uuid,
                                "aid": "0",
                                "net": "ws",
                                "path": "/vmess",
                                "type": "none",
                                "host": host,
                                "tls": "tls",
                                "sni": sni,
                                "allowInsecure": true
                            };
                            genLink = "vmess://" + btoa(JSON.stringify(vmessObj));
                        } else if (protocol === 'vless') {
                            genLink = `vless://${info.uuid}@${addr}:443?path=/vless&security=tls&encryption=none&type=ws&host=${host}&sni=${sni}#${label}`;
                        } else if (protocol === 'trojan') {
                            genLink = `trojan://${info.uuid}@${addr}:443?path=/trojan-ws&security=tls&type=ws&host=${host}&sni=${sni}#${label}`;
                        } else {
                            genLink = `ss://${info.uuid}@${addr}:443#${label}`;
                        }
                        return genLink;
                    };

                    window.updateConfigModal = function() {
                        const sniType = document.getElementById('sniSelector').value;
                        const newLink = window.generateVpnLink(sniType);
                        document.getElementById('swalConfigLink').value = newLink;
                        const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(newLink)}`;
                        document.getElementById('swalQrCode').src = qrUrl;
                    };
                    
                    let link = window.generateVpnLink('3');
                    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(link)}`;
                    
                    let sniSelectorHtml = '';
                    if (protocol !== 'ssh' && protocol !== 'shadowsocks') {
                        sniSelectorHtml = `
                        <div class="mt-3 text-start">
                            <label class="form-label fw-bold text-secondary small mb-1">Pilih Mode SNI / Payload:</label>
                            <select id="sniSelector" class="form-select form-select-sm mb-2" onchange="window.updateConfigModal()">
                                <option value="3">Tanpa konfigurasi (Default SNI)</option>
                                <option value="1">support.zoom.us</option>
                                <option value="2">live.iflix.com</option>
                            </select>
                        </div>
                        `;
                    }

                    const htmlContent = `
                        <div class="text-center mb-3">
                            <img src="${qrUrl}" id="swalQrCode" alt="QR Code" class="img-fluid border p-2 bg-white rounded shadow-sm" style="max-width: 200px; transition: all 0.3s;">
                        </div>
                        <div class="text-start bg-light p-3 rounded border">
                            <table class="table table-sm table-borderless mb-0">
                                <tr><td class="text-muted" width="110">Username</td><td class="fw-bold text-dark">: ${info.username}</td></tr>
                                <tr><td class="text-muted">Pass / UUID</td><td class="fw-bold text-dark font-monospace small">: <span style="user-select: all;">${info.uuid}</span></td></tr>
                                <tr><td class="text-muted">Protocol</td><td class="fw-bold text-dark text-uppercase">: ${protocol}</td></tr>
                                <tr><td class="text-muted">Domain</td><td class="fw-bold text-dark">: ${info.domain}</td></tr>
                                <tr><td class="text-muted">Limit IP</td><td class="fw-bold text-dark">: ${info.ip_limit}</td></tr>
                                <tr><td class="text-muted">Quota</td><td class="fw-bold text-dark">: ${info.quota == 0 ? 'Unlimited' : info.quota} GB</td></tr>
                            </table>
                        </div>
                        ${sniSelectorHtml}
                        <div class="mt-3 text-start">
                            <label class="form-label fw-bold text-secondary small mb-1">Link Konfigurasi (TLS):</label>
                            <textarea id="swalConfigLink" class="form-control font-monospace small bg-dark text-light" rows="3" readonly style="font-size:0.8rem; resize:none;">${link}</textarea>
                        </div>
                    `;
                    
                    Swal.fire({
                        title: `<span class="fw-bold"><i class="fas fa-qrcode text-primary me-2"></i>Detail ${protocol.toUpperCase()}</span>`,
                        html: htmlContent,
                        width: 500,
                        confirmButtonText: 'Tutup',
                        confirmButtonColor: '#0d6efd'
                    });
                } else {
                    // Fallback for old string response
                    Swal.fire({
                        title: `Konfigurasi ${username}`,
                        html: `<pre class="text-start bg-dark text-light p-3 rounded font-monospace" style="max-height: 300px; overflow-y: auto; font-size: 0.85rem; user-select: all;">${data.config}</pre>`,
                        width: 600,
                        confirmButtonText: 'Tutup'
                    });
                }
            })
            .catch(error => {
                console.error('Error fetching config:', error);
                Swal.fire('Error', 'Gagal memuat konfigurasi', 'error');
            });
    }

    // Modal Handlers
    function openRenewModal(username) {
        document.getElementById('renewUsername').value = username;
        document.getElementById('renewUsernameDisplay').value = username;
        
        // Setup Form Action
        const protocol = '{{ $protocol }}';
        const form = document.getElementById('renewForm');
        form.action = `/vpn/${protocol}/${username}/renew`;
        
        const limitInput = document.getElementById('renewLimitIpInput');
        if (limitInput) {
            const row = document.querySelector(`.account-row[data-username="${username.toLowerCase()}"]`);
            if (row && row.dataset.limitIp) {
                limitInput.value = row.dataset.limitIp;
            }
            if (typeof calculateRenewPrice === 'function') {
                calculateRenewPrice();
            }
        }

        const modal = new bootstrap.Modal(document.getElementById('renewModal'));
        modal.show();
    }

    // Manual Username Check
    document.addEventListener('DOMContentLoaded', function () {
        const usernameInput = document.getElementById('createUsername');
        const feedback = document.getElementById('usernameFeedback');
        const createBtn = document.getElementById('btnSubmitCreate');
        const checkBtn = document.getElementById('btnCheckUsername');

        if (checkBtn && usernameInput) {
            usernameInput.addEventListener('input', function() {
                if (createBtn) createBtn.disabled = true;
                feedback.innerHTML = '<span class="text-secondary">Silakan cek ketersediaan username</span>';
                usernameInput.classList.remove('is-valid', 'is-invalid');
            });

            checkBtn.addEventListener('click', function () {
                const username = usernameInput.value.trim();

                if (username.length < 3) {
                    feedback.innerHTML = '<span class="text-warning">Username minimal 3 karakter</span>';
                    return;
                }

                feedback.innerHTML = '<span class="text-secondary"><i class="fas fa-spinner fa-spin me-1"></i>Mengecek...</span>';

                fetch(`/api/internal/check-username?username=${encodeURIComponent(username)}`)
                    .then(response => response.json())
                    .then(data => {
                        if (data.exists) {
                            feedback.innerHTML = '<span class="text-danger"><i class="fas fa-times-circle me-1"></i>Username sudah terpakai</span>';
                            usernameInput.classList.add('is-invalid');
                            usernameInput.classList.remove('is-valid');
                            if (createBtn) createBtn.disabled = true;
                        } else {
                            feedback.innerHTML = '<span class="text-success"><i class="fas fa-check-circle me-1"></i>Username tersedia</span>';
                            usernameInput.classList.add('is-valid');
                            usernameInput.classList.remove('is-invalid');
                            if (createBtn) createBtn.disabled = false;
                        }
                    })
                    .catch(error => {
                        feedback.innerHTML = '<span class="text-danger">Gagal mengecek username</span>';
                    });
            });
        }
    });

    // Modal Pricing Logic
    const basePrice = {{ $basePrice ?? 0 }};
    const ipPrice = {{ $ipPrice ?? 0 }};
    
    function calculateCreatePrice() {
        const display = document.getElementById('createPriceDisplay');
        if (!display) return;

        let days = parseInt(document.getElementById('createExpiredInput').value) || 0;
        let ip = document.getElementById('createLimitIpInput') ? parseInt(document.getElementById('createLimitIpInput').value) || 1 : 1;
        
        let isTrial = false;
        if (document.getElementById('payTrial') && document.getElementById('payTrial').checked) {
            isTrial = true;
        }

        let priceVpn = Math.round((basePrice / 30) * days);
        let priceIp = ip > 1 ? (ipPrice * (ip - 1)) : 0;
        
        let total = isTrial ? 0 : (priceVpn + priceIp);
        display.innerText = 'Rp ' + total.toLocaleString('id-ID');
    }

    function calculateRenewPrice() {
        const days = parseInt(document.getElementById('renewExpiredInput').value) || 0;
        const ip = document.getElementById('renewLimitIpInput') ? parseInt(document.getElementById('renewLimitIpInput').value) || 1 : 1;
        const priceVpn = Math.round((basePrice / 30) * days);
        const priceIp = ip > 1 ? (ipPrice * (ip - 1)) : 0;
        const total = priceVpn + priceIp;
        const display = document.getElementById('renewPriceDisplay');
        if (display) {
            display.innerText = 'Rp ' + total.toLocaleString('id-ID');
        }
    }

    function initPricing(btnClass, inputId, displayId) {
        const btns = document.querySelectorAll(btnClass);
        const input = document.getElementById(inputId);
        const display = document.getElementById(displayId);
        
        if (!btns.length) return;

        function updatePrice(days) {
            if (!display) return;
            if (displayId === 'renewPriceDisplay') {
                calculateRenewPrice();
                return;
            }

            const total = Math.round((basePrice / 30) * days);
            display.innerText = 'Rp ' + total.toLocaleString('id-ID');
        }

        btns.forEach(btn => {
            btn.addEventListener('click', function() {
                btns.forEach(b => {
                    b.classList.remove('btn-primary', 'text-white');
                    b.classList.add('btn-outline-primary');
                });
                
                this.classList.remove('btn-outline-primary');
                this.classList.add('btn-primary', 'text-white');
                
                const days = this.getAttribute('data-days');
                if(input) input.value = days;
                updatePrice(days);
            });
        });

        // Initialize active state
        const defaultBtn = document.querySelector(btnClass + '[data-days="30"]');
        if (defaultBtn) {
            defaultBtn.classList.remove('btn-outline-primary');
            defaultBtn.classList.add('btn-primary', 'text-white');
            updatePrice(30);
        }
    }

    document.addEventListener('DOMContentLoaded', function() {
        initPricing('.renew-day-btn', 'renewExpiredInput', 'renewPriceDisplay');

        document.querySelectorAll('.create-day-btn').forEach(btn => {
            btn.addEventListener('click', function() {
                document.querySelectorAll('.create-day-btn').forEach(b => {
                    b.classList.remove('btn-primary', 'text-white');
                    b.classList.add('btn-outline-primary');
                    if (b.dataset.trial) {
                        b.classList.remove('btn-success', 'text-white');
                        b.classList.add('btn-outline-success');
                    }
                });
                
                if (this.dataset.trial) {
                    this.classList.remove('btn-outline-success');
                    this.classList.add('btn-success', 'text-white');
                    document.getElementById('createExpiredInput').value = this.dataset.days;
                    if (document.getElementById('payTrial')) {
                        document.getElementById('payTrial').checked = true;
                    }
                } else {
                    this.classList.remove('btn-outline-primary');
                    this.classList.add('btn-primary', 'text-white');
                    document.getElementById('createExpiredInput').value = this.dataset.days;
                    if (document.getElementById('paySaldo') && document.getElementById('payTrial') && document.getElementById('payTrial').checked) {
                        document.getElementById('paySaldo').checked = true;
                    }
                }
                
                calculateCreatePrice();
            });
        });
        
        const defaultCreateBtn = document.querySelector('.create-day-btn[data-days="30"]');
        if (defaultCreateBtn) {
            defaultCreateBtn.click();
        }

        const renewLimitIpInput = document.getElementById('renewLimitIpInput');
        if (renewLimitIpInput) {
            renewLimitIpInput.addEventListener('input', calculateRenewPrice);
        }

        const createLimitIpInput = document.getElementById('createLimitIpInput');
        if (createLimitIpInput) {
            createLimitIpInput.addEventListener('input', calculateCreatePrice);
        }
    });
</script>

@push('modals')
<!-- Create Modal -->
<div class="modal fade" id="createModal" tabindex="-1" aria-labelledby="createModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
            <div class="modal-header">
                <h5 class="modal-title" id="createModalLabel"><i class="fas fa-plus-circle me-2 text-primary"></i>Buat Akun {{ strtoupper($protocol) }}</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <form action="{{ route('vpn.store', $protocol) }}" method="POST" id="createFormModal">
                @csrf
                <div class="modal-body p-4">
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Username</label>
                        <div class="input-group">
                            <input type="text" name="username" id="createUsername" class="form-control form-control-sm" required>
                            <button class="btn btn-outline-secondary btn-sm" type="button" id="btnCheckUsername">Cek Ketersediaan</button>
                        </div>
                        <small id="usernameFeedback" class="form-text mt-1"></small>
                    </div>
                    @if($protocol === 'ssh')
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Password</label>
                        <input type="text" name="password" class="form-control form-control-sm" required>
                    </div>
                    @else
                    <input type="hidden" name="password" value="auto">
                    <input type="hidden" name="sni_config" value="3">
                    @endif
                    <div class="row mb-3">
                        <div class="col-12 mb-3">
                            <label class="form-label fw-bold text-secondary">Masa Aktif (Hari)</label>
                            <input type="hidden" name="expired" id="createExpiredInput" value="30">
                            <div class="d-flex flex-wrap gap-2">
                                @if(auth()->user()->role === 'customer')
                                    <button type="button" class="btn btn-outline-success create-day-btn" data-days="1" data-trial="true">Trial (15 Menit)</button>
                                @endif
                                @foreach([1, 3, 7, 14, 30, 60] as $day)
                                    <button type="button" class="btn btn-outline-primary create-day-btn" data-days="{{ $day }}">{{ $day }} Hari</button>
                                @endforeach
                            </div>
                            @if(auth()->user()->role === 'customer')
                                <small class="text-muted d-block mt-2"><i class="fas fa-info-circle me-1"></i>Akun trial dibatasi maksimal 3 kali pembuatan per minggu.</small>
                            @endif
                        </div>
                        @if(auth()->user()->role === 'admin')
                        <div class="col-6">
                            <label class="form-label fw-bold text-secondary">Limit IP</label>
                            <input type="number" name="limit_ip" id="createLimitIpInput" class="form-control form-control-sm" value="1" min="1">
                        </div>
                        @else
                        <div class="col-6">
                            <label class="form-label fw-bold text-secondary">Limit IP</label>
                            <input type="number" name="limit_ip" id="createLimitIpInput" class="form-control form-control-sm" value="1" min="1" {{ $maxIpLimit > 0 ? 'max=' . $maxIpLimit : '' }}>
                            <small class="text-muted">{{ $maxIpLimit > 0 ? 'Maks ' . $maxIpLimit . ' IP' : '' }}</small>
                        </div>
                        @endif
                    </div>
                    @if($protocol !== 'ssh')
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Quota (GB)</label>
                        <input type="number" name="quota" class="form-control form-control-sm" value="0" min="0">
                        <small class="text-muted">0 = unlimited</small>
                    </div>
                    @endif
                    
                    @if(Auth::user()->role === 'customer')
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Metode Pembayaran</label>
                        <div class="d-flex gap-3">
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="payment_method" id="paySaldo" value="saldo" checked>
                                <label class="form-check-label" for="paySaldo">Saldo Akun (Rp {{ number_format(Auth::user()->balance, 0, ',', '.') }})</label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="payment_method" id="payQris" value="qris">
                                <label class="form-check-label" for="payQris">QRIS (Otomatis)</label>
                            </div>
                            <div class="form-check d-none">
                                <input class="form-check-input" type="radio" name="payment_method" id="payTrial" value="trial">
                                <label class="form-check-label" for="payTrial">Trial (Gratis)</label>
                            </div>
                        </div>
                    </div>
                    <div class="alert alert-info border-0 shadow-sm mt-3 mb-0">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-1 fw-bold text-dark"><i class="fas fa-receipt me-2"></i>Total Tagihan</h6>
                                <small class="text-dark">Harga per 30 hari: Rp {{ number_format($basePrice ?? 0, 0, ',', '.') }}</small>
                            </div>
                            <h5 class="mb-0 fw-bold text-success" id="createPriceDisplay">Rp 0</h5>
                        </div>
                    </div>
                    @endif
                </div>
                <div class="modal-footer border-0 pt-0">
                    <button type="button" class="btn btn-light" data-bs-dismiss="modal">Batal</button>
                    <button type="submit" class="btn btn-primary px-4" id="btnSubmitCreate" disabled>Buat Akun</button>
                </div>
            </form>
        </div>
    </div>
</div>

<!-- Renew Modal -->
<div class="modal fade" id="renewModal" tabindex="-1" aria-labelledby="renewModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
            <div class="modal-header">
                <h5 class="modal-title" id="renewModalLabel"><i class="fas fa-sync me-2 text-primary"></i>Perpanjang Akun</h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <form method="POST" id="renewForm">
                @csrf
                <div class="modal-body p-4">
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Username</label>
                        <input type="text" id="renewUsernameDisplay" class="form-control form-control-sm" disabled>
                        <input type="hidden" name="username" id="renewUsername">
                    </div>
                    <div class="row mb-3">
                        <div class="col-12 mb-3">
                            <label class="form-label fw-bold text-secondary">Masa Aktif (Hari)</label>
                            <input type="hidden" name="days" id="renewExpiredInput" value="30">
                            <div class="d-flex flex-wrap gap-2">
                                @foreach([1, 3, 7, 14, 30, 60] as $day)
                                    <button type="button" class="btn btn-outline-primary renew-day-btn" data-days="{{ $day }}">{{ $day }} Hari</button>
                                @endforeach
                            </div>
                        </div>
                        @if(auth()->user()->role === 'admin')
                        <div class="col-6">
                            <label class="form-label fw-bold text-secondary">Limit IP</label>
                            <input type="number" name="limit_ip" id="renewLimitIpInput" class="form-control form-control-sm" value="1" min="1">
                        </div>
                        @else
                        <div class="col-6">
                            <label class="form-label fw-bold text-secondary">Limit IP</label>
                            <input type="number" name="limit_ip" id="renewLimitIpInput" class="form-control form-control-sm" value="1" min="1" {{ $maxIpLimit > 0 ? 'max=' . $maxIpLimit : '' }}>
                            <small class="text-muted">{{ $maxIpLimit > 0 ? 'Maks ' . $maxIpLimit . ' IP' : '' }}</small>
                        </div>
                        @endif
                    </div>
                    @if($protocol !== 'ssh')
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Quota (GB)</label>
                        <input type="number" name="quota" class="form-control form-control-sm" value="0" min="0">
                        <small class="text-muted">0 = unlimited</small>
                    </div>
                    @endif

                    @if(Auth::user()->role === 'customer')
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Metode Pembayaran</label>
                        <div class="d-flex gap-3">
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="payment_method" id="renewPaySaldo" value="saldo" checked>
                                <label class="form-check-label" for="renewPaySaldo">Saldo Akun (Rp {{ number_format(Auth::user()->balance, 0, ',', '.') }})</label>
                            </div>
                            <div class="form-check">
                                <input class="form-check-input" type="radio" name="payment_method" id="renewPayQris" value="qris">
                                <label class="form-check-label" for="renewPayQris">QRIS (Otomatis)</label>
                            </div>
                        </div>
                    </div>
                    <div class="alert alert-info border-0 shadow-sm mt-3 mb-0">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="mb-1 fw-bold text-dark"><i class="fas fa-receipt me-2"></i>Total Tagihan</h6>
                                <small class="text-dark">Harga per 30 hari: Rp {{ number_format($basePrice ?? 0, 0, ',', '.') }}</small>
                            </div>
                            <h5 class="mb-0 fw-bold text-success" id="renewPriceDisplay">Rp 0</h5>
                        </div>
                    </div>
                    @endif
                </div>
                <div class="modal-footer border-0 pt-0">
                    <button type="button" class="btn btn-light" data-bs-dismiss="modal">Batal</button>
                    <button type="submit" class="btn btn-primary px-4">Perpanjang</button>
                </div>
            </form>
        </div>
    </div>
</div>
@endpush
@endsection

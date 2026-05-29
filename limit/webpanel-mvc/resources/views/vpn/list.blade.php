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

/* Gradien pada Header Modal */
.modal-header {
    background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%) !important;
    border: none !important;
}

/* Gradien pada Tombol Utama Modal */
.modal-content .btn-primary {
    background: linear-gradient(135deg, #0d47a1 0%, #1565c0 100%) !important;
    border: none !important;
    box-shadow: 0 4px 15px rgba(13, 71, 161, 0.3) !important;
    transition: all 0.2s ease !important;
}

.modal-content .btn-primary:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(13, 71, 161, 0.4) !important;
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
                            if ($user['active'] == 0) {
                                $status = 'suspended';
                            } elseif ($daysLeft <= 3 && $daysLeft >= 0) {
                                $status = 'almost_expired';
                            } elseif ($daysLeft < 0) {
                                $status = 'expired';
                            }
                        @endphp
                        <tr class="account-row border-bottom" data-username="{{ strtolower($user['username']) }}" data-status="{{ $status }}">
                            <td class="ps-3 text-muted py-2">{{ $index + 1 }}</td>
                            <td class="fw-bold text-primary py-2">{{ $user['username'] }}</td>
                            <td class="py-2 fw-medium text-secondary">{{ $user['ip_limit'] ?? 1 }}</td>
                            <td class="py-2 text-secondary">{{ $formattedCreated }}</td>
                            <td class="py-2 text-secondary">{{ $formattedExp }}</td>
                            <td class="py-2">
                                @if($status === 'suspended')
                                    <span class="badge bg-danger">Disuspend</span>
                                @elseif($status === 'almost_expired')
                                    <span class="badge bg-warning text-dark">Hampir Expired</span>
                                @elseif($status === 'expired')
                                    <span class="badge bg-secondary">Expired</span>
                                @else
                                    <span class="badge bg-success">Aktif</span>
                                @endif
                            </td>
                            <td class="text-end pe-3 py-2">
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
                            </td>
                        </tr>
                        @endforeach
                    </tbody>
                </table>
            </div>
            @else
            <div class="p-5 text-center">
                <i class="fas fa-box-open fa-3x text-muted mb-3"></i>
                <h5 class="text-muted">Tidak ada akun yang ditemukan.</h5>
            </div>
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
                    // For the updated JSON response
                    const info = data.config;
                    let link = '';
                    
                    if (protocol === 'vmess') {
                        const vmessObj = {
                            "v": "2",
                            "ps": info.username,
                            "add": info.domain,
                            "port": "443",
                            "id": info.uuid,
                            "aid": "0",
                            "net": "ws",
                            "path": "/vmess",
                            "type": "none",
                            "host": info.domain,
                            "tls": "tls",
                            "sni": info.domain,
                            "allowInsecure": true
                        };
                        link = "vmess://" + btoa(JSON.stringify(vmessObj));
                    } else if (protocol === 'vless') {
                        link = `vless://${info.uuid}@${info.domain}:443?path=/vless&security=tls&encryption=none&type=ws&sni=${info.domain}#${info.username}`;
                    } else if (protocol === 'trojan') {
                        link = `trojan://${info.uuid}@${info.domain}:443?path=/trojan-ws&security=tls&type=ws&sni=${info.domain}#${info.username}`;
                    } else {
                        link = `ss://${info.uuid}@${info.domain}:443#${info.username}`; // Simplified SS
                    }
                    
                    const qrUrl = `https://api.qrserver.com/v1/create-qr-code/?size=250x250&data=${encodeURIComponent(link)}`;
                    
                    const htmlContent = `
                        <div class="text-center mb-3">
                            <img src="${qrUrl}" alt="QR Code" class="img-fluid border p-2 bg-white rounded shadow-sm" style="max-width: 200px;">
                        </div>
                        <div class="text-start bg-light p-3 rounded border">
                            <table class="table table-sm table-borderless mb-0">
                                <tr><td class="text-muted" width="110">Username</td><td class="fw-bold text-dark">: ${info.username}</td></tr>
                                <tr><td class="text-muted">Pass / UUID</td><td class="fw-bold text-dark font-monospace small">: <span style="user-select: all;">${info.uuid}</span></td></tr>
                                <tr><td class="text-muted">Protocol</td><td class="fw-bold text-dark text-uppercase">: ${protocol}</td></tr>
                                <tr><td class="text-muted">Domain</td><td class="fw-bold text-dark">: ${info.domain}</td></tr>
                                <tr><td class="text-muted">Limit IP</td><td class="fw-bold text-dark">: ${info.ip_limit}</td></tr>
                                <tr><td class="text-muted">Quota</td><td class="fw-bold text-dark">: ${info.quota} GB</td></tr>
                            </table>
                        </div>
                        <div class="mt-3 text-start">
                            <label class="form-label fw-bold text-secondary small mb-1">Link Konfigurasi (TLS):</label>
                            <textarea class="form-control font-monospace small bg-dark text-light" rows="3" readonly style="font-size:0.8rem; resize:none;">${link}</textarea>
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
        
        const modal = new bootstrap.Modal(document.getElementById('renewModal'));
        modal.show();
    }
</script>

@push('modals')
<!-- Create Modal -->
<div class="modal fade" id="createModal" tabindex="-1" aria-labelledby="createModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
            <div class="modal-header bg-primary text-white border-0">
                <h5 class="modal-title fw-bold" id="createModalLabel"><i class="fas fa-plus-circle me-2"></i>Buat Akun {{ strtoupper($protocol) }}</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
            </div>
            <form action="{{ route('vpn.store', $protocol) }}" method="POST" id="createFormModal">
                @csrf
                <div class="modal-body p-4">
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Username</label>
                        <input type="text" name="username" class="form-control form-control-sm" required>
                    </div>
                    @if($protocol === 'ssh')
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Password</label>
                        <input type="text" name="password" class="form-control form-control-sm" required>
                    </div>
                    @else
                    <input type="hidden" name="password" value="auto">
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Custom SNI</label>
                        <select name="sni_config" class="form-select form-select-sm">
                            <option value="3">Tanpa konfigurasi (Default)</option>
                            <option value="1">support.zoom.us</option>
                            <option value="2">live.iflix.com</option>
                        </select>
                    </div>
                    @endif
                    <div class="row mb-3">
                        <div class="col-6">
                            <label class="form-label fw-bold text-secondary">Masa Aktif (Hari)</label>
                            <input type="number" name="expired" class="form-control form-control-sm" value="30" min="1" max="365" required>
                        </div>
                        <div class="col-6">
                            <label class="form-label fw-bold text-secondary">Limit IP</label>
                            <input type="number" name="limit_ip" class="form-control form-control-sm" value="1" min="1">
                        </div>
                    </div>
                    @if($protocol !== 'ssh')
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Quota (GB)</label>
                        <input type="number" name="quota" class="form-control form-control-sm" value="0" min="0">
                        <small class="text-muted">0 = unlimited</small>
                    </div>
                    @endif
                </div>
                <div class="modal-footer border-0 pt-0">
                    <button type="button" class="btn btn-light" data-bs-dismiss="modal">Batal</button>
                    <button type="submit" class="btn btn-primary px-4">Buat Akun</button>
                </div>
            </form>
        </div>
    </div>
</div>

<!-- Renew Modal -->
<div class="modal fade" id="renewModal" tabindex="-1" aria-labelledby="renewModalLabel" aria-hidden="true">
    <div class="modal-dialog">
        <div class="modal-content border-0 shadow">
            <div class="modal-header bg-primary text-white border-0">
                <h5 class="modal-title fw-bold" id="renewModalLabel"><i class="fas fa-sync me-2"></i>Perpanjang Akun</h5>
                <button type="button" class="btn-close btn-close-white" data-bs-dismiss="modal" aria-label="Close"></button>
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
                        <div class="col-6">
                            <label class="form-label fw-bold text-secondary">Masa Aktif (Hari)</label>
                            <input type="number" name="days" class="form-control form-control-sm" value="30" min="1" max="365" required>
                        </div>
                        <div class="col-6">
                            <label class="form-label fw-bold text-secondary">Limit IP</label>
                            <input type="number" name="limit_ip" class="form-control form-control-sm" value="1" min="1">
                        </div>
                    </div>
                    @if($protocol !== 'ssh')
                    <div class="mb-3">
                        <label class="form-label fw-bold text-secondary">Quota (GB)</label>
                        <input type="number" name="quota" class="form-control form-control-sm" value="0" min="0">
                        <small class="text-muted">0 = unlimited</small>
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

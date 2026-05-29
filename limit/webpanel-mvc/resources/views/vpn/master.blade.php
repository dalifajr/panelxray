@extends('layouts.app')

<style>
/* Menghilangkan radius sudut pada tombol di dalam form di tengah grup */
.btn-group-sm > form:not(:last-child) > .btn {
    border-top-right-radius: 0;
    border-bottom-right-radius: 0;
}

.btn-group-sm > form:not(:first-child) > .btn {
    border-top-left-radius: 0;
    border-bottom-left-radius: 0;
    border-left: 0; /* Menghilangkan border ganda */
}

/* Jika tombol pertama bukan form tapi setelahnya ada form */
.btn-group-sm > .btn:first-child:not(:last-child) {
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
            <h2 class="fw-bold mb-0 text-uppercase"><i class="fas fa-database text-primary me-2"></i> Master Data VPN</h2>
        </div>
    </div>

    <div class="card shadow-sm border-0">
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-hover table-sm table-borderless align-middle mb-0" id="masterTable">
                    <thead class="table-light">
                        <tr>
                            <th class="ps-3 py-2">No.</th>
                            <th class="py-2">Protokol</th>
                            <th class="py-2">Username</th>
                            <th class="py-2">Password / UUID</th>
                            <th class="py-2">Status</th>
                            <th class="py-2">Limit IP</th>
                            <th class="py-2">Kedaluwarsa</th>
                            <th class="text-end pe-3 py-2">Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach($parsedUsers as $index => $user)
                        <tr class="border-bottom">
                            <td class="ps-3 text-muted py-2">{{ $index + 1 }}</td>
                            <td class="py-2"><span class="badge bg-secondary text-uppercase">{{ $user['service'] }}</span></td>
                            <td class="fw-bold text-primary py-2">{{ $user['username'] }}</td>
                            <td class="py-2"><span class="text-muted font-monospace small" style="user-select: all;">{{ $user['uuid'] ?? '***' }}</span></td>
                            <td class="py-2">
                                @if($user['active'] == 1)
                                    <span class="badge bg-success">Aktif</span>
                                @else
                                    <span class="badge bg-danger">Disuspend</span>
                                @endif
                            </td>
                            <td class="py-2 fw-medium text-secondary">{{ $user['ip_limit'] ?? 1 }}</td>
                            <td class="py-2 text-secondary">
                                @php
                                    $expStr = $user['expires_at'] ?? '';
                                    if (!empty($expStr)) {
                                        $expDate = \Carbon\Carbon::parse($expStr);
                                        $isExpired = $expDate->isPast();
                                        $formattedExp = $expDate->format('d M Y');
                                    } else {
                                        $isExpired = false;
                                        $formattedExp = '-';
                                    }
                                    
                                    $createdStr = $user['created_at'] ?? '';
                                    $formattedCreated = !empty($createdStr) ? \Carbon\Carbon::parse($createdStr)->format('d M Y') : '-';
                                @endphp
                                @if($isExpired)
                                    <span class="badge bg-danger">Expired</span>
                                @else
                                    {{ $formattedExp }}
                                @endif
                            </td>
                            <td class="text-end pe-3 py-2">
                                <div class="btn-group btn-group-sm">
                                    <button type="button" class="btn btn-outline-info" onclick="viewConfig('{{ $user['service'] }}', '{{ $user['username'] }}')" title="Lihat Konfigurasi">
                                        <i class="fas fa-qrcode"></i>
                                    </button>
                                @if($user['active'] == 1)
                                <form action="{{ route('vpn.suspend', [$user['service'], $user['username']]) }}" method="POST" class="d-inline mb-0">
                                    @csrf
                                    <button type="submit" class="btn btn-outline-warning" title="Suspend Akun">
                                        <i class="fas fa-ban"></i>
                                    </button>
                                </form>
                                @else
                                <form action="{{ route('vpn.unsuspend', [$user['service'], $user['username']]) }}" method="POST" class="d-inline mb-0">
                                    @csrf
                                    <button type="submit" class="btn btn-outline-success" title="Aktifkan Kembali">
                                        <i class="fas fa-play"></i>
                                    </button>
                                </form>
                                @endif
                                <form action="{{ route('vpn.delete', [$user['service'], $user['username']]) }}" method="POST" class="d-inline mb-0">
                                    @csrf
                                    <button type="button" class="btn btn-outline-danger btn-delete" data-user="{{ $user['username'] }}" title="Hapus Akun">
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
        </div>
    </div>
</div>

<!-- DataTables -->
<link rel="stylesheet" href="https://cdn.datatables.net/1.13.4/css/dataTables.bootstrap5.min.css">
<script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
<script src="https://cdn.datatables.net/1.13.4/js/jquery.dataTables.min.js"></script>
<script src="https://cdn.datatables.net/1.13.4/js/dataTables.bootstrap5.min.js"></script>

<script>
    $(document).ready(function() {
        $('#masterTable').DataTable({
            language: {
                search: "Cari Data:",
                lengthMenu: "Tampilkan _MENU_ data",
                info: "Menampilkan _START_ sampai _END_ dari _TOTAL_ data",
                paginate: {
                    first: "Awal",
                    last: "Akhir",
                    next: "Lanjut",
                    previous: "Kembali"
                }
            }
        });

        // Handle Delete Confirmation
        $('.btn-delete').on('click', function(e) {
            e.preventDefault();
            const form = $(this).closest('form');
            const username = $(this).data('user');
            
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
                                <tr><td class="text-muted" width="80">Username</td><td class="fw-bold text-dark">: ${info.username}</td></tr>
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
                Swal.fire('Error', 'Gagal mengambil konfigurasi dari server', 'error');
            });
    }
</script>
@endsection

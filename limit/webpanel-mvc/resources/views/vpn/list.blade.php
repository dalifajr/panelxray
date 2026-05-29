@extends('layouts.app')

@section('content')
<div class="container py-4">
    <div class="row mb-4 align-items-center">
        <div class="col-md-6">
            <h2 class="fw-bold mb-0 text-uppercase">Daftar Akun {{ strtoupper($protocol) }}</h2>
        </div>
        <div class="col-md-6 text-end">
            <a href="{{ route('vpn.create', $protocol) }}" class="btn btn-primary">
                <i class="fas fa-plus me-1"></i> Buat Akun Baru
            </a>
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
                <table class="table table-hover table-borderless align-middle mb-0" id="accountsTable">
                    <thead class="table-light">
                        <tr>
                            <th class="ps-4">No.</th>
                            <th>Username</th>
                            <th>Password / UUID</th>
                            <th>Limit IP</th>
                            <th>Dibuat</th>
                            <th>Kedaluwarsa</th>
                            <th>Status</th>
                            <th class="text-end pe-4">Aksi</th>
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
                        <tr class="account-row" data-username="{{ strtolower($user['username']) }}" data-status="{{ $status }}">
                            <td class="ps-4 text-muted">{{ $index + 1 }}</td>
                            <td class="fw-bold text-primary">{{ $user['username'] }}</td>
                            <td><span class="text-muted font-monospace small" style="user-select: all;">{{ $user['uuid'] ?? '***' }}</span></td>
                            <td><span class="badge bg-info text-dark">{{ $user['ip_limit'] ?? 1 }}</span></td>
                            <td>{{ $formattedCreated }}</td>
                            <td>{{ $formattedExp }}</td>
                            <td>
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
                            <td class="text-end pe-4">
                                @if($user['active'] == 1)
                                <form action="{{ route('vpn.suspend', [$protocol, $user['username']]) }}" method="POST" class="d-inline">
                                    @csrf
                                    <button type="submit" class="btn btn-sm btn-outline-warning" title="Suspend">
                                        <i class="fas fa-pause"></i>
                                    </button>
                                </form>
                                @else
                                <form action="{{ route('vpn.unsuspend', [$protocol, $user['username']]) }}" method="POST" class="d-inline">
                                    @csrf
                                    <button type="submit" class="btn btn-sm btn-outline-success" title="Unsuspend">
                                        <i class="fas fa-play"></i>
                                    </button>
                                </form>
                                @endif

                                <a href="{{ route('vpn.renew', [$protocol, $user['username']]) }}" class="btn btn-sm btn-outline-info" title="Renew">
                                    <i class="fas fa-sync"></i>
                                </a>

                                <button type="button" class="btn btn-sm btn-outline-dark" onclick="viewConfig('{{ $protocol }}', '{{ $user['username'] }}')" title="View Config">
                                    <i class="fas fa-qrcode"></i>
                                </button>

                                <form action="{{ route('vpn.delete', [$protocol, $user['username']]) }}" method="POST" class="d-inline action-delete">
                                    @csrf
                                    <button type="button" class="btn btn-sm btn-outline-danger btn-delete" data-user="{{ $user['username'] }}" title="Hapus">
                                        <i class="fas fa-trash"></i>
                                    </button>
                                </form>
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
                } else {
                    Swal.fire({
                        title: `Konfigurasi ${username}`,
                        html: `<pre class="text-start bg-light p-3 rounded font-monospace" style="max-height: 300px; overflow-y: auto; font-size: 0.85rem; user-select: all;">${data.config}</pre>`,
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

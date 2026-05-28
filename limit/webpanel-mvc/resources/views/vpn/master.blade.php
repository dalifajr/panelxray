@extends('layouts.app')

@section('content')
<div class="container py-4">
    <div class="row mb-4 align-items-center">
        <div class="col-md-6">
            <h2 class="fw-bold mb-0 text-uppercase"><i class="fas fa-database text-primary me-2"></i> Master Data VPN</h2>
        </div>
    </div>

    <div class="card shadow-sm border-0">
        <div class="card-body">
            <div class="table-responsive">
                <table class="table table-hover align-middle mb-0" id="masterTable">
                    <thead class="table-light">
                        <tr>
                            <th>No.</th>
                            <th>Protokol</th>
                            <th>Username</th>
                            <th>Password / UUID</th>
                            <th>Status</th>
                            <th>Limit IP</th>
                            <th>Kedaluwarsa</th>
                            <th class="text-end">Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach($parsedUsers as $index => $user)
                        <tr>
                            <td class="text-muted">{{ $index + 1 }}</td>
                            <td><span class="badge bg-secondary text-uppercase">{{ $user['service'] }}</span></td>
                            <td class="fw-bold text-primary">{{ $user['username'] }}</td>
                            <td><span class="text-muted font-monospace small" style="user-select: all;">{{ $user['uuid'] ?? '***' }}</span></td>
                            <td>
                                @if($user['active'] == 1)
                                    <span class="badge bg-success">Aktif</span>
                                @else
                                    <span class="badge bg-warning text-dark">Suspended</span>
                                @endif
                            </td>
                            <td><span class="badge bg-info text-dark">{{ $user['ip_limit'] ?? 1 }}</span></td>
                            <td>
                                @php
                                    $expDate = \Carbon\Carbon::parse($user['expires_at']);
                                    $isExpired = $expDate->isPast();
                                @endphp
                                <span class="badge {{ $isExpired ? 'bg-danger' : 'bg-success' }}">
                                    {{ $expDate->format('d M Y') }}
                                </span>
                            </td>
                            <td class="text-end">
                                @if($user['active'] == 1)
                                <form action="{{ route('vpn.suspend', [$user['service'], $user['username']]) }}" method="POST" class="d-inline">
                                    @csrf
                                    <button type="submit" class="btn btn-sm btn-outline-warning" title="Suspend">
                                        <i class="fas fa-pause"></i>
                                    </button>
                                </form>
                                @else
                                <form action="{{ route('vpn.unsuspend', [$user['service'], $user['username']]) }}" method="POST" class="d-inline">
                                    @csrf
                                    <button type="submit" class="btn btn-sm btn-outline-success" title="Unsuspend">
                                        <i class="fas fa-play"></i>
                                    </button>
                                </form>
                                @endif

                                <a href="{{ route('vpn.renew', [$user['service'], $user['username']]) }}" class="btn btn-sm btn-outline-info" title="Renew">
                                    <i class="fas fa-sync"></i>
                                </a>

                                <button type="button" class="btn btn-sm btn-outline-dark" onclick="viewConfig('{{ $user['service'] }}', '{{ $user['username'] }}')" title="View Config">
                                    <i class="fas fa-qrcode"></i>
                                </button>

                                <form action="{{ route('vpn.delete', [$user['service'], $user['username']]) }}" method="POST" class="d-inline action-delete">
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

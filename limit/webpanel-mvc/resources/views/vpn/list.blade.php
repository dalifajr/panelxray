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
                            <th class="text-end pe-4">Aksi</th>
                        </tr>
                    </thead>
                    <tbody>
                        @foreach($parsedUsers as $index => $user)
                        <tr>
                            <td class="ps-4 text-muted">{{ $index + 1 }}</td>
                            <td class="fw-bold text-primary">{{ $user['username'] }}</td>
                            <td><span class="text-muted font-monospace small" style="user-select: all;">{{ $user['uuid'] ?? '***' }}</span></td>
                            <td><span class="badge bg-info text-dark">{{ $user['ip_limit'] ?? 1 }}</span></td>
                            @php
                                $createdStr = $user['created_at'] ?? '';
                                $formattedCreated = !empty($createdStr) ? \Carbon\Carbon::parse($createdStr)->format('d M Y') : '-';
                            @endphp
                            <td>{{ $formattedCreated }}</td>
                            <td>
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
                                @endphp
                                <span class="badge {{ $isExpired ? 'bg-danger' : 'bg-success' }}">
                                    {{ $formattedExp }}
                                </span>
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

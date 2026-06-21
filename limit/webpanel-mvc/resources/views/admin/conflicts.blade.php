@extends('layouts.app')

@section('content')
<div class="container-fluid px-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h2 class="mb-0 text-dark fw-bold">Resolusi Konflik Restore</h2>
            <p class="text-muted mb-0">Beberapa pengguna atau akun VPN memiliki nama yang sama dengan yang sudah ada di server ini. Silakan selesaikan bentrokan data di bawah ini.</p>
        </div>
        <a href="{{ route('admin.settings') }}" class="btn btn-secondaryfw-bold"><i class="fas fa-arrow-left me-2"></i>Kembali ke Settings</a>
    </div>

    <div class="row">
        <div class="col-12 mb-4">
            <div class="card border-0 shadow-sm">
                <div class="card-header bg-white border-0 pt-4 pb-0">
                    <h5 class="mb-0 fw-bold"><i class="fas fa-users-cog me-2 text-warning"></i>Daftar Konflik Pengguna Duplikat</h5>
                </div>
                <div class="card-body p-4">
                    <div class="table-responsive">
                        <table class="table table-hover align-middle border" id="conflicts-table">
                            <thead class="table-light">
                                <tr>
                                    <th>Username</th>
                                    <th>Data Lama (Backup)</th>
                                    <th>Data Aktif (VPS Baru)</th>
                                    <th class="text-center" style="width: 300px;">Aksi Penyelesaian</th>
                                </tr>
                            </thead>
                            <tbody>
                                @foreach($conflicts as $username => $c)
                                <tr id="row-{{ $username }}">
                                    <td class="fw-bold text-primary">
                                        <i class="fas fa-user-circle me-1"></i>{{ $username }}
                                    </td>
                                    <td>
                                        <div class="small">
                                            <strong>Nama:</strong> {{ $c['old_name'] }}<br>
                                            <strong>Role:</strong> <span class="badge bg-secondary">{{ $c['old_role'] }}</span><br>
                                            <strong>Saldo:</strong> Rp {{ number_format($c['old_balance'] ?? 0, 0, ',', '.') }}<br>
                                            <span class="text-muted">Email: {{ $c['old_email'] ?: '-' }}</span>
                                        </div>
                                    </td>
                                    <td>
                                        <div class="small">
                                            <strong>Nama:</strong> {{ $c['new_name'] }}<br>
                                            <strong>Role:</strong> <span class="badge bg-primary">{{ $c['new_role'] }}</span><br>
                                            <strong>Saldo:</strong> Rp {{ number_format($c['new_balance'] ?? 0, 0, ',', '.') }}<br>
                                            <span class="text-muted">Email: {{ $c['new_email'] ?: '-' }}</span>
                                        </div>
                                    </td>
                                    <td>
                                        <div class="d-flex flex-column gap-2">
                                            <button onclick="resolve('{{ $username }}', 'rename_backup')" class="btn btn-warning btn-sm fw-bold">
                                                <i class="fas fa-edit me-1"></i>Rename User Backup
                                            </button>
                                            <button onclick="resolve('{{ $username }}', 'overwrite')" class="btn btn-danger btn-sm fw-bold">
                                                <i class="fas fa-user-times me-1"></i>Timpa (Ganti Data Baru)
                                            </button>
                                            <button onclick="resolve('{{ $username }}', 'ignore')" class="btn btn-outline-secondary btn-sm fw-bold">
                                                <i class="fas fa-minus-circle me-1"></i>Abaikan (Pakai Data Baru)
                                            </button>
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
    </div>
</div>

<script>
function resolve(username, action) {
    if (action === 'ignore') {
        Swal.fire({
            title: 'Abaikan User Backup?',
            text: `Data user backup '${username}' akan dibuang. Server akan tetap menggunakan data aktif saat ini.`,
            icon: 'question',
            showCancelButton: true,
            confirmButtonColor: '#6c757d',
            confirmButtonText: 'Ya, Abaikan',
            cancelButtonText: 'Batal'
        }).then((result) => {
            if (result.isConfirmed) {
                sendResolution(username, action);
            }
        });
    } else if (action === 'overwrite') {
        Swal.fire({
            title: 'Timpa Data Aktif?',
            text: `Data aktif untuk '${username}' di VPS saat ini akan dihapus dan diganti penuh dengan data dari backup. Tindakan ini tidak bisa dibatalkan!`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#dc3545',
            confirmButtonText: 'Ya, Timpa Data',
            cancelButtonText: 'Batal'
        }).then((result) => {
            if (result.isConfirmed) {
                sendResolution(username, action);
            }
        });
    } else if (action === 'rename_backup') {
        Swal.fire({
            title: 'Rename User Backup',
            input: 'text',
            inputLabel: 'Masukkan Username Baru untuk User Backup',
            inputValue: username + '_old',
            inputPlaceholder: 'john_doe_old',
            showCancelButton: true,
            inputValidator: (value) => {
                if (!value) {
                    return 'Username baru wajib diisi!';
                }
                if (!/^[a-zA-Z0-9_.-]+$/.test(value)) {
                    return 'Username hanya boleh mengandung huruf, angka, _, -, .';
                }
            }
        }).then((result) => {
            if (result.isConfirmed) {
                sendResolution(username, action, result.value);
            }
        });
    }
}

function sendResolution(username, action, newUsername = null) {
    Swal.fire({
        title: 'Memproses resolusi...',
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });

    fetch("{{ route('admin.settings.restore.conflicts.resolve') }}", {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRF-TOKEN': '{{ csrf_token() }}'
        },
        body: JSON.stringify({
            username: username,
            action: action,
            new_username: newUsername
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            Swal.fire('Berhasil', 'Konflik berhasil diselesaikan.', 'success').then(() => {
                const row = document.getElementById(`row-${username}`);
                if (row) {
                    row.remove();
                }
                
                // If table is empty, redirect back to settings
                const table = document.getElementById('conflicts-table');
                const rows = table.getElementsByTagName('tbody')[0].getElementsByTagName('tr');
                if (rows.length === 0) {
                    Swal.fire('Selesai', 'Semua resolusi konflik telah selesai!', 'success').then(() => {
                        window.location.href = "{{ route('admin.settings') }}";
                    });
                }
            });
        } else {
            Swal.fire('Gagal', data.error || 'Gagal menyelesaikan konflik.', 'error');
        }
    })
    .catch(error => {
        Swal.fire('Error', 'Gagal memproses resolusi konflik.', 'error');
        console.error(error);
    });
}
</script>
@endsection
